import { Buffer } from 'node:buffer'
import { createError } from 'h3'
import { SHELF_TIMEOUT_MS, validShelfResult, type ShelfResult } from '#shared/shelf'

const MAX_GROUP_RESPONSE_BYTES = 12 * 1024 * 1024
const PREDICTION_PATH = /\/v1\/eval\/predict\/?$/

export function groupMatchUrl(predictionEndpoint: unknown): URL {
  try {
    if (typeof predictionEndpoint !== 'string' || !predictionEndpoint) throw new Error('URL')
    const url = new URL(predictionEndpoint)
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash || !PREDICTION_PATH.test(url.pathname)) throw new Error('URL')
    url.pathname = url.pathname.replace(PREDICTION_PATH, '/v1/group/match')
    return url
  } catch {
    throw createError({ statusCode: 503, statusMessage: 'Group matching endpoint is not configured correctly' })
  }
}

export function hasGroupMatchEndpoint(predictionEndpoint: unknown): boolean {
  try { groupMatchUrl(predictionEndpoint); return true }
  catch { return false }
}

function upstreamError(status = 502) {
  const allowed = [400, 401, 408, 413, 415, 502, 503, 504]
  return createError({ statusCode: allowed.includes(status) ? status : 502, statusMessage: 'Group matching service failed' })
}

export async function matchGroup(file: File, predictionEndpoint: unknown, options: { fetch?: typeof fetch; signal?: AbortSignal; timeout?: number } = {}): Promise<ShelfResult> {
  const url = groupMatchUrl(predictionEndpoint)
  const signal = AbortSignal.any([options.signal || new AbortController().signal, AbortSignal.timeout(options.timeout ?? SHELF_TIMEOUT_MS)])
  try {
    const body = new FormData()
    body.set('image', file)
    const response = await (options.fetch || fetch)(url, { method: 'POST', body, signal, redirect: 'error' })
    if (!response.ok) throw upstreamError(response.status)
    const declared = Number(response.headers.get('content-length'))
    if (Number.isFinite(declared) && declared > MAX_GROUP_RESPONSE_BYTES) throw upstreamError()
    const reader = response.body?.getReader()
    if (!reader) throw upstreamError()
    const chunks: Uint8Array[] = []
    let total = 0
    try {
      while (true) {
        const next = await reader.read()
        if (next.done) break
        total += next.value.length
        if (total > MAX_GROUP_RESPONSE_BYTES) throw upstreamError()
        chunks.push(next.value)
      }
    } finally { await reader.cancel().catch(() => {}) }
    const value = JSON.parse(Buffer.concat(chunks).toString('utf8'))
    if (!validShelfResult(value)) throw upstreamError()
    return value
  } catch (error) {
    if (signal.aborted) throw createError({ statusCode: 504, statusMessage: 'Group matching timed out' })
    if (error && typeof error === 'object' && 'statusCode' in error) throw error
    throw upstreamError()
  }
}
