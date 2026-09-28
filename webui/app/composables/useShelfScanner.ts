import { computed, onScopeDispose, ref, shallowRef } from 'vue'
import { MAX_IMAGE_BYTES } from '#shared/catalog'
import { SHELF_TIMEOUT_MS, groupCandidateWine, validShelfResult, type ShelfResult } from '#shared/shelf'

interface Dependencies {
  fetch?: typeof fetch
  createObjectURL?: (file: Blob) => string
  revokeObjectURL?: (url: string) => void
  timeout?: number
}
export function useShelfScanner(dependencies: Dependencies = {}) {
  const request = dependencies.fetch || globalThis.fetch
  const createPreview = dependencies.createObjectURL || ((value: Blob) => URL.createObjectURL(value))
  const releasePreview = dependencies.revokeObjectURL || ((value: string) => URL.revokeObjectURL(value))
  const file = shallowRef<File | null>(null)
  const preview = ref('')
  const result = shallowRef<ShelfResult | null>(null)
  const phase = ref<'idle' | 'selected' | 'loading' | 'ready' | 'error'>('idle')
  const error = ref('')
  const exampleLoading = ref(false)
  const selectedId = ref('')
  const selectedBottle = computed(() => result.value?.bottles.find(b => b.id === selectedId.value) || null)
  const selectedMatch = computed(() => selectedBottle.value?.match || null)
  const selectedWine = computed(() => selectedMatch.value ? groupCandidateWine(selectedMatch.value) : null)
  const portalUrl = computed(() => selectedMatch.value?.wine.page_url || '')
  const busy = computed(() => exampleLoading.value || phase.value === 'loading')
  const displayImage = computed(() => result.value?.image.preview || preview.value)
  let controller: AbortController | undefined
  let generation = 0

  function closeBottle() { selectedId.value = '' }
  function cancel() {
    generation++
    controller?.abort(); controller = undefined
    exampleLoading.value = false
    phase.value = file.value ? 'selected' : 'idle'
    error.value = ''
    result.value = null
    closeBottle()
  }
  function reset() {
    cancel()
    if (preview.value) releasePreview(preview.value)
    file.value = null; preview.value = ''; phase.value = 'idle'
  }
  async function submit() {
    if (!file.value) return
    cancel()
    const current = generation
    controller = new AbortController()
    const active = controller
    const timer = setTimeout(() => active.abort(), dependencies.timeout ?? SHELF_TIMEOUT_MS + 15000)
    phase.value = 'loading'
    try {
      const body = new FormData(); body.set('image', file.value)
      const response = await request('/v1/group/match', { method: 'POST', body, signal: active.signal })
      if (!response.ok) {
        const messages: Record<number, string> = { 400: 'Не удалось прочитать фото. Попробуйте другой снимок.', 401: 'Сервис распознавания отклонил запрос.', 413: 'Выберите фото до 10 МБ.', 415: 'Нужен JPEG, PNG или WebP.', 502: 'Сервис не смог распознать полку. Попробуйте ещё раз.', 503: 'Режим полки пока не подключён. Попробуйте позже.', 504: 'Распознавание бутылок заняло слишком много времени. Попробуйте ещё раз.' }
        throw new Error(messages[response.status] || 'Сервис не смог распознать бутылки. Попробуйте ещё раз.')
      }
      const value = await response.json()
      if (!validShelfResult(value)) throw new Error('Сервис вернул неполный результат. Попробуйте ещё раз.')
      if (current !== generation) return
      result.value = value
      phase.value = 'ready'
    } catch (failure) {
      if (current !== generation) return
      error.value = active.signal.aborted ? 'Время ожидания истекло. Попробуйте ещё раз.' : failure instanceof Error && !(failure instanceof TypeError) ? failure.message : 'Нет связи с сервисом. Проверьте соединение.'
      phase.value = 'error'
    } finally { clearTimeout(timer); if (current === generation) controller = undefined }
  }
  async function select(files: File[]) {
    reset()
    const image = files[0]
    if (files.length !== 1 || !image) error.value = 'Выберите одну фотографию полки.'
    else if (!image.size) error.value = 'Файл пуст. Выберите другой снимок.'
    else if (image.size > MAX_IMAGE_BYTES) error.value = 'Выберите фотографию размером до 10 МБ.'
    else if (image.type && !['image/jpeg', 'image/png', 'image/webp'].includes(image.type)) error.value = 'Выберите JPEG, PNG или WebP. Сохраните HEIC в формате JPEG.'
    if (error.value) { phase.value = 'error'; return }
    file.value = image!; preview.value = createPreview(image!)
    await submit()
  }
  function selectBottle(id: string) {
    const bottle = result.value?.bottles.find(b => b.id === id)
    if (!bottle || phase.value !== 'ready') throw new Error('Select a bottle from the current shelf result.')
    selectedId.value = id
  }
  async function example() {
    reset()
    const current = generation
    controller = new AbortController()
    const active = controller
    const timer = setTimeout(() => active.abort(), 10000)
    exampleLoading.value = true
    try {
      const response = await request('/reference/shelf-example.jpg', { signal: active.signal })
      if (!response.ok) throw new Error('Example unavailable')
      const blob = await response.blob()
      if (current === generation) await select([new File([blob], 'Пример винной полки.jpg', { type: 'image/jpeg' })])
    } catch {
      if (current === generation) { error.value = 'Пример не загрузился. Выберите свою фотографию.'; phase.value = 'error' }
    } finally { clearTimeout(timer); if (current === generation) { exampleLoading.value = false; controller = undefined } }
  }
  onScopeDispose(reset)
  return { file, preview, result, phase, error, selectedId, selectedBottle, selectedMatch, selectedWine, portalUrl, busy, displayImage, exampleLoading, select, submit, selectBottle, example, closeBottle, cancel, reset }
}
