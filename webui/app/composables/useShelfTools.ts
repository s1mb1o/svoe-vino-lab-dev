import type { useShelfScanner } from './useShelfScanner'

export function useShelfTools(scanner: ReturnType<typeof useShelfScanner>) {
  let lifecycle: AbortController | undefined
  const read = () => ({
    phase: scanner.phase.value,
    hasPhoto: Boolean(scanner.file.value),
    bottles: scanner.result.value?.bottles.map(bottle => ({ id: bottle.id, box: bottle.box, matched: Boolean(bottle.match) })) || [],
    detectedCount: scanner.result.value?.detected_count || 0,
    truncated: scanner.result.value?.truncated || false,
    selectedId: scanner.selectedId.value || null,
    winePhase: scanner.selectedId.value ? 'matched' : 'idle',
    title: scanner.selectedWine.value?.name || null,
    slug: scanner.selectedMatch.value?.slug || null,
    portalUrl: scanner.portalUrl.value || null,
    mockRecognition: false,
    error: scanner.error.value || null,
  })
  const empty = (input: unknown) => { if (!input || typeof input !== 'object' || Array.isArray(input) || Object.keys(input).length) throw new Error('Provide an empty object.') }
  onMounted(() => {
    const context = (document as Document & { modelContext?: { registerTool: (tool: object, options: { signal: AbortSignal }) => void | Promise<void> } }).modelContext
    if (!context?.registerTool) return
    lifecycle = new AbortController()
    const tools = [
      { name: 'read_shelf_search', description: 'Read shelf group-match and selected wine state without exposing photo or mask content.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true }, execute(input: unknown) { empty(input); return read() } },
      { name: 'segment_example_wine_shelf', description: 'Replace the selected shelf with the first bundled owner-supplied example and match all detected bottles through the configured matcher.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: false }, async execute(input: unknown) { empty(input); await scanner.example(); await nextTick(); return read() } },
      { name: 'open_shelf_wine', description: 'Open the ready match for a detected bottle ID. This action does not send another recognition request.', inputSchema: { type: 'object', properties: { bottleId: { type: 'string' } }, required: ['bottleId'], additionalProperties: false }, annotations: { readOnlyHint: false }, async execute(input: unknown) {
        const value = input as { bottleId?: string }
        if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).some(k => k !== 'bottleId') || typeof value.bottleId !== 'string') throw new Error('Provide one bottleId.')
        scanner.selectBottle(value.bottleId); await nextTick(); return read()
      } },
      { name: 'close_shelf_wine', description: 'Close the selected wine popup. Keep the matched shelf.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: false }, async execute(input: unknown) { empty(input); scanner.closeBottle(); await nextTick(); return read() } },
      { name: 'reset_shelf_search', description: 'Cancel shelf processing. Discard the photo, masks, matches, and popup.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: false }, async execute(input: unknown) { empty(input); scanner.reset(); await nextTick(); return read() } },
    ]
    for (const tool of tools) {
      try { Promise.resolve(context.registerTool(tool, { signal: lifecycle.signal })).catch(() => console.warn(`Could not register shelf tool: ${tool.name}`)) }
      catch { console.warn(`Could not register shelf tool: ${tool.name}`) }
    }
  })
  onBeforeUnmount(() => lifecycle?.abort())
}
