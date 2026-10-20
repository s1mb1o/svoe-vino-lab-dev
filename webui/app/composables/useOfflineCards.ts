import { createOfflineStore, makeOfflineCard, OFFLINE_REVOKED, type OfflineCard, type OfflineSession } from '#shared/offline-cards'
import type { Wine } from '#shared/catalog'

let store: ReturnType<typeof createOfflineStore> | undefined
let generation = 0
let channel: BroadcastChannel | undefined
const storage = () => store ??= createOfflineStore(globalThis.indexedDB)

export function useOfflineCards() {
  const cards = useState<OfflineCard[]>('offline-cards', () => [])
  const session = useState<OfflineSession | null>('offline-owner', () => null)
  const error = useState('offline-error', () => '')
  if (import.meta.client && !channel && typeof BroadcastChannel !== 'undefined') {
    channel = new BroadcastChannel('chtozavino-offline')
    channel.onmessage = event => {
      if (event.data === 'clear') { generation++; cards.value = []; session.value = null }
      else if (session.value) void refresh().catch(() => {})
    }
  }
  async function refresh(offline = false) {
    const gen = generation
    if (localStorage.getItem(OFFLINE_REVOKED)) { cards.value = []; return }
    const data = await storage().list()
    if (gen !== generation) return
    if (!offline && data.session?.owner !== session.value?.owner) { cards.value = []; return }
    session.value = data.session
    cards.value = data.session ? data.cards : []
  }
  async function setOwner(owner: string) {
    if (session.value?.owner === owner && !localStorage.getItem(OFFLINE_REVOKED)) return refresh()
    const gen = ++generation
    cards.value = []
    session.value = null
    const value = await storage().activate(owner)
    if (gen !== generation) return
    localStorage.removeItem(OFFLINE_REVOKED)
    session.value = value
    error.value = ''
    await refresh()
  }
  async function save(wine: Wine, version: string) {
    const owner = session.value, gen = generation
    if (!owner || !navigator.onLine) throw new Error('Offline save unavailable')
    await storage().save(owner, makeOfflineCard(wine, version))
    if (gen !== generation) throw new Error('Account changed')
    await refresh()
    if (!cards.value.some(card => card.slug === wine.slug)) throw new Error('Local copy was not retained')
    channel?.postMessage('write')
  }
  async function remove(slug: string) {
    const owner = session.value
    if (!owner) return
    await storage().remove(owner, slug)
    await refresh(!navigator.onLine)
    channel?.postMessage('write')
  }
  async function clear() {
    generation++; cards.value = []; session.value = null
    // A tombstone also blocks later offline reads if IndexedDB deletion fails.
    try { localStorage.setItem(OFFLINE_REVOKED, 'yes') } catch { /* IndexedDB still gets cleared. */ }
    channel?.postMessage('clear')
    try { await storage().clear() }
    catch { error.value = 'Не удалось очистить копии на устройстве.' }
  }
  const hasStoredCards = async () => !localStorage.getItem(OFFLINE_REVOKED) && (await storage().list()).cards.length > 0
  return { cards, session, error, refresh, setOwner, save, remove, clear, hasStoredCards }
}
