import { Buffer } from 'node:buffer'
import { createError } from 'h3'
import { sourceWineUrl, type Wine } from '#shared/catalog'

const SOURCE_API_ORIGIN = 'https://api.vino-svoe.ru'
const SOURCE_RESPONSE_LIMIT = 256 * 1024
const SOURCE_SLUG = /^[a-z0-9](?:[a-z0-9-]{0,198}[a-z0-9])?$/

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : ''
}

function nestedText(value: unknown, key: string): string {
  return value && typeof value === 'object' ? text((value as Record<string, unknown>)[key]) : ''
}

function sourceImageUrl(value: unknown): string | null {
  const path = text(value)
  if (!path) return null
  try {
    const url = new URL(path, SOURCE_API_ORIGIN)
    if (url.origin !== SOURCE_API_ORIGIN || url.search || url.hash || !url.pathname.startsWith('/uploads/')) return null
    return `${SOURCE_API_ORIGIN}/v1/img/str-api/640/640/resize${url.pathname}`
  } catch {
    return null
  }
}

function wineStyle(value: unknown): { color: string; category: string } {
  const style = nestedText(value, 'name')
  const match = style.match(/(?:^|\s)(белое|красное|розовое|оранжевое)(?:\s|$)/i)
  if (!match?.[1]) return { color: '', category: style }
  const color = match[1][0]!.toLocaleUpperCase('ru') + match[1].slice(1).toLocaleLowerCase('ru')
  const category = style.replace(match[0], ' ').replace(/\s+/g, ' ').trim()
  return { color, category }
}

function percent(value: unknown): string | null {
  if (typeof value === 'number' && Number.isFinite(value)) return `${value}%`
  const result = text(value)
  return result ? result.includes('%') ? result : `${result}%` : null
}

function temperature(value: unknown): string | null {
  const result = text(value)
  return result ? /°|C/i.test(result) ? result : `${result}°C` : null
}

export function normalizeSourceWine(value: unknown, expectedSlug: string): Wine | null {
  if (!value || typeof value !== 'object') return null
  const item = value as Record<string, unknown>
  if (item.slug !== expectedSlug) return null
  const name = text(item.title)
  const image = sourceImageUrl(item.image && typeof item.image === 'object' ? (item.image as Record<string, unknown>).url : null)
  if (!name || !image) return null
  const style = wineStyle(item.category)
  const grapes = Array.isArray(item.grapes) ? item.grapes.map(grape => nestedText(grape, 'name')).filter(Boolean) : []
  const pairings = Array.isArray(item.dishes) ? item.dishes.map(dish => nestedText(dish, 'name')).filter(Boolean) : []
  const rating = typeof item.publicRating === 'number' && Number.isFinite(item.publicRating) ? item.publicRating : 0
  const description = text(item.description) || null
  return {
    slug: expectedSlug,
    name,
    producer: nestedText(item.manufacturer, 'name'),
    region: nestedText(item.region, 'name'),
    grapes,
    color: style.color,
    category: style.category,
    rating,
    image,
    alcohol: percent(item.alcohol),
    servingTemperature: temperature(item.temperature),
    pairings,
    description,
    source: sourceWineUrl(expectedSlug),
  }
}

async function boundedJson(response: Response): Promise<unknown> {
  const declared = Number(response.headers.get('content-length'))
  if (Number.isFinite(declared) && declared > SOURCE_RESPONSE_LIMIT) throw new Error('Source response is too large')
  const reader = response.body?.getReader()
  if (!reader) throw new Error('Source response is empty')
  const chunks: Uint8Array[] = []
  let total = 0
  try {
    while (true) {
      const next = await reader.read()
      if (next.done) break
      total += next.value.length
      if (total > SOURCE_RESPONSE_LIMIT) throw new Error('Source response is too large')
      chunks.push(next.value)
    }
  } finally {
    await reader.cancel().catch(() => {})
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf8'))
}

export async function fetchSourceWine(slug: string, options: { fetch?: typeof fetch; timeoutMs?: number } = {}): Promise<Wine | null> {
  if (!SOURCE_SLUG.test(slug)) return null
  const signal = AbortSignal.timeout(options.timeoutMs ?? 2500)
  try {
    const response = await (options.fetch || fetch)(`${SOURCE_API_ORIGIN}/v1/wines/${encodeURIComponent(slug)}`, {
      headers: { accept: 'application/json' },
      redirect: 'error',
      signal,
    })
    if (response.status === 404) return null
    if (!response.ok) throw new Error(`Source returned ${response.status}`)
    const wine = normalizeSourceWine(await boundedJson(response), slug)
    if (!wine) throw new Error('Source returned invalid wine metadata')
    return wine
  } catch (error) {
    if (signal.aborted) throw createError({ statusCode: 504, statusMessage: 'Wine metadata source timed out' })
    if (error && typeof error === 'object' && 'statusCode' in error) throw error
    throw createError({ statusCode: 502, statusMessage: 'Wine metadata source failed' })
  }
}
