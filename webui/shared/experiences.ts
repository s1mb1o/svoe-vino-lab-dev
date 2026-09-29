import type { Wine } from './catalog'

export interface ProductLineWine {
  slug: string
  name: string
  tier: 'Премиальная коллекция' | 'Классическая коллекция' | 'На каждый день'
  x: number
  y: number
  url: string
  image: string
  imageSource: 'main' | 'patched'
  current?: boolean
}

export const ABRAU_DEMO_CURRENT_SLUG = 'abrau-dyurso-victor-dravigny-bryut'

export const ABRAU_LINE: ProductLineWine[] = [
  { slug: 'abrau-dyurso-udelnoe-vedomstvo-imperatorskoe-beloe-bryut', name: 'Удельное Ведомство Императорское, брют', tier: 'Премиальная коллекция', x: 30, y: 12, url: 'https://vino-svoe.ru/wines/abrau-dyurso-udelnoe-vedomstvo-imperatorskoe-beloe-bryut', image: '/line-wines/abrau-dyurso-udelnoe-vedomstvo-imperatorskoe-beloe-bryut.webp', imageSource: 'patched' },
  { slug: 'abrau-dyurso-victor-dravigny-bryut', name: 'Victor Dravigny, брют', tier: 'Премиальная коллекция', x: 68, y: 23, url: 'https://vino-svoe.ru/wines/abrau-dyurso-victor-dravigny-bryut', image: '/line-wines/abrau-dyurso-victor-dravigny-bryut.webp', imageSource: 'main' },
  { slug: 'abrau-dyurso-abrau-durso-brut-rose-reserve-pino-nuar-beloe-bryut-12', name: 'Brut Rosé Reserve', tier: 'Классическая коллекция', x: 34, y: 49, url: 'https://vino-svoe.ru/wines/abrau-dyurso-abrau-durso-brut-rose-reserve-pino-nuar-beloe-bryut-12', image: '/line-wines/abrau-dyurso-abrau-durso-brut-rose-reserve-pino-nuar-beloe-bryut-12.webp', imageSource: 'main' },
  { slug: 'abrau-dyurso-abrau-dyurso-pino-nuar-krasnoe-suhoe-13', name: 'Абрау-Дюрсо Пино Нуар', tier: 'Классическая коллекция', x: 72, y: 57, url: 'https://vino-svoe.ru/wines/abrau-dyurso-abrau-dyurso-pino-nuar-krasnoe-suhoe-13', image: '/line-wines/abrau-dyurso-abrau-dyurso-pino-nuar-krasnoe-suhoe-13.webp', imageSource: 'main' },
  { slug: 'abrau-dyurso-fizz-beloe-bryut', name: 'Абрау-Дюрсо Физз, брют', tier: 'На каждый день', x: 31, y: 82, url: 'https://vino-svoe.ru/wines/abrau-dyurso-fizz-beloe-bryut', image: '/line-wines/abrau-dyurso-fizz-beloe-bryut.webp', imageSource: 'main' },
  { slug: 'abrau-dyurso-fizz-beloe-polusladkoe', name: 'Абрау-Дюрсо Физз, полусладкое', tier: 'На каждый день', x: 69, y: 89, url: 'https://vino-svoe.ru/wines/abrau-dyurso-fizz-beloe-polusladkoe', image: '/line-wines/abrau-dyurso-fizz-beloe-polusladkoe.webp', imageSource: 'main' },
]

export function isAbrauWine(wine: Pick<Wine, 'producer' | 'slug'>): boolean {
  const producer = wine.producer.toLocaleLowerCase('ru').replace(/[^a-zа-яё0-9]/gi, '')
  return producer.includes('абраудюрсо') || wine.slug.startsWith('abrau-dyurso-')
}

export function findAbrauLineWine(wine: Pick<Wine, 'producer' | 'slug'>): ProductLineWine | undefined {
  if (!isAbrauWine(wine)) return undefined
  return ABRAU_LINE.find(item => item.slug === wine.slug)
}
