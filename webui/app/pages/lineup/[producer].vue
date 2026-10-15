<script setup lang="ts">
import { PRODUCT_LINE_MAPS, findLineProduct } from '#shared/product-line-map'

const route = useRoute()
const line = computed(() => PRODUCT_LINE_MAPS.find(item => item.producer.id === route.params.producer))
const title = computed(() => line.value ? `Карта линейки ${line.value.producer.name} — Что за вино?` : 'Карта производителя не найдена — Что за вино?')
const initialSlug = computed(() => typeof route.query.wine === 'string' ? route.query.wine : undefined)
const unknownSlug = computed(() => initialSlug.value && line.value && !findLineProduct(line.value, initialSlug.value))
useSeoMeta({ title: () => title.value, robots: 'noindex, nofollow, noarchive', description: () => line.value ? `${line.value.scope.label}. Путеводитель по линейкам производителя.` : 'Для этого производителя пока нет проверенной карты.' })
useHead(() => ({ link: [{ rel: 'canonical', href: `https://chtozavino.ru/lineup/${encodeURIComponent(String(route.params.producer))}` }] }))
</script>

<template>
  <main id="main-content" class="lineup-page">
    <template v-if="line">
    <header class="lineup-heading">
      <div><p class="step-label">ПУТЕВОДИТЕЛЬ ПО ПРОИЗВОДИТЕЛЮ</p><h1>Карта линейки {{ line.producer.name }}</h1><p>{{ line.scope.label }}. Выберите линейку, затем познакомьтесь с конкретным продуктом.</p></div>
      <NuxtLink to="/" class="button secondary">К сканеру<AppIcon name="arrow" /></NuxtLink>
    </header>
    <p v-if="initialSlug" class="lineup-context">{{ unknownSlug ? 'Вино по этой ссылке не найдено в карте. Вы можете изучить линейки производителя.' : 'Вино выбрано по ссылке, без распознавания.' }}</p>
    <ProductLineMap :key="initialSlug || 'overview'" :line="line" :initial-slug="initialSlug" :recognized="false" />
    </template>
    <section v-else class="lineup-heading"><div><h1>Карта производителя пока не подготовлена</h1><p>Выберите доступную карту.</p><NuxtLink v-for="item in PRODUCT_LINE_MAPS" :key="item.producer.id" :to="`/lineup/${item.producer.id}`" class="button secondary">{{ item.producer.name }}</NuxtLink></div></section>
  </main>
</template>

<style scoped>
.lineup-page { max-width: 1390px; width: calc(100% - 64px); margin: 36px auto; }
.lineup-heading { display: flex; justify-content: space-between; align-items: center; gap: 24px; margin-bottom: 24px; }
.lineup-heading h1 { font-size: clamp(28px, 3.3vw, 48px); line-height: 1.15; margin: 12px 0; }
.lineup-heading p:not(.step-label), .lineup-context { color: var(--muted); font-size: 14px; line-height: 1.5; }
.lineup-heading .button { flex-shrink: 0; width: auto; }
.lineup-context { margin: 0 0 16px; }
@media (max-width: 767px) {
  .lineup-page { width: calc(100% - 24px); margin: 24px auto; }
  .lineup-heading { align-items: start; flex-direction: column; gap: 8px; margin-bottom: 12px; }
  .lineup-heading h1 { margin: 8px 0; font-size: 28px; }
  .lineup-heading div>p:not(.step-label) { display: none; }
  .lineup-context { font-size: 12px; margin-bottom: 0; }
  .lineup-heading .button { width: auto; min-height: 36px; padding: 7px 12px; font-size: 12px; }
}
</style>
