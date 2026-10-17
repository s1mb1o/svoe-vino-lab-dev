import { describe, expect, it } from 'vitest'
import { createHash } from 'node:crypto'
import { readFileSync, readdirSync } from 'node:fs'
import { PRODUCT_LINE_MAPS, resolveProductLine, findProducerLine, productPortalUrl, validateProductLineMaps } from '../shared/product-line-map'

const snapshotSha256 = 'e915493a0a960df040b4055d33c815940e48fb1a2994a7979a819786b2c41961'
// Pin the agreed snapshot coverage independently of the generated baselines.
const expectedCatalog: Record<string, { producer: string; count: number }> = {
  'soyuz-vino': { producer: 'Союз-Вино', count: 69 },
  'agora': { producer: 'AGORA WINERY', count: 32 },
  'sober-bash': { producer: 'Собер Баш', count: 37 },
  'belbek': { producer: 'Бельбек', count: 39 },
  'novy-svet': { producer: 'Новый Свет. Дом шампанских вин', count: 44 },
  'valery-zakharyin': { producer: 'Валерий Захарьин', count: 46 },
  'chateau-pinot': { producer: 'Шато Пино', count: 50 },
  'esse': { producer: 'ESSE', count: 53 },
  'derbent-vino': { producer: 'Дербент Вино', count: 63 },
  fanagoria: { producer: 'Фанагория', count: 102 },
  'kuban-vino': { producer: 'Кубань-Вино', count: 97 },
  myskhako: { producer: 'Мысхако', count: 92 },
  'zolotaya-balka': { producer: 'Золотая Балка', count: 41 },
  'alma-valley': { producer: 'Alma Valley', count: 39 },
  inkerman: { producer: 'Инкерманский ЗМВ', count: 15 },
  massandra: { producer: 'Массандра', count: 44 },
  vedernikov: { producer: 'Ведерниковъ', count: 43 },
  koktebel: { producer: 'ЗМВ Коктебель', count: 26 },
}
interface CatalogRecord { slug: string; name: string; description: string; grapes: string }
interface SnapshotRecord extends CatalogRecord { producer: string }
interface CatalogBaseline { catalog_snapshot: string; source_sha256: string; producer: string; expected_count: number; records: CatalogRecord[] }
interface AssetEntry { product_id: string; asset_sha256: string | null; absence_check?: string | { snapshot: string; producer: string; matched_catalog_slugs: string[]; reason: string } }
interface CatalogEntry extends AssetEntry { wine_slug: string; group_id: string; catalog_producer: string }
interface CatalogCrosswalk { producer_id: string; catalog_snapshot: string; catalog_producer: string; entries: CatalogEntry[]; official_additions: AssetEntry[] }

const sha256 = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex')
const bySlug = (a: CatalogRecord, b: CatalogRecord) => a.slug.localeCompare(b.slug, 'en')
// The full snapshot is optional in CI. When supplied, verify its exact bytes and rows.
const snapshotPath = process.env.PRODUCT_LINE_CATALOG_SNAPSHOT
const snapshotBytes = snapshotPath ? readFileSync(snapshotPath) : undefined
const snapshotRecords: SnapshotRecord[] = snapshotBytes
  ? snapshotBytes.toString('utf8').split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line))
  : []

describe('producer map registry', () => {
  it('has a bottle image and a measured frame for every current map product', () => {
    const missing = PRODUCT_LINE_MAPS.flatMap(line => line.products
      .filter(product => !product.image || !product.image.frame)
      .map(product => `${line.producer.id}: ${product.id}`))
    expect(missing).toEqual([])
  })

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

  it.skipIf(!snapshotBytes)('verifies the full catalog snapshot checksum', () => {
    expect(sha256(snapshotBytes!)).toBe(snapshotSha256)
  })

  it.skipIf(!snapshotBytes)('does not attribute another snapshot producer through a slug or name fallback', () => {
    const expectedByProducer = new Map(PRODUCT_LINE_MAPS.map(line => [
      line.producer.id === 'abrau-durso' ? 'Абрау-Дюрсо' : expectedCatalog[line.producer.id]!.producer,
      line.producer.id,
    ]))
    const mismatches = snapshotRecords.flatMap(record => {
      const resolution = resolveProductLine(record)
      const actual = 'line' in resolution ? resolution.line.producer.id : undefined
      const expected = expectedByProducer.get(record.producer)
      return actual === expected ? [] : [{ slug: record.slug, producer: record.producer, expected: expected ?? null, actual: actual ?? null, status: resolution.status }]
    })
    expect(mismatches).toEqual([])
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
    const crosswalk: CatalogCrosswalk = JSON.parse(readFileSync(new URL(`../docs/product-line-maps/${line.producer.id}/crosswalk.json`, import.meta.url), 'utf8'))
    const baseline: CatalogBaseline = JSON.parse(readFileSync(new URL(`../docs/product-line-maps/${line.producer.id}/catalog-baseline.json`, import.meta.url), 'utf8'))

    it(`${line.producer.id}: covers the independently pinned catalog baseline`, () => {
      const expected = expectedCatalog[line.producer.id]!
      expect(expected, `Add an independently checked catalog count for ${line.producer.id}`).toBeDefined()
      expect(baseline.source_sha256).toBe(snapshotSha256)
      expect(baseline.catalog_snapshot).toBe('official-2026-09-17')
      expect(baseline.producer).toBe(expected.producer)
      expect(baseline.expected_count).toBe(expected.count)
      expect(baseline.records).toHaveLength(expected.count)
      expect(new Set(baseline.records.map(record => record.slug)).size).toBe(expected.count)
      expect(line.products.filter(product => product.wine_slug).map(product => product.wine_slug).sort()).toEqual(baseline.records.map(record => record.slug).sort())
      for (const record of baseline.records) {
        const product = line.products.find(product => product.wine_slug === record.slug)!
        expect(product.name).toBe(record.name)
        expect(product.description).toBe(record.description || 'Описание в сохранённом каталоге не указано.')
        expect(product.grapes).toEqual((record.grapes || '').split(/[,;]/).map(value => value.trim()).filter(Boolean))
      }
    })

    it.skipIf(!snapshotBytes)(`${line.producer.id}: reproduces baseline records from the full snapshot`, () => {
      const records = snapshotRecords
        .filter(record => record.producer === expectedCatalog[line.producer.id]!.producer)
        .map(({ slug, name, description, grapes }) => ({ slug, name, description, grapes }))
      expect(records).toHaveLength(expectedCatalog[line.producer.id]!.count)
      expect([...baseline.records].sort(bySlug)).toEqual(records.sort(bySlug))
    })

    it(`${line.producer.id}: covers linked and gray products exactly in the crosswalk`, () => {
      expect(crosswalk.producer_id).toBe(line.producer.id)
      expect(crosswalk.catalog_snapshot).toBe('official-2026-09-17')
      expect(crosswalk.catalog_producer).toBe(expectedCatalog[line.producer.id]!.producer)
      const linked = line.products.filter(product => product.wine_slug)
      const gray = line.products.filter(product => product.wine_slug === null)
      expect(linked.map(product => product.wine_slug).sort()).toEqual(crosswalk.entries.map(entry => entry.wine_slug).sort())
      expect(linked.map(product => product.id).sort()).toEqual(crosswalk.entries.map(entry => entry.product_id).sort())
      expect(gray.map(product => product.id).sort()).toEqual(crosswalk.official_additions.map(entry => entry.product_id).sort())
      for (const entry of crosswalk.official_additions) {
        if (!entry.absence_check || typeof entry.absence_check === 'string') continue
        // A display-name alias can select zero snapshot rows and falsely prove absence.
        expect(entry.absence_check.producer, entry.product_id).toBe(expectedCatalog[line.producer.id]!.producer)
        expect(entry.absence_check.snapshot, entry.product_id).toBe(baseline.catalog_snapshot)
      }
      for (const entry of crosswalk.entries) {
        expect(entry.catalog_producer).toBe(expectedCatalog[line.producer.id]!.producer)
        expect(linked.find(product => product.id === entry.product_id)).toMatchObject({ wine_slug: entry.wine_slug, group_id: entry.group_id })
      }
    })

    it(`${line.producer.id}: matches every public image to its recorded output checksum`, () => {
      const assets = [...crosswalk.entries, ...crosswalk.official_additions]
      for (const product of line.products) {
        const entries = assets.filter(entry => entry.product_id === product.id)
        expect(entries, product.id).toHaveLength(1)
        const recorded = entries[0]!.asset_sha256
        if (product.image) {
          expect(recorded, product.id).toMatch(/^[a-f0-9]{64}$/)
          const bytes = readFileSync(new URL(`../public${product.image.src}`, import.meta.url))
          expect(sha256(bytes), product.id).toBe(recorded)
        } else {
          expect(recorded, `${product.id}: a placeholder must not claim image bytes`).toBeNull()
        }
      }
    })
  }
})
