<script setup lang="ts">
import { hasAgeConfirmation } from '~/utils/age'

const ageChecked = ref(false)
const ageConfirmed = ref(false)
const ageGateOpen = computed(() => !ageChecked.value || !ageConfirmed.value)
onMounted(() => {
  ageConfirmed.value = hasAgeConfirmation(localStorage)
  ageChecked.value = true
})
</script>

<template>
  <NuxtPwaManifest />
  <div class="site-shell" :inert="ageGateOpen">
    <a class="skip-link" href="#main-content">К поиску вина</a>
    <header class="site-header">
      <NuxtLink to="/" class="logo" aria-label="Что за вино? — поиск по фото"><ProductBrand /></NuxtLink>
      <span class="header-section"><AppIcon name="scan" />Сканер вина</span>
      <div class="header-actions">
        <ThemeSwitcher />
        <a class="portal-navigation" href="https://vino-svoe.ru/" target="_blank" rel="noopener noreferrer"><span>На портал «Свое Вино»</span><AppIcon name="arrow-up-right" /></a>
      </div>
    </header>
    <NuxtPage />
    <footer class="site-footer">
      <div><span>Что за вино? · Поиск по фотографии</span><a href="https://vino-svoe.ru/" target="_blank" rel="noopener noreferrer">Откройте культуру российского вина<AppIcon name="arrow-up-right" /></a><span>18+</span></div>
      <p>Чрезмерное употребление алкоголя вредит вашему здоровью</p>
    </footer>
  </div>
  <AgeGate v-if="ageGateOpen" @confirmed="ageConfirmed = true" />
</template>
