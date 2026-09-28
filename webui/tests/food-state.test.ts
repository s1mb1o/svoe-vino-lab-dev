import { afterEach, describe, expect, it, vi } from 'vitest'
import { effectScope, type EffectScope } from 'vue'
import { useFoodRecommendations } from '../app/composables/useFoodRecommendations'
const scopes: EffectScope[] = []
const value = { provider: 'globus', store: { id: 5020, name: 'Глобус Медведково' }, products: [], complete: false }
function setup(request = vi.fn(), locate = vi.fn(), timeout = 1000) {
  const scope = effectScope(); scopes.push(scope)
  const food = scope.run(() => useFoodRecommendations('wine-slug', { fetch: request as typeof fetch, locate, timeout }))!
  return { food, scope }
}
afterEach(() => scopes.splice(0).forEach(scope => scope.stop()))
describe('food recommendation state', () => {
  it('does not request location or products before an explicit action', () => {
    const request = vi.fn(), locate = vi.fn()
    const { food } = setup(request, locate)
    expect(food.phase.value).toBe('idle')
    expect(request).not.toHaveBeenCalled(); expect(locate).not.toHaveBeenCalled()
  })
  it('uses location only for the explicit nearest store action', async () => {
    const request = vi.fn().mockResolvedValue(Response.json(value))
    const locate = vi.fn().mockResolvedValue({ latitude: 55, longitude: 37 })
    const { food } = setup(request, locate)
    await food.nearby()
    expect(locate).toHaveBeenCalledTimes(1)
    expect(JSON.parse(request.mock.calls[0]![1].body)).toEqual({ slug: 'wine-slug', location: { latitude: 55, longitude: 37 } })
    expect(food.phase.value).toBe('ready')
  })
  it('permits manual selection after location denial', async () => {
    const locate = vi.fn().mockRejectedValue({ code: 1 })
    const request = vi.fn().mockResolvedValueOnce(Response.json({ stores: [{ id: 5020, name: 'Глобус' }] })).mockResolvedValueOnce(Response.json(value))
    const { food } = setup(request, locate)
    await food.nearby()
    expect(food.error.value).toContain('не разрешён')
    expect(request).not.toHaveBeenCalled()
    await food.loadStores()
    await food.recommend({ storeId: 5020 })
    expect(food.phase.value).toBe('ready')
    expect(locate).toHaveBeenCalledTimes(1)
    expect(JSON.parse(request.mock.calls[1]![1].body)).toEqual({ slug: 'wine-slug', storeId: 5020 })
  })
  it('ignores location completion after cancellation', async () => {
    let finish!: (v: object) => void
    const locate = vi.fn(() => new Promise(resolve => { finish = resolve }))
    const request = vi.fn()
    const { food } = setup(request, locate)
    const pending = food.nearby(); food.cancel(); finish({ latitude: 1, longitude: 1 }); await pending
    expect(request).not.toHaveBeenCalled()
    expect(food.phase.value).toBe('idle')
  })
  it('aborts the previous store request and rejects its late result', async () => {
    let finish!: (r: Response) => void
    const request = vi.fn().mockImplementationOnce(() => new Promise(resolve => { finish = resolve })).mockResolvedValueOnce(Response.json({ ...value, store: { id: 5001, name: 'Щёлково' } }))
    const { food } = setup(request)
    const old = food.recommend({ storeId: 5020 })
    await food.recommend({ storeId: 5001 })
    expect(request.mock.calls[0]![1].signal.aborted).toBe(true)
    finish(Response.json(value)); await old
    expect(food.result.value?.store.id).toBe(5001)
  })
  it('aborts on unmount so a new wine cannot receive the old products', async () => {
    let finish!: (r: Response) => void
    const request = vi.fn().mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
    const { food, scope } = setup(request)
    const pending = food.recommend({ storeId: 5020 }); scope.stop()
    expect(request.mock.calls[0]![1].signal.aborted).toBe(true)
    finish(Response.json(value)); await pending
    expect(food.result.value).toBeNull()
  })
  it('shows a retailer error without using sample products', async () => {
    const { food } = setup(vi.fn().mockResolvedValue(Response.json({}, { status: 502 })))
    await food.recommend({ storeId: 5020 })
    expect(food.phase.value).toBe('error'); expect(food.result.value).toBeNull()
    expect(food.error.value).toContain('ассортимент')
  })
  it('ends a stalled request with a retryable error', async () => {
    const request = vi.fn((_url, options) => new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => reject(new Error('timeout')))))
    const { food } = setup(request, vi.fn(), 5)
    await food.recommend({ storeId: 5020 })
    expect(food.phase.value).toBe('error'); expect(food.busy.value).toBe(false)
  })
})
