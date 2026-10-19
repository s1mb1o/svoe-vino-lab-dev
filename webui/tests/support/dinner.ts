import type { DinnerPage, DinnerWine } from '../../shared/dinner'

export const dinnerWine = (id: number): DinnerWine => ({
  wine_slug: `dinner-fixture-${id}`, name: `Fixture wine ${id}`, producer: `Fixture producer ${id}`,
  source_url: `https://vino-svoe.ru/wines/dinner-fixture-${id}`, selection_source: id <= 3 ? 'curated' : 'embedding',
  reason: 'A test fixture for the UI contract.',
  facts: { color: 'red', sweetness: 'dry', wine_kind: 'still', alcohol_percent: 13, reported_grapes: ['Cabernet Sauvignon'] },
})
export const dinnerPage = (overrides: Partial<DinnerPage> = {}): DinnerPage => ({
  status: 'ok', resolved_node_id: 'ribeye_grilled', results: [1, 2, 3].map(dinnerWine),
  next_cursor: 'fixture-first-cursor', shown_count: 3, total_eligible: 6,
  needs_clarification: false, clarification_question: null, ...overrides,
})
