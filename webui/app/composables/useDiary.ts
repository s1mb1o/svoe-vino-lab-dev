// «Винный дневник» on the pages outside /account: the pins of saved wines and the history records.
// Plan: docs/plans/07_diary-history-and-saved.md. The header makes no account call: the first pin on
// a page loads the saved slugs once, and all pins of the page share that state.
import { DEFAULT_SAVED_STATUS, type HistoryRecordStatus, type SavedSource, type SavedStatus } from '#shared/diary'
import { AccountRequestError, useAccountApi } from '~/composables/useAccountApi'

// unknown: nothing loaded yet; in: logged in; out: logged out (the pin offers the login);
// off: the diary is off on this site (no pins); error: the service did not answer (no pins; the
// next pin or record tries again).
export type DiaryState = 'unknown' | 'loading' | 'in' | 'out' | 'off' | 'error'

export interface HistoryRecord { slug: string; status: HistoryRecordStatus; metOn?: string }

let loading: Promise<void> | null = null
let generation = 0
let loadGeneration = 0

export function useDiary() {
  const api = useAccountApi()
  const offline = useOfflineCards()
  const state = useState<DiaryState>('diary-state', () => 'unknown')
  const saved = useState<Record<string, SavedStatus>>('diary-saved', () => ({}))
  const owner = useState('diary-owner', () => '')

  function load(force = false): Promise<void> {
    if (import.meta.server) return Promise.resolve()
    if (!force && state.value !== 'unknown' && state.value !== 'error') return loading ?? Promise.resolve()
    state.value = 'loading'
    const gen = generation
    const loadGen = ++loadGeneration
    loading = Promise.all([api.savedSlugs(), api.me()]).then(async ([answer, me]) => {
      if (gen !== generation || loadGen !== loadGeneration) return
      if (owner.value && owner.value !== me.user.id) {
        reset()
        return load(true)
      }
      owner.value = me.user.id
      // Offline storage failure must not disable a working online diary.
      try { await offline.setOwner(me.user.id) } catch { offline.error.value = 'Копии на устройстве недоступны.' }
      if (gen !== generation || loadGen !== loadGeneration) return
      saved.value = Object.fromEntries(answer.items.map(item => [item.slug, item.status]))
      state.value = 'in'
    }).catch((error: unknown) => {
      if (gen !== generation || loadGen !== loadGeneration) return
      saved.value = {}
      const status = error instanceof AccountRequestError ? error.status : 0
      state.value = status === 401 ? 'out' : status === 404 && error instanceof AccountRequestError && error.body.error === 'account_disabled' ? 'off' : 'error'
      if (state.value === 'out' || state.value === 'off') void offline.clear()
    }).finally(() => { if (gen === generation && loadGen === loadGeneration) loading = null })
    return loading
  }

  /** Saves a wine with the default status, or sets another status. Throws AccountRequestError. */
  async function save(slug: string, source: SavedSource, status: SavedStatus = DEFAULT_SAVED_STATUS) {
    const gen = generation
    const change = slug in saved.value
    let item
    try { item = await api.putSaved(slug, status, source, change) }
    catch (error) {
      if (gen === generation && error instanceof AccountRequestError && error.status === 401) { reset(); state.value = 'out' }
      throw error
    }
    if (gen !== generation) throw new AccountRequestError(409, { error: 'session_invalid' })
    saved.value = { ...saved.value, [slug]: item.status }
    return item
  }

  async function unsave(slug: string) {
    const gen = generation
    try {
      await api.deleteSaved(slug)
    } catch (error) {
      if (gen === generation && error instanceof AccountRequestError && error.status === 401) { reset(); state.value = 'out' }
      if (!(error instanceof AccountRequestError && error.status === 404)) throw error
    }
    if (gen !== generation) return
    const next = { ...saved.value }
    delete next[slug]
    saved.value = next
    try { await offline.remove(slug) } catch { offline.error.value = 'Не удалось убрать копию на устройстве.' }
  }

  /** Forgets the state after a login, a logout, or an account deletion. */
  function reset() {
    generation++
    loading = null
    state.value = 'unknown'
    saved.value = {}
    owner.value = ''
    if (import.meta.client) void offline.clear()
  }

  /** Keeps the shared state equal to a list that the account page loaded. */
  function setSaved(slug: string, status: SavedStatus | null) {
    const next = { ...saved.value }
    if (status) next[slug] = status
    else delete next[slug]
    saved.value = next
    if (!status && import.meta.client) void offline.remove(slug).catch(() => { offline.error.value = 'Не удалось убрать копию на устройстве.' })
  }

  /**
   * Records a found wine in the history, in the background. A logged-out person, mock mode, and
   * every failure give null: the search result never depends on the diary.
   */
  async function recordHistory(slug: string, source: 'photo' | 'shelf'): Promise<HistoryRecord | null> {
    if (import.meta.server || state.value === 'off') return null
    try {
      const answer = await api.recordHistory(slug, source)
      if (state.value !== 'in' && state.value !== 'loading') load(true)
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

  return { state, saved, load, reset, save, unsave, setSaved, recordHistory, undoHistory }
}
