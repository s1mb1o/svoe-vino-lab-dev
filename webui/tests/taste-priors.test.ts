import { describe, expect, it } from 'vitest'
import wineStylePriors from '../shared/data/wine-style-priors.json'

describe('wine style aggregate', () => {
  it('identifies the source and contains the expected aggregate scope', () => {
    const varieties = Object.values(wineStylePriors.varieties)
    expect(wineStylePriors.source).toMatchObject({
      license: 'CC BY-NC-SA 4.0',
      generatedOn: '2026-09-29',
    })
    expect(varieties).toHaveLength(18)
    expect(varieties.reduce((sum, item) => sum + item.sampleCount, 0)).toBe(66562)
    expect(wineStylePriors.varieties['Cabernet Sauvignon'].sampleCount).toBe(9472)
  })

  it('stores bounded aggregates without reviews or critic scores', () => {
    for (const prior of Object.values(wineStylePriors.varieties)) {
      expect(Object.keys(prior).sort()).toEqual(['aromas', 'sampleCount', 'structure'])
      expect(prior.sampleCount).toBeGreaterThanOrEqual(25)
      for (const frequency of Object.values(prior.aromas)) {
        expect(frequency).toBeGreaterThanOrEqual(0)
        expect(frequency).toBeLessThanOrEqual(1)
      }
      for (const metric of Object.values(prior.structure)) {
        expect(metric.level).toBeGreaterThanOrEqual(1)
        expect(metric.level).toBeLessThanOrEqual(5)
        expect(metric.observationCount).toBeGreaterThan(0)
        expect(metric.observationCount).toBeLessThanOrEqual(prior.sampleCount)
      }
    }
  })
})
