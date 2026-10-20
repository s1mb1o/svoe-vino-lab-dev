export interface Wine {
  slug: string
  name: string
  producer: string
  region: string
  grapes: string[]
  color: string
  category: string
  sweetness?: string | null
  rating: number
  image: string
  alcohol: string | null
  servingTemperature: string | null
  pairings: string[]
  description: string | null
  source: string
}

export const MAX_IMAGE_BYTES = 10 * 1024 * 1024
// A matcher without HEIF support answers HTTP 422 for a HEIC photo (issue #44).
export const isHeicFile = (file: { type: string; name: string }) => /^image\/hei[cf]$/.test(file.type) || /\.hei[cf]$/i.test(file.name)
export const MOCK_SLUG = 'priboj-marchenko-beloe-polusuhoe'

export function extractSlug(value: unknown): string | null {
  const item = Array.isArray(value) ? value[0] : value
  if (!item || typeof item !== 'object' || !('slug' in item)) return null
  return typeof item.slug === 'string' && item.slug.trim().length > 0 ? item.slug : null
}

export function sourceWineUrl(slug: string): string {
  return `https://vino-svoe.ru/wines/${encodeURIComponent(slug)}`
}

export function isNoMatch(value: unknown): boolean {
  const item = Array.isArray(value) ? value[0] : value
  return Boolean(item && typeof item === 'object' && 'slug' in item && item.slug === '')
}

// Static wine images are served as image/webp from the media host.
// A wine with no image has no file.
export type WineImageSize = 1600 | 400
export function wineImageUrl(slug: string, size: WineImageSize = 1600): string {
  return `https://media.chtozavino.ru/img/wines/${size}/${encodeURIComponent(slug)}.webp`
}
