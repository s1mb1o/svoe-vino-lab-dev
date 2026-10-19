import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import baseline from '../docs/product-line-maps/abrau-durso/catalog-baseline.json'
import extension from '../docs/product-line-maps/abrau-durso/catalog-extension.json'
import catalogCrosswalk from '../docs/product-line-maps/abrau-durso/catalog-crosswalk.json'
import { describe, expect, it } from 'vitest'
import crosswalk from '../docs/product-line-map-crosswalk.json'
import { findLineProduct, productLineEdges, productPortalUrl, productsInGroup, validateProductLineMap } from '../shared/product-line-map'
import { ABRAU_PRODUCT_LINE as line, findProducerLine, resolveProductLine } from './support/product-line-maps'

describe('producer product-line graph', () => {
  it('retains the six source sheets and adds the identified still-wine catalog cards', () => {
    expect(validateProductLineMap(line)).toEqual([])
    expect(line.products).toHaveLength(73)
    expect(line.groups).toHaveLength(19)
    expect(line.products.filter(product => product.wine_slug)).toHaveLength(53)
    expect(line.products.filter(product => !product.wine_slug)).toHaveLength(20)
    expect(line.products.reduce((count, product) => count + product.wine_slug_aliases.length, 0)).toBe(3)
    expect(line.scope.as_of).toBe('2026-10-16')
    const fizz = line.groups.find(group => group.name.includes('Fizz'))!
    expect(productsInGroup(line, fizz.id)).toHaveLength(4)
    expect(productsInGroup(line, fizz.id).every(product => /игристое вино/i.test(product.category))).toBe(true)
  })

  it('keeps all original sheet products separate from the 21 catalog additions', () => {
    expect(crosswalk.entries).toHaveLength(54)
    expect(new Set(crosswalk.entries.map(entry => entry.sheet)).size).toBe(6)
    expect(new Set(crosswalk.entries.map(entry => entry.product_id)).size).toBe(52)
    expect(new Set([...crosswalk.entries.map(entry => entry.product_id), ...extension.entries.map(entry => entry.product_id)])).toEqual(new Set(line.products.map(product => product.id)))
    expect(new Set(crosswalk.entries.map(entry => `${entry.sheet}:${entry.source_image}`)).size).toBe(54)
    for (const product of line.products) {
      const added = extension.entries.some(entry => entry.product_id === product.id)
      expect(crosswalk.entries.filter(entry => entry.product_id === product.id)).toHaveLength(added ? 0 : ['abrau-fizz-brut-white', 'abrau-fizz-semi-sweet-white'].includes(product.id) ? 2 : 1)
    }
  })

  it('covers the independently pinned Abrau catalog except the owner-excluded unidentified card', () => {
    expect(baseline.expected_count).toBe(57)
    expect(baseline.records).toHaveLength(57)
    expect(baseline.source_sha256).toBe('e915493a0a960df040b4055d33c815940e48fb1a2994a7979a819786b2c41961')
    expect(extension.entries).toHaveLength(21)
    expect(extension.excluded_catalog_cards.map(record => record.wine_slug)).toEqual(['rozovoe-polusladkoe-2'])
    expect(catalogCrosswalk.entries).toHaveLength(57)
    const excluded = new Set(extension.excluded_catalog_cards.map(record => record.wine_slug))
    for (const record of baseline.records) {
      const product = findLineProduct(line, record.slug)
      if (excluded.has(record.slug)) {
        expect(product).toBeUndefined()
        expect(catalogCrosswalk.entries.find(entry => entry.wine_slug === record.slug)?.match).toBe('excluded-unidentified')
      } else {
        expect(product, record.slug).toBeDefined()
        expect(catalogCrosswalk.entries.find(entry => entry.wine_slug === record.slug)?.product_id).toBe(product!.id)
      }
    }
    expect(baseline.records.filter(record => findLineProduct(line, record.slug))).toHaveLength(56)
    for (const entry of extension.entries) {
      const record = baseline.records.find(record => record.slug === entry.wine_slug)!
      const product = findLineProduct(line, record.slug)!
      expect(product).toMatchObject({ id: entry.product_id, group_id: entry.group_id, name: record.name, description: record.description, wine_slug_aliases: [], category: 'Тихое вино' })
      expect(product.grapes).toEqual(record.grapes.split(/[,;]/).map(value => value.trim()).filter(Boolean))
      const bytes = readFileSync(new URL(`../public${product.image!.src}`, import.meta.url))
      expect(createHash('sha256').update(bytes).digest('hex')).toBe(entry.asset_sha256)
      expect(product.image!.frame).toEqual(entry.frame)
    }
    expect(resolveProductLine({ producer: 'Абрау-Дюрсо', slug: 'rozovoe-polusladkoe-2' })).toMatchObject({ status: 'unplaced', line })
  })

  it.skipIf(!process.env.PRODUCT_LINE_CATALOG_SNAPSHOT)('verifies all 57 baseline records against the original snapshot', () => {
    const bytes = readFileSync(process.env.PRODUCT_LINE_CATALOG_SNAPSHOT!)
    expect(createHash('sha256').update(bytes).digest('hex')).toBe(baseline.source_sha256)
    const records = bytes.toString('utf8').split(/\r?\n/).filter(Boolean)
      .map(row => JSON.parse(row)).filter(row => row.producer === 'Абрау-Дюрсо')
      .map(({ slug, name, description, grapes }) => ({ slug, name, description, grapes }))
    expect(records).toHaveLength(57)
    expect(records).toEqual(baseline.records)
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
    expect(findLineProduct(line, 'abrau-dyurso-risling-beloe-suhoe-12')?.group_id).toBe('abrau-still')
    expect(findLineProduct(line, 'rozovoe-polusladkoe-2')).toBeUndefined()
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
    expect(edges).toHaveLength(92)
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

  it('reports a missing image field without throwing on a partial JSON record', () => {
    const broken = structuredClone(line)
    delete (broken.products[0] as Partial<typeof broken.products[number]>).image
    expect(validateProductLineMap(broken)).toContain(`Missing image field: ${broken.products[0]!.id}`)
  })

  it('rejects image frames that cannot fit the source image', () => {
    const invalidFrames = [
      { x: -1, y: 0, width: 30, height: 100, source_width: 100, source_height: 100 },
      { x: 0, y: 0, width: 0, height: 100, source_width: 100, source_height: 100 },
      { x: 80, y: 0, width: 30, height: 100, source_width: 100, source_height: 100 },
      { x: 0, y: 20, width: 30, height: 100, source_width: 100, source_height: 100 },
      { x: 0, y: 0, width: 30, height: 100, source_width: 0, source_height: 100 },
      { x: 0, y: 0, width: 30.5, height: 100, source_width: 100, source_height: 100 },
    ]
    for (const frame of invalidFrames) {
      const broken = structuredClone(line)
      broken.products[0]!.image!.frame = frame
      expect(validateProductLineMap(broken)).toContain(`Invalid image frame: ${broken.products[0]!.id}`)
    }
    const valid = structuredClone(line)
    valid.products[0]!.image!.frame = { x: 35, y: 0, width: 30, height: 100, source_width: 100, source_height: 100 }
    expect(validateProductLineMap(valid)).toEqual([])
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
