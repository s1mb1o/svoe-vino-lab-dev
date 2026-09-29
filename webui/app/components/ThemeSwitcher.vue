<script setup lang="ts">
import { THEME_STORAGE_KEY, type ThemePreference } from '#shared/theme'

const preference = ref<ThemePreference>('system')
const currentTheme = ref<'light' | 'dark' | null>(null)
const buttonLabel = computed(() => currentTheme.value === null
  ? 'Переключить цветовую тему'
  : currentTheme.value === 'dark'
    ? 'Тёмная тема. Включить светлую'
    : 'Светлая тема. Включить тёмную')
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
  currentTheme.value = dark ? 'dark' : 'light'
  document.documentElement.dataset.theme = currentTheme.value
  document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]').forEach(meta => {
    meta.content = dark ? '#211e1c' : '#7b3528'
  })
}

function toggleTheme() {
  preference.value = currentTheme.value === 'dark' ? 'light' : 'dark'
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
  <button type="button" class="theme-switcher" :aria-label="buttonLabel" :title="buttonLabel" @click="toggleTheme">
    <AppIcon name="sun" class="theme-icon-light" />
    <AppIcon name="moon" class="theme-icon-dark" />
  </button>
</template>
