import type { useShelfScanner } from './useShelfScanner'

export function useShelfTools(scanner: ReturnType<typeof useShelfScanner>) {
  let lifecycle: AbortController | undefined
  const read = () => ({ phase: scanner.phase.value, hasPhoto: Boolean(scanner.file.value), bottles: scanner.result.value?.bottles.map(b => ({ id: b.id, box: b.box })) || [], truncated: scanner.result.value?.truncated || false, selectedId: scanner.selectedId.value || null, winePhase: scanner.wineScanner.phase.value, title: scanner.wineScanner.wine.value?.name || null, slug: scanner.wineScanner.slug.value || null, portalUrl: scanner.wineScanner.portalUrl.value || null, mockRecognition: scanner.wineScanner.mock.value, error: scanner.error.value || scanner.wineScanner.error.value || null })
  const empty = (input: unknown) => { if (!input || typeof input !== 'object' || Array.isArray(input) || Object.keys(input).length) throw new Error('Provide an empty object.') }
  onMounted(() => {
    const context = (document as Document & { modelContext?: { registerTool: (tool: object, options: { signal: AbortSignal }) => void | Promise<void> } }).modelContext
    if (!context?.registerTool) return
    lifecycle = new AbortController()
    const tools = [
      { name: 'read_shelf_search', description: 'Read shelf segmentation and selected wine state without exposing photo, mask, or crop content.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true }, execute(input: unknown) { empty(input); return read() } },
      { name: 'segment_example_wine_shelf', description: 'Replace the selected shelf with the bundled public Wikimedia example and segment bottles through our portal and its configured SAM3 service. Does not upload a private photo or identify wine names until a bottle is selected.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: false }, async execute(input: unknown) { empty(input); await scanner.example(); await nextTick(); return read() } },
      { name: 'open_shelf_wine', description: 'Open the popup for a detected bottle ID and recognize its server-produced crop through our portal prediction API.', inputSchema: { type: 'object', properties: { bottleId: { type: 'string' } }, required: ['bottleId'], additionalProperties: false }, annotations: { readOnlyHint: false }, async execute(input: unknown) {
        const value = input as { bottleId?: string }
        if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).some(k => k !== 'bottleId') || typeof value.bottleId !== 'string') throw new Error('Provide one bottleId.')
        await scanner.selectBottle(value.bottleId); await nextTick(); return read()
      } },
      { name: 'close_shelf_wine', description: 'Close the selected wine popup and cancel its recognition. Keep the segmented shelf.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: false }, async execute(input: unknown) { empty(input); scanner.closeBottle(); await nextTick(); return read() } },
      { name: 'reset_shelf_search', description: 'Cancel shelf processing and wine recognition. Discard the photo, crops, masks, and popup.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: false }, async execute(input: unknown) { empty(input); scanner.reset(); await nextTick(); return read() } },
    ]
    for (const tool of tools) {
      try { Promise.resolve(context.registerTool(tool, { signal: lifecycle.signal })).catch(() => console.warn(`Could not register shelf tool: ${tool.name}`)) }
      catch { console.warn(`Could not register shelf tool: ${tool.name}`) }
    }
  })
  onBeforeUnmount(() => lifecycle?.abort())
}
