import type { useWineScanner } from './useWineScanner'

interface Tool {
  name: string
  description: string
  inputSchema: object
  annotations: { readOnlyHint: boolean }
  execute: (input: unknown) => unknown | Promise<unknown>
}

export function useScannerTools(scanner: ReturnType<typeof useWineScanner>) {
  let lifecycle: AbortController | undefined
  const read = () => ({ phase: scanner.phase.value, hasPhoto: Boolean(scanner.file.value), slug: scanner.slug.value || null, title: scanner.wine.value?.name || null, bottle: scanner.wine.value?.image || null, portalUrl: scanner.portalUrl.value || null, mock: scanner.mock.value, error: scanner.error.value || null })
  const validate = (input: unknown) => {
    if (!input || typeof input !== 'object' || Array.isArray(input) || Object.keys(input).length) throw new Error('Provide an empty object.')
  }
  onMounted(() => {
    const context = (document as Document & { modelContext?: { registerTool: (tool: Tool, options: { signal: AbortSignal }) => void | Promise<void> } }).modelContext
    if (!context?.registerTool) return
    lifecycle = new AbortController()
    const tools: Tool[] = [
      { name: 'read_wine_search', description: 'Read the current photo search status and single result. This does not expose photo content.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true }, execute(input) { validate(input); return read() } },
      { name: 'search_demo_wine_photo', description: 'Upload the bundled public example photo to the local mock prediction route and show its single result. This action is available only in mock mode. It replaces any selected photo.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: false }, async execute(input) { validate(input); const config = await $fetch('/api/config'); if (config.predictionMode !== 'mock') throw new Error('The example tool requires mock mode.'); await scanner.example(); await nextTick(); return read() } },
      { name: 'reset_wine_search', description: 'Cancel photo search, discard the selected photo preview, and clear the result.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: false }, async execute(input) { validate(input); scanner.reset(); await nextTick(); return read() } },
    ]
    for (const tool of tools) {
      try { Promise.resolve(context.registerTool(tool, { signal: lifecycle.signal })).catch(() => console.warn(`Could not register scanner tool: ${tool.name}`)) }
      catch { console.warn(`Could not register scanner tool: ${tool.name}`) }
    }
  })
  onBeforeUnmount(() => lifecycle?.abort())
}
