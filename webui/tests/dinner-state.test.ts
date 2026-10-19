import { afterEach, describe, expect, it, vi } from 'vitest'
import { effectScope, type EffectScope } from 'vue'
import { prepareDishPhoto, useDinnerLens } from '../app/composables/useDinnerLens'
import { dinnerPage, dinnerWine } from './support/dinner'
const scopes: EffectScope[] = []
const photo = () => new File(['fixture'], 'food.jpg', { type: 'image/jpeg' })
const reply = (value = dinnerPage()) => Response.json(value)
function setup(request: ReturnType<typeof vi.fn>, timeout = 2000) {
  const scope = effectScope(); scopes.push(scope)
  const prepare = vi.fn().mockResolvedValue('data:image/jpeg;base64,YWJj')
  const lens = scope.run(() => useDinnerLens({ fetch: request, prepare, timeout }))!
  return { lens, scope, prepare }
}
afterEach(() => scopes.splice(0).forEach(scope => scope.stop()))

describe('dish confirmation and wine pagination', () => {
  it('hides photo wines until the user confirms and never repeats vision on confirmation', async () => {
    const request = vi.fn().mockResolvedValueOnce(reply()).mockResolvedValueOnce(reply())
    const { lens, prepare } = setup(request)
    await lens.select([photo()])
    expect(lens.phase.value).toBe('confirm'); expect(lens.wines.value).toEqual([])
    expect(lens.dish.value).toBe('Стейк рибай на гриле')
    await lens.recommend({ node_id: 'ribeye_grilled', confirmed_attributes: { fatty_cream_sauce: false } })
    expect(request.mock.calls.map(call => call[0])).toEqual(['/api/dinner/recognize', '/api/dinner/recommendations'])
    expect(prepare).toHaveBeenCalledTimes(1)
    expect(lens.wines.value).toHaveLength(3)
  })
  it('appends real continuation pages with the original opaque cursor', async () => {
    const request = vi.fn().mockResolvedValueOnce(reply()).mockResolvedValueOnce(reply(dinnerPage({ results: [4, 5, 6].map(dinnerWine), shown_count: 6, next_cursor: null })))
    const { lens } = setup(request)
    await lens.recommend({ node_id: 'ribeye_grilled' }); await lens.more()
    expect(lens.wines.value).toHaveLength(6)
    expect(JSON.parse(request.mock.calls[1]![1].body)).toEqual({ cursor: 'fixture-first-cursor' })
    expect(lens.page.value?.next_cursor).toBeNull()
  })
  it('keeps previous cards on continuation failure and supports retry', async () => {
    const request = vi.fn().mockResolvedValueOnce(reply()).mockResolvedValueOnce(new Response('', { status: 503 }))
      .mockResolvedValueOnce(reply(dinnerPage({ results: [4, 5, 6].map(dinnerWine), shown_count: 6, next_cursor: null })))
    const { lens } = setup(request)
    await lens.recommend({ node_id: 'ribeye_grilled' }); await lens.more()
    expect(lens.wines.value).toHaveLength(3); expect(lens.error.value).toContain('недоступен')
    await lens.more(); expect(lens.wines.value).toHaveLength(6); expect(lens.error.value).toBe('')
  })
  it('rejects duplicate or changed-context continuation without losing cards', async () => {
    const request = vi.fn().mockResolvedValueOnce(reply()).mockResolvedValueOnce(reply(dinnerPage({ shown_count: 6, next_cursor: null })))
    const { lens } = setup(request)
    await lens.recommend({ node_id: 'ribeye_grilled' }); await lens.more()
    expect(lens.wines.value).toHaveLength(3); expect(lens.error.value).toContain('устарело')
  })
  it('suppresses a late result after a dish or sauce change', async () => {
    let finish!: (response: Response) => void
    const request = vi.fn().mockImplementationOnce(() => new Promise(resolve => { finish = resolve })).mockResolvedValueOnce(reply())
    const { lens } = setup(request)
    const first = lens.recommend({ node_id: 'ribeye_grilled' })
    const signal = request.mock.calls[0]![1].signal
    lens.invalidate(); expect(signal.aborted).toBe(true)
    finish(reply()); await first
    expect(lens.wines.value).toEqual([])
    await lens.recommend({ node_id: 'ribeye_grilled', confirmed_attributes: { heat: 'high' } })
    expect(lens.wines.value).toHaveLength(3)
  })
  it('cancels the previous photo and discards results after a mode change', async () => {
    let finish!: (response: Response) => void
    const request = vi.fn().mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
    const { lens, scope } = setup(request)
    const first = lens.select([photo()]); await vi.waitFor(() => expect(request).toHaveBeenCalledTimes(1))
    const signal = request.mock.calls[0]![1].signal; scope.stop()
    expect(signal.aborted).toBe(true)
    finish(reply()); await first
    expect(lens.wines.value).toEqual([]); expect(lens.dish.value).toBe('')
  })
  it('offers category selection for an unknown dish without inventing results', async () => {
    const request = vi.fn().mockResolvedValue(Response.json({ status: 'needs_category', resolved_node_id: null, results: [], needs_clarification: true, clarification_question: 'Выберите категорию блюда.' }))
    const { lens } = setup(request)
    await lens.recommend({ confirmed_dish: 'Unknown fixture dish' })
    expect(lens.phase.value).toBe('confirm'); expect(lens.wines.value).toEqual([]); expect(lens.question.value).toContain('категорию')
  })
  it('does not turn an unavailable service into a mock success', async () => {
    const { lens } = setup(vi.fn().mockResolvedValue(new Response('', { status: 503 })))
    await lens.recommend({ node_id: 'ribeye_grilled' })
    expect(lens.wines.value).toEqual([]); expect(lens.error.value).toContain('недоступен')
  })
  it('rejects unsupported images before browser decode or provider work', async () => {
    await expect(prepareDishPhoto(new File(['fixture'], 'food.svg', { type: 'image/svg+xml' }))).rejects.toThrow('JPEG')
    await expect(prepareDishPhoto(new File([], 'empty.jpg', { type: 'image/jpeg' }))).rejects.toThrow('10 МБ')
    const request = vi.fn(); const { lens } = setup(request)
    await lens.select([photo(), photo()]); expect(request).not.toHaveBeenCalled()
  })
})
