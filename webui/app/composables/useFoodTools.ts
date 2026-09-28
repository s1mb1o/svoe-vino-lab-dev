import type { useFoodRecommendations } from './useFoodRecommendations'

export function useFoodTools(food: ReturnType<typeof useFoodRecommendations>) {
  let lifecycle: AbortController | undefined
  const read = () => ({ phase: food.phase.value, error: food.error.value || null, result: food.result.value })
  const empty = (input: unknown) => { if (!input || typeof input !== 'object' || Array.isArray(input) || Object.keys(input).length) throw new Error('Provide an empty object.') }
  onMounted(() => {
    const context = (document as Document & { modelContext?: { registerTool: (tool: object, options: { signal: AbortSignal }) => void | Promise<void> } }).modelContext
    if (!context?.registerTool) return
    lifecycle = new AbortController()
    const tools = [
      { name: 'read_wine_food_pairings', description: 'Read the food recommendation state for the matched wine. This does not request location or query the retailer.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true }, execute(input: unknown) { empty(input); return read() } },
      { name: 'list_wine_food_stores', description: 'Read the live Globus store directory for manual selection. This does not request location.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true }, async execute(input: unknown) { empty(input); const value = await $fetch('/api/food/stores'); return value } },
      { name: 'recommend_wine_food_at_store', description: 'Recommend up to three available food products for the matched wine at one explicitly selected Globus store. Queries the live retailer without location, login, cart, or purchase.', inputSchema: { type: 'object', properties: { storeId: { type: 'integer', minimum: 1 } }, required: ['storeId'], additionalProperties: false }, annotations: { readOnlyHint: false }, async execute(input: unknown) {
        const value = input as { storeId?: number }
        if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).some(key => key !== 'storeId') || !Number.isInteger(value.storeId) || value.storeId! <= 0) throw new Error('Provide one positive integer storeId.')
        await food.recommend({ storeId: value.storeId! }); await nextTick(); return read()
      } },
    ]
    for (const tool of tools) {
      try { Promise.resolve(context.registerTool(tool, { signal: lifecycle.signal })).catch(() => console.warn(`Could not register food tool: ${tool.name}`)) }
      catch { console.warn(`Could not register food tool: ${tool.name}`) }
    }
  })
  onBeforeUnmount(() => lifecycle?.abort())
}
