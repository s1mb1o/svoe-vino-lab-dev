<script setup lang="ts">
const title = 'Что за вино? — презентация проекта'
const description = 'Презентация проекта «Что за вино?» в форматах PowerPoint и PDF.'

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description,
  ogType: 'website',
  ogUrl: 'https://chtozavino.ru/presentation',
  twitterTitle: title,
  twitterDescription: description,
})
useHead({ link: [{ rel: 'canonical', href: 'https://chtozavino.ru/presentation' }] })
</script>

<template>
  <main id="main-content" class="presentation-page">
    <NuxtLink to="/" class="presentation-brand" aria-label="Что за вино? — поиск по фото"><ProductBrand /></NuxtLink>
    <div class="presentation-content">
      <p class="presentation-kicker">ЧТО ЗА ВИНО?</p>
      <h1>Презентация проекта</h1>
      <p class="presentation-description">Выберите удобный формат</p>
      <div class="presentation-links">
        <a class="presentation-file" href="/presentations/chtozavino-presentation.pptx" download="chtozavino-presentation.pptx">
          <span class="file-format">PPTX</span>
          <span class="file-title">PowerPoint</span>
          <span class="file-action">Скачать<AppIcon name="download" /></span>
        </a>
        <a class="presentation-file" href="/presentations/chtozavino-presentation.pdf" target="_blank" rel="noopener noreferrer">
          <span class="file-format">PDF</span>
          <span class="file-title">PDF-версия</span>
          <span class="file-action">Открыть<AppIcon name="arrow-up-right" /></span>
        </a>
      </div>
    </div>
  </main>
</template>

<style scoped>
.presentation-page { min-height: 100dvh; padding: 32px clamp(20px, 5vw, 72px); display: flex; flex-direction: column; background: #fff; }
.presentation-brand { align-self: flex-start; }
.presentation-content { width: 100%; max-width: 640px; margin: auto; padding: 64px 0 100px; text-align: center; }
.presentation-kicker { color: var(--accent); font-size: 11px; font-weight: 600; letter-spacing: .18em; }
h1 { margin-top: 18px; font-size: clamp(32px, 5vw, 52px); line-height: 1.15; letter-spacing: -.035em; }
.presentation-description { margin-top: 18px; color: var(--muted); font-size: 15px; line-height: 1.6; }
.presentation-links { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: clamp(12px, 3vw, 24px); margin-top: 40px; }
.presentation-file { display: flex; flex-direction: column; align-items: flex-start; min-width: 0; padding: clamp(18px, 4vw, 32px); border: 1px solid var(--line); border-radius: 20px; text-align: left; transition: border-color .2s, background-color .2s; }
.presentation-file:hover { border-color: var(--accent); background: #fcf8ee; }
.file-format { padding: 7px 10px; border-radius: 8px; background: #f8f2e8; color: var(--accent); font-size: 11px; font-weight: 700; letter-spacing: .06em; }
.file-title { margin-top: 26px; font-size: clamp(16px, 3vw, 23px); font-weight: 500; }
.file-action { display: flex; align-items: center; gap: 8px; margin-top: 22px; color: var(--accent); font-size: 13px; }
.file-action .icon { width: 17px; height: 17px; }
@media (prefers-reduced-motion: reduce) { .presentation-file { transition: none; } }
</style>
