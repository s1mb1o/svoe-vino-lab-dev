<script setup lang="ts">
import { PRODUCT_LINE_INDEX } from '#shared/product-line-map'

const producers = PRODUCT_LINE_INDEX.producers
const title = 'Карты линеек производителей — Что за вино?'
const description = `Путеводители по линейкам ${producers.length} российских производителей вина: группы, ступени внутри линейки и бутылки.`
useSeoMeta({ title, description, ogType: 'website', ogTitle: title, ogDescription: description, ogUrl: 'https://chtozavino.ru/lineup', twitterTitle: title, twitterDescription: description })
useHead({ link: [{ rel: 'canonical', href: 'https://chtozavino.ru/lineup' }] })

function plural(count: number, one: string, few: string, many: string) {
  const last = count % 10
  const word = count % 100 >= 11 && count % 100 <= 14 ? many : last === 1 ? one : last >= 2 && last <= 4 ? few : many
  return `${count} ${word}`
}
const date = (value: string) => /^\d{4}-\d{2}-\d{2}$/.test(value) ? value.split('-').reverse().join('.') : value
const failedCovers = ref(new Set<string>())
function coverFailed(src: string) { failedCovers.value = new Set([...failedCovers.value, src]) }
// A cover can fail before hydration adds the error listener. Check the completed images on mount.
onMounted(() => {
  for (const image of document.querySelectorAll<HTMLImageElement>('img[data-cover]')) {
    if (image.complete && image.naturalWidth === 0 && image.dataset.cover) coverFailed(image.dataset.cover)
  }
})
</script>

<template>
  <main id="main-content" class="lineup-index">
    <header class="lineup-index-heading">
      <div>
        <p class="step-label">ПУТЕВОДИТЕЛИ ПО ПРОИЗВОДИТЕЛЯМ</p>
        <h1>Карты линеек производителей</h1>
        <p>{{ plural(producers.length, 'производитель', 'производителя', 'производителей') }}. На карте вина собраны по группам и ступеням внутри линейки. Выберите карту.</p>
      </div>
      <NuxtLink to="/" class="button secondary">К сканеру<AppIcon name="arrow" /></NuxtLink>
    </header>
    <ul class="lineup-index-grid" role="list">
      <li v-for="entry in producers" :key="entry.producer.id">
        <NuxtLink :to="`/lineup/${entry.producer.id}`" class="lineup-card" :data-producer-card="entry.producer.id">
          <span class="lineup-card-bottle" aria-hidden="true">
            <ProductLineImage v-if="entry.summary.cover && !failedCovers.has(entry.summary.cover.src)" :src="entry.summary.cover.src" :frame="entry.summary.cover.frame" :data-cover="entry.summary.cover.src" alt="" width="60" height="140" loading="lazy" decoding="async" draggable="false" @error="coverFailed(entry.summary.cover.src)" />
            <AppIcon v-else name="image" />
          </span>
          <span class="lineup-card-text">
            <strong>{{ entry.producer.name }}</strong>
            <span>{{ plural(entry.summary.products, 'позиция', 'позиции', 'позиций') }} · {{ plural(entry.summary.groups, 'группа', 'группы', 'групп') }}</span>
            <span class="lineup-card-date">Материалы на {{ date(entry.summary.as_of) }}</span>
          </span>
          <AppIcon name="arrow" />
        </NuxtLink>
      </li>
    </ul>
  </main>
</template>

<style scoped>
.lineup-index { max-width: 1390px; width: calc(100% - 64px); margin: 36px auto; }
.lineup-index-heading { display: flex; justify-content: space-between; align-items: center; gap: 24px; margin-bottom: 28px; }
.lineup-index-heading h1 { font-size: clamp(28px, 3.3vw, 48px); line-height: 1.15; margin: 12px 0; }
.lineup-index-heading p:not(.step-label) { max-width: 760px; color: var(--muted); font-size: 14px; line-height: 1.6; }
.lineup-index-heading .button { flex-shrink: 0; width: auto; }
.lineup-index-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr)); gap: 16px; margin: 0; padding: 0; list-style: none; }
.lineup-card { display: grid; grid-template-columns: 64px minmax(0, 1fr) 20px; gap: 16px; align-items: center; height: 100%; padding: 16px 18px; border: 1px solid var(--line); border-radius: 16px; color: var(--ink); background: var(--paper); text-decoration: none; }
.lineup-card:hover { border-color: color-mix(in srgb, var(--accent) 45%, var(--line)); }
.lineup-card:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.lineup-card-bottle { --plm-image-height: 140px; --plm-image-width: 60px; display: flex; align-items: flex-end; justify-content: center; height: 140px; color: var(--muted); }
.lineup-card-bottle > img { width: auto; max-width: 60px; height: 140px; object-fit: contain; object-position: bottom; }
.lineup-card-bottle .icon { width: 28px; height: 40px; opacity: .6; }
.lineup-card-text { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.lineup-card-text strong { font: 500 22px/1.25 'Playfair Display', Georgia, serif; overflow-wrap: anywhere; }
.lineup-card-text span { color: var(--muted); font-size: 13px; line-height: 1.45; }
.lineup-card-text .lineup-card-date { font-size: 12px; }
.lineup-card > .icon { width: 18px; height: 18px; color: var(--accent); }
@media (max-width: 767px) {
  .lineup-index { width: calc(100% - 32px); margin: 24px auto; }
  .lineup-index-heading { align-items: start; flex-direction: column; gap: 12px; margin-bottom: 20px; }
  .lineup-index-heading h1 { margin: 8px 0; font-size: 28px; }
  .lineup-card { grid-template-columns: 52px minmax(0, 1fr) 18px; gap: 12px; padding: 14px; }
  .lineup-card-bottle { --plm-image-height: 112px; --plm-image-width: 48px; height: 112px; }
  .lineup-card-bottle > img { max-width: 48px; height: 112px; }
  .lineup-card-text strong { font-size: 20px; }
}
</style>
