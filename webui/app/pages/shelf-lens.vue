<script setup lang="ts">
import { SHELF_LENS_ANDROID_RELEASE, SHELF_LENS_APK_URL } from '#shared/shelf-lens-android'
const title = 'Shelf Lens — винная полка с новым взглядом | Что за вино?'
const description = 'Снимайте винную полку на телефон. Shelf Lens распознаёт бутылки, показывает рейтинг «Своё Вино» в дополненной реальности и собирает планограмму.'
const canonical = 'https://chtozavino.ru/shelf-lens'
useSeoMeta({ title, description, ogTitle: title, ogDescription: description, ogType: 'website', ogUrl: canonical, ogImage: `${canonical}/ar-rating.jpg`, twitterTitle: title, twitterDescription: description })
useHead({ link: [{ rel: 'canonical', href: canonical }] })

const chapters = {
  scan: { image: '/shelf-lens/scanning.jpg', label: '01 · Сканирование полки', alt: 'Кадр приложения: бутылки на полке выделены рамками', time: 12 },
  rating: { image: '/shelf-lens/ar-rating.jpg', label: '02 · Рейтинг в дополненной реальности', alt: 'Распознанные бутылки с зелёными рамками и звёздами рейтинга поверх изображения', time: 36 },
  list: { image: '/shelf-lens/wine-list.jpg', label: '03 · Найденные вина', alt: 'Список найденных вин с названиями, рейтингами и числом бутылок на полке', time: 84 },
}
const activeChapter = ref<keyof typeof chapters>('scan')
const chapter = computed(() => chapters[activeChapter.value])
const heroVideo = ref<HTMLVideoElement>()
const fullVideo = ref<HTMLVideoElement>()
const videoDialog = ref<HTMLDialogElement>()
const planDialog = ref<HTMLDialogElement>()
const heroPaused = ref(true)
const dialogOpen = ref(false)
let opener: HTMLElement | null = null
let previousOverflow = ''
let requestedTime = 0
let userPaused = false
let heroInView = false
let observer: IntersectionObserver | undefined
let reducedMotion: MediaQueryList | undefined

function syncHero() {
  const video = heroVideo.value
  if (!video) return
  if (userPaused || !heroInView || document.hidden || dialogOpen.value) video.pause()
  else void video.play().catch(() => { heroPaused.value = true })
}
function toggleMotion() {
  userPaused = !heroVideo.value?.paused
  syncHero()
}
function motionChanged(event: MediaQueryListEvent) {
  userPaused = event.matches
  syncHero()
}
function openDialog(dialog: HTMLDialogElement | undefined, event: Event) {
  if (!dialog || dialogOpen.value) return false
  opener = event.currentTarget instanceof HTMLElement ? event.currentTarget : null
  previousOverflow = document.body.style.overflow
  dialog.showModal()
  dialogOpen.value = true
  document.body.style.overflow = 'hidden'
  syncHero()
  return true
}
function seekVideo(seconds: number) {
  requestedTime = seconds
  if (fullVideo.value && fullVideo.value.readyState >= 1) fullVideo.value.currentTime = seconds
  void fullVideo.value?.play().catch(() => {})
}
function applyRequestedTime() {
  if (fullVideo.value) fullVideo.value.currentTime = requestedTime
}
function openVideo(seconds: number, event: Event) {
  if (openDialog(videoDialog.value, event)) seekVideo(seconds)
}
function openPlan(event: Event) {
  openDialog(planDialog.value, event)
}
function closeDialog() {
  fullVideo.value?.pause()
  document.body.style.overflow = previousOverflow
  dialogOpen.value = false
  syncHero()
  if (opener?.isConnected) opener.focus({ preventScroll: true })
  opener = null
}
function closeOnBackdrop(event: MouseEvent) {
  const dialog = event.currentTarget as HTMLDialogElement
  if (event.target !== dialog) return
  const bounds = dialog.getBoundingClientRect()
  if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close()
}
onMounted(() => {
  reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
  userPaused = reducedMotion.matches
  reducedMotion.addEventListener('change', motionChanged)
  document.addEventListener('visibilitychange', syncHero)
  observer = new IntersectionObserver(([entry]) => {
    heroInView = Boolean(entry?.isIntersecting)
    syncHero()
  }, { threshold: 0.1 })
  if (heroVideo.value) observer.observe(heroVideo.value)
})
onBeforeUnmount(() => {
  observer?.disconnect()
  reducedMotion?.removeEventListener('change', motionChanged)
  document.removeEventListener('visibilitychange', syncHero)
  heroVideo.value?.pause()
  fullVideo.value?.pause()
  if (dialogOpen.value) document.body.style.overflow = previousOverflow
  opener = null
})
</script>

<template>
<main id="main-content" class="shelf-lens-page">
<nav class="sl-section-nav sl-wrap" aria-label="Разделы Shelf Lens"><span>Shelf Lens</span><a href="#demo">В действии</a><a href="#how">Как работает</a><a href="#planogram">Для бизнеса</a><a href="#next">Что дальше</a></nav>

    <section class="sl-hero sl-wrap" aria-labelledby="hero-title">
      <div class="sl-hero-copy">
        <p class="sl-eyebrow"><span class="sl-tiny-spark" aria-hidden="true">✳</span> НОВЫЙ ВЗГЛЯД НА ВЫБОР ВИНА</p>
        <h1 id="hero-title">Винная полка.<br>С новым<br><em>взглядом.</em></h1>
        <p class="sl-hero-description">Снимайте полку на телефон. Shelf Lens узнаёт вино, показывает рейтинг прямо в кадре и собирает цифровую карту выкладки.</p>
        <div class="sl-hero-actions"><a class="sl-button sl-button-primary" :href="SHELF_LENS_APK_URL" :download="SHELF_LENS_ANDROID_RELEASE.apkFileName" data-testid="shelf-lens-download">Скачать для Android <span aria-hidden="true">↓</span></a><button class="sl-text-link" @click="openVideo(0, $event)"><span class="sl-play-small" aria-hidden="true">▶</span> Смотреть демо</button></div>
        <div class="sl-hero-note"><span class="sl-android-mark" aria-hidden="true">◉</span><span>Android {{ SHELF_LENS_ANDROID_RELEASE.minAndroid }}+ <span class="sl-note-dot">·</span> Тестовая версия {{ SHELF_LENS_ANDROID_RELEASE.version }} <span class="sl-note-dot">·</span> APK {{ SHELF_LENS_ANDROID_RELEASE.apkDisplaySize }}</span></div>
      </div>
      <div class="sl-hero-stage" aria-label="Запись работы Shelf Lens: распознанные бутылки и рейтинги на полке">
        <span class="sl-stage-grid" aria-hidden="true"></span>
        <div class="sl-stage-top"><span class="sl-status-dot"></span> ЗАПИСЬ ПРИЛОЖЕНИЯ <span>01 / AR</span></div>
        <div class="sl-stage-lettering" aria-hidden="true">see<br>more.</div>
        <div class="sl-phone sl-hero-phone">
          <video id="hero-video" ref="heroVideo" @play="heroPaused = false" @pause="heroPaused = true" muted loop playsinline preload="metadata" poster="/shelf-lens/ar-rating.jpg" aria-label="Короткий фрагмент сканирования винной полки"><source :src="'/shelf-lens-video/hero-loop.mp4'" type="video/mp4"></video>
        </div>
        <div class="sl-floating-rating"><span class="sl-float-icon" aria-hidden="true">✦</span><div><small>РЕЙТИНГ В ПОЛЕ ЗРЕНИЯ</small><span class="sl-rating-stars" aria-label="Пять звёзд">★★★★★</span><p>Из каталога «Своё Вино»</p></div></div>
        <div class="sl-floating-reid"><span class="sl-reid-icon" aria-hidden="true">⌁</span><div><strong>Камера движется.<br>Карта остаётся.</strong><span>Реидентификация бутылок</span></div></div>
        <button class="sl-motion-toggle" @click="toggleMotion" :aria-label="heroPaused ? 'Воспроизвести фоновое видео' : 'Приостановить фоновое видео'" :title="heroPaused ? 'Воспроизвести видео' : 'Приостановить видео'"><span aria-hidden="true">{{ heroPaused ? '▶' : 'Ⅱ' }}</span></button>
        <span class="sl-stage-bottom">SHELF LENS <span>ВИДЕТЬ. УЗНАВАТЬ. ПОМНИТЬ.</span></span>
      </div>
    </section>

    <div class="sl-proof-strip sl-wrap" aria-label="Основные возможности">
      <div><span class="sl-strip-number">01</span><p><strong>Вся полка в движении</strong><span>Снимайте с разных ракурсов</span></p></div>
      <div><span class="sl-strip-number">02</span><p><strong>Рейтинг поверх реальности</strong><span>Звёзды рядом с бутылкой</span></p></div>
      <div><span class="sl-strip-number">03</span><p><strong>От видео к планограмме</strong><span>Цифровая схема выкладки</span></p></div>
    </div>

    <section class="sl-demo-section sl-wrap sl-section" id="demo" aria-labelledby="demo-title">
      <div class="sl-section-heading"><div><p class="sl-eyebrow">В ДЕЙСТВИИ</p><h2 id="demo-title">Камера видит полку.<br><em>Вы — больше.</em></h2></div><p>Реальная запись с телефона.<br>От первого кадра до готовой планограммы.</p></div>
      <div class="sl-demo-layout">
        <div class="sl-demo-screen">
          <div class="sl-demo-screen-label"><span class="sl-status-dot"></span><span id="demo-label">{{ chapter.label }}</span></div>
          <img id="demo-image" :src="chapter.image" :alt="chapter.alt" loading="lazy" width="540" height="960">
          <button class="sl-demo-play" @click="openVideo(chapter.time, $event)" :aria-label="`Смотреть видео: ${chapter.label.slice(5)}`"><span aria-hidden="true">▶</span></button>
          <span class="sl-demo-duration">2:12 <span>ПОЛНАЯ ДЕМОНСТРАЦИЯ</span></span>
        </div>
        <div class="sl-demo-chapters" role="group" aria-label="Этапы демонстрации">
          <button class="sl-chapter" :class="{ 'sl-active': activeChapter === 'scan' }" :aria-pressed="activeChapter === 'scan'" @click="activeChapter = 'scan'"><span class="sl-chapter-time">00:12</span><span class="sl-chapter-body"><strong>Проведите камерой вдоль полки</strong><span>Бутылки попадают на карту. Поворачивайте и смещайте телефон, возвращайтесь к уже снятому участку.</span></span><span class="sl-chapter-arrow" aria-hidden="true">↗</span></button>
          <button class="sl-chapter" :class="{ 'sl-active': activeChapter === 'rating' }" :aria-pressed="activeChapter === 'rating'" @click="activeChapter = 'rating'"><span class="sl-chapter-time">00:36</span><span class="sl-chapter-body"><strong>Увидьте рейтинг прямо в кадре</strong><span>Распознанные бутылки выделяются зелёным. Звёзды из «Своё Вино» появляются поверх изображения.</span></span><span class="sl-chapter-arrow" aria-hidden="true">↗</span></button>
          <button class="sl-chapter" :class="{ 'sl-active': activeChapter === 'list' }" :aria-pressed="activeChapter === 'list'" @click="activeChapter = 'list'"><span class="sl-chapter-time">01:24</span><span class="sl-chapter-body"><strong>Откройте найденные вина</strong><span>Название, производитель, рейтинг и число бутылок. Фильтруйте список и переходите в каталог.</span></span><span class="sl-chapter-arrow" aria-hidden="true">↗</span></button>
          <div class="sl-demo-caption"><span aria-hidden="true">↳</span><p>В записи приложение называется «Полка вина».<br>Его новое имя — <strong>Shelf Lens</strong>.</p></div>
        </div>
      </div>
      <div class="sl-state-legend"><span><i class="sl-legend-grey"></i> Бутылка найдена</span><span><i class="sl-legend-yellow"></i> Ожидает распознавания</span><span><i class="sl-legend-green"></i> Вино распознано</span><span class="sl-legend-note">Рейтинг отображается, если он есть в каталоге</span></div>
    </section>

    <section class="sl-how-section sl-section" id="how" aria-labelledby="how-title">
      <div class="sl-wrap">
        <div class="sl-section-heading"><div><p class="sl-eyebrow">ЗА МАГИЕЙ — ТЕХНОЛОГИЯ</p><h2 id="how-title">Один проход.<br><em>Связанная картина.</em></h2></div><p>Движение камеры превращается<br>в карту конкретных бутылок.</p></div>
        <div class="sl-how-grid">
          <article><div class="sl-how-top"><span>01 / ВИДЕТЬ</span><svg viewBox="0 0 48 48" fill="none" aria-hidden="true"><path d="M16 7H7v9M32 7h9v9M41 32v9h-9M16 41H7v-9M24 17a7 7 0 1 0 0 14 7 7 0 0 0 0-14Z" stroke="currentColor" stroke-width="1.5"/></svg></div><h3>Находит бутылки</h3><p>Детектор на телефоне выделяет бутылки в видеопотоке. Для распознавания выбирается крупная и резкая вырезка.</p></article>
          <article><div class="sl-how-top"><span>02 / ПОМНИТЬ</span><svg viewBox="0 0 48 48" fill="none" aria-hidden="true"><rect x="6" y="16" width="16" height="25" rx="3" stroke="currentColor" stroke-width="1.5"/><rect x="26" y="7" width="16" height="25" rx="3" stroke="currentColor" stroke-width="1.5"/><path d="m17 12 6-6 6 6M23 6v21m8 10-6 6-6-6m6 6V22" stroke="currentColor" stroke-width="1.5"/></svg></div><h3>Узнаёт ту же бутылку</h3><p>Пространственная реидентификация, или ReID, связывает ракурсы. Положение на полке помогает различать даже одинаковые соседние бутылки.</p></article>
          <article><div class="sl-how-top"><span>03 / ПОНИМАТЬ</span><svg viewBox="0 0 48 48" fill="none" aria-hidden="true"><path d="m24 6 5 11 12 2-9 9 2 13-10-6-11 6 2-13-9-9 13-2 5-11Z" stroke="currentColor" stroke-width="1.5"/></svg></div><h3>Добавляет информацию</h3><p>Matcher ЧтоЗаВино распознаёт вино по вырезке. Затем приложение загружает рейтинг «Своё Вино» и показывает его прямо на полке.</p></article>
        </div>
      </div>
    </section>

    <section class="sl-planogram-section sl-wrap sl-section" id="planogram" aria-labelledby="planogram-title">
      <div class="sl-section-heading"><div><p class="sl-eyebrow">ДЛЯ БИЗНЕСА</p><h2 id="planogram-title">Полка становится<br><em>данными.</em></h2></div><div class="sl-heading-aside"><p>Соберите планограмму из найденных бутылок: ряды, фейсинги и группы одного вина. Сохраните результат, отправьте коллеге или распечатайте.</p><a class="sl-text-link" href="/shelf-lens/planogram.png" download="shelf-lens-planogram.png">Скачать пример <span aria-hidden="true">↗</span></a></div></div>
      <div class="sl-planogram-frame"><div class="sl-window-bar"><span><i></i><i></i><i></i></span><p>ПЛАНОГРАММА ИЗ ДЕМОНСТРАЦИИ</p><button class="sl-expand-plan" @click="openPlan" aria-label="Открыть планограмму крупнее" title="Увеличить планограмму"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/></svg></button></div><button class="sl-planogram-image-button" @click="openPlan" aria-label="Рассмотреть планограмму из демонстрации"><img src="/shelf-lens/planogram.png" alt="Реальная планограмма: три полки, 95 фейсингов, 46 распознанных бутылок. Неопознанные позиции показаны серыми силуэтами." loading="lazy" width="1280" height="615"></button></div>
      <div class="sl-planogram-bottom"><p class="sl-planogram-note">Пример из демо.<br>Серые силуэты — позиции, которые ещё не распознаны.</p><dl class="sl-demo-stats"><div><dt>Полки</dt><dd>3</dd></div><div><dt>Фейсингов</dt><dd>95</dd></div><div><dt>Распознано</dt><dd>46</dd></div></dl></div>
      <div class="sl-business-line"><span class="sl-business-icon" aria-hidden="true">↗</span><p><strong>Основа для работы с выкладкой.</strong> Цифровая схема помогает увидеть расположение и число фейсингов. Сравнение с эталоном и контроль выкладки могут стать следующим уровнем.</p><button class="sl-text-link" @click="openVideo(114, $event)">Планограмма в видео <span aria-hidden="true">▶</span></button></div>
    </section>

    <section class="sl-future-section sl-section" id="next" aria-labelledby="next-title">
      <div class="sl-wrap"><div class="sl-section-heading"><div><p class="sl-eyebrow">ЧТО ДАЛЬШЕ</p><h2 id="next-title">Сегодня — рейтинг.<br><em>Завтра — ваш ориентир.</em></h2></div><p>Карта полки открывает новые сценарии.<br><span class="sl-future-disclaimer">Ниже — направления развития.</span></p></div>
        <div class="sl-future-grid">
          <article><div class="sl-future-art sl-search-art" aria-hidden="true"><span class="sl-mini-bottle"></span><span class="sl-mini-bottle"></span><span class="sl-mini-bottle sl-target-bottle"></span><span class="sl-mini-bottle"></span><span class="sl-search-ring">⌕</span></div><span class="sl-future-tag">СЦЕНАРИЙ РАЗВИТИЯ</span><h3>Найти нужную бутылку</h3><p>Введите название — и выделите искомое вино среди десятков похожих этикеток.</p></article>
          <article><div class="sl-future-art sl-route-art" aria-hidden="true"><svg viewBox="0 0 300 130" fill="none"><path d="M45 110V82q0-16 16-16h120q16 0 16-16V24" stroke="currentColor" stroke-width="2" stroke-dasharray="5 7"/><path d="m185 39 12-16 12 16" stroke="currentColor" stroke-width="2"/><circle cx="45" cy="110" r="5" fill="currentColor"/></svg><span class="sl-route-pin">⌖</span></div><span class="sl-future-tag">СЦЕНАРИЙ РАЗВИТИЯ</span><h3>Дойти до своей бутылки</h3><p>Получите подсказки в дополненной реальности, которые приведут к выбранной позиции.</p></article>
          <article><div class="sl-future-art sl-taste-art" aria-hidden="true"><span class="sl-mini-bottle"></span><span class="sl-mini-bottle sl-taste-match"></span><span class="sl-mini-bottle"></span><span class="sl-mini-bottle sl-taste-match"></span><span class="sl-taste-heart">♡</span></div><span class="sl-future-tag">СЦЕНАРИЙ РАЗВИТИЯ</span><h3>Увидеть то, что вам близко</h3><p>Подсветите вина, которые соответствуют вашему вкусу, прямо на полке магазина.</p></article>
        </div>
        <p class="sl-future-footnote">Поиск, AR-навигация и персональная подсветка пока не входят в текущую версию Shelf Lens.</p>
      </div>
    </section>

    <section class="sl-faq-section sl-wrap sl-section" aria-labelledby="faq-title"><div><p class="sl-eyebrow">ЕЩЁ НЕСКОЛЬКО ДЕТАЛЕЙ</p><h2 id="faq-title">Всё по местам.</h2></div><div class="sl-faq-list">
      <details><summary>Почему одинаковые бутылки не сливаются в одну?<span aria-hidden="true">+</span></summary><p>Shelf Lens учитывает положение бутылки на карте полки. Соседние бутылки одного вина получают отдельные позиции. При движении камеры приложение сопоставляет новые ракурсы с этой картой.</p></details>
      <details><summary>Нужен ли интернет?<span aria-hidden="true">+</span></summary><p>Детектор и трекер работают на телефоне. Для распознавания вина через matcher и загрузки рейтинга нужен интернет. На сервер отправляется выбранная вырезка бутылки.</p></details>
      <details><summary>На каких устройствах это работает?<span aria-hidden="true">+</span></summary><p>Текущая версия — Android-приложение для Android 10 и новее с ARM-процессором. Представленное видео записано на телефоне. Скорость зависит от устройства и условий съёмки.</p></details>
      <details><summary>Как установить на Android?<span aria-hidden="true">+</span></summary><p>Скачайте APK и откройте файл. Если Android запросит разрешение, разрешите установку приложений из этого браузера. Приложение появится на телефоне под именем «Полка вина». Для распознавания нужен интернет.</p></details>
      <details><summary>Можно ли уже искать бутылку с помощью AR?<span aria-hidden="true">+</span></summary><p>Сейчас доступны сканирование, распознавание, рейтинг поверх изображения, список вин и планограмма. Поиск конкретной бутылки, AR-навигация и подбор по вкусу — направления дальнейшего развития.</p></details>
    </div></section>

    <section class="sl-closing sl-wrap"><div class="sl-closing-mark" aria-hidden="true">✳</div><p class="sl-eyebrow">SHELF LENS / ЧТОЗАВИНО</p><h2>У каждой бутылки — место.<br><em>У вас — вся картина.</em></h2><a class="sl-button sl-button-primary" :href="SHELF_LENS_APK_URL" :download="SHELF_LENS_ANDROID_RELEASE.apkFileName">Скачать для Android <span aria-hidden="true">↓</span></a><span class="sl-closing-note">Тестовая версия {{ SHELF_LENS_ANDROID_RELEASE.version }} · APK {{ SHELF_LENS_ANDROID_RELEASE.apkDisplaySize }} · Android {{ SHELF_LENS_ANDROID_RELEASE.minAndroid }}+</span></section>

<dialog id="video-dialog" ref="videoDialog" @close="closeDialog" @click="closeOnBackdrop" aria-labelledby="video-dialog-title"><div class="sl-dialog-bar"><div><span class="sl-eyebrow">РЕАЛЬНАЯ ЗАПИСЬ</span><h2 id="video-dialog-title">Shelf Lens в действии</h2></div><button class="sl-dialog-close" @click="videoDialog?.close()" aria-label="Закрыть видео">×</button></div><video id="full-video" ref="fullVideo" @loadedmetadata="applyRequestedTime" controls playsinline preload="none" poster="/shelf-lens/ar-rating.jpg"><source :src="'/shelf-lens-video/shelf-lens-demo.mp4'" type="video/mp4"></video><div class="sl-video-timeline" aria-label="Перейти к фрагменту"><button @click="seekVideo(12)">00:12 · Камера</button><button @click="seekVideo(36)">00:36 · AR-рейтинг</button><button @click="seekVideo(84)">01:24 · Список</button><button @click="seekVideo(114)">01:54 · Планограмма</button></div></dialog>
  <dialog id="plan-dialog" ref="planDialog" @close="closeDialog" @click="closeOnBackdrop" aria-labelledby="plan-dialog-title"><div class="sl-dialog-bar"><div><span class="sl-eyebrow">РЕЗУЛЬТАТ ИЗ ДЕМО</span><h2 id="plan-dialog-title">Планограмма полки</h2></div><button class="sl-dialog-close" @click="planDialog?.close()" aria-label="Закрыть планограмму">×</button></div><div class="sl-plan-dialog-scroll"><img src="/shelf-lens/planogram.png" alt="Планограмма из демонстрации Shelf Lens: 3 полки, 95 фейсингов, 46 распознано" width="1280" height="615"></div><p class="sl-dialog-note">На телефоне прокрутите изображение по горизонтали, чтобы рассмотреть детали.</p><a class="sl-button sl-button-primary" href="/shelf-lens/planogram.png" download="shelf-lens-planogram.png">Скачать планограмму <span aria-hidden="true">↓</span></a></dialog>
</main>
</template>

<style scoped>
.shelf-lens-page { color-scheme:light;--sl-bg:#f6f4ef;--sl-paper:#fffefa;--sl-ink:#242727;--sl-muted:#6c706e;--sl-line:#dcded5;--sl-wine:#78283e;--sl-wine-dark:#602033;--sl-blush:#ece3e1;--sl-stage:#dce0d5;--sl-stage-ink:#52614c;--sl-soft:#eaece5;--sl-green:#4f7952;--sl-yellow:#b89440;--sl-shadow:0 22px 70px #20291c14; background: var(--sl-bg); color: var(--sl-ink); margin-top: 24px; font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
:global([data-theme='dark'] .shelf-lens-page) { color-scheme:dark;--sl-bg:#171b18;--sl-paper:#222723;--sl-ink:#edf0e7;--sl-muted:#b0b8ad;--sl-line:#3b443a;--sl-wine:#e8a0b3;--sl-wine-dark:#f4bac8;--sl-blush:#392c30;--sl-stage:#2d3c2d;--sl-stage-ink:#bbcdb1;--sl-soft:#222b23;--sl-green:#92b88c;--sl-yellow:#e3bf6d;--sl-shadow:0 22px 70px #0004; }
* { box-sizing: border-box; }
button,a { -webkit-tap-highlight-color: transparent; }
button,input { font: inherit; }
button { cursor: pointer; }
button:disabled { cursor: default; }
a { color: inherit; text-decoration: none; }
button { color: inherit; }
button:focus-visible,a:focus-visible,summary:focus-visible { outline: 3px solid var(--sl-wine); outline-offset: 5px; }
img,video { display: block; max-width: 100%; }
h1,h2,h3,p { margin: 0; }
h1,h2 { font-family: 'Playfair Display',Georgia,serif; font-weight: 500; letter-spacing: -.055em; }
h1 em,h2 em { font-weight: 500; font-style: italic; color: var(--sl-wine); }
.sl-wrap { max-width: 1280px; margin: auto; padding-inline: 48px; }
.sl-section { padding-top: 112px; padding-bottom: 110px; }
.sl-eyebrow { font-size: 10px; line-height: 1.5; font-weight: 650; letter-spacing: .16em; color: var(--sl-wine); }
.sl-button { min-height: 46px; display: inline-flex; align-items: center; justify-content: center; gap: 20px; border: 1px solid var(--sl-line); padding: 14px 22px; border-radius: 8px; font-size: 12px; line-height: 1.4; font-weight: 550; background: transparent; transition: background .2s,transform .2s,border-color .2s; }
.sl-button:hover { transform: translateY(-2px); border-color: var(--sl-wine); }
.sl-button span:last-child { font-size: 18px; }
.sl-button-primary { background: var(--sl-wine); color: var(--sl-bg); border-color: var(--sl-wine); min-height: 53px; }
.sl-button-primary:hover { background: var(--sl-wine-dark); }
.sl-text-link { display: inline-flex; gap: 20px; align-items: center; font-size: 12px; font-weight: 550; background: none; border: 0; padding: 12px 0; color: var(--sl-ink); }
.sl-text-link:hover { color: var(--sl-wine); }
.sl-text-link span { font-size: 18px; }
.sl-hero { display: grid; grid-template-columns: 1.05fr 1fr; gap: 50px; padding-top: 38px; padding-bottom: 68px; }
.sl-hero-copy { padding-top: 28px; display: flex; flex-direction: column; align-items: flex-start; }
.sl-tiny-spark { font-size: 18px; vertical-align: middle; margin-right: 7px; }
.sl-hero h1 { font-size: clamp(64px,6.5vw,94px); line-height: 1.025; margin: 25px 0 29px; }
.sl-hero-description { font-size: 15px; line-height: 1.8; max-width: 393px; color: var(--sl-muted); }
.sl-hero-actions { display: flex; align-items: center; gap: 27px; margin-top: 31px; }
.sl-hero-actions .sl-text-link { white-space: nowrap; font-size: 11px; gap: 12px; }
.sl-play-small { font-size: 10px !important; display: grid; place-items: center; border: 1px solid currentColor; border-radius: 50%; width: 24px; height: 24px; padding-left: 2px; }
.sl-hero-note { display: flex; gap: 9px; align-items: center; font-size: 10px; color: var(--sl-muted); margin-top: 23px; line-height: 1.6; }
.sl-android-mark { font-size: 16px; color: var(--sl-green); }
.sl-note-dot { margin: 0 7px; }
.sl-hero-stage { height: 613px; position: relative; background: var(--sl-stage); border-radius: 22px; isolation: isolate; overflow: hidden; }
.sl-stage-grid { position: absolute; inset: 0; background-image: linear-gradient(to right,color-mix(in srgb,var(--sl-stage-ink) 7%,transparent) 1px,transparent 1px),linear-gradient(to bottom,color-mix(in srgb,var(--sl-stage-ink) 7%,transparent) 1px,transparent 1px); background-size: 64px 64px; }
.sl-stage-top { position: absolute; top: 22px; left: 24px; right: 24px; display: flex; align-items: center; gap: 7px; font-size: 8px; letter-spacing: .12em; color: var(--sl-stage-ink); }
.sl-stage-top>span:last-child { margin-left: auto; font-size: 9px; letter-spacing: .07em; }
.sl-status-dot { width: 5px; height: 5px; border-radius: 50%; background: #5d8051; box-shadow: 0 0 0 3px #759b5f20; display: inline-block; flex-shrink: 0; }
.sl-stage-lettering { position: absolute; top: 105px; left: 28px; line-height: .85; font-family: 'Playfair Display',Georgia,serif; font-size: 120px; letter-spacing: -.1em; color: var(--sl-stage-ink); opacity: .12; user-select: none; }
.sl-phone { overflow: hidden; background: #111b15; border: 6px solid #2c322c; border-radius: 29px; box-shadow: 15px 25px 45px #1e311e40; }
.sl-hero-phone { position: absolute; height: 486px; aspect-ratio: 9/16; top: 64px; left: 50%; transform: translateX(-34%) rotate(6deg); }
.sl-phone video { height: 100%; width: 100%; object-fit: cover; border-radius: 23px; }
.sl-floating-rating { position: absolute; top: 143px; left: 20px; display: flex; gap: 12px; padding: 17px 19px; background: var(--sl-paper); border: 1px solid color-mix(in srgb,var(--sl-line) 70%,transparent); box-shadow: var(--sl-shadow); border-radius: 12px; transform: rotate(-4deg); z-index: 2; }
.sl-float-icon { color: var(--sl-wine); font-size: 26px; line-height: 1.3; }
.sl-floating-rating small { font-size: 7px; letter-spacing: .1em; color: var(--sl-muted); font-weight: 550; }
.sl-rating-stars { display: block; color: #bc8e37; letter-spacing: 3px; font-size: 22px; margin-top: 6px; }
.sl-floating-rating p { font-size: 9px; color: var(--sl-muted); margin-top: 3px; }
.sl-floating-reid { position: absolute; bottom: 85px; left: 26px; background: var(--sl-paper); padding: 17px 21px 17px 16px; display: flex; align-items: center; gap: 12px; box-shadow: var(--sl-shadow); border: 1px solid var(--sl-line); border-radius: 12px; transform: rotate(-3deg); z-index: 2; }
.sl-reid-icon { display: grid; place-items: center; background: var(--sl-soft); border-radius: 50%; width: 34px; height: 34px; font-size: 26px; color: var(--sl-green); }
.sl-floating-reid strong { font-size: 12px; font-weight: 550; line-height: 1.5; display: block; }
.sl-floating-reid div>span { font-size: 8px; display: block; color: var(--sl-muted); margin-top: 7px; }
.sl-stage-bottom { position: absolute; bottom: 21px; left: 24px; right: 24px; color: var(--sl-stage-ink); display: flex; justify-content: space-between; font-size: 8px; letter-spacing: .14em; }
.sl-stage-bottom span { font-size: 6px; }
.sl-motion-toggle { position: absolute; bottom: 51px; right: 18px; width: 29px; height: 29px; border-radius: 50%; background: var(--sl-paper); border: 1px solid var(--sl-line); color: var(--sl-ink); font-size: 12px; }
.sl-proof-strip { display: grid; grid-template-columns: repeat(3,1fr); padding-top: 25px; padding-bottom: 27px; position: relative; }
.sl-proof-strip::before,.sl-proof-strip::after { content: ''; position: absolute; left: 48px; right: 48px; height: 1px; background: var(--sl-line); top: 0; }
.sl-proof-strip::after { top: auto; bottom: 0; }
.sl-proof-strip>div { display: flex; align-items: center; gap: 18px; }
.sl-strip-number { font: italic 30px 'Playfair Display',Georgia,serif; color: var(--sl-wine); }
.sl-proof-strip strong { display: block; font-size: 12px; font-weight: 550; margin-bottom: 7px; }
.sl-proof-strip p>span { display: block; font-size: 11px; color: var(--sl-muted); }
.sl-section-heading { display: flex; justify-content: space-between; gap: 50px; align-items: flex-end; margin-bottom: 47px; }
.sl-section-heading h2 { font-size: 53px; line-height: 1.13; margin-top: 17px; }
.sl-section-heading>p,.sl-heading-aside>p { font-size: 13px; line-height: 1.85; color: var(--sl-muted); max-width: 342px; padding-bottom: 7px; }
.sl-demo-layout { display: grid; grid-template-columns: .9fr 1fr; gap: 100px; align-items: center; }
.sl-demo-screen { position: relative; height: 545px; background: #28362d; border-radius: 17px; overflow: hidden; display: flex; align-items: center; justify-content: center; }
.sl-demo-screen::after { content: ''; position: absolute; inset: 0; background: linear-gradient(180deg,#14211960,transparent 18%,transparent 75%,#14211999); pointer-events: none; }
.sl-demo-screen img { height: 100%; width: auto; aspect-ratio: 9/16; object-fit: cover; }
.sl-demo-screen-label { position: absolute; top: 20px; left: 20px; color: #fffdf7; font-size: 8px; letter-spacing: .05em; z-index: 1; display: flex; align-items: center; gap: 9px; background: #17271bc9; padding: 8px 11px; border-radius: 5px; }
.sl-demo-screen-label .sl-status-dot { background: #c2d9b3; }
.sl-demo-play { position: absolute; left: 50%; top: 50%; transform: translate(-50%,-50%); height: 65px; width: 65px; border: 1px solid #ffffff90; border-radius: 50%; background: #f8f9f133; color: #fff; backdrop-filter: blur(6px); font-size: 18px; z-index: 1; padding-left: 7px; transition: background .2s; }
.sl-demo-play:hover { background: #f8f9f166; }
.sl-demo-duration { position: absolute; z-index: 1; bottom: 20px; left: 22px; right: 22px; display: flex; align-items: center; justify-content: space-between; color: #fff; font-size: 15px; font-weight: 500; }
.sl-demo-duration>span { font-size: 7px; letter-spacing: .15em; opacity: .8; }
.sl-chapter { border: 0; border-top: 1px solid var(--sl-line); display: flex; gap: 21px; background: transparent; text-align: left; width: 100%; padding: 27px 0; color: var(--sl-muted); transition: color .2s; }
.sl-chapter:last-of-type { border-bottom: 1px solid var(--sl-line); }
.sl-chapter-time { font-family: monospace; font-size: 10px; padding-top: 5px; min-width: 36px; color: var(--sl-muted); }
.sl-chapter-body { flex: 1; }
.sl-chapter strong { font-size: 17px; font-weight: 500; line-height: 1.5; color: var(--sl-ink); display: block; margin-bottom: 10px; }
.sl-chapter-body>span { font-size: 12px; line-height: 1.9; display: block; }
.sl-chapter-arrow { font-size: 20px; color: var(--sl-muted); }
.sl-chapter.sl-active .sl-chapter-time,.sl-chapter.sl-active .sl-chapter-arrow,.sl-chapter.sl-active strong { color: var(--sl-wine); }
.sl-chapter.sl-active { border-top-color: var(--sl-wine); }
.sl-chapter:hover strong { color: var(--sl-wine); }
.sl-demo-caption { display: flex; gap: 15px; padding-top: 25px; color: var(--sl-muted); }
.sl-demo-caption>span { font-size: 22px; color: var(--sl-wine); }
.sl-demo-caption p { font-size: 10px; line-height: 1.8; }
.sl-demo-caption strong { font-weight: 550; }
.sl-state-legend { display: flex; flex-wrap: wrap; align-items: center; gap: 25px; margin-top: 24px; font-size: 9px; color: var(--sl-muted); }
.sl-state-legend>span { display: flex; gap: 7px; align-items: center; }
.sl-state-legend i { width: 8px; height: 8px; border-radius: 2px; border: 1px solid; }
.sl-legend-grey { border-color: #999 !important; }
.sl-legend-yellow { border-color: #cda335 !important; }
.sl-legend-green { border-color: #61975b !important; }
.sl-legend-note { margin-left: auto; font-size: 8px; }
.sl-how-section { background: var(--sl-soft); padding-top: 83px; padding-bottom: 84px; }
.sl-how-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 47px; }
.sl-how-grid article { border-top: 1px solid var(--sl-line); padding-top: 25px; }
.sl-how-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 31px; }
.sl-how-top span { font-size: 9px; letter-spacing: .1em; color: var(--sl-muted); }
.sl-how-top svg { width: 42px; height: 42px; color: var(--sl-wine); }
h3 { font-weight: 500; font-size: 19px; line-height: 1.4; letter-spacing: -.025em; }
.sl-how-grid p { font-size: 12px; line-height: 1.95; color: var(--sl-muted); margin-top: 16px; max-width: 300px; }
.sl-heading-aside { max-width: 340px; }
.sl-heading-aside .sl-text-link { color: var(--sl-wine); font-size: 11px; padding-bottom: 0; }
.sl-planogram-frame { overflow: hidden; background: #fffefa; border: 1px solid var(--sl-line); border-radius: 13px; box-shadow: var(--sl-shadow); }
.sl-window-bar { display: flex; align-items: center; justify-content: space-between; gap: 20px; height: 47px; padding: 0 20px; border-bottom: 1px solid #e7e7df; color: #6d746b; background: #f0f1eb; }
.sl-window-bar>span { display: flex; gap: 5px; }
.sl-window-bar i { background: #bdc3b8; width: 5px; height: 5px; border-radius: 50%; }
.sl-window-bar p { font-size: 8px; letter-spacing: .15em; }
.sl-expand-plan { background: none; border: 0; padding: 4px; line-height: 0; }
.sl-expand-plan svg { width: 18px; height: 18px; }
.sl-planogram-image-button { border: 0; background: #fffefa; padding: 18px 8px; display: block; width: 100%; cursor: zoom-in; }
.sl-planogram-image-button img { width: 100%; height: auto; }
.sl-planogram-bottom { margin-top: 27px; display: flex; align-items: center; justify-content: space-between; gap: 30px; }
.sl-planogram-note { font-size: 10px; line-height: 1.8; color: var(--sl-muted); }
.sl-demo-stats { display: flex; gap: 63px; margin: 0; }
.sl-demo-stats>div { display: flex; flex-direction: column-reverse; gap: 4px; }
.sl-demo-stats dd { font-family: 'Playfair Display',Georgia,serif; font-size: 43px; letter-spacing: -.05em; margin: 0; line-height: 1; }
.sl-demo-stats dt { font-size: 9px; line-height: 1.6; color: var(--sl-muted); }
.sl-business-line { border-top: 1px solid var(--sl-line); margin-top: 38px; padding-top: 23px; display: flex; align-items: center; gap: 25px; }
.sl-business-icon { font-size: 34px; color: var(--sl-wine); }
.sl-business-line p { font-size: 11px; color: var(--sl-muted); line-height: 1.9; max-width: 650px; }
.sl-business-line strong { color: var(--sl-ink); font-weight: 550; }
.sl-business-line .sl-text-link { margin-left: auto; font-size: 10px; white-space: nowrap; }
.sl-future-section { background: var(--sl-blush); padding-block: 87px; }
.sl-future-section .sl-section-heading h2 { font-size: 49px; }
.sl-future-disclaimer { font-size: 11px; }
.sl-future-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 33px; }
.sl-future-grid article { border-top: 1px solid color-mix(in srgb,var(--sl-wine) 20%,transparent); padding-top: 10px; }
.sl-future-art { height: 143px; display: flex; align-items: flex-end; justify-content: center; gap: 12px; position: relative; overflow: hidden; margin-bottom: 25px; color: var(--sl-wine); }
.sl-mini-bottle { display: block; width: 31px; height: 83px; border: 1px solid color-mix(in srgb,var(--sl-wine) 20%,transparent); background: color-mix(in srgb,var(--sl-wine) 8%,transparent); border-radius: 12px 12px 4px 4px; position: relative; margin-bottom: 12px; }
.sl-mini-bottle:before { content: ''; position: absolute; width: 12px; height: 25px; border: 1px solid color-mix(in srgb,var(--sl-wine) 20%,transparent); background: var(--sl-blush); left: 8px; top: -22px; border-radius: 2px; }
.sl-mini-bottle:after { content: ''; position: absolute; left: 3px; right: 3px; height: 27px; top: 32px; background: color-mix(in srgb,var(--sl-wine) 8%,transparent); }
.sl-target-bottle,.sl-taste-match { outline: 1px solid var(--sl-wine); outline-offset: 6px; background: color-mix(in srgb,var(--sl-wine) 18%,transparent); }
.sl-search-ring { position: absolute; top: 12px; right: 54px; border-radius: 50%; width: 46px; height: 46px; display: grid; place-items: center; background: var(--sl-wine); color: var(--sl-bg); font-size: 33px; transform: rotate(-18deg); box-shadow: 5px 6px 0 color-mix(in srgb,var(--sl-wine) 12%,transparent); }
.sl-route-art svg { position: absolute; height: 130px; width: 100%; bottom: 0; }
.sl-route-pin { position: absolute; top: 2px; right: 71px; font-size: 42px; line-height: 1; }
.sl-taste-heart { position: absolute; top: 7px; left: calc(50% - 23px); font-size: 46px; transform: rotate(-14deg); background: var(--sl-blush); padding-inline: 5px; }
.sl-future-tag { font-size: 7px; letter-spacing: .12em; color: var(--sl-wine); font-weight: 600; display: inline-block; border: 1px solid color-mix(in srgb,var(--sl-wine) 30%,transparent); border-radius: 3px; padding: 5px 7px; margin-bottom: 13px; }
.sl-future-grid h3 { font-size: 19px; }
.sl-future-grid p { font-size: 12px; line-height: 1.85; color: var(--sl-muted); margin-top: 13px; max-width: 310px; }
.sl-future-footnote { border-top: 1px solid color-mix(in srgb,var(--sl-wine) 20%,transparent); margin-top: 39px; padding-top: 19px; font-size: 9px; line-height: 1.8; color: var(--sl-muted); }
.sl-faq-section { display: grid; grid-template-columns: .85fr 1.15fr; gap: 80px; }
.sl-faq-section h2 { font-size: 45px; line-height: 1.2; margin-top: 20px; }
.sl-faq-list details { border-top: 1px solid var(--sl-line); }
.sl-faq-list details:last-child { border-bottom: 1px solid var(--sl-line); }
summary { cursor: pointer; list-style: none; display: flex; align-items: center; gap: 20px; justify-content: space-between; font-size: 13px; padding: 23px 0; line-height: 1.5; }
summary::-webkit-details-marker { display: none; }
summary>span { font-size: 24px; font-weight: 300; line-height: 1; color: var(--sl-wine); }
details[open] summary>span { transform: rotate(45deg); }
details>p { font-size: 12px; color: var(--sl-muted); line-height: 1.9; padding: 0 32px 23px 0; }
.sl-closing { text-align: center; border-top: 1px solid var(--sl-line); padding-top: 52px; padding-bottom: 75px; }
.sl-closing-mark { font-size: 40px; color: var(--sl-wine); margin-bottom: 17px; }
.sl-closing .sl-eyebrow { font-size: 8px; }
.sl-closing h2 { font-size: 53px; line-height: 1.23; margin: 22px 0 28px; }
.sl-closing .sl-button { min-width: 216px; }
.sl-closing-note { display: block; color: var(--sl-muted); font-size: 9px; margin-top: 18px; }
dialog { border: 1px solid var(--sl-line); border-radius: 18px; background: var(--sl-bg); color: var(--sl-ink); padding: 22px; max-height: 94dvh; box-shadow: 0 25px 100px #0006; }
dialog::backdrop { background: #0c150de6; backdrop-filter: blur(8px); }
#video-dialog { width: min(700px,calc(100% - 28px)); }
.sl-dialog-bar { display: flex; justify-content: space-between; align-items: center; gap: 20px; margin-bottom: 17px; }
.sl-dialog-bar h2 { font-size: 23px; letter-spacing: -.03em; margin-top: 3px; }
.sl-dialog-bar .sl-eyebrow { font-size: 7px; }
.sl-dialog-close { width: 38px; height: 38px; font-size: 29px; line-height: 1; border: 1px solid var(--sl-line); background: var(--sl-paper); border-radius: 50%; font-weight: 300; flex-shrink: 0; }
.sl-dialog-close:hover { border-color: var(--sl-wine); }
#full-video { width: 100%; max-height: calc(90dvh - 150px); background: #111; min-height: 240px; object-fit: contain; border-radius: 6px; }
.sl-video-timeline { display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
.sl-video-timeline button { border: 1px solid var(--sl-line); background: transparent; padding: 9px; font-size: 9px; border-radius: 4px; }
.sl-video-timeline button:hover { background: var(--sl-soft); }
#plan-dialog { width: min(1400px,calc(100% - 28px)); padding: 25px; }
#plan-dialog .sl-button { margin-top: 15px; min-height: 42px; font-size: 11px; }
.sl-plan-dialog-scroll { overflow: auto; border-radius: 6px; background: #fffefa; }
.sl-plan-dialog-scroll img { width: 100%; max-width: none; min-width: 800px; height: auto; }
.sl-dialog-note { font-size: 10px; margin-top: 13px; line-height: 1.7; color: var(--sl-muted); }
@media (min-width:1600px) {
  .sl-hero { padding-top: 58px; padding-bottom: 80px; }
  .sl-hero-stage { height: 650px; }
  .sl-hero-phone { height: 520px; }
  .sl-hero-copy { padding-top: 40px; }
  .sl-hero h1 { font-size: 96px; }
  .sl-floating-rating { top: 155px; }
  .sl-floating-reid { bottom: 92px; }
}
@media (max-width:1100px) {
  .sl-wrap { padding-inline: 32px; }
  .sl-hero { gap: 25px; }
  .sl-hero h1 { font-size: 74px; }
  .sl-hero-stage { height: 574px; }
  .sl-hero-phone { height: 457px; top: 61px; transform: translateX(-40%) rotate(6deg); }
  .sl-floating-rating { left: 13px; padding: 13px 14px; top: 135px; }
  .sl-floating-reid { left: 15px; bottom: 65px; padding: 13px; }
  .sl-floating-reid strong { font-size: 11px; }
  .sl-hero-description { font-size: 14px; max-width: 350px; }
  .sl-hero-actions { gap: 17px; flex-wrap: wrap; margin-top: 24px; }
  .sl-hero-actions .sl-button { font-size: 11px; padding-inline: 15px; gap: 12px; }
  .sl-proof-strip::before,.sl-proof-strip::after { left: 32px; right: 32px; }
  .sl-proof-strip>div { gap: 12px; }
  .sl-proof-strip strong { font-size: 11px; }
  .sl-proof-strip p>span { font-size: 10px; }
  .sl-demo-layout { gap: 55px; }
  .sl-section-heading h2 { font-size: 48px; }
  .sl-how-grid { gap: 30px; }
  .sl-future-grid { gap: 25px; }
  .sl-future-grid h3 { font-size: 17px; }
  .sl-faq-section { gap: 45px; }
  .sl-demo-stats { gap: 45px; }
  .sl-business-line { gap: 18px; }
  .sl-future-section .sl-section-heading h2 { font-size: 43px; }
}
@media (max-width:800px) {
  .sl-wrap { padding-inline: 24px; }
  .sl-hero { gap: 22px; padding-top: 20px; padding-bottom: 40px; }
  .sl-hero h1 { font-size: 61px; }
  .sl-hero-copy { padding-top: 17px; }
  .sl-eyebrow { font-size: 8px; }
  .sl-hero-description { font-size: 12px; line-height: 1.9; max-width: 300px; }
  .sl-hero-actions { gap: 10px; margin-top: 21px; }
  .sl-hero-actions .sl-button { min-height: 48px; font-size: 10px; padding: 10px 13px; }
  .sl-hero-actions .sl-text-link { font-size: 10px; }
  .sl-hero-note { font-size: 8px; margin-top: 16px; }
  .sl-hero-stage { height: 505px; }
  .sl-hero-phone { height: 390px; top: 70px; transform: translateX(-42%) rotate(6deg); }
  .sl-floating-rating { left: 9px; top: 145px; padding: 11px; gap: 7px; }
  .sl-float-icon { font-size: 19px; }
  .sl-floating-rating small { font-size: 6px; }
  .sl-rating-stars { font-size: 17px; }
  .sl-floating-rating p { font-size: 7px; }
  .sl-floating-reid { bottom: 65px; left: 10px; gap: 8px; padding: 12px; }
  .sl-reid-icon { height: 27px; width: 27px; font-size: 21px; }
  .sl-floating-reid strong { font-size: 9px; }
  .sl-floating-reid div>span { font-size: 6px; }
  .sl-stage-top { left: 16px; right: 16px; font-size: 6px; }
  .sl-stage-top>span:last-child { font-size: 7px; }
  .sl-stage-bottom { left: 16px; right: 16px; font-size: 6px; }
  .sl-stage-bottom span { font-size: 4px; }
  .sl-stage-lettering { font-size: 90px; }
  .sl-proof-strip { gap: 20px; }
  .sl-proof-strip>div { align-items: flex-start; gap: 10px; }
  .sl-strip-number { font-size: 23px; }
  .sl-proof-strip strong { line-height: 1.5; max-width: 160px; margin-bottom: 4px; }
  .sl-proof-strip p>span { font-size: 9px; line-height: 1.5; }
  .sl-proof-strip::before,.sl-proof-strip::after { left: 24px; right: 24px; }
  .sl-section { padding-block: 75px; }
  .sl-section-heading { gap: 24px; margin-bottom: 35px; }
  .sl-section-heading h2 { font-size: 40px; }
  .sl-section-heading>p,.sl-heading-aside>p { font-size: 11px; max-width: 260px; }
  .sl-demo-layout { gap: 35px; }
  .sl-demo-screen { height: 485px; }
  .sl-chapter { gap: 11px; padding-block: 22px; }
  .sl-chapter strong { font-size: 14px; }
  .sl-chapter-body>span { font-size: 11px; }
  .sl-chapter-time { font-size: 9px; min-width: 30px; }
  .sl-chapter-arrow { font-size: 16px; }
  .sl-demo-caption p { font-size: 9px; }
  .sl-state-legend { gap: 16px; font-size: 8px; }
  .sl-legend-note { margin-left: 0; }
  .sl-how-grid { gap: 22px; }
  .sl-how-grid h3 { font-size: 16px; }
  .sl-how-grid p { font-size: 11px; }
  .sl-how-top { margin-bottom: 20px; }
  .sl-how-top svg { width: 32px; height: 32px; }
  .sl-how-top span { font-size: 7px; }
  .sl-future-section .sl-section-heading h2 { font-size: 37px; }
  .sl-future-grid { gap: 20px; }
  .sl-future-art { gap: 8px; height: 125px; }
  .sl-mini-bottle { width: 25px; height: 68px; }
  .sl-mini-bottle:before { left: 6px; width: 11px; height: 20px; top: -18px; }
  .sl-mini-bottle:after { top: 27px; height: 20px; }
  .sl-future-grid h3 { font-size: 16px; }
  .sl-future-grid p { font-size: 11px; }
  .sl-search-ring { right: 5px; }
  .sl-route-pin { right: 20px; }
  .sl-future-tag { font-size: 6px; }
  .sl-planogram-note { font-size: 9px; }
  .sl-demo-stats { gap: 30px; }
  .sl-demo-stats dd { font-size: 36px; }
  .sl-business-line .sl-text-link { font-size: 9px; }
  .sl-business-line p { font-size: 10px; }
  .sl-business-icon { display: none; }
  .sl-faq-section { gap: 30px; grid-template-columns: .7fr 1fr; }
  .sl-faq-section h2 { font-size: 35px; }
  summary { font-size: 11px; padding-block: 20px; }
  details>p { font-size: 11px; }
  .sl-closing h2 { font-size: 44px; }
}
@media (max-width:600px) {
  .sl-wrap { padding-inline: 22px; }
  .sl-hero { grid-template-columns: 1fr; padding-top: 23px; gap: 31px; padding-bottom: 36px; }
  .sl-hero-copy { padding-top: 0; }
  .sl-hero .sl-eyebrow { font-size: 7px; letter-spacing: .13em; }
  .sl-tiny-spark { font-size: 14px; }
  .sl-hero h1 { font-size: clamp(44px,13vw,72px); margin: 18px 0 20px; line-height: 1.025; }
  .sl-hero-description { font-size: 13px; max-width: 345px; line-height: 1.85; }
  .sl-hero-actions { gap: 20px; margin-top: 23px; flex-wrap: nowrap; }
  .sl-hero-actions .sl-button { font-size: 10px; gap: 12px; padding: 12px 15px; min-height: 49px; }
  .sl-hero-actions .sl-text-link { font-size: 9px; gap: 10px; }
  .sl-hero-note { font-size: 8px; margin-top: 17px; }
  .sl-hero-stage { height: 488px; max-width: 440px; width: 100%; margin-inline: auto; border-radius: 16px; }
  .sl-hero-phone { height: 395px; top: 53px; transform: translateX(-36%) rotate(6deg); }
  .sl-floating-rating { left: 15px; top: 122px; padding: 14px 15px; gap: 11px; }
  .sl-floating-rating small { font-size: 6px; }
  .sl-floating-rating p { font-size: 8px; }
  .sl-rating-stars { font-size: 19px; }
  .sl-floating-reid { left: 16px; bottom: 63px; padding: 14px 17px; gap: 11px; }
  .sl-floating-reid strong { font-size: 10px; }
  .sl-floating-reid div>span { font-size: 7px; }
  .sl-reid-icon { width: 30px; height: 30px; }
  .sl-stage-top { top: 17px; font-size: 6px; }
  .sl-stage-bottom { bottom: 17px; font-size: 6px; }
  .sl-stage-bottom span { font-size: 5px; }
  .sl-motion-toggle { bottom: 44px; right: 15px; }
  .sl-proof-strip { grid-template-columns: 1fr; gap: 18px; padding-block: 23px; }
  .sl-proof-strip>div { align-items: center; gap: 17px; }
  .sl-proof-strip p { display: flex; flex-direction: column; gap: 2px; }
  .sl-proof-strip strong { font-size: 11px; max-width: none; margin: 0; }
  .sl-proof-strip p>span { font-size: 10px; }
  .sl-strip-number { font-size: 27px; }
  .sl-proof-strip::before,.sl-proof-strip::after { left: 22px; right: 22px; }
  .sl-section { padding-block: 64px; }
  .sl-section-heading { display: block; margin-bottom: 30px; }
  .sl-section-heading h2 { font-size: 38px; line-height: 1.16; margin-top: 13px; }
  .sl-section-heading>p,.sl-heading-aside>p { font-size: 12px; max-width: 340px; line-height: 1.85; margin-top: 22px; padding: 0; }
  .sl-demo-layout { grid-template-columns: 1fr; gap: 25px; }
  .sl-demo-screen { height: 505px; max-width: 420px; width: 100%; margin: auto; }
  .sl-demo-screen img { width: auto; max-width: 100%; }
  .sl-demo-screen-label { font-size: 8px; left: 16px; top: 17px; }
  .sl-demo-duration { font-size: 13px; bottom: 16px; }
  .sl-demo-duration>span { font-size: 6px; }
  .sl-chapter { padding-block: 22px; gap: 17px; }
  .sl-chapter-time { font-size: 9px; min-width: 31px; }
  .sl-chapter strong { font-size: 15px; }
  .sl-chapter-body>span { font-size: 11px; line-height: 1.85; }
  .sl-chapter-arrow { font-size: 19px; }
  .sl-demo-caption { padding-top: 21px; }
  .sl-demo-caption p { font-size: 9px; }
  .sl-state-legend { gap: 13px 18px; font-size: 8px; margin-top: 28px; }
  .sl-legend-note { width: 100%; font-size: 8px; }
  .sl-how-grid { grid-template-columns: 1fr; gap: 30px; }
  .sl-how-grid article { padding-top: 19px; }
  .sl-how-top { margin-bottom: 15px; }
  .sl-how-top span { font-size: 8px; }
  .sl-how-top svg { width: 38px; height: 38px; }
  .sl-how-grid h3 { font-size: 20px; }
  .sl-how-grid p { font-size: 12px; max-width: 100%; margin-top: 12px; }
  .sl-how-section .sl-section-heading>p { margin-top: 19px; }
  .sl-heading-aside { max-width: none; }
  .sl-heading-aside .sl-text-link { font-size: 11px; padding-top: 13px; }
  .sl-planogram-section .sl-section-heading { margin-bottom: 26px; }
  .sl-planogram-image-button { padding: 12px 4px; }
  .sl-window-bar { padding-inline: 12px; height: 38px; gap: 10px; }
  .sl-window-bar p { font-size: 6px; letter-spacing: .08em; }
  .sl-window-bar i { width: 4px; height: 4px; }
  .sl-expand-plan svg { width: 16px; height: 16px; }
  .sl-planogram-frame { border-radius: 9px; }
  .sl-planogram-bottom { flex-direction: column-reverse; align-items: stretch; gap: 22px; margin-top: 22px; }
  .sl-demo-stats { justify-content: space-between; gap: 15px; }
  .sl-demo-stats dd { font-size: 41px; }
  .sl-demo-stats dt { font-size: 9px; }
  .sl-planogram-note { font-size: 9px; }
  .sl-business-line { flex-wrap: wrap; gap: 8px; margin-top: 25px; padding-top: 19px; }
  .sl-business-line p { font-size: 11px; line-height: 1.85; }
  .sl-business-line .sl-text-link { margin-left: 0; font-size: 10px; }
  .sl-future-section .sl-section-heading h2 { font-size: 36px; }
  .sl-future-grid { grid-template-columns: 1fr; gap: 30px; }
  .sl-future-grid article { position: relative; padding-top: 0; }
  .sl-future-art { height: 150px; margin-bottom: 20px; gap: 13px; }
  .sl-mini-bottle { width: 32px; height: 85px; }
  .sl-mini-bottle:before { width: 12px; height: 25px; top: -22px; left: 9px; }
  .sl-mini-bottle:after { top: 33px; height: 26px; }
  .sl-search-ring { right: 72px; top: 22px; }
  .sl-route-art svg { width: 300px; }
  .sl-route-pin { right: calc(50% - 67px); top: 9px; }
  .sl-taste-heart { top: 15px; }
  .sl-future-tag { font-size: 6px; }
  .sl-future-grid h3 { font-size: 21px; }
  .sl-future-grid p { font-size: 12px; max-width: 340px; margin-top: 11px; }
  .sl-future-footnote { font-size: 9px; margin-top: 32px; padding-top: 16px; line-height: 1.9; }
  .sl-faq-section { display: block; }
  .sl-faq-section h2 { font-size: 36px; margin-top: 13px; }
  .sl-faq-list { margin-top: 32px; }
  summary { font-size: 12px; padding-block: 23px; }
  details>p { font-size: 12px; line-height: 1.85; padding-right: 10px; }
  .sl-closing { padding-top: 41px; padding-bottom: 51px; }
  .sl-closing-mark { font-size: 34px; }
  .sl-closing h2 { font-size: 34px; line-height: 1.27; margin-top: 20px; }
  .sl-closing .sl-eyebrow { font-size: 7px; }
  .sl-closing .sl-button { font-size: 11px; min-width: 205px; }
  .sl-closing-note { font-size: 8px; }
  dialog { padding: 15px; border-radius: 12px; }
  .sl-dialog-bar h2 { font-size: 20px; }
  .sl-dialog-close { height: 32px; width: 32px; font-size: 25px; }
  .sl-dialog-bar { margin-bottom: 12px; }
  .sl-video-timeline { gap: 5px; margin-top: 10px; }
  .sl-video-timeline button { font-size: 7px; padding: 8px 6px; }
  #full-video { max-height: calc(90dvh - 155px); min-height: 160px; }
  #plan-dialog { padding: 15px; }
  .sl-dialog-note { font-size: 9px; }
  .sl-plan-dialog-scroll img { min-width: 880px; }
}
@media (max-width:360px) {
  .sl-hero h1 { font-size: 44px; }
  .sl-wrap { padding-inline: 18px; }
  .sl-hero-actions { gap: 13px; }
  .sl-hero-actions .sl-button { font-size: 9px; padding-inline: 11px; }
  .sl-hero-actions .sl-text-link { font-size: 8px; }
  .sl-hero-stage { height: 457px; }
  .sl-hero-phone { height: 372px; }
  .sl-floating-rating { left: 10px; }
  .sl-floating-reid { left: 10px; }
  .sl-demo-screen { height: 472px; }
  .sl-section-heading h2 { font-size: 34px; }
  .sl-future-section .sl-section-heading h2 { font-size: 32px; }
  .sl-closing h2 { font-size: 30px; }
}
@media (prefers-reduced-motion:reduce) {
  *,*:before,*:after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
  .sl-button:hover { transform: none; }
}
.sl-section-nav { display: flex; align-items: center; justify-content: flex-end; gap: 24px; min-height: 56px; flex-wrap: wrap; font-size: 12px; color: var(--sl-muted); }
.sl-section-nav > span { margin-right: auto; font-size: 22px; letter-spacing: -.04em; font-weight: 600; color: var(--sl-wine); }
.sl-section-nav a:hover { color: var(--sl-wine); }
section[id] { scroll-margin-top: 24px; }
@media (max-width: 600px) {
  .sl-section-nav { justify-content: flex-start; gap: 14px; padding-block: 18px 0; font-size: 10px; }
  .sl-section-nav > span { flex-basis: 100%; font-size: 21px; }
}

</style>
