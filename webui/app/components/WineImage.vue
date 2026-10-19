<script setup lang="ts">
// A wine image with the placeholder of plan `docs/plans/06_wine-images.md`: a wine with no
// static image has no file, so an image that does not load shows a bottle silhouette.
// An empty `alt` marks a decorative image; its placeholder is hidden from screen readers.
const props = defineProps<{ src?: string | null; alt: string; width?: number | string; height?: number | string; loading?: 'lazy' | 'eager' }>()
const failed = ref(false)
watch(() => props.src, () => { failed.value = false })
</script>

<template>
  <img v-if="src && !failed" :src="src" :alt="alt" :width="width" :height="height" :loading="loading" decoding="async" referrerpolicy="no-referrer" @error="failed = true">
  <span v-else class="wine-image-placeholder" :role="alt ? 'img' : undefined" :aria-label="alt ? `${alt}: нет изображения` : undefined" :aria-hidden="alt ? undefined : 'true'">
    <svg viewBox="0 0 40 120" fill="currentColor" fill-rule="evenodd" aria-hidden="true" focusable="false"><path d="M15 2h10v7H15Z M16 9h8v23c0 6 12 10 12 22v58a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V54c0-12 12-16 12-22Z M9 66v26h22V66Z" /></svg>
  </span>
</template>

<style scoped>
.wine-image-placeholder { display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; min-height: inherit; color: var(--muted); }
.wine-image-placeholder svg { height: 78%; max-height: 220px; width: auto; opacity: .45; }
</style>
