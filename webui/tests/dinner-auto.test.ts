import { afterEach, describe, expect, it, vi } from 'vitest'
import { effectScope, ref, type EffectScope } from 'vue'
import { useDinnerLens } from '../app/composables/useDinnerLens'
import { useDinnerAutoRecommendations } from '../app/composables/useDinnerAutoRecommendations'
import { dinnerPage, dinnerWine } from './support/dinner'
import type { DinnerSelection } from '../shared/dinner'

const scopes: EffectScope[] = []
function setup(request = vi.fn().mockResolvedValue(Response.json(dinnerPage()))) {
  const scope = effectScope(); scopes.push(scope)
  const selection = ref<DinnerSelection | null>({ node_id: 'ribeye_grilled', confirmed_attributes: {} })
  const available = ref(true)
  const onResult = vi.fn()
  return scope.run(() => {
    const scanner = useDinnerLens({ fetch: request, prepare: async () => 'data:image/jpeg;base64,YWJj' })
    scanner.dish.value = 'Стейк рибай на гриле'
    const auto = useDinnerAutoRecommendations({ scanner, available: () => available.value, selection: () => selection.value, onResult })
    return { scanner, auto, selection, available, onResult, request, scope }
  })!
}
afterEach(() => { scopes.splice(0).forEach(scope => scope.stop()); vi.useRealTimers() })

describe('automatic dinner recommendations', () => {
  it('coalesces typed edits and uses only the latest name after the pause', async () => {
    vi.useFakeTimers()
    const { auto, selection, request } = setup()
    selection.value = { confirmed_dish: 'First fixture' }; auto.refresh(450)
    await vi.advanceTimersByTimeAsync(300)
    selection.value = { confirmed_dish: 'Latest fixture' }; auto.refresh(450)
    await vi.advanceTimersByTimeAsync(449); expect(request).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1)
    expect(request).toHaveBeenCalledTimes(1)
    expect(JSON.parse(request.mock.calls[0]![1].body)).toMatchObject({ confirmed_dish: 'Latest fixture' })
  })
  it('replaces a pending typed request with an immediate explicit selection and current sauce', async () => {
    vi.useFakeTimers()
    const { auto, selection, request } = setup()
    auto.refresh(450)
    selection.value = { node_id: 'meat_steak', confirmed_attributes: { heat: 'high', fatty_cream_sauce: true } }
    await auto.refresh()
    await vi.advanceTimersByTimeAsync(1000)
    expect(request).toHaveBeenCalledTimes(1)
    expect(JSON.parse(request.mock.calls[0]![1].body)).toMatchObject(selection.value!)
  })
  it('aborts a superseded request and ignores its late response and notification', async () => {
    let release!: (value: Response) => void
    const request = vi.fn().mockImplementationOnce(() => new Promise(resolve => { release = resolve }))
      .mockResolvedValueOnce(Response.json(dinnerPage({ results: [7, 8, 9].map(dinnerWine) })))
    const { auto, selection, scanner, onResult } = setup(request)
    const old = auto.refresh(); const signal = request.mock.calls[0]![1].signal
    selection.value = { node_id: 'ribeye_grilled', confirmed_attributes: { heat: 'high' } }
    await auto.refresh(); expect(signal.aborted).toBe(true)
    release(Response.json(dinnerPage())); await old
    expect(scanner.wines.value.map(wine => wine.wine_slug)).toEqual([7, 8, 9].map(n => dinnerWine(n).wine_slug))
    expect(onResult).toHaveBeenCalledTimes(1)
  })
  it('keeps recognition running during taste edits and uses their latest values afterwards', async () => {
    let release!: (value: Response) => void
    const request = vi.fn().mockImplementationOnce(() => new Promise(resolve => { release = resolve }))
      .mockResolvedValueOnce(Response.json(dinnerPage()))
    const { scanner, auto, selection } = setup(request)
    const photo = scanner.select([new File(['fixture'], 'food.jpg', { type: 'image/jpeg' })])
    await vi.waitFor(() => expect(request).toHaveBeenCalledTimes(1))
    selection.value = { node_id: 'ribeye_grilled', confirmed_attributes: { heat: 'high' } }
    await auto.refresh()
    expect(request.mock.calls[0]![1].signal.aborted).toBe(false)
    release(Response.json(dinnerPage())); await photo; await auto.refresh()
    expect(request.mock.calls.map(call => call[0])).toEqual(['/api/dinner/recognize', '/api/dinner/recommendations'])
    expect(JSON.parse(request.mock.calls[1]![1].body).confirmed_attributes).toEqual({ heat: 'high' })
    expect(scanner.wines.value).toHaveLength(3)
  })
  it('clears results and cancels delayed work when the dish becomes empty', async () => {
    vi.useFakeTimers()
    const { auto, scanner, selection, request } = setup()
    await auto.refresh(); expect(scanner.wines.value).toHaveLength(3)
    auto.refresh(450); selection.value = null; auto.refresh(450)
    await vi.advanceTimersByTimeAsync(1000)
    expect(request).toHaveBeenCalledTimes(1); expect(scanner.wines.value).toEqual([])
  })
  it('stops pending work on cancel or route disposal and resumes only on another edit', async () => {
    vi.useFakeTimers()
    const { auto, request, scope } = setup()
    auto.refresh(450); auto.stop(); await vi.advanceTimersByTimeAsync(1000)
    expect(request).not.toHaveBeenCalled()
    await auto.refresh(); expect(request).toHaveBeenCalledTimes(1)
    auto.refresh(450); scope.stop(); await vi.advanceTimersByTimeAsync(1000)
    expect(request).toHaveBeenCalledTimes(1)
  })
  it('does not request wines when unavailable or when recognition could not resolve a dish', async () => {
    const { auto, selection, available, request } = setup()
    available.value = false; await auto.refresh()
    expect(request).not.toHaveBeenCalled()
    selection.value = null; available.value = true; await auto.refresh()
    expect(request).not.toHaveBeenCalled()
  })
})
