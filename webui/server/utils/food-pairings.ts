import type { Wine } from '#shared/catalog'

export interface FoodIdea { food: string; query: string; reason: string; accept: RegExp; reject?: RegExp }
const ideas = {
  poultry: { food: 'Индейка с травами', query: 'филе индейки', reason: 'Нежное запечённое филе подойдёт к вину, для которого рекомендуют блюда из птицы.', accept: /^филе.*индей|^индей.*филе/i, reject: /копч|вялен|сушен|сушён/i },
  softCheese: { food: 'Моцарелла с томатами', query: 'моцарелла', reason: 'Мягкий сыр с томатами — лёгкая закуска, которая не перекрывает вкус вина.', accept: /^(сыр|моцарелла).*моцарелл|^моцарелл/i },
  hummus: { food: 'Хумус с хрустящим хлебом', query: 'хумус', reason: 'Нежный хумус дополнит вино как лёгкая закуска. Подайте с хлебом или овощами.', accept: /^хумус/i },
  beef: { food: 'Стейк на гриле', query: 'стейк говяжий', reason: 'Обжаренная говядина подойдёт к красному вину и сочетаниям с мясом или барбекю.', accept: /стейк.*(говя|рибай|стриплойн)|говя.*стейк/i },
  hardCheese: { food: 'Тарелка выдержанного сыра', query: 'сыр пармезан', reason: 'Выдержанный сыр создаёт насыщенное сочетание с вином. Подайте небольшими ломтиками.', accept: /^сыр.*пармезан/i },
  vegetables: { food: 'Запечённые шампиньоны', query: 'шампиньоны свежие', reason: 'Запечённые грибы дадут мягкий, насыщенный вкус без острой заправки.', accept: /^шампиньон/i, reject: /маринов|консерв|соус|солен|солён/i },
  fish: { food: 'Лосось в духовке', query: 'филе лосося', reason: 'Запечённая рыба — нежное сочетание с вином. Подайте без острого соуса.', accept: /^филе.*(лосос|семг|сёмг)|^(лосос|семг|сёмг).*филе/i, reject: /сол[её]н|копч[её]н|вялен|консерв/i },
  seafood: { food: 'Креветки с лимоном', query: 'креветки очищенные', reason: 'Нежные креветки — простое дополнение к вину, которое сочетается с морепродуктами.', accept: /креветк/i },
  chocolate: { food: 'Тёмный шоколад', query: 'шоколад темный', reason: 'Тёмный шоколад выбран по рекомендации сочетания с шоколадом в карточке вина.', accept: /^шоколад.*(темн|тёмн|горьк)/i },
} satisfies Record<string, FoodIdea>

export function foodIdeas(wine: Wine): FoodIdea[] {
  const keys: (keyof typeof ideas)[] = []
  const pairing = wine.pairings.join(' ').toLocaleLowerCase('ru')
  if (/птиц/.test(pairing)) keys.push('poultry')
  if (/рыб/.test(pairing)) keys.push('fish')
  if (/морепродукт/.test(pairing)) keys.push('seafood')
  if (/мяс|bbq|барбекю/.test(pairing)) keys.push('beef')
  if (/сыры/.test(pairing)) keys.push(wine.color === 'Красное' ? 'hardCheese' : 'softCheese')
  if (/шоколад/.test(pairing)) keys.push('chocolate')
  if (/закуск|салат/.test(pairing)) keys.push('softCheese', 'hummus')
  if (/овощ/.test(pairing)) keys.push('vegetables')
  // These are editorial defaults by wine style, not inferred tasting notes.
  keys.push(...(wine.color === 'Красное' ? ['beef', 'hardCheese', 'vegetables', 'hummus'] as const : ['softCheese', 'hummus', 'fish', 'vegetables'] as const))
  return [...new Set(keys)].map(key => ideas[key]).slice(0, 6)
}

export function matchesFood(idea: FoodIdea, name: string): boolean {
  return idea.accept.test(name) && !idea.reject?.test(name) && !/корм|для собак|для кошек/i.test(name)
}
