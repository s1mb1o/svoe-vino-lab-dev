<script setup lang="ts">
import { isMaxAppPath } from '#shared/account'
import { hasAgeConfirmation } from '~/utils/age'
import { legalLinks, legalPaths } from '~/data/legal'

const ageChecked = ref(false)
const ageConfirmed = ref(false)
const route = useRoute()
const isAndroidPage = computed(() => route.path.startsWith('/android'))
const isIphonePage = computed(() => route.path.startsWith('/iphone'))
const isHackatonPage = computed(() => route.path === '/hackaton' || route.path === '/hackaton/')
const isIdeasPage = computed(() => route.path === '/ideas' || route.path === '/ideas/')
const isGamePage = computed(() => route.path === '/game' || route.path === '/game/')
const isCrocodilePage = computed(() => route.path === '/crocodile' || route.path === '/crocodile/')
const isPresentationPage = computed(() => route.path === '/presentation' || route.path === '/presentation/')
// A bot user reads the terms before the 18+ confirmation, so the legal pages skip the age gate.
const isLegalPage = computed(() => legalPaths.includes(route.path.replace(/\/$/, '')))
// The MAX mini app has its own small header and footer: its host serves no other site page (plan 05).
const isMaxApp = computed(() => isMaxAppPath(route.path))
const ageGateOpen = computed(() => !isLegalPage.value && (!ageChecked.value || !ageConfirmed.value))
// «Винный дневник»: the server decides from NUXT_ACCOUNT_ENDPOINT; the page makes no account call.
const accountEnabled = useState('account-enabled', () => import.meta.server && Boolean(String(useRuntimeConfig().accountEndpoint || '').trim()))
onMounted(() => {
  ageConfirmed.value = hasAgeConfirmation(localStorage)
  ageChecked.value = true
})
</script>

<template>
  <NuxtPwaManifest />
  <div class="site-shell" :class="{ 'presentation-shell': isPresentationPage }" :inert="ageGateOpen">
    <a class="skip-link" href="#main-content">К основному содержанию</a>
    <header v-if="isMaxApp" class="site-header">
      <span class="logo"><ProductBrand /></span>
      <span class="header-section"><AppIcon name="book" />Винный дневник</span>
      <div class="header-actions"><ThemeSwitcher /></div>
    </header>
    <header v-else-if="!isPresentationPage" class="site-header">
      <NuxtLink to="/" class="logo" aria-label="Что за вино? — поиск по фото"><ProductBrand /></NuxtLink>
      <span class="header-section"><AppIcon :name="(isCrocodilePage || isGamePage) ? 'game' : isIdeasPage ? 'book' : isLegalPage ? 'shield' : isAndroidPage ? 'android' : isIphonePage ? 'phone' : 'scan'" />{{ isCrocodilePage ? 'Винный крокодил' : isGamePage ? 'Wine&Dine Merge' : isIdeasPage ? 'Больше, чем фото' : isHackatonPage ? 'Все приложения' : isLegalPage ? 'Правовая информация' : isAndroidPage ? 'Android-приложение' : isIphonePage ? 'iPhone-приложение' : 'Сканер вина' }}</span>
      <div class="header-actions">
        <NuxtLink v-if="accountEnabled" class="product-navigation account-navigation" to="/account" aria-label="Винный дневник"><span>Дневник</span><AppIcon name="book" /></NuxtLink>
        <NuxtLink class="product-navigation" :to="(isAndroidPage || isIphonePage) ? '/' : '/android'" :aria-label="(isAndroidPage || isIphonePage) ? 'Открыть веб-сканер' : 'Открыть страницу Android-приложения'"><span>{{ (isAndroidPage || isIphonePage) ? 'Веб-сканер' : 'Android' }}</span><AppIcon :name="(isAndroidPage || isIphonePage) ? 'scan' : 'android'" /></NuxtLink>
        <ThemeSwitcher />
        <a class="portal-navigation" href="https://vino-svoe.ru/" target="_blank" rel="noopener noreferrer"><span>На портал «Свое Вино»</span><AppIcon name="arrow-up-right" /></a>
      </div>
    </header>
    <NuxtPage />
    <footer v-if="isMaxApp" class="site-footer">
      <div><span>Что за вино? · Винный дневник</span><a href="/privacy">Политика конфиденциальности</a><a href="/terms">Условия использования</a><span>18+</span></div>
      <p>Чрезмерное употребление алкоголя вредит вашему здоровью</p>
    </footer>
    <footer v-else-if="!isPresentationPage" class="site-footer">
      <nav class="legal-navigation" aria-label="Правовая информация"><NuxtLink v-for="link in legalLinks" :key="link.path" :to="link.path" :aria-current="route.path.replace(/\/$/, '') === link.path ? 'page' : undefined">{{ link.label }}</NuxtLink></nav>
      <div><span>Что за вино? · {{ isCrocodilePage ? 'Винный крокодил' : isGamePage ? 'Wine&Dine Merge' : isIdeasPage ? 'Больше, чем распознавание' : isHackatonPage ? 'WebApp · Android · Telegram' : isAndroidPage ? 'Приложение для Android' : isIphonePage ? 'Приложение для iPhone' : 'Поиск по фотографии' }}</span><NuxtLink :to="isIdeasPage ? '/' : '/ideas'">{{ isIdeasPage ? 'Веб-сканер' : 'Идеи за пределами распознавания' }}<AppIcon name="arrow-up-right" /></NuxtLink><NuxtLink :to="isIphonePage ? '/android' : '/iphone'">{{ isIphonePage ? 'Android' : 'iPhone' }}<AppIcon name="arrow-up-right" /></NuxtLink><a href="https://vino-svoe.ru/" target="_blank" rel="noopener noreferrer">Откройте культуру российского вина<AppIcon name="arrow-up-right" /></a><span>18+</span></div>
      <p>Чрезмерное употребление алкоголя вредит вашему здоровью</p>
    </footer>
  </div>
  <AgeGate v-if="ageGateOpen" @confirmed="ageConfirmed = true" />
</template>
