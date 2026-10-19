// «Винный дневник» on the pages outside /account: the pins of saved wines and the history records.
// Plan: docs/plans/07_diary-history-and-saved.md. The header makes no account call: the first pin on
// a page loads the saved slugs once, and all pins of the page share that state.
import { DEFAULT_SAVED_STATUS, type HistoryRecordStatus, type SavedSource, type SavedStatus } from '#shared/diary'
import { AccountRequestError, useAccountApi } from '~/composables/useAccountApi'

// unknown: nothing loaded yet; in: logged in; out: logged out (the pin offers the login);
// off: the diary is off or unavailable (no pins).
export type DiaryState = 'unknown' | 'loading' | 'in' | 'out' | 'off'

export interface HistoryRecord { slug: string; status: HistoryRecordStatus; metOn?: string }

let loading: Promise<void> | null = null

export function useDiary() {
  const api = useAccountApi()
  const state = useState<DiaryState>('diary-state', () => 'unknown')
  const saved = useState<Record<string, SavedStatus>>('diary-saved', () => ({}))

  function load(force = false): Promise<void> {
    if (import.meta.server) return Promise.resolve()
    if (!force && state.value !== 'unknown') return loading ?? Promise.resolve()
    state.value = 'loading'
    loading = api.savedSlugs().then(answer => {
      saved.value = Object.fromEntries(answer.items.map(item => [item.slug, item.status]))
      state.value = 'in'
    }).catch((error: unknown) => {
      saved.value = {}
      state.value = error instanceof AccountRequestError && error.status === 401 ? 'out' : 'off'
    }).finally(() => { loading = null })
    return loading
  }

  /** Saves a wine with the default status, or sets another status. Throws AccountRequestError. */
  async function save(slug: string, source: SavedSource, status: SavedStatus = DEFAULT_SAVED_STATUS) {
    const change = slug in saved.value
    const item = await api.putSaved(slug, status, source, change)
    saved.value = { ...saved.value, [slug]: item.status }
    return item
  }

  async function unsave(slug: string) {
    try {
      await api.deleteSaved(slug)
    } catch (error) {
      if (!(error instanceof AccountRequestError && error.status === 404)) throw error
    }
    const next = { ...saved.value }
    delete next[slug]
    saved.value = next
  }

  /** Keeps the shared state equal to a list that the account page loaded. */
  function setSaved(slug: string, status: SavedStatus | null) {
    const next = { ...saved.value }
    if (status) next[slug] = status
    else delete next[slug]
    saved.value = next
  }

  /**
   * Records a found wine in the history, in the background. A logged-out person, mock mode, and
   * every failure give null: the search result never depends on the diary.
   */
  async function recordHistory(slug: string, source: 'photo' | 'shelf'): Promise<HistoryRecord | null> {
    if (import.meta.server || state.value === 'off') return null
    try {
      const answer = await api.recordHistory(slug, source)
      if (state.value === 'out' || state.value === 'unknown') load(true)
      return { slug, status: answer.status, metOn: answer.metOn }
    } catch (error) {
      if (error instanceof AccountRequestError && error.status === 401 && state.value === 'unknown') {
        state.value = 'out'
        saved.value = {}
      }
      return null
    }
  }

  async function undoHistory(record: HistoryRecord) {
    if (!record.metOn) return
    await api.deleteHistoryDay(record.slug, record.metOn)
  }

  return { state, saved, load, save, unsave, setSaved, recordHistory, undoHistory }
}
