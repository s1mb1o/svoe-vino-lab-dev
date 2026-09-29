import type { Wine } from './catalog'
import wineStylePriors from './data/wine-style-priors.json'

export type TasteMetricKey = 'body' | 'acidity' | 'tannin' | 'sweetness' | 'fruit' | 'oak'
export type InferenceBasis = 'source' | 'dataset' | 'style'

export interface TasteMetric {
  key: TasteMetricKey
  label: string
  value: number
  level: string
  detail: string
}

export interface AromaFamily {
  label: string
  basis: InferenceBasis
}

export interface DishRecommendation {
  name: string
  cuisine: string
  reason: string
  basis: InferenceBasis
  basisLabel: string
  image?: string
  imageAlt?: string
}

export interface DatasetPriorEvidence {
  sourceVariety: string
  datasetVariety: string
  sampleCount: number
}

export interface InternationalTwin {
  name: string
  place: string
  shared: string
  difference: string
  basisLabel: string
}

export interface WineTasteExperience {
  summary: string
  metrics: TasteMetric[]
  aromas: AromaFamily[]
  dishes: DishRecommendation[]
  twin: InternationalTwin
  sourcePairings: string[]
  sourceDescriptionUsed: boolean
  datasetPriors: DatasetPriorEvidence[]
  datasetSource: { name: string; url: string; license: string } | null
}

interface AggregateMetric {
  level: number
  mean: number
  observationCount: number
}

interface AggregatePrior {
  sampleCount: number
  aromas: Record<string, number>
  structure: Partial<Record<Exclude<TasteMetricKey, 'sweetness'>, AggregateMetric>>
}

interface TasteContext {
  wine: Wine
  text: string
  description: string
  category: string
  color: string
  grapes: string
  sparkling: boolean
  priors: Array<{ sourceVariety: string; datasetVariety: string; prior: AggregatePrior }>
  metrics: Record<TasteMetricKey, number>
}

type DishTrait = 'dessert' | 'fatty' | 'fish' | 'meat' | 'pastry' | 'poultry' | 'spiced' | 'vegetable'

interface DishRule {
  name: string
  cuisine: string
  richness: number
  traits: DishTrait[]
  sourceHints: string[]
  colors?: string[]
  image?: string
  imageAlt?: string
}

const AGGREGATE_PRIORS = wineStylePriors.varieties as Record<string, AggregatePrior>

const DATASET_GRAPE_RULES: Array<{ datasetVariety: string; pattern: RegExp }> = [
  { datasetVariety: 'Cabernet Sauvignon', pattern: /каберне\s*совиньон/ },
  { datasetVariety: 'Cabernet Franc', pattern: /каберне\s*фран/ },
  { datasetVariety: 'Sauvignon Blanc', pattern: /совиньон\s*блан/ },
  { datasetVariety: 'Pinot Noir', pattern: /пино\s*нуар/ },
  { datasetVariety: 'Pinot Gris', pattern: /пино\s*(?:гри|гриджио)/ },
  { datasetVariety: 'Gewurztraminer', pattern: /гевюрцтраминер/ },
  { datasetVariety: 'Chardonnay', pattern: /шардоне/ },
  { datasetVariety: 'Riesling', pattern: /рислинг/ },
  { datasetVariety: 'Rkatsiteli', pattern: /ркацители/ },
  { datasetVariety: 'Aligote', pattern: /алиготе/ },
  { datasetVariety: 'Viognier', pattern: /вионье/ },
  { datasetVariety: 'Syrah', pattern: /(?:сира|шираз)/ },
  { datasetVariety: 'Muscat', pattern: /мускат/ },
  { datasetVariety: 'Malbec', pattern: /мальбек/ },
  { datasetVariety: 'Sangiovese', pattern: /санджовезе/ },
  { datasetVariety: 'Tempranillo', pattern: /темпранильо/ },
  { datasetVariety: 'Saperavi', pattern: /саперави/ },
  { datasetVariety: 'Merlot', pattern: /мерло/ },
]

const DATASET_AROMA_LABELS: Record<string, string> = {
  apple_pear: 'Яблоко и груша',
  citrus: 'Цитрусы',
  cocoa_coffee: 'Какао и кофе',
  dark_berries: 'Тёмные ягоды',
  floral: 'Цветы',
  herbs_greens: 'Травы и зелень',
  honey_dried_fruit: 'Мёд и сухофрукты',
  mineral: 'Минеральные тона',
  oak_vanilla: 'Дуб и ваниль',
  red_berries: 'Красные ягоды',
  spices: 'Пряности',
  stone_fruit: 'Косточковые фрукты',
  tropical: 'Тропические фрукты',
}

const LEVELS: Record<TasteMetricKey, string[]> = {
  body: ['очень лёгкое', 'лёгкое', 'среднее', 'полное', 'очень полное'],
  acidity: ['очень мягкая', 'мягкая', 'заметная', 'высокая', 'очень высокая'],
  tannin: ['почти нет', 'мягкие', 'средние', 'выраженные', 'мощные'],
  sweetness: ['очень сухое', 'сухое', 'полусухое', 'полусладкое', 'сладкое'],
  fruit: ['сдержанная', 'деликатная', 'заметная', 'яркая', 'очень яркая'],
  oak: ['не заявлен', 'едва заметный', 'умеренный', 'выраженный', 'доминирующий'],
}

const METRIC_LABELS: Record<TasteMetricKey, string> = {
  body: 'Тело',
  acidity: 'Кислотность',
  tannin: 'Танины',
  sweetness: 'Сладость',
  fruit: 'Фруктовость',
  oak: 'Дуб',
}

const METRIC_DETAILS: Record<TasteMetricKey, string> = {
  body: 'Насыщенность и вес вкуса',
  acidity: 'Ощущение свежести',
  tannin: 'Терпкость и структура',
  sweetness: 'Ожидаемый уровень сахара',
  fruit: 'Интенсивность фруктовых тонов',
  oak: 'Признаки выдержки в дубе',
}

const AROMA_RULES: Array<{ label: string; pattern: RegExp }> = [
  { label: 'Цитрусы', pattern: /цитрус|лимон|лайм|грейпфрут|помело|цедр/ },
  { label: 'Яблоко и груша', pattern: /яблок|груш|айв/ },
  { label: 'Косточковые фрукты', pattern: /персик|абрикос|кураг|нектарин|желт[а-я]*\s+слив/ },
  { label: 'Тропические фрукты', pattern: /ананас|манго|маракуй|личи|тропич/ },
  { label: 'Красные ягоды', pattern: /малин|клубник|земляник|красн[а-я]*\s+смород|клюкв|брусник/ },
  { label: 'Тёмные ягоды', pattern: /черн[а-я]*\s+смород|ежевик|черник|вишн|черешн/ },
  { label: 'Цветы', pattern: /цветоч|цветы|цветов|цветами|цветущ|первоцвет|акаци|фиалк|пион|лепест|лаванд|жимолост|липов[а-я]*\s+цвет|(?:^|[^а-я])роз(?:а|ы|ой|у|е)(?:$|[^а-я])/ },
  { label: 'Травы и зелень', pattern: /трав|шалфе|мят|эвкалипт|лист|зел[её]н/ },
  { label: 'Пряности', pattern: /прян|перец|кориц|гвоздик|анис|кардамон/ },
  { label: 'Минеральные тона', pattern: /минерал|мелов|кремн|солоноват|камен|камн|слан/ },
  { label: 'Мёд и сухофрукты', pattern: /м[её]д|изюм|инжир|финик|сухофрукт/ },
  { label: 'Дуб и ваниль', pattern: /дуб|боч|баррик|ванил|тост/ },
  { label: 'Какао и кофе', pattern: /кофе|какао|шоколад/ },
]

const DISH_RULES: DishRule[] = [
  { name: 'Расстегай с судаком', cuisine: 'Русская кухня', richness: 2, traits: ['fish', 'pastry', 'fatty'], sourceHints: ['рыб', 'морепродукт', 'закуск'], colors: ['бел', 'роз'], image: '/dishes/rasstegai-s-sudakom.webp', imageAlt: 'Открытый расстегай с кусочками судака, луком и укропом' },
  { name: 'Пожарская котлета', cuisine: 'Русская кухня', richness: 3, traits: ['poultry', 'fatty'], sourceHints: ['птиц', 'мяс'], colors: ['бел', 'роз', 'красн'] },
  { name: 'Бефстроганов', cuisine: 'Русская кухня', richness: 4, traits: ['meat', 'fatty'], sourceHints: ['мяс', 'стейк', 'bbq'], colors: ['красн'] },
  { name: 'Винегрет с печёной свёклой', cuisine: 'Русская кухня', richness: 2, traits: ['vegetable'], sourceHints: ['салат', 'овощ', 'закуск'], colors: ['бел', 'роз', 'оранж'] },
  { name: 'Белёвская пастила', cuisine: 'Русская кухня', richness: 2, traits: ['dessert'], sourceHints: ['десерт', 'шоколад', 'выпеч'], colors: ['бел', 'роз'] },
  { name: 'Эчпочмак', cuisine: 'Татарская кухня', richness: 4, traits: ['meat', 'pastry', 'fatty'], sourceHints: ['мяс', 'птиц', 'закуск'], colors: ['красн', 'роз'] },
  { name: 'Кыстыбый с картофелем', cuisine: 'Татарская кухня', richness: 3, traits: ['pastry', 'vegetable', 'fatty'], sourceHints: ['овощ', 'закуск', 'сыр'], colors: ['бел', 'роз', 'оранж'] },
  { name: 'Чак-чак', cuisine: 'Татарская кухня', richness: 3, traits: ['dessert'], sourceHints: ['десерт', 'шоколад', 'выпеч'], colors: ['бел', 'роз'] },
  { name: 'Бёрики', cuisine: 'Калмыцкая кухня', richness: 4, traits: ['meat'], sourceHints: ['мяс', 'стейк', 'bbq', 'азиат'], colors: ['красн', 'роз', 'оранж'] },
  { name: 'Булмг с яблоком и грушей', cuisine: 'Калмыцкая кухня', richness: 3, traits: ['dessert'], sourceHints: ['десерт', 'выпеч'], colors: ['бел', 'роз'] },
  { name: 'Хуужуур', cuisine: 'Тувинская кухня', richness: 4, traits: ['meat', 'pastry', 'fatty'], sourceHints: ['мяс', 'стейк', 'bbq', 'закуск', 'азиат'], colors: ['красн', 'роз'] },
  { name: 'Чуду с зеленью и сыром', cuisine: 'Дагестанская кухня', richness: 3, traits: ['pastry', 'vegetable', 'fatty'], sourceHints: ['овощ', 'сыр', 'закуск'], colors: ['бел', 'роз', 'оранж'], image: '/dishes/chudu-s-zelenyu-i-syrom.webp', imageAlt: 'Тонкое чуду с начинкой из свежей зелени и белого сыра' },
  { name: 'Курзе с мясом', cuisine: 'Дагестанская кухня', richness: 4, traits: ['meat', 'spiced'], sourceHints: ['мяс', 'стейк', 'bbq'], colors: ['красн', 'роз', 'оранж'] },
  { name: 'Осетинский пирог с сыром', cuisine: 'Осетинская кухня', richness: 4, traits: ['pastry', 'fatty'], sourceHints: ['сыр', 'закуск'], colors: ['бел', 'роз', 'оранж'] },
  { name: 'Жижиг-галнаш', cuisine: 'Чеченская кухня', richness: 5, traits: ['meat'], sourceHints: ['мяс', 'стейк', 'bbq'], colors: ['красн'] },
  { name: 'Щипс с пастэ', cuisine: 'Адыгская кухня', richness: 4, traits: ['poultry', 'spiced', 'fatty'], sourceHints: ['птиц', 'мяс'], colors: ['красн', 'роз', 'оранж'] },
  { name: 'Халюж с адыгейским сыром', cuisine: 'Адыгская кухня', richness: 3, traits: ['pastry', 'fatty'], sourceHints: ['сыр', 'закуск'], colors: ['бел', 'роз', 'оранж'], image: '/dishes/khalyuzh-s-adygeiskim-syrom.webp', imageAlt: 'Жареные халюжи в форме полумесяца с адыгейским сыром' },
  { name: 'Хычины с сыром и картофелем', cuisine: 'Балкарская кухня', richness: 4, traits: ['pastry', 'vegetable', 'fatty'], sourceHints: ['сыр', 'овощ', 'закуск'], colors: ['бел', 'роз', 'оранж'] },
  { name: 'Хинкали', cuisine: 'Грузинская кухня', richness: 4, traits: ['meat', 'spiced'], sourceHints: ['мяс', 'стейк', 'bbq'], colors: ['красн', 'роз', 'оранж'] },
  { name: 'Лобио', cuisine: 'Грузинская кухня', richness: 3, traits: ['vegetable', 'spiced'], sourceHints: ['овощ', 'закуск'], colors: ['красн', 'оранж'] },
  { name: 'Пхали из свёклы', cuisine: 'Грузинская кухня', richness: 2, traits: ['vegetable', 'spiced'], sourceHints: ['салат', 'овощ', 'закуск'], colors: ['бел', 'роз', 'оранж'] },
  { name: 'Хачапури по-аджарски', cuisine: 'Грузинская кухня', richness: 5, traits: ['pastry', 'fatty'], sourceHints: ['сыр', 'закуск'], colors: ['бел', 'роз', 'оранж'] },
  { name: 'Чурчхела', cuisine: 'Грузинская кухня', richness: 3, traits: ['dessert'], sourceHints: ['десерт', 'шоколад', 'выпеч'], colors: ['красн', 'бел'] },
]

function normal(value: string | null | undefined): string {
  return (value || '').toLocaleLowerCase('ru').replace(/ё/g, 'е').replace(/\s+/g, ' ').trim()
}

function clamp(value: number): number {
  return Math.max(1, Math.min(5, Math.round(value)))
}

function has(text: string, pattern: RegExp): boolean {
  return pattern.test(text)
}

function stableFraction(value: string): number {
  let hash = 0
  for (const character of value) hash = (hash * 31 + character.charCodeAt(0)) >>> 0
  return (hash % 1000) / 1000
}

function sweetness(category: string): number {
  if (/сладк/.test(category) && !/полусладк/.test(category)) return 5
  if (/полусладк/.test(category)) return 4
  if (/полусух/.test(category)) return 3
  if (/сух/.test(category)) return 2
  if (/экстра\s*брют|брют/.test(category)) return 1
  return 2
}

function datasetPriors(wine: Wine): TasteContext['priors'] {
  const result: TasteContext['priors'] = []
  for (const sourceVariety of wine.grapes) {
    const normalized = normal(sourceVariety)
    const match = DATASET_GRAPE_RULES.find(rule => rule.pattern.test(normalized))
    const prior = match ? AGGREGATE_PRIORS[match.datasetVariety] : undefined
    if (!match || !prior || prior.sampleCount < 25 || result.some(item => item.datasetVariety === match.datasetVariety)) continue
    result.push({ sourceVariety, datasetVariety: match.datasetVariety, prior })
  }
  return result
}

function priorLevel(priors: TasteContext['priors'], key: Exclude<TasteMetricKey, 'sweetness'>): number | undefined {
  const usable = priors
    .map(item => item.prior.structure[key])
    .filter((item): item is AggregateMetric => Boolean(item && item.observationCount >= 20))
  if (!usable.length) return undefined
  return clamp(usable.reduce((sum, item) => sum + item.level, 0) / usable.length)
}

function buildContext(wine: Wine): TasteContext {
  const description = normal(wine.description)
  const category = normal(wine.category)
  const color = normal(wine.color)
  const grapes = normal(wine.grapes.join(' '))
  const priors = datasetPriors(wine)
  const text = normal([wine.name, wine.description, wine.category, wine.color, ...wine.grapes].filter(Boolean).join(' '))
  const sparkling = /брют|игрист|петнат|перляж|физз|метод\s+шарма|классическ[а-я]*\s+метод/.test(text)

  let acidity = priorLevel(priors, 'acidity') ?? (color.includes('бел') || color.includes('роз') ? 4 : 3)
  if (sparkling) acidity += 1
  if (has(description, /высок[а-я]*\s+кислот|ярк[а-я]*\s+кислот|звонк[а-я]*\s+кислот|хрустящ|освежающ|свеж[а-я]*\s+кислот/)) acidity = 5
  else if (has(description, /умеренн[а-я]*\s+кислот/)) acidity = 3
  else if (has(description, /мягк[а-я]*\s+кислот/)) acidity = 2
  else if (has(description, /деликатн[а-я]*\s+кислот/)) acidity = 3

  let body = priorLevel(priors, 'body') ?? (color.includes('красн') ? 4 : color.includes('оранж') ? 4 : 3)
  if (sparkling) body = 2
  if (has(description, /мощн[а-я]*\s+(?:тел|вкус|структур)|(?:тел|вкус|структур)[а-я]*\s+мощн[а-я]*/)) body = 5
  else if (has(description, /полнотел|(?:плотн|насыщ|объемн|обьемн)[а-я]*\s+(?:тел|вин|вкус|структур)|(?:тел|вин|вкус|структур)[а-я]*\s+(?:плотн[а-я]*|насыщ[а-я]*|объемн[а-я]*|обьемн[а-я]*)(?![а-я])(?!\s+(?:[а-я]+\s+)?(?:цвет|оттен))/)) body = 4
  else if (has(description, /средн[а-я]*\s+(?:тел|вкус|структур)|(?:тел|вкус|структур)[а-я]*\s+средн[а-я]*/)) body = 3
  else if (has(description, /легк[а-я]*\s+(?:тел|вин|вкус|стил|структур)|(?:тел|вин|вкус|стил|структур)[а-я]*\s+легк[а-я]*|воздушн|невесом/)) body = 2

  let tannin = priorLevel(priors, 'tannin') ?? (color.includes('красн') ? 3 : color.includes('оранж') ? 2 : 1)
  if (has(description, /мощн[а-я]*\s+танин/)) tannin = 5
  else if (has(description, /выраженн[а-я]*\s+танин|плотн[а-я]*\s+танин|(?:сильн|заметн)[а-я]*\s+терпк/)) tannin = 4
  else if (has(description, /(?:средн|умеренн)[а-я]*\s+танин|мелкозернист/)) tannin = 3
  else if (has(description, /мягк[а-я]*\s+танин|шелковист|бархатист/)) tannin = 2
  else if (has(description, /терпк/)) tannin += 1
  if (has(description, /(?:легк|деликатн|мягк)[а-я]*\s+терпк/)) tannin = Math.min(tannin, 3)

  let fruit = priorLevel(priors, 'fruit') ?? 2
  const fruitMatches = AROMA_RULES.slice(0, 6).filter(rule => rule.pattern.test(description)).length
  if (fruitMatches > 0) fruit = 3
  if (fruitMatches > 1 || has(description, /фруктов[а-я]*\s+(?:ярк|насыщ)|ягодн[а-я]*\s+(?:ярк|насыщ)/)) fruit = 4
  if (fruitMatches > 3) fruit = 5

  let oak = priorLevel(priors, 'oak') ?? 1
  if (has(description, /дуб|боч|баррик|ванил|тост/)) oak = 3
  if (has(description, /нов[а-я]*\s+(?:французск[а-я]*\s+)?дуб|длительн[а-я]*\s+выдержк[а-я]*\s+в\s+боч|выраженн[а-я]*\s+(?:дуб|древес|ванил)/)) oak = 4

  return {
    wine,
    text,
    description,
    category,
    color,
    grapes,
    sparkling,
    priors,
    metrics: {
      body: clamp(body),
      acidity: clamp(acidity),
      tannin: clamp(tannin),
      sweetness: sweetness(category),
      fruit: clamp(fruit),
      oak: clamp(oak),
    },
  }
}

function metric(key: TasteMetricKey, value: number): TasteMetric {
  return {
    key,
    label: METRIC_LABELS[key],
    value,
    level: LEVELS[key][value - 1]!,
    detail: METRIC_DETAILS[key],
  }
}

function aromaFamilies(context: TasteContext): AromaFamily[] {
  const explicit = AROMA_RULES
    .filter(rule => rule.pattern.test(context.description))
    .map(rule => ({ label: rule.label, basis: 'source' as const }))
  if (explicit.length >= 3) return explicit.slice(0, 6)

  const dataset = context.priors
    .flatMap(item => Object.entries(item.prior.aromas))
    .filter((entry): entry is [string, number] => entry[1] >= 0.18 && Boolean(DATASET_AROMA_LABELS[entry[0]]))
    .sort((left, right) => right[1] - left[1])

  const fallback: string[] = context.color.includes('красн')
    ? ['Тёмные ягоды', 'Пряности']
    : context.color.includes('роз')
      ? ['Красные ягоды', 'Цитрусы']
      : context.color.includes('оранж')
        ? ['Косточковые фрукты', 'Пряности']
        : ['Цитрусы', 'Яблоко и груша']
  if (context.sparkling) fallback.unshift('Цитрусы')

  const result: AromaFamily[] = [...explicit]
  for (const [key] of dataset) {
    const label = DATASET_AROMA_LABELS[key]!
    if (!result.some(item => item.label === label)) result.push({ label, basis: 'dataset' })
    if (result.length >= 6) return result
  }
  for (const label of fallback) {
    if (!result.some(item => item.label === label)) result.push({ label, basis: 'style' })
  }
  return result.slice(0, 6)
}

function sourcePairingFor(rule: DishRule, pairings: string[]): string | undefined {
  return pairings.find(pairing => rule.sourceHints.some(hint => normal(pairing).includes(hint)))
}

function dishScore(rule: DishRule, context: TasteContext, pairings: string[]): number {
  const { body, acidity, tannin, sweetness: sugar } = context.metrics
  const sourcePairing = sourcePairingFor(rule, pairings)
  let score = 10 - Math.abs(body - rule.richness) * 2
  if (sourcePairing) score += 12
  if (rule.colors?.some(color => context.color.includes(color))) score += 4
  else score -= 3
  if (rule.traits.includes('dessert')) score += sugar >= 4 ? 18 : -22
  else if (sugar >= 5) score -= 8
  if (rule.traits.includes('fatty') && acidity >= 4) score += 5
  if (rule.traits.includes('meat') && (tannin >= 3 || body >= 4)) score += 5
  if (rule.traits.includes('fish') && acidity >= 4 && tannin <= 2) score += 6
  if (rule.traits.includes('spiced') && context.metrics.fruit >= 3) score += 3
  if (rule.traits.includes('pastry') && context.sparkling) score += 5
  return score + stableFraction(`${context.wine.slug}:${rule.name}`)
}

function dishReason(rule: DishRule, context: TasteContext, sourcePairing?: string): string {
  const reasons: string[] = []
  if (sourcePairing) reasons.push(`Блюдо относится к близкой категории «${sourcePairing}» из карточки «Своё Вино».`)
  if (rule.traits.includes('dessert')) {
    reasons.push('Сладость вина не должна потеряться на фоне десерта, а фруктовые тона поддерживают яблоко, мёд, орехи или виноград.')
  } else if (rule.traits.includes('fish')) {
    reasons.push('Свежая кислотность поддерживает рыбу и тесто, а низкая танинность не создаёт металлического оттенка.')
  } else if (rule.traits.includes('meat') && context.metrics.tannin >= 3) {
    reasons.push('Танины и полнота вкуса соответствуют насыщенности мясной начинки или бульона.')
  } else if (rule.traits.includes('fatty') && context.metrics.acidity >= 4) {
    reasons.push('Кислотность освежает вкус после масла, сыра или сочной начинки.')
  } else if (rule.traits.includes('spiced')) {
    reasons.push('Фруктовый и пряный профиль поддерживает специи блюда без сравнения их остроты.')
  } else {
    reasons.push('Плотность блюда близка к ожидаемому телу вина, поэтому один вкус не должен перекрыть другой.')
  }
  return reasons.join(' ')
}

function dishRecommendations(context: TasteContext): DishRecommendation[] {
  const pairings = context.wine.pairings.filter(Boolean)
  const ranked = DISH_RULES
    .map(rule => ({ rule, score: dishScore(rule, context, pairings), sourcePairing: sourcePairingFor(rule, pairings) }))
    .sort((left, right) => right.score - left.score)
  const selected: typeof ranked = []
  for (const candidate of ranked) {
    if (selected.some(item => item.rule.cuisine === candidate.rule.cuisine)) continue
    selected.push(candidate)
    if (selected.length === 3) break
  }
  return selected.map(({ rule, sourcePairing }) => ({
    name: rule.name,
    cuisine: rule.cuisine,
    reason: dishReason(rule, context, sourcePairing),
    basis: sourcePairing ? 'source' : 'style',
    basisLabel: sourcePairing ? `Категория «${sourcePairing}»` : 'Вывод по профилю вкуса',
    image: rule.image,
    imageAlt: rule.imageAlt,
  }))
}

function twin(name: string, place: string, shared: string, difference: string, basisLabel: string): InternationalTwin {
  return { name, place, shared, difference, basisLabel }
}

function internationalTwin(context: TasteContext): InternationalTwin {
  const { grapes, text, category, color, sparkling, metrics } = context
  const grape = (pattern: RegExp) => pattern.test(grapes)
  const oak = metrics.oak >= 3
  const tropical = /ананас|манго|маракуй|тропич/.test(text)

  if (sparkling && grape(/мускат/) && metrics.sweetness >= 4) return twin('Moscato d’Asti', 'Пьемонт, Италия', 'Ароматный мускатный профиль, мягкие пузырьки и заметная фруктовость.', 'Давление и технология конкретного российского вина могут отличаться.', 'Игристый стиль, сладость и сорт Мускат')
  if (sparkling && metrics.sweetness >= 4) return twin('Champagne Demi-Sec', 'Шампань, Франция', 'Сладкий игристый стиль сочетает пузырьки, фруктовость и заметный остаточный сахар.', 'Сорта винограда, давление и метод производства российского вина могут отличаться.', 'Игристый стиль и сладкая категория')
  if (sparkling && metrics.sweetness === 3) return twin('Prosecco Extra Dry', 'Венето, Италия', 'Фруктовый игристый стиль с мягким ощущением остаточного сахара.', 'Название Extra Dry имеет отдельный диапазон сахара. Сорт и метод российского вина могут отличаться.', 'Игристый стиль и полусухая категория')
  if (sparkling && grape(/мускат/)) return twin('Asti Secco', 'Пьемонт, Италия', 'Сухой ароматный мускатный профиль, цветочные тона и свежая игристая структура.', 'Сортовой состав, давление и технология российского вина могут отличаться.', 'Сухой игристый стиль и сорт Мускат')
  if (sparkling && /шарма|резервуар/.test(text)) return twin('Prosecco Brut', 'Венето, Италия', 'Свежий фруктовый профиль и производство резервуарным методом.', 'Использованы другие сорта винограда, поэтому ароматический рисунок не будет одинаковым.', 'Метод Шарма из описания')
  if (sparkling && /классическ[а-я]*\s+метод|бутылочн|ремюаж|дегоржаж/.test(text)) return twin('Crémant de Bourgogne Brut', 'Бургундия, Франция', 'Сухой игристый стиль, высокая свежесть и выдержка на осадке.', 'Купаж, срок выдержки и климат российского региона создают собственный профиль.', 'Классический метод из описания')
  if (sparkling) return twin('Cava Brut', 'Каталония, Испания', 'Сухой освежающий игристый стиль с цитрусовым и яблочным направлением.', 'Это ориентир по структуре. Сорт и метод производства нужно проверять отдельно.', 'Категория игристого вина')
  if (metrics.sweetness >= 4 && grape(/мускат/)) return twin('Muscat de Beaumes-de-Venise', 'Южная Рона, Франция', 'Сладкий ароматный мускатный профиль с цветочными и фруктовыми тонами.', 'Французский ориентир обычно креплёный. Метод российского вина и уровень алкоголя могут отличаться.', 'Сладкая категория и сорт Мускат')
  if (metrics.sweetness >= 4 && color.includes('красн')) return twin('Recioto della Valpolicella', 'Венето, Италия', 'Сладкий красный стиль с тёмными ягодами, сухофруктами и полной структурой.', 'Итальянский стиль использует местные сорта и подвяливание винограда. Российская технология может быть другой.', 'Сладкая категория и красный цвет')
  if (metrics.sweetness >= 3 && color.includes('роз')) return twin('Rosé d’Anjou', 'Долина Луары, Франция', 'Мягкий розовый стиль с красными ягодами и заметным остаточным сахаром.', 'Сортовой состав, уровень сахара и насыщенность российского вина могут отличаться.', 'Розовый цвет и категория сахара')
  if (metrics.sweetness >= 4) return twin('Tokaji Late Harvest', 'Токай, Венгрия', 'Сладкий белый стиль с фруктами, мёдом и освежающей кислотностью.', 'Сортовой состав, цвет и метод производства российского вина могут быть другими.', 'Сладкая категория вина')
  if (color.includes('оранж')) return twin('Кахетинское янтарное вино', 'Кахетия, Грузия', 'Контакт с кожицей даёт белому винограду больше структуры, пряности и танинности.', 'Сравнение не означает выдержку в квеври. Технология российского вина может быть другой.', 'Оранжевый стиль')
  if (color.includes('роз')) return twin('Provence Rosé', 'Прованс, Франция', 'Свежий розовый стиль с красными ягодами и лёгким телом.', 'Цвет, сладость, сортовой состав и насыщенность российского вина могут отличаться.', 'Цвет и структура вина')
  if (grape(/рислинг/)) return twin(category.includes('полусух') ? 'German off-dry Riesling' : 'Rheingau Riesling trocken', 'Германия', 'Высокая кислотность, цитрусовые и цветочные тона, ясный сортовой профиль.', 'Климат и зрелость винограда меняют баланс кислотности и фруктовости.', 'Сорт Рислинг и категория сахара')
  if (grape(/шардоне/)) return oak
    ? twin('Côte de Beaune Chardonnay', 'Бургундия, Франция', 'Полное сухое белое вино с сочетанием фруктовости и дубовой выдержки.', 'Российское вино может иметь иной срок выдержки и более спелый фруктовый профиль.', 'Сорт Шардоне и признаки дуба')
    : twin('Chablis', 'Бургундия, Франция', 'Сухой стиль Шардоне с высокой свежестью, цитрусами и яблоком.', 'Минеральность и кислотность зависят от места и технологии. Это не сравнение терруаров.', 'Сорт Шардоне без явных признаков дуба')
  if (grape(/совиньон\s*блан/)) return tropical
    ? twin('Marlborough Sauvignon Blanc', 'Мальборо, Новая Зеландия', 'Яркая фруктовость, высокая свежесть и выразительный ароматический профиль.', 'Российское вино может быть менее тропическим и иметь другую зрелость винограда.', 'Сорт Совиньон Блан и тропические дескрипторы')
    : twin('Sancerre', 'Долина Луары, Франция', 'Сухой Совиньон Блан с высокой кислотностью, цитрусовым и травяным направлением.', 'Это ориентир по стилю, а не утверждение о минеральности или происхождении.', 'Сорт Совиньон Блан')
  if (grape(/каберне\s*совиньон/)) return twin('Левобережный Bordeaux', 'Бордо, Франция', 'Структурный сухой красный стиль, тёмные ягоды, пряности и заметные танины.', 'Российское вино может быть моносортовым, более спелым и выдержанным другим способом.', 'Сорт Каберне Совиньон')
  if (grape(/каберне\s*фран/)) return twin('Chinon Cabernet Franc', 'Долина Луары, Франция', 'Красные ягоды, травяные нюансы, свежесть и среднее тело.', 'Российский климат может дать более спелый фрукт и более полную структуру.', 'Сорт Каберне Фран')
  if (grape(/мерло/)) return twin('Правобережный Bordeaux', 'Бордо, Франция', 'Округлый красный стиль со сливой, ягодами и мягкими танинами.', 'Сравнение не означает бордоский купаж. Состав и выдержка могут отличаться.', 'Сорт Мерло')
  if (grape(/пино\s*нуар/)) return twin('Bourgogne Pinot Noir', 'Бургундия, Франция', 'Красные ягоды, умеренное тело и более мягкая танинная структура.', 'Климат российского региона может дать более спелый фрукт или иную кислотность.', 'Сорт Пино Нуар')
  if (grape(/саперави/)) return twin('Kakheti Saperavi', 'Кахетия, Грузия', 'Глубокий цвет, тёмные ягоды, пряность и выраженная структура.', 'Российское происхождение и технология дают самостоятельный стиль.', 'Сорт Саперави')
  if (grape(/ркацители/)) return twin('Kakheti Rkatsiteli', 'Кахетия, Грузия', 'Свежий белый профиль с яблоком, цитрусами и цветочными тонами.', 'Сравнение не предполагает квеври или длительный контакт с кожицей.', 'Сорт Ркацители')
  if (grape(/алиготе/)) return twin('Bourgogne Aligoté', 'Бургундия, Франция', 'Лёгкое сухое белое вино с высокой свежестью и цитрусово-яблочным профилем.', 'Зрелость фрукта и минеральные оттенки зависят от российского региона.', 'Сорт Алиготе')
  if (grape(/вионье/)) return twin('Condrieu', 'Северная Рона, Франция', 'Ароматный белый стиль с цветами и косточковыми фруктами.', 'Российское вино может быть легче, свежее и без дубовой выдержки.', 'Сорт Вионье')
  if (grape(/сира|шираз/)) return metrics.body >= 4
    ? twin('Barossa Shiraz', 'Южная Австралия', 'Полное тело, тёмные ягоды, перец и выраженная пряность.', 'Российское вино может иметь более высокую кислотность и сдержанную зрелость.', 'Сорт Сира и полное тело')
    : twin('Crozes-Hermitage Syrah', 'Северная Рона, Франция', 'Перечные и ягодные тона, свежесть и средняя структура.', 'Климат и выдержка российского вина могут изменить зрелость и танинность.', 'Сорт Сира')
  if (grape(/гевюрцтраминер/)) return twin('Alsace Gewurztraminer', 'Эльзас, Франция', 'Интенсивные цветочные, пряные и фруктовые ароматы.', 'Уровень сахара и полнота российского вина могут заметно отличаться.', 'Сорт Гевюрцтраминер')
  if (grape(/пино\s*(гри|гриджио)/)) return metrics.body >= 4 || metrics.sweetness >= 3
    ? twin('Alsace Pinot Gris', 'Эльзас, Франция', 'Полный ароматный белый стиль с грушей и косточковыми фруктами.', 'Российское вино может быть суше и легче.', 'Сорт Пино Гри и полный стиль')
    : twin('Pinot Grigio delle Venezie', 'Северо-Восточная Италия', 'Лёгкий сухой стиль, груша, цитрус и высокая свежесть.', 'Российский профиль может быть более ароматным и текстурным.', 'Сорт Пино Гри и лёгкий стиль')
  if (grape(/мускат/)) return twin('Alsace Muscat', 'Эльзас, Франция', 'Яркий виноградный, цветочный и фруктовый ароматический профиль.', 'Сладость и полнота зависят от категории российского вина.', 'Сорт Мускат')
  if (grape(/мальбек/)) return twin('Mendoza Malbec', 'Мендоса, Аргентина', 'Тёмные фрукты, пряность, полное тело и заметные танины.', 'Высота виноградника, климат и дубовая выдержка могут сильно изменить стиль.', 'Сорт Мальбек')
  if (grape(/санджовезе/)) return twin('Chianti Classico', 'Тоскана, Италия', 'Вишнёвый профиль, высокая свежесть и сухая танинная структура.', 'Сравнение не предполагает правила аппелласьона или одинаковую выдержку.', 'Сорт Санджовезе')
  if (grape(/темпранильо/)) return twin('Rioja Tempranillo', 'Риоха, Испания', 'Красные и тёмные ягоды, пряность и округлая структура.', 'Аппелласьон, срок выдержки и тип дуба российского вина могут отличаться.', 'Сорт Темпранильо')
  if (grape(/красностоп/)) return twin('Kakheti Saperavi', 'Кахетия, Грузия', 'Автохтонный структурный красный стиль с тёмными ягодами и пряностью.', 'Это сравнение характера, а не сортов: Красностоп остаётся самостоятельным российским сортом.', 'Российский сорт Красностоп и структура вина')
  if (grape(/кокур/)) return twin('Santorini Assyrtiko', 'Санторини, Греция', 'Сухой южный белый стиль с высокой свежестью и цитрусовым направлением.', 'Сорта, почвы и солоноватые оттенки не следует считать одинаковыми.', 'Сорт Кокур и сухой белый стиль')
  if (color.includes('красн')) return metrics.body >= 4
    ? twin('Côtes du Rhône Rouge', 'Долина Роны, Франция', 'Полный сухой красный стиль с ягодами и пряностями.', 'Это общий ориентир. Купаж, сорта и климат не совпадают.', 'Цвет, полнота и танинность')
    : twin('Cru Beaujolais', 'Божоле, Франция', 'Более лёгкий ягодный красный стиль с мягкими танинами.', 'Сорт винограда и ароматический профиль российского вина могут отличаться.', 'Цвет и лёгкая структура')
  return twin('Soave Classico', 'Венето, Италия', 'Сухой свежий белый стиль с цитрусовыми и яблочными тонами.', 'Это общий ориентир по структуре. Сорт и происхождение не совпадают.', 'Цвет, сухость и кислотность')
}

function profileSummary(context: TasteContext): string {
  const metrics = context.metrics
  const body = ['очень лёгкого тела', 'лёгкого тела', 'среднего тела', 'полного тела', 'очень полного тела'][metrics.body - 1]
  const acidity = ['очень мягкой', 'мягкой', 'заметной', 'высокой', 'очень высокой'][metrics.acidity - 1]
  const category = normal(context.wine.category) || LEVELS.sweetness[metrics.sweetness - 1]!
  const color = context.color.includes('красн')
    ? 'красное'
    : context.color.includes('роз')
      ? 'розовое'
      : context.color.includes('оранж')
        ? 'оранжевое'
        : context.color.includes('бел')
          ? 'белое'
          : ''
  const kind = context.sparkling ? [color, 'игристое вино'].filter(Boolean).join(' ') : [color, 'вино'].filter(Boolean).join(' ')
  const namedStyle = /брют/.test(category) ? `${kind} категории ${category}` : `${category} ${kind}`
  return `Ожидаемый стиль: ${namedStyle} ${body}, предположительно с ${acidity} кислотностью.`
}

export function deriveWineTasteExperience(wine: Wine): WineTasteExperience {
  const context = buildContext(wine)
  const order: TasteMetricKey[] = ['body', 'acidity', 'tannin', 'sweetness', 'fruit', 'oak']
  return {
    summary: profileSummary(context),
    metrics: order.map(key => metric(key, context.metrics[key])),
    aromas: aromaFamilies(context),
    dishes: dishRecommendations(context),
    twin: internationalTwin(context),
    sourcePairings: wine.pairings.filter(Boolean),
    sourceDescriptionUsed: context.description.length > 0,
    datasetPriors: context.priors.map(item => ({
      sourceVariety: item.sourceVariety,
      datasetVariety: item.datasetVariety,
      sampleCount: item.prior.sampleCount,
    })),
    datasetSource: {
      name: wineStylePriors.source.name,
      url: wineStylePriors.source.url,
      license: wineStylePriors.source.license,
    },
  }
}
