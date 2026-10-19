import { DISH_HEIC_TIMEOUT_MS, DISH_IMAGE_SIZE_ERROR } from '#shared/dish-image'

// A fresh outer worker owns the decoder and its child worker. Terminating it on
// replacement, cancellation or timeout releases conversion work and image memory.
export function decodeDishHeic(file: File, signal?: AbortSignal): Promise<ImageBitmap> {
  signal?.throwIfAborted()
  return new Promise((resolve, reject) => {
    const worker = new Worker(new URL('../workers/dinner-heic.worker.ts', import.meta.url), { type: 'module', name: 'dinner-heic' })
    let settled = false
    const cleanup = () => { settled = true; clearTimeout(timer); signal?.removeEventListener('abort', abort); worker.onmessage = worker.onerror = null; worker.terminate() }
    const fail = (message: string) => { if (!settled) { cleanup(); reject(new Error(message)) } }
    const abort = () => { if (!settled) { cleanup(); reject(new DOMException('Aborted', 'AbortError')) } }
    const timer = setTimeout(() => fail('Подготовка HEIC заняла слишком много времени. Проверьте соединение или попробуйте другой снимок.'), DISH_HEIC_TIMEOUT_MS)
    worker.onmessage = (event: MessageEvent<{ bitmap?: ImageBitmap; error?: string }>) => {
      if (settled) { event.data.bitmap?.close(); return }
      cleanup()
      if (event.data.bitmap) resolve(event.data.bitmap)
      else reject(new Error(event.data.error === 'size' ? DISH_IMAGE_SIZE_ERROR : event.data.error === 'load' ? 'Не удалось подготовить HEIC. Обновите страницу и проверьте соединение.' : 'Не удалось прочитать HEIC. Файл может быть повреждён. Попробуйте другой снимок.'))
    }
    worker.onerror = event => { event.preventDefault(); fail('Не удалось подготовить HEIC. Обновите страницу или повторите позже.') }
    signal?.addEventListener('abort', abort, { once: true })
    worker.postMessage(file)
  })
}
