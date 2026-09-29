<script setup lang="ts">
import { THEME_STORAGE_KEY, type ThemePreference } from '#shared/theme'

const preference = ref<ThemePreference>('system')
let systemTheme: MediaQueryList | undefined

function readPreference(): ThemePreference {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch { /* Use the system theme when storage is unavailable. */ }
  return 'system'
}

function applyTheme() {
  const dark = preference.value === 'dark' || (preference.value === 'system' && systemTheme?.matches)
  document.documentElement.dataset.theme = dark ? 'dark' : 'light'
  document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]').forEach(meta => {
    meta.content = dark ? '#211e1c' : '#7b3528'
  })
}

function changeTheme() {
  applyTheme()
  try { localStorage.setItem(THEME_STORAGE_KEY, preference.value) } catch { /* Keep the selection for this page. */ }
}

function syncPreference(event: StorageEvent) {
  if (event.key !== THEME_STORAGE_KEY && event.key !== null) return
  preference.value = readPreference()
  applyTheme()
}

onMounted(() => {
  systemTheme = window.matchMedia('(prefers-color-scheme: dark)')
  preference.value = readPreference()
  applyTheme()
  systemTheme.addEventListener('change', applyTheme)
  window.addEventListener('storage', syncPreference)
})

onBeforeUnmount(() => {
  systemTheme?.removeEventListener('change', applyTheme)
  window.removeEventListener('storage', syncPreference)
})
</script>

<template>
  <select v-model="preference" class="theme-switcher" aria-label="Цветовая тема" title="Цветовая тема: автоматически, светлая или тёмная" @change="changeTheme">
    <option value="system">Авто</option>
    <option value="light">Светлая</option>
    <option value="dark">Тёмная</option>
  </select>
</template>
