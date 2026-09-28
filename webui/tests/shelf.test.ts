import { describe, expect, it, vi } from 'vitest'
import sharp from 'sharp'
import { normalizeShelf, requireShelfMode, segmentShelf } from '../server/utils/shelf'
import { validBox, validShelfResult } from '../shared/shelf'

async function photo(width = 60, height = 40) {
  const bytes = await sharp({ create: { width, height, channels: 3, background: '#bb3311' } }).jpeg().toBuffer()
  return new File([new Uint8Array(bytes)], 'shelf.jpg', { type: 'image/jpeg' })
}
async function mask(width: number, height: number, box: number[], stray = false) {
  const pixels = new Uint8Array(width * height)
  for (let y = box[1]!; y < box[3]!; y++) for (let x = box[0]!; x < box[2]!; x++) pixels[y * width + x] = 255
  if (stray) pixels[width * height - 1] = 255
  return (await sharp(pixels, { raw: { width, height, channels: 1 } }).png().toBuffer()).toString('base64')
}
async function fixture() {
  return { width: 60, height: 40, count: 2, instances: [
    { score: .8, box: [-2, 3, 15, 34], mask_png_b64: await mask(60, 40, [0, 4, 14, 33], true) },
    { score: .9, box: [35, 2, 54, 35], mask_png_b64: await mask(60, 40, [36, 3, 53, 34]) },
  ] }
}
const endpoint = 'http://sam3.test/upstream/sam3'

describe('shelf segmentation service', () => {
  it('rejects every request while shelf mode is disabled', () => {
    expect(() => requireShelfMode('disabled')).toThrowError(expect.objectContaining({ statusCode: 503 }))
    expect(() => requireShelfMode(undefined)).toThrowError(expect.objectContaining({ statusCode: 503 }))
    expect(() => requireShelfMode('enabled')).not.toThrow()
  })
  it('uses normalized image dimensions, real mask shapes, and bounded photo crops', async () => {
    const request = vi.fn(async () => Response.json(await fixture()))
    const result = await segmentShelf(await photo(), { endpoint, fetch: request as typeof fetch })
    expect(validShelfResult(result)).toBe(true)
    expect(result.bottles).toHaveLength(2)
    expect(result.bottles[0]?.box[0]).toBe(0)
    expect(result.bottles[0]?.box[2]).toBeLessThan(.3)
    expect(result.bottles.map(b => b.id)).toEqual(['b1', 'b2'])
    const [url, options] = (request.mock.calls as unknown as [URL, RequestInit][])[0]!
    expect(url.href).toBe(endpoint + '/segment')
    const body = options.body as FormData
    expect(body.get('text')).toBe('wine bottle')
    expect(body.get('return_masks')).toBe('true')
    expect(options.redirect).toBe('error')
    expect((body.get('image') as File).type).toBe('image/jpeg')
    const overlay = Buffer.from(result.bottles[0]!.mask.split(',')[1]!, 'base64')
    const overlayInfo = await sharp(overlay).metadata()
    expect(overlayInfo.width).toBe(16)
    expect(overlayInfo.height).toBe(32)
    expect(overlayInfo.hasAlpha).toBe(true)
    const crop = Buffer.from(result.bottles[0]!.crop.split(',')[1]!, 'base64')
    const { data, info } = await sharp(crop).raw().toBuffer({ resolveWithObject: true })
    expect(info.width).toBeLessThan(25)
    expect(data[0]).toBeGreaterThan(data[1]! * 2) // Crop retains the photograph's red pixels, not the grayscale mask.
  })
  it('applies EXIF orientation and removes metadata before SAM3', async () => {
    const data = await sharp({ create: { width: 60, height: 40, channels: 3, background: '#fff' } }).jpeg().withMetadata({ orientation: 6 }).toBuffer()
    const normalized = await normalizeShelf(new File([new Uint8Array(data)], 'phone.jpg', { type: 'image/jpeg' }))
    expect([normalized.width, normalized.height]).toEqual([40, 60])
    const metadata = await sharp(normalized.data).metadata()
    expect(metadata.orientation).toBeUndefined()
    expect(metadata.exif).toBeUndefined()
  })
  it('removes duplicate detections and preserves empty results', async () => {
    const value = await fixture(); value.instances.push(value.instances[0]!); value.count++
    const result = await segmentShelf(await photo(), { endpoint, fetch: vi.fn(async () => Response.json(value)) })
    expect(result.bottles).toHaveLength(2)
    expect(result.truncated).toBe(false)
    const empty = await segmentShelf(await photo(), { endpoint, fetch: vi.fn(async () => Response.json({ width: 60, height: 40, count: 0, instances: [] })) })
    expect(empty.bottles).toEqual([])
    expect(validShelfResult(empty)).toBe(true)
  })
  it.each(['dimensions', 'mask-size', 'invalid-box', 'non-png', 'too-large', 'bad-json'])('rejects invalid service data: %s', async failure => {
    const data = await fixture()
    if (failure === 'dimensions') data.width = 59
    if (failure === 'mask-size') data.instances[0]!.mask_png_b64 = await mask(10, 10, [1, 1, 4, 8])
    if (failure === 'invalid-box') data.instances[0]!.box = [1, 2, 0, 3]
    if (failure === 'non-png') data.instances[0]!.mask_png_b64 = 'bm90LWFuLWltYWdl'
    const request = vi.fn(async () => failure === 'bad-json' ? new Response('invalid') : failure === 'too-large' ? new Response('{}', { headers: { 'content-length': String(17 * 1024 * 1024) } }) : Response.json(data))
    await expect(segmentShelf(await photo(), { endpoint, fetch: request })).rejects.toMatchObject({ statusCode: 502 })
    expect(request).toHaveBeenCalledTimes(1)
  })
  it.each(['empty', '503'])('retries once for recoverable upstream response: %s', async failure => {
    const request = vi.fn().mockResolvedValueOnce(failure === 'empty' ? new Response('') : new Response('', { status: 503 })).mockResolvedValueOnce(Response.json(await fixture()))
    expect((await segmentShelf(await photo(), { endpoint, fetch: request })).bottles).toHaveLength(2)
    expect(request).toHaveBeenCalledTimes(2)
  })
  it('does not retry an aborted request and reports timeout', async () => {
    const request = vi.fn((_url, options) => new Promise<Response>((_resolve, reject) => options.signal.addEventListener('abort', () => reject(new Error('aborted')))))
    await expect(segmentShelf(await photo(), { endpoint, fetch: request, timeout: 20 })).rejects.toMatchObject({ statusCode: 504 })
    expect(request).toHaveBeenCalledTimes(1)
  })
  it.each(['ECONNRESET', 'UND_ERR_SOCKET'])('retries one transient connection failure within the same timeout: %s', async code => {
    const request = vi.fn().mockRejectedValueOnce(new TypeError('fetch failed', { cause: { code } })).mockResolvedValueOnce(Response.json(await fixture()))
    expect((await segmentShelf(await photo(), { endpoint, fetch: request })).bottles).toHaveLength(2)
    expect(request).toHaveBeenCalledTimes(2)
    expect(request.mock.calls[0]![1].signal).toBe(request.mock.calls[1]![1].signal)
  })
  it('does not retry permanent connection failures', async () => {
    const request = vi.fn().mockRejectedValue(new TypeError('fetch failed', { cause: { code: 'ENOTFOUND' } }))
    await expect(segmentShelf(await photo(), { endpoint, fetch: request })).rejects.toMatchObject({ statusCode: 502 })
    expect(request).toHaveBeenCalledTimes(1)
  })
  it('rejects a missing service URL and undecodable images', async () => {
    await expect(segmentShelf(await photo(), { endpoint: '' })).rejects.toMatchObject({ statusCode: 503 })
    await expect(normalizeShelf(new File(['invalid'], 'bad.jpg'))).rejects.toMatchObject({ statusCode: 400 })
  })
  it('validates bounded normalized hit areas and malformed client responses', () => {
    expect(validBox([0, .2, 1, .9])).toBe(true)
    for (const box of [[0, 0, 2, 1], [1, 1, 0, 0], [0, NaN, 1, 1]]) expect(validBox(box)).toBe(false)
    for (const value of [null, {}, { image: { width: 10, height: 10, preview: 'data:image/jpeg;base64,eA==' }, bottles: [null] }]) expect(validShelfResult(value)).toBe(false)
  })
})
