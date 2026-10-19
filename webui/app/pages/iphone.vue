<script setup lang="ts">
const releaseIssueUrl = 'https://github.com/s1mb1o/svoe-vino-lab-dev/issues/36'
const pageTitle = 'Что за вино? для iPhone — распознавание на устройстве'
const pageDescription = 'Нативное приложение для iPhone определяет российское вино по фотографии, QR-коду или штрихкоду. Core ML и каталог работают без интернета.'

useSeoMeta({
  title: pageTitle,
  description: pageDescription,
  ogType: 'website',
  ogTitle: pageTitle,
  ogDescription: pageDescription,
  ogUrl: 'https://chtozavino.ru/iphone',
  ogImage: 'https://chtozavino.ru/screenshots/iphone/01-main.webp',
  ogImageAlt: 'Главный экран приложения Что за вино? на iPhone',
  twitterCard: 'summary_large_image',
  twitterTitle: pageTitle,
  twitterDescription: pageDescription,
  twitterImage: 'https://chtozavino.ru/screenshots/iphone/01-main.webp',
})

useHead({
  link: [{ rel: 'canonical', href: 'https://chtozavino.ru/iphone' }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'SoftwareApplication',
      name: 'Что за вино?',
      operatingSystem: 'iOS 17.2 и новее',
      applicationCategory: 'LifestyleApplication',
      description: pageDescription,
      inLanguage: 'ru',
      offers: { '@type': 'Offer', price: '0', priceCurrency: 'RUB' },
    }),
  }],
})

const benefits = [
  { icon: 'offline', title: 'Работает без сети', copy: 'Модели, изображения и каталог из 2 093 вин находятся на iPhone. Интернет нужен только для перехода на портал.' },
  { icon: 'shield', title: 'Фото остаётся на iPhone', copy: 'Сегментация, создание вектора и поиск выполняются локально. Приложение не отправляет снимок на сервер.' },
  { icon: 'barcode', title: 'Фото, QR и штрихкод', copy: 'Используйте камеру, галерею, сканер кода или ручной ввод. Результат сохраняется в локальной истории.' },
  { icon: 'cpu', title: 'Core ML и Neural Engine', copy: 'Режим «Авто» выбирает доступный ускоритель. Отдельный режим «ANE» запрашивает CPU и Neural Engine.' },
]

const pipeline = [
  { number: '01', icon: 'camera', title: 'Снимок', copy: 'Сделайте фотографию бутылки или выберите её в медиатеке.' },
  { number: '02', icon: 'scan', title: 'Сегментация', copy: 'DIS или YOLO26n-seg отделяет бутылку от фона.' },
  { number: '03', icon: 'cpu', title: 'Вектор', copy: 'SigLIP2 Base NaFlex p512 описывает изображение 768 значениями.' },
  { number: '04', icon: 'search', title: 'Совпадения', copy: 'Локальный индекс сравнивает вектор с каталогом из 2 093 вин.' },
]

const accessibilityFeatures = [
  'VoiceOver ведёт от выбора фото к результатам',
  'Все размеры Dynamic Type, включая самые крупные',
  'Voice Control и Switch Control',
  'Reduce Motion и Reduce Transparency',
  'Кнопки и ссылки с областью нажатия не менее 44 pt',
  'Состояния обозначены текстом и символом, а не только цветом',
]
</script>

<template>
  <main id="main-content" class="iphone-page">
    <section class="iphone-hero" aria-labelledby="iphone-title">
      <div class="iphone-hero-copy">
        <p class="iphone-kicker"><AppIcon name="phone" />ПРИЛОЖЕНИЕ ДЛЯ IPHONE</p>
        <h1 id="iphone-title">Вино в кадре.<br><span>Ответ на iPhone.</span></h1>
        <p class="iphone-lead">Сфотографируйте бутылку, отсканируйте код или выберите снимок. Приложение найдёт похожие российские вина прямо на устройстве.</p>
        <div class="iphone-actions">
          <NuxtLink class="button primary" to="/"><AppIcon name="scan" />Открыть веб-сканер</NuxtLink>
          <a class="button secondary" :href="releaseIssueUrl" target="_blank" rel="noopener noreferrer"><AppIcon name="history" />Следить за TestFlight</a>
        </div>
        <ul class="iphone-release-facts" aria-label="Требования и статус">
          <li>iOS 17.2+</li>
          <li>Закрытая бета</li>
          <li>2 093 вина</li>
          <li>Бесплатно</li>
        </ul>
      </div>

      <div class="iphone-hero-visual" aria-label="Главный экран приложения на iPhone">
        <span class="hero-halo hero-halo-one" aria-hidden="true" />
        <span class="hero-halo hero-halo-two" aria-hidden="true" />
        <figure class="iphone-device hero-device">
          <img src="/screenshots/iphone/01-main.webp" width="1206" height="2622" alt="Главный экран приложения Что за вино? с действиями Камера, Галерея и Код">
        </figure>
        <div class="hero-note hero-note-offline"><AppIcon name="offline" /><span><strong>Без сети</strong>после установки</span></div>
        <div class="hero-note hero-note-private"><AppIcon name="shield" /><span><strong>На устройстве</strong>фото не загружается</span></div>
      </div>
    </section>

    <section class="iphone-section" aria-labelledby="benefits-title">
      <div class="iphone-heading">
        <p class="iphone-kicker"><span />НАТИВНО ДЛЯ IOS</p>
        <h2 id="benefits-title">Всё нужное уже <span>в телефоне</span></h2>
        <p>Приложение повторяет основные сценарии Android-версии и использует системные возможности iPhone.</p>
      </div>
      <div class="benefit-grid">
        <article v-for="benefit in benefits" :key="benefit.title" class="benefit-card">
          <span class="benefit-icon"><AppIcon :name="benefit.icon" /></span>
          <h3>{{ benefit.title }}</h3>
          <p>{{ benefit.copy }}</p>
        </article>
      </div>
    </section>

    <section class="iphone-section pipeline-section" aria-labelledby="pipeline-title">
      <div class="iphone-heading left">
        <p class="iphone-kicker"><span />ОДИН ЛОКАЛЬНЫЙ КОНВЕЙЕР</p>
        <h2 id="pipeline-title">От фотографии до <span>списка вин</span></h2>
        <p>Каждый этап выполняется на iPhone. Полная карточка вина открывается на портале и требует интернет.</p>
      </div>
      <ol class="pipeline-list">
        <li v-for="(step, index) in pipeline" :key="step.number" class="pipeline-card">
          <span class="pipeline-number">{{ step.number }}</span>
          <span class="pipeline-icon"><AppIcon :name="step.icon" /></span>
          <h3>{{ step.title }}</h3>
          <p>{{ step.copy }}</p>
          <AppIcon v-if="index < pipeline.length - 1" class="pipeline-arrow" name="arrow" />
        </li>
      </ol>
    </section>

    <section class="iphone-section technology-section" aria-labelledby="technology-title">
      <div class="technology-copy">
        <p class="iphone-kicker"><span />CORE ML</p>
        <h2 id="technology-title">Выберите точность.<br><span>iPhone выберет ускоритель.</span></h2>
        <p>По умолчанию приложение использует SigLIP2 Base NaFlex p512. В настройках доступны DIS и YOLO26n-seg, три энкодера и режимы «Авто», «ANE» и «CPU».</p>
        <dl class="technology-facts">
          <div><dt>Энкодер по умолчанию</dt><dd>NaFlex p512</dd></div>
          <div><dt>Размер вектора</dt><dd>768</dd></div>
          <div><dt>Тёплый поиск</dt><dd>11 мс</dd></div>
          <div><dt>Минимальная версия</dt><dd>iOS 17.2</dd></div>
        </dl>
        <p class="measurement-note"><AppIcon name="info" />11 мс — время поиска по локальному индексу в симуляторе iPhone 17 Pro. Neural Engine в симуляторе недоступен. Проверка скорости на физическом iPhone ещё нужна.</p>
      </div>
      <figure class="settings-figure">
        <div class="iphone-device settings-device">
          <img src="/screenshots/iphone/02-settings.webp" width="1206" height="2622" alt="Настройки iPhone-приложения с выбором DIS или YOLO, энкодера и режима Авто, ANE или CPU" loading="lazy">
        </div>
        <figcaption>Реальный экран настроек · iPhone 17 Pro Simulator</figcaption>
      </figure>
    </section>

    <section class="iphone-section accessibility-section" aria-labelledby="accessibility-title">
      <div class="accessibility-copy">
        <p class="iphone-kicker"><AppIcon name="check" />ДОСТУПНОСТЬ</p>
        <h2 id="accessibility-title">Управление, которое следует <span>настройкам iPhone</span></h2>
        <p>Основные сценарии проверены автоматическими аудитами доступности на iPhone 17 Pro Simulator с iOS 26.2.</p>
        <div class="test-receipt"><span>12</span> модульных тестов <i /> <span>6</span> UI-тестов доступности</div>
      </div>
      <ul class="accessibility-list">
        <li v-for="feature in accessibilityFeatures" :key="feature"><span><AppIcon name="check" /></span>{{ feature }}</li>
      </ul>
    </section>

    <section class="iphone-final" aria-labelledby="beta-title">
      <div>
        <p class="iphone-kicker"><AppIcon name="phone" />IPHONE · IOS 17.2 И НОВЕЕ</p>
        <h2 id="beta-title">Нативная версия готова.<br><span>Следующий шаг — TestFlight.</span></h2>
        <p>Разработка и проверка в симуляторе завершены. Для удалённой установки нужен подписанный выпуск в Apple Developer и приглашение TestFlight.</p>
      </div>
      <div class="final-actions">
        <a class="button primary" :href="releaseIssueUrl" target="_blank" rel="noopener noreferrer">Следить за выпуском<AppIcon name="arrow-up-right" /></a>
        <NuxtLink class="final-web-link" to="/">Открыть веб-сканер сейчас<AppIcon name="arrow" /></NuxtLink>
      </div>
    </section>
  </main>
</template>

<style scoped>
.iphone-page { max-width: 1240px; width: calc(100% - 80px); margin: 0 auto; padding: 42px 0 20px; }
.iphone-hero { min-height: 700px; display: grid; grid-template-columns: .96fr 1.04fr; gap: 54px; align-items: center; padding: 54px 62px; overflow: hidden; position: relative; border: 1px solid var(--line); border-radius: 34px; background: linear-gradient(138deg, var(--paper) 0 43%, var(--cream) 100%); box-shadow: 0 20px 70px #5638200b; }
.iphone-hero-copy { position: relative; z-index: 4; }
.iphone-kicker { display: inline-flex; align-items: center; gap: 9px; color: var(--accent); font-size: 10px; font-weight: 600; letter-spacing: .15em; }
.iphone-kicker>span { width: 18px; height: 1px; background: currentColor; }
.iphone-kicker .icon { width: 18px; height: 18px; }
.iphone-hero h1 { max-width: 620px; margin: 18px 0 22px; font-size: clamp(50px, 5.3vw, 76px); line-height: 1.06; letter-spacing: -.052em; }
.iphone-hero h1 span, .iphone-heading h2 span, .technology-copy h2 span, .accessibility-copy h2 span, .iphone-final h2 span { color: var(--accent); }
.iphone-lead { max-width: 555px; color: var(--muted); font-size: 17px; line-height: 1.72; }
.iphone-actions { display: flex; flex-wrap: wrap; gap: 11px; margin-top: 31px; }
.iphone-actions .button { width: auto; min-height: 54px; padding-inline: 24px; }
.iphone-release-facts { display: flex; flex-wrap: wrap; gap: 7px; margin: 21px 0 0; padding: 0; list-style: none; }
.iphone-release-facts li { padding: 7px 10px; border: 1px solid var(--line); border-radius: 18px; background: var(--paper); color: var(--muted); font-size: 10px; }
.iphone-hero-visual { min-height: 590px; position: relative; display: grid; place-items: center; }
.iphone-device { position: relative; overflow: hidden; border: 8px solid #1f1d1c; border-radius: 48px; background: #fff; box-shadow: 0 30px 60px #3d251c2d; }
.iphone-device img { width: 100%; height: 100%; object-fit: cover; object-position: top; }
.hero-device { z-index: 2; width: 274px; aspect-ratio: 1206 / 2622; transform: rotate(3.5deg); }
.hero-halo { position: absolute; border: 1px solid color-mix(in srgb, var(--accent) 23%, transparent); border-radius: 50%; }
.hero-halo-one { width: 530px; height: 530px; }
.hero-halo-two { width: 395px; height: 395px; }
.hero-note { position: absolute; z-index: 3; display: flex; align-items: center; gap: 10px; padding: 13px 15px; border: 1px solid var(--line); border-radius: 15px; background: color-mix(in srgb, var(--paper) 93%, transparent); box-shadow: 0 14px 34px #3d251c1b; backdrop-filter: blur(12px); color: var(--muted); font-size: 9px; line-height: 1.4; }
.hero-note .icon { width: 22px; height: 22px; color: var(--accent); }
.hero-note span { display: flex; flex-direction: column; }
.hero-note strong { color: var(--ink); font-size: 11px; font-weight: 600; }
.hero-note-offline { left: 3%; top: 24%; }
.hero-note-private { right: 1%; bottom: 21%; }
.iphone-section { margin-top: 96px; }
.iphone-heading { max-width: 760px; margin: 0 auto 36px; text-align: center; }
.iphone-heading.left { max-width: 720px; margin-left: 0; text-align: left; }
.iphone-heading h2, .technology-copy h2, .accessibility-copy h2, .iphone-final h2 { margin: 14px 0; font-size: clamp(38px, 4.2vw, 58px); line-height: 1.13; letter-spacing: -.035em; }
.iphone-heading>p:last-child, .technology-copy>p, .accessibility-copy>p, .iphone-final>div>p:last-child { color: var(--muted); font-size: 14px; line-height: 1.75; }
.benefit-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 13px; }
.benefit-card { min-height: 250px; padding: 25px; border: 1px solid var(--line); border-radius: 21px; background: var(--paper); transition: transform .2s, border-color .2s; }
.benefit-card:hover { transform: translateY(-3px); border-color: color-mix(in srgb, var(--accent) 50%, var(--line)); }
.benefit-icon { width: 48px; height: 48px; display: grid; place-items: center; border-radius: 15px; background: var(--cream); color: var(--accent); }
.benefit-icon .icon { width: 24px; height: 24px; }
.benefit-card h3 { margin: 24px 0 9px; font: 500 20px/1.3 'Playfair Display', Georgia, serif; }
.benefit-card p { color: var(--muted); font-size: 12px; line-height: 1.65; }
.pipeline-section { padding: 56px clamp(30px, 5vw, 64px) 62px; border: 1px solid var(--line); border-radius: 34px; background: var(--paper); }
.pipeline-list { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 35px 0 0; padding: 0; list-style: none; }
.pipeline-card { min-height: 250px; position: relative; padding: 24px; border-radius: 21px; background: var(--cream); }
.pipeline-number { color: color-mix(in srgb, var(--accent) 60%, var(--muted)); font: 500 22px/1 'Playfair Display', Georgia, serif; }
.pipeline-icon { width: 52px; height: 52px; display: grid; place-items: center; margin-top: 28px; border-radius: 17px; color: var(--accent); background: var(--paper); }
.pipeline-icon .icon { width: 25px; height: 25px; }
.pipeline-card h3 { margin: 20px 0 8px; font: 500 21px/1.25 'Playfair Display', Georgia, serif; }
.pipeline-card p { color: var(--muted); font-size: 11px; line-height: 1.65; }
.pipeline-arrow { position: absolute; z-index: 2; width: 22px; height: 22px; right: -17px; top: 50%; padding: 5px; border-radius: 50%; color: var(--accent); background: var(--paper); transform: translateY(-50%); box-sizing: content-box; }
.technology-section { display: grid; grid-template-columns: 1.18fr minmax(300px, .82fr); gap: clamp(48px, 7vw, 100px); align-items: center; padding: 60px clamp(40px, 7vw, 92px); border-radius: 34px; background: var(--cream); }
.technology-copy h2 { font-size: clamp(40px, 4.5vw, 62px); }
.technology-facts { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; margin: 30px 0 0; overflow: hidden; border: 1px solid var(--line); border-radius: 17px; background: var(--line); }
.technology-facts div { padding: 17px; background: var(--paper); }
.technology-facts dt { color: var(--muted); font-size: 9px; letter-spacing: .08em; text-transform: uppercase; }
.technology-facts dd { margin: 7px 0 0; color: var(--accent); font: 500 19px/1.2 'Playfair Display', Georgia, serif; }
.measurement-note { display: flex; align-items: flex-start; gap: 8px; margin-top: 20px; font-size: 10px !important; line-height: 1.6 !important; }
.measurement-note .icon { width: 16px; height: 16px; margin-top: 1px; flex-shrink: 0; color: var(--accent); }
.settings-figure { margin: 0; text-align: center; }
.settings-device { width: 310px; aspect-ratio: 1206 / 2622; margin: 0 auto; }
.settings-figure figcaption { margin-top: 15px; color: var(--muted); font-size: 9px; line-height: 1.5; }
.accessibility-section { display: grid; grid-template-columns: 1fr 1fr; gap: clamp(42px, 7vw, 92px); align-items: center; padding: 58px clamp(38px, 7vw, 84px); border-radius: 34px; color: #f8efe8; background: radial-gradient(circle at 82% 12%, #c47f5940, transparent 35%), #54251f; }
.accessibility-section .iphone-kicker, .accessibility-section h2 span { color: #efb49c; }
.accessibility-copy>p { color: #e0c9bd; }
.test-receipt { display: flex; align-items: baseline; flex-wrap: wrap; gap: 7px; margin-top: 25px; color: #dfc5b8; font-size: 10px; }
.test-receipt span { color: #f5d2c0; font: 500 28px/1 'Playfair Display', Georgia, serif; }
.test-receipt i { width: 1px; height: 18px; margin: 0 5px; background: #ffffff2e; }
.accessibility-list { display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; }
.accessibility-list li { display: grid; grid-template-columns: 34px 1fr; align-items: center; gap: 12px; min-height: 54px; padding: 8px 14px 8px 10px; border: 1px solid #ffffff1c; border-radius: 15px; background: #ffffff0b; color: #ead8cf; font-size: 12px; line-height: 1.5; }
.accessibility-list li>span { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 50%; color: #f1c1aa; background: #ffffff10; }
.accessibility-list .icon { width: 17px; height: 17px; }
.iphone-final { min-height: 310px; display: grid; grid-template-columns: 1.1fr .9fr; align-items: center; gap: 48px; margin: 96px 0 42px; padding: 50px clamp(38px, 7vw, 84px); border: 1px solid var(--line); border-radius: 32px; background: var(--paper); }
.final-actions { display: grid; gap: 16px; text-align: center; }
.final-actions .button { width: 100%; min-height: 58px; font-size: 13px; }
.final-web-link { display: inline-flex; align-items: center; justify-content: center; gap: 8px; color: var(--accent); font-size: 12px; }
.final-web-link:hover { text-decoration: underline; text-underline-offset: 4px; }
.final-web-link .icon { width: 17px; height: 17px; }
:global(:root[data-theme='dark'] .iphone-hero) { box-shadow: none; }
:global(:root[data-theme='dark'] .iphone-device) { border-color: #4a4544; }
:global(:root[data-theme='dark'] .hero-note) { background: color-mix(in srgb, var(--paper) 88%, transparent); }
:global(:root[data-theme='dark'] .benefit-card:hover) { border-color: #8e715f; }
@media (max-width: 1023px) {
  .iphone-page { width: calc(100% - 48px); }
  .iphone-hero { grid-template-columns: 1fr; padding: 48px; }
  .iphone-hero-copy { max-width: 700px; }
  .iphone-hero-visual { width: min(610px, 100%); margin: 0 auto; }
  .benefit-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .pipeline-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .pipeline-arrow { display: none; }
  .technology-section { gap: 44px; padding: 48px; }
  .settings-device { width: 280px; }
}
@media (max-width: 767px) {
  .iphone-page { width: calc(100% - 32px); padding-top: 28px; }
  .iphone-hero { min-height: 0; padding: 32px 22px 38px; border-radius: 25px; }
  .iphone-hero h1 { font-size: clamp(42px, 13vw, 59px); }
  .iphone-lead { font-size: 14px; }
  .iphone-actions { flex-direction: column; }
  .iphone-actions .button { width: 100%; }
  .iphone-hero-visual { min-height: 520px; margin-top: 16px; }
  .hero-device { width: 220px; }
  .hero-halo-one { width: 410px; height: 410px; }
  .hero-halo-two { width: 310px; height: 310px; }
  .hero-note { padding: 10px; }
  .hero-note-offline { left: -2%; top: 20%; }
  .hero-note-private { right: -2%; bottom: 17%; }
  .iphone-section { margin-top: 68px; }
  .iphone-heading { margin-bottom: 25px; }
  .iphone-heading h2, .technology-copy h2, .accessibility-copy h2, .iphone-final h2 { font-size: 37px; }
  .benefit-grid { grid-template-columns: 1fr; gap: 10px; }
  .benefit-card { min-height: 0; padding: 20px; display: grid; grid-template-columns: 48px 1fr; column-gap: 16px; }
  .benefit-card h3 { margin: 2px 0 7px; }
  .benefit-card p { grid-column: 2; }
  .pipeline-section { padding: 34px 22px; border-radius: 25px; }
  .pipeline-list { grid-template-columns: 1fr; }
  .pipeline-card { min-height: 0; display: grid; grid-template-columns: 40px 48px 1fr; column-gap: 12px; align-items: center; padding: 18px; }
  .pipeline-number { font-size: 18px; }
  .pipeline-icon { width: 48px; height: 48px; margin: 0; }
  .pipeline-card h3 { margin: 0; }
  .pipeline-card p { grid-column: 3; margin-top: 6px; }
  .technology-section { grid-template-columns: 1fr; padding: 34px 22px; border-radius: 25px; }
  .technology-facts { grid-template-columns: 1fr; }
  .settings-device { width: min(290px, 94%); }
  .accessibility-section { grid-template-columns: 1fr; gap: 30px; padding: 36px 23px; border-radius: 25px; }
  .iphone-final { grid-template-columns: 1fr; gap: 28px; margin-top: 68px; padding: 36px 23px; border-radius: 25px; }
}
@media (max-width: 400px) {
  .iphone-hero-visual { min-height: 470px; }
  .hero-device { width: 198px; }
  .hero-note { font-size: 8px; }
  .hero-note strong { font-size: 10px; }
  .hero-note .icon { width: 18px; height: 18px; }
  .iphone-release-facts li { font-size: 9px; }
}
@media (prefers-reduced-motion: reduce) {
  .benefit-card { transition: none; }
  .benefit-card:hover { transform: none; }
}
</style>
