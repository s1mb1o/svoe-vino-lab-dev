import { afterEach, describe, expect, it, vi } from 'vitest'
import { readFile } from 'node:fs/promises'
import { checkHeicDimensions, dishImageType, DISH_IMAGE_SIZE_ERROR } from '../shared/dish-image'
import { decodeDishHeic } from '../app/utils/dinner-heic'

const file = (bytes: Uint8Array, name = 'photo', type = '') => new File([bytes as BlobPart], name, { type })
const box = (name: string, body: Uint8Array) => {
  const result = new Uint8Array(body.length + 8)
  new DataView(result.buffer).setUint32(0, result.length); result.set(new TextEncoder().encode(name), 4); result.set(body, 8)
  return result
}
const metadata = (width: number, height: number) => {
  const dimensions = new Uint8Array(12); const view = new DataView(dimensions.buffer)
  view.setUint32(4, width); view.setUint32(8, height)
  const iprp = box('iprp', box('ipco', box('ispe', dimensions)))
  return box('meta', new Uint8Array([0, 0, 0, 0, ...iprp]))
}

describe('dish image content validation', () => {
  it.each([
    [new Uint8Array([255, 216, 255, 224]), 'image/jpeg'],
    [new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10]), 'image/png'],
    [new TextEncoder().encode('RIFF1234WEBP'), 'image/webp'],
  ])('recognizes image signatures despite absent or generic MIME: %s', async (bytes, type) => {
    expect(await dishImageType(file(bytes as Uint8Array, 'photo.JPG', 'application/octet-stream'))).toBe(type)
  })
  it('accepts the real rotated macOS HEIC fixture with no MIME or extension', async () => {
    const bytes = await readFile(new URL('./data/dinner-rotated.heic', import.meta.url))
    expect(await dishImageType(file(bytes))).toBe('image/heic')
    expect(() => checkHeicDimensions(Uint8Array.from(bytes).buffer)).not.toThrow()
  })
  it('rejects misleading extensions, MIME and AVIF-compatible HEIF headers', async () => {
    await expect(dishImageType(file(new TextEncoder().encode('<svg></svg>'), 'photo.jpg', 'image/jpeg'))).rejects.toThrow('HEIC')
    const avif = box('ftyp', new TextEncoder().encode('avif0000mif1'))
    await expect(dishImageType(file(avif, 'photo.heic', 'image/heic'))).rejects.toThrow('HEIC')
  })
  it('rejects empty and oversized files before decoding', async () => {
    for (const bytes of [new Uint8Array(), new Uint8Array(10 * 1024 * 1024 + 1)]) await expect(dishImageType(file(bytes))).rejects.toThrow('10 МБ')
  })
  it('rejects huge or malformed HEIF dimensions before full pixel allocation', () => {
    expect(() => checkHeicDimensions(metadata(12000, 12000).buffer)).toThrow(DISH_IMAGE_SIZE_ERROR)
    expect(() => checkHeicDimensions(metadata(0, 32).buffer)).toThrow()
    expect(() => checkHeicDimensions(new Uint8Array([0, 0, 0]).buffer)).toThrow()
    expect(() => checkHeicDimensions(box('mdat', new Uint8Array(20)).buffer)).toThrow('Missing')
    const damaged = metadata(64, 32); new DataView(damaged.buffer).setUint32(0, damaged.length + 100)
    expect(() => checkHeicDimensions(damaged.buffer)).toThrow()
  })
  it('supports valid metadata and bounded extended-length boxes', () => {
    expect(() => checkHeicDimensions(metadata(4000, 3000).buffer)).not.toThrow()
    const body = metadata(64, 32); const extended = new Uint8Array(body.length + 8)
    const view = new DataView(extended.buffer); view.setUint32(0, 1); view.setBigUint64(8, BigInt(extended.length))
    extended.set(new TextEncoder().encode('meta'), 4); extended.set(body.subarray(8), 16)
    expect(() => checkHeicDimensions(extended.buffer)).not.toThrow()
  })
})

describe('HEIC conversion lifecycle', () => {
  afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers() })
  const stub = () => {
    const worker = { postMessage: vi.fn(), terminate: vi.fn(), onmessage: null as null | ((event: object) => void), onerror: null }
    vi.stubGlobal('Worker', vi.fn(function () { return worker }))
    return worker
  }
  it('terminates decoder work when cancelled', async () => {
    const worker = stub(); const controller = new AbortController()
    const pending = decodeDishHeic(file(new Uint8Array([1])), controller.signal)
    const queued = worker.onmessage!
    controller.abort()
    await expect(pending).rejects.toMatchObject({ name: 'AbortError' })
    expect(worker.terminate).toHaveBeenCalledTimes(1)
    const bitmap = { close: vi.fn() }; queued({ data: { bitmap } })
    expect(bitmap.close).toHaveBeenCalledTimes(1)
  })
  it('releases a completed worker and returns the transferred bitmap', async () => {
    const worker = stub(); const bitmap = { width: 32, height: 64 }
    const pending = decodeDishHeic(file(new Uint8Array([1])))
    worker.onmessage!({ data: { bitmap } })
    expect(await pending).toBe(bitmap); expect(worker.terminate).toHaveBeenCalledTimes(1)
  })
  it('bounds stuck conversions without an upstream request', async () => {
    vi.useFakeTimers(); const worker = stub()
    const pending = decodeDishHeic(file(new Uint8Array([1])))
    const assertion = expect(pending).rejects.toThrow('слишком много времени')
    await vi.advanceTimersByTimeAsync(60_000); await assertion
    expect(worker.terminate).toHaveBeenCalledTimes(1)
  })
})
