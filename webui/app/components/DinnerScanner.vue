<script setup lang="ts">
import { DINNER_CATEGORIES, DINNER_NODES, dinnerNode, type DinnerSelection } from '#shared/dinner'
import { DISH_CAMERA_ACCEPT, DISH_IMAGE_ACCEPT } from '#shared/dish-image'

const props = defineProps<{ available: boolean }>()
const scanner = useDinnerLens()
const { dish, preview, phase, page, wines, error, question, busy, file, failedAction } = scanner
const upload = ref<HTMLInputElement>(); const camera = ref<HTMLInputElement>(); const dishInput = ref<HTMLInputElement>()
const uploadButton = ref<HTMLButtonElement>(); const categoryInput = ref<HTMLSelectElement>(); const resultRegion = ref<HTMLElement>()
const announcement = ref('')
const settings = reactive({ heat: '', cream: '', acidity: '', sweetSauce: '' })
const tastePresets = [
  { key: 'heat', value: 'none', label: 'Неострое', icon: 'mild' },
  { key: 'heat', value: 'high', label: 'Острое', icon: 'chilli' },
  { key: 'cream', value: 'yes', label: 'Сливочный', icon: 'cream' },
  { key: 'cream', value: 'no', label: 'Без сливок', icon: 'no-cream' },
  { key: 'acidity', value: 'high', label: 'С кислинкой', icon: 'citrus' },
  { key: 'sweetSauce', value: 'high', label: 'Сладкий соус', icon: 'honey' },
  { key: 'sweetSauce', value: 'none', label: 'Несладкий', icon: 'no-sugar' },
] as const
function toggleTaste(preset: typeof tastePresets[number]) {
  settings[preset.key] = settings[preset.key] === preset.value ? '' : preset.value
  update()
}
const resultHeading = ref<HTMLElement>()
const category = ref('')
const dragDepth = ref(0)
function selectFiles(files: File[]) { category.value = ''; announcement.value = ''; void scanner.select(files) }
function selectPhoto(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || []); input.value = ''; if (files.length) selectFiles(files)
}
function fileDrag(event: DragEvent) { return Array.from(event.dataTransfer?.types || []).includes('Files') }
function preventFileNavigation(event: DragEvent) {
  if (!fileDrag(event)) return
  const handled = event.defaultPrevented; event.preventDefault()
  if (event.type === 'drop') dragDepth.value = 0
  else if (!handled && event.dataTransfer) event.dataTransfer.dropEffect = 'none'
}
onMounted(() => { window.addEventListener('dragover', preventFileNavigation); window.addEventListener('drop', preventFileNavigation) })
onBeforeUnmount(() => { window.removeEventListener('dragover', preventFileNavigation); window.removeEventListener('drop', preventFileNavigation) })
function dragEnter(event: DragEvent) { if (fileDrag(event)) { event.preventDefault(); if (props.available) dragDepth.value++ } }
function dragOver(event: DragEvent) { if (fileDrag(event)) { event.preventDefault(); if (event.dataTransfer) event.dataTransfer.dropEffect = props.available ? 'copy' : 'none' } }
function dragLeave(event: DragEvent) { event.preventDefault(); dragDepth.value = Math.max(0, dragDepth.value - 1) }
function dropPhoto(event: DragEvent) {
  event.preventDefault(); dragDepth.value = 0
  const files = Array.from(event.dataTransfer?.files || [])
  if (props.available && files.length) selectFiles(files)
}
function chooseCategory(event: Event) {
  const node = dinnerNode((event.target as HTMLSelectElement).value)
  if (node) { dish.value = node.label; scanner.invalidate(); dishInput.value?.focus() }
}
function update() { announcement.value = ''; if (phase.value !== 'recognizing') scanner.invalidate() }
function editDish() { category.value = ''; update() }
async function removePhoto() { scanner.reset(); category.value = ''; announcement.value = ''; await nextTick(); uploadButton.value?.focus() }
async function cancel() { scanner.cancel(); await nextTick(); dishInput.value?.focus() }
const progressMessage = computed(() => phase.value === 'recognizing' ? 'Рассматриваем блюдо. Название можно будет исправить.' : phase.value === 'more' ? 'Ищем следующие подходящие вина.' : 'Подбираем вино с учётом блюда и соуса.')
const statusMessage = computed(() => busy.value ? progressMessage.value : announcement.value || (question.value ? (preview.value && dish.value ? `Похоже на: ${dish.value}. ` : '') + question.value : ''))
watch(phase, async (value, previous) => { if (previous === 'recognizing' && ['confirm', 'idle'].includes(value)) { await nextTick(); (error.value ? uploadButton.value : dishInput.value)?.focus() } })
async function showMore() {
  if (busy.value) return
  const before = wines.value.length
  await scanner.more()
  if (wines.value.length > before) {
    announcement.value = `Добавлено вин: ${wines.value.length - before}. Всего показано: ${wines.value.length}.`
    await nextTick(); resultRegion.value?.querySelectorAll<HTMLElement>('.dinner-wine h3')[before]?.focus({ preventScroll: true })
  }
}
async function submit() {
  if (!dish.value.trim()) { dishInput.value?.focus(); return }
  announcement.value = ''
  const attributes: Record<string, string | boolean> = {}
  if (settings.heat) attributes.heat = settings.heat
  if (settings.acidity) attributes.acidity = settings.acidity
  if (settings.sweetSauce) attributes.sauce_sweetness = settings.sweetSauce
  if (settings.cream) attributes.fatty_cream_sauce = settings.cream === 'yes'
  const categoryNode = dinnerNode(category.value)
  const exact = categoryNode?.label === dish.value ? categoryNode : DINNER_NODES.find(node => node.label.toLocaleLowerCase('ru') === dish.value.trim().toLocaleLowerCase('ru'))
  const selection: DinnerSelection = { ...(exact ? { node_id: exact.id } : { confirmed_dish: dish.value.trim() }),
    confirmed_attributes: attributes }
  await scanner.recommend(selection)
  if (page.value?.status === 'needs_category') { await nextTick(); categoryInput.value?.focus(); return }
  if (phase.value === 'ready') { await nextTick(); resultHeading.value?.focus({ preventScroll: true }); resultHeading.value?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' }) }
}
const labels: Record<string, string> = { red: 'Красное', white: 'Белое', rose: 'Розовое', orange: 'Оранжевое', dry: 'Сухое', semi_dry: 'Полусухое', semi_sweet: 'Полусладкое', sweet: 'Сладкое', brut: 'Брют', extra_brut: 'Экстра-брют', brut_nature: 'Брют натюр', still: 'Тихое', sparkling: 'Игристое' }
const selectedLabel = computed(() => dinnerNode(page.value?.resolved_node_id)?.label || dish.value)
</script>

<template>
  <section class="dinner-scanner" aria-label="Вино к блюду">
    <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ statusMessage }}</p>
    <p v-if="!available" class="dinner-notice" role="status"><AppIcon name="info" />Подбор вина временно недоступен. Попробуйте позже.</p>
    <div class="dinner-entry">
      <div class="dinner-photo-panel" :class="{ dragging: dragDepth > 0 }" role="region" aria-label="Загрузка фото блюда" @dragenter="dragEnter" @dragover="dragOver" @dragleave="dragLeave" @drop="dropPhoto">
        <div v-if="dragDepth > 0" class="dinner-drop-overlay" aria-hidden="true"><AppIcon name="upload" /><span>Отпустите фото блюда</span></div>
        <div v-if="preview" class="dinner-preview"><img :src="preview" alt="Выбранное фото блюда"><button class="button secondary" type="button" @click="removePhoto">Убрать фото<AppIcon name="close" /></button></div>
        <div v-else class="dinner-photo-placeholder" aria-hidden="true"><div class="dinner-plate"><AppIcon name="food" /></div></div>
        <div class="dinner-photo-copy"><p class="step-label">НАЧНИТЕ С БЛЮДА</p><h2>Ваш стол.<br> <span>Подходящее вино.</span></h2><p>Покажите блюдо, а затем подтвердите название и соус. Или сразу введите название рядом.</p></div>
        <div class="upload-actions dinner-upload-actions"><button ref="uploadButton" class="button primary" type="button" :disabled="!available" @click="upload?.click()"><AppIcon name="upload" />{{ preview ? 'Заменить фото' : 'Загрузить фото' }}</button><button class="button secondary camera-action" type="button" :disabled="!available" @click="camera?.click()"><AppIcon name="camera" />Снять блюдо</button></div>
        <input ref="upload" class="sr-only" tabindex="-1" type="file" :accept="DISH_IMAGE_ACCEPT" :disabled="!available" aria-label="Фото блюда" @change="selectPhoto">
        <input ref="camera" class="sr-only" tabindex="-1" type="file" :accept="DISH_CAMERA_ACCEPT" :disabled="!available" capture="environment" aria-label="Снять блюдо камерой" @change="selectPhoto">
        <p class="upload-hint">JPEG, HEIC, PNG, WebP<span class="desktop-drop-hint"><br>Можно перетащить фото сюда</span></p>
        <button v-if="file && !busy && failedAction === 'recognizing'" class="example-button" type="button" :disabled="!available" @click="scanner.recognize()">Повторить распознавание<AppIcon name="arrow" /></button>
      </div>
      <form class="dinner-form" @submit.prevent="submit" @change="update">
        <p class="step-label">{{ preview ? 'ПРОВЕРЬТЕ БЛЮДО И СОУС' : 'ИЛИ НАЗОВИТЕ БЛЮДО' }}</p>
        <h2>{{ preview ? 'Всё верно?' : 'Что сегодня на столе?' }}</h2>
        <p v-if="question" class="dinner-question">{{ question }}</p>
        <label for="dinner-dish">Название блюда</label>
        <input id="dinner-dish" ref="dishInput" v-model="dish" list="dinner-dishes" type="search" maxlength="500" placeholder="Например, стейк рибай на гриле" :disabled="!available || phase === 'recognizing'" required autocomplete="off" @input="editDish">
        <datalist id="dinner-dishes"><option v-for="node in DINNER_NODES" :key="node.id" :value="node.label" /></datalist>
        <p class="dinner-field-hint">Фотография не раскрывает состав блюда. Уточните название, прежде чем выбирать вино.</p>
        <label for="dinner-category">Можно выбрать общую категорию</label>
        <select id="dinner-category" ref="categoryInput" v-model="category" :disabled="!available || phase === 'recognizing'" @change="chooseCategory"><option value="">Выберите, если точное блюдо неизвестно</option><option v-for="node in DINNER_CATEGORIES" :key="node.id" :value="node.id">{{ node.label }}</option></select>
        <div class="dinner-preferences" lang="ru">
          <fieldset class="dinner-preference-row" aria-describedby="dinner-taste-hint">
            <legend>Вкус и соус</legend>
            <div class="dinner-choices">
              <button v-for="preset in tastePresets" :key="preset.label" class="dinner-choice" type="button" :aria-pressed="settings[preset.key] === preset.value" :disabled="!available" @click="toggleTaste(preset)"><AppIcon :name="preset.icon" /><span>{{ preset.label }}</span></button>
            </div>
            <p id="dinner-taste-hint" class="dinner-field-hint">Можно сочетать. Без выбора — как в рецепте. Нажмите ещё раз, чтобы снять выбор.</p>
          </fieldset>
        </div>
        <button class="button primary dinner-submit" type="submit" :disabled="!available || busy || !dish.trim()"><AppIcon name="taste" />{{ preview ? 'Подтвердить и подобрать вино' : 'Подобрать вино' }}</button>
        <p class="dinner-field-hint">Рецепт, соус и острота влияют на сочетание. Выбор можно изменить.</p>
      </form>
    </div>
    <div v-if="busy" class="dinner-progress"><span class="spinner" /><p>{{ progressMessage }}</p><button class="button secondary" type="button" @click="cancel">Отменить</button></div>
    <p v-if="error" class="dinner-error" role="alert">{{ error }}</p>
    <section v-if="phase === 'ready' || wines.length" ref="resultRegion" class="dinner-results" aria-label="Подобранные вина">
      <p class="step-label">К ВАШЕМУ СТОЛУ</p><h2 ref="resultHeading" tabindex="-1">Вино к вашему блюду</h2><p class="dinner-result-context">{{ selectedLabel }}</p>
      <p v-if="page?.status === 'no_results'" class="dinner-notice" role="status">Подтверждённых сочетаний с этими условиями пока нет. Попробуйте уточнить блюдо или изменить ограничения.</p>
      <p v-else-if="page?.needs_clarification && question" class="dinner-field-hint">{{ question }}</p>
      <div class="dinner-wines"><article v-for="wine in wines" :key="wine.wine_slug" class="dinner-wine">
        <div class="dinner-wine-top"><AppIcon name="taste" /><span>{{ wine.selection_source === 'curated' ? 'Подборка к блюду' : 'Ещё один вариант' }}</span></div>
        <p class="dinner-producer">{{ wine.producer }}</p><h3 tabindex="-1">{{ wine.name }}</h3>
        <p class="dinner-wine-facts">{{ labels[wine.facts.color] }} · {{ labels[wine.facts.sweetness] }} · {{ labels[wine.facts.wine_kind] }}<template v-if="wine.facts.alcohol_percent !== null"> · {{ wine.facts.alcohol_percent }}%</template></p>
        <p v-if="wine.facts.reported_grapes.length" class="dinner-grapes">{{ wine.facts.reported_grapes.join(', ') }}</p>
        <p class="dinner-reason">{{ wine.reason }}</p><a :href="wine.source_url" class="button secondary" :aria-label="`Карточка вина: ${wine.name} (откроется в новой вкладке)`" target="_blank" rel="noopener noreferrer">Карточка вина<AppIcon name="arrow-up-right" /></a>
      </article></div>
      <button v-if="page?.next_cursor" class="button secondary dinner-more" type="button" :aria-disabled="busy" @click="showMore">Показать ещё<AppIcon name="arrow" /></button>
      <p v-else-if="wines.length" class="dinner-field-hint dinner-end">Все подходящие варианты из текущей подборки показаны.</p>
      <p v-if="wines.length" class="dinner-field-hint dinner-end">Сочетания основаны на данных карточек и правилах подбора. Наличие и цены уточняйте отдельно.</p>
    </section>
  </section>
</template>

<style scoped>
.dinner-entry { display: grid; grid-template-columns: .9fr 1.1fr; border: 1px solid var(--line); border-radius: 24px; background: var(--paper); overflow: hidden; }
.dinner-photo-panel { position: relative; padding: 36px; text-align: center; background: var(--cream); display: flex; flex-direction: column; align-items: center; }
.dinner-photo-panel.dragging { outline: 3px dashed var(--accent); outline-offset: -10px; }
.dinner-drop-overlay { position: absolute; inset: 12px; z-index: 2; border-radius: 14px; background: var(--paper); color: var(--accent); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 18px; font-size: 20px; pointer-events: none; }
.dinner-drop-overlay .icon { width: 42px; height: 42px; }
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
.dinner-preferences { margin-top: 28px; }
.dinner-preference-row { min-width: 0; margin: 0 0 18px; padding: 0; border: 0; }
.dinner-preference-row legend { padding: 0; margin-bottom: 10px; font-size: 13px; font-weight: 600; }
.dinner-choices { display: grid; grid-template-columns: repeat(7,minmax(0,1fr)); gap: 6px; }
.dinner-choice { position: relative; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; gap: 8px; min-width: 0; min-height: 86px; padding: 12px 3px 9px; border: 1px solid var(--line); border-radius: 12px; background: var(--paper); color: var(--ink); font-size: 11px; line-height: 1.35; text-align: center; }
.dinner-choice span { max-width: 100%; hyphens: auto; overflow-wrap: break-word; }
.dinner-choice .icon { width: 25px; height: 25px; color: var(--accent); }
.dinner-choice[aria-pressed="true"] { border-color: var(--accent); background: var(--cream); box-shadow: inset 0 0 0 1px var(--accent); }
.dinner-choice[aria-pressed="true"]::after { content: ''; position: absolute; top: 5px; right: 6px; width: 4px; height: 7px; border-right: 2px solid var(--accent); border-bottom: 2px solid var(--accent); transform: rotate(45deg); }
@media (forced-colors: active) { .dinner-choice[aria-pressed="true"] { outline: 2px solid Highlight; outline-offset: -3px; } .dinner-choice[aria-pressed="true"]:focus-visible { outline: 2px solid CanvasText; outline-offset: 4px; } .dinner-choice[aria-pressed="true"]::after { border-color: Highlight; } }
@media (hover: hover) { .dinner-choice:hover:not(:disabled) { border-color: var(--accent); background: var(--cream); } }
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
@media(max-width: 1023px) { .dinner-entry { grid-template-columns: 1fr; } .dinner-photo-panel, .dinner-form { padding: 28px; } .dinner-wines { grid-template-columns: repeat(2,minmax(0,1fr)); } }
@media(max-width: 600px) { .dinner-choices { grid-template-columns: repeat(4,minmax(0,1fr)); } }
@media(max-width: 360px) { .dinner-choices { grid-template-columns: repeat(3,minmax(0,1fr)); } }
@media(max-width: 767px) { .dinner-entry { grid-template-columns: 1fr; border-radius: 20px; } .dinner-photo-panel, .dinner-form { padding: 24px; } .dinner-photo-placeholder { min-height: 140px; } .dinner-plate { width: 116px; height: 116px; } .dinner-photo-copy h2 { font-size: 30px; } .dinner-photo-copy h2 br { display: none; } .dinner-form h2 { font-size: 26px; } .dinner-form input, .dinner-form select { font-size: 16px; } .dinner-wines { grid-template-columns: 1fr; } .dinner-results>h2 { font-size: 30px; } .dinner-progress { flex-wrap: wrap; } .dinner-progress p { flex: 1; min-width: 160px; } .dinner-progress>.button { width: 100%; } .dinner-submit { font-size: 12px; padding-inline: 8px; } }
</style>
