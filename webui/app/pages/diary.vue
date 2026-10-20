<script setup lang="ts">
import { HISTORY_SOURCE_LABELS, SAVED_STATUSES, SAVED_STATUS_LABELS, type HistorySource, type SavedStatus } from '#shared/diary'

const title = 'Винный дневник — общая история, сохранённые вина и заметки'
const description = 'Ваши находки на сайте, в Telegram и MAX — в одном аккаунте. Сохраняйте вина, отмечайте, что хотите попробовать и что понравилось, и оставляйте личные заметки.'
const canonical = 'https://chtozavino.ru/diary'
useSeoMeta({ title, description, ogType: 'website', ogTitle: title, ogDescription: description, ogUrl: canonical, twitterCard: 'summary', twitterTitle: title, twitterDescription: description })
useHead({
  link: [{ rel: 'canonical', href: canonical }],
  script: [{ type: 'application/ld+json', innerHTML: JSON.stringify({
    '@context': 'https://schema.org', '@type': 'WebPage', name: title, description, url: canonical,
    inLanguage: 'ru', isPartOf: { '@id': 'https://chtozavino.ru/#website' },
    about: { '@type': 'WebApplication', name: 'Винный дневник — Что за вино?', url: 'https://chtozavino.ru/account', applicationCategory: 'LifestyleApplication', inLanguage: 'ru' },
  }) }],
})

type PreviewTab = 'saved' | 'history'
const previewTabs: { key: PreviewTab; label: string; icon: string }[] = [
  { key: 'saved', label: 'Сохранённые', icon: 'pin' },
  { key: 'history', label: 'История', icon: 'history' },
]
const previewTab = ref<PreviewTab>('saved')
const previewStatus = ref<SavedStatus | ''>('')
// Public catalogue wines; the statuses, dates, sources, and notes below are illustrative only.
// This preview makes no account calls and never saves data.
const examples: { slug: string; name: string; producer: string; style: string; status: SavedStatus; source: HistorySource; date: string; note: string }[] = [
  { slug: 'priboj-marchenko-beloe-polusuhoe', name: 'Прибой Марченко белое полусухое', producer: 'Винодельня Марченко', style: 'Белое · Полусухое', status: 'want', source: 'telegram', date: '20 октября', note: 'Вернуться к этой бутылке на следующей встрече.' },
  { slug: 'gevyurcztraminer-oranzh', name: 'Гевюрцтраминер Оранж', producer: 'Усадьба Перовских', style: 'Оранжевое · Сухое', status: 'liked', source: 'max', date: '19 октября', note: 'Запомнить название: понравилось за ужином.' },
  { slug: 'priboj-marchenko-rozovoe-polusuhoe', name: 'Прибой Марченко розовое полусухое', producer: 'Винодельня Марченко', style: 'Розовое · Полусухое', status: 'not_tasted', source: 'photo', date: '18 октября', note: 'Знакомство ещё впереди.' },
  { slug: 'priboj-marchenko-krasnoe-polusuhoe', name: 'Прибой Марченко красное полусухое', producer: 'Винодельня Марченко', style: 'Красное · Полусухое', status: 'disliked', source: 'shelf', date: '17 октября', note: 'В следующий раз выбрать другой стиль.' },
]
const shownExamples = computed(() => previewTab.value === 'history' || !previewStatus.value ? examples : examples.filter(wine => wine.status === previewStatus.value))
const statusDetails: Record<SavedStatus, { icon: string; copy: string }> = {
  not_tasted: { icon: 'wine-white', copy: 'Сохраните интересную бутылку, даже если знакомство с ней ещё впереди. Это начальный статус нового вина.' },
  want: { icon: 'pin', copy: 'Соберите свой список желаний. При следующем выборе вина будет легко вспомнить, что хотелось попробовать.' },
  liked: { icon: 'check', copy: 'Отметьте удачное знакомство, чтобы вернуться к нему. Добавьте заметку о вкусе, блюде или поводе.' },
  disliked: { icon: 'minus', copy: 'Оставьте и этот опыт в дневнике. Заметка поможет вспомнить, что именно вам не подошло.' },
}
const historyFeatures = [
  { icon: 'wine-red', title: 'Вино и его карточка', copy: 'Фото бутылки, название, производитель, цвет и сахар. Можно открыть страницу вина на «Свое Вино».' },
  { icon: 'history', title: 'Даты и источник', copy: 'Видно, когда и где вы нашли вино. Повторные находки собираются в одной карточке: одна запись на вино в день.' },
  { icon: 'filter', title: 'Поиск и фильтры', copy: 'Ищите по названию и производителю. Отберите вина по цвету, сахару или источнику: сайт, полка, Telegram, MAX.' },
]

function selectPreview(tab: PreviewTab, focus = false) {
  previewTab.value = tab
  if (focus) nextTick(() => document.getElementById(`diary-preview-${tab}`)?.focus())
}
function previewKey(event: KeyboardEvent, index: number) {
  const target = event.key === 'ArrowRight' || event.key === 'ArrowLeft' ? 1 - index : event.key === 'Home' ? 0 : event.key === 'End' ? 1 : -1
  if (target < 0) return
  event.preventDefault()
  selectPreview(previewTabs[target]!.key, true)
}
</script>

<template>
  <main id="main-content" class="diary-landing">
    <section class="diary-hero" aria-labelledby="diary-title">
      <div class="diary-hero-copy">
        <p class="diary-kicker"><AppIcon name="book" />ВИННЫЙ ДНЕВНИК</p>
        <h1 id="diary-title">Нашли.<br>Сохранили.<br><span>Запомнили.</span></h1>
        <p class="diary-lead">Соберите свои винные находки в одном месте. Возвращайтесь к понравившимся бутылкам, отмечайте, что хочется попробовать, и сохраняйте впечатления.</p>
        <div class="diary-actions">
          <NuxtLink class="button primary" to="/account" data-testid="diary-open"><AppIcon name="book" />Открыть дневник</NuxtLink>
          <a class="diary-text-link" href="#diary-connections">Связать Telegram и MAX<AppIcon name="arrow" /></a>
        </div>
        <ul class="diary-hero-facts" aria-label="Возможности дневника"><li>Один аккаунт</li><li>Общая история</li><li>Свои заметки</li><li>18+</li></ul>
      </div>

      <figure class="diary-preview" aria-labelledby="diary-preview-caption">
        <div class="preview-heading"><AppIcon name="book" /><span>Мой винный дневник</span><span class="preview-badge">Пример</span></div>
        <div class="preview-tabs" role="tablist" aria-label="Пример разделов дневника">
          <button v-for="(tab, index) in previewTabs" :id="`diary-preview-${tab.key}`" :key="tab.key" type="button" role="tab" :aria-selected="previewTab === tab.key" aria-controls="diary-preview-panel" :tabindex="previewTab === tab.key ? 0 : -1" @click="selectPreview(tab.key)" @keydown="previewKey($event, index)"><AppIcon :name="tab.icon" />{{ tab.label }}</button>
        </div>
        <div id="diary-preview-panel" role="tabpanel" :aria-labelledby="`diary-preview-${previewTab}`" class="preview-panel">
          <div v-if="previewTab === 'saved'" class="preview-filters" role="group" aria-label="Статус в примере">
            <button type="button" :aria-pressed="previewStatus === ''" @click="previewStatus = ''">Все</button>
            <button v-for="status in SAVED_STATUSES" :key="status" type="button" :aria-pressed="previewStatus === status" @click="previewStatus = status">{{ SAVED_STATUS_LABELS[status] }}</button>
          </div>
          <p v-else class="preview-history-hint">Находки с сайта и из привязанных чатов</p>
          <p class="sr-only" role="status">В примере показано вин: {{ shownExamples.length }}</p>
          <ul class="preview-wines">
            <li v-for="wine in shownExamples" :key="wine.slug" class="preview-wine">
              <div class="preview-bottle"><img :src="`/wines/${wine.slug}.webp`" alt="" width="52" height="102"></div>
              <div class="preview-wine-copy"><h3>{{ wine.name }}</h3><p class="preview-producer">{{ wine.producer }} · {{ wine.style }}</p><span v-if="previewTab === 'saved'" class="preview-status" :data-status="wine.status"><AppIcon :name="statusDetails[wine.status].icon" />{{ SAVED_STATUS_LABELS[wine.status] }}</span><span v-else class="preview-source">{{ wine.date }} · {{ HISTORY_SOURCE_LABELS[wine.source] }}</span><p v-if="previewTab === 'saved'" class="preview-wine-note">{{ wine.note }}</p></div>
            </li>
          </ul>
        </div>
        <figcaption id="diary-preview-caption">Интерактивный пример · вымышленные записи.<br>Переключайте разделы и статусы. Ваш дневник откроется после входа.</figcaption>
      </figure>
    </section>

    <section class="diary-section diary-history" aria-labelledby="diary-history-title">
      <div class="diary-section-heading"><p class="diary-kicker">01 / ИСТОРИЯ НАХОДОК</p><h2 id="diary-history-title">Фото на сайте.<br>Сообщение боту.<br><span>Одна история.</span></h2><p>Войдите в аккаунт на сайте и привяжите к нему Telegram и MAX. Если включено «Записывать найденные вина», новые находки появятся во вкладке «История» этого аккаунта — с любого устройства, где вы в него вошли.</p><NuxtLink class="diary-text-link" to="/account?tab=history">Открыть свою историю<AppIcon name="arrow" /></NuxtLink></div>
      <ul class="history-feature-list"><li v-for="feature in historyFeatures" :key="feature.title"><span class="diary-feature-icon"><AppIcon :name="feature.icon" /></span><div><h3>{{ feature.title }}</h3><p>{{ feature.copy }}</p></div></li></ul>
    </section>

    <section class="diary-section diary-saved" aria-labelledby="diary-saved-title">
      <div class="diary-section-heading"><p class="diary-kicker"><AppIcon name="pin" />02 / СОХРАНЁННЫЕ</p><h2 id="diary-saved-title">У каждой бутылки —<br><span>своё продолжение.</span></h2><p>Нажмите значок булавки в карточке вина: после распознавания, в истории, на карте линейки или в «Вино к блюду». Вино появится в «Сохранённых». Статус можно изменить в любой момент.</p></div>
      <ul class="saved-status-grid"><li v-for="status in SAVED_STATUSES" :key="status" :data-status="status"><AppIcon :name="statusDetails[status].icon" /><h3>{{ SAVED_STATUS_LABELS[status] }}</h3><p>{{ statusDetails[status].copy }}</p></li></ul>
      <div class="diary-keepsake"><AppIcon name="pin" /><p><strong>Сохранённые остаются с вами.</strong> Удаление вина или очистка всей истории не удаляет его из «Сохранённых». Этот список вы собираете сами.</p></div>
    </section>

    <section class="diary-section diary-notes" aria-labelledby="diary-notes-title">
      <div class="diary-section-heading"><p class="diary-kicker"><AppIcon name="book" />03 / ЛИЧНЫЕ ЗАМЕТКИ</p><h2 id="diary-notes-title">Не только название.<br><span>Ваши впечатления.</span></h2><p>Добавьте к сохранённому вину свою заметку: вкус, повод, блюдо или место покупки. Она видна только вам и сохраняется автоматически. Текст заметок тоже участвует в поиске по «Сохранённым».</p></div>
      <figure class="diary-note-example"><span class="note-label">ЛИЧНАЯ ЗАМЕТКА · ПРИМЕР</span><blockquote>«Понравилось за ужином с друзьями. В следующий раз хочу сравнить с другим вином этой винодельни.»</blockquote><figcaption><AppIcon name="shield" />Ваши слова. Только в вашем дневнике.</figcaption></figure>
    </section>

    <section id="diary-connections" class="diary-section diary-connections" aria-labelledby="diary-connections-title">
      <div class="diary-section-heading"><p class="diary-kicker">04 / СВЯЗАННЫЕ МЕССЕНДЖЕРЫ</p><h2 id="diary-connections-title">Оба чата —<br><span>в вашем аккаунте.</span></h2><p>Откройте «Настройки» → «Связанные мессенджеры» → «Привязать мессенджер». Привяжите каждый мессенджер к тому же аккаунту и проверьте переключатель «Записывать найденные вина».</p></div>
      <div class="connection-grid">
        <article><AppIcon name="telegram" /><h3>Telegram</h3><p>Выберите «Telegram», нажмите «Открыть Telegram» и подтвердите привязку в чате с ботом. Одноразовую ссылку не пересылайте другим людям.</p><NuxtLink class="diary-text-link" to="/telegram-bot">О боте в Telegram<AppIcon name="arrow" /></NuxtLink></article>
        <article><AppIcon name="message" /><h3>MAX</h3><p>Выберите «MAX» и откройте мини-приложение по ссылке или QR-коду. Войдите по коду из письма, используя почту своего аккаунта на сайте, и подтвердите привязку. Историю смотрите на сайте.</p><NuxtLink class="diary-text-link" to="/max-bot">О боте в MAX<AppIcon name="arrow" /></NuxtLink></article>
      </div>
      <div class="connection-bottom"><p>В дневник можно войти по коду из письма или с Яндекс ID. Telegram и MAX сохраняют находки после привязки; вход в аккаунт выполняется на сайте.</p><NuxtLink class="button secondary" to="/account?tab=settings"><AppIcon name="plus" />Привязать мессенджер</NuxtLink></div>
    </section>

    <section class="diary-section diary-control" aria-labelledby="diary-control-title"><div><p class="diary-kicker"><AppIcon name="shield" />ПОД ВАШИМ КОНТРОЛЕМ</p><h2 id="diary-control-title">Ваш дневник.<br><span>Ваши решения.</span></h2></div><ul><li><AppIcon name="check" /><p>Выключите запись новых находок в настройках. Уже записанные вина останутся в истории.</p></li><li><AppIcon name="check" /><p>Удалите отдельное вино или очистите всю историю. Сохранёнными винами управляйте отдельно.</p></li><li><AppIcon name="check" /><p>Отвяжите мессенджер или удалите аккаунт и его данные в настройках.</p></li></ul></section>

    <section class="diary-final" aria-labelledby="diary-final-title"><div><p class="diary-kicker"><AppIcon name="book" />ВАШИ ВИННЫЕ НАХОДКИ</p><h2 id="diary-final-title">Начните<br><span>свою коллекцию.</span></h2><p>Войдите на сайте — аккаунт создаётся при первом входе. Дневник доступен совершеннолетним. Обработка данных описана в <NuxtLink to="/privacy">политике конфиденциальности</NuxtLink>.</p></div><div class="diary-final-actions"><NuxtLink class="button primary" to="/account">Открыть «Винный дневник»<AppIcon name="arrow-up-right" /></NuxtLink><NuxtLink class="diary-text-link" to="/"><AppIcon name="scan" />Сначала найти вино по фото</NuxtLink></div></section>
  </main>
</template>

<style scoped>
.diary-landing { --diary-soft: color-mix(in srgb, var(--ink) 75%, var(--paper)); width: calc(100% - 80px); max-width: 1240px; margin: 0 auto; padding: 42px 0 24px; }
.diary-kicker { display: flex; align-items: center; gap: 9px; color: var(--accent); font-size: 10px; line-height: 1.7; letter-spacing: .13em; font-weight: 600; }
.diary-kicker .icon { width: 18px; height: 18px; }
.diary-hero { display: grid; grid-template-columns: .9fr 1.1fr; align-items: center; gap: 46px; padding: 54px; border: 1px solid var(--line); border-radius: 34px; background: linear-gradient(135deg, var(--paper), var(--cream)); }
.diary-hero-copy { min-width: 0; }
.diary-hero h1 { margin: 22px 0 24px; font-size: clamp(52px, 5.8vw, 80px); letter-spacing: -.045em; line-height: 1.06; }
.diary-hero h1 span, .diary-section h2 span, .diary-final h2 span { color: var(--accent); }
.diary-lead { color: var(--diary-soft); font-size: 16px; line-height: 1.8; }
.diary-actions { display: flex; flex-direction: column; align-items: flex-start; gap: 14px; margin-top: 30px; }
.diary-actions .button { width: auto; padding-inline: 25px; min-height: 54px; }
.diary-text-link { display: inline-flex; align-items: center; gap: 9px; min-height: 44px; color: var(--accent); font-size: 13px; line-height: 1.5; }
.diary-text-link:hover { text-decoration: underline; text-underline-offset: 4px; }
.diary-text-link .icon { width: 17px; height: 17px; }
.diary-hero-facts { display: flex; flex-wrap: wrap; gap: 7px; padding: 0; margin: 20px 0 0; list-style: none; }
.diary-hero-facts li { padding: 7px 10px; border: 1px solid var(--line); border-radius: 20px; color: var(--diary-soft); font-size: 10px; }
.diary-preview { min-width: 0; margin: 0; padding: 24px; background: var(--paper); border: 1px solid var(--line); border-radius: 24px; box-shadow: 0 24px 70px #56382012; }
.preview-heading { display: flex; align-items: center; gap: 8px; margin-bottom: 20px; font-family: 'Playfair Display', Georgia, serif; font-size: 20px; }
.preview-heading>.icon { color: var(--accent); width: 22px; height: 22px; }
.preview-badge { margin-left: auto; padding: 4px 7px; border-radius: 6px; background: var(--cream); color: var(--diary-soft); font: 10px/1.5 system-ui, sans-serif; }
.preview-tabs { display: flex; gap: 6px; border-bottom: 1px solid var(--line); }
.preview-tabs button { min-height: 44px; display: flex; align-items: center; justify-content: center; gap: 6px; flex: 1; padding: 8px; border-bottom: 2px solid transparent; color: var(--diary-soft); font-size: 12px; }
.preview-tabs button[aria-selected='true'] { border-color: var(--accent); color: var(--accent); font-weight: 600; }
.preview-tabs .icon { width: 16px; height: 16px; }
.preview-panel { min-height: 480px; padding-top: 14px; }
.preview-filters { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 12px; }
.preview-filters button { min-height: 44px; padding: 7px 9px; border: 1px solid var(--line); border-radius: 13px; color: var(--diary-soft); background: var(--paper); font-size: 10px; }
.preview-filters button[aria-pressed='true'] { background: var(--accent); border-color: var(--accent); color: var(--paper); }
.preview-history-hint { margin: 0 0 12px; color: var(--diary-soft); font-size: 12px; line-height: 1.6; }
.preview-wines { display: grid; gap: 9px; margin: 0; padding: 0; list-style: none; }
.preview-wine { display: grid; grid-template-columns: 48px minmax(0, 1fr); gap: 13px; padding: 12px; background: var(--cream); border-radius: 13px; }
.preview-bottle { display: grid; align-items: start; justify-items: center; }
.preview-bottle img { width: 43px; height: 92px; object-fit: contain; }
.preview-wine-copy { min-width: 0; }
.preview-wine h3 { margin: 0 0 4px; font: 500 15px/1.35 'Playfair Display', Georgia, serif; }
.preview-producer { color: var(--diary-soft); font-size: 10px; line-height: 1.5; }
.preview-status, .preview-source { display: inline-flex; align-items: center; gap: 4px; margin-top: 7px; color: var(--accent); font-size: 10px; font-weight: 600; line-height: 1.5; }
.preview-status .icon { width: 12px; height: 12px; }
.preview-wine-note { margin-top: 6px; color: var(--diary-soft); font-size: 10px; line-height: 1.5; }
.diary-preview figcaption { margin-top: 16px; color: var(--diary-soft); font-size: 10px; line-height: 1.6; }
.diary-section { margin-top: 96px; }
.diary-section-heading h2, .diary-control h2, .diary-final h2 { margin: 16px 0 20px; font-size: clamp(38px, 4.5vw, 60px); line-height: 1.12; letter-spacing: -.035em; }
.diary-section-heading>p:last-of-type, .diary-control p, .diary-final>div>p:last-child { color: var(--diary-soft); font-size: 14px; line-height: 1.8; }
.diary-history { display: grid; grid-template-columns: 1fr 1fr; gap: 80px; align-items: center; padding: 0 38px; }
.diary-history .diary-text-link { margin-top: 16px; }
.history-feature-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 30px; }
.history-feature-list li { display: grid; grid-template-columns: 50px minmax(0, 1fr); gap: 20px; }
.diary-feature-icon { display: grid; place-items: center; width: 50px; height: 50px; border-radius: 16px; background: var(--cream); color: var(--accent); }
.history-feature-list h3 { margin: 0 0 8px; font: 500 23px/1.3 'Playfair Display', Georgia, serif; }
.history-feature-list p, .saved-status-grid p, .connection-grid p { color: var(--diary-soft); font-size: 13px; line-height: 1.75; }
.diary-saved { padding: 56px; border: 1px solid var(--line); border-radius: 32px; background: var(--cream); }
.diary-saved .diary-section-heading { max-width: 720px; }
.saved-status-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 34px 0 0; padding: 0; list-style: none; }
.saved-status-grid li { padding: 24px 20px; background: var(--paper); border: 1px solid var(--line); border-radius: 18px; }
.saved-status-grid .icon { width: 29px; height: 29px; margin-bottom: 20px; color: var(--accent); }
.saved-status-grid h3 { margin: 0 0 10px; font: 500 22px/1.25 'Playfair Display', Georgia, serif; }
.diary-keepsake { display: flex; align-items: flex-start; gap: 12px; max-width: 820px; margin-top: 28px; color: var(--diary-soft); font-size: 13px; line-height: 1.7; }
.diary-keepsake .icon { width: 19px; height: 19px; margin-top: 2px; color: var(--accent); }
.diary-keepsake strong { color: var(--ink); }
.diary-notes { display: grid; grid-template-columns: 1fr 1fr; align-items: center; gap: 70px; padding: 0 38px; }
.diary-note-example { margin: 0; padding: 36px; border: 1px solid var(--line); border-radius: 22px; background: var(--cream); }
.note-label { color: var(--diary-soft); font-size: 9px; letter-spacing: .13em; }
.diary-note-example blockquote { margin: 22px 0 24px; font: 500 27px/1.5 'Playfair Display', Georgia, serif; color: var(--accent); }
.diary-note-example figcaption { display: flex; gap: 8px; align-items: center; color: var(--diary-soft); font-size: 11px; line-height: 1.6; }
.diary-note-example .icon { width: 17px; height: 17px; }
.diary-connections { padding: 56px; border: 1px solid var(--line); border-radius: 32px; background: var(--paper); scroll-margin-top: 100px; }
.diary-connections .diary-section-heading { max-width: 740px; }
.connection-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-top: 32px; }
.connection-grid article { padding: 28px; border-radius: 20px; background: var(--cream); }
.connection-grid article>.icon { width: 30px; height: 30px; color: var(--accent); }
.connection-grid h3 { margin: 18px 0 12px; font: 500 28px/1.2 'Playfair Display', Georgia, serif; }
.connection-grid .diary-text-link { margin-top: 12px; }
.connection-bottom { display: flex; align-items: center; justify-content: space-between; gap: 32px; margin-top: 28px; }
.connection-bottom p { max-width: 660px; color: var(--diary-soft); font-size: 12px; line-height: 1.75; }
.connection-bottom .button { width: auto; flex-shrink: 0; padding-inline: 22px; }
.diary-control { display: grid; grid-template-columns: 1fr 1fr; gap: 80px; align-items: center; padding: 0 38px; }
.diary-control ul { display: grid; gap: 20px; list-style: none; margin: 0; padding: 0; }
.diary-control li { display: flex; align-items: flex-start; gap: 14px; }
.diary-control li>.icon { margin-top: 3px; color: var(--accent); }
.diary-final { display: grid; grid-template-columns: 1fr .85fr; gap: 64px; align-items: center; margin-top: 96px; padding: 56px; border-radius: 32px; background: var(--cream); }
.diary-final a:not(.button) { color: var(--accent); }
.diary-final p a { text-decoration: underline; text-underline-offset: 3px; }
.diary-final-actions { display: grid; gap: 16px; }
.diary-final-actions .button { min-height: 56px; width: 100%; }
.diary-final-actions .diary-text-link { justify-content: center; }
@media (max-width: 1100px) {
  .diary-hero { padding: 36px; gap: 30px; }
  .diary-preview { padding: 18px; }
  .preview-heading { font-size: 18px; }
  .diary-history, .diary-notes, .diary-control { gap: 38px; padding-inline: 20px; }
  .diary-saved, .diary-connections { padding: 40px; }
  .saved-status-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .connection-bottom { align-items: flex-start; flex-direction: column; gap: 20px; }
}
@media (max-width: 900px) {
  .diary-landing { width: calc(100% - 48px); }
  .diary-hero { grid-template-columns: 1fr; padding: 42px; }
  .diary-hero-copy { max-width: 580px; }
  .diary-hero h1 { font-size: 72px; }
  .diary-preview { max-width: 580px; width: 100%; justify-self: center; padding: 26px; }
  .diary-history, .diary-notes, .diary-control { grid-template-columns: 1fr; gap: 34px; }
  .diary-final { grid-template-columns: 1fr; gap: 28px; padding: 42px; }
}
@media (max-width: 600px) {
  .diary-landing { width: calc(100% - 32px); padding-top: 28px; }
  .diary-hero { padding: 28px 20px; gap: 32px; border-radius: 25px; }
  .diary-hero h1 { font-size: clamp(45px, 11.8vw, 68px); }
  .diary-lead { font-size: 14px; }
  .diary-actions { align-items: stretch; }
  .diary-actions .button { width: 100%; }
  .diary-actions .diary-text-link { justify-content: center; }
  .diary-preview { padding: 15px 12px; border-radius: 18px; }
  .preview-heading { flex-wrap: wrap; gap: 6px; font-size: 16px; }
  .preview-heading>.icon { width: 18px; height: 18px; }
  .preview-badge { font-size: 9px; }
  .preview-tabs button { gap: 4px; padding-inline: 3px; font-size: 11px; }
  .preview-tabs .icon { width: 14px; height: 14px; }
  .preview-wine { grid-template-columns: 34px minmax(0, 1fr); padding: 10px; gap: 10px; }
  .preview-bottle img { width: 33px; height: 84px; }
  .preview-wine h3 { font-size: 14px; }
  .preview-producer, .preview-wine-note, .preview-status, .preview-source { font-size: 10px; }
  .diary-section { margin-top: 64px; }
  .diary-history, .diary-notes, .diary-control { padding-inline: 6px; }
  .diary-section-heading h2, .diary-control h2, .diary-final h2 { font-size: clamp(34px, 9vw, 46px); }
  .diary-saved, .diary-connections { padding: 30px 22px; border-radius: 25px; }
  .saved-status-grid, .connection-grid { grid-template-columns: 1fr; }
  .saved-status-grid li { padding: 22px; }
  .saved-status-grid .icon { margin-bottom: 12px; }
  .diary-note-example { padding: 26px; }
  .diary-note-example blockquote { font-size: 24px; }
  .connection-grid article { padding: 22px; }
  .connection-bottom .button { width: 100%; }
  .diary-final { margin-top: 64px; padding: 32px 22px; border-radius: 25px; }
  .diary-final-actions .button { font-size: 12px; }
}
</style>
