<script setup lang="ts">
import { DINNER_CATEGORIES, DINNER_NODES, dinnerNode, type DinnerSelection } from '#shared/dinner'

defineProps<{ available: boolean }>()
const scanner = useDinnerLens()
const { dish, preview, phase, page, wines, error, question, busy, file } = scanner
const upload = ref<HTMLInputElement>(); const camera = ref<HTMLInputElement>(); const dishInput = ref<HTMLInputElement>()
const settings = reactive({ heat: '', cream: '', acidity: '', sweetSauce: '', color: '', sweetness: '', kind: '', excludeProducer: '' })
const resultHeading = ref<HTMLElement>()
const category = ref('')
function selectPhoto(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || []); input.value = ''; void scanner.select(files)
}
function chooseCategory(event: Event) {
  const node = dinnerNode((event.target as HTMLSelectElement).value)
  if (node) { dish.value = node.label; scanner.invalidate(); dishInput.value?.focus() }
}
function update() { if (phase.value !== 'recognizing') scanner.invalidate() }
async function submit() {
  if (!dish.value.trim()) { dishInput.value?.focus(); return }
  const attributes: Record<string, string | boolean> = {}
  if (settings.heat) attributes.heat = settings.heat
  if (settings.acidity) attributes.acidity = settings.acidity
  if (settings.sweetSauce) attributes.sauce_sweetness = settings.sweetSauce
  if (settings.cream) attributes.fatty_cream_sauce = settings.cream === 'yes'
  const constraints: Record<string, string> = {}
  if (settings.color) constraints.color = settings.color
  if (settings.sweetness) constraints.sweetness = settings.sweetness
  if (settings.kind) constraints.wine_kind = settings.kind
  if (settings.excludeProducer.trim()) constraints.exclude_producer = settings.excludeProducer.trim()
  const exact = DINNER_NODES.find(node => node.label.toLocaleLowerCase('ru') === dish.value.trim().toLocaleLowerCase('ru'))
  const selection: DinnerSelection = { ...(exact ? { node_id: exact.id } : { confirmed_dish: dish.value.trim() }),
    confirmed_attributes: attributes, user_constraints: constraints }
  await scanner.recommend(selection)
  if (phase.value === 'ready') { await nextTick(); resultHeading.value?.focus({ preventScroll: true }); resultHeading.value?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' }) }
}
const labels: Record<string, string> = { red: 'Красное', white: 'Белое', rose: 'Розовое', orange: 'Оранжевое', dry: 'Сухое', semi_dry: 'Полусухое', semi_sweet: 'Полусладкое', sweet: 'Сладкое', brut: 'Брют', extra_brut: 'Экстра-брют', brut_nature: 'Брют натюр', still: 'Тихое', sparkling: 'Игристое' }
const selectedLabel = computed(() => dinnerNode(page.value?.resolved_node_id)?.label || dish.value)
</script>

<template>
  <section class="dinner-scanner" aria-label="Вино к блюду">
    <p v-if="!available" class="dinner-notice" role="status"><AppIcon name="info" />Подбор вина временно недоступен. Попробуйте позже.</p>
    <div class="dinner-entry">
      <div class="dinner-photo-panel">
        <div v-if="preview" class="dinner-preview"><img :src="preview" alt="Выбранное фото блюда"><button class="button secondary" type="button" @click="scanner.reset(); category = ''">Убрать фото<AppIcon name="close" /></button></div>
        <div v-else class="dinner-photo-placeholder" aria-hidden="true"><div class="dinner-plate"><AppIcon name="food" /></div></div>
        <div class="dinner-photo-copy"><p class="step-label">НАЧНИТЕ С БЛЮДА</p><h2>Ваш стол.<br> <span>Подходящее вино.</span></h2><p>Покажите блюдо, а затем подтвердите название и соус. Или сразу введите название рядом.</p></div>
        <div class="upload-actions dinner-upload-actions"><button class="button primary" type="button" :disabled="!available" @click="upload?.click()"><AppIcon name="upload" />{{ preview ? 'Заменить фото' : 'Загрузить фото' }}</button><button class="button secondary camera-action" type="button" :disabled="!available" @click="camera?.click()"><AppIcon name="camera" />Снять блюдо</button></div>
        <input ref="upload" class="sr-only" tabindex="-1" type="file" accept="image/jpeg,image/png,image/webp" aria-label="Фото блюда" @change="selectPhoto">
        <input ref="camera" class="sr-only" tabindex="-1" type="file" accept="image/jpeg,image/png" capture="environment" aria-label="Снять блюдо камерой" @change="selectPhoto">
        <p class="upload-hint">JPEG, PNG, WebP · до 10 МБ</p>
        <button v-if="file && !busy && (error || !dish.trim())" class="example-button" type="button" :disabled="!available" @click="scanner.recognize()">Повторить распознавание<AppIcon name="arrow" /></button>
      </div>
      <form class="dinner-form" @submit.prevent="submit" @change="update">
        <p class="step-label">{{ preview ? 'ПРОВЕРЬТЕ БЛЮДО И СОУС' : 'ИЛИ НАЗОВИТЕ БЛЮДО' }}</p>
        <h2>{{ preview ? 'Всё верно?' : 'Что сегодня на столе?' }}</h2>
        <p v-if="question" class="dinner-question" role="status">{{ question }}</p>
        <label for="dinner-dish">Название блюда</label>
        <input id="dinner-dish" ref="dishInput" v-model="dish" list="dinner-dishes" type="search" maxlength="500" placeholder="Например, стейк рибай на гриле" :disabled="!available || phase === 'recognizing'" required autocomplete="off" @input="update">
        <datalist id="dinner-dishes"><option v-for="node in DINNER_NODES" :key="node.id" :value="node.label" /></datalist>
        <p class="dinner-field-hint">Фотография не раскрывает состав блюда. Уточните название, прежде чем выбирать вино.</p>
        <label for="dinner-category">Можно выбрать общую категорию</label>
        <select id="dinner-category" v-model="category" :disabled="!available || phase === 'recognizing'" @change="chooseCategory"><option value="">Выберите, если точное блюдо неизвестно</option><option v-for="node in DINNER_CATEGORIES" :key="node.id" :value="node.id">{{ node.label }}</option></select>
        <details class="dinner-options"><summary>Уточнить соус и вино<AppIcon name="filter" /></summary><div class="dinner-options-grid">
          <label>Острота<select aria-label="Острота" v-model="settings.heat" :disabled="!available"><option value="">Как в рецепте</option><option value="none">Неострое</option><option value="low">Слегка острое</option><option value="medium">Умеренно острое</option><option value="high">Острое</option></select></label>
          <label>Сливочный соус<select aria-label="Сливочный соус" v-model="settings.cream" :disabled="!available"><option value="">Как в рецепте</option><option value="yes">Со сливочным соусом</option><option value="no">Без сливочного соуса</option></select></label>
          <label>Кислотность блюда<select aria-label="Кислотность блюда" v-model="settings.acidity" :disabled="!available"><option value="">Как в рецепте</option><option value="low">Мягкий вкус</option><option value="medium">Умеренная кислинка</option><option value="high">Выраженная кислинка, лимон</option></select></label>
          <label>Сладость соуса<select aria-label="Сладость соуса" v-model="settings.sweetSauce" :disabled="!available"><option value="">Как в рецепте</option><option value="none">Несладкий соус</option><option value="low">Слегка сладкий</option><option value="medium">Заметно сладкий</option><option value="high">Сладкая глазурь</option></select></label>
          <label>Цвет вина<select aria-label="Цвет вина" v-model="settings.color" :disabled="!available"><option value="">Любой подходящий</option><option v-for="color in ['red', 'white', 'rose', 'orange']" :key="color" :value="color">{{ labels[color] }}</option></select></label>
          <label>Сладость вина<select aria-label="Сладость вина" v-model="settings.sweetness" :disabled="!available"><option value="">Любая подходящая</option><option v-for="sweetness in ['dry', 'semi_dry', 'semi_sweet', 'sweet', 'brut', 'extra_brut', 'brut_nature']" :key="sweetness" :value="sweetness">{{ labels[sweetness] }}</option></select></label>
          <label>Тихое или игристое<select aria-label="Тихое или игристое" v-model="settings.kind" :disabled="!available"><option value="">Любое подходящее</option><option value="still">Тихое</option><option value="sparkling">Игристое</option></select></label>
          <label>Исключить производителя<input aria-label="Исключить производителя" v-model="settings.excludeProducer" maxlength="400" placeholder="Название винодельни" :disabled="!available" @input="update"></label>
        </div></details>
        <button class="button primary dinner-submit" type="submit" :disabled="!available || busy || !dish.trim()"><AppIcon name="taste" />{{ preview ? 'Подтвердить и подобрать вино' : 'Подобрать вино' }}</button>
        <p class="dinner-field-hint">Рецепт, соус и острота влияют на сочетание. Выбор можно изменить.</p>
      </form>
    </div>
    <div v-if="busy" class="dinner-progress" role="status" aria-live="polite"><span class="spinner" /><p>{{ phase === 'recognizing' ? 'Рассматриваем блюдо. Название можно будет исправить.' : phase === 'more' ? 'Ищем следующие подходящие вина.' : 'Подбираем вино с учётом блюда и соуса.' }}</p><button class="button secondary" type="button" @click="scanner.cancel()">Отменить</button></div>
    <p v-if="error" class="dinner-error" role="alert">{{ error }}</p>
    <section v-if="phase === 'ready' || wines.length" class="dinner-results" aria-label="Подобранные вина">
      <p class="step-label">К ВАШЕМУ СТОЛУ</p><h2 ref="resultHeading" tabindex="-1">Вино к вашему блюду</h2><p class="dinner-result-context">{{ selectedLabel }}</p>
      <p v-if="page?.status === 'no_results'" class="dinner-notice" role="status">Подтверждённых сочетаний с этими условиями пока нет. Попробуйте уточнить блюдо или изменить ограничения.</p>
      <p v-else-if="page?.needs_clarification && question" class="dinner-field-hint">{{ question }}</p>
      <div class="dinner-wines"><article v-for="wine in wines" :key="wine.wine_slug" class="dinner-wine">
        <div class="dinner-wine-top"><AppIcon name="taste" /><span>{{ wine.selection_source === 'curated' ? 'Подборка к блюду' : 'Ещё один вариант' }}</span></div>
        <p class="dinner-producer">{{ wine.producer }}</p><h3>{{ wine.name }}</h3>
        <p class="dinner-wine-facts">{{ labels[wine.facts.color] }} · {{ labels[wine.facts.sweetness] }} · {{ labels[wine.facts.wine_kind] }}<template v-if="wine.facts.alcohol_percent !== null"> · {{ wine.facts.alcohol_percent }}%</template></p>
        <p v-if="wine.facts.reported_grapes.length" class="dinner-grapes">{{ wine.facts.reported_grapes.join(', ') }}</p>
        <p class="dinner-reason">{{ wine.reason }}</p><a :href="wine.source_url" class="button secondary" target="_blank" rel="noopener noreferrer">Карточка вина<AppIcon name="arrow-up-right" /></a>
      </article></div>
      <button v-if="page?.next_cursor" class="button secondary dinner-more" type="button" :disabled="busy" @click="scanner.more()">Показать ещё<AppIcon name="arrow" /></button>
      <p v-else-if="wines.length" class="dinner-field-hint dinner-end">Все подходящие варианты из текущей подборки показаны.</p>
      <p v-if="wines.length" class="dinner-field-hint dinner-end">Сочетания основаны на данных карточек и правилах подбора. Наличие и цены уточняйте отдельно.</p>
    </section>
  </section>
</template>

<style scoped>
.dinner-entry { display: grid; grid-template-columns: .9fr 1.1fr; border: 1px solid var(--line); border-radius: 24px; background: var(--paper); overflow: hidden; }
.dinner-photo-panel { padding: 36px; text-align: center; background: var(--cream); display: flex; flex-direction: column; align-items: center; }
.dinner-photo-placeholder { display: grid; place-items: center; min-height: 170px; width: 100%; }
.dinner-plate { width: 138px; height: 138px; display: grid; place-items: center; border: 1px solid var(--line); box-shadow: inset 0 0 0 14px var(--paper), inset 0 0 0 15px var(--line); border-radius: 50%; color: var(--accent); }
.dinner-plate .icon { width: 48px; height: 48px; }
.dinner-photo-copy h2 { font-size: 34px; margin: 16px 0; line-height: 1.2; }
.dinner-photo-copy h2 span { color: var(--accent); }
.dinner-photo-copy>p:last-child { font-size: 14px; color: var(--muted); line-height: 1.7; max-width: 360px; margin-bottom: 24px; }
.dinner-upload-actions { justify-content: center; flex-wrap: wrap; width: 100%; }
.dinner-preview { width: 100%; margin-bottom: 24px; position: relative; }
.dinner-preview img { width: 100%; max-height: 300px; object-fit: contain; border-radius: 14px; }
.dinner-preview button { margin: 12px auto 0; font-size: 12px; }
.dinner-form { padding: 40px; min-width: 0; }
.dinner-form h2 { font-size: 28px; margin: 14px 0 24px; }
.dinner-form label { display: block; font-size: 12px; font-weight: 600; margin: 18px 0 8px; }
.dinner-form input, .dinner-form select { display: block; width: 100%; min-width: 0; min-height: 46px; padding: 12px; margin-top: 8px; border: 1px solid var(--line); border-radius: 9px; background: var(--paper); color: var(--ink); font: inherit; font-size: 14px; }
.dinner-field-hint { color: var(--muted); font-size: 12px; line-height: 1.65; margin-top: 10px; }
.dinner-question { color: var(--accent); line-height: 1.6; font-size: 14px; }
.dinner-options { margin: 24px 0; border-block: 1px solid var(--line); padding-block: 16px; }
.dinner-options summary { display: flex; justify-content: space-between; align-items: center; cursor: pointer; font-size: 13px; min-height: 28px; }
.dinner-options-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 0 16px; }
.dinner-options-grid label { line-height: 1.5; }
.dinner-submit { width: 100%; margin-top: 22px; }
.dinner-progress { display: flex; align-items: center; justify-content: center; gap: 18px; margin-top: 24px; padding: 20px; border: 1px solid var(--line); border-radius: 14px; }
.dinner-progress p { color: var(--muted); font-size: 14px; line-height: 1.5; }
.dinner-progress .spinner { flex-shrink: 0; }
.dinner-error, .dinner-notice { display: flex; gap: 12px; align-items: center; border: 1px solid var(--line); padding: 18px; border-radius: 12px; background: var(--cream); line-height: 1.6; font-size: 14px; margin-bottom: 20px; }
.dinner-error { margin-top: 20px; color: var(--accent); }
.dinner-results { margin-top: 52px; }
.dinner-results>h2 { font-size: 36px; margin: 14px 0 10px; scroll-margin-top: 110px; }
.dinner-result-context { color: var(--muted); line-height: 1.6; margin-bottom: 24px; }
.dinner-wines { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 20px; margin-top: 24px; }
.dinner-wine { border: 1px solid var(--line); border-radius: 18px; background: var(--paper); padding: 26px; display: flex; flex-direction: column; min-width: 0; }
.dinner-wine-top { display: flex; justify-content: space-between; align-items: center; gap: 12px; color: var(--accent); font-size: 10px; margin-bottom: 24px; }
.dinner-wine-top .icon { width: 30px; height: 30px; }
.dinner-producer { color: var(--muted); font-size: 11px; margin-bottom: 8px; }
.dinner-wine h3 { font-size: 22px; line-height: 1.35; overflow-wrap: anywhere; }
.dinner-wine-facts, .dinner-grapes { font-size: 12px; line-height: 1.7; color: var(--muted); margin-top: 14px; }
.dinner-reason { font-size: 13px; line-height: 1.75; margin: 18px 0 24px; }
.dinner-wine>.button { margin-top: auto; font-size: 12px; }
.dinner-more { display: flex; margin: 28px auto; }
.dinner-end { text-align: center; }
@media(max-width: 1023px) { .dinner-photo-panel, .dinner-form { padding: 28px; } .dinner-options-grid { grid-template-columns: 1fr; } .dinner-wines { grid-template-columns: repeat(2,minmax(0,1fr)); } }
@media(max-width: 767px) { .dinner-entry { grid-template-columns: 1fr; border-radius: 20px; } .dinner-photo-panel, .dinner-form { padding: 24px; } .dinner-photo-placeholder { min-height: 140px; } .dinner-plate { width: 116px; height: 116px; } .dinner-photo-copy h2 { font-size: 30px; } .dinner-photo-copy h2 br { display: none; } .dinner-form h2 { font-size: 26px; } .dinner-form input, .dinner-form select { font-size: 16px; } .dinner-wines { grid-template-columns: 1fr; } .dinner-results>h2 { font-size: 30px; } .dinner-progress { flex-wrap: wrap; } .dinner-progress p { flex: 1; min-width: 160px; } .dinner-progress>.button { width: 100%; } .dinner-submit { font-size: 12px; padding-inline: 8px; } }
</style>
