import { describe, expect, it } from 'vitest'
import snapshot from '../server/data/alternative-catalog.json'
import { compareWineFacts, publicPair, publicWine, rankAlternatives, type AlternativeWine } from '../shared/alternatives'
import { makeOfflineCard, validOfflineCard } from '../shared/offline-cards'

const base: AlternativeWine = { slug: 'source-2023', canonicalId: 'source', name: 'Источник 2023', producer: 'Первый', producerId: 'p1', color: 'Красное', category: 'Красное сухое', sweetness: 'dry', sparkle: null, region: 'Кубань', grapes: ['Мерло'], rating: 0, image: '', alcohol: null, servingTemperature: null, pairings: [], description: null, source: '' }
const candidate = (change: Partial<AlternativeWine> = {}): AlternativeWine => ({ ...base, slug: 'candidate-2022', canonicalId: 'candidate', producer: 'Второй', producerId: 'p2', name: 'Кандидат 2022', ...change })
const version = 'a'.repeat(64)

describe('strict other-producer alternatives', () => {
  it('excludes the source, its alias, producer aliases, unknown producers, duplicates, and missing hard-filter fields', () => {
    const good = candidate()
    const results = rankAlternatives(base, [base, candidate({ slug: 'source-alias', canonicalId: base.canonicalId }), candidate({ slug: 'same-producer', producerId: base.producerId }), candidate({ slug: 'unknown', producerId: null }), candidate({ slug: 'no-color', color: '' }), candidate({ slug: 'no-sugar', sweetness: null }), good, { ...good }, candidate({ slug: 'equivalent', canonicalId: good.canonicalId })])
    expect(results.map(result => result.wine.slug)).toEqual([good.slug])
    expect(results[0]!.reasons.join(' ')).toContain('Общие сорта: Мерло')
  })
  it('does not infer still wine from missing sparkling evidence', () => {
    expect(rankAlternatives(base, [candidate()], { sparkle: 'still' })).toEqual([])
    expect(rankAlternatives(base, [candidate({ sparkle: 'sparkling' })], { sparkle: 'sparkling' })).toHaveLength(1)
  })
  it('does not relax constraints to fill results', () => {
    expect(rankAlternatives({ ...base, producerId: null }, [candidate()])).toEqual([])
    expect(rankAlternatives(base, [candidate({ grapes: ['Сира'] })])).toEqual([])
    expect(rankAlternatives(base, [candidate()], { color: 'Белое' })).toEqual([])
    expect(rankAlternatives(base, [candidate()], { sweetness: 'sweet' })).toEqual([])
  })
  it('preserves exact accepted IDs and producer exclusion across the whole pinned catalog', () => {
    const wines = snapshot.wines as AlternativeWine[]
    const slugs = new Set(wines.map(wine => wine.slug))
    expect(slugs.size).toBe(2093)
    for (const wine of wines) for (const result of rankAlternatives(wine, wines)) {
      expect(slugs.has(result.wine.slug)).toBe(true)
      expect(result.wine.producerId).toBeTruthy()
      expect(result.wine.producerId).not.toBe(wine.producerId)
      expect(result.wine.canonicalId).not.toBe(wine.canonicalId)
      expect(result.wine.color).toBe(wine.color)
      expect(result.wine.sweetness).toBe(wine.sweetness)
    }
  })
})

describe('factual comparison and bounded public copies', () => {
  it('keeps shared, different, and unknown fields separate', () => {
    const rows = compareWineFacts(base, candidate({ grapes: ['МЕРЛО'], region: 'Крым', sweetness: null }))
    expect(rows.find(row => row.key === 'grapes')?.kind).toBe('shared')
    expect(rows.find(row => row.key === 'region')?.kind).toBe('different')
    expect(rows.find(row => row.key === 'alcohol')).toMatchObject({ kind: 'unknown', left: 'Нет данных', right: 'Нет данных' })
    expect(rows.find(row => row.key === 'sweetness')?.kind).toBe('unknown')
    expect(() => compareWineFacts(base, base)).toThrow()
  })
  it('drops private and unexpected data, uploaded images, and arbitrary links', () => {
    const copy = publicWine({ ...base, image: 'data:image/jpeg;base64,private', note: 'private text', token: 'private-token', source: 'https://attacker.test/' })!
    expect(copy.image).toBe('')
    expect(copy.source).toBe('https://vino-svoe.ru/wines/source-2023')
    expect(JSON.stringify(copy)).not.toMatch(/private|attacker/)
    const saved = makeOfflineCard(copy, version, '2026-10-20T06:00:00.000Z')
    expect(validOfflineCard(saved)).toBe(true)
    expect(validOfflineCard({ ...saved, note: 'leak' })).toBe(false)
    expect(validOfflineCard({ ...saved, wine: { ...copy, note: 'leak' } })).toBe(false)
    expect(publicPair({ base, candidate: base, version })).toBe(null)
    expect(publicPair({ base, candidate: candidate(), version: 'bad' })).toBe(null)
    expect(publicWine({ ...base, slug: '../account' })).toBe(null)
  })
})
