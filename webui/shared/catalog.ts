export interface Wine {
  slug: string
  name: string
  producer: string
  region: string
  grapes: string[]
  color: string
  category: string
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
