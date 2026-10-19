<script setup lang="ts">
import { SHELF_EXAMPLES, type BottleBox } from '#shared/shelf'
import { useDiary } from '~/composables/useDiary'
const scanner = useShelfScanner()
const { file, result, phase, error, selectedId, selectedBottle, selectedMatch, selectedWine: wine, portalUrl, busy, displayImage, exampleLoading } = scanner
// Chrome and Firefox cannot show a HEIC photo. The matcher result has a JPEG preview.
const photoFailed = ref(false)
watch(displayImage, () => { photoFailed.value = false })
const upload = ref<HTMLInputElement>()
const camera = ref<HTMLInputElement>()
const dialog = ref<HTMLDialogElement>()
const dialogHeading = ref<HTMLElement>()
const zoomed = ref(false)
const dragging = ref(false)
const activeExample = ref(0)
const shelfExample = computed(() => SHELF_EXAMPLES[activeExample.value] || SHELF_EXAMPLES[0]!)
let returnFocus: HTMLElement | null = null
let pendingOpener: HTMLElement | null = null

function choose(event: Event) { const input = event.target as HTMLInputElement; if (input.files?.length) { ownPhoto.value = true; void scanner.select([...input.files]) } input.value = '' }
function drop(event: DragEvent) { dragging.value = false; if (event.dataTransfer?.files.length) { ownPhoto.value = true; void scanner.select([...event.dataTransfer.files]) } }
function runExample() { ownPhoto.value = false; void scanner.example(shelfExample.value) }
// «Винный дневник» (plan 07): a bottle that the person opens on their own shelf photo goes to the
// history once per result. An example shelf is not the person's wine.
const diary = useDiary()
const ownPhoto = ref(false)
const recorded = new Set<string>()
watch(result, () => recorded.clear())
watch(selectedMatch, match => {
  if (!match || !ownPhoto.value || recorded.has(match.slug)) return
  recorded.add(match.slug)
  void diary.recordHistory(match.slug, 'shelf')
})
function openBottle(id: string, event: MouseEvent) {
  scanner.selectBottle(id)
  pendingOpener = selectedId.value === id && event.currentTarget instanceof HTMLElement ? event.currentTarget : null
}
function boxStyle(box: BottleBox) { return { left: `${box[0] * 100}%`, top: `${box[1] * 100}%`, width: `${(box[2] - box[0]) * 100}%`, height: `${(box[3] - box[1]) * 100}%` } }
function backdrop(event: MouseEvent) {
  if (event.target !== dialog.value) return
  const rect = dialog.value.getBoundingClientRect()
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) scanner.closeBottle()
}
watch(selectedId, async id => {
  const opener = pendingOpener
  pendingOpener = null
  await nextTick()
  if (selectedId.value !== id) return
  if (id && !dialog.value?.open) {
    returnFocus = opener?.isConnected ? opener : document.activeElement as HTMLElement | null
    dialog.value?.showModal()
    dialogHeading.value?.focus({ preventScroll: true })
  } else if (!id && dialog.value?.open) {
    dialog.value.close()
    if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true })
  }
})
function dialogClosed() { if (!dialog.value?.open) scanner.closeBottle() }
watch(file, () => { zoomed.value = false })
onBeforeUnmount(() => dialog.value?.close())
useShelfTools(scanner)
</script>

<template>
  <section class="shelf-scanner" aria-label="Поиск вина на фотографии полки">
    <input ref="upload" class="file-input" type="file" accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif" tabindex="-1" aria-label="Выбрать фотографию полки" @change="choose">
    <input ref="camera" class="file-input" type="file" accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif" capture="environment" tabindex="-1" aria-label="Сфотографировать винную полку" @change="choose">
    <div v-if="!file" class="shelf-upload" :class="{ dragging }" @dragover.prevent="dragging = true" @dragleave.prevent="dragging = false" @drop.prevent="drop">
      <div class="shelf-upload-copy"><p class="step-label">НЕСКОЛЬКО ВИН НА ОДНОМ ФОТО</p><h2>Вся полка.<br><span>Ваше вино.</span></h2><p>Снимите полку целиком. Мы выделим бутылки — останется нажать на ту, которая вас заинтересовала.</p><div class="upload-actions"><button class="button primary" :disabled="exampleLoading" @click="upload?.click()"><AppIcon name="upload" />Загрузить фото</button><button class="button secondary camera-action" :disabled="exampleLoading" @click="camera?.click()"><AppIcon name="camera" />Снять полку</button></div><p class="upload-hint">JPEG, PNG, WebP, HEIC · до 10 МБ<span class="desktop-drop-hint"><br>Можно перетащить фото сюда</span></p><button class="example-button" :disabled="exampleLoading" @click="runExample"><span v-if="exampleLoading" class="spinner" /><AppIcon v-else name="image" />{{ exampleLoading ? 'Загружаем пример…' : 'Попробовать этот пример' }}<AppIcon name="arrow" /></button></div>
      <div class="shelf-example-visual">
        <img :src="shelfExample.src" :alt="shelfExample.alt" width="2560" height="1928">
        <div class="shelf-example-picker" role="group" aria-label="Примеры фотографий полок">
          <button v-for="(item, index) in SHELF_EXAMPLES" :key="item.id" type="button" :aria-label="`Выбрать пример ${index + 1}`" :aria-pressed="activeExample === index" @click="activeExample = index"><img :src="item.src" alt=""><span>0{{ index + 1 }}</span></button>
        </div>
        <div class="shelf-example-caption"><AppIcon name="shelf" /><span>Пример {{ activeExample + 1 }} из {{ SHELF_EXAMPLES.length }} · затем выберите бутылку</span></div>
      </div>
    </div>
    <div v-else class="shelf-workspace">
      <div class="shelf-toolbar"><div><p class="step-label">ВАША ВИННАЯ ПОЛКА</p><h2>{{ phase === 'ready' ? result?.bottles.length ? 'Выберите бутылку на фото' : 'Бутылки не найдены' : 'Знакомимся с вашей полкой' }}</h2></div><span v-if="result?.bottles.length" class="shelf-count">{{ result.bottles.length }} в кадре</span><button v-if="phase === 'ready'" class="button secondary zoom-button" :aria-pressed="zoomed" @click="zoomed = !zoomed"><AppIcon name="search" />{{ zoomed ? 'Уместить' : 'Увеличить' }}</button><button class="icon-button" aria-label="Убрать фото полки" @click="scanner.reset()"><AppIcon name="close" /></button></div>
      <div class="shelf-viewport" :aria-busy="busy"><div class="shelf-frame" :class="{ 'is-zoomed': zoomed }"><img v-if="!photoFailed" class="shelf-photo" :src="displayImage" alt="Ваша фотография винной полки" :width="result?.image.width" :height="result?.image.height" @error="photoFailed = true"><p v-else class="preview-unavailable"><AppIcon name="image" />Браузер не может показать это фото, но мы всё равно его проверим.</p><template v-if="result"><img v-for="bottle in result.bottles" :key="`${bottle.id}-mask`" class="bottle-mask" :style="boxStyle(bottle.box)" :class="{ selected: selectedId === bottle.id }" :src="bottle.mask" alt="" aria-hidden="true"><button v-for="(bottle, index) in result.bottles" :key="bottle.id" class="bottle-hotspot" :style="boxStyle(bottle.box)" :aria-label="`Открыть вино: бутылка ${index + 1}`" aria-haspopup="dialog" @click="openBottle(bottle.id, $event)"><span>{{ index + 1 }}</span></button></template><div v-if="busy" class="shelf-loading"><span class="spinner" /><strong>Ищем бутылки и совпадения…</strong><p>Первый снимок может обрабатываться несколько минут.</p><button class="button secondary" @click="scanner.cancel()">Отменить</button></div></div></div>
      <div v-if="result?.bottles.length" class="shelf-selection-row"><span>Выбрать бутылку</span><div class="shelf-bottle-list" role="group" aria-label="Бутылки на полке"><button v-for="(bottle, index) in result.bottles" :key="bottle.id" :aria-label="`Бутылка ${index + 1}: открыть карточку`" aria-haspopup="dialog" @click="openBottle(bottle.id, $event)">{{ index + 1 }}</button></div></div>
      <p v-if="result?.truncated" class="shelf-notice">На полке много бутылок. Показываем {{ result.bottles.length }} выделенных областей. Снимите нужную часть ближе, чтобы рассмотреть остальные.</p>
      <p v-if="phase === 'ready' && !result?.bottles.length" class="shelf-notice">Попробуйте снять полку ближе и прямо, чтобы бутылки были видны целиком.</p>
      <div class="shelf-actions"><button class="button secondary" @click="upload?.click()"><AppIcon name="upload" />Другое фото</button><button class="button secondary" @click="camera?.click()"><AppIcon name="camera" />Снять ещё</button><button v-if="phase === 'error' || phase === 'selected'" class="button primary" @click="scanner.submit()">Повторить обработку</button></div>
    </div>
    <div v-if="error" class="inline-error" role="alert"><AppIcon name="info" /><span>{{ error }}</span></div>
    <div class="scanner-footnote"><p><AppIcon name="info" />Нажмите на выделенную бутылку, чтобы узнать о вине.</p><span>Фото передаётся сервису распознавания</span></div>
    <p class="shelf-attribution">Примеры предоставлены владельцем проекта.</p>

    <dialog ref="dialog" class="shelf-dialog" aria-labelledby="shelf-wine-heading" @cancel.prevent="scanner.closeBottle()" @click="backdrop" @close="dialogClosed">
      <div class="shelf-dialog-top"><p class="step-label">ВЫБРАННАЯ БУТЫЛКА {{ selectedId.replace('b', '') }}</p><span class="shelf-dialog-actions"><PinButton v-if="selectedMatch" :key="selectedMatch.slug" :slug="selectedMatch.slug" source="shelf" :wine-name="wine?.name" /><button class="icon-button" aria-label="Закрыть карточку вина" @click="scanner.closeBottle()"><AppIcon name="close" /></button></span></div>
      <div v-if="selectedBottle" class="shelf-wine-card">
        <div class="shelf-wine-image"><WineImage :src="wine?.image || result?.image.preview" :alt="wine?.name || 'Выбранная бутылка с полки'" /></div>
        <div class="shelf-wine-copy"><p v-if="selectedMatch" class="result-kicker">Лучшее совпадение · оценка {{ selectedMatch.score.toFixed(3) }}</p><h2 id="shelf-wine-heading" ref="dialogHeading" tabindex="-1">{{ wine?.name || 'Совпадение не найдено' }}</h2><p v-if="wine && (wine.producer || wine.region)" class="match-producer">{{ [wine.producer, wine.region].filter(Boolean).join(' · ') }}</p><p v-if="wine && (wine.color || wine.category)" class="match-kind">{{ [wine.color, wine.category.toLocaleLowerCase('ru')].filter(Boolean).join(' ') }}</p><p v-if="wine?.grapes.length" class="match-kind">Сорта: {{ wine.grapes.join(', ') }}</p><p v-if="!selectedMatch" class="shelf-dialog-status">Не удалось уверенно определить это вино. Снимите бутылку ближе или попробуйте другое фото.</p><a v-if="portalUrl" :href="portalUrl" class="button primary result-link" target="_blank" rel="noopener noreferrer">Подробнее на «Свое Вино»<AppIcon name="arrow-up-right" /></a></div>
      </div>
      <WineExperiences v-if="wine" :key="`${selectedId}-${wine.slug}`" :wine="wine" />
      <button class="text-button shelf-return" @click="scanner.closeBottle()"><AppIcon name="back" />Вернуться к полке</button>
    </dialog>
  </section>
</template>
