import { describe, expect, it, vi } from 'vitest'
import { DINNER_CATEGORIES, DINNER_MAX_BODY_BYTES, DINNER_NODES, parseDinnerPage, validDinnerRequest } from '../shared/dinner'
import { dinnerConfigured, dinnerEndpoint, readDinnerBody, requestDinner } from '../server/utils/dinner'
import { dinnerPage, dinnerWine } from './support/dinner'
import type { H3Event } from 'h3'

const endpoint = 'http://127.0.0.1:28007'
const token = 'dinner-proxy-unit-test-token-placeholder'

describe('Dinner Lens request and response contracts', () => {
  it('exports all dishes and fallback labels without wine selection data', () => {
    expect(DINNER_NODES).toHaveLength(320)
    expect(DINNER_CATEGORIES).toHaveLength(16)
    expect(DINNER_NODES.filter(node => node.kind === 'dish')).toHaveLength(200)
    expect(DINNER_NODES.every(node => !('curated' in node))).toBe(true)
  })
  it('accepts confirmed names or exact nodes and explicit sauce/negation constraints', () => {
    expect(validDinnerRequest('recommendations', { node_id: 'ribeye_grilled', limit: 3,
      confirmed_attributes: { heat: 'high', fatty_cream_sauce: false }, user_constraints: { exclude_producer: 'Фанагория', wine_kind: 'still' } })).toBe(true)
    expect(validDinnerRequest('recommendations', { confirmed_dish: 'Оливье с докторской колбасой' })).toBe(true)
    expect(validDinnerRequest('recognize', { image_base64: 'data:image/jpeg;base64,YWJj', limit: 3 })).toBe(true)
  })
  it.each([
    { node_id: 'invented-node' }, { confirmed_dish: ' ' }, { node_id: 'ribeye_grilled', confirmed_dish: 'Steak' },
    { node_id: 'ribeye_grilled', user_constraints: { stock: true } }, { node_id: 'ribeye_grilled', limit: 10 },
    { node_id: 'ribeye_grilled', confirmed_attributes: { fatty_cream_sauce: 'false' } },
  ])('rejects unknown fields and invalid dish/constraint values: %j', body => {
    expect(validDinnerRequest('recommendations', body)).toBe(false)
  })
  it('does not accept remote photos or changed continuation filters', () => {
    expect(validDinnerRequest('recognize', { image_base64: 'https://example.com/food.jpg' })).toBe(false)
    expect(validDinnerRequest('more', { cursor: 'signed-cursor', user_constraints: { color: 'white' } })).toBe(false)
    expect(validDinnerRequest('more', { cursor: 'signed-cursor' })).toBe(true)
  })
  it('projects the result without provider/internal metadata', () => {
    const raw = { ...dinnerPage(), llm: { internal_endpoint: 'http://private.invalid' }, diagnostics: { query_text: 'Internal rule' } }
    expect(parseDinnerPage(raw)).toEqual(dinnerPage())
  })
  it.each(['javascript:alert(1)', 'https://evil.example/wines/dinner-fixture-1', 'https://vino-svoe.ru/wines/different-wine'])('rejects an unsafe or wrong wine link: %s', source_url => {
    expect(parseDinnerPage(dinnerPage({ results: [{ ...dinnerWine(1), source_url }] }))).toBeNull()
  })
  it('rejects repeated IDs and silently truncated continuation', () => {
    expect(parseDinnerPage(dinnerPage({ results: [dinnerWine(1), dinnerWine(1)] }))).toBeNull()
    expect(parseDinnerPage(dinnerPage({ next_cursor: null }))).toBeNull()
    expect(parseDinnerPage(dinnerPage({ total_eligible: 2 }))).toBeNull()
  })
  it('accepts unknown dishes and honest empty results', () => {
    expect(parseDinnerPage({ status: 'needs_category', resolved_node_id: null, results: [], needs_clarification: true, clarification_question: 'Выберите категорию блюда.' })?.status).toBe('needs_category')
    expect(parseDinnerPage(dinnerPage({ status: 'no_results', results: [], next_cursor: null, shown_count: 0, total_eligible: 0 }))?.status).toBe('no_results')
  })
})

describe('server-only Dinner Lens proxy', () => {
  it('routes only configured service actions and requires a private credential', () => {
    expect(dinnerEndpoint(endpoint, 'more').href).toBe(endpoint + '/v1/recommendations/more')
    expect(dinnerConfigured(endpoint, token)).toBe(true)
    for (const bad of ['file:///etc/passwd', 'http://user:password@localhost/', 'https://example.com/?target=x', 'https://example.com/v1']) expect(dinnerConfigured(bad, token)).toBe(false)
    expect(dinnerConfigured(endpoint, '')).toBe(false)
  })
  it('injects bearer auth on the server and forbids redirects', async () => {
    const request = vi.fn().mockResolvedValue(Response.json({ ...dinnerPage(), llm: { private: true } }))
    expect(await requestDinner('recommendations', { node_id: 'ribeye_grilled' }, endpoint, token, { fetch: request })).toEqual(dinnerPage())
    expect(request.mock.calls[0]![1]).toMatchObject({ redirect: 'error', headers: { Authorization: 'Bearer ' + token } })
  })
  it('rejects invalid input before spending a provider request', async () => {
    const request = vi.fn()
    await expect(requestDinner('recommendations', { node_id: 'invented' }, endpoint, token, { fetch: request })).rejects.toMatchObject({ statusCode: 422 })
    expect(request).not.toHaveBeenCalled()
  })
  it('rejects a different dish returned for an explicitly selected node', async () => {
    const request = vi.fn().mockResolvedValue(Response.json(dinnerPage({ resolved_node_id: 'king_crab_steamed_butter' })))
    await expect(requestDinner('recommendations', { node_id: 'ribeye_grilled' }, endpoint, token, { fetch: request })).rejects.toMatchObject({ statusCode: 502 })
  })
  it.each([401, 500, 422, 503])('preserves safe status handling for upstream %s without its body', async status => {
    const request = vi.fn().mockResolvedValue(new Response('private upstream detail', { status }))
    await expect(requestDinner('recommendations', { node_id: 'ribeye_grilled' }, endpoint, token, { fetch: request })).rejects.toMatchObject({ statusCode: [422, 503].includes(status) ? status : 502, statusMessage: 'Dinner Lens request failed' })
  })
  it('rejects oversized declared and streamed responses', async () => {
    for (const response of [new Response('{}', { headers: { 'content-length': '3000000' } }), new Response(' '.repeat(2 * 1024 * 1024 + 1))]) {
      await expect(requestDinner('more', { cursor: 'fixture' }, endpoint, token, { fetch: vi.fn().mockResolvedValue(response) })).rejects.toMatchObject({ statusCode: 502 })
    }
  })
  it('propagates cancellation and bounds total fetch time', async () => {
    const request = vi.fn((_url, options) => new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))))
    await expect(requestDinner('more', { cursor: 'fixture' }, endpoint, token, { fetch: request as typeof fetch, timeout: 5 })).rejects.toMatchObject({ statusCode: 504 })
  })
  it('bounds chunked body bytes and requires JSON before parsing', async () => {
    const event = (chunks: string[], headers: object = { 'content-type': 'application/json' }) => ({ node: { req: Object.assign((async function* () { yield* chunks })(), { headers }) } }) as unknown as H3Event
    expect(await readDinnerBody(event(['{"confirmed_dish":', '"Стейк"}']))).toEqual({ confirmed_dish: 'Стейк' })
    await expect(readDinnerBody(event([' '.repeat(DINNER_MAX_BODY_BYTES + 1)]))).rejects.toMatchObject({ statusCode: 413 })
    await expect(readDinnerBody(event(['not json']))).rejects.toMatchObject({ statusCode: 400 })
    await expect(readDinnerBody(event(['{}'], { 'content-type': 'text/plain' }))).rejects.toMatchObject({ statusCode: 415 })
  })
})
