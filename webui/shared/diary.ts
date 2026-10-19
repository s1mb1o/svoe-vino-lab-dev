// «Винный дневник» lists: the history of found wines and the saved wines.
// Plan: docs/plans/07_diary-history-and-saved.md (issues #71 and #64).

export const DIARY_SLUG_PATTERN = /^[a-z0-9](?:[a-z0-9_-]{0,198}[a-z0-9])?$/
export const DIARY_DAY_PATTERN = /^\d{4}-\d{2}-\d{2}$/

export const SAVED_STATUSES = ['not_tasted', 'want', 'liked', 'disliked'] as const
export type SavedStatus = typeof SAVED_STATUSES[number]
export const SAVED_STATUS_LABELS: Record<SavedStatus, string> = {
  not_tasted: 'Не пробовано',
  want: 'Отведать желаю',
  liked: 'Понравилось',
  disliked: 'Не понравилось',
}
export const DEFAULT_SAVED_STATUS: SavedStatus = 'not_tasted'

// Where a wine was saved from. `history` is the «История» tab of the diary.
export const SAVED_SOURCES = ['photo', 'shelf', 'lineup', 'dinner_lens', 'history'] as const
export type SavedSource = typeof SAVED_SOURCES[number]
export const SAVED_SOURCE_LABELS: Record<SavedSource, string> = {
  photo: 'Из поиска по фото',
  shelf: 'С полки',
  lineup: 'С карты линейки',
  dinner_lens: 'Из «Вино к блюду»',
  history: 'Из истории',
}

// Where a wine was found. The site records `photo` and `shelf`; the bots record their own source.
export const HISTORY_SOURCES = ['photo', 'shelf', 'telegram', 'max'] as const
export type HistorySource = typeof HISTORY_SOURCES[number]
export const SITE_HISTORY_SOURCES: readonly HistorySource[] = ['photo', 'shelf']
export const HISTORY_SOURCE_LABELS: Record<HistorySource, string> = {
  photo: 'Сайт',
  shelf: 'Полка',
  telegram: 'Telegram',
  max: 'MAX',
}

export const isSavedStatus = (value: unknown): value is SavedStatus => SAVED_STATUSES.includes(value as SavedStatus)
export const isSavedSource = (value: unknown): value is SavedSource => SAVED_SOURCES.includes(value as SavedSource)
export const isHistorySource = (value: unknown): value is HistorySource => HISTORY_SOURCES.includes(value as HistorySource)

/** The wine data that the diary keeps with a slug, so a list renders without the vino-svoe.ru API. */
export interface DiaryWine {
  name?: string
  producer?: string
  color?: string
  sugar?: string
  region?: string
  grapes?: string[]
}

export interface HistoryDay { metOn: string; source: HistorySource | string; firstAt: string }

export interface HistoryItem {
  slug: string
  wine: DiaryWine | null
  firstMetAt: string
  lastMetAt: string
  daysCount: number
  sources: string[]
  savedStatus: SavedStatus | null
  days?: HistoryDay[]
}

export interface SavedItem {
  slug: string
  wine: DiaryWine | null
  status: SavedStatus
  source: SavedSource | string
  addedAt: string
  updatedAt: string
  inHistory: boolean
}

export type HistoryRecordStatus = 'recorded' | 'already' | 'off'

const SNAPSHOT_TEXT = 200
const SNAPSHOT_GRAPE = 80
const SNAPSHOT_GRAPES = 12
const SNAPSHOT_BYTES = 2048

function clean(value: unknown, limit: number): string | undefined {
  if (typeof value !== 'string') return undefined
  const text = value.replace(/\s+/g, ' ').trim()
  return text ? text.slice(0, limit) : undefined
}

/**
 * Builds the snapshot that the account service accepts: known keys only, strings of 1–200
 * characters, at most 12 grapes, at most 2 KiB of JSON. Returns null when nothing is left.
 */
export function diarySnapshot(wine: { name?: unknown; producer?: unknown; color?: unknown; sugar?: unknown; category?: unknown; region?: unknown; grapes?: unknown }): DiaryWine | null {
  const snapshot: DiaryWine = {}
  const name = clean(wine.name, SNAPSHOT_TEXT)
  const producer = clean(wine.producer, SNAPSHOT_TEXT)
  const color = clean(wine.color, SNAPSHOT_TEXT)
  const sugar = clean(wine.sugar ?? wine.category, SNAPSHOT_TEXT)
  const region = clean(wine.region, SNAPSHOT_TEXT)
  if (name) snapshot.name = name
  if (producer) snapshot.producer = producer
  if (color) snapshot.color = color
  if (sugar) snapshot.sugar = sugar
  if (region) snapshot.region = region
  if (Array.isArray(wine.grapes)) {
    const grapes = wine.grapes.map(item => clean(item, SNAPSHOT_GRAPE)).filter((item): item is string => Boolean(item)).slice(0, SNAPSHOT_GRAPES)
    if (grapes.length) snapshot.grapes = grapes
  }
  const size = (value: DiaryWine) => new TextEncoder().encode(JSON.stringify(value)).byteLength
  if (size(snapshot) > SNAPSHOT_BYTES) delete snapshot.grapes
  if (size(snapshot) > SNAPSHOT_BYTES) delete snapshot.region
  return Object.keys(snapshot).length ? snapshot : null
}

// Color and sugar come as Russian text from the catalogue («Белое», «Полусухое», «Экстра брют»).
// The filters group the text by these keys.
export const COLOR_LABELS = { red: 'Красное', white: 'Белое', rose: 'Розовое', orange: 'Оранжевое' } as const
export type ColorKey = keyof typeof COLOR_LABELS

export const SUGAR_LABELS = {
  brut_nature: 'Брют натюр',
  extra_brut: 'Экстра брют',
  brut: 'Брют',
  dry: 'Сухое',
  semi_dry: 'Полусухое',
  semi_sweet: 'Полусладкое',
  sweet: 'Сладкое',
} as const
export type SugarKey = keyof typeof SUGAR_LABELS

const normalized = (value: string | undefined) => (value ?? '').toLocaleLowerCase('ru').replace(/ё/g, 'е').replace(/[-–—]/g, ' ').replace(/\s+/g, ' ').trim()

export function colorKey(value: string | undefined): ColorKey | null {
  const text = normalized(value)
  if (/красн/.test(text)) return 'red'
  if (/бел/.test(text)) return 'white'
  if (/розов/.test(text)) return 'rose'
  if (/оранж/.test(text)) return 'orange'
  return null
}

export function sugarKey(value: string | undefined): SugarKey | null {
  const text = normalized(value)
  if (/брют натюр|brut nature|нулев/.test(text)) return 'brut_nature'
  if (/экстра брют|extra brut/.test(text)) return 'extra_brut'
  if (/брют|brut/.test(text)) return 'brut'
  if (/полусух/.test(text)) return 'semi_dry'
  if (/полуслад/.test(text)) return 'semi_sweet'
  if (/сух/.test(text)) return 'dry'
  if (/слад|десерт/.test(text)) return 'sweet'
  return null
}

/** «Красное · Сухое», or an empty string. */
export function wineStyleLine(wine: DiaryWine | null | undefined): string {
  return [wine?.color, wine?.sugar].filter(Boolean).join(' · ')
}

export interface DiaryFilter {
  text: string
  color: ColorKey | ''
  sugar: SugarKey | ''
}

export function matchesFilter(slug: string, wine: DiaryWine | null, filter: DiaryFilter): boolean {
  if (filter.color && colorKey(wine?.color) !== filter.color) return false
  if (filter.sugar && sugarKey(wine?.sugar) !== filter.sugar) return false
  const query = normalized(filter.text)
  if (!query) return true
  const haystack = normalized([wine?.name, wine?.producer, wine?.region, slug.replace(/-/g, ' ')].filter(Boolean).join(' '))
  return query.split(' ').every(word => haystack.includes(word))
}
