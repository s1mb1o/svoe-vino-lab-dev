import type { DiaryWine } from './diary'

export const PREFERENCE_COLORS = { white: 'Белое', red: 'Красное', rose: 'Розовое', orange: 'Оранжевое' } as const
export const PREFERENCE_SWEETNESS = { dry: 'Сухое', semi_dry: 'Полусухое', semi_sweet: 'Полусладкое', sweet: 'Сладкое' } as const
export const PREFERENCE_BODY = { any: 'Не важно', light: 'Лёгкое', medium: 'Среднее', full: 'Насыщенное' } as const
export const PREFERENCE_FRESHNESS = { any: 'Не важно', fresh: 'Свежее', soft: 'Мягкое' } as const

export interface TastePreferences {
  schema_version: 1
  colors: Array<keyof typeof PREFERENCE_COLORS>
  sparkling: boolean | null
  sweetness: Array<keyof typeof PREFERENCE_SWEETNESS>
  body: keyof typeof PREFERENCE_BODY
  freshness: keyof typeof PREFERENCE_FRESHNESS
  grapes: string[]
}
export interface WineRating { slug: string; rating: number; note: string | null; updated_at: string; wine?: DiaryWine | null }
export const emptyPreferences = (): TastePreferences => ({ schema_version: 1, colors: [], sparkling: null, sweetness: [], body: 'any', freshness: 'any', grapes: [] })

/** Validate a bounded, versioned statement of preference; never infer one from activity. */
export function parsePreferences(value: unknown): TastePreferences {
  const invalid = () => { throw new Error('Invalid preferences') }
  if (!value || typeof value !== 'object' || Array.isArray(value)) return invalid()
  const input = value as Record<string, unknown>
  const result = { ...emptyPreferences(), ...input }
  if (Object.keys(input).some(key => !Object.hasOwn(emptyPreferences(), key)) || result.schema_version !== 1) return invalid()
  if (result.sparkling !== null && typeof result.sparkling !== 'boolean') return invalid()
  if (!Object.hasOwn(PREFERENCE_BODY, result.body) || !Object.hasOwn(PREFERENCE_FRESHNESS, result.freshness)) return invalid()
  for (const [key, vocabulary, max] of [['colors', PREFERENCE_COLORS, 4], ['sweetness', PREFERENCE_SWEETNESS, 4], ['grapes', null, 16]] as const) {
    const values = result[key]
    if (!Array.isArray(values) || values.length > max || values.some(item => typeof item !== 'string')) return invalid()
    if (values.some(item => vocabulary ? !Object.hasOwn(vocabulary, item) : !item.trim() || [...item].length > 80 || /[\u0000-\u001f\u007f-\u009f]/u.test(item))) return invalid()
    if (new Set(values.map(item => item.trim().toLocaleLowerCase('ru'))).size !== values.length) return invalid()
  }
  return { ...result, grapes: result.grapes.map(item => item.trim()) } as TastePreferences
}
