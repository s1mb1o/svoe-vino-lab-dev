<script setup lang="ts">
import { hasAgeConfirmation } from '~/utils/age'

const ageChecked = ref(false)
const ageConfirmed = ref(false)
const route = useRoute()
const isAndroidPage = computed(() => route.path.startsWith('/android'))
const isHackatonPage = computed(() => route.path === '/hackaton' || route.path === '/hackaton/')
const isIdeasPage = computed(() => route.path === '/ideas' || route.path === '/ideas/')
const isPresentationPage = computed(() => route.path === '/presentation' || route.path === '/presentation/')
const ageGateOpen = computed(() => !ageChecked.value || !ageConfirmed.value)
onMounted(() => {
  ageConfirmed.value = hasAgeConfirmation(localStorage)
  ageChecked.value = true
})
</script>

<template>
  <NuxtPwaManifest />
  <div class="site-shell" :class="{ 'presentation-shell': isPresentationPage }" :inert="ageGateOpen">
    <a class="skip-link" href="#main-content">К основному содержанию</a>
    <header v-if="!isPresentationPage" class="site-header">
      <NuxtLink to="/" class="logo" aria-label="Что за вино? — поиск по фото"><ProductBrand /></NuxtLink>
      <span class="header-section"><AppIcon :name="isIdeasPage ? 'book' : isAndroidPage ? 'android' : 'scan'" />{{ isIdeasPage ? 'Больше, чем фото' : isHackatonPage ? 'Все приложения' : isAndroidPage ? 'Android-приложение' : 'Сканер вина' }}</span>
      <div class="header-actions">
        <NuxtLink class="product-navigation" :to="isAndroidPage ? '/' : '/android'" :aria-label="isAndroidPage ? 'Открыть веб-сканер' : 'Открыть страницу Android-приложения'"><span>{{ isAndroidPage ? 'Веб-сканер' : 'Android' }}</span><AppIcon :name="isAndroidPage ? 'scan' : 'android'" /></NuxtLink>
        <ThemeSwitcher />
        <a class="portal-navigation" href="https://vino-svoe.ru/" target="_blank" rel="noopener noreferrer"><span>На портал «Свое Вино»</span><AppIcon name="arrow-up-right" /></a>
      </div>
    </header>
    <NuxtPage />
    <footer v-if="!isPresentationPage" class="site-footer">
      <div><span>Что за вино? · {{ isIdeasPage ? 'Больше, чем распознавание' : isHackatonPage ? 'WebApp · Android · Telegram' : isAndroidPage ? 'Приложение для Android' : 'Поиск по фотографии' }}</span><NuxtLink :to="isIdeasPage ? '/hackaton' : '/ideas'">{{ isIdeasPage ? 'Все приложения' : 'Идеи за пределами распознавания' }}<AppIcon name="arrow-up-right" /></NuxtLink><a href="https://vino-svoe.ru/" target="_blank" rel="noopener noreferrer">Откройте культуру российского вина<AppIcon name="arrow-up-right" /></a><span>18+</span></div>
      <p>Чрезмерное употребление алкоголя вредит вашему здоровью</p>
    </footer>
  </div>
  <AgeGate v-if="ageGateOpen" @confirmed="ageConfirmed = true" />
</template>
