import { computed, onScopeDispose, ref, shallowRef } from 'vue'
import type { FoodResult, FoodSelection, FoodStore, Location } from '#shared/food'

type Phase = 'idle' | 'locating' | 'stores' | 'loading' | 'ready' | 'error'
interface Dependencies {
  fetch?: typeof fetch
  locate?: () => Promise<Location>
  timeout?: number
}
export function browserLocation(): Promise<Location> {
  return new Promise((resolve, reject) => {
    if (!globalThis.isSecureContext || !navigator.geolocation) { reject(new Error('unavailable')); return }
    navigator.geolocation.getCurrentPosition(
      position => resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude }),
      reject, { enableHighAccuracy: false, maximumAge: 60000, timeout: 10000 },
    )
  })
}

export function useFoodRecommendations(slug: string, dependencies: Dependencies = {}) {
  const request = dependencies.fetch || globalThis.fetch
  const locate = dependencies.locate || browserLocation
  const phase = ref<Phase>('idle')
  const error = ref('')
  const result = shallowRef<FoodResult | null>(null)
  const stores = shallowRef<FoodStore[]>([])
  const loadingStores = ref(false)
  const busy = computed(() => phase.value === 'locating' || phase.value === 'loading' || loadingStores.value)
  let generation = 0
  let controller: AbortController | undefined
  function cancel() {
    generation++
    controller?.abort()
    controller = undefined
    loadingStores.value = false
    phase.value = result.value ? 'ready' : 'idle'
    error.value = ''
  }
  async function recommend(selection: FoodSelection) {
    cancel()
    result.value = null
    const current = generation
    controller = new AbortController()
    const abort = controller
    const timer = setTimeout(() => abort.abort(), dependencies.timeout ?? 25000)
    phase.value = 'loading'
    try {
      const response = await request('/api/food/pairings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ slug, ...selection }), signal: abort.signal })
      if (!response.ok) throw new Error(response.status === 422 ? 'wine' : 'store')
      const value = await response.json() as FoodResult
      if (value.provider !== 'globus' || !value.store?.name || !Array.isArray(value.products) || value.products.length > 3) throw new Error('store')
      if (generation !== current) return
      result.value = value
      phase.value = 'ready'
    } catch (failure) {
      if (generation !== current) return
      error.value = failure instanceof Error && failure.message === 'wine'
        ? 'Для этого вина пока нет описания. Подбор продуктов станет доступен вместе с карточкой.'
        : 'Не удалось получить ассортимент «Глобуса». Попробуйте ещё раз или выберите другой магазин.'
      phase.value = 'error'
    } finally { clearTimeout(timer); if (generation === current) controller = undefined }
  }
  async function nearby() {
    cancel()
    result.value = null
    const current = generation
    phase.value = 'locating'
    try {
      const location = await locate()
      if (generation !== current) return
      await recommend({ location })
    } catch (failure) {
      if (generation !== current) return
      error.value = (failure as { code?: number })?.code === 1
        ? 'Доступ к геолокации не разрешён. Выберите магазин вручную.'
        : 'Не удалось определить местоположение. Выберите магазин вручную.'
      phase.value = 'error'
    }
  }
  async function loadStores() {
    cancel()
    phase.value = 'stores'
    if (stores.value.length) return stores.value
    loadingStores.value = true
    const current = generation
    controller = new AbortController()
    const abort = controller
    const timer = setTimeout(() => abort.abort(), dependencies.timeout ?? 10000)
    try {
      const response = await request('/api/food/stores', { signal: abort.signal })
      if (!response.ok) throw new Error('stores')
      const value = await response.json()
      if (!Array.isArray(value.stores) || !value.stores.length) throw new Error('stores')
      if (current !== generation) return []
      stores.value = value.stores
      return stores.value
    } catch {
      if (current === generation) { error.value = 'Список магазинов пока недоступен. Попробуйте ещё раз.'; phase.value = 'error' }
      return []
    } finally { clearTimeout(timer); if (current === generation) { loadingStores.value = false; controller = undefined } }
  }
  onScopeDispose(cancel)
  return { phase, error, result, stores, loadingStores, busy, nearby, recommend, loadStores, cancel }
}
