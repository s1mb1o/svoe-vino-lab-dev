import type { Wine } from './catalog'
import { grapeReferences, labelSources, regionReferences, type LabelReference, type LabelSource } from './label-reference'

export interface LabelNote { value: string; text: string; sources: LabelSource[]; specific: boolean }
export interface LabelSection { id: 'grapes' | 'sweetness' | 'region' | 'alcohol'; label: string; value: string; title: string; intro?: string; notes: LabelNote[] }
export interface WineLabelExperience { sections: LabelSection[]; isBlend: boolean }

const normal = (text: string) => text.normalize('NFKC').toLocaleLowerCase('ru').replace(/ё/g, 'е').replace(/[‐‑–—-]/g, ' ').replace(/\s+/g, ' ').trim()
const present = (value: unknown): value is string => typeof value === 'string' && Boolean(value.trim()) && !/^(?:[-–—]|нет(?: данных)?|не указан[аоы]?|unknown|n\/a|null|undefined)$/iu.test(value.trim())
const source = (id: string): LabelSource[] => labelSources[id] ? [labelSources[id]!] : []
const grapeIndex = new Map(grapeReferences.flatMap(entry => entry.aliases.map(alias => [normal(alias), entry] as const)))
const grapeKey = (value: string) => normal(value.replace(/\d+(?:[.,]\d+)?\s*%/gu, '').replace(/,\s*(?=\))/gu, '').replace(/\(\s*\)/gu, '').replace(/\s+\d+(?:[.,]\d+)?\s*$/gu, ''))

function grapeParts(raw: string): string[] {
  const parts: string[] = []
  let depth = 0
  let start = 0
  for (let i = 0; i < raw.length; i++) {
    const char = raw[i]!
    if (char === '(') depth++
    if (char === ')') depth = Math.max(0, depth - 1)
    if (depth) continue
    // Parenthetical aliases and decimal commas belong to the supplied grape name.
    const comma = char === ',' && !(/\d/u.test(raw[i - 1] || '') && /\d/u.test(raw[i + 1] || ''))
    const conjunction = /^\s+и\s+(?!(?:белый|розовый|ч[её]рный|ж[её]лтый|янтарный)(?:\s|$))/iu.exec(raw.slice(i))
    if (comma || /[;\/\n+]/u.test(char) || conjunction) {
      parts.push(raw.slice(start, i))
      i += (conjunction?.[0].length || 1) - 1
      start = i + 1
    }
  }
  parts.push(raw.slice(start))
  return parts
}

function note(value: string, reference: LabelReference | undefined, fallback: string, fallbackSource: string): LabelNote {
  return { value, text: reference?.text || fallback, sources: source(reference?.source || fallbackSource), specific: Boolean(reference) }
}

// Only source category text determines sweetness. A name, slug or tasting note cannot supply it.
function sweetness(value: string): string | undefined {
  const remaining = normal(value).replace(/[^\p{L}\p{N}]+/gu, ' ').trim()
  // These English styles do not establish one unambiguous category here.
  if (/(?:^|\s)(?:off dry|medium dry|medium sweet)(?=\s|$)/u.test(remaining)) return undefined
  const patterns: Array<[string, RegExp]> = [
    ['brutNature', /(?:^|\s)(?:брют натюр|brut nature|zero dosage|нулевой дозаж)(?=\s|$)/u],
    ['extraBrut', /(?:^|\s)(?:экстра брют|extra brut)(?=\s|$)/u],
    ['extraDry', /(?:^|\s)(?:экстра ?сух(?:ое|ой|ая)?|extra dry)(?=\s|$)/u],
    ['semiDry', /(?:^|\s)(?:полусух(?:ое|ой|ая)?|semi dry)(?=\s|$)/u],
    ['semiSweet', /(?:^|\s)(?:полусладк(?:ое|ий|ая)?|semi sweet)(?=\s|$)/u],
    ['sweet', /(?:^|\s)(?:сладк(?:ое|ий|ая)?|sweet)(?=\s|$)/u],
    ['dry', /(?:^|\s)(?:сух(?:ое|ой|ая)?|dry)(?=\s|$)/u],
    ['brut', /(?:^|\s)(?:брют|brut)(?=\s|$)/u],
  ]
  let rest = remaining
  const matches: string[] = []
  for (const [id, pattern] of patterns) if (pattern.test(rest)) { matches.push(id); rest = rest.replace(pattern, ' ') }
  return matches.length === 1 ? matches[0] : undefined
}

const sweetnessText: Record<string, string> = {
  dry: 'Сухое — вино с небольшим содержанием остаточного сахара. Во вкусе на первый план обычно выходят свежесть, фруктовые оттенки и кислотность.',
  semiDry: 'Полусухое — вино с небольшим количеством сахара и обычно лёгкой сладостью. По содержанию сахара это промежуточная категория между сухим и полусладким. Кислотность уравновешивает сладость и помогает вину сохранять свежесть.',
  semiSweet: 'Полусладкое — вино с заметной сладостью. Сахар делает вкус мягче, а кислотность помогает сохранить баланс и свежесть.',
  sweet: 'Сладкое — вино, в котором сладость играет заметную роль во вкусе. Баланс сахара и кислотности помогает ему оставаться гармоничным.',
  brut: 'Брют — категория сладости игристого вина. Обычно такое вино ощущается сухим: пузырьки и кислотность подчёркивают свежесть.',
  extraBrut: 'Экстра брют — очень сухой стиль игристого вина с меньшим содержанием сахара, чем допускает категория брют. Во вкусе заметнее свежесть и кислотность.',
  brutNature: 'Брют натюр — самая сухая категория игристого вина. После вторичного брожения сахар не добавляют; стиль строится на свежести и вкусе самого вина.',
  extraDry: 'Экстра-сухое (Extra Dry) — категория сладости игристого вина. Во вкусе возможны сладковатые оттенки: такой стиль слаще брюта. Кислотность и пузырьки помогают сохранять свежесть.',
}

const sparklingSweetnessText: Record<string, string> = {
  dry: 'Сухое — категория сладости игристого вина. Вино этого стиля может ощущаться сладковатым: по шкале игристых вин оно слаще брюта. Кислотность и пузырьки помогают сохранять свежесть.',
  semiDry: 'Полусухое игристое — стиль со сладковатыми оттенками во вкусе. На шкале сладости игристых эта категория расположена между сухим и полусладким. Пузырьки и кислотность дополняют ощущение свежести.',
}

export function deriveWineLabelExperience(wine: Pick<Wine, 'grapes' | 'category' | 'region' | 'alcohol'>): WineLabelExperience {
  const sections: LabelSection[] = []
  const grapes: LabelNote[] = []
  const seen = new Set<string>()
  for (const raw of Array.isArray(wine.grapes) ? wine.grapes : []) {
    if (!present(raw)) continue
    for (const part of grapeParts(raw)) {
      if (!present(part)) continue
      const value = part.trim()
      const key = grapeKey(value)
      if (!/\p{L}/u.test(key)) continue
      const reference = grapeIndex.get(key)
      const identity = reference && !reference.group ? normal(reference.aliases[0]!) : key
      if (seen.has(identity)) continue
      seen.add(identity)
      grapes.push(note(value, reference, 'Сорт винограда влияет на состав ягод: их кислотность, ароматические вещества и танины. Винодел сочетает особенности сорта, места выращивания и способа производства, формируя стиль вина.', 'basics'))
    }
  }
  const namedGrapes = grapes.filter(item => !grapeIndex.get(grapeKey(item.value))?.group)
  const isBlend = namedGrapes.length > 1
  if (grapes.length) sections.push({
    id: 'grapes', label: grapes.length > 1 ? 'Сорта' : 'Сорт', value: grapes.map(item => item.value).join(' · '),
    title: isBlend ? 'Несколько сортов — один купаж' : 'О винограде этого вина',
    intro: isBlend ? 'Купаж — сочетание нескольких сортов винограда в одном вине. Винодел объединяет их особенности, чтобы создать задуманный стиль.' : undefined,
    notes: grapes,
  })
  if (present(wine.category)) {
    const category = wine.category.trim()
    const id = sweetness(category)
    if (id) {
      const sparkling = ['brut', 'extraBrut', 'brutNature', 'extraDry'].includes(id) || /(?:игрист|шампанск|sparkling)/iu.test(category)
      const text = (sparkling && sparklingSweetnessText[id]) || sweetnessText[id]!
      sections.push({ id: 'sweetness', label: 'Сладость', value: category, title: 'Что ожидать во вкусе', notes: [note(category, undefined, text, sparkling ? 'sparkling' : id === 'semiDry' ? 'semiDry' : 'sweetness')] })
    }
  }
  if (present(wine.region)) {
    const region = wine.region.trim()
    // A subregion retains its exact source name and receives its parent region's background.
    const normalized = normal(region)
    const reference = regionReferences.flatMap(entry => entry.aliases.map(alias => ({ entry, alias: normal(alias) })))
      .sort((a, b) => b.alias.length - a.alias.length)
      .find(({ alias }) => normalized === alias || (normalized.startsWith(alias) && /^[^\p{L}\p{N}]/u.test(normalized.slice(alias.length))))?.entry
    sections.push({ id: 'region', label: 'Регион', value: region, title: 'О виноделии региона', notes: [note(region, reference, 'Регион указывает место происхождения вина. Почвы, рельеф и климат влияют на созревание винограда и разнообразие местных винодельческих стилей.', 'basics')] })
  }
  if (present(wine.alcohol) && /^\d{1,2}(?:[.,]\d+)?(?:\s*[-–]\s*\d{1,2}(?:[.,]\d+)?)?\s*%(?:\s*об\.?)?$/u.test(wine.alcohol.trim())) {
    sections.push({ id: 'alcohol', label: 'Крепость', value: wine.alcohol.trim(), title: 'Что означает процент алкоголя', notes: [note(wine.alcohol.trim(), undefined, 'Это доля алкоголя в объёме вина. Алкоголь образуется при брожении, когда дрожжи перерабатывают сахар винограда. На этикетке крепость также обозначают как «% об.» или «алк.».', 'basics')] })
  }
  return { sections, isBlend }
}
