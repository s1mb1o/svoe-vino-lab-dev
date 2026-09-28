import { computed, onScopeDispose, ref, shallowRef, type Ref } from 'vue'
import { MAX_IMAGE_BYTES, MOCK_SLUG, extractSlug, sourceWineUrl, type Wine } from '#shared/catalog'

type Mode = 'mock' | 'upstream' | undefined
type Phase = 'idle' | 'selected' | 'loading' | 'resolving' | 'matched' | 'error'
interface Dependencies {
  fetch?: typeof fetch
  createObjectURL?: (file: Blob) => string
  revokeObjectURL?: (url: string) => void
  predictionTimeout?: number
  metadataTimeout?: number
}

export function useWineScanner(mode: Ref<Mode>, dependencies: Dependencies = {}) {
  const request = dependencies.fetch || globalThis.fetch
  const createPreview = dependencies.createObjectURL || ((file: Blob) => URL.createObjectURL(file))
  const releasePreview = dependencies.revokeObjectURL || ((url: string) => URL.revokeObjectURL(url))
  const file = shallowRef<File | null>(null)
  const preview = ref('')
  const phase = ref<Phase>('idle')
  const error = ref('')
  const slug = ref('')
  const wine = shallowRef<Wine | null>(null)
  const mock = ref(false)
  const metadataUnavailable = ref(false)
  const exampleLoading = ref(false)
  const busy = computed(() => exampleLoading.value || phase.value === 'loading' || phase.value === 'resolving')
  const portalUrl = computed(() => slug.value ? sourceWineUrl(slug.value) : '')
  let controller: AbortController | undefined
  let generation = 0

  function invalidate() {
    generation++
    controller?.abort()
    controller = undefined
    exampleLoading.value = false
  }
  function clearResult() {
    error.value = ''
    slug.value = ''
    wine.value = null
    mock.value = false
    metadataUnavailable.value = false
  }
  function reset() {
    invalidate()
    if (preview.value) releasePreview(preview.value)
    preview.value = ''
    file.value = null
    phase.value = 'idle'
    clearResult()
  }
  function cancel() {
    invalidate()
    clearResult()
    phase.value = file.value ? 'selected' : 'idle'
  }

  async function submit() {
    if (!file.value) return
    invalidate()
    clearResult()
    if (!mode.value) {
      phase.value = 'error'
      error.value = 'Сервис поиска недоступен. Обновите настройки и попробуйте ещё раз.'
      return
    }
    const requestMode = mode.value
    const current = generation
    const activeController = new AbortController()
    controller = activeController
    let timer = setTimeout(() => activeController.abort(), dependencies.predictionTimeout ?? 10000)
    phase.value = 'loading'
    try {
      const body = new FormData()
      body.set('image', file.value)
      const response = await request('/v1/eval/predict', { method: 'POST', body, signal: activeController.signal })
      if (![200, 201].includes(response.status)) {
        const messages: Record<number, string> = {
          400: 'Не удалось прочитать фото. Попробуйте другой снимок.',
          413: 'Фото слишком большое. Выберите файл до 10 МБ.',
          415: 'Нужен снимок в формате JPEG, PNG или WebP.',
          502: 'Сервис поиска не ответил. Попробуйте ещё раз.',
          503: 'Сервис поиска ещё не подключён. Попробуйте позже.',
          504: 'Поиск занял слишком много времени. Попробуйте ещё раз.',
        }
        throw new Error(messages[response.status] || 'Не удалось найти вино. Попробуйте ещё раз.')
      }
      const predicted = extractSlug(await response.json())
      if (!predicted) throw new Error('Сервис вернул неполный ответ. Попробуйте ещё раз.')
      if (current !== generation) return
      clearTimeout(timer)
      slug.value = predicted
      mock.value = response.headers.get('X-Prediction-Mode') === 'mock' || requestMode === 'mock'
      phase.value = 'resolving'
      timer = setTimeout(() => activeController.abort(), dependencies.metadataTimeout ?? 4000)
      try {
        const metadata = await request(`/api/wines/${encodeURIComponent(predicted)}`, { signal: activeController.signal })
        if (!metadata.ok) throw new Error('Metadata unavailable')
        const record = await metadata.json()
        if (!record || record.slug !== predicted || typeof record.name !== 'string' || !record.name || typeof record.image !== 'string' || !record.image) throw new Error('Invalid metadata')
        if (current !== generation) return
        wine.value = record as Wine
      } catch {
        if (current !== generation) return
        metadataUnavailable.value = true
      }
      if (current === generation) phase.value = 'matched'
    } catch (failure) {
      if (current !== generation) return
      phase.value = 'error'
      error.value = activeController.signal.aborted
        ? 'Время ожидания истекло. Проверьте соединение и повторите поиск.'
        : failure instanceof SyntaxError ? 'Сервис вернул неполный ответ. Попробуйте ещё раз.'
          : failure instanceof TypeError ? 'Не удалось связаться с сервисом. Проверьте соединение.'
          : failure instanceof Error ? failure.message : 'Не удалось отправить фото. Попробуйте ещё раз.'
    } finally {
      clearTimeout(timer)
      if (current === generation) controller = undefined
    }
  }

  async function select(files: File[]) {
    reset()
    const selected = files[0]
    if (files.length !== 1 || !selected) error.value = 'Выберите одну фотографию этикетки.'
    else if (!selected.size) error.value = 'Файл пуст. Выберите другой снимок.'
    else if (selected.size > MAX_IMAGE_BYTES) error.value = 'Выберите фотографию размером до 10 МБ.'
    else if (selected.type && !['image/jpeg', 'image/png', 'image/webp'].includes(selected.type)) error.value = 'Выберите JPEG, PNG или WebP. Сохраните HEIC в формате JPEG.'
    if (error.value) { phase.value = 'error'; return }
    file.value = selected!
    preview.value = createPreview(selected!)
    await submit()
  }

  async function example() {
    reset()
    const current = generation
    const activeController = new AbortController()
    controller = activeController
    const timer = setTimeout(() => activeController.abort(), 5000)
    exampleLoading.value = true
    try {
      const response = await request(`/wines/${MOCK_SLUG}.webp`, { signal: activeController.signal })
      if (!response.ok) throw new Error('Example unavailable')
      const blob = await response.blob()
      if (current !== generation) return
      await select([new File([blob], 'Пример этикетки.webp', { type: 'image/webp' })])
    } catch {
      if (current !== generation) return
      error.value = 'Пример не загрузился. Выберите свою фотографию.'
      phase.value = 'error'
    } finally {
      clearTimeout(timer)
      if (current === generation) { exampleLoading.value = false; controller = undefined }
    }
  }

  onScopeDispose(reset)
  return { file, preview, phase, error, slug, wine, mock, metadataUnavailable, exampleLoading, busy, portalUrl, select, submit, example, reset, cancel }
}
