import { publicPair, type ComparisonPair } from '#shared/alternatives'

export const COMPARISON_RETURN = 'chtozavino.comparison-return.v1'
let opener: HTMLElement | null = null
export function useWineComparison() {
  const pair = useState<ComparisonPair | null>('wine-comparison', () => null)
  function open(value: ComparisonPair, element?: HTMLElement) {
    const safe = publicPair(value)
    if (!safe) return
    opener = element || null
    if (!pair.value) history.pushState({ ...history.state, f04Comparison: true }, '', location.href)
    pair.value = safe
  }
  function close() {
    const wasOpen = Boolean(pair.value)
    const target = opener
    pair.value = null
    if (import.meta.client && wasOpen && history.state?.f04Comparison) history.back()
    if (import.meta.client && target) requestAnimationFrame(() => { if (target.isConnected) target.focus() })
    opener = null
  }
  function remember(value?: ComparisonPair) {
    const safe = publicPair(value ?? pair.value)
    if (!safe) return false
    try { sessionStorage.setItem(COMPARISON_RETURN, JSON.stringify(safe)); return true } catch { return false }
  }
  function takeReturn() {
    try {
      const text = sessionStorage.getItem(COMPARISON_RETURN)
      sessionStorage.removeItem(COMPARISON_RETURN)
      return text && text.length < 40000 ? publicPair(JSON.parse(text)) : null
    } catch { return null }
  }
  return { pair, open, close, remember, takeReturn }
}
