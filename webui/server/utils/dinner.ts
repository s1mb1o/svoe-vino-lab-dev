import { Buffer } from 'node:buffer'
import { createError, type H3Event } from 'h3'
import { DINNER_MAX_BODY_BYTES, DINNER_TIMEOUT_MS, parseDinnerPage, validDinnerRequest, type DinnerAction } from '#shared/dinner'

const paths: Record<DinnerAction, string> = {
  recognize: '/v1/recognize-and-recommend', recommendations: '/v1/recommendations', more: '/v1/recommendations/more',
}
const MAX_RESPONSE_BYTES = 2 * 1024 * 1024
export function dinnerEndpoint(endpoint: unknown, action: DinnerAction): URL {
  try {
    if (typeof endpoint !== 'string' || !endpoint) throw new Error('URL')
    const base = new URL(endpoint)
    if (!['http:', 'https:'].includes(base.protocol) || base.username || base.password || base.search || base.hash || base.pathname !== '/') throw new Error('URL')
    return new URL(paths[action], base)
  } catch { throw createError({ statusCode: 503, statusMessage: 'Dinner Lens is not configured' }) }
}
export function dinnerConfigured(endpoint: unknown, token: unknown) {
  try { dinnerEndpoint(endpoint, 'recommendations'); return typeof token === 'string' && /^[A-Za-z0-9._~-]{24,}$/.test(token) }
  catch { return false }
}
export async function requestDinner(action: DinnerAction, body: unknown, endpoint: unknown, token: unknown,
  options: { fetch?: typeof fetch; signal?: AbortSignal; timeout?: number } = {}) {
  const url = dinnerEndpoint(endpoint, action)
  if (!dinnerConfigured(endpoint, token)) throw createError({ statusCode: 503, statusMessage: 'Dinner Lens is not configured' })
  if (!validDinnerRequest(action, body)) throw createError({ statusCode: 422, statusMessage: 'Invalid dish request' })
  const signal = AbortSignal.any([options.signal || new AbortController().signal, AbortSignal.timeout(options.timeout ?? DINNER_TIMEOUT_MS)])
  try {
    const response = await (options.fetch || fetch)(url, { method: 'POST', body: JSON.stringify(body), signal, redirect: 'error',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token } })
    if (!response.ok) {
      const status = [400, 408, 413, 415, 422, 429, 503, 504].includes(response.status) ? response.status : 502
      await response.body?.cancel().catch(() => {})
      throw createError({ statusCode: status, statusMessage: 'Dinner Lens request failed' })
    }
    const declared = Number(response.headers.get('content-length'))
    if (Number.isFinite(declared) && declared > MAX_RESPONSE_BYTES) { await response.body?.cancel(); throw new Error('Response bound') }
    const reader = response.body?.getReader()
    if (!reader) throw new Error('Missing response')
    const chunks: Uint8Array[] = []; let bytes = 0
    try {
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        bytes += value.length
        if (bytes > MAX_RESPONSE_BYTES) throw new Error('Response bound')
        chunks.push(value)
      }
    } finally { await reader.cancel().catch(() => {}) }
    const result = parseDinnerPage(JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks))))
    if (!result) throw new Error('Invalid response')
    if (action === 'recommendations' && typeof body.node_id === 'string' && result.resolved_node_id !== body.node_id) throw new Error('Dish identity mismatch')
    return result
  } catch (failure) {
    if (signal.aborted) throw createError({ statusCode: 504, statusMessage: 'Dinner Lens request timed out' })
    if (failure && typeof failure === 'object' && 'statusCode' in failure) throw failure
    throw createError({ statusCode: 502, statusMessage: 'Dinner Lens response is unavailable' })
  }
}

export async function readDinnerBody(event: H3Event) {
  if (!/^application\/json(?:\s*;|$)/i.test(event.node.req.headers['content-type'] || '')) throw createError({ statusCode: 415, statusMessage: 'Dish requests require JSON' })
  const declared = Number(event.node.req.headers['content-length'])
  if (Number.isFinite(declared) && declared > DINNER_MAX_BODY_BYTES) throw createError({ statusCode: 413, statusMessage: 'Dish request is too large' })
  const chunks: Buffer[] = []; let bytes = 0
  for await (const chunk of event.node.req) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)
    bytes += buffer.length
    if (bytes > DINNER_MAX_BODY_BYTES) throw createError({ statusCode: 413, statusMessage: 'Dish request is too large' })
    chunks.push(buffer)
  }
  try { return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks))) as unknown }
  catch { throw createError({ statusCode: 400, statusMessage: 'Invalid dish JSON' }) }
}

export async function handleDinner(event: H3Event, action: DinnerAction) {
  setHeader(event, 'Cache-Control', 'no-store')
  const config = useRuntimeConfig(event)
  const controller = new AbortController()
  const disconnect = () => { if (!event.node.res.writableEnded) controller.abort() }
  event.node.res.once('close', disconnect)
  try {
    if (!dinnerConfigured(config.dinnerLensEndpoint, config.dinnerLensApiToken)) throw createError({ statusCode: 503, statusMessage: 'Dinner Lens is not configured' })
    return await requestDinner(action, await readDinnerBody(event), config.dinnerLensEndpoint, config.dinnerLensApiToken, { signal: controller.signal })
  } finally { event.node.res.off('close', disconnect) }
}
