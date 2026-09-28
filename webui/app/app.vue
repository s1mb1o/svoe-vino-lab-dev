<script setup lang="ts">
import { hasAgeConfirmation } from '~/utils/age'

const ageChecked = ref(false)
const ageConfirmed = ref(false)
onMounted(() => {
  ageConfirmed.value = hasAgeConfirmation(localStorage)
  ageChecked.value = true
})
</script>

<template>
  <NuxtPwaManifest />
  <div v-if="!ageChecked" class="age-loading" aria-label="Проверяем подтверждение возраста" aria-busy="true"><span class="spinner" /></div>
  <AgeGate v-else-if="!ageConfirmed" @confirmed="ageConfirmed = true" />
  <div v-else class="site-shell">
    <a class="skip-link" href="#main-content">К поиску вина</a>
    <header class="site-header">
      <NuxtLink to="/" class="logo" aria-label="Свое Вино — поиск по фото"><img src="/reference/logo.svg" alt="Свое Вино" width="160" height="40"></NuxtLink>
      <span class="header-section"><AppIcon name="scan" />Сканер вина</span>
      <a class="portal-navigation" href="https://vino-svoe.ru/" target="_blank" rel="noopener noreferrer"><span>На портал «Свое Вино»</span><AppIcon name="arrow-up-right" /></a>
    </header>
    <NuxtPage />
    <footer class="site-footer">
      <div><span>Свое Вино · Поиск по фотографии</span><a href="https://vino-svoe.ru/" target="_blank" rel="noopener noreferrer">Откройте культуру российского вина<AppIcon name="arrow-up-right" /></a><span>18+</span></div>
      <p>Чрезмерное употребление алкоголя вредит вашему здоровью</p>
    </footer>
  </div>
</template>
