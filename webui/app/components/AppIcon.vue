<script setup lang="ts">
defineProps<{ name: string }>()
const paths: Record<string, string> = {
  shelf: 'M2 11h20 M2 21h20 M5 2h2v3l1 2v3H4V7l1-2Z M15 2h2v3l1 2v3h-4V7l1-2Z M5 13h2v2l1 2v3H4v-3l1-2Z M15 13h2v2l1 2v3h-4v-3l1-2Z',
  food: 'M4 3v6a3 3 0 0 0 6 0V3 M7 3v18 M18 21V3c-4 2-4 9 0 9',
  location: 'M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0 M15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  store: 'M3 9l2-6h14l2 6 M3 9v3h18V9H3 M5 12v9h14v-9 M9 21v-6h6v6',
  search: 'm21 21-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  scan: 'M8 3H5a2 2 0 0 0-2 2v3 M16 3h3a2 2 0 0 1 2 2v3 M21 16v3a2 2 0 0 1-2 2h-3 M8 21H5a2 2 0 0 1-2-2v-3 M3 12h18 M10 6h4v3l2 5v4H8v-4l2-5Z',
  camera: 'M4 7h4l2-3h4l2 3h4a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2 M16 13a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  upload: 'M12 16V3 M7 8l5-5 5 5 M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5',
  close: 'm6 6 12 12 M6 18 18 6',
  menu: 'M3 6h18 M3 12h18 M3 18h18',
  filter: 'M3 6h18 M3 18h18 M8 3v6 M16 15v6 M3 12h18',
  'arrow-up-right': 'M6 18 18 6 M6 6h12v12',
  arrow: 'M4 12h16 M14 6l6 6-6 6',
  back: 'M20 12H4 M10 6l-6 6 6 6',
  check: 'm5 12 4 4L19 6',
  image: 'M3 4h18v16H3Z m0 12 5-5 5 5 3-3 5 5 M15 8h.01',
  chevron: 'm6 9 6 6 6-6',
  info: 'M12 11v6 M12 7h.01 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
  book: 'M4 5a3 3 0 0 1 3-2h5v17H7a3 3 0 0 0-3 2Z M20 5a3 3 0 0 0-3-2h-5v17h5a3 3 0 0 1 3 2Z',
  story: 'M4 18h16 M6 15V8a6 6 0 0 1 12 0v7 M9 15V9a3 3 0 0 1 6 0v6',
  map: 'm3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Z M9 3v15 M15 6v15',
  plus: 'M12 5v14 M5 12h14',
  minus: 'M5 12h14',
  navigation: 'm12 3 7 18-7-4-7 4Z M12 17V9',
}
</script>
<template><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="paths[name] || paths.info" /></svg></template>
