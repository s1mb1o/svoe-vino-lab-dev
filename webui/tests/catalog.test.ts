import { describe, expect, it } from 'vitest'
import wines from '../server/data/wines.json'
import { extractSlug, MOCK_SLUG, sourceWineUrl } from '../shared/catalog'
import { existsSync } from 'node:fs'

describe('demo catalog', () => {
  it('contains unique source slugs, local assets, and a resolvable mock result', () => {
    expect(new Set(wines.map(wine => wine.slug)).size).toBe(wines.length)
    expect(wines.find(wine => wine.slug === MOCK_SLUG)).toBeTruthy()
    for (const wine of wines) {
      expect(existsSync(`public${wine.image}`)).toBe(true)
      expect(wine.source).toBe(sourceWineUrl(wine.slug))
    }
    expect(wines.find(wine => wine.slug === 'muskat-ottonel-gusev')?.alcohol).toBeNull()
  })
})

describe('official slug response', () => {
  it('accepts the evaluator object and array forms without rewriting slugs', () => {
    expect(extractSlug({ slug: 'Exact-Slug_2024' })).toBe('Exact-Slug_2024')
    expect(extractSlug([{ slug: 'first' }, { slug: 'second' }])).toBe('first')
  })
  it.each([null, [], {}, { wine_slug: 'wrong-field' }, { slug: '' }, { slug: 123 }, { slug: '   ' }, [{ slug: null }, { slug: 'second' }]])('rejects invalid response %j', value => {
    expect(extractSlug(value)).toBeNull()
  })
  it('encodes a source link path without changing the host', () => {
    expect(sourceWineUrl('//other.test/?x=1')).toBe('https://vino-svoe.ru/wines/%2F%2Fother.test%2F%3Fx%3D1')
  })
})
