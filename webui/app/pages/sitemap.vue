<script setup lang="ts">
import { sitemapSections } from '~/data/sitemap'

const title = 'Карта сайта — Что за вино?'
const description = 'Все разделы «Что за вино?»: поиск вина по фото, полки и вина к блюду, карты линеек производителей, приложения для Android и iPhone, боты в Telegram и MAX, «Винный дневник», игры, идеи, презентация проекта и правовая информация.'
const canonical = 'https://chtozavino.ru/sitemap'
const sections = sitemapSections

useSeoMeta({
  title, description, ogType: 'website', ogTitle: title, ogDescription: description,
  ogUrl: canonical, twitterCard: 'summary', twitterTitle: title, twitterDescription: description,
})
useHead({
  link: [{ rel: 'canonical', href: canonical }],
  script: [{ type: 'application/ld+json', innerHTML: JSON.stringify({
    '@context': 'https://schema.org', '@type': 'CollectionPage',
    name: title, description, url: canonical, inLanguage: 'ru',
    isPartOf: { '@id': 'https://chtozavino.ru/#website' },
    hasPart: sections.flatMap(section => section.pages.map(item => ({
      '@type': 'WebPage', name: item.label, url: `https://chtozavino.ru${item.path}`,
    }))),
  }) }],
})
</script>

<template>
  <main id="main-content" class="sitemap-page">
    <header class="sitemap-heading">
      <p class="eyebrow"><span />НАВИГАЦИЯ ПО САЙТУ</p>
      <h1>Карта сайта</h1>
      <p>Найдите нужный раздел: от первого снимка до знакомства со всеми приложениями проекта.</p>
    </header>
    <nav aria-label="Разделы сайта">
      <section v-for="section in sections" :key="section.id" class="sitemap-section" :aria-labelledby="`sitemap-${section.id}`">
        <h2 :id="`sitemap-${section.id}`">{{ section.title }}</h2>
        <ul class="sitemap-grid">
          <li v-for="item in section.pages" :key="item.path">
            <NuxtLink :to="item.path" class="sitemap-card"><span class="sitemap-icon"><AppIcon :name="item.icon" /></span><div><h3>{{ item.label }}</h3><p>{{ item.description }}</p></div><AppIcon name="arrow" /></NuxtLink>
          </li>
        </ul>
      </section>
    </nav>
    <a class="xml-sitemap" href="/sitemap.xml"><AppIcon name="map" />XML-карта для поисковых систем<AppIcon name="arrow-up-right" /></a>
  </main>
</template>

<style scoped>
.sitemap-page { width: calc(100% - 80px); max-width: 1120px; margin: 0 auto; padding: 60px 0 24px; }
.sitemap-heading { max-width: 720px; margin-bottom: 52px; }
.sitemap-heading .eyebrow { color: var(--ink); }
.sitemap-heading h1 { margin: 18px 0; color: var(--ink); font-size: clamp(42px, 5vw, 64px); line-height: 1.12; letter-spacing: -.035em; }
.sitemap-heading>p:last-child { color: var(--ink); font-size: 16px; line-height: 1.75; }
.sitemap-section + .sitemap-section { margin-top: 42px; }
.sitemap-section h2 { margin: 0 0 18px; font-size: 32px; line-height: 1.2; }
.sitemap-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; list-style: none; margin: 0; padding: 0; }
.sitemap-card { display: grid; grid-template-columns: 46px minmax(0, 1fr) 18px; gap: 18px; align-items: center; min-height: 138px; height: 100%; padding: 25px; border: 1px solid var(--line); border-radius: 22px; background: var(--paper); }
.sitemap-card:hover { border-color: var(--accent); background: var(--cream); }
.sitemap-icon { display: grid; place-items: center; width: 46px; height: 46px; border-radius: 14px; background: var(--cream); color: var(--accent); }
.sitemap-card>.icon { width: 18px; height: 18px; color: var(--accent); }
.sitemap-card h3 { margin: 0 0 8px; font: 500 23px/1.3 'Playfair Display', Georgia, serif; }
.sitemap-card p { color: var(--ink); font-size: 13px; line-height: 1.7; }
.xml-sitemap { display: inline-flex; align-items: center; gap: 9px; min-height: 44px; margin-top: 36px; color: var(--accent); font-size: 12px; }
.xml-sitemap:hover { text-decoration: underline; text-underline-offset: 4px; }
.xml-sitemap .icon { width: 17px; height: 17px; }
@media (max-width: 1023px) {
  .sitemap-page { width: calc(100% - 48px); }
  .sitemap-card { padding: 22px; gap: 14px; }
}
@media (max-width: 767px) {
  .sitemap-page { width: calc(100% - 32px); padding-top: 36px; }
  .sitemap-heading { margin-bottom: 36px; }
  .sitemap-heading>p:last-child { font-size: 14px; }
  .sitemap-grid { grid-template-columns: 1fr; gap: 12px; }
  .sitemap-card { min-height: 124px; padding: 20px; grid-template-columns: 38px minmax(0, 1fr) 16px; gap: 12px; border-radius: 18px; }
  .sitemap-icon { width: 38px; height: 38px; border-radius: 12px; }
  .sitemap-card h3 { font-size: 21px; }
  .sitemap-card p { font-size: 12px; }
}
</style>
