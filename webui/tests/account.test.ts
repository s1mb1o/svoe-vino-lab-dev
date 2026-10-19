import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest'
import { createServer, type IncomingMessage, type Server } from 'node:http'
import { createApp, createRouter, eventHandler, toNodeListener } from 'h3'
import {
  accountConfig, accountConfigRoute, callAccount, deleteMeRoute, emailStartRoute, emailVerifyRoute, logoutRoute,
  maxHostDecision, maxLinkRoute, maxQrRoute, meRoute, signupRoute, telegramLinkRoute, unlinkMessengerRoute,
  yandexCallbackRoute, yandexStartRoute, type AccountConfigSource,
} from '../server/utils/account'
import { accountErrorMessage, isAccountPath, isMaxAppPath, safeNextPath, splitIdentities } from '../shared/account'
import { METRIKA_INIT_SCRIPT } from '../shared/metrika'

const TOKEN = 'w'.repeat(64)
type Seen = { method: string; url: string; headers: IncomingMessage['headers']; body: string }
let seen: Seen[] = []
let reply: (request: Seen) => { status: number; body?: unknown; headers?: Record<string, string>; hang?: boolean; delayMs?: number } = () => ({ status: 200, body: {} })
let service: Server
let site: Server
let serviceUrl = ''
let siteUrl = ''
let source: AccountConfigSource
let baseSource: AccountConfigSource
const MAX_APP_LINK = 'https://max.ru/se14697933_bot?startapp=account'

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
      if (answer.hang) return
      const send = () => {
        res.writeHead(answer.status, { 'Content-Type': 'application/json', ...(answer.headers ?? {}) })
        res.end(answer.body === undefined ? '' : JSON.stringify(answer.body))
      }
      if (answer.delayMs) setTimeout(send, answer.delayMs)
      else send()
    })
  })
  serviceUrl = await listen(service)
  baseSource = () => accountConfig({ endpoint: serviceUrl, token: TOKEN, publicOrigin: 'https://chtozavino.ru' }, { timeoutMs: 300 })
  source = baseSource
  const app = createApp()
  const routes: Record<string, (event: Parameters<typeof meRoute>[0], source: AccountConfigSource) => unknown> = {
    '/api/account/config': accountConfigRoute,
    '/api/account/me': meRoute,
    '/api/account/delete': deleteMeRoute,
    '/api/account/logout': logoutRoute,
    '/api/account/email/start': emailStartRoute,
    '/api/account/email/verify': emailVerifyRoute,
    '/api/account/signup': signupRoute,
    '/api/account/yandex/start': yandexStartRoute,
    '/api/account/yandex/callback': yandexCallbackRoute,
    '/api/account/links/telegram': telegramLinkRoute,
    '/api/account/identities/telegram': (event, config) => unlinkMessengerRoute(event, config, 'telegram'),
    '/api/account/identities/email': (event, config) => unlinkMessengerRoute(event, config, 'email'),
    '/api/account/identities/max': (event, config) => unlinkMessengerRoute(event, config, 'max'),
    '/api/account/max/link': maxLinkRoute,
    '/api/account/max/qr.svg': maxQrRoute,
  }
  const router = createRouter()
  // `source` is read at request time, so a test can switch the settings.
  for (const [path, route] of Object.entries(routes)) router.use(path, eventHandler(event => route(event, () => source())))
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
  reply = () => ({ status: 200, body: {} })
  source = baseSource
})
const withMaxLink = () => {
  source = () => accountConfig({ endpoint: serviceUrl, token: TOKEN, publicOrigin: 'https://chtozavino.ru', maxAppLink: MAX_APP_LINK }, { timeoutMs: 300 })
}

function call(path: string, init: RequestInit & { cookie?: string } = {}) {
  const headers = new Headers(init.headers)
  if (init.cookie) headers.set('cookie', init.cookie)
  if (init.method && init.method !== 'GET' && !headers.has('origin')) headers.set('origin', 'https://chtozavino.ru')
  return fetch(`${siteUrl}${path}`, { ...init, headers, redirect: 'manual' })
}
const json = (body: unknown) => ({ body: JSON.stringify(body), headers: { 'content-type': 'application/json' } })
const cookies = (response: Response) => response.headers.getSetCookie()

describe('shared account rules', () => {
  it.each([
    ['/shelf', '/shelf'], ['/account?x=1', '/account?x=1'], ['//evil.example', '/account'], ['/\\evil', '/account'],
    ['https://evil.example', '/account'], ['/api/account/me', '/account'], ['/v1/match', '/account'], [undefined, '/account'],
    ['/a\nb', '/account'],
  ])('keeps only same-site paths after login: %s', (value, expected) => {
    expect(safeNextPath(value)).toBe(expected)
  })
  it('marks the account pages for Metrika and the page cache', () => {
    expect(isAccountPath('/account')).toBe(true)
    expect(isAccountPath('/account/onboarding')).toBe(true)
    expect(isAccountPath('/max')).toBe(true)
    expect(isAccountPath('/accounting')).toBe(false)
    expect(isAccountPath('/maxim')).toBe(false)
    expect(isMaxAppPath('/max')).toBe(true)
    expect(isMaxAppPath('/account')).toBe(false)
  })
  it('lists only email and Yandex ID as login methods', () => {
    const { login, linked } = splitIdentities([
      { provider: 'yandex' }, { provider: 'email', email: 'a@example.com' }, { provider: 'telegram' }, { provider: 'max' },
    ])
    expect(login.map(item => item.key)).toEqual(['yandex', 'email'])
    expect(linked.map(item => item.label)).toEqual(['Telegram', 'MAX'])
  })
  it('explains errors in Russian without the input', () => {
    expect(accountErrorMessage({ error: 'invalid_code', attemptsLeft: 2 })).toBe('Неверный код. Осталось попыток: 2.')
    expect(accountErrorMessage({ error: 'rate_limited', retryAfter: 61 })).toContain('2 мин')
    expect(accountErrorMessage({ error: 'unknown_thing' })).toBe('Что-то пошло не так. Попробуйте ещё раз.')
  })
})

describe('Metrika on account pages', () => {
  function runInit(pathname: string) {
    const inserted: unknown[] = []
    const scope: Record<string, unknown> = {
      location: { pathname, href: `https://chtozavino.ru${pathname}` },
      document: {
        scripts: [],
        referrer: '',
        createElement: () => ({}),
        getElementsByTagName: () => [{ parentNode: { insertBefore: (node: unknown) => inserted.push(node) } }],
      },
    }
    scope.window = scope
    // The init script runs as a classic script, where window properties are globals.
    new Function('scope', `with (scope) {${METRIKA_INIT_SCRIPT}}`)(scope)
    return { ym: scope.ym as { a?: unknown[][] } | undefined, inserted }
  }
  it('parses as JavaScript', () => {
    expect(() => new Function(METRIKA_INIT_SCRIPT)).not.toThrow()
  })
  it.each(['/', '/shelf', '/accounting'])('starts Metrika on %s', pathname => {
    const { ym, inserted } = runInit(pathname)
    expect(typeof ym).toBe('function')
    expect(ym?.a?.[0]?.[1]).toBe('init')
    expect(inserted).toHaveLength(1)
  })
  it.each(['/account', '/account/onboarding', '/max'])('does not start Metrika on %s', pathname => {
    const { ym, inserted } = runInit(pathname)
    expect(ym).toBeUndefined()
    expect(inserted).toHaveLength(0)
  })
})

describe('account configuration', () => {
  it('turns the feature off with an empty endpoint', async () => {
    expect(accountConfig({ endpoint: '' })).toBeNull()
    const off = await accountConfigRoute({ node: { req: {}, res: { setHeader() {} } } } as never, () => null)
    expect(off).toEqual({ enabled: false, available: false })
  })
  it.each([
    [{ endpoint: 'ftp://host/', token: TOKEN }],
    [{ endpoint: 'http://user:pw@host/', token: TOKEN }],
    [{ endpoint: 'http://host/?a=1', token: TOKEN }],
    [{ endpoint: 'http://host/', token: 'short' }],
  ])('refuses an unsafe setting: %o', settings => {
    expect(() => accountConfig(settings)).toThrow('account_unavailable')
  })
  it('reports the enabled providers and versions', async () => {
    reply = () => ({ status: 200, body: { providers: { email: true, yandex: true, max_login: true, telegram_link: true }, consent_version: 'c1', terms_version: 't1' } })
    const response = await call('/api/account/config')
    expect(response.headers.get('cache-control')).toBe('no-store')
    expect(await response.json()).toEqual({ enabled: true, available: true, providers: { email: true, yandex: true, telegram: true, max: false }, consentVersion: 'c1', termsVersion: 't1' })
    expect(seen[0].headers.authorization).toBe(`Bearer ${TOKEN}`)
  })
  it('reports an unavailable service instead of failing the page', async () => {
    reply = () => ({ status: 500, body: {} })
    expect(await (await call('/api/account/config')).json()).toEqual({ enabled: true, available: false })
  })
})

describe('calls to the account service', () => {
  const config = () => source()!
  it('passes a refusal through with its code, attempts and Retry-After', async () => {
    reply = () => ({ status: 429, body: { error: 'rate_limited', detail: 'x' }, headers: { 'Retry-After': '120' } })
    await expect(callAccount(config(), 'GET', '/v1/config')).rejects.toMatchObject({ status: 429, code: 'rate_limited', extra: { retryAfter: 120 } })
  })
  it.each([
    ['a server error', () => ({ status: 503, body: { error: 'busy' } })],
    ['a refused service token', () => ({ status: 401, body: { error: 'unauthorized' } })],
    ['a refused network', () => ({ status: 403, body: { error: 'forbidden' } })],
    ['a redirect', () => ({ status: 302, headers: { location: '/elsewhere' } })],
    ['a timeout', () => ({ status: 200, hang: true })],
  ])('maps %s to account_unavailable', async (_name, answer) => {
    reply = answer as typeof reply
    await expect(callAccount(config(), 'GET', '/v1/config')).rejects.toMatchObject({ status: 503, code: 'account_unavailable' })
  })
  it('does not accept a large answer', async () => {
    reply = () => ({ status: 200, body: { pad: 'x'.repeat(70 * 1024) } })
    await expect(callAccount(config(), 'GET', '/v1/config')).rejects.toMatchObject({ code: 'account_unavailable' })
  })
})

describe('email login', () => {
  it('keeps the challenge in a strict httpOnly cookie and sends the client address', async () => {
    reply = () => ({ status: 200, body: { challenge_id: 'c'.repeat(32), expires_in: 600 } })
    const response = await call('/api/account/email/start', { method: 'POST', ...json({ email: 'a@example.com' }), headers: { ...json({}).headers, 'x-forwarded-for': '203.0.113.9, 198.51.100.7' } })
    expect(response.status).toBe(200)
    expect(await response.json()).toEqual({ expiresIn: 600 })
    const cookie = cookies(response).find(item => item.startsWith('__Host-cv_email='))!
    expect(cookie).toMatch(/HttpOnly/i)
    expect(cookie).toMatch(/Secure/i)
    expect(cookie).toMatch(/SameSite=Strict/i)
    expect(cookie).toMatch(/Path=\//)
    expect(JSON.parse(seen[0].body)).toEqual({ email: 'a@example.com', purpose: 'login' })
    expect(seen[0].headers['x-client-ip']).toBe('198.51.100.7')
  })
  it.each([
    ['no Origin', {}],
    ['a foreign Origin', { origin: 'https://evil.example' }],
  ])('refuses a state change with %s', async (_name, headers) => {
    const response = await fetch(`${siteUrl}/api/account/email/start`, { method: 'POST', body: '{"email":"a@example.com"}', headers: { 'content-type': 'application/json', ...headers } })
    expect(response.status).toBe(403)
    expect(await response.json()).toEqual({ error: 'origin_rejected' })
    expect(seen).toHaveLength(0)
  })
  it('sets the session cookie after a correct code and keeps the token away from the browser', async () => {
    reply = () => ({ status: 200, body: { status: 'session', session: { token: 's'.repeat(43), expires_at: new Date(Date.now() + 86400e3).toISOString(), auth_method: 'email' }, user: { id: 'u', username: 'anna', identities: [] } } })
    const response = await call('/api/account/email/verify', { method: 'POST', ...json({ code: '123456' }), cookie: `__Host-cv_email=${'c'.repeat(32)}` })
    const body = await response.json()
    expect(body).toEqual({ status: 'session', user: { id: 'u', username: 'anna', identities: [] } })
    expect(JSON.stringify(body)).not.toContain('s'.repeat(43))
    const session = cookies(response).find(item => item.startsWith('__Host-cv_session='))!
    expect(session).toMatch(/HttpOnly/i)
    expect(session).toMatch(/SameSite=Lax/i)
    expect(cookies(response).some(item => item.startsWith('__Host-cv_email=;'))).toBe(true)
    expect(JSON.parse(seen[0].body)).toEqual({ challenge_id: 'c'.repeat(32), code: '123456' })
  })
  it('passes a wrong code with the attempts left and keeps the challenge', async () => {
    reply = () => ({ status: 400, body: { error: 'invalid_code', attempts_left: 3 } })
    const response = await call('/api/account/email/verify', { method: 'POST', ...json({ code: '000000' }), cookie: `__Host-cv_email=${'c'.repeat(32)}` })
    expect(response.status).toBe(400)
    expect(await response.json()).toEqual({ error: 'invalid_code', attemptsLeft: 3 })
    expect(cookies(response).some(item => item.startsWith('__Host-cv_email='))).toBe(false)
  })
  it('keeps a new identity in a sign-up cookie', async () => {
    reply = () => ({ status: 200, body: { status: 'signup_required', signup_ticket: 't'.repeat(32), provider: 'email', email: 'a@example.com' } })
    const response = await call('/api/account/email/verify', { method: 'POST', ...json({ code: '123456' }), cookie: `__Host-cv_email=${'c'.repeat(32)}` })
    expect(await response.json()).toEqual({ status: 'signup_required', provider: 'email', email: 'a@example.com' })
    expect(cookies(response).find(item => item.startsWith('__Host-cv_signup='))).toMatch(/HttpOnly/i)
  })
})

describe('request bodies', () => {
  it('stops a chunked body above 4 KiB before the service', async () => {
    const chunk = new TextEncoder().encode('x'.repeat(1024))
    let sent = 0
    const body = new ReadableStream<Uint8Array>({
      pull(controller) {
        if (sent++ < 64) controller.enqueue(chunk)
        else controller.close()
      },
    })
    const outcome = await fetch(`${siteUrl}/api/account/email/start`, {
      method: 'POST', body, duplex: 'half', headers: { 'content-type': 'application/json', origin: 'https://chtozavino.ru' },
    } as RequestInit).then(response => response.status, () => 'connection closed')
    expect([413, 'connection closed']).toContain(outcome)
    expect(seen).toHaveLength(0)
  })
})

describe('sign-up', () => {
  const valid = { username: 'anna_wine', acceptTerms: true, acceptConsent: true, consentVersion: 'c1', termsVersion: 't1' }
  it.each([
    [{ ...valid, acceptTerms: false }, 'consent_required'],
    [{ ...valid, acceptConsent: 'yes' }, 'consent_required'],
    [{ ...valid, username: 'Anna' }, 'invalid_username'],
  ])('checks the input before the service: %o', async (input, error) => {
    const response = await call('/api/account/signup', { method: 'POST', ...json(input), cookie: `__Host-cv_signup=${'t'.repeat(32)}` })
    expect(response.status).toBe(400)
    expect(await response.json()).toEqual({ error })
    expect(seen).toHaveLength(0)
  })
  it('creates the account with the ticket from the cookie', async () => {
    reply = () => ({ status: 200, body: { status: 'session', session: { token: 's'.repeat(43), expires_at: new Date(Date.now() + 86400e3).toISOString() }, user: { id: 'u', username: 'anna_wine', identities: [] } } })
    const response = await call('/api/account/signup', { method: 'POST', ...json(valid), cookie: `__Host-cv_signup=${'t'.repeat(32)}` })
    expect(response.status).toBe(200)
    expect(JSON.parse(seen[0].body)).toEqual({ signup_ticket: 't'.repeat(32), username: 'anna_wine', consent_version: 'c1', terms_version: 't1' })
    expect(cookies(response).some(item => item.startsWith('__Host-cv_session='))).toBe(true)
  })
})

describe('session routes', () => {
  it('asks for login without a cookie and does not call the service', async () => {
    const response = await call('/api/account/me')
    expect(response.status).toBe(401)
    expect(await response.json()).toEqual({ error: 'session_required' })
    expect(seen).toHaveLength(0)
  })
  it('removes a session cookie that the service no longer accepts', async () => {
    reply = () => ({ status: 401, body: { error: 'session_invalid' } })
    const response = await call('/api/account/me', { cookie: '__Host-cv_session=old' })
    expect(response.status).toBe(401)
    expect(cookies(response).some(item => item.startsWith('__Host-cv_session=;'))).toBe(true)
    expect(seen[0].headers['x-session-token']).toBe('old')
  })
  it('logs out even when the service is down', async () => {
    reply = () => ({ status: 503, body: {} })
    const response = await call('/api/account/logout', { method: 'POST', ...json({}), cookie: '__Host-cv_session=abc' })
    expect(response.status).toBe(200)
    expect(cookies(response).some(item => item.startsWith('__Host-cv_session=;'))).toBe(true)
  })
  it('passes reauth_required for account deletion', async () => {
    reply = () => ({ status: 403, body: { error: 'reauth_required' } })
    const response = await call('/api/account/delete', { method: 'DELETE', cookie: '__Host-cv_session=abc' })
    expect(response.status).toBe(403)
    expect(await response.json()).toEqual({ error: 'reauth_required' })
  })
})

describe('Telegram link', () => {
  const deepLink = `https://t.me/ChtoZaVinoBot?start=link_${'a'.repeat(22)}`
  it('returns only the bot deep link for a session', async () => {
    reply = () => ({ status: 200, body: { code: 'a'.repeat(22), deep_link: deepLink, expires_in: 600 } })
    const response = await call('/api/account/links/telegram', { method: 'POST', ...json({}), cookie: '__Host-cv_session=abc' })
    expect(response.status).toBe(200)
    expect(response.headers.get('cache-control')).toBe('no-store')
    expect(await response.json()).toEqual({ deepLink, expiresIn: 600 })
    expect(seen[0]).toMatchObject({ method: 'POST', url: '/v1/me/links/telegram' })
    expect(seen[0].headers['x-session-token']).toBe('abc')
  })
  it('needs a session and the site origin', async () => {
    expect((await call('/api/account/links/telegram', { method: 'POST', ...json({}) })).status).toBe(401)
    const foreign = await call('/api/account/links/telegram', { method: 'POST', ...json({}), cookie: '__Host-cv_session=abc', headers: { origin: 'https://evil.example' } })
    expect(foreign.status).toBe(403)
    expect(seen).toHaveLength(0)
  })
  it.each([
    'https://evil.example/ChtoZaVinoBot?start=link_aaaaaaaaaaaaaaaaaaaaaa',
    'http://t.me/ChtoZaVinoBot?start=link_aaaaaaaaaaaaaaaaaaaaaa',
    'https://t.me/ChtoZaVinoBot?start=privacy',
    'javascript:alert(1)',
  ])('refuses an unexpected deep link: %s', async link => {
    reply = () => ({ status: 200, body: { deep_link: link, expires_in: 600 } })
    const response = await call('/api/account/links/telegram', { method: 'POST', ...json({}), cookie: '__Host-cv_session=abc' })
    expect(response.status).toBe(503)
  })
  it('passes provider_already_linked', async () => {
    reply = () => ({ status: 409, body: { error: 'provider_already_linked' } })
    const response = await call('/api/account/links/telegram', { method: 'POST', ...json({}), cookie: '__Host-cv_session=abc' })
    expect(response.status).toBe(409)
    expect(await response.json()).toEqual({ error: 'provider_already_linked' })
  })
  it('unlinks Telegram and treats a missing link as done', async () => {
    reply = () => ({ status: 204 })
    const first = await call('/api/account/identities/telegram', { method: 'DELETE', cookie: '__Host-cv_session=abc' })
    expect(await first.json()).toEqual({ status: 'unlinked' })
    expect(seen[0]).toMatchObject({ method: 'DELETE', url: '/v1/me/identities/telegram' })
    reply = () => ({ status: 404, body: { error: 'not_linked' } })
    const second = await call('/api/account/identities/telegram', { method: 'DELETE', cookie: '__Host-cv_session=abc' })
    expect(second.status).toBe(200)
  })
  it('does not unlink a login method', async () => {
    const response = await call('/api/account/identities/email', { method: 'DELETE', cookie: '__Host-cv_session=abc' })
    expect(response.status).toBe(404)
    expect(seen).toHaveLength(0)
  })
})

describe('MAX link', () => {
  const initData = `auth_date=1&query_id=q&user=${encodeURIComponent('{"id":7}')}&hash=${'a'.repeat(64)}`
  it('reports MAX only with the service flag and the site link', async () => {
    reply = () => ({ status: 200, body: { providers: { email: true, max_link: true } } })
    expect((await (await call('/api/account/config')).json()).providers.max).toBe(false)
    withMaxLink()
    const body = await (await call('/api/account/config')).json()
    expect(body.providers.max).toBe(true)
    expect(body.maxAppLink).toBe(MAX_APP_LINK)
    reply = () => ({ status: 200, body: { providers: { email: true, max_link: false } } })
    const off = await (await call('/api/account/config')).json()
    expect(off.providers.max).toBe(false)
    expect(off.maxAppLink).toBeUndefined()
  })
  it.each(['https://evil.example/bot?startapp=account', 'https://max.ru/bot?startapp=link_abc', 'javascript:alert(1)'])('ignores an unsafe mini-app link: %s', link => {
    expect(accountConfig({ endpoint: 'http://host/', token: TOKEN, maxAppLink: link })?.maxAppLink).toBe('')
  })
  it('sends the launch data with the session and the client address', async () => {
    reply = () => ({ status: 200, body: { status: 'linked' } })
    const response = await call('/api/account/max/link', { method: 'POST', ...json({ initData }), cookie: '__Host-cv_session=abc' })
    expect(await response.json()).toEqual({ status: 'linked' })
    expect(seen[0]).toMatchObject({ method: 'POST', url: '/v1/me/identities/max' })
    expect(JSON.parse(seen[0].body)).toEqual({ init_data: initData })
    expect(seen[0].headers['x-session-token']).toBe('abc')
    expect(seen[0].headers['x-client-ip']).toBe('127.0.0.1')
  })
  it('needs a session, the site origin, and launch data', async () => {
    expect((await call('/api/account/max/link', { method: 'POST', ...json({ initData }) })).status).toBe(401)
    expect((await call('/api/account/max/link', { method: 'POST', ...json({ initData }), cookie: '__Host-cv_session=abc', headers: { origin: 'https://evil.example' } })).status).toBe(403)
    const empty = await call('/api/account/max/link', { method: 'POST', ...json({}), cookie: '__Host-cv_session=abc' })
    expect(await empty.json()).toEqual({ error: 'invalid_launch' })
    expect(seen).toHaveLength(0)
  })
  it('accepts long launch data and stops a larger body', async () => {
    reply = () => ({ status: 200, body: { status: 'linked' } })
    const long = await call('/api/account/max/link', { method: 'POST', ...json({ initData: 'a'.repeat(8000) }), cookie: '__Host-cv_session=abc' })
    expect(long.status).toBe(200)
    const huge = await call('/api/account/max/link', { method: 'POST', ...json({ initData: 'a'.repeat(10_000) }), cookie: '__Host-cv_session=abc' })
    expect(huge.status).toBe(413)
  })
  it.each([[400, 'launch_expired'], [403, 'reauth_required'], [409, 'identity_in_use']])('passes the refusal %s %s', async (status, error) => {
    reply = () => ({ status, body: { error } })
    const response = await call('/api/account/max/link', { method: 'POST', ...json({ initData }), cookie: '__Host-cv_session=abc' })
    expect(response.status).toBe(status)
    expect(await response.json()).toEqual({ error })
  })
  it('serves the QR code of the fixed link only when it is set', async () => {
    expect((await call('/api/account/max/qr.svg')).status).toBe(404)
    withMaxLink()
    const response = await call('/api/account/max/qr.svg')
    expect(response.headers.get('content-type')).toContain('image/svg+xml')
    expect(await response.text()).toMatch(/^<svg/)
    expect(seen).toHaveLength(0)
  })
  it('unlinks MAX', async () => {
    reply = () => ({ status: 204 })
    const response = await call('/api/account/identities/max', { method: 'DELETE', cookie: '__Host-cv_session=abc' })
    expect(await response.json()).toEqual({ status: 'unlinked' })
    expect(seen[0]).toMatchObject({ method: 'DELETE', url: '/v1/me/identities/max' })
  })
  it('explains a stale MAX launch', () => {
    for (const error of ['launch_expired', 'launch_reused', 'launch_ip_mismatch', 'invalid_launch']) {
      expect(accountErrorMessage({ error })).toContain('откройте его в MAX снова')
    }
  })
})

describe('MAX mini-app host', () => {
  it.each([
    ['GET', '/', 'redirect'],
    ['GET', '/max', 'allow'],
    ['GET', '/_nuxt/entry.js', 'allow'],
    ['GET', '/reference/logo.svg', 'allow'],
    ['GET', '/privacy', 'allow'],
    ['GET', '/api/account/config', 'allow'],
    ['GET', '/api/account/max/qr.svg', 'allow'],
    ['POST', '/api/account/email/start', 'allow'],
    ['POST', '/api/account/max/link', 'allow'],
    ['DELETE', '/api/account/me', 'allow'],
    ['DELETE', '/api/account/identities/max', 'allow'],
    ['GET', '/api/account/yandex/start', 'reject'],
    ['POST', '/api/account/links/telegram', 'reject'],
    ['DELETE', '/api/account/identities/telegram', 'reject'],
    ['GET', '/account', 'reject'],
    ['GET', '/shelf', 'reject'],
    ['GET', '/sw.js', 'reject'],
    ['GET', '/manifest.webmanifest', 'reject'],
    ['POST', '/v1/match', 'reject'],
    ['POST', '/max', 'reject'],
    ['GET', '/max/../account', 'reject'],
  ])('%s %s: %s', (method, path, decision) => {
    expect(maxHostDecision(method, path)).toBe(decision)
  })
})

describe('Yandex ID', () => {
  it('redirects to oauth.yandex.ru with the fixed callback and keeps the flow in a Lax cookie', async () => {
    reply = () => ({ status: 200, body: { authorize_url: 'https://oauth.yandex.ru/authorize?client_id=x&state=s', flow_id: 'f'.repeat(32), expires_in: 600 } })
    const response = await call('/api/account/yandex/start?next=%2Fshelf')
    expect(response.status).toBe(302)
    expect(response.headers.get('location')).toBe('https://oauth.yandex.ru/authorize?client_id=x&state=s')
    expect(JSON.parse(seen[0].body)).toEqual({ redirect_uri: 'https://chtozavino.ru/api/account/yandex/callback', purpose: 'login' })
    expect(cookies(response).find(item => item.startsWith('__Host-cv_yandex='))).toMatch(/SameSite=Lax/i)
    expect(cookies(response).find(item => item.startsWith('__Host-cv_next='))).toContain('%2Fshelf')
  })
  it('refuses an authorize URL outside oauth.yandex.ru', async () => {
    reply = () => ({ status: 200, body: { authorize_url: 'https://evil.example/authorize', flow_id: 'f'.repeat(32), expires_in: 600 } })
    const response = await call('/api/account/yandex/start')
    expect(response.headers.get('location')).toBe('/account?error=account_unavailable')
  })
  it('finishes the flow with a redirect and no page', async () => {
    reply = () => ({ status: 200, body: { status: 'session', session: { token: 's'.repeat(43), expires_at: new Date(Date.now() + 86400e3).toISOString() }, user: { id: 'u' } } })
    const response = await call('/api/account/yandex/callback?code=CODE123&state=STATE', { cookie: `__Host-cv_yandex=${'f'.repeat(32)}; __Host-cv_next=%2Fshelf` })
    expect(response.status).toBe(302)
    expect(response.headers.get('location')).toBe('/shelf')
    expect(response.headers.get('referrer-policy')).toBe('no-referrer')
    expect(await response.text()).not.toContain('CODE123')
    expect(JSON.parse(seen[0].body)).toEqual({ flow_id: 'f'.repeat(32), state: 'STATE', code: 'CODE123' })
  })
  it.each([
    ['a cancelled consent', '?error=access_denied', `__Host-cv_yandex=${'f'.repeat(32)}`, '/account?error=yandex_cancelled'],
    ['a missing flow cookie', '?code=c&state=s', '', '/account?error=invalid_flow'],
  ])('returns to the login page after %s', async (_name, query, cookie, location) => {
    const response = await call(`/api/account/yandex/callback${query}`, { cookie })
    expect(response.headers.get('location')).toBe(location)
    expect(seen).toHaveLength(0)
  })
  it('waits for a slow Yandex finish longer than the general timeout', async () => {
    reply = () => ({ status: 200, delayMs: 600, body: { status: 'session', session: { token: 's'.repeat(43), expires_at: new Date(Date.now() + 86400e3).toISOString() }, user: { id: 'u' } } })
    const response = await call('/api/account/yandex/callback?code=c&state=s', { cookie: `__Host-cv_yandex=${'f'.repeat(32)}` })
    expect(response.headers.get('location')).toBe('/account')
  })
  describe('reauth before account deletion', () => {
    const flow = `__Host-cv_yandex=${'f'.repeat(32)}; __Host-cv_next=%2Faccount%3Fconfirm%3Ddelete; __Host-cv_reauth=1`
    const session = (id: string, token: string) => ({ status: 'session', session: { token, expires_at: new Date(Date.now() + 86400e3).toISOString() }, user: { id } })
    const serviceFor = (finish: unknown, me: { status: number; body: unknown } = { status: 200, body: { user: { id: 'A' } } }) => (request: Seen) => {
      if (request.url === '/v1/me') return me
      if (request.url === '/v1/auth/yandex/finish') return { status: 200, body: finish }
      if (request.url === '/v1/sessions/current') return { status: 204 }
      return { status: 404, body: { error: 'not_found' } }
    }
    it('marks the flow as a reauth', async () => {
      reply = () => ({ status: 200, body: { authorize_url: 'https://oauth.yandex.ru/authorize?x=1', flow_id: 'f'.repeat(32), expires_in: 600 } })
      const response = await call('/api/account/yandex/start?intent=reauth&next=%2Faccount%3Fconfirm%3Ddelete')
      expect(cookies(response).find(item => item.startsWith('__Host-cv_reauth=1'))).toMatch(/HttpOnly/i)
    })
    it('accepts the same account and returns to the confirmation', async () => {
      reply = serviceFor(session('A', 'new-a'))
      const response = await call('/api/account/yandex/callback?code=c&state=s', { cookie: `${flow}; __Host-cv_session=old-a` })
      expect(response.headers.get('location')).toBe('/account?confirm=delete')
      expect(cookies(response).some(item => item.startsWith('__Host-cv_session=new-a'))).toBe(true)
      expect(seen.find(item => item.url === '/v1/me')?.headers['x-session-token']).toBe('old-a')
    })
    it('refuses another account, keeps the current session, and ends the new one', async () => {
      reply = serviceFor(session('B', 'new-b'))
      const response = await call('/api/account/yandex/callback?code=c&state=s', { cookie: `${flow}; __Host-cv_session=old-a` })
      expect(response.headers.get('location')).toBe('/account?error=reauth_mismatch')
      expect(cookies(response).some(item => item.startsWith('__Host-cv_session='))).toBe(false)
      const revoke = seen.find(item => item.method === 'DELETE' && item.url === '/v1/sessions/current')
      expect(revoke?.headers['x-session-token']).toBe('new-b')
    })
    it('refuses a Yandex account without a diary', async () => {
      reply = serviceFor({ status: 'signup_required', signup_ticket: 't'.repeat(32), provider: 'yandex' })
      const response = await call('/api/account/yandex/callback?code=c&state=s', { cookie: `${flow}; __Host-cv_session=old-a` })
      expect(response.headers.get('location')).toBe('/account?error=reauth_mismatch')
      expect(cookies(response).some(item => item.startsWith('__Host-cv_signup='))).toBe(false)
    })
    it.each([
      ['no current session', '', { status: 200, body: { user: { id: 'A' } } }, '/account?error=session_required'],
      ['an expired current session', '; __Host-cv_session=old-a', { status: 401, body: { error: 'session_invalid' } }, '/account?error=session_invalid'],
    ])('never reaches the confirmation with %s', async (_name, extra, me, location) => {
      reply = serviceFor(session('B', 'new-b'), me)
      const response = await call('/api/account/yandex/callback?code=c&state=s', { cookie: `${flow}${extra}` })
      expect(response.headers.get('location')).toBe(location)
      expect(seen.some(item => item.url === '/v1/auth/yandex/finish')).toBe(false)
    })
  })
  it('sends a new identity to the sign-up step', async () => {
    reply = () => ({ status: 200, body: { status: 'signup_required', signup_ticket: 't'.repeat(32), provider: 'yandex' } })
    const response = await call('/api/account/yandex/callback?code=c&state=s', { cookie: `__Host-cv_yandex=${'f'.repeat(32)}` })
    expect(response.headers.get('location')).toBe('/account?step=signup')
  })
})
