import { sourceWineUrl, type Wine } from './catalog'

export const MAX_SHELF_BOTTLES = 100
export const SHELF_TIMEOUT_MS = 330000
export type BottleBox = [number, number, number, number]

export interface GroupWineCard {
  name: string
  page_url: string
  producer: string | null
  category: string | null
  region: string | null
  color: string | null
  grapes: string | null
  sugar: string | null
  image_url: string | null
  qr_urls: string[]
}
export interface GroupMatchCandidate { rank: number; slug: string; score: number; wine: GroupWineCard }
export interface ShelfBottle { id: string; segmentation_score: number; box: BottleBox; mask: string; match: GroupMatchCandidate | null }
export interface ShelfResult {
  pipeline: string
  latency_ms: number
  image: { width: number; height: number; preview: string }
  bottles: ShelfBottle[]
  detected_count: number
  truncated: boolean
}
export function imageDataUrl(value: unknown, mime: 'jpeg' | 'png', maxLength: number): value is string {
  const prefix = `data:image/${mime};base64,`
  if (typeof value !== 'string' || !value.startsWith(prefix) || value.length >= maxLength) return false
  const data = value.slice(prefix.length)
  return data.length > 0 && /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(data)
}
export function validBox(value: unknown): value is BottleBox {
  return Array.isArray(value) && value.length === 4 && value.every(n => typeof n === 'number' && Number.isFinite(n) && n >= 0 && n <= 1) && value[2] > value[0] && value[3] > value[1]
}
function nullableString(value: unknown) { return value === null || typeof value === 'string' }
function validWineCard(value: unknown): value is GroupWineCard {
  const wine = value as GroupWineCard | null
  return Boolean(wine && typeof wine === 'object' && typeof wine.name === 'string' && wine.name
    && typeof wine.page_url === 'string' && wine.page_url
    && nullableString(wine.producer) && nullableString(wine.category) && nullableString(wine.region)
    && nullableString(wine.color) && nullableString(wine.grapes) && nullableString(wine.sugar)
    && nullableString(wine.image_url) && Array.isArray(wine.qr_urls) && wine.qr_urls.every(url => typeof url === 'string'))
}
function validCandidate(value: unknown): value is GroupMatchCandidate {
  const candidate = value as GroupMatchCandidate | null
  return Boolean(candidate && typeof candidate === 'object' && candidate.rank === 1
    && typeof candidate.slug === 'string' && candidate.slug
    && typeof candidate.score === 'number' && Number.isFinite(candidate.score)
    && validWineCard(candidate.wine))
}
export function validShelfResult(value: unknown): value is ShelfResult {
  const r = value as ShelfResult | null
  return Boolean(r && typeof r.pipeline === 'string' && r.pipeline && typeof r.latency_ms === 'number' && Number.isFinite(r.latency_ms) && r.latency_ms >= 0
    && r.image && Number.isInteger(r.image.width) && r.image.width > 0 && r.image.width <= 1600 && Number.isInteger(r.image.height) && r.image.height > 0 && r.image.height <= 1600
    && imageDataUrl(r.image.preview, 'jpeg', 8 * 1024 * 1024)
    && Array.isArray(r.bottles) && r.bottles.length <= MAX_SHELF_BOTTLES && r.bottles.every(b => b && typeof b === 'object') && new Set(r.bottles.map(b => b.id)).size === r.bottles.length
    && Number.isInteger(r.detected_count) && r.detected_count >= r.bottles.length && typeof r.truncated === 'boolean'
    && r.bottles.every(b => b && typeof b.id === 'string' && /^b[1-9]\d{0,2}$/.test(b.id) && validBox(b.box)
      && typeof b.segmentation_score === 'number' && Number.isFinite(b.segmentation_score) && b.segmentation_score >= 0 && b.segmentation_score <= 1
      && imageDataUrl(b.mask, 'png', 3 * 1024 * 1024)
      && (b.match === null || validCandidate(b.match))))
}

export function groupCandidateWine(candidate: GroupMatchCandidate): Wine {
  const card = candidate.wine
  return {
    slug: candidate.slug,
    name: card.name,
    producer: card.producer || '',
    region: card.region || '',
    grapes: card.grapes?.split(/[,;]/).map(value => value.trim()).filter(Boolean) || [],
    color: card.color || '',
    category: card.sugar || card.category || '',
    rating: 0,
    image: card.image_url || '',
    alcohol: null,
    servingTemperature: null,
    pairings: [],
    description: null,
    source: card.page_url || sourceWineUrl(candidate.slug),
  }
}
