import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest'
import { createServer, type IncomingMessage, type Server } from 'node:http'
import { createApp, createRouter, eventHandler, toNodeListener, type H3Event } from 'h3'
import type { Wine } from '../shared/catalog'
import { accountConfig, maxHostDecision, type AccountConfigSource } from '../server/utils/account'
import {
  historyClearRoute, historyDeleteDayRoute, historyDeleteWineRoute, historyItemRoute, historyListRoute, historyRecordRoute,
  savedDeleteRoute, savedListRoute, savedPutRoute, savedSlugsRoute, settingsRoute, type WineLookup,
} from '../server/utils/diary'
import { colorKey, diarySnapshot, matchesFilter, sugarKey, wineStyleLine } from '../shared/diary'

const TOKEN = 'w'.repeat(64)
const SLUG = 'abrau-durso-brut-beloe'
const SESSION = '__Host-cv_session=session-token'
type Seen = { method: string; url: string; headers: IncomingMessage['headers']; body: string }
let seen: Seen[] = []
let reply: (request: Seen) => { status: number; body?: unknown } = () => ({ status: 200, body: {} })
let lookups: string[] = []
let lookup: WineLookup
let mock = false
let service: Server
let site: Server
let siteUrl = ''

const WINE = {
  slug: SLUG, name: 'Абрау-Дюрсо Брют', producer: 'Абрау-Дюрсо', region: 'Краснодарский край', grapes: ['Шардоне', 'Пино нуар'],
  color: 'Белое', category: 'Брют', rating: 0, image: '', alcohol: null, servingTemperature: null, pairings: [], description: null, source: '',
} satisfies Wine

function listen(server: Server): Promise<string> {
  return new Promise(resolve => server.listen(0, '127.0.0.1', () => {
    const address = server.address()
    if (!address || typeof address === 'string') throw new Error('No port')
    resolve(`http://127.0.0.1:${address.port}`)
  }))
}

beforeAll(async () => {
  service = createServer((req, res) => {
    let body = ''
    req.on('data', chunk => { body += chunk })
    req.on('end', () => {
      const request = { method: req.method ?? '', url: req.url ?? '', headers: req.headers, body }
      seen.push(request)
      const answer = reply(request)
      res.writeHead(answer.status, { 'Content-Type': 'application/json' })
      res.end(answer.body === undefined ? '' : JSON.stringify(answer.body))
    })
  })
  const serviceUrl = await listen(service)
  const source: AccountConfigSource = () => accountConfig({ endpoint: serviceUrl, token: TOKEN, publicOrigin: 'https://chtozavino.ru' }, { timeoutMs: 500 })
  const counted: WineLookup = slug => { lookups.push(slug); return lookup(slug) }
  const routes: Record<string, (event: H3Event) => unknown> = {
    '/api/account/history': event => event.method === 'POST' ? historyRecordRoute(event, source, { mock, lookup: counted })
      : event.method === 'DELETE' ? historyClearRoute(event, source) : historyListRoute(event, source),
    [`/api/account/history/${SLUG}`]: event => event.method === 'DELETE' ? historyDeleteWineRoute(event, source, SLUG) : historyItemRoute(event, source, SLUG),
    '/api/account/history/bad': event => historyItemRoute(event, source, '../me'),
    [`/api/account/history/${SLUG}/days/2026-10-20`]: event => historyDeleteDayRoute(event, source, SLUG, '2026-10-20'),
    [`/api/account/history/${SLUG}/days/bad`]: event => historyDeleteDayRoute(event, source, SLUG, '20-10-2026'),
    '/api/account/me': event => settingsRoute(event, source),
    '/api/account/saved': event => savedListRoute(event, source),
    '/api/account/saved/slugs': event => savedSlugsRoute(event, source),
    [`/api/account/saved/${SLUG}`]: event => event.method === 'DELETE' ? savedDeleteRoute(event, source, SLUG) : savedPutRoute(event, source, SLUG, { lookup: counted }),
  }
  const router = createRouter()
  for (const [path, route] of Object.entries(routes)) router.use(path, eventHandler(route))
  const app = createApp()
  app.use(router)
  site = createServer(toNodeListener(app))
  siteUrl = await listen(site)
})
afterAll(async () => {
  for (const server of [service, site]) {
    server.closeAllConnections()
    await new Promise<void>(resolve => server.close(() => resolve()))
  }
})
beforeEach(() => {
  seen = []
  lookups = []
  mock = false
  lookup = async () => WINE
  reply = () => ({ status: 200, body: {} })
})

function call(path: string, init: RequestInit & { cookie?: string | null } = {}) {
  const headers = new Headers(init.headers)
  if (init.cookie !== null) headers.set('cookie', init.cookie ?? SESSION)
  if (init.method && init.method !== 'GET' && !headers.has('origin')) headers.set('origin', 'https://chtozavino.ru')
  return fetch(`${siteUrl}${path}`, { ...init, headers })
}
const json = (body: unknown) => ({ body: JSON.stringify(body), headers: { 'content-type': 'application/json' } })

describe('diary history routes', () => {
  it('lists the history in the browser shape without a service call when logged out', async () => {
    const anonymous = await call('/api/account/history', { cookie: null })
    expect(anonymous.status).toBe(401)
    expect(await anonymous.json()).toEqual({ error: 'session_required' })
    expect(seen).toEqual([])

    reply = () => ({ status: 200, body: {
      save_history: false,
      items: [{ slug: SLUG, wine: { name: 'Брют', producer: 'Абрау', unknown: 'x' }, first_met_at: '2026-06-03T10:00:00Z', last_met_at: '2026-10-19T10:00:00Z', days_count: 4, sources: ['photo', 'telegram', 7], saved_status: 'want' }],
    } })
    const response = await call('/api/account/history')
    expect(response.status).toBe(200)
    expect(response.headers.get('cache-control')).toBe('no-store')
    expect(await response.json()).toEqual({
      saveHistory: false,
      items: [{ slug: SLUG, wine: { name: 'Брют', producer: 'Абрау' }, firstMetAt: '2026-06-03T10:00:00Z', lastMetAt: '2026-10-19T10:00:00Z', daysCount: 4, sources: ['photo', 'telegram'], savedStatus: 'want' }],
    })
    expect(seen[0]).toMatchObject({ method: 'GET', url: '/v1/me/history' })
    expect(seen[0]!.headers['x-session-token']).toBe('session-token')
    expect(seen[0]!.headers.authorization).toBe(`Bearer ${TOKEN}`)
  })

  it('accepts a long history answer', async () => {
    const items = Array.from({ length: 2000 }, (_, index) => ({ slug: `wine-${index}`, wine: { name: 'Вино '.repeat(20), producer: 'Винодельня '.repeat(10) }, days_count: 1, sources: ['photo'] }))
    reply = () => ({ status: 200, body: { items, save_history: true } })
    const response = await call('/api/account/history')
    expect(response.status).toBe(200)
    expect((await response.json()).items).toHaveLength(2000)
  })

  it('shows one wine with its dates and refuses a bad slug locally', async () => {
    reply = () => ({ status: 200, body: { slug: SLUG, wine: null, days_count: 1, sources: ['max'], saved_status: null, days: [{ met_on: '2026-10-20', source: 'max', first_at: '2026-10-20T09:00:00Z' }] } })
    const response = await call(`/api/account/history/${SLUG}`)
    expect(await response.json()).toMatchObject({ slug: SLUG, wine: null, days: [{ metOn: '2026-10-20', source: 'max', firstAt: '2026-10-20T09:00:00Z' }] })
    seen = []
    const bad = await call('/api/account/history/bad')
    expect(bad.status).toBe(404)
    expect(seen).toEqual([])
  })

  it('records a found wine with a snapshot that the server builds', async () => {
    reply = () => ({ status: 200, body: { status: 'recorded', met_on: '2026-10-20' } })
    const response = await call('/api/account/history', { method: 'POST', ...json({ slug: SLUG, source: 'photo', wine_snapshot: { name: 'forged' } }) })
    expect(response.status).toBe(200)
    expect(await response.json()).toEqual({ status: 'recorded', metOn: '2026-10-20' })
    expect(lookups).toEqual([SLUG])
    expect(JSON.parse(seen[0]!.body)).toEqual({
      slug: SLUG, source: 'photo',
      wine_snapshot: { name: 'Абрау-Дюрсо Брют', producer: 'Абрау-Дюрсо', color: 'Белое', sugar: 'Брют', region: 'Краснодарский край', grapes: ['Шардоне', 'Пино нуар'] },
    })
  })

  it('records without a snapshot when the catalogue does not answer', async () => {
    lookup = async () => { throw new Error('timeout') }
    reply = () => ({ status: 200, body: { status: 'already', met_on: '2026-10-20' } })
    const response = await call('/api/account/history', { method: 'POST', ...json({ slug: SLUG, source: 'shelf' }) })
    expect(await response.json()).toEqual({ status: 'already', metOn: '2026-10-20' })
    expect(JSON.parse(seen[0]!.body)).toEqual({ slug: SLUG, source: 'shelf' })
  })

  it.each([
    ['an unknown wine', { slug: SLUG, source: 'photo' }, 404, 'unknown_wine', true],
    ['a bad slug', { slug: '../me', source: 'photo' }, 400, 'invalid_request', false],
    ['a bot source', { slug: SLUG, source: 'telegram' }, 400, 'invalid_request', false],
  ])('refuses %s without a service call', async (_, body, status, error, unknown) => {
    if (unknown) lookup = async () => null
    const response = await call('/api/account/history', { method: 'POST', ...json(body) })
    expect(response.status).toBe(status)
    expect(await response.json()).toEqual({ error })
    expect(seen).toEqual([])
  })

  it('refuses a record in mock mode and from another site', async () => {
    mock = true
    const demo = await call('/api/account/history', { method: 'POST', ...json({ slug: SLUG, source: 'photo' }) })
    expect(demo.status).toBe(409)
    expect(await demo.json()).toEqual({ error: 'mock_mode' })
    mock = false
    const foreign = await call('/api/account/history', { method: 'POST', ...json({ slug: SLUG, source: 'photo' }), headers: { origin: 'https://evil.example', 'content-type': 'application/json' } })
    expect(foreign.status).toBe(403)
    expect(seen).toEqual([])
    expect(lookups).toEqual([])
  })

  it('deletes a date, a wine, and the whole history', async () => {
    expect((await call(`/api/account/history/${SLUG}/days/2026-10-20`, { method: 'DELETE' })).status).toBe(200)
    expect((await call(`/api/account/history/${SLUG}/days/bad`, { method: 'DELETE' })).status).toBe(404)
    expect((await call(`/api/account/history/${SLUG}`, { method: 'DELETE' })).status).toBe(200)
    expect((await call('/api/account/history', { method: 'DELETE' })).status).toBe(200)
    expect(seen.map(item => `${item.method} ${item.url}`)).toEqual([
      `DELETE /v1/me/history/${SLUG}/days/2026-10-20`,
      `DELETE /v1/me/history/${SLUG}`,
      'DELETE /v1/me/history',
    ])
  })

  it('passes a missing wine on as 404', async () => {
    reply = () => ({ status: 404, body: { error: 'not_found' } })
    const response = await call(`/api/account/history/${SLUG}`, { method: 'DELETE' })
    expect(response.status).toBe(404)
    expect(await response.json()).toEqual({ error: 'not_found' })
  })

  it('switches the history recording', async () => {
    reply = () => ({ status: 200, body: { user: { username: 'anna', save_history: false } } })
    const response = await call('/api/account/me', { method: 'PATCH', ...json({ saveHistory: false }) })
    expect(await response.json()).toEqual({ user: { username: 'anna', save_history: false } })
    expect(seen[0]).toMatchObject({ method: 'PATCH', url: '/v1/me' })
    expect(JSON.parse(seen[0]!.body)).toEqual({ save_history: false })
    seen = []
    expect((await call('/api/account/me', { method: 'PATCH', ...json({ saveHistory: 'no' }) })).status).toBe(400)
    expect(seen).toEqual([])
  })
})

describe('saved wine routes', () => {
  it('lists the saved wines and the pin states', async () => {
    reply = request => request.url === '/v1/me/saved/slugs'
      ? { status: 200, body: { items: [{ slug: SLUG, status: 'liked' }, { slug: 'x', status: 'bad' }] } }
      : { status: 200, body: { items: [{ slug: SLUG, wine: { name: 'Брют' }, status: 'disliked', source: 'lineup', added_at: '2026-10-19T10:00:00Z', updated_at: '2026-10-20T10:00:00Z', in_history: false }] } }
    expect(await (await call('/api/account/saved/slugs')).json()).toEqual({ items: [{ slug: SLUG, status: 'liked' }] })
    expect(await (await call('/api/account/saved')).json()).toEqual({
      items: [{ slug: SLUG, wine: { name: 'Брют' }, status: 'disliked', source: 'lineup', addedAt: '2026-10-19T10:00:00Z', updatedAt: '2026-10-20T10:00:00Z', inHistory: false }],
    })
  })

  it('saves a wine with a server snapshot, and changes a status without a catalogue request', async () => {
    reply = request => ({ status: 200, body: { slug: SLUG, status: JSON.parse(request.body).status, source: 'dinner_lens', in_history: true } })
    const saved = await call(`/api/account/saved/${SLUG}`, { method: 'PUT', ...json({ status: 'want', source: 'dinner_lens' }) })
    expect(await saved.json()).toMatchObject({ slug: SLUG, status: 'want', inHistory: true })
    expect(seen[0]).toMatchObject({ method: 'PUT', url: `/v1/me/saved/${SLUG}` })
    expect(JSON.parse(seen[0]!.body)).toMatchObject({ status: 'want', source: 'dinner_lens', wine_snapshot: { name: 'Абрау-Дюрсо Брют' } })
    seen = []
    lookups = []
    await call(`/api/account/saved/${SLUG}`, { method: 'PUT', ...json({ status: 'liked', source: 'dinner_lens', change: true }) })
    expect(lookups).toEqual([])
    expect(JSON.parse(seen[0]!.body)).toEqual({ status: 'liked', source: 'dinner_lens' })
  })

  it.each([
    [{ status: 'favourite', source: 'photo' }],
    [{ status: 'want', source: 'telegram' }],
    [{ status: 'want' }],
  ])('refuses an invalid save %j', async body => {
    const response = await call(`/api/account/saved/${SLUG}`, { method: 'PUT', ...json(body) })
    expect(response.status).toBe(400)
    expect(seen).toEqual([])
  })

  it('passes the full list refusal on and removes a wine', async () => {
    reply = () => ({ status: 409, body: { error: 'saved_full' } })
    const full = await call(`/api/account/saved/${SLUG}`, { method: 'PUT', ...json({ status: 'want', source: 'photo' }) })
    expect(full.status).toBe(409)
    expect(await full.json()).toEqual({ error: 'saved_full' })
    reply = () => ({ status: 204 })
    expect((await call(`/api/account/saved/${SLUG}`, { method: 'DELETE' })).status).toBe(200)
    expect(seen.at(-1)).toMatchObject({ method: 'DELETE', url: `/v1/me/saved/${SLUG}` })
  })

  it('keeps the list routes off the MAX mini-app host', () => {
    expect(maxHostDecision('GET', '/api/account/history')).toBe('reject')
    expect(maxHostDecision('PUT', `/api/account/saved/${SLUG}`)).toBe('reject')
    expect(maxHostDecision('PATCH', '/api/account/me')).toBe('reject')
  })
})

describe('shared diary rules', () => {
  it('builds a snapshot with known keys and limits', () => {
    expect(diarySnapshot({ name: '  Брют  ', producer: '', color: 'Белое', category: 'Брют', grapes: ['', 'Шардоне', 3] })).toEqual({ name: 'Брют', color: 'Белое', sugar: 'Брют', grapes: ['Шардоне'] })
    expect(diarySnapshot({})).toBeNull()
    const long = diarySnapshot({ name: 'я'.repeat(500), producer: 'я'.repeat(500), region: 'я'.repeat(500), grapes: Array.from({ length: 30 }, () => 'я'.repeat(100)) })!
    expect(long.name).toHaveLength(200)
    expect(new TextEncoder().encode(JSON.stringify(long)).byteLength).toBeLessThanOrEqual(2048)
  })

  it.each([
    ['Белое', 'white'], ['Красное', 'red'], ['Розовое', 'rose'], ['Оранжевое', 'orange'], ['', null],
  ])('groups the color %s', (value, key) => {
    expect(colorKey(value)).toBe(key)
  })

  it.each([
    ['Сухое', 'dry'], ['Полусухое', 'semi_dry'], ['Полусладкое', 'semi_sweet'], ['Сладкое', 'sweet'],
    ['Брют', 'brut'], ['Экстра-брют', 'extra_brut'], ['Экстра брют', 'extra_brut'], ['Брют натюр', 'brut_nature'], ['Тихое', null],
  ])('groups the sugar %s', (value, key) => {
    expect(sugarKey(value)).toBe(key)
  })

  it('filters by words, color, and sugar', () => {
    const wine = { name: 'Абрау-Дюрсо Брют', producer: 'Абрау-Дюрсо', color: 'Белое', sugar: 'Брют' }
    expect(matchesFilter(SLUG, wine, { text: 'абрау брют', color: 'white', sugar: 'brut' })).toBe(true)
    expect(matchesFilter(SLUG, wine, { text: 'ёлка', color: '', sugar: '' })).toBe(false)
    expect(matchesFilter(SLUG, wine, { text: '', color: 'red', sugar: '' })).toBe(false)
    expect(matchesFilter(SLUG, null, { text: 'durso', color: '', sugar: '' })).toBe(true)
    expect(wineStyleLine(wine)).toBe('Белое · Брют')
  })
})
