<script setup lang="ts">
import type { BotLanding } from '~/data/botLandings'

// The layout of /iphone for the Telegram and MAX bots. The chat in the hero is drawn in HTML:
// it is an example, not a platform screenshot.
const props = defineProps<{ bot: BotLanding }>()
const bot = props.bot
const canonical = `https://chtozavino.ru${bot.path}`
const exampleWine = {
  name: 'Абрау-Дюрсо Пино Нуар',
  producer: 'Абрау-Дюрсо',
  color: 'Красное',
  sugar: 'Сухое',
  grapes: 'Пино Нуар',
  image: '/line-wines/abrau-dyurso-abrau-dyurso-pino-nuar-krasnoe-suhoe-13.webp',
}
const chatLabel = `Пример переписки с ботом в ${bot.platform}: человек отправил фото бутылки, бот поставил фото в очередь и прислал карточку вина «${exampleWine.name}» с кнопками «Открыть страницу вина», «Совпало» и «Не совпало».`

useSeoMeta({
  title: bot.title,
  description: bot.description,
  ogType: 'website',
  ogTitle: bot.title,
  ogDescription: bot.description,
  ogUrl: canonical,
  twitterCard: 'summary',
  twitterTitle: bot.title,
  twitterDescription: bot.description,
})

useHead({
  link: [{ rel: 'canonical', href: canonical }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: bot.title,
      description: bot.description,
      url: canonical,
      inLanguage: 'ru',
      isPartOf: { '@id': 'https://chtozavino.ru/#website' },
      about: {
        '@type': 'SoftwareApplication',
        name: `Что за вино? — бот в ${bot.platform}`,
        url: bot.url,
        applicationCategory: 'LifestyleApplication',
        inLanguage: 'ru',
        offers: { '@type': 'Offer', price: '0', priceCurrency: 'RUB' },
      },
    }),
  }],
})
</script>

<template>
  <main id="main-content" class="bot-page">
    <section class="bot-hero" aria-labelledby="bot-title">
      <div class="bot-hero-copy">
        <p class="bot-kicker"><AppIcon :name="bot.icon" />БОТ В {{ bot.platform.toUpperCase() }}</p>
        <h1 id="bot-title">Вино в кадре.<br><span>Ответ в {{ bot.platform }}.</span></h1>
        <p class="bot-lead">Отправьте боту фотографию бутылки. Он найдёт российское вино в каталоге и пришлёт карточку в этот же чат.</p>
        <div class="bot-actions">
          <a class="button primary" :href="bot.url" target="_blank" rel="noopener noreferrer" data-testid="bot-open"><AppIcon :name="bot.icon" />Открыть {{ bot.handle }}</a>
          <NuxtLink class="button secondary" to="/"><AppIcon name="scan" />Открыть веб-сканер</NuxtLink>
        </div>
        <ul class="bot-facts" aria-label="Возможности и условия">
          <li>Фото или альбом</li>
          <li>JPEG · PNG · WebP · HEIC</li>
          <li>50 фото в час</li>
          <li>Бесплатно</li>
          <li>18+</li>
        </ul>
      </div>

      <figure class="bot-hero-visual">
        <span class="bot-halo bot-halo-one" aria-hidden="true" />
        <span class="bot-halo bot-halo-two" aria-hidden="true" />
        <div class="bot-device" role="img" :aria-label="chatLabel">
          <div class="chat-screen">
            <div class="chat-head">
              <img src="/icons/product-logo.svg" alt="" width="32" height="32">
              <span><strong>Что за вино?</strong>бот · {{ bot.handle }}</span>
            </div>
            <div class="chat-feed">
              <div class="chat-photo"><img :src="exampleWine.image" width="112" height="360" alt=""></div>
              <p class="chat-bubble">Фотография принята и поставлена в очередь.<br>Позиция: 1; обработка начнётся сразу.</p>
              <div class="chat-card">
                <div class="chat-card-image"><img :src="exampleWine.image" width="112" height="360" alt=""></div>
                <p>Похоже, это:</p>
                <p><strong>{{ exampleWine.name }}</strong></p>
                <p>🏡 <b>Винодельня:</b> {{ exampleWine.producer }}<br>🍷 <b>Цвет:</b> {{ exampleWine.color }}<br>🍬 <b>Сахар:</b> {{ exampleWine.sugar }}<br>🍇 <b>Виноград:</b> {{ exampleWine.grapes }}</p>
              </div>
              <div class="chat-buttons">
                <span class="wide">Открыть страницу вина</span>
                <span>✅ Совпало</span>
                <span>❌ Не совпало</span>
              </div>
            </div>
            <div class="chat-input"><span>Сообщение</span><AppIcon name="camera" /></div>
          </div>
        </div>
        <div class="bot-note bot-note-queue" aria-hidden="true"><AppIcon name="history" /><span><strong>Очередь</strong>позиция и время</span></div>
        <div class="bot-note bot-note-diary" aria-hidden="true"><AppIcon name="book" /><span><strong>Дневник</strong>находки сохраняются</span></div>
        <figcaption>Пример переписки · не снимок экрана {{ bot.platform }}</figcaption>
      </figure>
    </section>

    <section class="bot-section" aria-labelledby="bot-benefits-title">
      <div class="bot-heading">
        <p class="bot-kicker"><span />ВОЗМОЖНОСТИ БОТА</p>
        <h2 id="bot-benefits-title">Всё о найденном вине&nbsp;— <span>в переписке</span></h2>
        <p>Бот работает в привычном чате {{ bot.platform }}. Устанавливать приложение не нужно. Фото обрабатывает сервер, поэтому нужен интернет.</p>
      </div>
      <ul class="bot-benefit-grid">
        <li v-for="benefit in bot.benefits" :key="benefit.title" class="bot-benefit-card">
          <span class="bot-benefit-icon"><AppIcon :name="benefit.icon" /></span>
          <h3>{{ benefit.title }}</h3>
          <p>{{ benefit.copy }}</p>
        </li>
      </ul>
    </section>

    <section class="bot-section bot-steps-section" aria-labelledby="bot-steps-title">
      <div class="bot-heading left">
        <p class="bot-kicker"><span />ЧЕТЫРЕ ШАГА</p>
        <h2 id="bot-steps-title">От фотографии до <span>карточки вина</span></h2>
        <p>Распознавание может ошибаться. Всегда сравнивайте название и изображение с этикеткой своей бутылки.</p>
      </div>
      <ol class="bot-step-list">
        <li v-for="(step, index) in bot.steps" :key="step.number" class="bot-step-card">
          <span class="bot-step-number">{{ step.number }}</span>
          <span class="bot-step-icon"><AppIcon :name="step.icon" /></span>
          <h3>{{ step.title }}</h3>
          <p>{{ step.copy }}</p>
          <AppIcon v-if="index < bot.steps.length - 1" class="bot-step-arrow" name="arrow" />
        </li>
      </ol>
    </section>

    <section class="bot-section bot-diary-section" aria-labelledby="bot-diary-title">
      <div class="bot-diary-copy">
        <p class="bot-kicker"><span />ВИННЫЙ ДНЕВНИК</p>
        <h2 id="bot-diary-title">Находки из чата&nbsp;—<br><span>в вашем дневнике</span></h2>
        <p>{{ bot.diaryCopy }}</p>
        <dl class="bot-diary-facts">
          <div v-for="fact in bot.diaryFacts" :key="fact.term"><dt>{{ fact.term }}</dt><dd>{{ fact.value }}</dd></div>
        </dl>
      </div>
      <div class="bot-diary-card">
        <h3>Как привязать {{ bot.platform }}</h3>
        <ol>
          <li v-for="(step, index) in bot.diarySteps" :key="step"><span>{{ index + 1 }}</span>{{ step }}</li>
        </ol>
        <p class="bot-diary-note"><AppIcon name="info" />{{ bot.diaryNote }}</p>
        <NuxtLink class="button secondary" to="/account"><AppIcon name="book" />Открыть «Винный дневник»</NuxtLink>
      </div>
    </section>

    <section class="bot-section bot-commands-section" aria-labelledby="bot-commands-title">
      <div class="bot-commands-copy">
        <p class="bot-kicker"><AppIcon name="menu" />КОМАНДЫ</p>
        <h2 id="bot-commands-title">Подсказки и статистика&nbsp;— <span>прямо в чате</span></h2>
        <p>Команды есть в меню бота. Их можно отправить и обычным сообщением.</p>
      </div>
      <dl class="bot-command-list">
        <div v-for="command in bot.commands" :key="command.name"><dt>{{ command.name }}</dt><dd>{{ command.copy }}</dd></div>
      </dl>
    </section>

    <section class="bot-final" aria-labelledby="bot-final-title">
      <div>
        <p class="bot-kicker"><AppIcon :name="bot.icon" />{{ bot.platform.toUpperCase() }} · {{ bot.handle.toUpperCase() }}</p>
        <h2 id="bot-final-title">Следующая бутылка&nbsp;—<br><span>одно фото в чат.</span></h2>
        <p>Бот бесплатный и доступен только совершеннолетним. Как бот обрабатывает фото и данные, описано в <NuxtLink :to="`/privacy#${bot.privacyAnchor}`">политике конфиденциальности</NuxtLink>.</p>
      </div>
      <div class="bot-final-actions">
        <a class="button primary" :href="bot.url" target="_blank" rel="noopener noreferrer">Открыть бота в {{ bot.platform }}<AppIcon name="arrow-up-right" /></a>
        <NuxtLink class="bot-final-link" to="/">Открыть веб-сканер<AppIcon name="arrow" /></NuxtLink>
      </div>
    </section>
  </main>
</template>

<style scoped>
/* --muted has 3.93:1 on --paper in the light theme. This mix has at least 5.7:1 on --paper and --cream in both themes. */
.bot-page { --bot-soft: color-mix(in srgb, var(--ink) 75%, var(--paper)); max-width: 1240px; width: calc(100% - 80px); margin: 0 auto; padding: 42px 0 20px; }
.bot-hero { min-height: 700px; display: grid; grid-template-columns: .96fr 1.04fr; gap: 54px; align-items: center; padding: 54px 62px; overflow: hidden; position: relative; border: 1px solid var(--line); border-radius: 34px; background: linear-gradient(138deg, var(--paper) 0 43%, var(--cream) 100%); box-shadow: 0 20px 70px #5638200b; }
.bot-hero-copy { position: relative; z-index: 4; }
.bot-kicker { display: inline-flex; align-items: center; gap: 9px; color: var(--accent); font-size: 10px; font-weight: 600; letter-spacing: .15em; }
.bot-kicker>span { width: 18px; height: 1px; background: currentColor; }
.bot-kicker .icon { width: 18px; height: 18px; }
.bot-hero h1 { max-width: 620px; margin: 18px 0 22px; font-size: clamp(50px, 5.3vw, 76px); line-height: 1.06; letter-spacing: -.052em; }
.bot-hero h1 span, .bot-heading h2 span, .bot-diary-copy h2 span, .bot-commands-copy h2 span, .bot-final h2 span { color: var(--accent); }
.bot-lead { max-width: 555px; color: var(--bot-soft); font-size: 17px; line-height: 1.72; }
.bot-actions { display: flex; flex-wrap: wrap; gap: 11px; margin-top: 31px; }
.bot-actions .button { width: auto; min-height: 54px; padding-inline: 24px; }
.bot-facts { display: flex; flex-wrap: wrap; gap: 7px; margin: 21px 0 0; padding: 0; list-style: none; }
.bot-facts li { padding: 7px 10px; border: 1px solid var(--line); border-radius: 18px; background: var(--paper); color: var(--bot-soft); font-size: 10px; }
.bot-hero-visual { min-height: 590px; position: relative; display: grid; place-items: center; align-content: center; gap: 22px; margin: 0; }
.bot-hero-visual figcaption { position: relative; z-index: 3; color: var(--bot-soft); font-size: 9px; text-align: center; }
.bot-halo { position: absolute; border: 1px solid color-mix(in srgb, var(--accent) 23%, transparent); border-radius: 50%; }
.bot-halo-one { width: 530px; height: 530px; }
.bot-halo-two { width: 395px; height: 395px; }
.bot-device { z-index: 2; position: relative; width: 274px; aspect-ratio: 1206 / 2622; overflow: hidden; container-type: inline-size; border: 8px solid #1f1d1c; border-radius: 48px; background: var(--cream); box-shadow: 0 30px 60px #3d251c2d; transform: rotate(3.5deg); }
/* Font sizes in cqw follow the device width, so the chat keeps its proportions at every width. */
.chat-screen { height: 100%; display: flex; flex-direction: column; color: var(--ink); font-size: 10px; font-size: 3.9cqw; line-height: 1.38; }
.chat-head { display: flex; align-items: center; gap: .7em; padding: 2.6em 1.2em .8em; border-bottom: 1px solid var(--line); background: var(--paper); }
.chat-head img { width: 2.6em; height: 2.6em; border-radius: 50%; background: var(--cream); }
.chat-head span { display: flex; flex-direction: column; color: var(--bot-soft); font-size: .85em; }
.chat-head strong { color: var(--ink); font-size: 1.18em; font-weight: 600; }
.chat-feed { flex: 1; min-height: 0; display: flex; flex-direction: column; justify-content: flex-end; gap: .6em; overflow: hidden; padding: .8em .9em; }
.chat-photo { align-self: flex-end; display: grid; place-items: center; width: 42%; height: 9.5em; flex-shrink: 0; overflow: hidden; border-radius: 1.2em 1.2em .3em 1.2em; background: color-mix(in srgb, var(--accent) 18%, var(--paper)); }
.chat-photo img { height: 8.2em; width: auto; }
.chat-bubble { align-self: flex-start; max-width: 88%; padding: .6em .8em; border-radius: 1.2em 1.2em 1.2em .3em; background: var(--paper); font-size: .92em; }
.chat-card { align-self: flex-start; width: 84%; overflow: hidden; border-radius: 1.2em 1.2em 1.2em .3em; background: var(--paper); font-size: .92em; }
.chat-card-image { display: grid; place-items: center; height: 8.6em; overflow: hidden; background: #fff; }
.chat-card-image img { height: 7.6em; width: auto; }
.chat-card p { padding: 0 .8em; }
.chat-card p:nth-child(2) { margin-top: .5em; }
.chat-card p + p { margin-top: .35em; }
.chat-card p:last-child { padding-bottom: .6em; }
.chat-buttons { display: grid; grid-template-columns: 1fr 1fr; gap: .3em; width: 84%; }
.chat-buttons span { padding: .45em .3em; border-radius: .7em; background: color-mix(in srgb, var(--paper) 72%, transparent); color: var(--accent); font-size: .85em; font-weight: 600; text-align: center; }
.chat-buttons .wide { grid-column: 1 / -1; }
.chat-input { display: flex; align-items: center; justify-content: space-between; margin: 0 .9em 1.4em; padding: .6em 1em; border-radius: 2em; background: var(--paper); color: var(--bot-soft); }
.chat-input .icon { width: 1.4em; height: 1.4em; }
.bot-note { position: absolute; z-index: 3; display: flex; align-items: center; gap: 10px; padding: 13px 15px; border: 1px solid var(--line); border-radius: 15px; background: color-mix(in srgb, var(--paper) 93%, transparent); box-shadow: 0 14px 34px #3d251c1b; backdrop-filter: blur(12px); color: var(--bot-soft); font-size: 9px; line-height: 1.4; }
.bot-note .icon { width: 22px; height: 22px; color: var(--accent); }
.bot-note span { display: flex; flex-direction: column; }
.bot-note strong { color: var(--ink); font-size: 11px; font-weight: 600; }
.bot-note-queue { left: 3%; top: 24%; }
.bot-note-diary { right: 1%; bottom: 21%; }
.bot-section { margin-top: 96px; }
.bot-heading { max-width: 760px; margin: 0 auto 36px; text-align: center; }
.bot-heading.left { max-width: 720px; margin-left: 0; text-align: left; }
.bot-heading h2, .bot-diary-copy h2, .bot-commands-copy h2, .bot-final h2 { margin: 14px 0; font-size: clamp(38px, 4.2vw, 58px); line-height: 1.13; letter-spacing: -.035em; }
.bot-heading>p:last-child, .bot-diary-copy>p, .bot-commands-copy>p, .bot-final>div>p:last-child { color: var(--bot-soft); font-size: 14px; line-height: 1.75; }
.bot-final>div>p:last-child a { color: var(--accent); text-decoration: underline; text-underline-offset: 3px; }
.bot-benefit-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 13px; margin: 0; padding: 0; list-style: none; }
.bot-benefit-card { min-height: 250px; padding: 25px; border: 1px solid var(--line); border-radius: 21px; background: var(--paper); transition: transform .2s, border-color .2s; }
.bot-benefit-card:hover { transform: translateY(-3px); border-color: color-mix(in srgb, var(--accent) 50%, var(--line)); }
.bot-benefit-icon { width: 48px; height: 48px; display: grid; place-items: center; border-radius: 15px; background: var(--cream); color: var(--accent); }
.bot-benefit-icon .icon { width: 24px; height: 24px; }
.bot-benefit-card h3 { margin: 24px 0 9px; font: 500 20px/1.3 'Playfair Display', Georgia, serif; }
.bot-benefit-card p { color: var(--bot-soft); font-size: 12px; line-height: 1.65; }
.bot-steps-section { padding: 56px clamp(30px, 5vw, 64px) 62px; border: 1px solid var(--line); border-radius: 34px; background: var(--paper); }
.bot-step-list { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 35px 0 0; padding: 0; list-style: none; }
.bot-step-card { min-height: 250px; position: relative; padding: 24px; border-radius: 21px; background: var(--cream); }
.bot-step-number { color: color-mix(in srgb, var(--accent) 60%, var(--bot-soft)); font: 500 22px/1 'Playfair Display', Georgia, serif; }
.bot-step-icon { width: 52px; height: 52px; display: grid; place-items: center; margin-top: 28px; border-radius: 17px; color: var(--accent); background: var(--paper); }
.bot-step-icon .icon { width: 25px; height: 25px; }
.bot-step-card h3 { margin: 20px 0 8px; font: 500 21px/1.25 'Playfair Display', Georgia, serif; }
.bot-step-card p { color: var(--bot-soft); font-size: 11px; line-height: 1.65; }
.bot-step-arrow { position: absolute; z-index: 2; width: 22px; height: 22px; right: -17px; top: 50%; padding: 5px; border-radius: 50%; color: var(--accent); background: var(--paper); transform: translateY(-50%); box-sizing: content-box; }
.bot-diary-section { display: grid; grid-template-columns: 1.18fr minmax(300px, .82fr); gap: clamp(48px, 7vw, 100px); align-items: center; padding: 60px clamp(40px, 7vw, 92px); border-radius: 34px; background: var(--cream); }
.bot-diary-copy h2 { font-size: clamp(40px, 4.5vw, 62px); }
.bot-diary-facts { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; margin: 30px 0 0; overflow: hidden; border: 1px solid var(--line); border-radius: 17px; background: var(--line); }
.bot-diary-facts div { padding: 17px; background: var(--paper); }
.bot-diary-facts dt { color: var(--bot-soft); font-size: 9px; letter-spacing: .08em; text-transform: uppercase; }
.bot-diary-facts dd { margin: 7px 0 0; color: var(--accent); font: 500 19px/1.2 'Playfair Display', Georgia, serif; }
.bot-diary-card { padding: 32px; border: 1px solid var(--line); border-radius: 24px; background: var(--paper); }
.bot-diary-card h3 { margin: 0 0 18px; font: 500 24px/1.25 'Playfair Display', Georgia, serif; }
.bot-diary-card ol { display: grid; gap: 12px; margin: 0; padding: 0; list-style: none; }
.bot-diary-card li { display: grid; grid-template-columns: 30px 1fr; gap: 12px; align-items: start; color: var(--ink); font-size: 13px; line-height: 1.6; }
.bot-diary-card li>span { width: 30px; height: 30px; display: grid; place-items: center; border-radius: 50%; background: var(--cream); color: var(--accent); font: 500 15px/1 'Playfair Display', Georgia, serif; }
.bot-diary-note { display: flex; align-items: flex-start; gap: 8px; margin: 20px 0 22px; color: var(--bot-soft); font-size: 11px; line-height: 1.6; }
.bot-diary-note .icon { width: 16px; height: 16px; margin-top: 2px; flex-shrink: 0; color: var(--accent); }
.bot-diary-card .button { width: 100%; }
.bot-commands-section { display: grid; grid-template-columns: 1fr 1fr; gap: clamp(42px, 7vw, 92px); align-items: center; padding: 58px clamp(38px, 7vw, 84px); border-radius: 34px; color: #f8efe8; background: radial-gradient(circle at 82% 12%, #c47f5940, transparent 35%), #54251f; }
.bot-commands-section .bot-kicker, .bot-commands-section h2 span { color: #efb49c; }
.bot-commands-copy>p { color: #e0c9bd; }
.bot-command-list { display: grid; gap: 10px; margin: 0; }
.bot-command-list div { display: grid; grid-template-columns: 92px 1fr; align-items: center; gap: 12px; min-height: 54px; padding: 8px 14px 8px 10px; border: 1px solid #ffffff1c; border-radius: 15px; background: #ffffff0b; }
.bot-command-list dt { padding: 6px 0; border-radius: 10px; background: #ffffff10; color: #f5d2c0; font: 600 12px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace; text-align: center; }
.bot-command-list dd { margin: 0; color: #ead8cf; font-size: 12px; line-height: 1.5; }
.bot-final { min-height: 310px; display: grid; grid-template-columns: 1.1fr .9fr; align-items: center; gap: 48px; margin: 96px 0 42px; padding: 50px clamp(38px, 7vw, 84px); border: 1px solid var(--line); border-radius: 32px; background: var(--paper); }
.bot-final-actions { display: grid; gap: 16px; text-align: center; }
.bot-final-actions .button { width: 100%; min-height: 58px; font-size: 13px; }
.bot-final-link { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; color: var(--accent); font-size: 12px; }
.bot-final-link:hover { text-decoration: underline; text-underline-offset: 4px; }
.bot-final-link .icon { width: 17px; height: 17px; }
:global(:root[data-theme='dark'] .bot-hero) { box-shadow: none; }
:global(:root[data-theme='dark'] .bot-device) { border-color: #4a4544; }
:global(:root[data-theme='dark'] .bot-note) { background: color-mix(in srgb, var(--paper) 88%, transparent); }
:global(:root[data-theme='dark'] .bot-benefit-card:hover) { border-color: #8e715f; }
@media (max-width: 1023px) {
  .bot-page { width: calc(100% - 48px); }
  .bot-hero { grid-template-columns: 1fr; padding: 48px; }
  .bot-hero-copy { max-width: 700px; }
  .bot-hero-visual { width: min(610px, 100%); margin: 0 auto; }
  .bot-benefit-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .bot-step-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .bot-step-arrow { display: none; }
  .bot-diary-section { grid-template-columns: 1fr; gap: 36px; padding: 48px; }
}
@media (max-width: 767px) {
  .bot-page { width: calc(100% - 32px); padding-top: 28px; }
  .bot-hero { min-height: 0; padding: 32px 22px 38px; border-radius: 25px; }
  .bot-hero h1 { font-size: clamp(42px, 13vw, 59px); }
  .bot-lead { font-size: 14px; }
  .bot-actions { flex-direction: column; }
  .bot-actions .button { width: 100%; }
  .bot-hero-visual { min-height: 520px; margin-top: 16px; }
  .bot-device { width: 220px; border-radius: 40px; }
  .bot-halo-one { width: 410px; height: 410px; }
  .bot-halo-two { width: 310px; height: 310px; }
  .bot-note { padding: 10px; }
  .bot-note-queue { left: -2%; top: 20%; }
  .bot-note-diary { right: -2%; bottom: 17%; }
  .bot-section { margin-top: 68px; }
  .bot-heading { margin-bottom: 25px; }
  .bot-heading h2, .bot-diary-copy h2, .bot-commands-copy h2, .bot-final h2 { font-size: 37px; }
  .bot-benefit-grid { grid-template-columns: 1fr; gap: 10px; }
  .bot-benefit-card { min-height: 0; padding: 20px; display: grid; grid-template-columns: 48px 1fr; column-gap: 16px; }
  .bot-benefit-card h3 { margin: 2px 0 7px; }
  .bot-benefit-card p { grid-column: 2; }
  .bot-steps-section { padding: 34px 22px; border-radius: 25px; }
  .bot-step-list { grid-template-columns: 1fr; }
  .bot-step-card { min-height: 0; display: grid; grid-template-columns: 40px 48px 1fr; column-gap: 12px; align-items: center; padding: 18px; }
  .bot-step-number { font-size: 18px; }
  .bot-step-icon { width: 48px; height: 48px; margin: 0; }
  .bot-step-card h3 { margin: 0; }
  .bot-step-card p { grid-column: 3; margin-top: 6px; }
  .bot-diary-section { padding: 34px 22px; border-radius: 25px; }
  .bot-diary-facts { grid-template-columns: 1fr; }
  .bot-diary-card { padding: 24px 20px; }
  .bot-commands-section { grid-template-columns: 1fr; gap: 30px; padding: 36px 23px; border-radius: 25px; }
  .bot-command-list div { grid-template-columns: 78px 1fr; }
  .bot-final { grid-template-columns: 1fr; gap: 28px; margin-top: 68px; padding: 36px 23px; border-radius: 25px; }
}
@media (max-width: 400px) {
  .bot-hero-visual { min-height: 470px; }
  .bot-device { width: 198px; }
  .bot-note { font-size: 8px; }
  .bot-note strong { font-size: 10px; }
  .bot-note .icon { width: 18px; height: 18px; }
  .bot-facts li { font-size: 9px; }
}
@media (prefers-reduced-motion: reduce) {
  .bot-benefit-card { transition: none; }
  .bot-benefit-card:hover { transform: none; }
}
</style>
