import { describe, expect, it } from 'vitest'
import { DINNER_NODES } from '../shared/dinner'
import { DINNER_PICKER_ENTRIES, dinnerPickerRows } from '../shared/dinner-picker'

describe('dish picker hierarchy', () => {
  it('keeps every source ID and label reachable in at most three visual levels', () => {
    const all = dinnerPickerRows(new Set(DINNER_NODES.map(node => node.id)))
    expect(all).toHaveLength(320)
    expect(new Set(all.map(node => node.id))).toEqual(new Set(DINNER_NODES.map(node => node.id)))
    for (const node of all) {
      expect(node.label).toBe(DINNER_NODES.find(source => source.id === node.id)?.label)
      expect(node.level).toBeLessThanOrEqual(3)
      if (node.parentId) expect(all.find(parent => parent.id === node.parentId)?.level).toBe(node.level - 1)
    }
  })
  it('starts with broad categories and opens meat, then steak, then individual dishes', () => {
    expect(dinnerPickerRows(new Set())).toHaveLength(16)
    const meat = dinnerPickerRows(new Set(['meat']))
    expect(meat.find(node => node.id === 'meat_steak')?.level).toBe(2)
    expect(meat.some(node => node.id === 'ribeye_grilled')).toBe(false)
    expect(dinnerPickerRows(new Set(['meat', 'meat_steak'])).find(node => node.id === 'ribeye_grilled')?.level).toBe(3)
  })
  it('retains the context of a folded intermediate class', () => {
    const fish = DINNER_PICKER_ENTRIES.find(node => node.label === 'Запечённая рыба')!
    expect(fish.displayLabel).toBe('Рыба › Запечённая рыба')
    expect(fish.level).toBe(2)
    expect(fish.context).toContain('Рыба и морепродукты')
  })
  it('searches across collapsed branches, category words and е/ё without inventing matches', () => {
    const result = dinnerPickerRows(new Set(), 'мясо РИБАЙ')
    expect(result.map(node => node.id)).toEqual(['ribeye_grilled'])
    expect(dinnerPickerRows(new Set(), 'запеченная рыба').some(node => node.label === 'Запечённая рыба')).toBe(true)
    expect(dinnerPickerRows(new Set(), 'unknown dish')).toEqual([])
  })
})
