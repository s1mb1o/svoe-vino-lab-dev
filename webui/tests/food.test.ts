import { describe, expect, it, vi } from 'vitest'
import { createGlobusClient, globusStores, recommendGlobus, selectGlobusStore, validateFoodRequest, type GlobusClient } from '../server/utils/globus'
import { distanceKm, type FoodStore } from '../shared/food'
import wines from '../server/data/wines.json'
import { foodIdeas, matchesFood } from '../server/utils/food-pairings'

const stores: FoodStore[] = [
  { id: 5020, name: 'Медведково', address: 'Test A', location: { latitude: 55.887168, longitude: 37.639079 }, schedule: 'Круглосуточно' },
  { id: 5001, name: 'Щёлково', address: 'Test B', location: { latitude: 55.928776, longitude: 38.003613 }, schedule: 'Круглосуточно' },
]
const directory = { stores: stores.map(s => ({ ...s, full_addr: s.address })) }
const product = (id: string, name: string, extra = {}) => ({ id, name, name_optional: name, name_required: '', active: true, quantity: 0, quantity_max: 5, is_adult: false, price_per: '169,99 ₽ / 100 г', images: ['https://image.globus.ru/mobile/a.jpg'], share_text: `https://www.globus.ru/products/${id}`, promotions: [{ offer_text: 'Цена по карте', price_comments: ['Без карты 199,99 ₽'] }], ...extra })
const choices = [product('turkey', 'Филе индейки'), product('cheese', 'Сыр моцарелла'), product('hummus', 'Хумус классический')]
function fixture(options: { sparse?: boolean; detailUnavailable?: boolean; unsafeUrl?: boolean; badContext?: boolean } = {}) {
  return vi.fn(async (path: string, _method?: string, body?: any) => {
    if (path.includes('directories')) return directory
    if (path === 'v1/context') return { result: !options.badContext }
    if (path.includes('search:result')) {
      const found = choices.find(p => p.name.toLowerCase().includes(body.query.toLowerCase())) || (body.query === 'моцарелла' ? choices[1] : undefined)
      return { products: { items: found && (!options.sparse || found.id === 'turkey') ? [product('out', found.name, { quantity_max: 0 }), product('wrong', 'Салфетки с рисунком сыра'), found] : [] } }
    }
    const found = choices.find(p => p.id === body.id)!
    return { product: { ...found, ...(options.detailUnavailable ? { quantity_max: 0 } : {}), ...(options.unsafeUrl ? { share_text: 'javascript:alert(1)', images: ['https://evil.example/pixel'] } : {}) } }
  }) as unknown as GlobusClient
}

describe('retailer selection and pairing', () => {
  it('selects the nearest live directory coordinate, independent of directory order', () => {
    const location = { latitude: 55.888168, longitude: 37.639079 }
    expect(distanceKm(location, stores[0]!.location)).toBeCloseTo(.1112, 3)
    expect(selectGlobusStore([...stores].reverse(), { location }).id).toBe(5020)
    expect(selectGlobusStore(stores, { storeId: 5001 }).id).toBe(5001)
    expect(() => selectGlobusStore(stores, { storeId: 123 })).toThrow()
    expect(distanceKm({ latitude: 0, longitude: 179.9 }, { latitude: 0, longitude: -179.9 })).toBeLessThan(23)
  })
  it.each([{}, { slug: 'x' }, { slug: 'x', location: { latitude: 91, longitude: 0 } }, { slug: 'x', location: { latitude: 0, longitude: Infinity } }, { slug: 'x', location: { latitude: '1', longitude: 0 } }, { slug: 'x', location: { latitude: 1, longitude: 1 }, storeId: 1 }, { slug: 'x', storeId: '1' }, { slug: 'x', storeId: -1 }, { slug: 'x', storeId: 1, endpoint: 'https://evil.example' }])('rejects invalid location selectors: %j', input => { expect(() => validateFoodRequest(input)).toThrow() })
  it('accepts finite zero coordinates without substituting a default location', () => {
    expect(validateFoodRequest({ slug: 'x', location: { latitude: 0, longitude: 0 } }).selection).toEqual({ location: { latitude: 0, longitude: 0 } })
  })
  it('returns three distinct actual products and preserves units and card conditions', async () => {
    const client = fixture()
    const result = await recommendGlobus(wines[0]!, { location: { latitude: 55.888168, longitude: 37.639079 } }, client)
    expect(result.complete).toBe(true)
    expect(result.products.map(p => p.id)).toEqual(['turkey', 'cheese', 'hummus'])
    expect(result.products[0]?.priceLabel).toBe('169,99 ₽ / 100 г')
    expect(result.products[0]?.conditions).toContain('Цена по карте')
    expect(result.products[0]?.url).toBe('https://www.globus.ru/products/turkey')
    expect(client).toHaveBeenCalledWith('v1/context', 'PATCH', { context: { purchase_method: 1, store_id: 5020 } })
    expect(JSON.stringify(vi.mocked(client).mock.calls)).not.toContain('55.888168')
  })
  it('reports a partial result rather than inventing products when stock is sparse', async () => {
    const result = await recommendGlobus(wines[0]!, { storeId: 5020 }, fixture({ sparse: true }))
    expect(result.complete).toBe(false)
    expect(result.products).toHaveLength(1)
    expect(result.distanceKm).toBeNull()
  })
  it.each([{ detailUnavailable: true }, { unsafeUrl: true }])('omits invalid or newly unavailable detail records: %j', async options => {
    expect((await recommendGlobus(wines[0]!, { storeId: 5020 }, fixture(options))).products).toEqual([])
  })
  it('fails explicitly when store context cannot be selected', async () => {
    await expect(recommendGlobus(wines[0]!, { storeId: 5020 }, fixture({ badContext: true }))).rejects.toMatchObject({ statusCode: 502 })
  })
  it('uses source pairings and offers different food groups for red and white wine', () => {
    expect(foodIdeas(wines[0]!).slice(0, 3).map(i => i.query)).toEqual(['филе индейки', 'моцарелла', 'хумус'])
    expect(foodIdeas(wines[2]!).slice(0, 2).map(i => i.query)).toEqual(['стейк говяжий', 'сыр пармезан'])
  })
})

describe('food preparation and candidate fallback', () => {
  it('excludes salted fish and pickled mushrooms from baking ideas', () => {
    const fish = foodIdeas(wines[0]!).find(i => i.query === 'филе лосося')!
    const mushrooms = foodIdeas(wines[2]!).find(i => i.query === 'шампиньоны свежие')!
    expect(matchesFood(fish, 'Филе лосося слабосолёное')).toBe(false)
    expect(matchesFood(fish, 'Филе лосося свежее')).toBe(true)
    expect(matchesFood(mushrooms, 'Шампиньоны маринованные')).toBe(false)
    expect(matchesFood(mushrooms, 'Шампиньоны свежие')).toBe(true)
  })
  it('uses the next candidate if the first product becomes unavailable', async () => {
    const base = fixture()
    const client: GlobusClient = async (path, method, body: any) => {
      if (path.includes('search:result') && body.query === 'филе индейки') return { products: { items: [product('sold', 'Филе индейки'), choices[0]] } }
      if (path.includes('/pdp') && body.id === 'sold') return { product: product('sold', 'Филе индейки', { quantity_max: 0 }) }
      return base(path, method, body)
    }
    const result = await recommendGlobus(wines[0]!, { storeId: 5020 }, client)
    expect(result.products[0]?.id).toBe('turkey')
    expect(result.complete).toBe(true)
  })
})

describe('Globus HTTP boundary', () => {
  it('isolates concurrent guest store contexts without tokens, cookies, or coordinates', async () => {
    const request = vi.fn(async () => Response.json({ data: { result: true } }))
    const first = createGlobusClient(request as typeof fetch)
    const second = createGlobusClient(request as typeof fetch)
    await Promise.all([first('v1/context', 'PATCH', {}), second('v1/context', 'PATCH', {})])
    await first('v6/catalog/search:result', 'POST', {})
    const headers = request.mock.calls.map(c => (c as unknown as [string, RequestInit])[1].headers as Record<string, string>)
    expect(headers[0]!['X-App-Id']).toBe(headers[2]!['X-App-Id'])
    expect(headers[0]!['X-App-Id']).not.toBe(headers[1]!['X-App-Id'])
    expect(headers[0]!['X-Device-Id']).not.toBe(headers[1]!['X-Device-Id'])
    expect(headers[0]!['X-Request-ID']).not.toBe(headers[2]!['X-Request-ID'])
    expect(headers[0]).not.toHaveProperty('Authorization')
    expect(headers[0]).not.toHaveProperty('Cookie')
  })
  it.each(['auth', 'html', 'malformed', 'oversize', 'shape'])('rejects invalid upstream response: %s', async kind => {
    const request = vi.fn(async () => {
      if (kind === 'auth') return Response.json({}, { status: 401 })
      if (kind === 'html') return new Response('<html>challenge</html>')
      if (kind === 'malformed') return new Response('{', { headers: { 'content-type': 'application/json' } })
      if (kind === 'oversize') return Response.json({ data: 'x'.repeat(524289) })
      return Response.json({ error: 'context' })
    })
    await expect(createGlobusClient(request as typeof fetch)('test')).rejects.toMatchObject({ statusCode: 502 })
  })
  it('rejects invalid directory coordinates', async () => {
    await expect(globusStores(async () => ({ stores: [{ id: 1, name: 'x', full_addr: 'y', location: { latitude: null, longitude: 1 } }] }))).rejects.toMatchObject({ statusCode: 502 })
  })
})
