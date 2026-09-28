<script setup lang="ts">
useHead({ title: 'Найти вино по фото — Свое Вино' })
const scanMode = ref<'bottle' | 'shelf'>('bottle')
let modeTools: AbortController | undefined
onMounted(() => {
  const context = (document as Document & { modelContext?: { registerTool: (tool: object, options: { signal: AbortSignal }) => void | Promise<void> } }).modelContext
  if (!context?.registerTool) return
  modeTools = new AbortController()
  const tool = { name: 'set_wine_scan_mode', description: 'Switch between single-bottle and whole-shelf photo search. Switching discards the previous mode photo, results, and pending requests.', inputSchema: { type: 'object', properties: { mode: { type: 'string', enum: ['bottle', 'shelf'] } }, required: ['mode'], additionalProperties: false }, annotations: { readOnlyHint: false }, async execute(input: unknown) {
    const value = input as { mode?: string }
    if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).some(k => k !== 'mode') || !['bottle', 'shelf'].includes(value.mode || '')) throw new Error('Choose bottle or shelf mode.')
    scanMode.value = value.mode as 'bottle' | 'shelf'; await nextTick(); return { mode: scanMode.value }
  } }
  try { Promise.resolve(context.registerTool(tool, { signal: modeTools.signal })).catch(() => console.warn('Could not register scan mode tool')) }
  catch { console.warn('Could not register scan mode tool') }
})
onBeforeUnmount(() => modeTools?.abort())
</script>

<template>
  <main id="main-content" class="scanner-page">
    <section class="hero">
      <p class="eyebrow"><span />ОТКРЫВАЙТЕ РОССИЙСКОЕ ВИНО</p>
      <h1>Найти вино <span>по фото</span></h1>
      <p class="hero-description">{{ scanMode === 'bottle' ? 'У каждой бутылки своя история. Начните с фотографии этикетки.' : 'Режим обработки полки временно недоступен.' }}</p>
    </section>
    <div class="scan-mode-switch" role="group" aria-label="Режим поиска вина"><button :aria-pressed="scanMode === 'bottle'" @click="scanMode = 'bottle'"><AppIcon name="scan" />Одна бутылка</button><button :aria-pressed="scanMode === 'shelf'" @click="scanMode = 'shelf'"><AppIcon name="shelf" />Вся полка</button></div>
    <PhotoScanner v-if="scanMode === 'bottle'" />
    <ShelfUnavailable v-else @choose-bottle="scanMode = 'bottle'" />
    <section v-if="scanMode === 'bottle'" class="photo-tips" aria-label="Как сделать хороший снимок">
      <div><span class="tip-number">01</span><p><strong>Этикетка целиком</strong><span>Снимайте бутылку спереди</span></p></div>
      <div><span class="tip-number">02</span><p><strong>Мягкий свет</strong><span>Без бликов и размытия</span></p></div>
      <div><span class="tip-number">03</span><p><strong>Одно вино в кадре</strong><span>Так проще найти совпадение</span></p></div>
    </section>
  </main>
</template>
