import { randomUUID } from 'node:crypto'
import { createError } from 'h3'
import type { Wine } from '#shared/catalog'
import { distanceKm, validLocation, type FoodStore, type FoodSelection, type FoodResult, type FoodProduct } from '#shared/food'
import { foodIdeas, matchesFood, type FoodIdea } from './food-pairings'

const BASE = 'https://digitalone.globus.ru/d1-mobile-bff/api/'
const MAX_RESPONSE = 512 * 1024
type RecordValue = Record<string, any>
function upstreamError() { return createError({ statusCode: 502, statusMessage: 'Globus catalog is unavailable' }) }

export function createGlobusClient(request: typeof fetch = fetch, signal = AbortSignal.timeout(20000)) {
  // Store selection belongs to this request only. Never reuse a guest identity across users.
  const appId = randomUUID()
  const deviceId = randomUUID()
  return async (path: string, method = 'GET', body?: unknown): Promise<RecordValue> => {
    try {
      const response = await request(BASE + path, {
        method, redirect: 'error', signal: AbortSignal.any([signal, AbortSignal.timeout(5000)]),
        headers: { Accept: 'application/json', 'Content-Type': 'application/json', Env: 'prod', 'X-App-Id': appId, 'X-Device-Id': deviceId, 'X-Request-ID': randomUUID(), 'User-Agent': 'SvoeVinoWebui/0.1' },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      })
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) { await response.body?.cancel(); throw upstreamError() }
      if (Number(response.headers.get('content-length')) > MAX_RESPONSE) { await response.body?.cancel(); throw upstreamError() }
      const reader = response.body?.getReader()
      if (!reader) throw upstreamError()
      const chunks: Uint8Array[] = []
      let total = 0
      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          total += value.byteLength
          if (total > MAX_RESPONSE) { await reader.cancel(); throw upstreamError() }
          chunks.push(value)
        }
      } finally { reader.releaseLock() }
      const value = JSON.parse(Buffer.concat(chunks).toString('utf8'))
      if (!value?.data || typeof value.data !== 'object' || Array.isArray(value.data)) throw upstreamError()
      return value.data
    } catch { throw upstreamError() }
  }
}
export type GlobusClient = ReturnType<typeof createGlobusClient>

export async function globusStores(client: GlobusClient): Promise<FoodStore[]> {
  const data = await client('v1/directories/stores')
  if (!Array.isArray(data.stores)) throw upstreamError()
  const stores: FoodStore[] = data.stores.filter((s: RecordValue) => s && Number.isInteger(s.id) && s.id > 0 && typeof s.name === 'string' && typeof s.full_addr === 'string' && validLocation(s.location))
    .map((s: RecordValue) => ({ id: s.id, name: s.name, address: s.full_addr, location: s.location, schedule: typeof s.schedule === 'string' ? s.schedule : '' }))
  if (!stores.length) throw upstreamError()
  return stores
}

export function selectGlobusStore(stores: FoodStore[], selection: FoodSelection) {
  if (selection.location) {
    return [...stores].sort((a, b) => distanceKm(selection.location!, a.location) - distanceKm(selection.location!, b.location))[0]!
  }
  const store = stores.find(store => store.id === selection.storeId)
  if (!store) throw createError({ statusCode: 400, statusMessage: 'Select a store from the current directory' })
  return store
}

export function validateFoodRequest(value: unknown): { slug: string; selection: FoodSelection } {
  const body = value as RecordValue | null
  if (!body || typeof body !== 'object' || Array.isArray(body) || typeof body.slug !== 'string' || !body.slug.trim() || body.slug.length > 300 || Object.keys(body).some(k => !['slug', 'location', 'storeId'].includes(k))) throw createError({ statusCode: 400, statusMessage: 'Invalid food request' })
  if (Object.hasOwn(body, 'location') === Object.hasOwn(body, 'storeId')) throw createError({ statusCode: 400, statusMessage: 'Select one location method' })
  if ('location' in body) {
    if (!validLocation(body.location) || Object.keys(body.location).some(k => !['latitude', 'longitude'].includes(k))) throw createError({ statusCode: 400, statusMessage: 'Invalid coordinates' })
    return { slug: body.slug, selection: { location: { latitude: body.location.latitude, longitude: body.location.longitude } } }
  }
  if (!Number.isInteger(body.storeId) || body.storeId <= 0) throw createError({ statusCode: 400, statusMessage: 'Invalid store' })
  return { slug: body.slug, selection: { storeId: body.storeId } }
}

function retailerUrl(value: unknown, kind: 'image' | 'product'): string | null {
  if (typeof value !== 'string') return null
  try {
    const url = new URL(value)
    if (url.protocol !== 'https:' || url.username || url.password || url.port) return null
    if (kind === 'image' && url.hostname === 'image.globus.ru') return url.href
    if (kind === 'product' && url.hostname === 'www.globus.ru' && /^\/products\/[a-zA-Z0-9_-]+\/?$/.test(url.pathname)) return url.href
  } catch { /* Invalid source URL. */ }
  return null
}

function eligible(p: RecordValue) {
  return p && typeof p.id === 'string' && p.active === true && typeof p.quantity_max === 'number' && p.quantity_max > 0 && p.is_adult !== true
}

export async function recommendGlobus(wine: Wine, selection: FoodSelection, client = createGlobusClient()): Promise<FoodResult> {
  const store = selectGlobusStore(await globusStores(client), selection)
  const context = await client('v1/context', 'PATCH', { context: { purchase_method: 1, store_id: store.id } })
  if (context.result !== true) throw upstreamError()
  const candidates = foodIdeas(wine)
  const products: FoodProduct[] = []
  const used = new Set<string>()
  async function search(idea: FoodIdea) {
    const data = await client('v6/catalog/search:result', 'POST', { query: idea.query, sort: 'default', pagination: { page: 1, per_page: 8 }, filter: { filter: [], range: [] }, include: ['products'] })
    if (!Array.isArray(data.products?.items)) throw upstreamError()
    return { idea, items: data.products.items as RecordValue[] }
  }
  for (let start = 0; start < candidates.length && products.length < 3; start += 3) {
    const batch = await Promise.all(candidates.slice(start, start + 3).map(search))
    for (const { idea, items } of batch) {
      if (products.length === 3) break
      const alternatives = items.filter(p => eligible(p) && !used.has(p.id) && matchesFood(idea, `${p.name_optional || ''} ${p.name_required || ''}`)).slice(0, 2)
      for (const item of alternatives) {
        const data = await client('v5/catalog/pdp', 'POST', { id: item.id })
        const p = data.product
        if (!p || p.id !== item.id || !eligible(p) || typeof p.name !== 'string' || !matchesFood(idea, p.name) || typeof p.price_per !== 'string') continue
        const url = retailerUrl(p.share_text, 'product')
        if (!url) continue
        used.add(p.id)
        const conditions = [p.condition_text, ...(Array.isArray(p.promotions) ? p.promotions.flatMap((promotion: RecordValue) => [promotion.offer_text, ...(Array.isArray(promotion.price_comments) ? promotion.price_comments : [])]) : [])]
          .filter((s): s is string => typeof s === 'string' && s.trim().length > 0)
        products.push({ id: p.id, name: p.name, image: retailerUrl(p.images?.[0] || item.preview_images?.[0], 'image'), url, priceLabel: p.price_per, conditions: [...new Set(conditions)], food: idea.food, reason: idea.reason })
        break
      }
    }
  }
  return { provider: 'globus', store, distanceKm: selection.location ? distanceKm(selection.location, store.location) : null, checkedAt: new Date().toISOString(), products, complete: products.length === 3 }
}
