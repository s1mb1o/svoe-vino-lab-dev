<script setup lang="ts">
// A large bottle image in a native modal dialog. `open()` takes the wine and the control that
// opened the dialog. The dialog gives focus back to that control when it closes.
import { wineImageUrl } from '#shared/catalog'

const dialog = ref<HTMLDialogElement>()
const heading = ref<HTMLElement>()
const headingId = useId()
const wine = ref<{ slug: string; name: string; producer?: string | null } | null>(null)
let opener: HTMLElement | null = null

async function open(value: { slug: string; name: string; producer?: string | null }, control?: HTMLElement | null) {
  opener = control || null
  wine.value = value
  await nextTick()
  if (!dialog.value?.open) dialog.value?.showModal()
  heading.value?.focus({ preventScroll: true })
}
function close() { dialog.value?.close() }
function closed() {
  wine.value = null
  if (opener?.isConnected) opener.focus({ preventScroll: true })
  opener = null
}
function backdrop(event: MouseEvent) {
  if (event.target !== dialog.value) return
  const rect = dialog.value.getBoundingClientRect()
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close()
}

onBeforeUnmount(() => dialog.value?.close())
defineExpose({ open })
</script>

<template>
  <dialog ref="dialog" class="wine-preview-dialog" :aria-labelledby="headingId" @cancel.prevent="close" @click="backdrop" @close="closed">
    <template v-if="wine">
      <div class="wine-preview-top">
        <div><p v-if="wine.producer" class="wine-preview-producer">{{ wine.producer }}</p><h2 :id="headingId" ref="heading" tabindex="-1">{{ wine.name }}</h2></div>
        <button class="icon-button" type="button" aria-label="Закрыть изображение бутылки" @click="close"><AppIcon name="close" /></button>
      </div>
      <div class="wine-preview-image"><WineImage :src="wineImageUrl(wine.slug, 1600)" :alt="wine.name" width="1600" height="1600" /></div>
    </template>
  </dialog>
</template>

<style scoped>
.wine-preview-dialog { position: fixed; inset: 0; width: min(640px, calc(100% - 32px)); max-height: calc(100dvh - 32px); margin: auto; padding: 22px; border: 1px solid var(--line); border-radius: 24px; background: var(--paper); color: var(--ink); overflow: auto; overscroll-behavior: contain; box-shadow: 0 25px 100px #180e1744; }
.wine-preview-dialog::backdrop { background: #1c1716b8; backdrop-filter: blur(5px); }
.wine-preview-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
.wine-preview-producer { color: var(--muted); font-size: 11px; margin-bottom: 6px; }
.wine-preview-top h2 { font-size: 24px; line-height: 1.3; overflow-wrap: anywhere; }
.wine-preview-top h2:focus { outline: none; }
.wine-preview-image { height: clamp(240px, calc(100dvh - 170px), 720px); padding: 16px; border-radius: 16px; background: var(--card); display: flex; align-items: center; justify-content: center; overflow: hidden; }
/* The same tile as the Dinner Lens card: `multiply` keeps the tile colour around a white image background. */
.wine-preview-image>img { width: 100%; height: 100%; object-fit: contain; mix-blend-mode: multiply; }
:global([data-theme='dark'] .wine-preview-image) { background: #e8e2da; }
:global(body:has(.wine-preview-dialog[open])) { overflow: hidden; }
@media(max-width: 767px) { .wine-preview-dialog { padding: 18px; border-radius: 20px; } .wine-preview-top h2 { font-size: 20px; } }
</style>
