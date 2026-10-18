<script setup lang="ts">
const props = defineProps<{ mode: 'bottle' | 'shelf' }>()
const { data: config } = await useFetch('/api/config', { key: 'portal-config' })
// Each mode has its own page. Switching discards the photo, results, and pending requests of the previous mode.
const modePaths = { bottle: '/', shelf: '/shelf' } as const
const chooseBottle = () => navigateTo(modePaths.bottle)
let modeTools: AbortController | undefined
onMounted(() => {
  const context = (document as Document & { modelContext?: { registerTool: (tool: object, options: { signal: AbortSignal }) => void | Promise<void> } }).modelContext
  if (!context?.registerTool) return
  modeTools = new AbortController()
  const tool = { name: 'set_wine_scan_mode', description: 'Switch between single-bottle and whole-shelf photo search. Switching discards the previous mode photo, results, and pending requests.', inputSchema: { type: 'object', properties: { mode: { type: 'string', enum: ['bottle', 'shelf'] } }, required: ['mode'], additionalProperties: false }, annotations: { readOnlyHint: false }, async execute(input: unknown) {
    const value = input as { mode?: string }
    if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).some(k => k !== 'mode') || !['bottle', 'shelf'].includes(value.mode || '')) throw new Error('Choose bottle or shelf mode.')
    const mode = value.mode as 'bottle' | 'shelf'
    if (mode !== props.mode) await navigateTo(modePaths[mode])
    return { mode }
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
      <p class="hero-description">{{ mode === 'bottle' ? 'У каждой бутылки своя история. Начните с фотографии этикетки.' : config?.shelfAvailable ? 'Снимите полку целиком. Мы найдём бутылки и покажем совпадения.' : 'Режим обработки полки временно недоступен.' }}</p>
    </section>
    <nav class="scan-mode-switch" aria-label="Режим поиска вина"><NuxtLink :to="modePaths.bottle"><AppIcon name="scan" />Одна бутылка</NuxtLink><NuxtLink :to="modePaths.shelf"><AppIcon name="shelf" />Вся полка</NuxtLink></nav>
    <PhotoScanner v-if="mode === 'bottle'" />
    <ShelfScanner v-else-if="config?.shelfAvailable" />
    <ShelfUnavailable v-else @choose-bottle="chooseBottle" />
    <section v-if="mode === 'bottle'" class="photo-tips" aria-label="Как сделать хороший снимок">
      <div><span class="tip-number">01</span><p><strong>Этикетка целиком</strong><span>Снимайте бутылку спереди</span></p></div>
      <div><span class="tip-number">02</span><p><strong>Мягкий свет</strong><span>Без бликов и размытия</span></p></div>
      <div><span class="tip-number">03</span><p><strong>Одно вино в кадре</strong><span>Так проще найти совпадение</span></p></div>
    </section>
  </main>
</template>
