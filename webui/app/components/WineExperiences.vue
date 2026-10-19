<script setup lang="ts">
import type { Wine } from '#shared/catalog'
import { loadProductLine, resolveProductLine } from '#shared/product-line-map'
import type { ProductLineMapData } from '#shared/product-line-map'
import { deriveWineTasteExperience } from '#shared/taste'

type Experience = 'food' | 'label' | 'taste' | 'line'

const props = withDefaults(defineProps<{ wine: Wine; recognized?: boolean }>(), { recognized: true })
const dialog = ref<HTMLDialogElement>()
const dialogHeading = ref<HTMLElement>()
const lineMap = ref<{ centerInitial: () => Promise<void> }>()
const active = ref<Experience | null>(null)
// The index gives the producer and the match state. The map data loads only for the guide.
const lineResolution = computed(() => resolveProductLine(props.wine))
const lineProducer = computed(() => 'producer' in lineResolution.value ? lineResolution.value.producer : undefined)
const lineMatched = computed(() => 'product_id' in lineResolution.value)
const loadedLine = shallowRef<ProductLineMapData>()
const lineFailed = ref(false)
const producerLine = computed(() => loadedLine.value && loadedLine.value.producer.id === lineProducer.value?.id ? loadedLine.value : undefined)
const lineLoading = computed(() => active.value === 'line' && Boolean(lineProducer.value) && !producerLine.value && !lineFailed.value)
let opener: HTMLElement | null = null

const title = computed(() => ({
  food: 'Блюда к вашему вину',
  label: 'Что расскажет этикетка',
  taste: 'Паспорт вкуса',
  line: lineProducer.value ? `Карта линейки ${lineProducer.value.name}` : 'Карта линейки производителя',
}[active.value || 'food']))
const varieties = computed(() => props.wine.grapes.length ? props.wine.grapes.join(', ') : 'Сорт не указан в карточке')
const taste = computed(() => deriveWineTasteExperience(props.wine))
const dialogEyebrow = computed(() => active.value === 'line' ? 'ПУТЕВОДИТЕЛЬ ПО ЛИНЕЙКЕ' : 'ДЕМОНСТРАЦИЯ ВОЗМОЖНОСТИ')
const lineActionSubtitle = computed(() => lineMatched.value ? (props.recognized ? 'Ваше вино отмечено на карте' : 'Выбранное вино отмечено на карте') : lineProducer.value ? 'Линейка вашего производителя' : 'Карта производителя пока не подготовлена')

async function open(kind: Experience, event: MouseEvent) {
  opener = event.currentTarget as HTMLElement
  active.value = kind
  await nextTick()
  dialog.value?.showModal()
  dialogHeading.value?.focus({ preventScroll: true })
  if (kind === 'line') await showLine()
}

async function prepareLine() {
  const producer = lineProducer.value
  if (!producer || producerLine.value) return
  lineFailed.value = false
  try {
    const line = await loadProductLine(producer.id)
    if (lineProducer.value?.id !== producer.id) return
    if (line) loadedLine.value = line
    else lineFailed.value = true
  } catch {
    if (lineProducer.value?.id === producer.id) lineFailed.value = true
  }
}

async function showLine() {
  await prepareLine()
  if (active.value !== 'line') return
  await nextTick()
  await lineMap.value?.centerInitial()
  // A successful retry removes the focused «Повторить» button. Keep focus inside the dialog.
  if (!dialog.value?.contains(document.activeElement)) dialogHeading.value?.focus({ preventScroll: true })
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

onBeforeUnmount(() => dialog.value?.close())
</script>

<template>
  <section class="experience-panel" aria-labelledby="experience-heading">
    <div class="experience-heading">
      <div><p class="step-label">03 / ПРОДОЛЖИТЬ ЗНАКОМСТВО</p><h2 id="experience-heading">Что ещё узнать о вине?</h2></div>
      <span class="demo-badge">О ВИНЕ И ПРОИЗВОДИТЕЛЕ</span>
    </div>
    <p class="experience-lead">Узнайте больше о вине и найдите другие продукты его производителя.</p>
    <div class="experience-grid">
      <button class="experience-action" @click="open('food', $event)"><span class="experience-icon"><AppIcon name="food" /></span><span><strong>Подобрать блюда</strong><small>Кухни России и соседних регионов</small></span><AppIcon name="arrow" /></button>
      <button class="experience-action" @click="open('label', $event)"><span class="experience-icon"><AppIcon name="book" /></span><span><strong>Рассказать об этикетке</strong><small>Сорта, термины и почему это важно</small></span><AppIcon name="arrow" /></button>
      <button class="experience-action" @click="open('taste', $event)"><span class="experience-icon"><AppIcon name="taste" /></span><span><strong>Паспорт вкуса</strong><small>Профиль и международный ориентир</small></span><AppIcon name="arrow" /></button>
      <button class="experience-action" @pointerenter="prepareLine" @focus="prepareLine" @click="open('line', $event)"><span class="experience-icon"><AppIcon name="map" /></span><span><strong>Путеводитель по линейке</strong><small>{{ lineActionSubtitle }}</small></span><AppIcon name="arrow" /></button>
    </div>

    <dialog ref="dialog" class="experience-dialog" :class="{ 'product-line-dialog': active === 'line' }" :aria-labelledby="active ? 'experience-dialog-heading' : undefined" :aria-busy="lineLoading" @cancel.prevent="close" @click="backdrop" @close="closed">
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
        <ProductLineMap v-if="producerLine" ref="lineMap" :key="wine.slug" :line="producerLine" :initial-slug="wine.slug" :recognized="recognized" :unmatched-wine="lineMatched ? undefined : wine" />
        <p v-else-if="lineLoading" class="line-loading" role="status"><span class="spinner" aria-hidden="true" />Загружаем карту линейки…</p>
        <div v-else-if="lineProducer" class="line-unavailable" role="alert">
          <AppIcon name="map" />
          <h3>Не удалось загрузить карту</h3>
          <p>Проверьте подключение к интернету и попробуйте ещё раз.</p>
          <button type="button" class="button secondary" @click="showLine">Повторить</button>
        </div>
        <div v-else class="line-unavailable" role="status">
          <AppIcon name="map" />
          <h3>Карта этого производителя пока не подготовлена</h3>
          <p>{{ wine.producer || 'Производитель не указан в карточке' }}. Для этого вина пока нет проверенной карты линейки.</p>
          <NuxtLink to="/lineup" target="_blank" rel="noopener noreferrer" class="button secondary" @click="close">Все карты производителей<AppIcon name="arrow" /></NuxtLink>
        </div>
      </template>
    </dialog>
  </section>
</template>

<style scoped>
.product-line-dialog { width: min(1370px, calc(100% - 32px)); padding: 24px; }
.product-line-dialog .experience-dialog-header { padding-bottom: 16px; }
.product-line-dialog .experience-dialog-header h2 { font-size: clamp(25px, 3vw, 36px); }
.line-unavailable { padding: 36px 8px; display: grid; gap: 18px; justify-items: start; }
.line-unavailable p { color: var(--muted); line-height: 1.6; }
.line-loading { display: flex; align-items: center; gap: 12px; padding: 36px 8px; color: var(--muted); }
@media (max-width: 700px) {
  .product-line-dialog { width: 100%; max-width: 100%; max-height: 100dvh; height: 100dvh; margin: 0; padding: 16px 12px max(16px, env(safe-area-inset-bottom)); border-radius: 0; }
  .product-line-dialog .experience-dialog-header { gap: 10px; }
}
</style>
