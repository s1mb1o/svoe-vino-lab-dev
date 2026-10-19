/*! HEIC decoding: heic-to 1.6.6 (LGPL-3.0-or-later). License, GPL text and source: /third-party/heic-to-NOTICE.txt */
import { checkHeicDimensions, DISH_IMAGE_SIZE_ERROR, DISH_MAX_PIXELS } from '../../shared/dish-image'

self.onmessage = async (event: MessageEvent<File>) => {
  let bitmap: ImageBitmap | undefined
  try {
    checkHeicDimensions(await event.data.arrayBuffer())
    // Keep the upstream library separately replaceable, outside the app bundle.
    const url = new URL('/third-party/heic-to-1.6.6/heic-to.js', self.location.origin).href
    const { heicTo } = await import(/* @vite-ignore */ url).catch(() => { throw new Error('decoder-load') }) as typeof import('heic-to/csp')
    bitmap = await heicTo({ blob: event.data, type: 'bitmap' })
    if (!bitmap.width || !bitmap.height || bitmap.width * bitmap.height > DISH_MAX_PIXELS) throw new Error(DISH_IMAGE_SIZE_ERROR)
    self.postMessage({ bitmap }, { transfer: [bitmap] })
    bitmap = undefined
  } catch (failure) {
    const message = failure instanceof Error ? failure.message : ''
    self.postMessage({ error: message === DISH_IMAGE_SIZE_ERROR ? 'size' : message === 'decoder-load' ? 'load' : 'decode' })
  } finally { bitmap?.close() }
}
