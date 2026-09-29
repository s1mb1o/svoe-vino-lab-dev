import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import type { Wine } from '../shared/catalog'
import { ABRAU_DEMO_CURRENT_SLUG, ABRAU_LINE, findAbrauLineWine, isAbrauWine } from '../shared/experiences'
import { deriveWineTasteExperience } from '../shared/taste'
import wines from '../server/data/wines.json'

const baseWine: Wine = {
  slug: 'cantiani-cabernet-sauvignon',
  name: 'Cantiani Cabernet Sauvignon',
  producer: 'Шато АЛВИСА',
  region: 'Дагестан',
  grapes: ['Каберне Совиньон'],
  color: 'Красное',
  category: 'Сухое',
  rating: 0,
  image: '/wine.webp',
  alcohol: '13%',
  servingTemperature: '14-16°C',
  pairings: ['Мясо и стейки', 'Запеченные овощи'],
  description: 'Полный вкус с мелкозернистыми танинами. Аромат вишни, черники, ежевики, пряностей и черного перца.',
  source: 'https://vino-svoe.ru/wines/cantiani-cabernet-sauvignon',
}

describe('local result experiences', () => {
  it('derives six taste metrics and source aroma signals', () => {
    const result = deriveWineTasteExperience(baseWine)
    expect(result.metrics.map(item => item.key)).toEqual(['body', 'acidity', 'tannin', 'sweetness', 'fruit', 'oak'])
    expect(result.metrics.every(item => item.value >= 1 && item.value <= 5)).toBe(true)
    expect(result.aromas.some(item => item.label === 'Тёмные ягоды' && item.basis === 'source')).toBe(true)
  })

  it('selects three distinct regional cuisines and uses source pairing evidence', () => {
    const result = deriveWineTasteExperience(baseWine)
    expect(result.dishes).toHaveLength(3)
    expect(new Set(result.dishes.map(item => item.cuisine)).size).toBe(3)
    expect(result.dishes.some(item => item.basis === 'source' && item.basisLabel.includes('Мясо и стейки'))).toBe(true)
  })

  it('uses grape and method signals for international style analogues', () => {
    expect(deriveWineTasteExperience(baseWine).twin.name).toContain('Bordeaux')
    const sparkling = deriveWineTasteExperience({
      ...baseWine,
      slug: 'sparkling-muscat',
      name: 'Мускат игристый',
      grapes: ['Мускат Белый'],
      color: 'Белое',
      category: 'Брют',
      pairings: [],
      description: 'Аромат белых цветов и спелого винограда. Метод Шарма.',
    })
    expect(sparkling.twin.name).toBe('Asti Secco')
    expect(sparkling.dishes.every(item => item.name && item.reason)).toBe(true)
  })

  it('uses dataset aggregates only as a labeled fallback', () => {
    const result = deriveWineTasteExperience({ ...baseWine, description: null, pairings: [] })
    expect(result.datasetSource).toMatchObject({ license: 'CC BY-NC-SA 4.0' })
    expect(result.datasetPriors).toEqual([expect.objectContaining({ datasetVariety: 'Cabernet Sauvignon', sampleCount: 9472 })])
    expect(result.aromas.some(item => item.basis === 'dataset')).toBe(true)
  })

  it('keeps explicit source structure above dataset aggregates', () => {
    const result = deriveWineTasteExperience({
      ...baseWine,
      description: 'Вино со средним телом, умеренной кислотностью и средними танинами.',
    })
    expect(result.metrics.find(item => item.key === 'body')?.value).toBe(3)
    expect(result.metrics.find(item => item.key === 'acidity')?.value).toBe(3)
    expect(result.metrics.find(item => item.key === 'tannin')?.value).toBe(3)
  })

  it('does not treat color words as floral or full-body evidence', () => {
    const result = deriveWineTasteExperience({
      ...baseWine,
      grapes: ['Неизвестный сорт'],
      color: 'Белое',
      description: 'Вино насыщенного золотистого цвета. Аромат свежий. Розовый оттенок заметен по краю бокала.',
    })
    expect(result.aromas.some(item => item.label === 'Цветы' && item.basis === 'source')).toBe(false)
    expect(result.metrics.find(item => item.key === 'body')?.value).toBe(3)
  })

  it('keeps gentle astringency at the medium tannin level', () => {
    const result = deriveWineTasteExperience({ ...baseWine, grapes: [], description: 'Во вкусе лёгкая терпкость и красные ягоды.' })
    expect(result.metrics.find(item => item.key === 'tannin')?.value).toBe(3)
  })

  it('handles sweet wines before dry varietal analogues', () => {
    const sweetRed = deriveWineTasteExperience({ ...baseWine, category: 'Сладкое', pairings: ['Десерты'] })
    expect(sweetRed.twin.name).toBe('Recioto della Valpolicella')
    expect(sweetRed.dishes.every(item => ['Белёвская пастила', 'Чак-чак', 'Булмг с яблоком и грушей', 'Чурчхела'].includes(item.name))).toBe(true)
    expect(new Set(sweetRed.dishes.map(item => item.cuisine)).size).toBe(3)

    const sweetRosé = deriveWineTasteExperience({ ...baseWine, grapes: [], color: 'Розовое', category: 'Полусладкое' })
    expect(sweetRosé.twin.name).toBe('Rosé d’Anjou')
  })

  it('uses the wine name to detect a semisweet sparkling style', () => {
    const result = deriveWineTasteExperience({
      ...baseWine,
      name: 'Игристое розовое',
      grapes: [],
      color: 'Розовое',
      category: 'Полусладкое',
      description: null,
    })
    expect(result.twin.name).toBe('Champagne Demi-Sec')
  })

  it('does not use Kabinett as a sweetness category', () => {
    const result = deriveWineTasteExperience({ ...baseWine, grapes: ['Рислинг'], color: 'Белое', category: 'Полусухое' })
    expect(result.twin.name).toBe('German off-dry Riesling')
  })

  it('uses source portal links and a stable demonstration item', () => {
    expect(ABRAU_LINE.every(item => item.url.startsWith('https://vino-svoe.ru/wines/'))).toBe(true)
    expect(ABRAU_LINE.every(item => item.image.startsWith('/line-wines/') && item.image.endsWith('.webp'))).toBe(true)
    expect(ABRAU_LINE.filter(item => item.imageSource === 'patched').map(item => item.name)).toEqual(['Удельное Ведомство Императорское, брют'])
    expect(ABRAU_LINE.filter(item => item.imageSource === 'main')).toHaveLength(5)
    expect(ABRAU_LINE.some(item => item.slug === ABRAU_DEMO_CURRENT_SLUG)).toBe(true)
    expect(ABRAU_LINE.filter(item => item.current)).toHaveLength(0)
    expect(new Set(ABRAU_LINE.map(item => item.tier))).toEqual(new Set(['Премиальная коллекция', 'Классическая коллекция', 'На каждый день']))
  })

  it('connects an Abrau-Durso result to its exact map node', () => {
    const exact = { producer: 'Абрау—Дюрсо', slug: 'abrau-dyurso-fizz-beloe-bryut' }
    expect(isAbrauWine(exact)).toBe(true)
    expect(findAbrauLineWine(exact)?.slug).toBe(exact.slug)
    expect(isAbrauWine({ producer: '', slug: 'abrau-dyurso-risling-beloe-suhoe-12' })).toBe(true)
    expect(findAbrauLineWine({ producer: 'Абрау-Дюрсо', slug: 'abrau-dyurso-risling-beloe-suhoe-12' })).toBeUndefined()
    expect(isAbrauWine({ producer: 'Винодельня Марченко', slug: baseWine.slug })).toBe(false)
  })

  it('ships every product-line image as a WebP asset', () => {
    for (const item of ABRAU_LINE) {
      const image = readFileSync(new URL(`../public${item.image}`, import.meta.url))
      expect(image.subarray(0, 4).toString('ascii')).toBe('RIFF')
      expect(image.subarray(8, 12).toString('ascii')).toBe('WEBP')
    }
  })

  it('attaches the three pilot images to the mock recommendations', () => {
    const wine = wines.find(item => item.slug === 'priboj-marchenko-beloe-polusuhoe')
    expect(wine).toBeDefined()
    const result = deriveWineTasteExperience(wine as Wine)
    expect(result.datasetPriors).toEqual([])
    expect(result.datasetSource).toMatchObject({ license: 'CC BY-NC-SA 4.0' })
    expect(result.dishes.map(item => item.image)).toEqual([
      '/dishes/rasstegai-s-sudakom.webp',
      '/dishes/chudu-s-zelenyu-i-syrom.webp',
      '/dishes/khalyuzh-s-adygeiskim-syrom.webp',
    ])
    expect(result.dishes.every(item => Boolean(item.imageAlt))).toBe(true)
    expect(result.summary).toBe('Ожидаемый стиль: полусухое белое вино среднего тела, предположительно с высокой кислотностью.')
  })

  it('uses natural wording for a brut sparkling wine', () => {
    const result = deriveWineTasteExperience({
      ...baseWine,
      name: 'Игристое белое брют',
      grapes: [],
      color: 'Белое',
      category: 'Брют',
      description: null,
    })
    expect(result.summary).toBe('Ожидаемый стиль: белое игристое вино категории брют лёгкого тела, предположительно с очень высокой кислотностью.')
  })
})
