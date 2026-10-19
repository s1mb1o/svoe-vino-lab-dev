<script setup lang="ts">
import { legalLinks, legalRevisionLabel } from '~/data/legal'

const props = defineProps<{
  path: string
  title: string
  heading: string
  description: string
  lead: string
  contents: { id: string; title: string }[]
}>()

const canonical = `https://chtozavino.ru${props.path}`
const related = legalLinks.filter(link => link.path !== props.path)

useSeoMeta({
  title: props.title, description: props.description, ogType: 'website', ogTitle: props.title, ogDescription: props.description,
  ogUrl: canonical, twitterCard: 'summary', twitterTitle: props.title, twitterDescription: props.description,
})
useHead({ link: [{ rel: 'canonical', href: canonical }] })
</script>

<template>
  <main id="main-content" class="legal-page">
    <header class="legal-heading">
      <p class="eyebrow"><span />ПРАВОВАЯ ИНФОРМАЦИЯ</p>
      <h1>{{ heading }}</h1>
      <p>{{ lead }}</p>
      <p class="legal-revision">Редакция от {{ legalRevisionLabel }}</p>
    </header>
    <nav class="legal-contents" aria-labelledby="legal-contents-title">
      <h2 id="legal-contents-title">Содержание</h2>
      <ol><li v-for="item in contents" :key="item.id"><a :href="`#${item.id}`">{{ item.title }}</a></li></ol>
    </nav>
    <div class="legal-body"><slot /></div>
    <nav class="legal-related" aria-label="Другие документы">
      <NuxtLink v-for="link in related" :key="link.path" :to="link.path">{{ link.label }}<AppIcon name="arrow" /></NuxtLink>
    </nav>
  </main>
</template>

<style>
.legal-page { width: calc(100% - 80px); max-width: 820px; margin: 0 auto; padding: 60px 0 24px; color: var(--ink); }
.legal-heading { margin-bottom: 36px; }
.legal-heading .eyebrow { color: var(--ink); }
.legal-heading h1 { margin: 18px 0; font-size: clamp(36px, 5vw, 56px); line-height: 1.12; letter-spacing: -.03em; overflow-wrap: anywhere; }
.legal-heading>p:not(.eyebrow) { color: var(--ink); font-size: 16px; line-height: 1.75; }
.legal-heading .legal-revision { margin-top: 12px; font-size: 13px; }
.legal-contents { margin-bottom: 40px; padding: 22px 26px; border: 1px solid var(--line); border-radius: 22px; background: var(--paper); }
.legal-contents h2 { margin: 0 0 10px; font-size: 22px; }
.legal-contents ol { margin: 0; padding-left: 22px; columns: 2; column-gap: 32px; }
.legal-contents li { break-inside: avoid; padding: 2px 0; font-size: 14px; line-height: 1.6; }
.legal-contents a, .legal-body a { color: var(--accent); text-decoration: underline; text-underline-offset: 3px; }
.legal-contents a:hover, .legal-body a:hover { color: var(--accent-hover); }
.legal-body section { scroll-margin-top: 24px; }
.legal-body section + section { margin-top: 40px; }
.legal-body section section + section { margin-top: 0; }
.legal-body h2 { margin: 0 0 14px; font-size: 30px; line-height: 1.25; }
.legal-body h3 { margin: 24px 0 10px; font-size: 18px; font-weight: 600; line-height: 1.4; }
.legal-body p, .legal-body li, .legal-body dd, .legal-body dt { font-size: 15px; line-height: 1.75; }
.legal-body p + p, .legal-body p + ul, .legal-body ul + p, .legal-body p + ol, .legal-body ol + p { margin-top: 12px; }
.legal-body p + dl, .legal-body dl + p, .legal-body ul + dl { margin-top: 14px; }
.legal-body ul, .legal-body ol { margin: 0; padding-left: 22px; }
.legal-body li + li { margin-top: 6px; }
.legal-body dl { display: grid; grid-template-columns: minmax(150px, max-content) minmax(0, 1fr); gap: 8px 20px; margin: 0; }
.legal-body dt { font-weight: 600; }
.legal-body dd { margin: 0; overflow-wrap: anywhere; }
.legal-body .legal-note { margin-top: 16px; padding: 16px 20px; border-left: 3px solid var(--accent); border-radius: 0 14px 14px 0; background: var(--cream); }
.legal-related { display: flex; flex-wrap: wrap; gap: 12px 28px; margin-top: 48px; padding-top: 22px; border-top: 1px solid var(--line); }
.legal-related a { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; color: var(--accent); font-size: 14px; }
.legal-related a:hover { text-decoration: underline; text-underline-offset: 4px; }
.legal-related .icon { width: 16px; height: 16px; }
@media (max-width: 1023px) {
  .legal-page { width: calc(100% - 48px); }
}
@media (max-width: 767px) {
  .legal-page { width: calc(100% - 32px); padding-top: 36px; }
  .legal-heading>p:not(.eyebrow) { font-size: 14px; }
  .legal-contents { padding: 18px 20px; border-radius: 18px; }
  .legal-contents ol { columns: 1; }
  .legal-body h2 { font-size: 25px; }
  .legal-body p, .legal-body li, .legal-body dd, .legal-body dt { font-size: 14px; }
  .legal-body dl { grid-template-columns: 1fr; gap: 2px; }
  .legal-body dd + dt { margin-top: 10px; }
}
</style>
