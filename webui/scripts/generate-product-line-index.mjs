// Writes shared/data/product-line-index.json from the producer maps.
// Usage: node scripts/generate-product-line-index.mjs [--check]
import { readFileSync, readdirSync, writeFileSync } from 'node:fs'
import { buildProductLineIndex, validateProductLineMaps } from '../shared/product-line-core.ts'

const mapsDirectory = new URL('../shared/data/product-line-maps/', import.meta.url)
const indexFile = new URL('../shared/data/product-line-index.json', import.meta.url)

const lines = readdirSync(mapsDirectory).filter(name => name.endsWith('.json')).sort()
  .map(name => JSON.parse(readFileSync(new URL(name, mapsDirectory), 'utf8')))
const errors = validateProductLineMaps(lines)
if (errors.length) {
  console.error(`Invalid product-line maps:\n${errors.join('\n')}`)
  process.exit(1)
}
const text = `${JSON.stringify(buildProductLineIndex(lines), null, 2)}\n`
if (process.argv.includes('--check')) {
  if (readFileSync(indexFile, 'utf8') !== text) {
    console.error('shared/data/product-line-index.json is out of date. Run `npm run line-maps:index`.')
    process.exit(1)
  }
  console.log(`Product-line index is current: ${lines.length} producers.`)
} else {
  writeFileSync(indexFile, text)
  console.log(`Wrote the product-line index: ${lines.length} producers.`)
}
