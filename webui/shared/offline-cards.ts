import { publicWine } from './alternatives'
import type { Wine } from './catalog'

export const OFFLINE_DB = 'chtozavino-offline-cards-v1'
export const OFFLINE_LIMIT = 50
export const OFFLINE_REVOKED = 'chtozavino.offline-revoked.v1'
export interface OfflineSession { owner: string; epoch: string }
export interface OfflineCard { slug: string; wine: Wine; version: string; savedAt: string }

export function makeOfflineCard(wine: unknown, version: string, now = new Date().toISOString()): OfflineCard {
  const safe = publicWine(wine)
  if (!safe || !/^[a-f0-9]{64}$/.test(version) || !Number.isFinite(Date.parse(now))) throw new Error('Invalid offline card')
  return { slug: safe.slug, wine: safe, version, savedAt: now }
}
export function validOfflineCard(value: unknown): value is OfflineCard {
  const v = value as Partial<OfflineCard> | null
  if (!v || Object.keys(v).some(key => !['slug', 'wine', 'version', 'savedAt'].includes(key))) return false
  try { return Boolean(v.wine && JSON.stringify(makeOfflineCard(v.wine, v.version!, v.savedAt)) === JSON.stringify(v)) } catch { return false }
}
const sameSession = (a: OfflineSession | undefined, b: OfflineSession) => a?.owner === b.owner && a.epoch === b.epoch

export function createOfflineStore(factory: IDBFactory) {
  let opening: Promise<IDBDatabase> | undefined
  function open(): Promise<IDBDatabase> {
    if (!factory) return Promise.reject(new Error('IndexedDB unavailable'))
    if (opening) return opening
    opening = new Promise<IDBDatabase>((resolve, reject) => {
      const request = factory.open(OFFLINE_DB, 1)
      let expired = false
      const fail = () => { expired = true; opening = undefined; clearTimeout(timer); reject(new Error('Offline storage unavailable')) }
      const timer = setTimeout(fail, 3000)
      request.onupgradeneeded = () => {
        request.result.createObjectStore('cards', { keyPath: 'slug' })
        request.result.createObjectStore('meta')
      }
      request.onblocked = fail
      request.onerror = fail
      request.onsuccess = () => {
        clearTimeout(timer)
        if (expired) return request.result.close()
        const db = request.result
        db.onversionchange = () => { db.close(); opening = undefined }
        resolve(db)
      }
    }).catch(error => { opening = undefined; throw error })
    return opening
  }
  async function transaction<T>(mode: IDBTransactionMode, run: (tx: IDBTransaction, finish: (result: T) => void, fail: (error: Error) => void) => void): Promise<T> {
    const db = await open()
    return new Promise<T>((resolve, reject) => {
      const tx = db.transaction(['cards', 'meta'], mode)
      let result: T, failure: Error | undefined
      tx.oncomplete = () => resolve(result)
      tx.onabort = tx.onerror = () => reject(failure || tx.error || new Error('Offline transaction failed'))
      try { run(tx, value => { result = value }, error => { failure = error; tx.abort() }) }
      catch (error) { failure = error as Error; tx.abort() }
    })
  }
  return {
    activate(owner: string): Promise<OfflineSession> {
      if (!owner || owner.length > 200) return Promise.reject(new Error('Invalid offline owner'))
      return transaction('readwrite', (tx, finish, fail) => {
        const meta = tx.objectStore('meta'), request = meta.get('session')
        request.onsuccess = () => {
          try {
            const old = request.result as OfflineSession | undefined
            const next = old?.owner === owner && typeof old.epoch === 'string' ? old : { owner, epoch: crypto.randomUUID() }
            if (next !== old) tx.objectStore('cards').clear()
            meta.put(next, 'session'); finish(next)
          } catch (error) { fail(error as Error) }
        }
      })
    },
    list(): Promise<{ session: OfflineSession | null; cards: OfflineCard[] }> {
      return transaction('readonly', (tx, finish) => {
        const meta = tx.objectStore('meta').get('session')
        const request = tx.objectStore('cards').getAll()
        request.onsuccess = () => finish({ session: meta.result?.owner ? meta.result : null, cards: (request.result as unknown[]).filter(validOfflineCard).sort((a, b) => b.savedAt.localeCompare(a.savedAt) || a.slug.localeCompare(b.slug)).slice(0, OFFLINE_LIMIT) })
      })
    },
    save(session: OfflineSession, card: OfflineCard): Promise<void> {
      if (!validOfflineCard(card)) return Promise.reject(new Error('Invalid offline card'))
      return transaction('readwrite', (tx, finish, fail) => {
        const meta = tx.objectStore('meta').get('session')
        meta.onsuccess = () => {
          try {
            if (!sameSession(meta.result, session)) return fail(new Error('Account changed'))
            const cards = tx.objectStore('cards')
            cards.put(card)
            const all = cards.getAll()
            all.onsuccess = () => {
              try {
                const rows = (all.result as unknown[]).filter(validOfflineCard).sort((a, b) => b.savedAt.localeCompare(a.savedAt) || a.slug.localeCompare(b.slug))
                const keep = new Set(rows.slice(0, OFFLINE_LIMIT).map(row => row.slug))
                for (const row of all.result as Array<{ slug?: string }>) if (row.slug && !keep.has(row.slug)) cards.delete(row.slug)
                finish(undefined)
              } catch (error) { fail(error as Error) }
            }
          } catch (error) { fail(error as Error) }
        }
      })
    },
    remove(session: OfflineSession, slug: string): Promise<void> {
      return transaction('readwrite', (tx, finish, fail) => {
        const request = tx.objectStore('meta').get('session')
        request.onsuccess = () => {
          try {
            if (!sameSession(request.result, session)) return fail(new Error('Account changed'))
            tx.objectStore('cards').delete(slug); finish(undefined)
          } catch (error) { fail(error as Error) }
        }
      })
    },
    clear(): Promise<void> {
      return transaction('readwrite', (tx, finish) => {
        tx.objectStore('cards').clear()
        tx.objectStore('meta').put({ owner: '', epoch: crypto.randomUUID() }, 'session')
        finish(undefined)
      })
    },
  }
}
