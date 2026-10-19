import { onScopeDispose, watch } from 'vue'
import type { DinnerPage, DinnerSelection } from '#shared/dinner'
import type { useDinnerLens } from './useDinnerLens'

type Scanner = Pick<ReturnType<typeof useDinnerLens>, 'phase' | 'page' | 'recommend' | 'invalidate' | 'cancel'>

export function useDinnerAutoRecommendations(options: {
  scanner: Scanner
  available: () => boolean
  selection: () => DinnerSelection | null
  onResult?: (page: DinnerPage) => void | Promise<void>
}) {
  let timer: ReturnType<typeof setTimeout> | undefined
  let version = 0
  function cancelPending() { version++; clearTimeout(timer); timer = undefined }
  async function run(current: number) {
    if (current !== version || !options.available() || options.scanner.phase.value === 'recognizing') return
    const selection = options.selection()
    if (!selection) return
    await options.scanner.recommend(selection)
    const page = options.scanner.page.value
    if (current === version && page) await options.onResult?.(page)
  }
  function refresh(delay = 0) {
    cancelPending()
    // Taste edits must not interrupt image recognition. Its completion uses the latest settings.
    if (options.scanner.phase.value === 'recognizing') return
    options.scanner.invalidate()
    if (!options.available() || !options.selection()) return
    const current = version
    if (delay) timer = setTimeout(() => { timer = undefined; void run(current) }, delay)
    else return run(current)
  }
  function stop() { cancelPending(); options.scanner.cancel() }
  watch(options.available, available => { if (available) void refresh(); else stop() })
  onScopeDispose(stop)
  return { refresh, cancelPending, stop }
}
