// Pure product-line types and functions. Keep this module free of runtime imports:
// the MCP server imports it directly in Node.js, which cannot load the JSON registry.

export interface LineSource { id: string; label: string; url: string }
export interface LineTier { id: string; label: string; rank: number; description: string; price_label: string; source_ids: string[] }
export interface LineGroup { id: string; name: string; tier_id: string; method: string; description: string; source_ids: string[] }
export interface LineImageFrame {
  x: number
  y: number
  width: number
  height: number
  source_width: number
  source_height: number
}
export interface LineProduct {
  id: string
  group_id: string
  name: string
  variant: string
  catalog_card_label?: string
  wine_slug: string | null
  wine_slug_aliases: string[]
  image: { src: string; source_id: string; frame?: LineImageFrame } | null
  category: string
  style: string
  grapes: string[]
  description: string
  release_status: 'catalog' | 'archive' | 'limited'
  badges: string[]
  price: null | { amount: number; currency: string; as_of: string; source_id: string }
  source_ids: string[]
}
export interface ProductLineMapData {
  schema_version: number
  producer: { id: string; name: string; aliases: string[]; slug_prefixes: string[] }
  scope: { label: string; as_of: string; catalog_snapshot: string }
  sources: LineSource[]
  price_positioning: { kind: string; currency: string; disclaimer: string }
  tiers: LineTier[]
  groups: LineGroup[]
  products: LineProduct[]
}
export interface LineEdge { source: string; target: string; type: 'contains' }
export interface ProductLineWineRef { producer?: string | null; slug: string }

const normalizedProducer = (value: string) => value.toLocaleLowerCase('ru').replace(/[^a-zа-яё0-9]/g, '')

export function findLineProduct(line: ProductLineMapData, slug?: string): LineProduct | undefined {
  if (!slug) return undefined
  return line.products.find(product => product.wine_slug === slug || product.wine_slug_aliases.includes(slug))
}

export function findProducerLineIn(lines: ProductLineMapData[], wine: ProductLineWineRef): ProductLineMapData | undefined {
  const producer = normalizedProducer(wine.producer ?? '')
  return lines.find(line => findLineProduct(line, wine.slug))
    || lines.find(line => [line.producer.name, ...line.producer.aliases]
      .some(name => normalizedProducer(name) === producer))
    || lines.find(line => line.producer.slug_prefixes.some(prefix => wine.slug.startsWith(prefix)))
}

export type ProductLineResolution =
  | { status: 'none' | 'unsupported' }
  | { status: 'unplaced'; line: ProductLineMapData }
  | { status: 'placed' | 'alias'; line: ProductLineMapData; product: LineProduct }

export function resolveProductLineIn(lines: ProductLineMapData[], wine?: ProductLineWineRef): ProductLineResolution {
  if (!wine) return { status: 'none' }
  // Exact identities take priority over producer-name metadata.
  for (const line of lines) {
    const product = findLineProduct(line, wine.slug)
    if (product) return { status: product.wine_slug === wine.slug ? 'placed' : 'alias', line, product }
  }
  const line = findProducerLineIn(lines, wine)
  return line ? { status: 'unplaced', line } : { status: 'unsupported' }
}

// The index holds only what resolution needs. Pages load a full map on demand.
export interface ProductLineIndexSummary {
  products: number
  groups: number
  as_of: string
  cover: { src: string; frame?: LineImageFrame } | null
}
export interface ProductLineIndexEntry {
  producer: ProductLineMapData['producer']
  summary: ProductLineIndexSummary
  slugs: Record<string, string>
  alias_slugs: Record<string, string>
}
export interface ProductLineIndex { schema_version: 1; producers: ProductLineIndexEntry[] }

export type ProductLineIndexResolution =
  | { status: 'none' | 'unsupported' }
  | { status: 'unplaced'; producer: ProductLineMapData['producer'] }
  | { status: 'placed' | 'alias'; producer: ProductLineMapData['producer']; product_id: string }

function summaryOf(line: ProductLineMapData): ProductLineIndexSummary {
  const image = line.products.find(product => product.image)?.image
  const cover = image ? { src: image.src, ...(image.frame ? { frame: { ...image.frame } } : {}) } : null
  return { products: line.products.length, groups: line.groups.length, as_of: line.scope.as_of, cover }
}

const sortedRecord = (entries: [string, string][]) => Object.fromEntries(entries.sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0))

export function buildProductLineIndex(lines: ProductLineMapData[]): ProductLineIndex {
  const producers = [...lines].sort((a, b) => a.producer.name.localeCompare(b.producer.name, 'ru')).map(line => ({
    producer: { id: line.producer.id, name: line.producer.name, aliases: [...line.producer.aliases], slug_prefixes: [...line.producer.slug_prefixes] },
    // The index page shows these values. The first product image of the map is its cover.
    summary: summaryOf(line),
    slugs: sortedRecord(line.products.flatMap(product => product.wine_slug ? [[product.wine_slug, product.id] as [string, string]] : [])),
    alias_slugs: sortedRecord(line.products.flatMap(product => product.wine_slug_aliases.map(slug => [slug, product.id] as [string, string]))),
  }))
  return { schema_version: 1, producers }
}

// Same order as resolveProductLineIn: exact slug, verified alias, producer name, slug prefix.
export function resolveProductLineIndex(index: ProductLineIndex, wine?: ProductLineWineRef): ProductLineIndexResolution {
  if (!wine) return { status: 'none' }
  for (const entry of index.producers) {
    if (Object.hasOwn(entry.slugs, wine.slug)) return { status: 'placed', producer: entry.producer, product_id: entry.slugs[wine.slug]! }
    if (Object.hasOwn(entry.alias_slugs, wine.slug)) return { status: 'alias', producer: entry.producer, product_id: entry.alias_slugs[wine.slug]! }
  }
  const producer = normalizedProducer(wine.producer ?? '')
  const entry = index.producers.find(item => [item.producer.name, ...item.producer.aliases].some(name => normalizedProducer(name) === producer))
    || index.producers.find(item => item.producer.slug_prefixes.some(prefix => wine.slug.startsWith(prefix)))
  return entry ? { status: 'unplaced', producer: entry.producer } : { status: 'unsupported' }
}

export function productsInGroup(line: ProductLineMapData, groupId: string): LineProduct[] {
  return line.products.filter(product => product.group_id === groupId)
}

// Containment has one source of truth. No independent edge list can diverge from membership.
export function productLineEdges(line: ProductLineMapData): LineEdge[] {
  return [
    ...line.groups.map(group => ({ source: line.producer.id, target: group.id, type: 'contains' as const })),
    ...line.products.map(product => ({ source: product.group_id, target: product.id, type: 'contains' as const })),
  ]
}

export function validateProductLineMap(line: ProductLineMapData): string[] {
  const errors: string[] = []
  if (line.schema_version !== 1) errors.push('Unsupported schema_version')
  if (!/^\d{4}-\d{2}-\d{2}$/.test(line.scope.as_of)) errors.push('Invalid scope date')
  const unique = (values: string[], label: string) => {
    if (values.some(value => !value || !/^[a-z0-9][a-z0-9-]*$/.test(value))) errors.push(`Invalid ${label}`)
    if (new Set(values).size !== values.length) errors.push(`Duplicate ${label}`)
  }
  unique([line.producer.id, ...line.groups.map(group => group.id), ...line.products.map(product => product.id)], 'node ID')
  unique(line.tiers.map(tier => tier.id), 'tier ID')
  unique(line.sources.map(source => source.id), 'source ID')
  const sources = new Set(line.sources.map(source => source.id))
  const tiers = new Set(line.tiers.map(tier => tier.id))
  const groups = new Set(line.groups.map(group => group.id))
  const slugs: string[] = []
  const checkSources = (ids: string[], label: string) => {
    if (!ids.length || ids.some(id => !sources.has(id))) errors.push(`Unknown or missing source: ${label}`)
  }
  for (const source of line.sources) {
    if (source.url && !/^https:\/\//.test(source.url)) errors.push(`Unsafe source URL: ${source.id}`)
  }
  const rankedTiers = line.tiers.filter(tier => tier.rank !== 0).map(tier => tier.rank)
  if (new Set(rankedTiers).size !== rankedTiers.length) errors.push('Duplicate premium tier rank')
  for (const tier of line.tiers) {
    if (!line.groups.some(group => group.tier_id === tier.id)) errors.push(`Empty tier: ${tier.id}`)
    if (!Number.isFinite(tier.rank)) errors.push(`Invalid tier rank: ${tier.id}`)
    checkSources(tier.source_ids, tier.id)
  }
  for (const group of line.groups) {
    if (!tiers.has(group.tier_id)) errors.push(`Unknown tier: ${group.id}`)
    if (!line.products.some(product => product.group_id === group.id)) errors.push(`Empty group: ${group.id}`)
    checkSources(group.source_ids, group.id)
  }
  for (const product of line.products) {
    if (!groups.has(product.group_id)) errors.push(`Unknown group: ${product.id}`)
    if (!product.name || !product.description || !product.style) errors.push(`Incomplete product: ${product.id}`)
    if (product.image === undefined) errors.push(`Missing image field: ${product.id}`)
    if (product.image != null && (!product.image.src.startsWith(`/product-line-maps/${line.producer.id}/`) || !/^[a-z0-9/.-]+\.webp$/.test(product.image.src) || product.image.src.includes('..'))) errors.push(`Unsafe image path: ${product.id}`)
    const frame = product.image?.frame
    if (frame && (![frame.x, frame.y, frame.width, frame.height, frame.source_width, frame.source_height].every(Number.isSafeInteger)
      || frame.x < 0 || frame.y < 0 || frame.width <= 0 || frame.height <= 0 || frame.source_width <= 0 || frame.source_height <= 0
      || frame.x + frame.width > frame.source_width || frame.y + frame.height > frame.source_height)) errors.push(`Invalid image frame: ${product.id}`)
    checkSources([...product.source_ids, ...(product.image ? [product.image.source_id] : [])], product.id)
    if (product.wine_slug === null && product.wine_slug_aliases.length) errors.push(`Unlinked product has aliases: ${product.id}`)
    for (const slug of [product.wine_slug, ...product.wine_slug_aliases]) {
      if (slug === null) continue
      if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) errors.push(`Invalid wine slug: ${product.id}`)
      slugs.push(slug)
    }
    if (!['catalog', 'archive', 'limited'].includes(product.release_status)) errors.push(`Invalid release status: ${product.id}`)
    if (product.price !== null && (!(product.price.amount > 0) || !sources.has(product.price.source_id) || !/^\d{4}-\d{2}-\d{2}$/.test(product.price.as_of))) errors.push(`Unverified price: ${product.id}`)
  }
  if (new Set(slugs).size !== slugs.length) errors.push('Ambiguous wine slug or alias')
  return errors
}

export function validateProductLineMaps(lines: ProductLineMapData[]): string[] {
  const errors = lines.flatMap(line => validateProductLineMap(line).map(error => `${line.producer.id}: ${error}`))
  const producers = new Set<string>()
  const slugs = new Map<string, string>()
  const names = new Map<string, string>()
  const prefixes = new Map<string, string>()
  for (const line of lines) {
    const id = line.producer.id
    if (producers.has(id)) errors.push(`Duplicate producer: ${id}`)
    producers.add(id)
    for (const name of [line.producer.name, ...line.producer.aliases]) {
      const key = normalizedProducer(name)
      if (!key) errors.push(`Empty producer name: ${id}`)
      if (names.has(key) && names.get(key) !== id) errors.push(`Ambiguous producer name: ${name}`)
      names.set(key, id)
    }
    for (const prefix of line.producer.slug_prefixes) {
      if (!/^[a-z0-9]+(?:-[a-z0-9]+)*-$/.test(prefix)) errors.push(`Invalid producer prefix: ${id}`)
      for (const [other, owner] of prefixes) {
        if (owner !== id && (other.startsWith(prefix) || prefix.startsWith(other))) errors.push(`Ambiguous producer prefix: ${prefix}`)
      }
      prefixes.set(prefix, id)
    }
    for (const product of line.products) {
      for (const slug of [product.wine_slug, ...product.wine_slug_aliases]) {
        if (slug === null) continue
        if (slugs.has(slug) && slugs.get(slug) !== id) errors.push(`Ambiguous producer slug: ${slug}`)
        slugs.set(slug, id)
      }
    }
  }
  return errors
}
