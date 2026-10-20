import { publicPair, type ComparisonPair } from '#shared/alternatives'
import { DIARY_SLUG_PATTERN } from '#shared/diary'

export const COMPARISON_RETURN = 'chtozavino.comparison-return.v1'
export const SAVED_COMPARISON_RETURN = 'chtozavino.saved-comparison-return.v1'
let opener: HTMLElement | null = null
export function useWineComparison() {
  const pair = useState<ComparisonPair | null>('wine-comparison', () => null)
  const savedBase = useState<string | null>('wine-comparison-saved-base', () => null)
  const active = computed(() => Boolean(pair.value || savedBase.value))
  function begin(element?: HTMLElement) {
    if (!active.value) {
      opener = element || null
      history.pushState({ ...history.state, f04Comparison: true }, '', location.href)
    }
  }
  function open(value: ComparisonPair, element?: HTMLElement) {
    const safe = publicPair(value)
    if (!safe) return
    begin(element)
    pair.value = safe
    savedBase.value = null
  }
  function openSaved(slug: string, element?: HTMLElement) {
    if (!DIARY_SLUG_PATTERN.test(slug)) return
    begin(element)
    savedBase.value = slug
  }
  function cancelSaved() {
    if (pair.value) savedBase.value = null
    else close()
  }
  function close() {
    const wasOpen = active.value
    const target = opener
    pair.value = null
    savedBase.value = null
    if (import.meta.client && wasOpen && history.state?.f04Comparison) history.back()
    if (import.meta.client && target) requestAnimationFrame(() => { if (target.isConnected) target.focus() })
    opener = null
  }
  function remember(value?: ComparisonPair) {
    const safe = publicPair(value ?? pair.value)
    if (!safe) return false
    try { sessionStorage.removeItem(SAVED_COMPARISON_RETURN); sessionStorage.setItem(COMPARISON_RETURN, JSON.stringify(safe)); return true } catch { return false }
  }
  function rememberSaved() {
    if (!savedBase.value) return false
    try { sessionStorage.removeItem(COMPARISON_RETURN); sessionStorage.setItem(SAVED_COMPARISON_RETURN, savedBase.value); return true } catch { return false }
  }
  function takeSavedReturn() {
    try {
      const slug = sessionStorage.getItem(SAVED_COMPARISON_RETURN)
      sessionStorage.removeItem(SAVED_COMPARISON_RETURN)
      return slug && DIARY_SLUG_PATTERN.test(slug) ? slug : null
    } catch { return null }
  }
  function takeReturn() {
    try {
      const text = sessionStorage.getItem(COMPARISON_RETURN)
      sessionStorage.removeItem(COMPARISON_RETURN)
      return text && text.length < 40000 ? publicPair(JSON.parse(text)) : null
    } catch { return null }
  }
  return { pair, savedBase, active, open, openSaved, cancelSaved, close, remember, rememberSaved, takeReturn, takeSavedReturn }
}
