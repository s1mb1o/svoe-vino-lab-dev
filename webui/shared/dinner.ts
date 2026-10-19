import taxonomy from './data/dinner-taxonomy.json'

export const DINNER_TIMEOUT_MS = 180_000
export const DINNER_MAX_BODY_BYTES = 8 * 1024 * 1024
export interface DinnerNode { id: string; parent_id: string | null; kind: string; label: string }
export const DINNER_NODES: readonly DinnerNode[] = taxonomy.nodes
export const DINNER_CATEGORIES = DINNER_NODES.filter(node => node.kind === 'fallback_class')
const nodeIds = new Set(DINNER_NODES.map(node => node.id))
export function dinnerNode(id: string | null | undefined) { return DINNER_NODES.find(node => node.id === id) }

export interface DinnerWine {
  wine_slug: string
  name: string
  producer: string | null
  source_url: string
  selection_source: 'curated' | 'embedding'
  reason: string
  facts: { color: string; sweetness: string; wine_kind: string; alcohol_percent: number | null; reported_grapes: string[] }
}
export interface DinnerPage {
  status: 'ok' | 'no_results' | 'needs_category'
  resolved_node_id: string | null
  results: DinnerWine[]
  next_cursor: string | null
  shown_count: number
  total_eligible: number
  needs_clarification: boolean
  clarification_question: string | null
}
export type DinnerAction = 'recognize' | 'recommendations' | 'more'
export interface DinnerSelection {
  confirmed_dish?: string
  node_id?: string
  user_constraints?: Record<string, string>
  confirmed_attributes?: Record<string, string | boolean>
  limit?: number
}
const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value)
const text = (value: unknown, max: number): value is string => typeof value === 'string' && value.length > 0 && value.length <= max
const choice = (value: unknown, choices: string[]) => typeof value === 'string' && choices.includes(value)
const colors = ['red', 'white', 'rose', 'orange']
const sweetness = ['dry', 'semi_dry', 'semi_sweet', 'sweet', 'brut', 'extra_brut', 'brut_nature']
const kinds = ['still', 'sparkling']
const attributes: Record<string, (string | boolean)[]> = {
  heat: ['none', 'low', 'medium', 'high'], acidity: ['low', 'medium', 'high'],
  sauce_sweetness: ['none', 'low', 'medium', 'high'], fatty_cream_sauce: [true, false],
}
export function validDinnerRequest(action: DinnerAction, body: unknown): body is Record<string, unknown> {
  if (!object(body)) return false
  if (action === 'more') return Object.keys(body).length === 1 && text(body.cursor, 1_500_000)
  const allowed = ['user_constraints', 'confirmed_attributes', 'limit', ...(action === 'recognize' ? ['image_base64'] : ['node_id', 'confirmed_dish'])]
  if (Object.keys(body).some(key => !allowed.includes(key)) || (body.limit !== undefined && body.limit !== 3)) return false
  if (action === 'recognize') {
    if (!text(body.image_base64, 7_000_000) || !/^data:image\/(?:jpeg|png);base64,[A-Za-z0-9+/]+={0,2}$/.test(body.image_base64)) return false
  } else if ((body.node_id === undefined) === (body.confirmed_dish === undefined)
    || (body.node_id !== undefined && (!text(body.node_id, 200) || !nodeIds.has(body.node_id)))
    || (body.confirmed_dish !== undefined && (!text(body.confirmed_dish, 500) || !body.confirmed_dish.trim()))) return false
  if (body.user_constraints !== undefined) {
    if (!object(body.user_constraints)) return false
    for (const [key, value] of Object.entries(body.user_constraints)) {
      if (key === 'color' ? !choice(value, colors) : key === 'sweetness' ? !choice(value, sweetness)
        : key === 'wine_kind' ? !choice(value, kinds) : key === 'exclude_producer' ? !text(value, 400) : true) return false
    }
  }
  if (body.confirmed_attributes !== undefined) {
    if (!object(body.confirmed_attributes)) return false
    for (const [key, value] of Object.entries(body.confirmed_attributes)) {
      if (!Object.hasOwn(attributes, key) || !attributes[key]!.includes(value as string | boolean)) return false
    }
  }
  return true
}

function validSource(value: unknown, slug: string) {
  if (!text(value, 2000)) return false
  try {
    const url = new URL(value)
    return url.protocol === 'https:' && url.hostname === 'vino-svoe.ru' && !url.port && !url.username && !url.password
      && !url.search && !url.hash && decodeURIComponent(url.pathname).replace(/\/$/, '') === '/wines/' + slug
  } catch { return false }
}

// Project only UI fields. Provider receipts, internal endpoints and rule diagnostics stay on the server.
export function parseDinnerPage(value: unknown): DinnerPage | null {
  if (!object(value) || !choice(value.status, ['ok', 'no_results', 'needs_category'])
    || (value.resolved_node_id !== null && (!text(value.resolved_node_id, 200) || !nodeIds.has(value.resolved_node_id)))
    || !Array.isArray(value.results) || value.results.length > 3 || typeof value.needs_clarification !== 'boolean'
    || (value.clarification_question !== null && !text(value.clarification_question, 2000))) return null
  const results: DinnerWine[] = []
  for (const wine of value.results) {
    if (!object(wine) || !text(wine.wine_slug, 500) || !/^[a-z0-9][a-z0-9_-]*$/.test(wine.wine_slug)
      || !text(wine.name, 1000) || (wine.producer !== null && !text(wine.producer, 500))
      || !validSource(wine.source_url, wine.wine_slug) || !choice(wine.selection_source, ['curated', 'embedding'])
      || !text(wine.reason, 15_000) || !object(wine.facts) || !choice(wine.facts.color, colors)
      || !choice(wine.facts.sweetness, sweetness) || !choice(wine.facts.wine_kind, kinds)
      || (wine.facts.alcohol_percent !== null && (typeof wine.facts.alcohol_percent !== 'number' || !Number.isFinite(wine.facts.alcohol_percent) || wine.facts.alcohol_percent < 0 || wine.facts.alcohol_percent > 100))
      || !Array.isArray(wine.facts.reported_grapes) || wine.facts.reported_grapes.length > 50 || wine.facts.reported_grapes.some(grape => !text(grape, 400))) return null
    results.push({ wine_slug: wine.wine_slug, name: wine.name, producer: wine.producer as string | null,
      source_url: wine.source_url as string, selection_source: wine.selection_source as DinnerWine['selection_source'], reason: wine.reason,
      facts: { color: wine.facts.color as string, sweetness: wine.facts.sweetness as string, wine_kind: wine.facts.wine_kind as string,
        alcohol_percent: wine.facts.alcohol_percent as number | null, reported_grapes: wine.facts.reported_grapes as string[] } })
  }
  const unknown = value.status === 'needs_category'
  const cursor = unknown ? null : value.next_cursor
  const shown = unknown ? 0 : value.shown_count
  const total = unknown ? 0 : value.total_eligible
  if ((cursor !== null && !text(cursor, 1_500_000)) || !Number.isInteger(shown) || !Number.isInteger(total)
    || (shown as number) < results.length || (total as number) < (shown as number) || (total as number) > 2500
    || new Set(results.map(wine => wine.wine_slug)).size !== results.length
    || (unknown && (value.resolved_node_id !== null || results.length))
    || (!unknown && value.resolved_node_id === null)
    || (value.status === 'no_results' && (results.length || cursor !== null || total !== 0))
    || (value.status === 'ok' && (!results.length || total === 0))
    || ((cursor === null) !== (shown === total))) return null
  return { status: value.status as DinnerPage['status'], resolved_node_id: value.resolved_node_id as string | null,
    results, next_cursor: cursor as string | null, shown_count: shown as number, total_eligible: total as number,
    needs_clarification: value.needs_clarification, clarification_question: value.clarification_question as string | null }
}
