<script setup lang="ts">
const title = 'Что за вино? — презентация проекта'
const description = 'Презентация проекта «Что за вино?» в форматах PowerPoint и PDF.'
const videoUnavailable = ref(true)
const videoSource = ref<string>()
onMounted(() => { videoSource.value = '/presentation/video.mp4' })

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
      <section class="presentation-video" aria-labelledby="video-title">
        <h2 id="video-title">Видео о проекте</h2>
        <div class="video-frame">
          <video
            v-show="!videoUnavailable"
            :src="videoSource"
            controls
            playsinline
            preload="metadata"
            aria-label="Видеопрезентация проекта «Что за вино?»"
            @error="videoUnavailable = true"
            @loadedmetadata="videoUnavailable = false"
          >
            <a href="/presentation/video.mp4">Открыть видеопрезентацию</a>
          </video>
          <div v-if="videoUnavailable" class="video-placeholder" role="status">
            <span class="video-symbol" aria-hidden="true">▶</span>
            <p>Видео появится после записи</p>
          </div>
        </div>
      </section>
      <nav class="presentation-resources" aria-label="Материалы проекта">
        <a class="presentation-file" href="https://github.com/s1mb1o/svoe-vino-lab-dev" target="_blank" rel="noopener noreferrer">
          <span class="file-format">КОД</span>
          <span class="file-title">GitHub</span>
          <span class="file-action">Открыть<AppIcon name="arrow-up-right" /></span>
        </a>
        <a class="presentation-file" href="https://drive.google.com/drive/folders/1YfZ9ghYz8yJpznCIEiqgKho64EB3vdHD" target="_blank" rel="noopener noreferrer">
          <span class="file-format">ФАЙЛЫ</span>
          <span class="file-title">Google Drive</span>
          <span class="file-action">Открыть<AppIcon name="arrow-up-right" /></span>
        </a>
      </nav>
      <NuxtLink to="/hackaton" class="presentation-file presentation-hackaton">
        <span class="file-format">ПРОЕКТ</span>
        <span class="file-title">Все приложения проекта</span>
        <span class="file-action">Открыть<AppIcon name="arrow-up-right" /></span>
      </NuxtLink>
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
.presentation-links, .presentation-resources { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: clamp(12px, 3vw, 24px); margin-top: 40px; }
.presentation-file { display: flex; flex-direction: column; align-items: flex-start; min-width: 0; padding: clamp(18px, 4vw, 32px); border: 1px solid var(--line); border-radius: 20px; text-align: left; transition: border-color .2s, background-color .2s; }
.presentation-file:hover { border-color: var(--accent); background: #fcf8ee; }
.presentation-hackaton { margin-top: clamp(12px, 3vw, 24px); }
.file-format { padding: 7px 10px; border-radius: 8px; background: #f8f2e8; color: var(--accent); font-size: 11px; font-weight: 700; letter-spacing: .06em; }
.file-title { margin-top: 26px; font-size: clamp(16px, 3vw, 23px); font-weight: 500; }
.file-action { display: flex; align-items: center; gap: 8px; margin-top: 22px; color: var(--accent); font-size: 13px; }
.file-action .icon { width: 17px; height: 17px; }
.presentation-video { margin-top: 40px; text-align: left; }
.presentation-video h2 { margin-bottom: 18px; font-size: clamp(24px, 4vw, 30px); }
.video-frame { overflow: hidden; aspect-ratio: 16 / 9; border: 1px solid var(--line); border-radius: 20px; background: #fcf8ee; }
.video-frame video { display: block; width: 100%; height: 100%; background: #211e1c; object-fit: contain; }
.video-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; width: 100%; height: 100%; padding: 20px; text-align: center; color: var(--muted); font-size: 14px; line-height: 1.5; }
.video-symbol { display: grid; place-items: center; width: 48px; height: 48px; padding-left: 3px; border-radius: 50%; background: #f3e6cf; color: var(--accent); font-size: 18px; }
@media (prefers-reduced-motion: reduce) { .presentation-file { transition: none; } }
</style>
