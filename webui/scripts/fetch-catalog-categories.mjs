import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
import { BUNDLE_PATH } from '../../mcp/src/catalog.mjs'

// An explicit maintenance command; builds and inference never call the source API.
const root = fileURLToPath(new URL('../../', import.meta.url))
const source = 'https://api.vino-svoe.ru/v1/wines'
const rows = async path => (await readFile(resolve(root, path), 'utf8')).trim().split('\n').map(JSON.parse)
const bundle = new Set((await rows(`${BUNDLE_PATH}/wines.jsonl`)).map(row => row.wine_slug))
const active = (await rows('workbench/db-export/rows/wine_catalog.jsonl'))
  .filter(row => row.state === 'Active' && bundle.has(row.wine_slug)).map(row => row.wine_slug).sort()

async function json(url, missingAllowed = false) {
  for (let attempt = 0; ; attempt++) {
    try {
      const response = await fetch(url, { headers: { accept: 'application/json' }, redirect: 'error', signal: AbortSignal.timeout(15000) })
      if (missingAllowed && response.status === 404) return null
      if (!response.ok) throw new Error(`Source returned HTTP ${response.status}`)
      const bytes = new Uint8Array(await response.arrayBuffer())
      if (bytes.length > 1024 * 1024) throw new Error('Source page is too large')
      return JSON.parse(new TextDecoder().decode(bytes))
    } catch (error) { if (attempt === 2) throw error }
  }
}

const pageUrl = page => `${source}?page=${page}&perPage=30`
const first = await json(pageUrl(1))
if (!Number.isInteger(first.totalPages) || first.totalPages < 1 || first.totalPages > 200 || !Number.isInteger(first.totalItems)) throw new Error('Invalid source pagination')
const categories = new Map()
function collect(page, expected) {
  if (page.currentPage !== expected || page.totalPages !== first.totalPages || page.totalItems !== first.totalItems || !Array.isArray(page.items)) throw new Error('Source pagination changed during collection')
  for (const item of page.items) {
    if (typeof item.slug !== 'string' || typeof item.category !== 'string' || categories.has(item.slug)) throw new Error('Invalid or duplicate source card')
    categories.set(item.slug, item.category)
  }
}
collect(first, 1)
let next = 2
await Promise.all(Array.from({ length: 3 }, async () => {
  while (next <= first.totalPages) {
    const page = next++
    collect(await json(pageUrl(page)), page)
  }
}))
if (categories.size !== first.totalItems) throw new Error('Source catalog count mismatch')
const missing = active.filter(slug => !categories.has(slug))
if (missing.length > 200) throw new Error('Too many pinned IDs are absent from the source listing')
for (const slug of missing) {
  const card = await json(`${source}/${encodeURIComponent(slug)}`, true)
  if (card === null) continue
  if (card.slug !== slug || typeof card.category?.name !== 'string') throw new Error('Exact source card does not match the pinned ID')
  categories.set(slug, card.category.name)
}
const output = {
  schemaVersion: 1, source, checkedAt: new Date().toISOString(),
  categories: active.filter(slug => categories.has(slug)).map(slug => ({ slug, category: categories.get(slug) })),
  unavailableSlugs: active.filter(slug => !categories.has(slug)),
}
await writeFile(resolve(root, 'webui/docs/catalog-category-provenance.json'), JSON.stringify(output, null, 2) + '\n')
console.log(JSON.stringify({ pinned: active.length, categories: output.categories.length, unavailable: output.unavailableSlugs }))
