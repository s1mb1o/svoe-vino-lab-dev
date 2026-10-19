import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'

// Export labels only. Wine eligibility, pairing rules and curation stay in Dinner Lens.
const source = new URL('../../dinner-lens/data/pairing-dataset.v4.json', import.meta.url)
const raw = readFileSync(source)
const dataset = JSON.parse(raw)
const nodes = dataset.nodes.map(({ id, parent_id, kind, label_ru }) => ({ id, parent_id, kind, label: label_ru }))
writeFileSync(new URL('../shared/data/dinner-taxonomy.json', import.meta.url), JSON.stringify({
  source: 'dinner-lens/data/pairing-dataset.v4.json',
  dataset_sha256: createHash('sha256').update(raw).digest('hex'),
  nodes,
}, null, 2) + '\n')
