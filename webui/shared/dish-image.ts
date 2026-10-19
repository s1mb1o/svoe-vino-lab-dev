import { MAX_IMAGE_BYTES } from './catalog'

export const DISH_IMAGE_ACCEPT = 'image/jpeg,image/heic,image/heif,image/png,image/webp,.jpg,.jpeg,.heic,.heif,.png,.webp'
export const DISH_CAMERA_ACCEPT = 'image/jpeg,image/heic,image/heif,image/png,image/webp'
export const DISH_MAX_PIXELS = 50_000_000
export const DISH_HEIC_TIMEOUT_MS = 60_000
export const DISH_IMAGE_FORMAT_ERROR = 'Выберите JPG, JPEG, HEIC, PNG или WebP.'
export const DISH_IMAGE_SIZE_ERROR = 'Снимок слишком большой. Выберите уменьшенную копию.'
const brands = new Set(['heic', 'heix', 'heim', 'heis', 'hevc', 'hevx', 'hevm', 'hevs', 'mif1', 'msf1'])
const ascii = (bytes: Uint8Array, start: number, end: number) => String.fromCharCode(...bytes.subarray(start, end))

// Detect actual bytes. Dragged files can have an empty or generic MIME type.
export async function dishImageType(file: File): Promise<'image/jpeg' | 'image/png' | 'image/webp' | 'image/heic'> {
  if (!file.size || file.size > MAX_IMAGE_BYTES) throw new Error('Выберите фотографию размером до 10 МБ.')
  const bytes = new Uint8Array(await file.slice(0, 4096).arrayBuffer())
  if (bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255) return 'image/jpeg'
  if ([137, 80, 78, 71, 13, 10, 26, 10].every((v, i) => bytes[i] === v)) return 'image/png'
  if (ascii(bytes, 0, 4) === 'RIFF' && ascii(bytes, 8, 12) === 'WEBP') return 'image/webp'
  if (bytes.length >= 16 && ascii(bytes, 4, 8) === 'ftyp') {
    const size = new DataView(bytes.buffer).getUint32(0)
    if (size >= 16 && size <= bytes.length && size % 4 === 0) {
      const types = [ascii(bytes, 8, 12)]
      for (let offset = 16; offset < size; offset += 4) types.push(ascii(bytes, offset, offset + 4))
      if (!types.some(type => ['avif', 'avis'].includes(type)) && types.some(type => brands.has(type))) return 'image/heic'
    }
  }
  throw new Error(DISH_IMAGE_FORMAT_ERROR)
}

// Walk only metadata containers, never compressed image data. Check ispe dimensions
// before the HEIF decoder allocates its full-size pixel buffer.
export function checkHeicDimensions(buffer: ArrayBuffer) {
  const view = new DataView(buffer); const bytes = new Uint8Array(buffer)
  let boxes = 0; let dimensions = 0
  function walk(start: number, end: number, depth: number) {
    if (depth > 4) throw new Error('Invalid HEIF metadata')
    for (let offset = start; offset < end;) {
      if (++boxes > 10_000 || offset + 8 > end) throw new Error('Invalid HEIF metadata')
      let size = view.getUint32(offset); let header = 8
      const type = ascii(bytes, offset + 4, offset + 8)
      if (size === 1) {
        if (offset + 16 > end) throw new Error('Invalid HEIF metadata')
        const extended = view.getBigUint64(offset + 8)
        if (extended > BigInt(end - offset)) throw new Error('Invalid HEIF metadata')
        size = Number(extended); header = 16
      } else if (size === 0) size = end - offset
      if (size < header || size > end - offset) throw new Error('Invalid HEIF metadata')
      if (type === 'ispe') {
        if (size < header + 12) throw new Error('Invalid HEIF dimensions')
        const width = view.getUint32(offset + header + 4); const height = view.getUint32(offset + header + 8)
        if (!width || !height) throw new Error('Invalid HEIF dimensions')
        if (width * height > DISH_MAX_PIXELS) throw new Error(DISH_IMAGE_SIZE_ERROR)
        dimensions++
      } else if (['meta', 'iprp', 'ipco'].includes(type)) {
        const children = offset + header + (type === 'meta' ? 4 : 0)
        if (children > offset + size) throw new Error('Invalid HEIF metadata')
        walk(children, offset + size, depth + 1)
      }
      offset += size
    }
  }
  walk(0, bytes.length, 0)
  if (!dimensions) throw new Error('Missing HEIF dimensions')
}
