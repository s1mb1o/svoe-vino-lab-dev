export interface DemoFoodProduct {
  name: string
  kind: string
  origin: string
  reason: string
  promoted?: boolean
}

export interface WineStory {
  title: string
  text: string
}

export interface ProductLineWine {
  name: string
  tier: 'Премиальная коллекция' | 'Классическая коллекция' | 'На каждый день'
  x: number
  y: number
  url: string
  current?: boolean
}

export const DEMO_FOOD_PRODUCTS: DemoFoodProduct[] = [
  { name: 'Сыр «Северная долина»', kind: 'Полутвёрдый сыр', origin: 'Вологодская область', reason: 'Сливочная текстура смягчает кислотность вина, а выдержанный вкус поддерживает его аромат.', promoted: true },
  { name: 'Пастрами «Донская ферма»', kind: 'Мясная гастрономия', origin: 'Ростовская область', reason: 'Пряности поддерживают ягодные и перечные оттенки, не перекрывая вкус вина.' },
  { name: 'Конфитюр «Карельская ягода»', kind: 'Ягодный конфитюр', origin: 'Республика Карелия', reason: 'Небольшая сладость и лесные ягоды создают контраст к сухому вкусу и подходят к сырной тарелке.' },
]

export const WINE_STORIES: WineStory[] = [
  { title: 'Столик у окна', text: 'В маленьком ресторане у канала официант ставит бутылку на край стола и просит сначала послушать город. Велосипедный звонок, плеск воды, разговор за соседним столиком. Только после этого он разливает вино и говорит: «У каждого бокала должен быть собственный фон». Никто не знает, было ли это правилом ресторана или его личной традицией.' },
  { title: 'Записка виноделу', text: 'Путешественник однажды оставил на винодельне короткую записку: «Ваше вино напомнило мне дорогу после дождя». Ответ пришёл через год и состоял из одной строки: «Значит, мы правильно выбрали день для сбора». Они больше никогда не встречались, но каждый новый урожай начинался с чтения этой записки.' },
  { title: 'Три минуты тишины', text: 'Хозяин вымышленного погреба не разрешал обсуждать вино первые три минуты. Гости сначала смущались, потом замечали аромат хлеба из кухни, прохладу каменной стены и вечерний свет. После паузы каждый рассказывал о своём вкусе, и ни одно описание не совпадало с другим.' },
  { title: 'Бокал для опоздавшего', text: 'За большим семейным столом всегда оставляли один пустой бокал. Не для вина и не для гостя, а для истории, которая ещё не случилась. Когда кто-то приходил позже остальных, ему предлагали наполнить бокал и рассказать, что встретилось по дороге. Так обычный ужин каждый раз получал новую главу.' },
]

export const ABRAU_LINE: ProductLineWine[] = [
  { name: 'Удельное Ведомство Императорское, брют', tier: 'Премиальная коллекция', x: 30, y: 12, url: 'https://vino-svoe.ru/wines/abrau-dyurso-udelnoe-vedomstvo-imperatorskoe-beloe-bryut' },
  { name: 'Victor Dravigny, брют', tier: 'Премиальная коллекция', x: 68, y: 23, url: 'https://vino-svoe.ru/wines/abrau-dyurso-victor-dravigny-bryut', current: true },
  { name: 'Brut Rosé Reserve', tier: 'Классическая коллекция', x: 34, y: 49, url: 'https://vino-svoe.ru/wines/abrau-dyurso-abrau-durso-brut-rose-reserve-pino-nuar-beloe-bryut-12' },
  { name: 'Абрау-Дюрсо Пино Нуар', tier: 'Классическая коллекция', x: 72, y: 57, url: 'https://vino-svoe.ru/wines/abrau-dyurso-abrau-dyurso-pino-nuar-krasnoe-suhoe-13' },
  { name: 'Абрау-Дюрсо Физз, брют', tier: 'На каждый день', x: 31, y: 82, url: 'https://vino-svoe.ru/wines/abrau-dyurso-fizz-beloe-bryut' },
  { name: 'Абрау-Дюрсо Физз, полусладкое', tier: 'На каждый день', x: 69, y: 90, url: 'https://vino-svoe.ru/wines/abrau-dyurso-fizz-beloe-polusladkoe' },
]

export function nextStoryIndex(current: number, random = Math.random): number {
  if (WINE_STORIES.length < 2) return 0
  const candidate = Math.floor(random() * (WINE_STORIES.length - 1))
  return candidate >= current ? candidate + 1 : candidate
}
