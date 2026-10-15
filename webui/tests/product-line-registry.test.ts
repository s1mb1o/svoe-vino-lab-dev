import { describe, expect, it } from 'vitest'
import { readFileSync, readdirSync } from 'node:fs'
import { PRODUCT_LINE_MAPS, resolveProductLine, findProducerLine, productPortalUrl, validateProductLineMaps } from '../shared/product-line-map'

describe('producer map registry', () => {
  it('registers every producer JSON and rejects cross-producer ambiguity', () => {
    const files = readdirSync(new URL('../shared/data/product-line-maps/', import.meta.url)).filter(file => file.endsWith('.json'))
    expect(PRODUCT_LINE_MAPS.map(line => `${line.producer.id}.json`).sort()).toEqual(files.sort())
    expect(validateProductLineMaps(PRODUCT_LINE_MAPS)).toEqual([])
    const duplicate = structuredClone(PRODUCT_LINE_MAPS[0]!)
    duplicate.producer.id = 'another-producer'
    duplicate.producer.name = 'Другой производитель'
    duplicate.producer.aliases = []
    duplicate.producer.slug_prefixes = []
    for (const product of duplicate.products) product.image = null
    expect(validateProductLineMaps([PRODUCT_LINE_MAPS[0]!, duplicate]).some(error => error.startsWith('Ambiguous producer slug:'))).toBe(true)
    duplicate.products = duplicate.products.map(product => ({ ...product, wine_slug: null, wine_slug_aliases: [] }))
    duplicate.producer.aliases = [PRODUCT_LINE_MAPS[0]!.producer.name]
    expect(validateProductLineMaps([PRODUCT_LINE_MAPS[0]!, duplicate]).some(error => error.startsWith('Ambiguous producer name:'))).toBe(true)
  })

  for (const line of PRODUCT_LINE_MAPS) {
    it(`${line.producer.id}: resolves all exact identities and preserves gray products`, () => {
      for (const product of line.products) {
        for (const slug of [product.wine_slug, ...product.wine_slug_aliases]) {
          if (!slug) continue
          // Deliberately supply another producer name. Exact identity must win.
          const wrongProducer = PRODUCT_LINE_MAPS.find(other => other !== line)?.producer.name || 'Другой'
          expect(resolveProductLine({ producer: wrongProducer, slug })).toMatchObject({ line, product })
          expect(findProducerLine({ producer: wrongProducer, slug })).toBe(line)
        }
        expect(productPortalUrl(product)).toBe(product.wine_slug ? `https://vino-svoe.ru/wines/${product.wine_slug}` : null)
        if (product.image) {
          const bytes = readFileSync(new URL(`../public${product.image.src}`, import.meta.url))
          expect(bytes.subarray(0, 4).toString('ascii'), product.id).toBe('RIFF')
          expect(bytes.subarray(8, 12).toString('ascii'), product.id).toBe('WEBP')
        } else {
          expect(product.image).toBeNull()
        }
        expect(product.source_ids.length).toBeGreaterThan(0)
        if (product.wine_slug === null) {
          expect(product.wine_slug_aliases).toEqual([])
          expect(product.description.length).toBeGreaterThan(10)
        }
      }
      for (const name of [line.producer.name, ...line.producer.aliases]) {
        expect(resolveProductLine({ producer: name, slug: 'unknown-product' })).toMatchObject({ status: 'unplaced', line })
      }
    })

    if (line.producer.id === 'abrau-durso') continue
    it(`${line.producer.id}: covers the saved catalog crosswalk`, () => {
      const crosswalk = JSON.parse(readFileSync(new URL(`../docs/product-line-maps/${line.producer.id}/crosswalk.json`, import.meta.url), 'utf8'))
      const linked = line.products.filter(product => product.wine_slug)
      expect(linked.map(product => product.wine_slug).sort()).toEqual(crosswalk.entries.map((entry: { wine_slug: string }) => entry.wine_slug).sort())
      for (const entry of crosswalk.entries) {
        expect(linked.find(product => product.id === entry.product_id)).toMatchObject({ wine_slug: entry.wine_slug, group_id: entry.group_id })
      }
    })
  }
})
