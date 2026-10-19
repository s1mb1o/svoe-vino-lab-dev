import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { PRODUCT_LINE_LOADERS } from '../shared/data/product-line-maps'
import { PRODUCT_LINE_INDEX, buildProductLineIndex, loadProductLine, resolveProductLine } from '../shared/product-line-map'
import type { ProductLineIndexResolution, ProductLineResolution } from '../shared/product-line-map'
import { PRODUCT_LINE_FILES, PRODUCT_LINE_MAPS, resolveProductLine as resolveWithFullMaps } from './support/product-line-maps'

// The index answer must equal the full-map answer, reduced to the fields the index holds.
function reduced(resolution: ProductLineResolution): ProductLineIndexResolution {
  if (!('line' in resolution)) return resolution
  if (!('product' in resolution)) return { status: 'unplaced', producer: resolution.line.producer }
  return { status: resolution.status, producer: resolution.line.producer, product_id: resolution.product.id }
}

describe('product-line index', () => {
  it('matches the producer maps and the generator output', () => {
    expect(PRODUCT_LINE_INDEX).toEqual(buildProductLineIndex(PRODUCT_LINE_MAPS))
    const text = `${JSON.stringify(buildProductLineIndex(PRODUCT_LINE_MAPS), null, 2)}\n`
    expect(readFileSync(new URL('../shared/data/product-line-index.json', import.meta.url), 'utf8'), 'Run `npm run line-maps:index`').toBe(text)
  })

  it('lists exactly the registered loaders and map files', () => {
    const ids = PRODUCT_LINE_INDEX.producers.map(entry => entry.producer.id).sort()
    expect(ids).toEqual(Object.keys(PRODUCT_LINE_LOADERS).sort())
    expect(ids.map(id => `${id}.json`)).toEqual(PRODUCT_LINE_FILES)
  })

  it('resolves every slug, alias, producer name, and prefix like the full maps', () => {
    const wines = [
      { producer: 'Неизвестный производитель', slug: 'unknown-product' },
      { producer: null, slug: 'unknown-product' },
      { producer: '', slug: 'constructor' },
      { producer: 'Other', slug: '__proto__' },
    ]
    for (const line of PRODUCT_LINE_MAPS) {
      for (const product of line.products) {
        for (const slug of [product.wine_slug, ...product.wine_slug_aliases]) {
          if (slug) wines.push({ producer: line.producer.name, slug }, { producer: 'Другой производитель', slug })
        }
      }
      for (const name of [line.producer.name, ...line.producer.aliases]) wines.push({ producer: name, slug: 'unknown-product' })
      for (const prefix of line.producer.slug_prefixes) wines.push({ producer: '', slug: `${prefix}unknown-product` })
    }
    expect(wines.length).toBeGreaterThan(2000)
    for (const wine of wines) expect(resolveProductLine(wine), JSON.stringify(wine)).toEqual(reduced(resolveWithFullMaps(wine)))
    expect(resolveProductLine()).toEqual({ status: 'none' })
  })

  it('loads one exact map on demand and caches it', async () => {
    for (const line of PRODUCT_LINE_MAPS) expect(await loadProductLine(line.producer.id)).toEqual(line)
    expect(loadProductLine('abrau-durso')).toBe(loadProductLine('abrau-durso'))
    expect(await loadProductLine('unknown-producer')).toBeUndefined()
    expect(await loadProductLine('constructor')).toBeUndefined()
  })
})
