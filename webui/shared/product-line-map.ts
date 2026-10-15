import abrauData from './data/product-line-maps/abrau-durso.json'
import type { Wine } from './catalog'
import { sourceWineUrl } from './catalog'

export interface LineSource { id: string; label: string; url: string }
export interface LineTier { id: string; label: string; rank: number; description: string; price_label: string; source_ids: string[] }
export interface LineGroup { id: string; name: string; tier_id: string; method: string; description: string; source_ids: string[] }
export interface LineProduct {
  id: string
  group_id: string
  name: string
  variant: string
  wine_slug: string | null
  wine_slug_aliases: string[]
  image: { src: string; source_id: string }
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

export const ABRAU_PRODUCT_LINE = abrauData as ProductLineMapData
export const PRODUCT_LINE_MAPS: ProductLineMapData[] = [ABRAU_PRODUCT_LINE]

const normalizedProducer = (value: string) => value.toLocaleLowerCase('ru').replace(/[^a-zа-яё0-9]/g, '')

export function findLineProduct(line: ProductLineMapData, slug?: string): LineProduct | undefined {
  if (!slug) return undefined
  return line.products.find(product => product.wine_slug === slug || product.wine_slug_aliases.includes(slug))
}

export function findProducerLine(wine: Pick<Wine, 'producer' | 'slug'>): ProductLineMapData | undefined {
  return PRODUCT_LINE_MAPS.find(line => findLineProduct(line, wine.slug)
    || line.producer.slug_prefixes.some(prefix => wine.slug.startsWith(prefix))
    || [line.producer.name, ...line.producer.aliases].some(name => normalizedProducer(name) === normalizedProducer(wine.producer)))
}

export type ProductLineResolution =
  | { status: 'none' | 'unsupported' }
  | { status: 'unplaced'; line: ProductLineMapData }
  | { status: 'placed' | 'alias'; line: ProductLineMapData; product: LineProduct }

export function resolveProductLine(wine?: Pick<Wine, 'producer' | 'slug'>): ProductLineResolution {
  if (!wine) return { status: 'none' }
  // Exact identities take priority over producer-name metadata.
  for (const line of PRODUCT_LINE_MAPS) {
    const product = findLineProduct(line, wine.slug)
    if (product) return { status: product.wine_slug === wine.slug ? 'placed' : 'alias', line, product }
  }
  const line = findProducerLine(wine)
  return line ? { status: 'unplaced', line } : { status: 'unsupported' }
}

export function productsInGroup(line: ProductLineMapData, groupId: string): LineProduct[] {
  return line.products.filter(product => product.group_id === groupId)
}

export function productPortalUrl(product: LineProduct): string | null {
  return product.wine_slug ? sourceWineUrl(product.wine_slug) : null
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
  for (const tier of line.tiers) {
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
    if (!product.image.src.startsWith(`/product-line-maps/${line.producer.id}/`) || !/^[a-z0-9/.-]+\.webp$/.test(product.image.src) || product.image.src.includes('..')) errors.push(`Unsafe image path: ${product.id}`)
    checkSources([...product.source_ids, product.image.source_id], product.id)
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

for (const line of PRODUCT_LINE_MAPS) {
  const errors = validateProductLineMap(line)
  if (errors.length) throw new Error(`Invalid product-line map ${line.producer.id}: ${errors.join('; ')}`)
}
