<script setup lang="ts">
import { ANDROID_RELEASE, DEFAULT_ANDROID_APK_URL } from '#shared/android'

const runtimeConfig = useRuntimeConfig()
const apkUrl = computed(() => String(runtimeConfig.public.androidApkUrl || DEFAULT_ANDROID_APK_URL))
const pageTitle = 'Что за вино? для Android — распознавание без интернета'
const pageDescription = 'Определяйте российское вино по фотографии, QR-коду или штрихкоду. Каталог и модели работают на Android без интернета.'

useSeoMeta({
  title: pageTitle,
  description: pageDescription,
  ogType: 'website',
  ogTitle: pageTitle,
  ogDescription: pageDescription,
  ogUrl: 'https://chtozavino.ru/android',
  ogImage: 'https://chtozavino.ru/screenshots/android/03_bottle_selected_dark.webp',
  twitterCard: 'summary_large_image',
  twitterTitle: pageTitle,
  twitterDescription: pageDescription,
  twitterImage: 'https://chtozavino.ru/screenshots/android/03_bottle_selected_dark.webp',
})
useHead({
  link: [{ rel: 'canonical', href: 'https://chtozavino.ru/android' }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'SoftwareApplication',
      name: 'Что за вино?',
      operatingSystem: `Android ${ANDROID_RELEASE.minAndroid} и новее`,
      applicationCategory: 'LifestyleApplication',
      softwareVersion: ANDROID_RELEASE.version,
      fileSize: `${ANDROID_RELEASE.apkBytes} bytes`,
      downloadUrl: apkUrl.value,
      description: pageDescription,
      inLanguage: 'ru',
      offers: { '@type': 'Offer', price: '0', priceCurrency: 'RUB' },
    }),
  }],
})

const benefits = [
  { icon: 'offline', title: 'Работает без интернета', copy: 'Модели и каталог находятся на телефоне. Связь нужна только для открытия карточки на сайте.' },
  { icon: 'image', title: 'Поиск по изображению', copy: 'Сфотографируйте бутылку или выберите готовое изображение из галереи.' },
  { icon: 'barcode', title: 'QR и штрихкоды', copy: 'Сканер распознаёт QR и EAN-13. Найденный код проверяется в локальном каталоге.' },
  { icon: 'shield', title: 'Обработка на устройстве', copy: 'Сегментация, вектор и сравнение фотографии выполняются непосредственно на телефоне.' },
  { icon: 'book', title: '2 093 вина внутри', copy: 'Каталог, изображения и векторы устанавливаются вместе с приложением.' },
  { icon: 'cpu', title: 'Автоматический ускоритель', copy: 'Приложение проверяет совместимость и выбирает GPU или CPU отдельно для каждой модели.' },
  { icon: 'history', title: 'История результатов', copy: 'Успешные поиски сохраняются локально и остаются доступны после перезапуска.' },
  { icon: 'moon', title: 'Светлая и тёмная темы', copy: 'Интерфейс автоматически следует системной теме Android.' },
]

const recognitionSteps = [
  { number: '01', title: 'Добавьте фотографию', copy: 'Используйте камеру или галерею. Лучше всего работает снимок одной бутылки спереди.', image: '/screenshots/android/03_bottle_selected_dark.webp', alt: 'Бутылка Пино Нуар выбрана в приложении Что за вино' },
  { number: '02', title: 'Приложение выделит бутылку', copy: 'DIS отделяет объект, обрезает изображение и создаёт ровный белый фон.', image: '/screenshots/android/05_processing_pipeline_dark.webp', alt: 'Маска бутылки после локальной обработки DIS' },
  { number: '03', title: 'Получите совпадения', copy: 'SigLIP2 создаёт вектор, а локальный поиск сравнивает его со встроенным каталогом.', image: '/screenshots/android/04_recognition_result_dark.webp', alt: 'Результат распознавания Пино Нуар со сходством 91 процент' },
]
</script>

<template>
  <main id="main-content" class="android-page">
    <section class="android-hero" aria-labelledby="android-title">
      <div class="android-hero-copy">
        <p class="android-kicker"><AppIcon name="android" />ПРИЛОЖЕНИЕ ДЛЯ ANDROID</p>
        <h1 id="android-title">Узнайте вино.<br><span>Даже без интернета.</span></h1>
        <p class="android-lead">Наведите камеру на бутылку или выберите фотографию. Приложение найдёт похожие российские вина прямо на телефоне.</p>
        <div class="android-actions">
          <a class="button primary android-download" :href="apkUrl" :download="ANDROID_RELEASE.apkFileName" data-testid="android-download"><AppIcon name="download" /><span>Скачать для Android</span></a>
          <NuxtLink class="button secondary" to="/"><AppIcon name="scan" />Открыть веб-сканер</NuxtLink>
        </div>
        <ul class="android-release-facts" aria-label="Требования и версия">
          <li>Android {{ ANDROID_RELEASE.minAndroid }}+</li>
          <li>Версия {{ ANDROID_RELEASE.version }}</li>
          <li>{{ ANDROID_RELEASE.apkDisplaySize }}</li>
          <li>Бесплатно</li>
        </ul>
        <p class="android-test-note"><AppIcon name="info" />Тестовая версия подписана ключом разработчика. Android может запросить разрешение на установку APK из браузера.</p>
      </div>
      <div class="android-phones" aria-label="Светлая и тёмная темы приложения">
        <figure class="phone phone-light">
          <img src="/screenshots/android/02_bottle_selected_light.webp" width="1080" height="2199" alt="Главный экран приложения с бутылкой в светлой теме">
          <figcaption>Светлая тема</figcaption>
        </figure>
        <figure class="phone phone-dark">
          <img src="/screenshots/android/03_bottle_selected_dark.webp" width="1080" height="2199" alt="Главный экран приложения с бутылкой в тёмной теме">
          <figcaption>Тёмная тема</figcaption>
        </figure>
        <span class="hero-orbit hero-orbit-one" />
        <span class="hero-orbit hero-orbit-two" />
      </div>
    </section>

    <section class="android-section android-benefits" aria-labelledby="benefits-title">
      <div class="android-section-heading">
        <p class="android-kicker"><span />ПОИСК ВСЕГДА ПОД РУКОЙ</p>
        <h2 id="benefits-title">Всё необходимое уже <span>в приложении</span></h2>
        <p>После установки фотография проходит весь путь на телефоне: от выделения бутылки до сравнения с каталогом.</p>
      </div>
      <div class="benefit-grid">
        <article v-for="benefit in benefits" :key="benefit.title" class="benefit-card">
          <span class="benefit-icon"><AppIcon :name="benefit.icon" /></span>
          <h3>{{ benefit.title }}</h3>
          <p>{{ benefit.copy }}</p>
        </article>
      </div>
    </section>

    <section class="android-section recognition-story" aria-labelledby="recognition-title">
      <div class="android-section-heading left">
        <p class="android-kicker"><span />ПОИСК ПО ФОТОГРАФИИ</p>
        <h2 id="recognition-title">Три шага до <span>нужного вина</span></h2>
        <p>Пример ниже выполнен на Google Pixel 8. Приложение нашло «Пино Нуар» со сходством 91%.</p>
      </div>
      <div class="recognition-grid">
        <article v-for="step in recognitionSteps" :key="step.number" class="recognition-card">
          <div class="recognition-copy">
            <span>{{ step.number }}</span>
            <div><h3>{{ step.title }}</h3><p>{{ step.copy }}</p></div>
          </div>
          <div class="recognition-screen"><img :src="step.image" width="1080" height="2199" :alt="step.alt" loading="lazy"></div>
        </article>
      </div>
    </section>

    <section class="android-section code-search" aria-labelledby="code-title">
      <div class="code-screen phone">
        <img src="/screenshots/android/08_barcode_result_dark.webp" width="1080" height="2199" alt="Результат поиска вина по штрихкоду EAN-13" loading="lazy">
      </div>
      <div class="code-copy">
        <p class="android-kicker"><AppIcon name="barcode" />QR И ШТРИХКОДЫ</p>
        <h2 id="code-title">Сканируйте код — <span>без повторной фотографии</span></h2>
        <p>Google Code Scanner считывает QR или штрихкод. Приложение проверяет код во встроенном каталоге и сразу показывает карточку вина.</p>
        <div class="verified-code">
          <span class="verified-mark"><AppIcon name="check" /></span>
          <div><strong>Проверено на EAN-13</strong><p>Код 4630037250909 найден как «Шато Тамань. Каберне Совиньон» со сходством 100%.</p></div>
        </div>
        <ul class="code-points">
          <li><AppIcon name="check" />Поддержка ручного ввода кода</li>
          <li><AppIcon name="check" />Результат сохраняется в истории</li>
          <li><AppIcon name="check" />Переход к полной карточке на «Своё Вино»</li>
        </ul>
      </div>
    </section>

    <section class="android-section android-technology" aria-labelledby="technology-title">
      <div class="technology-copy">
        <p class="android-kicker"><span />ТЕХНОЛОГИИ НА УСТРОЙСТВЕ</p>
        <h2 id="technology-title">DIS выделяет объект.<br><span>SigLIP2 находит сходство.</span></h2>
        <p>При первом запуске приложение отдельно проверяет DIS и SigLIP2. Оно сохраняет безопасный режим GPU или CPU для каждой модели.</p>
        <dl class="technology-facts">
          <div><dt>Каталог</dt><dd>2 093 вина</dd></div>
          <div><dt>Вектор</dt><dd>768 значений</dd></div>
          <div><dt>Минимальная версия</dt><dd>Android 9</dd></div>
          <div><dt>Интернет для поиска</dt><dd>Не требуется</dd></div>
        </dl>
      </div>
      <div class="settings-preview phone">
        <img src="/screenshots/android/07_settings_dark.webp" width="1080" height="2199" alt="Настройки автоматического выбора GPU или CPU для моделей DIS и SigLIP2" loading="lazy">
      </div>
    </section>

    <section class="android-final" aria-labelledby="download-title">
      <div>
        <p class="android-kicker"><AppIcon name="android" />ANDROID {{ ANDROID_RELEASE.minAndroid }} И НОВЕЕ</p>
        <h2 id="download-title">Ваш винный каталог<br><span>всегда с вами</span></h2>
        <p>Скачайте тестовую версию {{ ANDROID_RELEASE.version }}. Для установки и распаковки встроенного каталога требуется не менее 1,5 ГБ свободного места.</p>
      </div>
      <div class="final-action">
        <a class="button primary android-download" :href="apkUrl" :download="ANDROID_RELEASE.apkFileName"><AppIcon name="download" />Скачать {{ ANDROID_RELEASE.apkFileName }}</a>
        <p>{{ ANDROID_RELEASE.apkDisplaySize }} · SHA-256 доступен в документации релиза</p>
      </div>
    </section>
  </main>
</template>

<style scoped>
.android-page { max-width: 1240px; width: calc(100% - 80px); margin: 0 auto; padding: 42px 0 20px; }
.android-hero { min-height: 690px; display: grid; grid-template-columns: .92fr 1.08fr; gap: 54px; align-items: center; padding: 52px 62px; overflow: hidden; position: relative; border: 1px solid var(--line); border-radius: 34px; background: linear-gradient(135deg, var(--paper) 0 44%, var(--cream) 100%); box-shadow: 0 20px 70px #5638200b; }
.android-hero-copy { position: relative; z-index: 2; }
.android-kicker { display: inline-flex; align-items: center; gap: 9px; color: var(--accent); font-size: 10px; font-weight: 600; letter-spacing: .15em; }
.android-kicker>span { width: 18px; height: 1px; background: currentColor; }
.android-kicker .icon { width: 18px; height: 18px; }
.android-hero h1 { max-width: 610px; margin: 18px 0 22px; font-size: clamp(50px, 5.3vw, 76px); line-height: 1.06; letter-spacing: -.052em; }
.android-hero h1 span, .android-section-heading h2 span, .code-copy h2 span, .technology-copy h2 span, .android-final h2 span { color: var(--accent); }
.android-lead { max-width: 540px; color: var(--muted); font-size: 17px; line-height: 1.72; }
.android-actions { display: flex; flex-wrap: wrap; gap: 11px; margin-top: 31px; }
.android-actions .button { width: auto; min-height: 54px; padding-inline: 24px; }
.android-download .icon { width: 20px; height: 20px; }
.android-release-facts { display: flex; flex-wrap: wrap; gap: 7px; margin: 21px 0 0; padding: 0; list-style: none; }
.android-release-facts li { padding: 7px 10px; border: 1px solid var(--line); border-radius: 18px; background: var(--paper); color: var(--muted); font-size: 10px; }
.android-test-note { display: flex; align-items: flex-start; gap: 8px; max-width: 520px; margin-top: 18px; color: var(--muted); font-size: 10px; line-height: 1.55; }
.android-test-note .icon { width: 16px; height: 16px; margin-top: 1px; color: var(--accent); }
.android-phones { min-height: 570px; position: relative; }
.phone { position: relative; overflow: hidden; border: 8px solid #2b2928; border-radius: 38px; background: #171416; box-shadow: 0 28px 55px #3d251c2e; }
.phone:before { content: ''; position: absolute; z-index: 3; top: 8px; left: 50%; width: 33%; height: 12px; border-radius: 0 0 12px 12px; background: #2b2928; transform: translateX(-50%); }
.phone img { width: 100%; height: 100%; object-fit: cover; object-position: top; }
.phone figcaption { position: absolute; z-index: 4; bottom: 10px; left: 50%; padding: 6px 10px; border-radius: 18px; background: #181417d9; color: #fff; font-size: 9px; transform: translateX(-50%); white-space: nowrap; }
.phone-light, .phone-dark { position: absolute; width: 258px; height: 525px; }
.phone-light { top: 32px; left: 4%; transform: rotate(-6deg); }
.phone-dark { z-index: 2; top: 6px; right: 4%; transform: rotate(5deg); }
.hero-orbit { position: absolute; border: 1px solid color-mix(in srgb, var(--accent) 24%, transparent); border-radius: 50%; }
.hero-orbit-one { width: 520px; height: 520px; top: 24px; left: 23px; }
.hero-orbit-two { width: 390px; height: 390px; top: 90px; left: 90px; }
.android-section { margin-top: 96px; }
.android-section-heading { max-width: 760px; margin: 0 auto 36px; text-align: center; }
.android-section-heading.left { max-width: 700px; margin-left: 0; text-align: left; }
.android-section-heading h2, .code-copy h2, .technology-copy h2, .android-final h2 { margin: 14px 0 14px; font-size: clamp(38px, 4.2vw, 58px); line-height: 1.13; letter-spacing: -.035em; }
.android-section-heading>p:last-child, .code-copy>p, .technology-copy>p, .android-final>div>p:last-child { color: var(--muted); font-size: 14px; line-height: 1.75; }
.benefit-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 13px; }
.benefit-card { min-height: 228px; padding: 25px; border: 1px solid var(--line); border-radius: 21px; background: var(--paper); transition: transform .2s, border-color .2s; }
.benefit-card:hover { transform: translateY(-3px); border-color: color-mix(in srgb, var(--accent) 50%, var(--line)); }
.benefit-icon { width: 48px; height: 48px; display: grid; place-items: center; border-radius: 15px; background: var(--cream); color: var(--accent); }
.benefit-icon .icon { width: 24px; height: 24px; }
.benefit-card h3 { margin: 24px 0 9px; font: 500 20px/1.3 'Playfair Display', Georgia, serif; }
.benefit-card p { color: var(--muted); font-size: 12px; line-height: 1.65; }
.recognition-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }
.recognition-card { overflow: hidden; border: 1px solid var(--line); border-radius: 24px; background: var(--cream); }
.recognition-copy { min-height: 142px; display: grid; grid-template-columns: 42px 1fr; gap: 14px; padding: 24px; }
.recognition-copy>span { color: var(--accent); font: 500 31px/1 'Playfair Display', Georgia, serif; }
.recognition-copy h3 { margin: 0 0 8px; font: 500 21px/1.25 'Playfair Display', Georgia, serif; }
.recognition-copy p { color: var(--muted); font-size: 11px; line-height: 1.62; }
.recognition-screen { height: 500px; overflow: hidden; margin: 0 12px 12px; border: 5px solid #2b2928; border-radius: 25px 25px 18px 18px; background: #171416; }
.recognition-screen img { width: 100%; height: 100%; object-fit: cover; object-position: top; }
.code-search, .android-technology { display: grid; grid-template-columns: minmax(300px, .78fr) 1.22fr; gap: clamp(48px, 7vw, 100px); align-items: center; padding: 62px clamp(40px, 7vw, 92px); border-radius: 34px; background: var(--cream); }
.code-screen, .settings-preview { width: 330px; height: 670px; justify-self: center; }
.code-copy h2, .technology-copy h2 { font-size: clamp(40px, 4.5vw, 62px); }
.verified-code { display: grid; grid-template-columns: 46px 1fr; gap: 15px; margin-top: 28px; padding: 18px; border: 1px solid color-mix(in srgb, var(--success) 42%, var(--line)); border-radius: 16px; background: var(--paper); }
.verified-mark { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 50%; background: color-mix(in srgb, var(--success) 16%, var(--paper)); color: var(--success); }
.verified-code strong { font-size: 13px; font-weight: 600; }
.verified-code p { margin-top: 5px; color: var(--muted); font-size: 11px; line-height: 1.55; }
.code-points { display: grid; gap: 12px; margin: 24px 0 0; padding: 0; list-style: none; color: var(--muted); font-size: 12px; }
.code-points li { display: flex; align-items: center; gap: 9px; }
.code-points .icon { width: 17px; height: 17px; color: var(--accent); }
.android-technology { grid-template-columns: 1.2fr minmax(300px, .8fr); background: var(--paper); border: 1px solid var(--line); }
.technology-facts { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; margin: 30px 0 0; overflow: hidden; border: 1px solid var(--line); border-radius: 17px; background: var(--line); }
.technology-facts div { padding: 17px; background: var(--paper); }
.technology-facts dt { color: var(--muted); font-size: 9px; letter-spacing: .08em; text-transform: uppercase; }
.technology-facts dd { margin: 7px 0 0; color: var(--accent); font: 500 19px/1.2 'Playfair Display', Georgia, serif; }
.settings-preview { order: 2; }
.android-final { min-height: 310px; display: grid; grid-template-columns: 1.1fr .9fr; align-items: center; gap: 48px; margin: 96px 0 42px; padding: 50px clamp(38px, 7vw, 84px); border-radius: 32px; color: #f8efe8; background: radial-gradient(circle at 85% 20%, #c47f5942, transparent 34%), #54251f; }
.android-final .android-kicker, .android-final h2 span { color: #efb49c; }
.android-final>div>p:last-child { color: #e0c9bd; max-width: 670px; }
.final-action { text-align: center; }
.final-action .button { width: 100%; min-height: 58px; color: #3a1f19; background: #f2c0a9; border-color: #f2c0a9; font-size: 13px; overflow-wrap: anywhere; }
.final-action>p { margin-top: 11px; color: #d7bcb0; font-size: 9px; line-height: 1.55; }
:global(:root[data-theme='dark'] .android-hero) { box-shadow: none; }
:global(:root[data-theme='dark'] .phone) { border-color: #4a4544; }
:global(:root[data-theme='dark'] .phone:before) { background: #4a4544; }
:global(:root[data-theme='dark'] .benefit-card:hover) { border-color: #8e715f; }
@media (max-width: 1023px) {
  .android-page { width: calc(100% - 48px); }
  .android-hero { grid-template-columns: 1fr; padding: 48px; }
  .android-hero-copy { max-width: 690px; }
  .android-phones { width: min(590px, 100%); margin: 0 auto; }
  .benefit-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .recognition-screen { height: 420px; }
  .code-search, .android-technology { gap: 44px; padding: 48px; }
  .code-screen, .settings-preview { width: 286px; height: 580px; }
}
@media (max-width: 767px) {
  .android-page { width: calc(100% - 32px); padding-top: 28px; }
  .android-hero { min-height: 0; padding: 32px 22px 38px; border-radius: 25px; }
  .android-hero h1 { font-size: clamp(42px, 13vw, 59px); }
  .android-lead { font-size: 14px; }
  .android-actions { flex-direction: column; }
  .android-actions .button { width: 100%; }
  .android-phones { min-height: 440px; margin-top: 12px; }
  .phone-light, .phone-dark { width: 188px; height: 383px; border-width: 6px; border-radius: 29px; }
  .phone-light { left: 1%; }
  .phone-dark { right: 1%; }
  .hero-orbit-one { width: 390px; height: 390px; left: 50%; transform: translateX(-50%); }
  .hero-orbit-two { display: none; }
  .android-section { margin-top: 68px; }
  .android-section-heading { margin-bottom: 25px; }
  .android-section-heading h2, .code-copy h2, .technology-copy h2, .android-final h2 { font-size: 37px; }
  .benefit-grid { grid-template-columns: 1fr; gap: 10px; }
  .benefit-card { min-height: 0; padding: 20px; display: grid; grid-template-columns: 48px 1fr; column-gap: 16px; }
  .benefit-card h3 { margin: 2px 0 7px; }
  .benefit-card p { grid-column: 2; }
  .recognition-grid { grid-template-columns: 1fr; }
  .recognition-copy { min-height: 0; }
  .recognition-screen { height: 500px; }
  .code-search, .android-technology { grid-template-columns: 1fr; padding: 34px 22px; border-radius: 25px; }
  .code-screen, .settings-preview { width: min(300px, 94%); height: auto; aspect-ratio: 1080 / 2199; }
  .code-copy { order: -1; }
  .android-technology .settings-preview { order: initial; }
  .technology-facts { grid-template-columns: 1fr; }
  .android-final { grid-template-columns: 1fr; gap: 28px; margin-top: 68px; padding: 36px 23px; border-radius: 25px; }
}
@media (max-width: 400px) {
  .android-phones { min-height: 390px; }
  .phone-light, .phone-dark { width: 164px; height: 334px; }
  .recognition-screen { height: 430px; }
  .android-release-facts li { font-size: 9px; }
}
@media (prefers-reduced-motion: reduce) {
  .benefit-card { transition: none; }
  .benefit-card:hover { transform: none; }
}
</style>
