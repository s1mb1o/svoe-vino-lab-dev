import { createError, getHeader, type H3Event } from 'h3'
import { Buffer } from 'node:buffer'
import { MAX_IMAGE_BYTES, MOCK_SLUG, extractSlug } from '#shared/catalog'

const MAX_BODY_BYTES = MAX_IMAGE_BYTES + 64 * 1024
export type PredictionMode = 'mock' | 'upstream'

export function predictionMode(value: unknown): PredictionMode {
  if (value === 'mock' || value === 'upstream') return value
  throw createError({ statusCode: 503, statusMessage: 'Prediction mode is not configured correctly' })
}

export function imageType(bytes: Uint8Array): string | null {
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return 'image/jpeg'
  if (bytes.length >= 8 && [137, 80, 78, 71, 13, 10, 26, 10].every((byte, i) => bytes[i] === byte)) return 'image/png'
  if (bytes.length >= 12 && Buffer.from(bytes.subarray(0, 4)).toString() === 'RIFF' && Buffer.from(bytes.subarray(8, 12)).toString() === 'WEBP') return 'image/webp'
  return null
}

function upstreamError(status = 502) {
  const allowed = [400, 401, 408, 413, 415, 502, 503, 504]
  return createError({ statusCode: allowed.includes(status) ? status : 502, statusMessage: 'Recognition service failed. Please retry.' })
}

function readLimitedBody(event: H3Event): Promise<Buffer> {
  const declared = Number(getHeader(event, 'content-length'))
  if (Number.isFinite(declared) && declared > MAX_BODY_BYTES) {
    throw createError({ statusCode: 413, statusMessage: 'Image must be at most 10 MiB' })
  }
  return new Promise((resolve, reject) => {
    const request = event.node.req
    const chunks: Buffer[] = []
    let total = 0
    const cleanup = () => {
      request.off('data', onData)
      request.off('end', onEnd)
      request.off('error', onError)
      request.off('aborted', onAbort)
    }
    const onError = () => { cleanup(); reject(createError({ statusCode: 400, statusMessage: 'Upload interrupted' })) }
    const onAbort = () => onError()
    const onEnd = () => { cleanup(); resolve(Buffer.concat(chunks)) }
    const onData = (chunk: Buffer) => {
      total += chunk.length
      if (total > MAX_BODY_BYTES) {
        cleanup()
        request.resume()
        reject(createError({ statusCode: 413, statusMessage: 'Image must be at most 10 MiB' }))
        return
      }
      chunks.push(chunk)
    }
    request.on('data', onData).once('end', onEnd).once('error', onError).once('aborted', onAbort)
  })
}

export async function readImage(event: H3Event): Promise<File> {
  const contentType = getHeader(event, 'content-type') || ''
  if (!contentType.toLowerCase().startsWith('multipart/form-data;')) {
    throw createError({ statusCode: 415, statusMessage: 'Send multipart/form-data with an image file' })
  }
  const body = await readLimitedBody(event)
  let form: FormData
  try {
    form = await new Response(new Uint8Array(body), { headers: { 'content-type': contentType } }).formData()
  } catch {
    throw createError({ statusCode: 400, statusMessage: 'Invalid multipart upload' })
  }
  const files = [...form.entries()].filter((entry): entry is [string, File] => typeof entry[1] !== 'string')
  const field = form.getAll('image')
  if (files.length !== 1 || field.length !== 1 || files[0]?.[0] !== 'image' || typeof field[0] === 'string') {
    throw createError({ statusCode: 400, statusMessage: 'Send exactly one file under image' })
  }
  const file = files[0][1]
  if (!file.size) throw createError({ statusCode: 400, statusMessage: 'Image is empty' })
  if (file.size > MAX_IMAGE_BYTES) throw createError({ statusCode: 413, statusMessage: 'Image must be at most 10 MiB' })
  const type = imageType(new Uint8Array(await file.slice(0, 12).arrayBuffer()))
  if (!type) throw createError({ statusCode: 415, statusMessage: 'Use a JPEG, PNG, or WebP image' })
  return new File([file], `image.${type.split('/')[1]}`, { type })
}

export async function predict(file: File, mode: PredictionMode, endpoint: string, timeoutMs = 8000, requestSignal?: AbortSignal): Promise<{ slug: string }> {
  if (mode === 'mock') return { slug: MOCK_SLUG }
  let url: URL
  try {
    url = new URL(endpoint)
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new Error('URL')
  } catch {
    throw createError({ statusCode: 503, statusMessage: 'Prediction endpoint is not configured correctly' })
  }
  const signal = requestSignal ? AbortSignal.any([requestSignal, AbortSignal.timeout(timeoutMs)]) : AbortSignal.timeout(timeoutMs)
  try {
    const form = new FormData()
    form.set('image', file)
    const response = await fetch(url, { method: 'POST', body: form, signal, redirect: 'error' })
    if (![200, 201].includes(response.status)) throw upstreamError(response.status)
    // Bound the upstream response. A prediction only needs one short string.
    const reader = response.body?.getReader()
    if (!reader) throw new Error('Empty upstream body')
    const chunks: Uint8Array[] = []
    let total = 0
    try {
      while (true) {
        const next = await reader.read()
        if (next.done) break
        total += next.value.length
        if (total > 64 * 1024) throw new Error('Upstream response is too large')
        chunks.push(next.value)
      }
    } finally {
      await reader.cancel().catch(() => {})
    }
    const slug = extractSlug(JSON.parse(Buffer.concat(chunks).toString('utf8')))
    if (!slug) throw new Error('Invalid upstream slug')
    return { slug }
  } catch (error) {
    if (signal.aborted) throw createError({ statusCode: 504, statusMessage: 'Recognition timed out. Please retry.' })
    if (error && typeof error === 'object' && 'statusCode' in error) throw error
    throw upstreamError()
  }
}
