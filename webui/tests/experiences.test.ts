import { describe, expect, it } from 'vitest'
import { ABRAU_LINE, DEMO_FOOD_PRODUCTS, WINE_STORIES, nextStoryIndex } from '../shared/experiences'

describe('local result experiences', () => {
  it('uses three domestic mock products and labels promoted placement', () => {
    expect(DEMO_FOOD_PRODUCTS).toHaveLength(3)
    expect(DEMO_FOOD_PRODUCTS.every(item => item.origin && item.reason)).toBe(true)
    expect(DEMO_FOOD_PRODUCTS.filter(item => item.promoted)).toHaveLength(1)
  })

  it('keeps fictional stories available without audio or network data', () => {
    expect(WINE_STORIES.length).toBeGreaterThanOrEqual(3)
    expect(WINE_STORIES.every(item => item.title && item.text.length > 100)).toBe(true)
    expect(nextStoryIndex(1, () => 0)).not.toBe(1)
  })

  it('uses source portal links and one current map item', () => {
    expect(ABRAU_LINE.every(item => item.url.startsWith('https://vino-svoe.ru/wines/'))).toBe(true)
    expect(ABRAU_LINE.filter(item => item.current)).toHaveLength(1)
    expect(new Set(ABRAU_LINE.map(item => item.tier))).toEqual(new Set(['Премиальная коллекция', 'Классическая коллекция', 'На каждый день']))
  })
})
