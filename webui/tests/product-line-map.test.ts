import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import crosswalk from '../docs/product-line-map-crosswalk.json'
import { ABRAU_PRODUCT_LINE as line, findLineProduct, findProducerLine, productLineEdges, productPortalUrl, productsInGroup, resolveProductLine, validateProductLineMap } from '../shared/product-line-map'

describe('producer product-line graph', () => {
  it('covers the six source sheets without repeated Fizz packages', () => {
    expect(validateProductLineMap(line)).toEqual([])
    expect(line.products).toHaveLength(52)
    expect(line.groups).toHaveLength(14)
    expect(line.products.filter(product => product.wine_slug)).toHaveLength(32)
    expect(line.products.filter(product => !product.wine_slug)).toHaveLength(20)
    expect(line.products.reduce((count, product) => count + product.wine_slug_aliases.length, 0)).toBe(3)
    expect(line.scope.as_of).toBe('2026-09-20')
    const fizz = line.groups.find(group => group.name.includes('Fizz'))!
    expect(productsInGroup(line, fizz.id)).toHaveLength(4)
    expect(productsInGroup(line, fizz.id).every(product => /игристое вино/i.test(product.category))).toBe(true)
  })

  it('maps each source-sheet entry to one product and covers every product', () => {
    expect(crosswalk.entries).toHaveLength(54)
    expect(new Set(crosswalk.entries.map(entry => entry.sheet)).size).toBe(6)
    expect(new Set(crosswalk.entries.map(entry => entry.product_id))).toEqual(new Set(line.products.map(product => product.id)))
    expect(new Set(crosswalk.entries.map(entry => `${entry.sheet}:${entry.source_image}`)).size).toBe(54)
    for (const product of line.products) {
      expect(crosswalk.entries.filter(entry => entry.product_id === product.id)).toHaveLength(['abrau-fizz-brut-white', 'abrau-fizz-semi-sweet-white'].includes(product.id) ? 2 : 1)
    }
  })

  it('resolves the exact scanner result and verified legacy aliases to one product', () => {
    for (const product of line.products.filter(product => product.wine_slug)) {
      expect(findLineProduct(line, product.wine_slug!)).toBe(product)
      for (const alias of product.wine_slug_aliases) expect(findLineProduct(line, alias)).toBe(product)
    }
    const victor = findLineProduct(line, 'abrau-dyurso-victor-dravigny-bryut')!
    expect(victor.wine_slug).toBe('abrau-dyurso-victor-dravigny-brut-shardone-beloe-bryut-12')
    const kosher = findLineProduct(line, 'abrau-dyurso-victor-dravigny-koshernoe-bryut-shardone-beloe-125')!
    expect(kosher.id).toBe('victor-dravigny-kosher-brut')
    expect(kosher.badges).toContain('Кошерное')
    expect(victor.badges).not.toContain('Кошерное')
    expect(kosher).not.toBe(victor)
  })

  it('does not invent a product or producer match', () => {
    expect(findProducerLine({ producer: 'Абрау—Дюрсо', slug: 'unknown' })).toBe(line)
    expect(findProducerLine({ producer: '', slug: 'abrau-dyurso-risling-beloe-suhoe-12' })).toBe(line)
    expect(findLineProduct(line, 'abrau-dyurso-risling-beloe-suhoe-12')).toBeUndefined()
    expect(findLineProduct(line, undefined)).toBeUndefined()
    expect(findProducerLine({ producer: 'Винодельня Марченко', slug: 'priboj-marchenko-beloe-polusuhoe' })).toBeUndefined()
  })

  it('returns explicit recognition states without replacing unknown results', () => {
    expect(resolveProductLine()).toEqual({ status: 'none' })
    expect(resolveProductLine({ producer: 'Other', slug: 'unknown' })).toEqual({ status: 'unsupported' })
    expect(resolveProductLine({ producer: 'Abrau Durso', slug: 'unknown' })).toEqual({ status: 'unplaced', line })
    expect(resolveProductLine({ producer: 'Other', slug: 'abrau-dyurso-victor-dravigny-bryut' })).toMatchObject({ status: 'alias', product: { id: 'victor-dravigny-brut' } })
    expect(resolveProductLine({ producer: '', slug: 'abrau-dyurso-victor-dravigny-brut-shardone-beloe-bryut-12' })).toMatchObject({ status: 'placed', product: { id: 'victor-dravigny-brut' } })
  })

  it('keeps gray products selectable as full records without a portal URL', () => {
    for (const product of line.products) {
      if (product.wine_slug) expect(productPortalUrl(product)).toBe(`https://vino-svoe.ru/wines/${product.wine_slug}`)
      else {
        expect(productPortalUrl(product)).toBeNull()
        expect(product.description.length).toBeGreaterThan(10)
        expect(product.name.length).toBeGreaterThan(0)
      }
      expect(product.price).toBeNull()
    }
  })

  it('derives a connected containment tree from one membership field', () => {
    const edges = productLineEdges(line)
    expect(edges).toHaveLength(66)
    for (const product of line.products) {
      expect(edges.filter(edge => edge.target === product.id)).toEqual([{ source: product.group_id, target: product.id, type: 'contains' }])
      expect(edges.some(edge => edge.source === line.producer.id && edge.target === product.group_id)).toBe(true)
    }
  })

  it('ships every product image as a real local WebP', () => {
    for (const product of line.products) {
      const bytes = readFileSync(new URL(`../public${product.image!.src}`, import.meta.url))
      expect(bytes.subarray(0, 4).toString('ascii'), product.id).toBe('RIFF')
      expect(bytes.subarray(8, 12).toString('ascii'), product.id).toBe('WEBP')
    }
  })

  it('rejects broken membership, ambiguous aliases, and unsafe links', () => {
    const broken = structuredClone(line)
    broken.products[0]!.group_id = 'missing-group'
    broken.groups[0]!.tier_id = 'missing-tier'
    broken.products[1]!.wine_slug_aliases.push(broken.products[0]!.wine_slug!)
    broken.products[2]!.image!.src = '/product-line-maps/abrau-durso/../secret.webp'
    broken.sources[0]!.url = 'javascript:alert(1)'
    const errors = validateProductLineMap(broken)
    expect(errors).toContain('Ambiguous wine slug or alias')
    expect(errors.some(error => error.startsWith('Unknown group:'))).toBe(true)
    expect(errors.some(error => error.startsWith('Unknown tier:'))).toBe(true)
    expect(errors.some(error => error.startsWith('Unsafe image path:'))).toBe(true)
    expect(errors.some(error => error.startsWith('Unsafe source URL:'))).toBe(true)
  })

  it('rejects ambiguous premium ranks and empty tiers', () => {
    const broken = structuredClone(line)
    broken.tiers[1]!.rank = broken.tiers[0]!.rank
    broken.tiers.push({ ...broken.tiers[0]!, id: 'empty-tier', rank: 99 })
    expect(validateProductLineMap(broken)).toContain('Duplicate premium tier rank')
    expect(validateProductLineMap(broken)).toContain('Empty tier: empty-tier')
  })

  it('rejects duplicate node IDs and aliases on an unlinked product', () => {
    const broken = structuredClone(line)
    broken.products[1]!.id = broken.products[0]!.id
    const unlinked = broken.products.find(product => product.wine_slug === null)!
    unlinked.wine_slug_aliases.push('unverified-alias')
    expect(validateProductLineMap(broken)).toContain('Duplicate node ID')
    expect(validateProductLineMap(broken)).toContain(`Unlinked product has aliases: ${unlinked.id}`)
  })
})
