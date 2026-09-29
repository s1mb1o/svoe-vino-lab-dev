<script setup lang="ts">
import { ANDROID_RELEASE, DEFAULT_ANDROID_APK_URL } from '#shared/android'

const config = useRuntimeConfig()
const apkUrl = computed(() => String(config.public.androidApkUrl || DEFAULT_ANDROID_APK_URL))
const botUrl = 'https://t.me/ChtoZaVinoBot'
const title = 'Что за вино? — WebApp, Android и Telegram'
const description = 'Три способа узнать российское вино по фото: веб-приложение, Android без интернета — даже на парковке — и Telegram-бот.'

useSeoMeta({
  title,
  description,
  robots: 'noindex, nofollow, noarchive',
  ogType: 'website',
  ogTitle: title,
  ogDescription: description,
  ogUrl: 'https://chtozavino.ru/hackaton',
  ogImage: 'https://chtozavino.ru/screenshots/hackaton/web-desktop.jpg',
  ogImageAlt: 'Веб-приложение «Что за вино?» на компьютере',
  twitterCard: 'summary_large_image',
  twitterTitle: title,
  twitterDescription: description,
  twitterImage: 'https://chtozavino.ru/screenshots/hackaton/web-desktop.jpg',
})
useHead({ link: [{ rel: 'canonical', href: 'https://chtozavino.ru/hackaton' }] })
</script>

<template>
  <main id="main-content" class="hackaton-page">
    <section class="hackaton-hero" aria-labelledby="hackaton-title">
      <p class="eyebrow"><span />ПРОЕКТ ДЛЯ ХАКАТОНА · ЧТО ЗА ВИНО?</p>
      <h1 id="hackaton-title">Одно фото.<br><span>Три способа узнать вино.</span></h1>
      <p class="hero-copy">В браузере, без связи или прямо в чате.<br>Узнайте российское вино там, где удобно вам.</p>
      <nav class="platform-nav" aria-label="Приложения проекта">
        <a href="#webapp"><AppIcon name="desktop" />WebApp<AppIcon name="chevron" /></a>
        <a href="#android-app"><AppIcon name="android" />Android App<AppIcon name="chevron" /></a>
        <a href="#telegram-bot"><AppIcon name="telegram" />Telegram Bot<AppIcon name="chevron" /></a>
      </nav>
      <div class="project-links"><NuxtLink class="presentation-link" to="/presentation"><AppIcon name="desktop" />Смотреть презентацию<AppIcon name="arrow-up-right" /></NuxtLink><NuxtLink class="presentation-link" to="/ideas"><AppIcon name="book" />Идеи за пределами распознавания<AppIcon name="arrow-up-right" /></NuxtLink></div>
    </section>

    <section id="webapp" class="platform-section web-section" aria-labelledby="webapp-title">
      <div class="section-copy">
        <p class="platform-label"><span>01</span><AppIcon name="desktop" />WEBAPP</p>
        <h2 id="webapp-title">Знакомство с вином.<br><em>В одном окне.</em></h2>
        <p class="section-description">Откройте сайт, загрузите фото этикетки и получите карточку вина. На большом экране и на телефоне — один привычный сервис.</p>
        <ul class="feature-list">
          <li><AppIcon name="check" />Фото с камеры или из галереи</li>
          <li><AppIcon name="check" />Название и карточка на «Свое Вино»</li>
          <li><AppIcon name="check" />Без установки приложения</li>
        </ul>
        <NuxtLink class="button primary" to="/">Открыть WebApp<AppIcon name="arrow-up-right" /></NuxtLink>
        <p class="connection-note"><AppIcon name="info" />Для распознавания нужен интернет</p>
      </div>
      <div class="web-showcase" aria-label="Скриншоты WebApp на компьютере и телефоне">
        <figure class="desktop-preview">
          <div class="browser-bar" aria-hidden="true"><span class="browser-dots"><i /><i /><i /></span><span>chtozavino.ru</span><AppIcon name="shield" /></div>
          <a href="/screenshots/hackaton/web-desktop.jpg" target="_blank" rel="noopener noreferrer" aria-label="Открыть скриншот WebApp на компьютере в полном размере">
            <img src="/screenshots/hackaton/web-desktop.jpg" width="1920" height="1320" alt="WebApp на компьютере: загрузка фотографии слева и результат поиска справа" fetchpriority="high">
          </a>
          <figcaption><AppIcon name="desktop" />На компьютере</figcaption>
        </figure>
        <figure class="mobile-preview">
          <a class="phone-frame" href="/screenshots/hackaton/web-mobile.jpg" target="_blank" rel="noopener noreferrer" aria-label="Открыть скриншот WebApp на телефоне в полном размере">
            <img src="/screenshots/hackaton/web-mobile.jpg" width="1080" height="2160" alt="WebApp на телефоне: кнопки Сделать фото и Загрузить фото" decoding="async">
          </a>
          <figcaption><AppIcon name="phone" />На телефоне</figcaption>
        </figure>
      </div>
    </section>

    <section id="android-app" class="platform-section android-section" aria-labelledby="android-app-title">
      <div class="section-copy">
        <p class="platform-label"><span>02</span><AppIcon name="android" />ANDROID APP</p>
        <div class="offline-badge"><AppIcon name="offline" />РАБОТАЕТ БЕЗ ИНТЕРНЕТА</div>
        <h2 id="android-app-title">Связи нет.<br><em>Ответ есть.</em></h2>
        <p class="parking-callout">Даже на подземной парковке.</p>
        <p class="section-description">Сфотографируйте бутылку — приложение распознает её прямо на телефоне. Модели и каталог уже внутри: мобильная сеть и Wi-Fi не нужны.</p>
        <ul class="feature-list">
          <li><AppIcon name="check" />Распознавание фото на устройстве</li>
          <li><AppIcon name="check" />Поиск по QR-коду и штрихкоду</li>
          <li><AppIcon name="check" />Локальный каталог и история</li>
        </ul>
        <div class="platform-actions">
          <a class="button android-cta" :href="apkUrl" :download="ANDROID_RELEASE.apkFileName"><AppIcon name="download" />Скачать APK</a>
          <NuxtLink class="text-link" to="/android">О приложении<AppIcon name="arrow" /></NuxtLink>
        </div>
        <p class="release-note">Android {{ ANDROID_RELEASE.minAndroid }}+ · {{ ANDROID_RELEASE.apkDisplaySize }} · Тестовая версия {{ ANDROID_RELEASE.version }}</p>
        <p class="android-note">Установите приложение заранее. Интернет понадобится только для перехода на сайт «Свое Вино».</p>
      </div>
      <figure class="android-showcase">
        <div class="offline-orbit" aria-hidden="true" />
        <div class="parking-sign" aria-hidden="true">P<span>−2</span></div>
        <div class="android-phone phone-frame">
          <img src="/screenshots/android/04_recognition_result_dark.webp" width="1080" height="2199" alt="Реальный экран Android-приложения: результат распознавания Пино Нуар без интернета" loading="lazy" decoding="async">
        </div>
        <figcaption class="offline-caption"><AppIcon name="offline" /><span>Режим без связи<strong>Распознавание на телефоне</strong></span><AppIcon name="check" /></figcaption>
      </figure>
    </section>

    <section id="telegram-bot" class="platform-section telegram-section" aria-labelledby="telegram-title">
      <div class="section-copy">
        <p class="platform-label"><span>03</span><AppIcon name="telegram" />TELEGRAM BOT</p>
        <h2 id="telegram-title">Просто отправьте<br><em>фотографию в чат.</em></h2>
        <p class="section-description">Никаких новых привычек. Откройте бота в Telegram, отправьте фото вина и получите ответ в той же переписке.</p>
        <ul class="feature-list">
          <li><AppIcon name="check" />Одно фото или целый альбом</li>
          <li><AppIcon name="check" />Отдельный результат для каждого фото</li>
          <li><AppIcon name="check" />Название, производитель и ссылка на вино</li>
        </ul>
        <a class="button primary" :href="botUrl" target="_blank" rel="noopener noreferrer"><AppIcon name="telegram" />Открыть Telegram-бота<AppIcon name="arrow-up-right" /></a>
        <p class="connection-note">@ChtoZaVinoBot · Нужен интернет</p>
      </div>
      <figure class="telegram-showcase">
        <div class="chat-window">
          <div class="chat-header"><img src="/icons/product-logo.svg" width="44" height="44" alt=""><span><strong>Что за вино?</strong><small>@ChtoZaVinoBot</small></span><AppIcon name="telegram" /></div>
          <div class="chat-body">
            <div class="chat-message chat-outgoing"><AppIcon name="image" /><span>Фото этикетки<strong>Что за вино?</strong></span><AppIcon name="check" /></div>
            <div class="chat-message chat-incoming"><span class="chat-bottle"><AppIcon name="scan" /></span><strong>Узнаём вино по фотографии</strong><p>В ответе — фото бутылки, название, производитель, сорт винограда и ссылка на карточку.</p><span class="chat-result-link">Карточка на «Свое Вино»<AppIcon name="arrow-up-right" /></span></div>
          </div>
          <a class="chat-start" :href="botUrl" target="_blank" rel="noopener noreferrer">Начать знакомство<AppIcon name="arrow" /></a>
        </div>
        <figcaption>Пример сценария · Отправьте своё фото боту</figcaption>
      </figure>
    </section>

    <div class="hackaton-end"><AppIcon name="scan" /><p>Одна этикетка — и вино уже знакомо.</p><a href="#main-content">Наверх<AppIcon name="arrow-up-right" /></a></div>
  </main>
</template>

<style scoped>
.hackaton-page { width: calc(100% - 80px); max-width: 1240px; margin: 0 auto; }
.hackaton-hero { text-align: center; padding: 66px 0 54px; }
.hackaton-hero h1 { margin: 20px 0; font-size: clamp(42px, 5vw, 70px); line-height: 1.14; letter-spacing: -.045em; }
.hackaton-hero h1 span { color: var(--accent); }
.hero-copy { color: var(--muted); font-size: 17px; line-height: 1.7; }
.platform-nav { display: flex; justify-content: center; flex-wrap: wrap; gap: 10px; margin-top: 28px; }
.platform-nav a { display: inline-flex; align-items: center; gap: 10px; min-height: 46px; padding: 0 17px; border: 1px solid var(--line); border-radius: 28px; background: var(--paper); font-size: 13px; }
.platform-nav a:hover { background: var(--cream); border-color: var(--accent); }
.platform-nav .icon { width: 18px; height: 18px; color: var(--accent); }
.platform-nav .icon:last-child { width: 13px; height: 13px; margin-left: 5px; }
.presentation-link { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; margin-top: 12px; color: var(--accent); font-size: 12px; }
.project-links { display: flex; justify-content: center; flex-wrap: wrap; column-gap: 24px; }
.presentation-link .icon { width: 16px; height: 16px; }
.presentation-link:hover { text-decoration: underline; text-underline-offset: 4px; }
.platform-section { display: grid; grid-template-columns: 1fr 1.2fr; gap: 44px; align-items: center; padding: 54px; border: 1px solid var(--line); border-radius: 30px; margin-bottom: 24px; scroll-margin-top: 24px; }
.section-copy { position: relative; z-index: 1; min-width: 0; }
.platform-label { display: flex; align-items: center; gap: 10px; color: var(--accent); font-size: 11px; font-weight: 600; letter-spacing: .13em; margin-bottom: 25px; }
.platform-label > span { border-right: 1px solid currentColor; padding-right: 12px; opacity: .65; }
.platform-label .icon { width: 19px; height: 19px; }
.section-copy h2 { font-size: clamp(32px, 3.15vw, 44px); line-height: 1.18; letter-spacing: -.035em; }
.section-copy h2 em { color: var(--accent); font-style: normal; }
.section-description { color: var(--muted); font-size: 14px; line-height: 1.85; margin-top: 22px; max-width: 400px; }
.feature-list { list-style: none; padding: 0; margin: 24px 0 30px; display: grid; gap: 13px; font-size: 13px; line-height: 1.55; }
.feature-list li { display: flex; align-items: flex-start; gap: 10px; }
.feature-list .icon { width: 18px; height: 18px; color: var(--accent); margin-top: 1px; }
.section-copy .button { min-height: 50px; font-size: 13px; gap: 10px; }
.section-copy .button .icon { width: 18px; height: 18px; }
.connection-note { display: flex; align-items: center; gap: 6px; color: var(--muted); font-size: 11px; line-height: 1.6; margin-top: 14px; }
.connection-note .icon { width: 14px; height: 14px; }
figure { margin: 0; min-width: 0; }
figcaption { display: flex; align-items: center; justify-content: center; gap: 6px; color: var(--muted); font-size: 10px; margin-top: 13px; line-height: 1.5; }
figcaption .icon { width: 14px; height: 14px; }
.web-section { background: var(--cream); grid-template-columns: .85fr 1.3fr; gap: 30px; overflow: hidden; }
.web-showcase { position: relative; padding: 18px 66px 87px 0; }
.desktop-preview { transform: rotate(-2deg); }
.browser-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; background: #f7f4ef; color: #7a756e; border: 1px solid #d8d3cc; border-bottom: 0; border-radius: 12px 12px 0 0; padding: 10px 12px; font-size: 9px; }
.browser-bar .icon { width: 11px; height: 11px; }
.browser-dots { display: flex; gap: 4px; }
.browser-dots i { width: 5px; height: 5px; border-radius: 50%; background: #c7bfb6; }
.desktop-preview a { display: block; overflow: hidden; border: 1px solid #d8d3cc; border-radius: 0 0 9px 9px; box-shadow: 0 18px 45px #39251c15; }
.desktop-preview img { width: 100%; height: auto; }
.phone-frame { display: block; border: 6px solid #302c29; border-radius: 27px; overflow: hidden; background: #fefdfa; box-shadow: 0 18px 40px #1b151524; }
.phone-frame img { width: 100%; height: auto; }
.mobile-preview { position: absolute; width: 31%; right: -10px; top: 108px; transform: rotate(3deg); }
.mobile-preview .phone-frame { border-width: 5px; border-radius: 22px; }
.android-section { position: relative; overflow: hidden; background: #243b33; border-color: #243b33; color: #f9f7ef; grid-template-columns: 1fr 1fr; }
.android-section .platform-label, .android-section h2 em, .android-section .feature-list .icon { color: #c5dbb1; }
.android-section .section-description { color: #d1dbd4; }
.offline-badge { display: inline-flex; align-items: center; gap: 8px; padding: 8px 11px; margin-bottom: 20px; border: 1px solid #7b9c8166; border-radius: 6px; color: #d4e9c2; background: #b8d2a30c; font-size: 9px; font-weight: 600; letter-spacing: .1em; }
.offline-badge .icon { width: 15px; height: 15px; }
.android-section h2 { font-size: clamp(40px, 4vw, 56px); }
.parking-callout { margin-top: 16px; font-size: 18px; color: #e0ebd8; }
.android-section .section-description { margin-top: 14px; }
.platform-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 22px; }
.android-cta { background: #d8e8c5; color: #243b33; }
.android-cta:hover { background: #e7f2da; }
.text-link { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; font-size: 12px; }
.text-link:hover { text-decoration: underline; text-underline-offset: 4px; }
.text-link .icon { width: 17px; height: 17px; }
.release-note { font-size: 11px; line-height: 1.7; margin-top: 16px; color: #d1dbd4; }
.android-note { color: #b4c6ba; font-size: 11px; line-height: 1.7; max-width: 355px; margin-top: 8px; }
.android-showcase { position: relative; display: flex; align-items: center; justify-content: center; padding: 4px 0 26px; }
.android-phone { z-index: 1; width: 245px; transform: rotate(4deg); border-color: #172820; box-shadow: 0 25px 50px #0b1b235c; }
.offline-orbit { position: absolute; width: 370px; height: 370px; max-width: 100%; border-radius: 50%; border: 1px solid #b8d2a324; box-shadow: 0 0 0 42px #b8d2a308, 0 0 0 84px #b8d2a304; }
.parking-sign { position: absolute; top: 38px; left: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; width: 85px; height: 108px; border: 1px solid #a2b7a343; border-radius: 12px; font-size: 45px; font-weight: 300; color: #a9bead; transform: rotate(-8deg); }
.parking-sign span { font-size: 13px; border-top: 1px solid #a2b7a343; margin-top: 4px; padding-top: 4px; width: 45px; text-align: center; }
.offline-caption { position: absolute; z-index: 2; bottom: 6px; left: 50%; transform: translateX(-50%); display: flex; justify-content: flex-start; gap: 12px; width: max-content; max-width: 100%; padding: 15px 19px; border: 1px solid #d5e0c7; border-radius: 12px; color: #263d33; background: #eef3e6; box-shadow: 0 10px 30px #0b1b2326; }
.offline-caption .icon { width: 23px; height: 23px; }
.offline-caption .icon:last-child { margin-left: 8px; width: 19px; }
.offline-caption span { display: grid; gap: 3px; font-size: 10px; }
.offline-caption strong { font-size: 12px; font-weight: 600; }
.android-section a:focus-visible { outline-color: #d8e8c5; }
.telegram-section { background: var(--paper); }
.telegram-showcase { padding: 10px 26px; }
.chat-window { max-width: 360px; margin: auto; border: 1px solid var(--line); border-radius: 22px; overflow: hidden; background: var(--cream); box-shadow: 0 14px 40px #39251c09; }
.chat-header { display: flex; align-items: center; gap: 10px; padding: 18px; background: var(--paper); border-bottom: 1px solid var(--line); }
.chat-header img { border-radius: 12px; }
.chat-header > span { display: grid; gap: 4px; }
.chat-header strong { font-size: 14px; font-weight: 600; }
.chat-header small { color: var(--muted); font-size: 10px; }
.chat-header > .icon { color: var(--accent); margin-left: auto; }
.chat-body { padding: 22px 18px; }
.chat-message { border: 1px solid var(--line); padding: 16px; font-size: 12px; line-height: 1.7; }
.chat-outgoing { display: flex; align-items: center; gap: 12px; width: 85%; margin-left: auto; margin-bottom: 18px; border-radius: 14px 14px 3px 14px; background: var(--tag); }
.chat-outgoing > .icon:first-child { width: 32px; height: 32px; color: var(--accent); }
.chat-outgoing span { display: grid; font-size: 10px; color: var(--muted); }
.chat-outgoing strong { font-size: 12px; color: var(--ink); }
.chat-outgoing > .icon:last-child { width: 13px; margin: auto 0 0 auto; color: var(--accent); }
.chat-incoming { width: 93%; border-radius: 14px 14px 14px 3px; background: var(--paper); }
.chat-bottle { display: grid; place-items: center; width: 46px; height: 46px; border-radius: 50%; margin-bottom: 12px; background: var(--cream); color: var(--accent); }
.chat-bottle .icon { width: 27px; height: 27px; }
.chat-incoming strong { font-size: 13px; font-weight: 600; }
.chat-incoming p { margin-top: 8px; color: var(--muted); }
.chat-result-link { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--line); color: var(--accent); font-size: 10px; }
.chat-result-link .icon { width: 15px; height: 15px; }
.chat-start { display: flex; justify-content: center; align-items: center; gap: 10px; background: var(--paper); border-top: 1px solid var(--line); color: var(--accent); padding: 16px; font-size: 12px; }
.chat-start:hover { background: var(--tag); }
.chat-start .icon { width: 16px; height: 16px; }
.hackaton-end { display: flex; justify-content: center; align-items: center; gap: 14px; padding: 28px 0 8px; color: var(--muted); }
.hackaton-end > .icon { color: var(--accent); }
.hackaton-end p { font: 20px 'Playfair Display', Georgia, serif; }
.hackaton-end a { display: inline-flex; align-items: center; gap: 6px; min-height: 44px; margin-left: auto; font-size: 11px; }
.hackaton-end a:hover { color: var(--accent); }
.hackaton-end a .icon { width: 16px; height: 16px; }
@media (max-width: 1100px) {
  .platform-section { padding: 36px; gap: 25px; }
  .web-section { grid-template-columns: 1fr 1.15fr; }
  .web-showcase { padding-right: 45px; }
  .mobile-preview { width: 35%; top: 85px; }
  .telegram-showcase { padding: 0; }
  .parking-sign { left: -12px; }
}
@media (max-width: 850px) {
  .hackaton-page { width: calc(100% - 40px); }
  .platform-section { grid-template-columns: 1fr; padding: 36px; gap: 36px; }
  .section-description { max-width: 100%; }
  .section-copy h2 { font-size: 40px; }
  .web-showcase { width: 100%; max-width: 560px; margin: 0 auto; padding: 0 75px 65px 0; }
  .mobile-preview { width: 29%; right: 0; top: 55px; }
  .android-showcase { width: 100%; max-width: 400px; margin: 0 auto; }
  .parking-sign { left: 0; }
  .telegram-showcase { width: 100%; }
}
@media (max-width: 540px) {
  .hackaton-page { width: calc(100% - 32px); }
  .hackaton-hero { padding: 42px 0 32px; }
  .hackaton-hero .eyebrow { font-size: 8px; letter-spacing: .1em; }
  .hackaton-hero h1 { font-size: clamp(34px, 8.5vw, 46px); margin: 17px 0; }
  .hero-copy { font-size: 13px; }
  .platform-nav { gap: 7px; margin-top: 23px; }
  .platform-nav a { gap: 6px; padding: 0 10px; min-height: 44px; font-size: 10px; }
  .platform-nav .icon { width: 15px; height: 15px; }
  .platform-nav .icon:last-child { display: none; }
  .platform-section { padding: 28px 22px; border-radius: 23px; margin-bottom: 16px; gap: 28px; }
  .platform-label { margin-bottom: 20px; font-size: 10px; }
  .section-copy h2 { font-size: 32px; }
  .section-description { font-size: 13px; margin-top: 17px; }
  .feature-list { font-size: 12px; margin: 21px 0 24px; gap: 11px; }
  .section-copy .button { font-size: 12px; padding-left: 18px; padding-right: 18px; }
  .web-showcase { display: grid; grid-template-columns: 1fr .48fr; align-items: center; gap: 12px; padding: 7px 0 0; }
  .desktop-preview, .mobile-preview { position: static; width: auto; transform: none; }
  .browser-bar { padding: 6px; font-size: 6px; gap: 4px; border-radius: 7px 7px 0 0; }
  .browser-dots { gap: 2px; }
  .browser-dots i { width: 3px; height: 3px; }
  .browser-bar .icon { width: 8px; height: 8px; }
  .mobile-preview .phone-frame { border-width: 3px; border-radius: 12px; }
  figcaption { font-size: 9px; gap: 4px; margin-top: 9px; }
  figcaption .icon { width: 12px; height: 12px; }
  .android-section h2 { font-size: 43px; }
  .parking-callout { font-size: 16px; }
  .platform-actions { gap: 8px 17px; }
  .android-phone { width: 210px; }
  .parking-sign { width: 60px; height: 82px; font-size: 34px; top: 20px; left: -8px; }
  .parking-sign span { width: 34px; font-size: 10px; }
  .offline-caption { padding: 12px; gap: 8px; }
  .offline-caption strong { font-size: 10px; }
  .offline-caption span { font-size: 9px; }
  .offline-caption .icon:last-child { margin-left: 0; }
  .chat-body { padding: 18px 12px; }
  .chat-message { padding: 13px; }
  .chat-header { padding: 14px; }
  .chat-outgoing { width: 90%; }
  .chat-incoming { width: 95%; }
  .hackaton-end { flex-wrap: wrap; gap: 8px; padding-top: 18px; }
  .hackaton-end p { font-size: 15px; }
  .hackaton-end a { margin: 0; width: 100%; justify-content: center; }
}
</style>
