import sharp from 'sharp'
import { createError } from 'h3'
import { MAX_SHELF_BOTTLES, SHELF_TIMEOUT_MS, type BottleBox, type ShelfBottle, type ShelfResult } from '#shared/shelf'

const MAX_RESPONSE_BYTES = 16 * 1024 * 1024
interface Instance { score: number; box: number[]; mask_png_b64: string }
function serviceError(timeout = false) { return createError({ statusCode: timeout ? 504 : 502, statusMessage: timeout ? 'Shelf segmentation timed out' : 'Shelf segmentation service is unavailable' }) }

export function requireShelfMode(value: unknown) {
  if (value !== 'enabled') throw createError({ statusCode: 503, statusMessage: 'Shelf photo mode is temporarily unavailable' })
}

export async function normalizeShelf(file: File) {
  try {
    const { data, info } = await sharp(Buffer.from(await file.arrayBuffer()), { limitInputPixels: 40000000, animated: false })
      .rotate().resize({ width: 1600, height: 1600, fit: 'inside', withoutEnlargement: true }).flatten({ background: '#ffffff' }).jpeg({ quality: 86 }).toBuffer({ resolveWithObject: true })
    return { data, width: info.width, height: info.height }
  } catch { throw createError({ statusCode: 400, statusMessage: 'Image cannot be decoded or exceeds 40 megapixels' }) }
}

async function sam3(image: Buffer, width: number, height: number, endpoint: string, signal: AbortSignal, request: typeof fetch): Promise<Instance[]> {
  let url: URL
  try {
    url = new URL(`${endpoint.replace(/\/+$/, '')}/segment`)
    if (!endpoint || !['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw new Error('endpoint')
  } catch { throw createError({ statusCode: 503, statusMessage: 'SAM3_ENDPOINT is not configured correctly' }) }
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const body = new FormData()
      body.set('image', new File([new Uint8Array(image)], 'shelf.jpg', { type: 'image/jpeg' }))
      body.set('text', 'wine bottle')
      body.set('threshold', '0.4')
      body.set('mask_threshold', '0.5')
      body.set('return_masks', 'true')
      const response = await request(url, { method: 'POST', body, signal, redirect: 'error' })
      if (response.status >= 500 && attempt === 0) { await response.body?.cancel(); continue }
      if (!response.ok || Number(response.headers.get('content-length')) > MAX_RESPONSE_BYTES) { await response.body?.cancel(); throw serviceError() }
      const reader = response.body?.getReader()
      const chunks: Uint8Array[] = []
      let total = 0
      if (reader) {
        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) break
            total += value.byteLength
            if (total > MAX_RESPONSE_BYTES) throw serviceError()
            chunks.push(value)
          }
        } finally { await reader.cancel().catch(() => {}) }
      }
      if (!total && attempt === 0) continue
      const result = JSON.parse(Buffer.concat(chunks).toString('utf8'))
      if (result.width !== width || result.height !== height || !Array.isArray(result.instances) || result.instances.length > 500 || result.count !== result.instances.length) throw serviceError()
      if (result.instances.some((i: Instance) => !i || typeof i.score !== 'number' || !Number.isFinite(i.score) || i.score < 0 || i.score > 1 || !Array.isArray(i.box) || i.box.length !== 4 || !i.box.every(Number.isFinite) || i.box[2]! <= i.box[0]! || i.box[3]! <= i.box[1]! || typeof i.mask_png_b64 !== 'string' || i.mask_png_b64.length > 1024 * 1024)) throw serviceError()
      return result.instances
    } catch (error) {
      const failure = error as { code?: string; cause?: { code?: string } }
      const code = failure?.cause?.code || failure?.code
      if (attempt === 0 && !signal.aborted && ['ECONNRESET', 'ETIMEDOUT', 'UND_ERR_SOCKET', 'UND_ERR_HEADERS_TIMEOUT', 'UND_ERR_BODY_TIMEOUT'].includes(code || '')) continue
      throw serviceError(signal.aborted)
    }
  }
  throw serviceError(signal.aborted)
}

export function boxOverlap(a: BottleBox, b: BottleBox) {
  const intersection = Math.max(0, Math.min(a[2], b[2]) - Math.max(a[0], b[0])) * Math.max(0, Math.min(a[3], b[3]) - Math.max(a[1], b[1]))
  const union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection
  return union ? intersection / union : 0
}

export async function segmentShelf(file: File, options: { endpoint: string; signal?: AbortSignal; fetch?: typeof fetch; timeout?: number }): Promise<ShelfResult> {
  const signal = AbortSignal.any([options.signal || new AbortController().signal, AbortSignal.timeout(options.timeout ?? SHELF_TIMEOUT_MS)])
  const normalized = await normalizeShelf(file)
  const { data: image, width, height } = normalized
  const instances = await sam3(image, width, height, options.endpoint, signal, options.fetch || fetch)
  const bottles: ShelfBottle[] = []
  let totalBytes = image.byteLength
  const valid = instances.filter(i => i.score >= .4).sort((a, b) => b.score - a.score)
  for (const instance of valid) {
    if (signal.aborted) throw serviceError(true)
    if (bottles.length >= MAX_SHELF_BOTTLES) break
    try {
      const maskBytes = Buffer.from(instance.mask_png_b64, 'base64')
      const metadata = await sharp(maskBytes, { limitInputPixels: 1600 * 1600 }).metadata()
      if (metadata.format !== 'png' || metadata.width !== width || metadata.height !== height) throw serviceError()
      // Some masks contain distant fragments. Keep the detector's clamped region.
      const left = Math.max(0, Math.floor(instance.box[0]!))
      const top = Math.max(0, Math.floor(instance.box[1]!))
      const right = Math.min(width - 1, Math.ceil(instance.box[2]!))
      const bottom = Math.min(height - 1, Math.ceil(instance.box[3]!))
      if (right < left || bottom < top) continue
      const maskWidth = right - left + 1, maskHeight = bottom - top + 1
      const mask = await sharp(maskBytes).extract({ left, top, width: maskWidth, height: maskHeight }).greyscale().removeAlpha().threshold(128).raw().toBuffer()
      if (!mask.some(pixel => pixel >= 128)) continue
      const box: BottleBox = [left / width, top / height, (right + 1) / width, (bottom + 1) / height]
      if (bottles.some(b => boxOverlap(b.box, box) >= .9)) continue
      const overlay = await sharp({ create: { width: maskWidth, height: maskHeight, channels: 3, background: '#edd9aa' } }).joinChannel(mask, { raw: { width: maskWidth, height: maskHeight, channels: 1 } }).png().toBuffer()
      const padding = Math.max(2, Math.round((right - left + 1) * .05))
      const cropLeft = Math.max(0, left - padding), cropTop = Math.max(0, top - padding)
      const crop = await sharp(image).extract({ left: cropLeft, top: cropTop, width: Math.min(width, right + 1 + padding) - cropLeft, height: Math.min(height, bottom + 1 + padding) - cropTop })
        .resize({ width: 640, height: 960, fit: 'inside', withoutEnlargement: true }).jpeg({ quality: 92 }).toBuffer()
      totalBytes += crop.byteLength + overlay.byteLength
      if (totalBytes > 6 * 1024 * 1024) break
      bottles.push({ id: '', box, mask: `data:image/png;base64,${overlay.toString('base64')}`, crop: `data:image/jpeg;base64,${crop.toString('base64')}` })
    } catch { throw serviceError(signal.aborted) }
  }
  // Group by vertical band, then read each shelf from left to right.
  bottles.sort((a, b) => Math.floor(a.box[1] * 8) - Math.floor(b.box[1] * 8) || a.box[0] - b.box[0])
  bottles.forEach((b, index) => { b.id = `b${index + 1}` })
  return { image: { width, height, preview: `data:image/jpeg;base64,${image.toString('base64')}` }, bottles, detectedCount: valid.length, truncated: bottles.length === MAX_SHELF_BOTTLES && valid.length > bottles.length || totalBytes > 6 * 1024 * 1024 }
}
