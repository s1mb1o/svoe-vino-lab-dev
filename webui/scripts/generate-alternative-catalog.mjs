import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
import { CatalogService, normal, sha256 } from '../../mcp/src/catalog.mjs'
import { build } from 'esbuild'

const root = resolve(fileURLToPath(new URL('../../', import.meta.url)))
const service = await CatalogService.load(root)
const index = JSON.parse(await readFile(resolve(root, 'webui/shared/data/product-line-index.json'), 'utf8'))
const aliases = new Map()
const producers = new Map()
const exactProducers = new Map()
for (const entry of index.producers) {
  for (const name of [entry.producer.name, ...entry.producer.aliases]) producers.set(normal(name), `map:${entry.producer.id}`)
  for (const [slug, product] of Object.entries(entry.slugs)) {
    aliases.set(slug, `${entry.producer.id}:${product}`)
    exactProducers.set(slug, `map:${entry.producer.id}`)
  }
  for (const [slug, product] of Object.entries(entry.alias_slugs)) {
    aliases.set(slug, `${entry.producer.id}:${product}`)
    exactProducers.set(slug, `map:${entry.producer.id}`)
  }
}
const colors = { white: 'Белое', red: 'Красное', rose: 'Розовое', orange: 'Оранжевое' }
const wines = service.active.map(w => {
  const producer = normal(w.producer)
  const known = producer && !/^(неизвест|нет данных|не указан|unknown|n\/a)/.test(producer)
  // A missing sparkling cue is unknown. It does not establish a still wine.
  const category = normal(w.category)
  const sparkle = /игрист/.test(category) ? 'sparkling' : /тихое|тихие/.test(category) ? 'still' : null
  return {
    slug: w.slug, name: w.name, producer: w.producer || '', region: w.region || '', grapes: w.grapes,
    color: colors[w.color] || '', category: w.category || '', rating: 0,
    image: `/img/wines/400/${encodeURIComponent(w.slug)}.webp`, alcohol: w.alcohol,
    servingTemperature: w.serving_temperature, pairings: w.pairings, description: w.description, source: w.source_url,
    producerId: exactProducers.get(w.slug) || (known ? producers.get(producer) || `name:${producer}` : null),
    canonicalId: aliases.get(w.slug) || w.slug, sweetness: w.sweetness, sparkle,
  }
})
const output = { schemaVersion: 1, version: service.metadata.version, sources: service.metadata, wines }
const content = JSON.stringify(output) + '\n'
const outputPath = resolve(root, 'webui/server/data/alternative-catalog.json')
if (process.argv.includes('--check')) {
  if (await readFile(outputPath, 'utf8') !== content) throw new Error('Alternative catalog is stale. Regenerate it from the accepted catalog sources.')
  const code = await build({ entryPoints: [resolve(root, 'webui/shared/alternatives.ts')], bundle: true, platform: 'node', format: 'esm', write: false })
  const { compareWineFacts, rankAlternatives } = await import('data:text/javascript;base64,' + Buffer.from(code.outputFiles[0].text).toString('base64'))
  const anchors = JSON.parse(await readFile(resolve(root, 'webui/tests/data/f04-anchors.json'), 'utf8'))
  if (anchors.version !== output.version) throw new Error('Review anchor expectations for the selected catalog version.')
  let checked = 0
  for (const anchor of anchors.anchors) {
    const base = wines.find(wine => wine.slug === anchor.slug)
    if (!base) throw new Error('Anchor is absent from the selected catalog')
    for (const { wine } of rankAlternatives(base, wines)) {
      const source = service.compareWines([base.slug, wine.slug])
      for (const row of compareWineFacts(base, wine)) {
        const key = row.key === 'servingTemperature' ? 'serving_temperature' : row.key
        const expected = source.unknown_fields.includes(key) ? 'unknown' : source.shared.some(item => item.field === key) ? 'shared' : 'different'
        if (row.kind !== expected) throw new Error(`Comparison parity failed: ${base.slug}, ${wine.slug}, ${key}`)
      }
      checked++
    }
  }
  console.log(JSON.stringify({ factualComparisonPairsMatchMcp: checked }))
} else await writeFile(outputPath, content)
console.log(JSON.stringify({ wines: wines.length, version: output.version, bytes: Buffer.byteLength(content), sha256: sha256(content) }))
