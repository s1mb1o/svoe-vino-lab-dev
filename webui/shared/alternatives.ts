import { sourceWineUrl, type Wine } from './catalog'

export interface AlternativeWine extends Wine {
  producerId: string | null
  canonicalId: string
  sweetness: string | null
  sparkle: 'still' | 'sparkling' | null
}
export interface AlternativeFilters { color?: string; sweetness?: string; sparkle?: string }
export interface AlternativeResult { wine: AlternativeWine; reasons: string[]; missing: string[] }
export interface AlternativeAnswer { base: AlternativeWine; results: AlternativeResult[]; version: string; explanation: string }
export const ALTERNATIVE_COLORS = ['Белое', 'Красное', 'Розовое', 'Оранжевое']
export const ALTERNATIVE_SUGAR: Record<string, string> = {
  dry: 'Сухое', semi_dry: 'Полусухое', semi_sweet: 'Полусладкое', sweet: 'Сладкое',
  brut: 'Брют', extra_brut: 'Экстра брют', brut_nature: 'Брют натюр',
}
export const normalizedFact = (value: string) => value.normalize('NFKC').toLocaleLowerCase('ru').replace(/ё/g, 'е').replace(/\s+/g, ' ').trim()
export const alternativeStyleLine = (wine: Wine) => [...new Set([wine.color, ALTERNATIVE_SUGAR[wine.sweetness || ''] || wine.category].filter(Boolean))].join(' · ')

// Bounded similar-style slice of the legacy rankAlternatives flow.
// Eligibility is strict. A diversity score cannot override producer exclusion.
export function rankAlternatives(base: AlternativeWine, wines: readonly AlternativeWine[], filters: AlternativeFilters = {}): AlternativeResult[] {
  if (!base.producerId || !base.color || !base.sweetness) return []
  const color = filters.color || base.color
  const sugar = filters.sweetness || base.sweetness
  const grapes = new Set(base.grapes.map(normalizedFact))
  const seen = new Set([base.canonicalId])
  const eligible: Array<AlternativeResult & { score: number }> = []
  for (const wine of wines) {
    if (!wine.producerId || wine.producerId === base.producerId || seen.has(wine.canonicalId)
      || wine.color !== color || wine.sweetness !== sugar || (filters.sparkle && wine.sparkle !== filters.sparkle)) continue
    const shared = [...new Set(wine.grapes.filter(grape => grapes.has(normalizedFact(grape))))]
    if (!shared.length) continue
    seen.add(wine.canonicalId)
    eligible.push({ wine, score: shared.length, reasons: [`Другая винодельня: ${wine.producer}`, `Общие сорта: ${shared.join(', ')}`, `${wine.color}, ${ALTERNATIVE_SUGAR[wine.sweetness!]}`], missing: wine.sparkle ? [] : ['Тихое или игристое: нет данных'] })
  }
  return eligible.sort((a, b) => b.score - a.score || a.wine.slug.localeCompare(b.wine.slug, 'en')).slice(0, 5).map(({ score: _score, ...result }) => result)
}

export interface ComparisonPair { base: Wine; candidate: Wine; version: string }
export interface SavedComparisonAnswer {
  base: Wine
  items: Array<{ slug: string; wine: Wine | null }>
  version: string
}
export interface ComparisonRow { key: string; label: string; left: string; right: string; kind: 'shared' | 'different' | 'unknown' }
export function compareWineFacts(left: Wine, right: Wine): ComparisonRow[] {
  if (left.slug === right.slug) throw new Error('Comparison requires distinct exact wine IDs')
  const fields: Array<[keyof Wine, string]> = [
    ['producer', 'Производитель'], ['region', 'Регион'], ['category', 'Категория'], ['color', 'Цвет'],
    ['grapes', 'Сорта винограда'], ['sweetness', 'Сладость'], ['alcohol', 'Алкоголь'], ['servingTemperature', 'Температура подачи'],
  ]
  return fields.map(([key, label]) => {
    const a = left[key], b = right[key]
    const value = (v: unknown) => Array.isArray(v) ? v.join(', ') : typeof v === 'string' ? key === 'sweetness' ? ALTERNATIVE_SUGAR[v] || '' : v : ''
    const comparable = (v: unknown) => Array.isArray(v) ? v.map(normalizedFact).sort().join('|') : normalizedFact(value(v))
    const known = Boolean(value(a).trim() && value(b).trim())
    return { key, label, left: value(a) || 'Нет данных', right: value(b) || 'Нет данных', kind: !known ? 'unknown' : comparable(a) === comparable(b) ? 'shared' : 'different' }
  })
}

// Storage and login continuation accept only bounded public fields.
export function publicWine(value: unknown): Wine | null {
  if (!value || typeof value !== 'object') return null
  const v = value as Record<string, unknown>
  if (typeof v.slug !== 'string' || !/^[a-z0-9][a-z0-9_-]{0,199}$/.test(v.slug) || typeof v.name !== 'string' || !v.name.trim()) return null
  const text = (key: string, max = 300) => typeof v[key] === 'string' ? (v[key] as string).slice(0, max) : ''
  const list = (key: string) => Array.isArray(v[key]) ? (v[key] as unknown[]).filter((s): s is string => typeof s === 'string').slice(0, 24).map(s => s.slice(0, 100)) : []
  return { slug: v.slug, name: text('name'), producer: text('producer'), region: text('region'), grapes: list('grapes'), color: text('color'), category: text('category'), sweetness: typeof v.sweetness === 'string' && Object.hasOwn(ALTERNATIVE_SUGAR, v.sweetness) ? v.sweetness : null, rating: 0, image: '', alcohol: text('alcohol') || null, servingTemperature: text('servingTemperature') || null, pairings: list('pairings'), description: text('description', 3000) || null, source: sourceWineUrl(v.slug) }
}
export function publicPair(value: unknown): ComparisonPair | null {
  const v = value as Partial<ComparisonPair> | null
  if (!v || typeof v.version !== 'string' || !/^[a-f0-9]{64}$/.test(v.version)) return null
  const base = publicWine(v.base), candidate = publicWine(v.candidate)
  return base && candidate && base.slug !== candidate.slug ? { base, candidate, version: v.version } : null
}
