import { describe, expect, it } from 'vitest'
import { deriveWineLabelExperience } from '../shared/label'
import { grapeReferences, labelSources, regionReferences } from '../shared/label-reference'
import wines from '../server/data/wines.json'

const empty = { grapes: [], category: '', region: '', alcohol: null }

describe('wine label guide', () => {
  it('gives a separate sourced note for each grape of the rose example', () => {
    const wine = wines.find(item => item.slug === 'priboj-marchenko-rozovoe-polusuhoe')!
    const result = deriveWineLabelExperience(wine)
    const grapes = result.sections.find(section => section.id === 'grapes')!
    expect(result.isBlend).toBe(true)
    expect(grapes.notes.map(item => item.value)).toEqual(['Антей магарачский', 'Мерло'])
    expect(grapes.notes.every(item => item.specific && item.text.length > 60 && item.sources.length)).toBe(true)
    expect(grapes.notes[0]!.text).toContain('«Магарач»')
    expect(grapes.notes[1]!.text).toContain('Бордо')
    expect(JSON.stringify(grapes)).not.toMatch(/\d+%|отвечает за|доля сорта/u)
  })

  it('covers every grape in the current twelve preview wines with a reviewed reference', () => {
    for (const wine of wines) {
      const result = deriveWineLabelExperience(wine)
      const grapeSection = result.sections.find(section => section.id === 'grapes')!
      expect(grapeSection.notes.every(item => item.specific), wine.slug).toBe(true)
      expect(result.sections.some(section => section.id === 'region'), wine.slug).toBe(true)
      expect(result.sections.some(section => section.id === 'sweetness'), wine.slug).toBe(true)
    }
  })

  it('omits absent or placeholder values without missing-data copy', () => {
    expect(deriveWineLabelExperience(empty).sections).toEqual([])
    expect(deriveWineLabelExperience({ grapes: [' ', 'Не указан', '—'], category: 'Нет данных', region: ' N/A ', alcohol: '-' }).sections).toEqual([])
    const wine = { ...empty, region: 'Кубань' }
    expect(deriveWineLabelExperience(wine).sections.map(item => item.id)).toEqual(['region'])
    expect(JSON.stringify(deriveWineLabelExperience(wine))).not.toMatch(/не указан|нет данных|не приведен|не найден/iu)
  })

  it('deduplicates synonyms, preserves source spellings and explicit proportions', () => {
    const aliases = deriveWineLabelExperience({ ...empty, grapes: [' Сира (Шираз) ', 'Шираз'] })
    expect(aliases.isBlend).toBe(false)
    expect(aliases.sections[0]!.notes.map(item => item.value)).toEqual(['Сира (Шираз)'])
    const blend = deriveWineLabelExperience({ ...empty, grapes: ['Шардоне 70,5%; Мерло 29,5%'] })
    expect(blend.isBlend).toBe(true)
    expect(blend.sections[0]!.notes.map(item => item.value)).toEqual(['Шардоне 70,5%', 'Мерло 29,5%'])
    expect(blend.sections[0]!.notes.every(item => item.specific)).toBe(true)
  })

  it('keeps distinct muscat and local grape varieties separate', () => {
    const result = deriveWineLabelExperience({ ...empty, grapes: ['Мускат Белый', 'Мускат Блан', 'Мускат Розовый', 'Красностоп', 'Сибирьковый'] })
    expect(result.sections[0]!.notes.map(item => item.value)).toEqual(['Мускат Белый', 'Мускат Розовый', 'Красностоп', 'Сибирьковый'])
    expect(result.isBlend).toBe(true)
  })

  it('handles joined aliases and new grape names without inventing varietal facts', () => {
    const joined = deriveWineLabelExperience({ ...empty, grapes: ['Пино чёрный (Пино нуар) и Сира (Шираз)'] })
    expect(joined.sections[0]!.notes.every(item => item.specific)).toBe(true)
    const result = deriveWineLabelExperience({ ...empty, grapes: ['Совершенно новый сорт'] })
    expect(result.sections[0]!.notes[0]).toMatchObject({ value: 'Совершенно новый сорт', specific: false })
    expect(result.sections[0]!.notes[0]!.text).not.toMatch(/Сира|Вионье|француз|Бордо/u)
    expect(result.sections[0]!.notes[0]!.sources).toHaveLength(1)
  })

  it('separates slash, newline and numeric grape lists while retaining decimal percentages', () => {
    for (const value of ['Каберне Совиньон / Мерло', 'Каберне Совиньон\nМерло', 'Каберне Совиньон+Мерло', 'Каберне Совиньон 60, Мерло 40']) {
      const result = deriveWineLabelExperience({ ...empty, grapes: [value] })
      expect(result.isBlend, value).toBe(true)
      expect(result.sections[0]!.notes).toHaveLength(2)
      expect(result.sections[0]!.notes.every(item => item.specific)).toBe(true)
    }
    const shorthand = deriveWineLabelExperience({ ...empty, grapes: ['Мускат белый и розовый'] })
    expect(shorthand.sections[0]!.notes.map(item => item.value)).toEqual(['Мускат белый и розовый'])
    const parenthetical = deriveWineLabelExperience({ ...empty, grapes: ['Сира (Шираз, 60%), Мерло 40%'] })
    expect(parenthetical.sections[0]!.notes.map(item => item.value)).toEqual(['Сира (Шираз, 60%)', 'Мерло 40%'])
    expect(parenthetical.sections[0]!.notes.every(item => item.specific)).toBe(true)
    expect(deriveWineLabelExperience({ ...empty, grapes: ['60%)', '100%'] }).sections).toEqual([])
  })

  it('does not collapse generic Krasnostop or distinct regional names into a specific identity', () => {
    const grapes = deriveWineLabelExperience({ ...empty, grapes: ['Красностоп', 'Красностоп Золотовский', 'Красностоп Анапский'] })
    expect(grapes.sections[0]!.notes).toHaveLength(3)
    expect(grapes.sections[0]!.notes[0]!.text).not.toContain('Название связано с красным цветом')
    const terek = deriveWineLabelExperience({ ...empty, region: 'Долина Терека' })
    expect(terek.sections[0]!.notes[0]!.text).toContain('Кабардино-Балкарии')
    const ossetia = deriveWineLabelExperience({ ...empty, region: 'Северная Осетия' })
    expect(ossetia.sections[0]!.notes[0]!.text).toContain('Республике Северная Осетия')
  })

  it.each(['Сухое', 'Полусухое', 'Полусладкое', 'Сладкое', 'Брют', 'Экстра-брют', 'Брют натюр'])('explains the explicit sweetness category %s', category => {
    const result = deriveWineLabelExperience({ ...empty, category })
    expect(result.sections).toHaveLength(1)
    expect(result.sections[0]!.id).toBe('sweetness')
    expect(result.sections[0]!.value).toBe(category)
    expect(result.sections[0]!.notes[0]!.text.length).toBeGreaterThan(70)
  })

  it('does not confuse a dry substring with semi-dry, or infer sweetness from unrelated categories', () => {
    const result = deriveWineLabelExperience({ ...empty, category: 'Белое полусухое' })
    expect(result.sections[0]!.notes[0]!.text).toContain('лёгкой сладостью')
    for (const category of ['Белое', 'Тихое', 'Сухое полусладкое', 'Не указано', 'Off-dry', 'Medium dry', 'Medium sweet']) expect(deriveWineLabelExperience({ ...empty, category }).sections).toEqual([])
  })

  it('recognizes supplied sweetness next to punctuation and keeps source text verbatim', () => {
    for (const category of ['Сухое, белое', 'Красное сухое.', 'Брют/Розе', 'Полусухое (белое)']) {
      const result = deriveWineLabelExperience({ ...empty, category })
      expect(result.sections[0]?.id, category).toBe('sweetness')
      expect(result.sections[0]!.value).toBe(category)
    }
  })

  it('explains sparkling sweetness on its own scale, including extra dry spellings', () => {
    for (const category of ['Экстра-сухое', 'Экстрасухое', 'Extra dry', 'Сухое игристое']) {
      const section = deriveWineLabelExperience({ ...empty, category }).sections[0]!
      expect(section.notes[0]!.text, category).toContain('слаще брюта')
      expect(section.notes[0]!.sources[0]).toEqual(labelSources.sparkling)
    }
    const semiDry = deriveWineLabelExperience({ ...empty, category: 'Полусухое игристое' }).sections[0]!
    expect(semiDry.notes[0]!.text).toContain('сладковатыми оттенками')
    expect(semiDry.notes[0]!.text).not.toContain('небольшим количеством сахара')
    expect(semiDry.notes[0]!.sources[0]).toEqual(labelSources.sparkling)
  })

  it('retains exact subregion and grape names and does not substitute a similar variety', () => {
    const result = deriveWineLabelExperience({ ...empty, region: 'Кубань, Новороссийск', grapes: ['Каберне АЗОС'] })
    expect(result.sections[0]!.notes[0]!.text).toContain('анапской селекции')
    const region = result.sections.find(section => section.id === 'region')!
    expect(region.value).toBe('Кубань, Новороссийск')
    expect(region.notes[0]!.text).toContain('Чёрным и Азовским')
    for (const suffix of ['Кубань — Анапа', 'Кубань / Тамань', 'Кубань (Анапа)']) {
      expect(deriveWineLabelExperience({ ...empty, region: suffix }).sections[0]!.notes[0]!.specific).toBe(true)
    }
    expect(deriveWineLabelExperience({ ...empty, region: 'Кубаньский' }).sections[0]!.notes[0]!.specific).toBe(false)
  })

  it('accepts a supplied alcohol range but rejects non-numeric placeholder text', () => {
    expect(deriveWineLabelExperience({ ...empty, alcohol: '12-13.5%' }).sections[0]!.value).toBe('12-13.5%')
    expect(deriveWineLabelExperience({ ...empty, alcohol: 'скоро' }).sections).toEqual([])
  })

  it('uses only explicitly allowed Russian publishers, and every dictionary item has a source', () => {
    const publishers = new Set(['rskrf.ru', 'rvwa.ru', 'vino.ru', 'swn.ru', 'magarach-institut.ru', 'magarach-journal.ru', 'journalkubansad.ru'])
    for (const reference of Object.values(labelSources)) {
      const url = new URL(reference.url)
      expect(url.protocol).toBe('https:')
      expect(publishers.has(url.hostname.replace(/^www\./u, '')), reference.url).toBe(true)
    }
    for (const item of [...grapeReferences, ...regionReferences]) expect(labelSources[item.source], item.aliases[0]).toBeDefined()
  })
})
