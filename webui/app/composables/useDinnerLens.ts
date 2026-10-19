import { computed, onScopeDispose, ref, shallowRef } from 'vue'
import { dishImageType, DISH_HEIC_TIMEOUT_MS, DISH_MAX_PIXELS, DISH_IMAGE_SIZE_ERROR } from '#shared/dish-image'
import { DINNER_TIMEOUT_MS, dinnerNode, parseDinnerPage, type DinnerPage, type DinnerSelection, type DinnerWine } from '#shared/dinner'

export async function prepareDishPhoto(file: File, signal?: AbortSignal): Promise<string> {
  const type = await dishImageType(file)
  signal?.throwIfAborted()
  const url = type === 'image/heic' ? '' : URL.createObjectURL(new Blob([file], { type }))
  let bitmap: ImageBitmap | undefined
  try {
    let image: HTMLImageElement | ImageBitmap
    if (type === 'image/heic') {
      const { decodeDishHeic } = await import('../utils/dinner-heic')
      signal?.throwIfAborted()
      image = bitmap = await decodeDishHeic(file, signal)
    }
    else {
      const decoded = new Image(); decoded.src = url
      try { await decoded.decode() } catch { throw new Error('Не удалось прочитать фото. Попробуйте другой снимок.') }
      image = decoded
    }
    signal?.throwIfAborted()
    const width = image instanceof HTMLImageElement ? image.naturalWidth : image.width
    const height = image instanceof HTMLImageElement ? image.naturalHeight : image.height
    if (!width || !height || width * height > DISH_MAX_PIXELS) throw new Error(DISH_IMAGE_SIZE_ERROR)
    const scale = Math.min(1, 1600 / Math.max(width, height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(width * scale)); canvas.height = Math.max(1, Math.round(height * scale))
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Браузер не смог подготовить фото. Попробуйте другой браузер.')
    context.fillStyle = '#fff'; context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    const normalized = canvas.toDataURL('image/jpeg', 0.86)
    canvas.width = 0; canvas.height = 0
    if (normalized.length > 7_000_000 || !normalized.startsWith('data:image/jpeg;base64,')) throw new Error('Снимок слишком большой. Выберите уменьшенную копию.')
    return normalized
  } finally { if (url) URL.revokeObjectURL(url); bitmap?.close() }
}

export function useDinnerLens(dependencies: { fetch?: typeof fetch; prepare?: typeof prepareDishPhoto; timeout?: number } = {}) {
  const request = dependencies.fetch || globalThis.fetch
  const prepare = dependencies.prepare || prepareDishPhoto
  const dish = ref(''); const preview = ref(''); const error = ref(''); const question = ref('')
  const failedAction = ref<'recognizing' | 'loading' | 'more' | null>(null)
  const phase = ref<'idle' | 'recognizing' | 'confirm' | 'loading' | 'more' | 'ready'>('idle')
  const wines = shallowRef<DinnerWine[]>([])
  const page = shallowRef<DinnerPage | null>(null)
  const busy = computed(() => ['recognizing', 'loading', 'more'].includes(phase.value))
  const file = shallowRef<File | null>(null)
  let generation = 0; let controller: AbortController | undefined

  function cancel() {
    generation++; controller?.abort(); controller = undefined
    error.value = ''
    failedAction.value = null
    phase.value = page.value ? 'ready' : dish.value || preview.value ? 'confirm' : 'idle'
  }
  function invalidate() { cancel(); page.value = null; wines.value = []; question.value = ''; phase.value = dish.value || preview.value ? 'confirm' : 'idle' }
  function reset() { invalidate(); dish.value = ''; preview.value = ''; file.value = null; phase.value = 'idle' }
  const message = (status: number) => ({
    400: 'Не удалось прочитать запрос. Попробуйте ещё раз.', 413: 'Выберите фотографию размером до 10 МБ.',
    415: 'Выберите JPG, JPEG, HEIC, PNG или WebP.', 422: 'Проверьте название блюда и выбранные условия.',
    429: 'Слишком много запросов. Попробуйте немного позже.', 503: 'Подбор вина временно недоступен. Попробуйте ещё раз позже.',
    504: 'Подбор занял слишком много времени. Попробуйте ещё раз.',
  } as Record<number, string>)[status] || 'Сервис не смог выполнить подбор. Попробуйте ещё раз.'

  async function post(path: string, body: unknown, active: AbortController): Promise<DinnerPage> {
    const response = await request('/api/dinner/' + path, { method: 'POST', body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' }, signal: active.signal })
    if (!response.ok) throw new Error(message(response.status))
    let raw: unknown
    try { raw = await response.json() } catch { throw new Error('Пришёл неполный результат. Попробуйте ещё раз.') }
    const value = parseDinnerPage(raw)
    if (!value) throw new Error('Пришёл неполный результат. Попробуйте ещё раз.')
    return value
  }
  async function operation(mode: 'recognizing' | 'loading' | 'more', work: (active: AbortController, current: number) => Promise<void>) {
    cancel()
    const current = generation; const active = new AbortController(); controller = active; phase.value = mode
    const timer = setTimeout(() => active.abort(), dependencies.timeout ?? DINNER_TIMEOUT_MS + 10_000 + (mode === 'recognizing' ? DISH_HEIC_TIMEOUT_MS : 0))
    try { await work(active, current) }
    catch (failure) {
      if (current !== generation) return
      failedAction.value = mode
      error.value = active.signal.aborted ? 'Время ожидания истекло. Попробуйте ещё раз.'
        : failure instanceof Error && !(failure instanceof TypeError) ? failure.message : 'Нет связи с сервисом. Проверьте соединение.'
      phase.value = page.value ? 'ready' : dish.value || preview.value ? 'confirm' : 'idle'
    } finally { clearTimeout(timer); if (current === generation) controller = undefined }
  }
  async function recognize() {
    if (!file.value) return
    page.value = null; wines.value = []; question.value = ''; dish.value = ''
    await operation('recognizing', async (active, current) => {
      const image = preview.value || await prepare(file.value!, active.signal)
      if (current !== generation) return
      preview.value = image
      const value = await post('recognize', { image_base64: image, limit: 3 }, active)
      if (current !== generation) return
      dish.value = dinnerNode(value.resolved_node_id)?.label || ''
      question.value = value.clarification_question || 'Проверьте название блюда и уточните соус.'
      // Keep recognition separate so the view can request wines with the latest dish and taste settings.
      phase.value = 'confirm'
    })
  }
  async function select(files: File[]) {
    reset()
    if (files.length !== 1 || !files[0]) { error.value = 'Выберите одну фотографию блюда.'; return }
    file.value = files[0]
    await recognize()
  }
  async function recommend(selection: DinnerSelection) {
    page.value = null; wines.value = []; question.value = ''
    await operation('loading', async (active, current) => {
      const value = await post('recommendations', { ...selection, limit: 3 }, active)
      if (current !== generation) return
      if (value.shown_count !== value.results.length) throw new Error('Пришёл неполный результат. Попробуйте ещё раз.')
      page.value = value; wines.value = value.results; question.value = value.clarification_question || ''
      phase.value = value.status === 'needs_category' ? 'confirm' : 'ready'
    })
  }
  async function more() {
    const previous = page.value
    if (!previous?.next_cursor || busy.value) return
    await operation('more', async (active, current) => {
      const value = await post('more', { cursor: previous.next_cursor }, active)
      if (current !== generation) return
      if (value.resolved_node_id !== previous.resolved_node_id || value.total_eligible !== previous.total_eligible
        || value.shown_count !== previous.shown_count + value.results.length || value.next_cursor === previous.next_cursor
        || value.results.some(wine => wines.value.some(old => old.wine_slug === wine.wine_slug))) throw new Error('Продолжение подбора устарело. Выполните подбор ещё раз.')
      wines.value = [...wines.value, ...value.results]; page.value = value; phase.value = 'ready'
    })
  }
  onScopeDispose(cancel)
  return { dish, preview, error, question, phase, page, wines, busy, file, failedAction, recognize, select, recommend, more, cancel, invalidate, reset }
}
