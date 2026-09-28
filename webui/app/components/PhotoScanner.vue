<script setup lang="ts">
import { MOCK_SLUG } from '#shared/catalog'
const { data: config, error: configError, refresh } = await useFetch('/api/config', { key: 'portal-config' })
const apiUnavailable = computed(() => config.value?.apiAvailable === false)
const mode = computed(() => config.value?.apiAvailable ? config.value.predictionMode : undefined)
const scanner = useWineScanner(mode)
const { file, preview, phase, error, slug, wine, mock, busy, exampleLoading, portalUrl } = scanner
const fileInput = ref<HTMLInputElement>()
const cameraInput = ref<HTMLInputElement>()
const resultHeading = ref<HTMLElement>()
const resultPanel = ref<HTMLElement>()
const dragging = ref(false)
const hasResult = computed(() => phase.value === 'matched')
const demoBottle = `/wines/${MOCK_SLUG}.webp`

function selected(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.length) void scanner.select([...input.files])
  input.value = ''
}
function dropped(event: DragEvent) {
  dragging.value = false
  if (mode.value && event.dataTransfer?.files.length) void scanner.select([...event.dataTransfer.files])
}
watch(phase, async state => {
  if (state !== 'matched') return
  await nextTick()
  resultHeading.value?.focus({ preventScroll: true })
  if (window.matchMedia('(max-width: 767px)').matches) resultPanel.value?.scrollIntoView({ block: 'start', behavior: 'auto' })
})
useScannerTools(scanner)
</script>

<template>
  <section class="scanner-section" aria-label="Поиск вина по фотографии">
    <div v-if="configError || apiUnavailable" class="service-error" role="alert">
      <AppIcon name="info" /><span>Сервис поиска временно недоступен.</span>
      <button class="text-button" @click="refresh()">Повторить подключение</button>
    </div>
    <div class="scanner-workspace" :class="{ 'with-result': hasResult }">
      <section class="upload-panel" :class="{ dragging }" @dragover.prevent="dragging = true" @dragleave.prevent="dragging = false" @drop.prevent="dropped">
        <div class="panel-heading"><span class="step-label">01 / ВАША ФОТОГРАФИЯ</span><span v-if="file" class="file-size">{{ (file.size / 1024 / 1024).toFixed(2) }} МБ</span><span v-else-if="mode === 'mock'" class="demo-badge">ДЕМО</span></div>
        <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" class="file-input" tabindex="-1" aria-label="Выбрать фотографию этикетки" :disabled="!mode" @change="selected">
        <input ref="cameraInput" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" class="file-input" tabindex="-1" aria-label="Сфотографировать этикетку" :disabled="!mode" @change="selected">

        <template v-if="!file">
          <div class="upload-visual" aria-hidden="true"><div class="camera-symbol"><AppIcon name="camera" /></div><span class="frame-corner corner-tl" /><span class="frame-corner corner-tr" /><span class="frame-corner corner-bl" /><span class="frame-corner corner-br" /></div>
          <h2>Всего один снимок</h2>
          <p class="upload-copy">Загрузите фото этикетки.<br>Поиск начнётся автоматически.</p>
          <div class="upload-actions">
            <button class="button primary" :disabled="!mode || exampleLoading" @click="fileInput?.click()"><AppIcon name="upload" />Загрузить фото</button>
            <button class="button secondary camera-action" :disabled="!mode || exampleLoading" @click="cameraInput?.click()"><AppIcon name="camera" />Сделать фото</button>
          </div>
          <p class="upload-hint"><span class="desktop-drop-hint">Или перетащите файл сюда<br></span>JPEG, PNG, WebP · до 10 МБ</p>
        </template>
        <template v-else>
          <div class="photo-preview"><img :src="preview" alt="Ваша фотография этикетки"><div v-if="busy" class="scan-overlay" aria-hidden="true"><span /></div></div>
          <div class="photo-caption"><span>{{ file.name }}</span><button class="icon-button" aria-label="Убрать фото и начать заново" @click="scanner.reset()"><AppIcon name="close" /></button></div>
          <div v-if="busy" class="upload-progress" role="status"><span class="spinner" /><span>{{ phase === 'resolving' ? 'Открываем карточку вина…' : 'Ищем вино по этикетке…' }}</span><button class="text-button" @click="scanner.cancel()">Отменить</button></div>
          <div v-else class="upload-actions selected-actions"><button class="button secondary" @click="fileInput?.click()"><AppIcon name="upload" />Другое фото</button><button v-if="phase === 'error' || phase === 'selected'" class="button primary" @click="scanner.submit()">{{ phase === 'error' ? 'Повторить поиск' : 'Найти вино' }}</button><button v-else class="text-button" @click="cameraInput?.click()"><AppIcon name="camera" />Сделать фото</button></div>
        </template>
        <div v-if="error" class="inline-error" role="alert"><AppIcon name="info" /><span>{{ error }}</span></div>
        <button v-if="!file && mode === 'mock'" class="example-button" :disabled="exampleLoading" @click="scanner.example()"><span v-if="exampleLoading" class="spinner" /><AppIcon v-else name="image" />{{ exampleLoading ? 'Загружаем пример…' : 'Попробовать на примере' }}<AppIcon name="arrow" /></button>
      </section>

      <section ref="resultPanel" class="match-panel" :class="{ 'is-empty': !file && !hasResult, 'is-loading': busy }" aria-label="Результат поиска" :aria-busy="busy">
        <div class="panel-heading"><span class="step-label">02 / ВАШЕ ВИНО</span><span v-if="hasResult && !mock" class="match-badge"><AppIcon name="check" />Совпадение найдено</span><span v-else-if="hasResult && mock" class="demo-badge">ДЕМО</span></div>
        <div class="result-announcement" role="status" aria-live="polite" aria-atomic="true"><span class="sr-only">{{ hasResult ? `${mock ? 'Демонстрационный результат' : 'Лучшее совпадение'}: ${wine?.name || slug}` : busy ? 'Поиск вина выполняется' : '' }}</span></div>
        <template v-if="hasResult && wine">
          <div class="match-bottle"><img :src="wine.image" :alt="wine.name" width="300" height="300"></div>
          <div class="match-copy"><p class="result-kicker">{{ mock ? 'Демонстрационный результат' : 'Лучшее совпадение' }}</p><h2 ref="resultHeading" tabindex="-1">{{ wine.name }}</h2><p class="match-producer">{{ wine.producer }}<span v-if="wine.region"> · {{ wine.region }}</span></p><p class="match-kind">{{ wine.color }} {{ wine.category.toLocaleLowerCase('ru') }}</p><a :href="portalUrl" class="button primary result-link" target="_blank" rel="noopener noreferrer">Подробнее на «Свое Вино»<AppIcon name="arrow-up-right" /></a><p v-if="mock" class="result-disclaimer">Пример карточки. Это не распознавание вашего фото.</p></div>
        </template>
        <div v-else-if="hasResult" class="missing-result"><div class="result-symbol"><AppIcon name="check" /></div><p class="result-kicker">Результат поиска</p><h2 ref="resultHeading" tabindex="-1">Вино найдено.<br>Узнайте о нём больше.</h2><p>Фото бутылки и описание пока недоступны. Карточку можно открыть на основном портале.</p><code>{{ slug }}</code><a :href="portalUrl" class="button primary result-link" target="_blank" rel="noopener noreferrer">Открыть на «Свое Вино»<AppIcon name="arrow-up-right" /></a><p v-if="mock" class="result-disclaimer">Демонстрационный результат.</p></div>
        <div v-else-if="busy" class="waiting-result"><div class="bottle-silhouette" aria-hidden="true"><img :src="demoBottle" alt="" width="230" height="300"></div><span class="spinner" /><h2>Знакомимся с вашим вином</h2><p>Проверяем этикетку и ищем<br>подходящую карточку.</p></div>
        <div v-else class="empty-result"><div class="bottle-stage" aria-hidden="true"><div class="bottle-orbit" /><img :src="demoBottle" alt="" width="230" height="300"><span class="bottle-caption">СВОЯ ИСТОРИЯ В КАЖДОЙ БУТЫЛКЕ</span></div><h2>Здесь появится ваше вино</h2><p>Название, фото бутылки и ссылка<br>на карточку «Свое Вино».</p></div>
      </section>
    </div>
    <div class="scanner-footnote"><p><AppIcon name="info" />{{ mode === 'mock' ? 'Деморежим: любое фото покажет одну примерную карточку.' : 'Поиск начинается автоматически после выбора фотографии.' }}</p><span>Фото не сохраняется</span></div>
    <WineExperiences v-if="hasResult && wine" :key="slug" :wine="wine" />
  </section>
</template>
