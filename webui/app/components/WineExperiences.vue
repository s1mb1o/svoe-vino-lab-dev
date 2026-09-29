<script setup lang="ts">
import type { Wine } from '#shared/catalog'
import { ABRAU_DEMO_CURRENT_SLUG, ABRAU_LINE, findAbrauLineWine, isAbrauWine, type ProductLineWine } from '#shared/experiences'
import { deriveWineTasteExperience } from '#shared/taste'

type Experience = 'food' | 'label' | 'taste' | 'line'

const props = defineProps<{ wine: Wine }>()
const dialog = ref<HTMLDialogElement>()
const dialogHeading = ref<HTMLElement>()
const lineViewport = ref<HTMLElement>()
const active = ref<Experience | null>(null)
const mapZoom = ref(1)
const demoLineWine = ABRAU_LINE.find(item => item.slug === ABRAU_DEMO_CURRENT_SLUG) || ABRAU_LINE[0]!
const lineUsesMatchedProducer = computed(() => isAbrauWine(props.wine))
const matchedLineWine = computed(() => findAbrauLineWine(props.wine))
const currentLineWine = computed(() => matchedLineWine.value || (lineUsesMatchedProducer.value ? undefined : demoLineWine))
const lineItems = computed(() => ABRAU_LINE.map(item => ({ ...item, current: item.slug === currentLineWine.value?.slug })))
const selectedLineWine = shallowRef<ProductLineWine>(currentLineWine.value || ABRAU_LINE[0]!)
let opener: HTMLElement | null = null

const title = computed(() => ({
  food: 'Блюда к вашему вину',
  label: 'Что расскажет этикетка',
  taste: 'Паспорт вкуса',
  line: 'Карта линейки Абрау-Дюрсо',
}[active.value || 'food']))
const varieties = computed(() => props.wine.grapes.length ? props.wine.grapes.join(', ') : 'Сорт не указан в карточке')
const taste = computed(() => deriveWineTasteExperience(props.wine))
const dialogEyebrow = computed(() => active.value === 'line' && lineUsesMatchedProducer.value ? 'ЛИНЕЙКА ВАШЕГО ПРОИЗВОДИТЕЛЯ' : 'ДЕМОНСТРАЦИЯ ВОЗМОЖНОСТИ')
const lineActionSubtitle = computed(() => matchedLineWine.value ? 'Ваше вино отмечено на карте' : lineUsesMatchedProducer.value ? 'Линейка вашего производителя' : 'Карта вин одного производителя')
const mapCanvasStyle = computed(() => ({ transform: `scale(${mapZoom.value})`, transformOrigin: 'top center' }))
const mapSurfaceStyle = computed(() => ({ height: `${620 * mapZoom.value}px` }))

async function open(kind: Experience, event: MouseEvent) {
  opener = event.currentTarget as HTMLElement
  active.value = kind
  if (kind === 'line') { mapZoom.value = 1; selectedLineWine.value = currentLineWine.value || ABRAU_LINE[0]! }
  await nextTick()
  dialog.value?.showModal()
  dialogHeading.value?.focus({ preventScroll: true })
  if (kind === 'line') await locateCurrent()
}

function close() { dialog.value?.close() }
function closed() {
  active.value = null
  opener?.focus({ preventScroll: true })
}
function backdrop(event: MouseEvent) {
  if (event.target !== dialog.value) return
  const rect = dialog.value.getBoundingClientRect()
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close()
}
function changeZoom(change: number) { mapZoom.value = Math.min(1.3, Math.max(.75, Number((mapZoom.value + change).toFixed(2)))) }
async function locateCurrent() {
  const current = currentLineWine.value
  if (current) selectedLineWine.value = current
  await nextTick()
  lineViewport.value?.querySelector<HTMLElement>('[data-current="true"]')?.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' })
}
function selectLineWine(item: ProductLineWine) { selectedLineWine.value = item }
function openLineWine(item: ProductLineWine) { window.open(item.url, '_blank', 'noopener,noreferrer') }

onBeforeUnmount(() => dialog.value?.close())
</script>

<template>
  <section class="experience-panel" aria-labelledby="experience-heading">
    <div class="experience-heading">
      <div><p class="step-label">03 / ПРОДОЛЖИТЬ ЗНАКОМСТВО</p><h2 id="experience-heading">Что ещё узнать о вине?</h2></div>
      <span class="demo-badge">ДЕМО-ФУНКЦИИ</span>
    </div>
    <p class="experience-lead">Четыре идеи показывают, как портал может продолжить диалог после распознавания.</p>
    <div class="experience-grid">
      <button class="experience-action" @click="open('food', $event)"><span class="experience-icon"><AppIcon name="food" /></span><span><strong>Подобрать блюда</strong><small>Кухни России и соседних регионов</small></span><AppIcon name="arrow" /></button>
      <button class="experience-action" @click="open('label', $event)"><span class="experience-icon"><AppIcon name="book" /></span><span><strong>Рассказать об этикетке</strong><small>Сорта, термины и почему это важно</small></span><AppIcon name="arrow" /></button>
      <button class="experience-action" @click="open('taste', $event)"><span class="experience-icon"><AppIcon name="taste" /></span><span><strong>Паспорт вкуса</strong><small>Профиль и международный ориентир</small></span><AppIcon name="arrow" /></button>
      <button class="experience-action" @click="open('line', $event)"><span class="experience-icon"><AppIcon name="map" /></span><span><strong>Путеводитель по линейке</strong><small>{{ lineActionSubtitle }}</small></span><AppIcon name="arrow" /></button>
    </div>

    <dialog ref="dialog" class="experience-dialog" :aria-labelledby="active ? 'experience-dialog-heading' : undefined" @cancel.prevent="close" @click="backdrop" @close="closed">
      <header class="experience-dialog-header"><div><p class="step-label">{{ dialogEyebrow }}</p><h2 id="experience-dialog-heading" ref="dialogHeading" tabindex="-1">{{ title }}</h2></div><button class="icon-button" aria-label="Закрыть окно" @click="close"><AppIcon name="close" /></button></header>

      <template v-if="active === 'food'">
        <div class="dish-intro"><div><p class="step-label">ГАСТРОНОМИЧЕСКАЯ ГИПОТЕЗА</p><h3>Три блюда из региональных кухонь</h3><p>Подбор использует рекомендации «Своё Вино», описание вкуса, сорт и категорию вина.</p></div><div v-if="taste.sourcePairings.length" class="source-pairings"><span>ИЗ КАРТОЧКИ</span><p>{{ taste.sourcePairings.join(' · ') }}</p></div></div>
        <div class="dish-grid"><article v-for="(dish, index) in taste.dishes" :key="dish.name" class="dish-card"><div class="dish-card-top"><span class="dish-number">{{ String(index + 1).padStart(2, '0') }}</span><span class="inference-badge" :class="dish.basis">{{ dish.basis === 'source' ? 'КАТЕГОРИЯ ИЗ КАРТОЧКИ' : 'ВЫВОД ПО СТИЛЮ' }}</span></div><img v-if="dish.image" class="dish-image" :src="dish.image" :alt="dish.imageAlt || dish.name" width="640" height="400" loading="lazy" decoding="async"><p class="step-label">{{ dish.cuisine }}</p><h3>{{ dish.name }}</h3><p>{{ dish.reason }}</p><small>{{ dish.basisLabel }}</small></article></div>
        <div class="demo-callout"><AppIcon name="info" /><p><strong>Это не традиционное правило подачи.</strong> Сервис выводит сочетание из структуры вина и состава блюда. Конкретный рецепт, соус и острота могут изменить результат.</p></div>
      </template>

      <template v-else-if="active === 'label'">
        <div class="label-summary"><p class="step-label">НА ЭТИКЕТКЕ ВАШЕГО ВИНА</p><h3>{{ varieties }}</h3><p>Сервис может превратить короткую надпись на этикетке в понятное объяснение.</p></div>
        <div class="label-compare"><article><span>01</span><h3>Сира или Шираз</h3><p>Это два названия одного красного сорта. На этикетке имя часто подсказывает стилистический контекст, но не гарантирует конкретный вкус.</p></article><article><span>02</span><h3>Вионье</h3><p>Это белый ароматный сорт. Его иногда используют рядом с Сира, чтобы показать более цветочный и мягкий образ вина.</p></article><article><span>03</span><h3>Почему это важно</h3><p>Сорт помогает сформировать ожидание. Регион, год и способ производства объясняют, почему два вина из похожего винограда могут отличаться.</p></article></div>
        <div class="demo-callout"><AppIcon name="info" /><p>Сира и Вионье — фиксированный пример интерфейса. Это не утверждение о составе вина «{{ wine.name }}» и не дегустационная оценка.</p></div>
      </template>

      <template v-else-if="active === 'taste'">
        <div class="taste-summary"><p class="step-label">ОЖИДАЕМЫЙ СТИЛЬ</p><h3>{{ wine.name }}</h3><p>{{ taste.summary }}</p><div class="aroma-list"><span v-for="aroma in taste.aromas" :key="aroma.label" :class="aroma.basis">{{ aroma.label }}<small>{{ aroma.basis === 'source' ? 'из описания' : aroma.basis === 'dataset' ? 'из датасета' : 'по стилю' }}</small></span></div></div>
        <div v-if="taste.datasetSource" class="dataset-evidence"><div><span>ОТКРЫТЫЕ ДАННЫЕ</span><p v-if="taste.datasetPriors.length">Пробелы в карточке дополняют агрегаты: {{ taste.datasetPriors.map(item => `${item.sourceVariety} — ${item.sampleCount.toLocaleString('ru-RU')} обзоров`).join(' · ') }}.</p><p v-else>Для сортов этого вина нет надёжного соответствия в агрегатах. Профиль использует карточку и правила винных стилей.</p></div><a :href="taste.datasetSource.url" target="_blank" rel="noopener noreferrer">{{ taste.datasetSource.name }} · {{ taste.datasetSource.license }}</a></div>
        <div class="taste-metrics"><article v-for="item in taste.metrics" :key="item.key"><div><span>{{ item.label }}</span><strong>{{ item.level }}</strong></div><div class="taste-track" role="meter" :aria-label="item.label" :aria-valuenow="item.value" aria-valuemin="1" aria-valuemax="5"><span :style="{ width: `${item.value * 20}%` }" /></div><small>{{ item.detail }}</small></article></div>
        <article class="international-twin"><div class="twin-marker">≈</div><div><p class="step-label">МЕЖДУНАРОДНЫЙ ОРИЕНТИР</p><h3>{{ taste.twin.name }}</h3><p class="twin-place">{{ taste.twin.place }} · {{ taste.twin.basisLabel }}</p><p><strong>Что общего.</strong> {{ taste.twin.shared }}</p><p><strong>Что может отличаться.</strong> {{ taste.twin.difference }}</p></div></article>
        <div class="demo-callout"><AppIcon name="info" /><p><strong>Не дегустационная оценка.</strong> Профиль рассчитан по карточке «Своё Вино» и правилам винных стилей. Международный ориентир сравнивает структуру, а не качество, цену или рейтинг конкретных бутылок.</p></div>
      </template>

      <template v-else-if="active === 'line'">
        <div class="line-toolbar"><div><p v-if="matchedLineWine">Найденное вино отмечено на карте линейки.</p><p v-else-if="lineUsesMatchedProducer">Найдено вино производителя «Абрау-Дюрсо».</p><p v-else>Премиальные примеры расположены выше, массовые — ниже.</p><small>{{ lineUsesMatchedProducer ? 'Карта показывает шесть примеров и не является рейтингом качества.' : 'Это демонстрация навигации, а не рейтинг качества.' }}</small></div><div><button class="map-control" aria-label="Уменьшить карту" :disabled="mapZoom <= .75" @click="changeZoom(-.15)"><AppIcon name="minus" /></button><button class="map-control current-control" :aria-label="matchedLineWine ? 'Показать ваше вино' : lineUsesMatchedProducer ? 'Для этого вина нет узла на карте' : 'Показать демонстрационный пример'" :disabled="!currentLineWine" @click="locateCurrent"><AppIcon name="navigation" /></button><button class="map-control" aria-label="Увеличить карту" :disabled="mapZoom >= 1.3" @click="changeZoom(.15)"><AppIcon name="plus" /></button></div></div>
        <article v-if="lineUsesMatchedProducer && !matchedLineWine" class="line-live-match"><img :src="wine.image" alt="" width="72" height="96"><div><p class="step-label">НАЙДЕНО ВИНО АБРАУ-ДЮРСО</p><h3>{{ wine.name }}</h3><p>Отдельного узла для этого вина пока нет. Карта ниже показывает шесть примеров линейки.</p></div><a :href="wine.source" target="_blank" rel="noopener noreferrer">Открыть вино<AppIcon name="arrow-up-right" /></a></article>
        <div ref="lineViewport" class="line-viewport" :style="mapSurfaceStyle"><div class="line-canvas" :style="mapCanvasStyle"><span class="tier tier-premium">ПРЕМИАЛЬНАЯ КОЛЛЕКЦИЯ</span><span class="tier tier-classic">КЛАССИЧЕСКАЯ КОЛЛЕКЦИЯ</span><span class="tier tier-everyday">НА КАЖДЫЙ ДЕНЬ</span><svg class="line-paths" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d="M30 12 C45 25 55 12 68 23 S48 43 34 49 S59 48 72 57 S47 73 31 82 S54 83 69 89" /></svg><button v-for="item in lineItems" :key="item.url" class="line-node" :class="{ current: item.current, selected: selectedLineWine.url === item.url }" :data-current="item.current || undefined" :style="{ left: `${item.x}%`, top: `${item.y}%` }" :aria-label="`${item.name}. Двойной клик откроет карточку`" @click="selectLineWine(item)" @dblclick="openLineWine(item)"><span class="mini-bottle"><img :src="item.image" alt="" width="52" height="84" loading="lazy" decoding="async"></span><strong>{{ item.name }}</strong><small v-if="item.current">{{ matchedLineWine ? 'ВАШЕ ВИНО' : 'ПРИМЕР · ДЕМО' }}</small></button></div></div>
        <div class="line-selection"><div><p class="step-label">ВЫБРАНО НА КАРТЕ</p><h3>{{ selectedLineWine.name }}</h3><p>{{ selectedLineWine.tier }}. Дважды нажмите узел мышью или используйте ссылку.</p></div><a :href="selectedLineWine.url" class="button primary" target="_blank" rel="noopener noreferrer">Открыть на «Свое Вино»<AppIcon name="arrow-up-right" /></a></div>
      </template>
    </dialog>
  </section>
</template>
