<script setup lang="ts">
import type { Wine } from '#shared/catalog'
import { ABRAU_LINE, DEMO_FOOD_PRODUCTS, WINE_STORIES, nextStoryIndex, type ProductLineWine } from '#shared/experiences'

type Experience = 'food' | 'label' | 'story' | 'line'
type ProductPhase = 'permission' | 'locating' | 'ready'

const props = defineProps<{ wine: Wine }>()
const dialog = ref<HTMLDialogElement>()
const dialogHeading = ref<HTMLElement>()
const lineViewport = ref<HTMLElement>()
const active = ref<Experience | null>(null)
const productPhase = ref<ProductPhase>('permission')
const storyIndex = ref(0)
const mapZoom = ref(1)
const selectedLineWine = shallowRef<ProductLineWine>(ABRAU_LINE.find(item => item.current) || ABRAU_LINE[0]!)
let opener: HTMLElement | null = null
let locationTimer: ReturnType<typeof setTimeout> | undefined

const title = computed(() => ({
  food: 'Продукты к вашему вину',
  label: 'Что расскажет этикетка',
  story: 'История для этого вина',
  line: 'Карта линейки Абрау-Дюрсо',
}[active.value || 'food']))
const varieties = computed(() => props.wine.grapes.length ? props.wine.grapes.join(', ') : 'Сорт не указан в карточке')
const story = computed(() => WINE_STORIES[storyIndex.value]!)
const mapCanvasStyle = computed(() => ({ transform: `scale(${mapZoom.value})`, transformOrigin: 'top center' }))
const mapSurfaceStyle = computed(() => ({ height: `${620 * mapZoom.value}px` }))

async function open(kind: Experience, event: MouseEvent) {
  opener = event.currentTarget as HTMLElement
  active.value = kind
  if (kind === 'food') productPhase.value = 'permission'
  if (kind === 'story') storyIndex.value = nextStoryIndex(storyIndex.value)
  if (kind === 'line') { mapZoom.value = 1; selectedLineWine.value = ABRAU_LINE.find(item => item.current) || ABRAU_LINE[0]! }
  await nextTick()
  dialog.value?.showModal()
  dialogHeading.value?.focus({ preventScroll: true })
  if (kind === 'line') await locateCurrent()
}

function close() { dialog.value?.close() }
function closed() {
  active.value = null
  if (locationTimer) clearTimeout(locationTimer)
  locationTimer = undefined
  opener?.focus({ preventScroll: true })
}
function backdrop(event: MouseEvent) {
  if (event.target !== dialog.value) return
  const rect = dialog.value.getBoundingClientRect()
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close()
}
function allowLocation() {
  productPhase.value = 'locating'
  locationTimer = setTimeout(() => { productPhase.value = 'ready'; locationTimer = undefined }, 700)
}
function anotherStory() { storyIndex.value = nextStoryIndex(storyIndex.value) }
function changeZoom(change: number) { mapZoom.value = Math.min(1.3, Math.max(.75, Number((mapZoom.value + change).toFixed(2)))) }
async function locateCurrent() {
  const current = ABRAU_LINE.find(item => item.current)
  if (current) selectedLineWine.value = current
  await nextTick()
  lineViewport.value?.querySelector<HTMLElement>('[data-current="true"]')?.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' })
}
function selectLineWine(item: ProductLineWine) { selectedLineWine.value = item }
function openLineWine(item: ProductLineWine) { window.open(item.url, '_blank', 'noopener,noreferrer') }

onBeforeUnmount(() => { if (locationTimer) clearTimeout(locationTimer); dialog.value?.close() })
</script>

<template>
  <section class="experience-panel" aria-labelledby="experience-heading">
    <div class="experience-heading">
      <div><p class="step-label">03 / ПРОДОЛЖИТЬ ЗНАКОМСТВО</p><h2 id="experience-heading">Что ещё узнать о вине?</h2></div>
      <span class="demo-badge">ДЕМО-ФУНКЦИИ</span>
    </div>
    <p class="experience-lead">Четыре идеи показывают, как портал может продолжить диалог после распознавания.</p>
    <div class="experience-grid">
      <button class="experience-action" @click="open('food', $event)"><span class="experience-icon"><AppIcon name="food" /></span><span><strong>Подобрать продукты</strong><small>Российские продукты в магазине рядом</small></span><AppIcon name="arrow" /></button>
      <button class="experience-action" @click="open('label', $event)"><span class="experience-icon"><AppIcon name="book" /></span><span><strong>Рассказать об этикетке</strong><small>Сорта, термины и почему это важно</small></span><AppIcon name="arrow" /></button>
      <button class="experience-action" @click="open('story', $event)"><span class="experience-icon"><AppIcon name="story" /></span><span><strong>История о вине</strong><small>Небольшая байка вместо аудио</small></span><AppIcon name="arrow" /></button>
      <button class="experience-action" @click="open('line', $event)"><span class="experience-icon"><AppIcon name="map" /></span><span><strong>Путеводитель по линейке</strong><small>Карта вин одного производителя</small></span><AppIcon name="arrow" /></button>
    </div>

    <dialog ref="dialog" class="experience-dialog" :aria-labelledby="active ? 'experience-dialog-heading' : undefined" @cancel.prevent="close" @click="backdrop" @close="closed">
      <header class="experience-dialog-header"><div><p class="step-label">ДЕМОНСТРАЦИЯ ВОЗМОЖНОСТИ</p><h2 id="experience-dialog-heading" ref="dialogHeading" tabindex="-1">{{ title }}</h2></div><button class="icon-button" aria-label="Закрыть окно" @click="close"><AppIcon name="close" /></button></header>

      <template v-if="active === 'food'">
        <div v-if="productPhase === 'permission'" class="mock-location">
          <div class="dialog-emblem"><AppIcon name="location" /></div><h3>Найти магазин рядом?</h3>
          <p>В будущем координаты помогут определить конкретный магазин и проверить его ассортимент. Сейчас это mock-сценарий: браузер не запросит координаты и ничего не сохранит.</p>
          <div class="dialog-actions"><button class="button primary" @click="allowLocation">Разрешить в демо</button><button class="button secondary" @click="close">Не сейчас</button></div>
        </div>
        <div v-else-if="productPhase === 'locating'" class="experience-progress" role="status"><span class="spinner" /><h3>Определяем магазин…</h3><p>Имитируем выбор магазина по координатам.</p></div>
        <div v-else class="mock-products">
          <div class="mock-store"><span class="experience-icon"><AppIcon name="store" /></span><div><p class="step-label">МАГАЗИН РЯДОМ · MOCK</p><h3>СуперЛента на Ленинградском шоссе</h3><p>Подборка учитывает магазин, российское происхождение и сочетание с вином.</p></div></div>
          <div class="demo-callout"><AppIcon name="info" /><p><strong>Как это может работать.</strong> Магазин сообщает ассортимент. Портал выбирает отечественные продукты к вину. Бренд может получить приоритет, но такая позиция всегда имеет заметную отметку.</p></div>
          <div class="mock-product-grid"><article v-for="product in DEMO_FOOD_PRODUCTS" :key="product.name" class="mock-product"><span v-if="product.promoted" class="promotion-badge">ПРОДВИЖЕНИЕ · ДЕМО</span><div class="mock-product-symbol"><AppIcon name="food" /></div><p class="step-label">{{ product.kind }}</p><h3>{{ product.name }}</h3><p class="product-origin">Сделано в России · {{ product.origin }}</p><p>{{ product.reason }}</p></article></div>
        </div>
      </template>

      <template v-else-if="active === 'label'">
        <div class="label-summary"><p class="step-label">НА ЭТИКЕТКЕ ВАШЕГО ВИНА</p><h3>{{ varieties }}</h3><p>Сервис может превратить короткую надпись на этикетке в понятное объяснение.</p></div>
        <div class="label-compare"><article><span>01</span><h3>Сира или Шираз</h3><p>Это два названия одного красного сорта. На этикетке имя часто подсказывает стилистический контекст, но не гарантирует конкретный вкус.</p></article><article><span>02</span><h3>Вионье</h3><p>Это белый ароматный сорт. Его иногда используют рядом с Сира, чтобы показать более цветочный и мягкий образ вина.</p></article><article><span>03</span><h3>Почему это важно</h3><p>Сорт помогает сформировать ожидание. Регион, год и способ производства объясняют, почему два вина из похожего винограда могут отличаться.</p></article></div>
        <div class="demo-callout"><AppIcon name="info" /><p>Сира и Вионье — фиксированный пример интерфейса. Это не утверждение о составе вина «{{ wine.name }}» и не дегустационная оценка.</p></div>
      </template>

      <template v-else-if="active === 'story'">
        <div class="story-player"><div class="story-wave" aria-hidden="true"><span v-for="n in 18" :key="n" :style="{ height: `${18 + ((n * 17) % 48)}%` }" /></div><span>АУДИО В БУДУЩЕМ · СЕЙЧАС ТЕКСТ</span></div>
        <article class="wine-story"><p class="step-label">СЛУЧАЙНАЯ ИСТОРИЯ</p><h3>{{ story.title }}</h3><p>{{ story.text }}</p></article>
        <div class="dialog-actions"><button class="button primary" @click="anotherStory"><AppIcon name="story" />Другая история</button></div>
        <div class="demo-callout"><AppIcon name="info" /><p>Это художественная байка. Она не описывает реальные события, не сообщает факты о производителе и не рекламирует вино. Позже такой текст можно озвучить.</p></div>
      </template>

      <template v-else-if="active === 'line'">
        <div class="line-toolbar"><div><p>Премиальные примеры расположены выше, массовые — ниже.</p><small>Это демонстрация навигации, а не рейтинг качества.</small></div><div><button class="map-control" aria-label="Уменьшить карту" :disabled="mapZoom <= .75" @click="changeZoom(-.15)"><AppIcon name="minus" /></button><button class="map-control current-control" aria-label="Показать текущее вино" @click="locateCurrent"><AppIcon name="navigation" /></button><button class="map-control" aria-label="Увеличить карту" :disabled="mapZoom >= 1.3" @click="changeZoom(.15)"><AppIcon name="plus" /></button></div></div>
        <div ref="lineViewport" class="line-viewport" :style="mapSurfaceStyle"><div class="line-canvas" :style="mapCanvasStyle"><span class="tier tier-premium">ПРЕМИАЛЬНАЯ КОЛЛЕКЦИЯ</span><span class="tier tier-classic">КЛАССИЧЕСКАЯ КОЛЛЕКЦИЯ</span><span class="tier tier-everyday">НА КАЖДЫЙ ДЕНЬ</span><svg class="line-paths" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d="M30 12 C45 25 55 12 68 23 S48 43 34 49 S59 48 72 57 S47 73 31 82 S54 83 69 90" /></svg><button v-for="item in ABRAU_LINE" :key="item.url" class="line-node" :class="{ current: item.current, selected: selectedLineWine.url === item.url }" :data-current="item.current || undefined" :style="{ left: `${item.x}%`, top: `${item.y}%` }" :aria-label="`${item.name}. Двойной клик откроет карточку`" @click="selectLineWine(item)" @dblclick="openLineWine(item)"><span class="mini-bottle" /><strong>{{ item.name }}</strong><small v-if="item.current">ВАШЕ ВИНО · ДЕМО</small></button></div></div>
        <div class="line-selection"><div><p class="step-label">ВЫБРАНО НА КАРТЕ</p><h3>{{ selectedLineWine.name }}</h3><p>{{ selectedLineWine.tier }}. Дважды нажмите узел мышью или используйте ссылку.</p></div><a :href="selectedLineWine.url" class="button primary" target="_blank" rel="noopener noreferrer">Открыть на «Свое Вино»<AppIcon name="arrow-up-right" /></a></div>
      </template>
    </dialog>
  </section>
</template>
