<script setup lang="ts">
import { MOCK_SLUG, type Wine } from '#shared/catalog'

const title = 'Больше, чем распознавание — Что за вино?'
const description = 'Что происходит после фото: готовые функции, четыре интерактивных демо и макеты новых идей для знакомства с российским вином.'
useSeoMeta({ title, description, ogType: 'website', ogTitle: title, ogDescription: description, ogUrl: 'https://chtozavino.ru/ideas', twitterTitle: title, twitterDescription: description })
useHead({ link: [{ rel: 'canonical', href: 'https://chtozavino.ru/ideas' }] })

const implemented = [
  { icon: 'book', platform: 'WEB · ANDROID · TELEGRAM', title: 'Узнать больше о находке', description: 'От найденного названия — к карточке на «Свое Вино». Производитель, сорт и описание помогают продолжить знакомство с вином.', detail: 'Открывается карточка конкретного вина в исходном каталоге. Для перехода нужен интернет.', href: '/', action: 'Открыть веб-сканер' },
  { icon: 'history', platform: 'ANDROID', title: 'Вернуться к своим находкам', description: 'Не вспоминать название и не искать старое фото. Результаты распознавания остаются в локальной истории приложения.', detail: 'Историю можно просматривать на устройстве и очищать. Облачная синхронизация не требуется.', href: '/android', action: 'Посмотреть Android' },
  { icon: 'telegram', platform: 'TELEGRAM', title: 'Сказать: «Это другое вино»', description: 'Подтвердить результат или посмотреть ещё три варианта. Если ничего не подходит, сообщить об этом одним нажатием.', detail: 'Обратная связь сохраняется. Кнопки доступны для результата одиночной фотографии, вне альбома.', href: 'https://t.me/ChtoZaVinoBot', action: 'Открыть бота' },
]

const demos = [
  { icon: 'food', title: 'Блюда с местным характером', description: 'Три региональные кухни и объяснение каждого сочетания. Подбор учитывает карточку вина и правила стиля.', limit: 'Гастрономическая гипотеза: рецепт и соус могут изменить сочетание.' },
  { icon: 'book', title: 'Этикетка понятным языком', description: 'Показать сорта из карточки и объяснить, как читать короткие надписи на бутылке.', limit: 'Объяснение Сира и Вионье — фиксированный пример, а не разбор любой этикетки.' },
  { icon: 'taste', title: 'Вкус до первого глотка', description: 'Шесть характеристик, семейства ароматов и международный ориентир по стилю.', limit: 'Ожидаемый профиль по карточке, правилам и открытым данным. Не дегустационная оценка.' },
  { icon: 'map', title: 'Место в линейке', description: 'Карта помогает разобраться в коллекциях производителя и перейти к соседним винам.', limit: 'Шесть примеров Абрау-Дюрсо. Для других производителей открывается демонстрационная карта.' },
]

const mockups = [
  { id: 'groceries', icon: 'store', title: 'От блюда — к продуктам', description: 'Превратить гастрономическую пару в список ингредиентов и найти их в выбранном магазине.', limit: 'Макет списка. Наличие, цены и магазины не подключены.', tags: ['Рыба', 'Зелень', 'Лимон'] },
  { id: 'audio', icon: 'story', title: 'История, которую можно услышать', description: 'Короткий аудиорассказ о месте, винодельне и людях за этикеткой.', limit: 'Макет аудиокарточки. Записи и воспроизведения пока нет.', tags: [] },
  { id: 'discovery', icon: 'search', title: 'Искать по вкусу', description: 'Описать желаемый стиль и найти похожие российские вина, в том числе у других производителей.', limit: 'Пример запроса. Поиск по вкусу и рекомендации по всему каталогу пока не работают.', tags: ['Свежее', 'Цитрусовое', 'Без дуба'] },
  { id: 'personal', icon: 'taste', title: 'Личный паспорт предпочтений', description: 'Собирать впечатления о винах, замечать любимые стили и получать персональные рекомендации.', limit: 'Пример профиля. Предпочтения не сохраняются, персонализация не подключена.', tags: ['Свежесть', 'Фруктовость', 'Мягкость'] },
  { id: 'blind', icon: 'book', title: 'Угадать стиль вслепую', description: 'Небольшая игра: узнать сорт или регион по описанию, а затем открыть объяснение.', limit: 'Пример вопроса. Игровой сценарий и подсчёт результата пока не реализованы.', tags: ['Сорт', 'Регион', 'Разгадка'] },
  { id: 'shelf', icon: 'shelf', title: 'Полка как система', description: 'Сравнить фактическую выкладку с планом, увидеть пропуски и проследить изменения во времени.', limit: 'Макет планограммы. Распознавание полки уже есть; планы, контроль выкладки и история — пока идея.', tags: [] },
]

const stages = [
  { id: 'implemented', number: '01', name: 'Реализовано', count: implemented.length, description: 'Готовые сценарии в приложениях' },
  { id: 'demo', number: '02', name: 'Демо', count: demos.length, description: 'Можно попробовать на примере' },
  { id: 'mock', number: '03', name: 'Макеты', count: mockups.length, description: 'Так могут выглядеть следующие шаги' },
]

const { data: examples, status, refresh } = await useFetch<Wine[]>('/api/wines', { key: 'ideas-example-wines' })
const exampleSlugs = [MOCK_SLUG, 'priboj-marchenko-krasnoe-polusuhoe', 'gevyurcztraminer-oranzh']
const demoWines = computed(() => (examples.value || []).filter(wine => exampleSlugs.includes(wine.slug)))
const selectedSlug = ref(MOCK_SLUG)
const selectedWine = computed(() => demoWines.value.find(wine => wine.slug === selectedSlug.value) || demoWines.value[0])
</script>

<template>
  <main id="main-content" class="ideas-page">
    <section class="ideas-hero" aria-labelledby="ideas-title">
      <div class="hero-copy">
        <p class="eyebrow"><span />ИДЕИ ВОКРУГ ВИНА</p>
        <h1 id="ideas-title">Распознать —<br><em>только начало.</em></h1>
        <p class="hero-lead">Фото отвечает на вопрос «что это?».<br>Дальше — понять вкус, найти сочетание<br class="desktop-break"> и открыть для себя что-то новое.</p>
        <a href="#implemented" class="button primary">Что уже умеет проект<AppIcon name="arrow" /></a>
        <p class="hero-note">От готовых возможностей к идеям на будущее</p>
      </div>
      <div class="hero-art" role="img" aria-label="От знакомой бутылки к блюдам, вкусу и истории вина. Иллюстрация идей проекта.">
        <div class="art-orbit outer" /><div class="art-orbit inner" />
        <span class="art-caption">У КАЖДОЙ ЭТИКЕТКИ ЕСТЬ ПРОДОЛЖЕНИЕ</span>
        <img class="hero-bottle" src="/wines/priboj-marchenko-beloe-polusuhoe.webp" width="360" height="440" alt="" fetchpriority="high">
        <span class="art-label label-taste"><AppIcon name="taste" /><span>Понять<br><strong>характер</strong></span></span>
        <span class="art-label label-food"><AppIcon name="food" /><span>Найти<br><strong>сочетание</strong></span></span>
        <span class="art-label label-story"><AppIcon name="map" /><span>Открыть<br><strong>историю</strong></span></span>
        <span class="art-footnote">ОДНА БУТЫЛКА · МНОГО ОТКРЫТИЙ</span>
      </div>
    </section>

    <nav class="stage-nav" aria-label="Идеи по степени готовности">
      <a v-for="stage in stages" :key="stage.id" :href="`#${stage.id}`" :class="stage.id">
        <span class="stage-number">{{ stage.number }}</span>
        <span class="stage-copy"><strong>{{ stage.name }} <small>{{ stage.count }}</small></strong><span>{{ stage.description }}</span></span>
        <AppIcon name="chevron" />
      </a>
    </nav>

    <section id="implemented" class="ideas-section" aria-labelledby="implemented-title" data-stage="implemented">
      <div class="section-heading">
        <div><p class="section-kicker"><span>01</span> РЕАЛИЗОВАНО ПОЛНОСТЬЮ</p><h2 id="implemented-title">Уже часть знакомства.</h2></div>
        <p>Завершённые сценарии в текущих приложениях. На каждой карточке указано, где они доступны.</p>
      </div>
      <div class="ready-grid">
        <article v-for="idea in implemented" :key="idea.title" class="ready-card">
          <div class="card-top"><span class="feature-icon"><AppIcon :name="idea.icon" /></span><span class="status-badge ready"><AppIcon name="check" />Реализовано</span></div>
          <p class="platform-caption">{{ idea.platform }}</p>
          <h3>{{ idea.title }}</h3><p class="card-description">{{ idea.description }}</p>
          <p class="card-detail">{{ idea.detail }}</p>
          <a v-if="idea.href.startsWith('https:')" :href="idea.href" class="idea-link" target="_blank" rel="noopener noreferrer">{{ idea.action }}<AppIcon name="arrow-up-right" /></a>
          <NuxtLink v-else :to="idea.href" class="idea-link">{{ idea.action }}<AppIcon name="arrow-up-right" /></NuxtLink>
        </article>
      </div>
    </section>

    <section id="demo" class="ideas-section" aria-labelledby="demo-title" data-stage="demo">
      <div class="section-heading">
        <div><p class="section-kicker"><span>02</span> ИНТЕРАКТИВНЫЕ ДЕМО</p><h2 id="demo-title">Попробовать продолжение.</h2></div>
        <p>Четыре работающих прототипа после распознавания. Здесь их можно открыть на готовой карточке, без загрузки фото.</p>
      </div>
      <div class="demo-editorial">
        <figure class="dish-figure"><img src="/dishes/chudu-s-zelenyu-i-syrom.webp" width="640" height="400" alt="Чуду с зеленью и сыром — одна из иллюстраций региональных блюд в демо" loading="lazy"><figcaption><span class="status-badge demo">Демо</span><span>Знакомство через вкус<br><strong>и кухни регионов</strong></span></figcaption></figure>
        <div class="demo-descriptions">
          <article v-for="idea in demos" :key="idea.title"><AppIcon :name="idea.icon" /><div><h3>{{ idea.title }}</h3><p>{{ idea.description }}</p><small>{{ idea.limit }}</small></div></article>
        </div>
      </div>
      <div id="try-demo" class="demo-playground">
        <div class="playground-heading"><p class="section-kicker">ОТКРОЙТЕ ЛЮБОЙ ИЗ ЧЕТЫРЁХ СЦЕНАРИЕВ</p><span class="status-badge demo">Демо на примере</span></div>
        <template v-if="selectedWine">
          <div class="example-context">
            <img :src="selectedWine.image" width="72" height="96" alt="" loading="lazy">
            <div><label for="idea-wine">Вино для примера</label><select id="idea-wine" v-model="selectedSlug"><option v-for="wine in demoWines" :key="wine.slug" :value="wine.slug">{{ wine.name }}</option></select><p>Это готовая карточка из каталога, а не результат распознавания вашей фотографии.</p></div>
          </div>
          <WineExperiences :key="selectedWine.slug" :wine="selectedWine" />
        </template>
        <div v-else class="example-unavailable" role="status"><p>Не удалось загрузить карточку для примера.</p><button class="button secondary" :disabled="status === 'pending'" @click="refresh()">{{ status === 'pending' ? 'Загружаем…' : 'Загрузить пример' }}</button></div>
      </div>
    </section>

    <section id="mock" class="ideas-section" aria-labelledby="mock-title" data-stage="mock">
      <div class="section-heading">
        <div><p class="section-kicker"><span>03</span> МАКЕТЫ И ИДЕИ</p><h2 id="mock-title">Куда пойти дальше.</h2></div>
        <p>Эскизы следующих возможностей. Они показывают замысел: сервисы за этими макетами пока не работают.</p>
      </div>
      <div class="mock-grid">
        <article v-for="idea in mockups" :id="`idea-${idea.id}`" :key="idea.id" class="mock-card">
          <div class="mock-preview" :class="`preview-${idea.id}`" aria-hidden="true">
            <span class="mock-preview-label">ЭСКИЗ ИНТЕРФЕЙСА</span>
            <template v-if="idea.id === 'audio'"><div class="audio-sketch"><AppIcon name="story" /><div class="waveform"><i v-for="(height, index) in [14, 26, 38, 20, 44, 30, 18, 36, 46, 24, 14, 32, 42, 22, 12]" :key="index" :style="{ height: `${height}px` }" /></div></div><span class="preview-caption">Голос места. История винодельни.</span></template>
            <template v-else-if="idea.id === 'shelf'"><div class="shelf-sketch"><span v-for="slot in 7" :key="slot" :class="{ 'empty-slot': slot === 4 }"><AppIcon :name="slot === 4 ? 'plus' : 'taste'" /></span></div><span class="preview-caption">План → фотография → отличия</span></template>
            <template v-else-if="idea.id === 'personal'"><div class="profile-sketch"><div v-for="(tag, index) in idea.tags" :key="tag"><span>{{ tag }}</span><i><b :style="{ width: `${[80, 65, 45][index]}%` }" /></i></div></div></template>
            <template v-else><AppIcon :name="idea.icon" /><p class="sketch-title">{{ idea.id === 'groceries' ? 'К ужину с рыбой' : idea.id === 'discovery' ? '«Хочется чего-то…»' : 'Что скрывает этикетка?' }}</p><div class="sketch-tags"><span v-for="tag in idea.tags" :key="tag">{{ tag }}</span></div></template>
          </div>
          <div class="mock-copy"><span class="status-badge mock">Макет · не подключено</span><h3>{{ idea.title }}</h3><p class="card-description">{{ idea.description }}</p><p class="card-detail">{{ idea.limit }}</p></div>
        </article>
      </div>
    </section>

    <section class="ideas-outro" aria-labelledby="outro-title"><div><p class="section-kicker">НАЧНИТЕ СО ЗНАКОМСТВА</p><h2 id="outro-title">Узнать вино.<br><em>А потом — чуть больше.</em></h2></div><div><NuxtLink to="/" class="button primary">Открыть сканер<AppIcon name="arrow-up-right" /></NuxtLink><NuxtLink to="/android" class="idea-link">Приложение для Android<AppIcon name="arrow" /></NuxtLink></div></section>
  </main>
</template>

<style scoped>
.ideas-page { --ideas-muted: color-mix(in srgb, var(--ink) 72%, var(--paper)); width: calc(100% - 80px); max-width: 1240px; margin: 0 auto; }
.ideas-hero { display: grid; grid-template-columns: 1.1fr 1fr; align-items: center; gap: 24px; padding: 68px 32px 52px; }
.hero-copy { position: relative; z-index: 1; }
.hero-copy h1 { margin: 24px 0; font-size: clamp(44px, 5.3vw, 74px); line-height: 1.08; letter-spacing: -.045em; }
.hero-copy h1 em, .ideas-outro em { color: var(--accent); font-style: normal; }
.hero-lead { color: var(--ideas-muted); font-size: 17px; line-height: 1.8; }
.hero-copy .button { margin-top: 30px; }
.hero-note { margin-top: 15px; font-size: 11px; color: var(--ideas-muted); }
.hero-art { height: 440px; position: relative; display: grid; place-items: center; isolation: isolate; }
.art-orbit { position: absolute; border: 1px solid color-mix(in srgb, var(--accent) 18%, transparent); border-radius: 50%; z-index: -1; }
.art-orbit.outer { width: 390px; height: 390px; }
.art-orbit.inner { width: 300px; height: 300px; background: radial-gradient(ellipse, var(--tag), transparent 70%); }
.hero-bottle { width: 330px; height: 380px; object-fit: contain; transform: rotate(12deg); filter: drop-shadow(10px 15px 8px #482d251c); }
.art-caption, .art-footnote { position: absolute; font-size: 8px; letter-spacing: .17em; color: var(--ideas-muted); text-align: center; }
.art-caption { top: 0; }.art-footnote { bottom: 0; }
.art-label { position: absolute; display: flex; align-items: center; gap: 12px; padding: 16px 20px; border: 1px solid var(--line); border-radius: 16px; background: var(--paper); box-shadow: 0 10px 24px #482d2508; font-size: 11px; line-height: 1.6; color: var(--ideas-muted); }
.art-label .icon { color: var(--accent); width: 27px; height: 27px; }.art-label strong { color: var(--ink); font-size: 14px; font-weight: 500; }
.label-taste { top: 70px; left: 0; transform: rotate(-5deg); }.label-food { top: 170px; right: 0; transform: rotate(5deg); }.label-story { bottom: 53px; left: 20px; transform: rotate(-3deg); }
.stage-nav { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border: 1px solid var(--line); border-radius: 20px; overflow: hidden; background: var(--paper); }
.stage-nav a { display: flex; align-items: center; gap: 17px; padding: 25px; }.stage-nav a + a { border-left: 1px solid var(--line); }.stage-nav a:hover { background: var(--cream); }
.stage-number { font: 400 30px/1 'Playfair Display', Georgia, serif; color: var(--muted); }.stage-copy { flex: 1; min-width: 0; }.stage-copy strong { display: flex; align-items: center; gap: 10px; font-size: 15px; font-weight: 600; }.stage-copy small { font: 500 11px/1 system-ui, sans-serif; padding: 5px 7px; border-radius: 50%; background: var(--cream); }.stage-copy > span { display: block; margin-top: 7px; font-size: 10px; line-height: 1.5; color: var(--ideas-muted); }.stage-nav .icon { width: 15px; height: 15px; color: var(--accent); }
.ideas-section { margin-top: 86px; scroll-margin-top: 30px; }.section-heading { display: flex; justify-content: space-between; align-items: flex-end; gap: 32px; margin-bottom: 30px; }.section-kicker { display: flex; gap: 12px; align-items: center; font-size: 10px; font-weight: 600; letter-spacing: .13em; color: var(--accent); line-height: 1.6; }.section-kicker > span { color: var(--muted); border-right: 1px solid var(--line); padding-right: 12px; }.section-heading h2 { font-size: clamp(30px, 3.25vw, 44px); line-height: 1.22; letter-spacing: -.035em; margin-top: 13px; }.section-heading > p { max-width: 370px; font-size: 13px; line-height: 1.8; color: var(--ideas-muted); }
.ready-grid, .mock-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }.ready-card { display: flex; flex-direction: column; padding: 28px; border: 1px solid var(--line); border-radius: 22px; background: var(--paper); }.card-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }.feature-icon { display: grid; place-items: center; width: 46px; height: 46px; color: var(--success); background: color-mix(in srgb, var(--success) 10%, var(--paper)); border-radius: 14px; }.status-badge { display: inline-flex; align-items: center; gap: 5px; width: fit-content; padding: 6px 9px; border: 1px solid var(--line); border-radius: 30px; font-size: 9px; font-weight: 600; line-height: 1.4; white-space: nowrap; }.status-badge .icon { width: 12px; height: 12px; }.status-badge.ready { color: var(--success); border-color: color-mix(in srgb, var(--success) 30%, var(--line)); background: color-mix(in srgb, var(--success) 6%, var(--paper)); }.status-badge.demo { color: var(--accent); background: var(--cream); }.status-badge.mock { color: var(--ideas-muted); border-style: dashed; }
.platform-caption { margin: 25px 0 12px; color: var(--ideas-muted); font-size: 9px; letter-spacing: .11em; }.ready-card h3, .mock-card h3 { margin: 0 0 15px; font: 500 26px/1.2 'Playfair Display', Georgia, serif; letter-spacing: -.025em; }.card-description { font-size: 13px; line-height: 1.85; color: var(--ideas-muted); }.card-detail { margin-top: 20px; padding-top: 15px; border-top: 1px solid var(--line); font-size: 11px; line-height: 1.75; color: var(--ideas-muted); }.ready-card .card-detail { margin-bottom: 20px; }.idea-link { display: inline-flex; align-items: center; gap: 9px; min-height: 44px; width: fit-content; color: var(--accent); font-size: 12px; }.idea-link .icon { width: 16px; height: 16px; }.idea-link:hover { text-decoration: underline; text-underline-offset: 4px; }.ready-card .idea-link { margin-top: auto; }
.demo-editorial { display: grid; grid-template-columns: .85fr 1.15fr; gap: 34px; }.dish-figure { position: relative; min-width: 0; margin: 0; overflow: hidden; border-radius: 24px; background: #332d22; min-height: 520px; }.dish-figure img { width: 100%; height: 100%; object-fit: cover; position: absolute; }.dish-figure:after { position: absolute; content: ''; inset: 25% 0 0; background: linear-gradient(transparent, #201c16de); }.dish-figure figcaption { position: absolute; z-index: 1; bottom: 30px; left: 30px; right: 25px; color: #fff7e8; }.dish-figure .status-badge { background: #fff8eb; color: #743b2d; border: 0; margin-bottom: 16px; }.dish-figure figcaption > span:last-child { display: block; font: 400 32px/1.28 'Playfair Display', Georgia, serif; }.dish-figure strong { font-weight: 400; }.demo-descriptions { display: grid; gap: 20px; align-content: center; }.demo-descriptions article { display: grid; grid-template-columns: 24px 1fr; gap: 15px; }.demo-descriptions article > .icon { color: var(--accent); margin-top: 3px; }.demo-descriptions h3 { font: 500 23px/1.3 'Playfair Display', Georgia, serif; margin: 0 0 7px; }.demo-descriptions p { color: var(--ideas-muted); font-size: 12px; line-height: 1.75; }.demo-descriptions small { display: block; color: var(--ideas-muted); font-size: 10px; line-height: 1.65; margin-top: 7px; padding-left: 10px; border-left: 2px solid var(--line); }
.demo-playground { margin-top: 30px; padding: 28px; border: 1px solid var(--line); border-radius: 24px; background: var(--cream); scroll-margin-top: 24px; }.playground-heading { display: flex; align-items: center; justify-content: space-between; gap: 15px; }.example-context { display: flex; align-items: center; gap: 18px; margin-top: 20px; }.example-context > img { width: 66px; height: 86px; object-fit: contain; }.example-context > div { flex: 1; min-width: 0; }.example-context label { display: block; margin-bottom: 7px; color: var(--ideas-muted); font-size: 11px; }.example-context select { display: block; width: 100%; max-width: 480px; min-height: 44px; border: 1px solid var(--line); border-radius: 10px; padding: 10px; background: var(--paper); color: var(--ink); font: inherit; font-size: 13px; }.example-context p { margin-top: 9px; font-size: 11px; line-height: 1.6; color: var(--ideas-muted); }.demo-playground :deep(.experience-panel) { margin-top: 22px; }.example-unavailable { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; padding-top: 24px; font-size: 13px; }
.mock-card { overflow: hidden; min-width: 0; border: 1px solid var(--line); border-radius: 22px; background: var(--paper); scroll-margin-top: 24px; }.mock-preview { height: 194px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; position: relative; border-bottom: 1px solid var(--line); background: var(--cream); color: var(--accent); padding: 35px 20px 20px; }.mock-preview-label { position: absolute; top: 15px; left: 20px; font-size: 8px; letter-spacing: .12em; color: var(--ideas-muted); }.mock-preview > .icon { width: 26px; height: 26px; }.sketch-title { font: 500 19px/1.3 'Playfair Display', Georgia, serif; }.sketch-tags { display: flex; flex-wrap: wrap; justify-content: center; gap: 6px; }.sketch-tags span { padding: 5px 10px; border: 1px solid var(--line); background: var(--paper); border-radius: 20px; font-size: 10px; }.preview-caption { font-size: 10px; color: var(--ideas-muted); margin-top: 7px; }.mock-copy { padding: 26px; }.mock-copy h3 { margin-top: 17px; font-size: 25px; }.mock-copy .card-detail { margin-top: 17px; }.audio-sketch { display: flex; align-items: center; gap: 18px; }.audio-sketch > .icon { width: 38px; height: 38px; padding: 8px; box-sizing: content-box; border: 1px solid var(--line); border-radius: 50%; background: var(--paper); }.waveform { display: flex; align-items: center; gap: 4px; height: 46px; }.waveform i { width: 3px; border-radius: 5px; background: currentColor; opacity: .55; }.shelf-sketch { display: flex; gap: 7px; padding: 15px 0 8px; border-bottom: 3px solid var(--accent); }.shelf-sketch > span { width: 26px; height: 51px; display: grid; place-items: end center; padding-bottom: 5px; }.shelf-sketch .empty-slot { border: 1px dashed currentColor; border-radius: 6px; place-items: center; opacity: .5; }.shelf-sketch .icon { width: 21px; height: 34px; }.profile-sketch { width: 100%; max-width: 245px; display: grid; gap: 13px; }.profile-sketch > div { display: flex; align-items: center; gap: 12px; font-size: 10px; }.profile-sketch span { width: 85px; }.profile-sketch i { flex: 1; height: 6px; border-radius: 8px; background: var(--line); }.profile-sketch b { display: block; height: 6px; border-radius: 8px; background: var(--accent); opacity: .7; }
.ideas-outro { display: flex; align-items: center; justify-content: space-between; gap: 28px; padding: 48px; margin: 80px 0 30px; border-radius: 26px; background: var(--cream); }.ideas-outro h2 { font-size: clamp(32px, 3.6vw, 46px); line-height: 1.2; letter-spacing: -.03em; margin-top: 16px; }.ideas-outro > div:last-child { display: flex; flex-direction: column; align-items: center; gap: 9px; }
@media (max-width: 1100px) { .ideas-hero { padding-inline: 0; }.hero-art { transform: scale(.9); }.ready-card { padding: 22px; }.card-top { align-items: flex-start; flex-direction: column; }.stage-nav a { padding: 22px 18px; gap: 12px; }.demo-editorial { gap: 25px; }.mock-copy { padding: 22px; } }
@media (max-width: 900px) { .ideas-page { width: calc(100% - 48px); }.ideas-hero { grid-template-columns: 1.05fr 1fr; gap: 0; }.hero-art { height: 380px; transform: none; }.art-orbit.outer { width: 300px; height: 300px; }.art-orbit.inner { width: 230px; height: 230px; }.hero-bottle { width: 270px; height: 330px; }.art-label { padding: 10px; gap: 8px; }.label-taste { left: 0; top: 60px; }.label-food { top: 160px; right: 0; }.label-story { left: 5px; bottom: 30px; }.art-caption { max-width: 210px; font-size: 7px; }.art-footnote { font-size: 7px; }.hero-lead { font-size: 14px; }.stage-number { display: none; }.section-heading { align-items: flex-start; flex-direction: column; gap: 16px; }.section-heading > p { max-width: 600px; }.ready-grid { grid-template-columns: 1fr; }.ready-card { padding: 26px; }.card-top { flex-direction: row; align-items: center; }.platform-caption { margin-top: 18px; }.ready-card h3 { font-size: 28px; }.ready-card .card-detail { margin-top: 16px; margin-bottom: 8px; }.mock-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }.demo-editorial { grid-template-columns: .75fr 1.25fr; }.dish-figure figcaption { left: 22px; }.dish-figure figcaption > span:last-child { font-size: 27px; }.ideas-outro { padding: 34px; } }
@media (max-width: 600px) { .ideas-page { width: calc(100% - 32px); }.ideas-hero { grid-template-columns: 1fr; padding: 42px 6px 28px; }.hero-copy h1 { font-size: clamp(39px, 10.5vw, 58px); margin: 18px 0; }.hero-copy .eyebrow { font-size: 9px; }.hero-lead { font-size: 15px; }.hero-copy .button { margin-top: 24px; font-size: 12px; }.hero-art { width: 100%; max-width: 370px; margin: 34px auto 0; height: 340px; }.hero-bottle { width: 240px; height: 300px; }.art-orbit.outer { width: 270px; height: 270px; }.art-orbit.inner { width: 210px; height: 210px; }.label-taste { top: 60px; }.label-food { top: 140px; }.label-story { bottom: 30px; }.art-label strong { font-size: 12px; }.stage-nav { grid-template-columns: 1fr; border-radius: 18px; }.stage-nav a { padding: 18px 20px; gap: 18px; }.stage-nav a + a { border-left: 0; border-top: 1px solid var(--line); }.stage-number { display: block; font-size: 26px; }.stage-copy > span { margin-top: 4px; }.ideas-section { margin-top: 54px; }.section-heading { gap: 13px; margin-bottom: 22px; }.section-heading h2 { font-size: 31px; }.section-kicker { font-size: 9px; }.ready-card { padding: 23px; }.ready-card h3 { font-size: 27px; }.demo-editorial { grid-template-columns: 1fr; gap: 28px; }.dish-figure { min-height: 270px; }.dish-figure figcaption { bottom: 22px; }.demo-descriptions { gap: 24px; }.demo-descriptions h3 { font-size: 23px; }.demo-playground { padding: 20px 14px; }.playground-heading { align-items: flex-start; flex-direction: column; gap: 10px; }.example-context { gap: 9px; align-items: flex-start; }.example-context > img { width: 42px; height: 70px; }.example-context select { font-size: 11px; }.demo-playground :deep(.experience-panel) { padding: 20px 14px; }.mock-grid { grid-template-columns: 1fr; gap: 20px; }.mock-preview { height: 182px; }.mock-copy { padding: 24px; }.mock-copy h3 { font-size: 27px; }.ideas-outro { flex-direction: column; align-items: flex-start; padding: 28px; margin-top: 54px; }.ideas-outro h2 { font-size: 32px; }.ideas-outro > div:last-child { align-items: flex-start; }.desktop-break { display: none; } }
</style>
