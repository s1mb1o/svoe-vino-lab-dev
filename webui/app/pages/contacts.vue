<script setup lang="ts">
import { contactChannels, operator } from '~/data/legal'

const contents = [
  { id: 'about', title: 'О сервисе' },
  { id: 'operator', title: 'Оператор' },
  { id: 'channels', title: 'Способы связи' },
  { id: 'complaints', title: 'Жалобы на контент' },
  { id: 'data-requests', title: 'Запросы о персональных данных' },
]
</script>

<template>
  <LegalPage
    path="/contacts"
    title="Контакты — Что за вино?"
    heading="Контакты"
    description="Оператор сервиса «Что за вино?», способы связи, жалобы на контент и запросы о персональных данных."
    lead="Здесь указан оператор сервиса «Что за вино?» и способы связи с ним: вопросы, жалобы на контент и запросы о персональных данных."
    :contents="contents"
  >
    <section id="about" aria-labelledby="about-title">
      <h2 id="about-title">О сервисе</h2>
      <p>«Что за вино?» распознаёт российское вино по фотографии и показывает страницу вина в каталоге портала «Свое Вино» (<a href="https://vino-svoe.ru/" target="_blank" rel="noopener noreferrer">vino-svoe.ru</a>). Сведения носят справочный характер и не являются предложением о продаже.</p>
      <p>Сервис работает на сайте chtozavino.ru, в боте <a href="https://t.me/ChtoZaVinoBot" target="_blank" rel="noopener noreferrer">@ChtoZaVinoBot</a> в Telegram, в боте <a href="https://max.ru/se14697933_bot" target="_blank" rel="noopener noreferrer">@se14697933_bot</a> в MAX и в приложении для Android. Приложение для iOS пока не распространяется.</p>
      <dl>
        <dt>Возрастная категория</dt><dd>18+</dd>
        <dt>Разработчик</dt><dd>Команда ALOLA 1</dd>
      </dl>
    </section>

    <section id="operator" aria-labelledby="operator-title">
      <h2 id="operator-title">Оператор</h2>
      <p>Оператор сервиса и оператор персональных данных:</p>
      <dl>
        <dt>ФИО</dt><dd>{{ operator.name }}</dd>
        <dt>Статус</dt><dd>{{ operator.status }}</dd>
        <dt>ИНН</dt><dd>{{ operator.inn }}</dd>
      </dl>
    </section>

    <section id="channels" aria-labelledby="channels-title">
      <h2 id="channels-title">Способы связи</h2>
      <dl>
        <template v-for="channel in contactChannels" :key="channel.id">
          <dt>{{ channel.label }}</dt><dd><a :href="channel.href" :target="channel.id === 'email' ? undefined : '_blank'" :rel="channel.id === 'email' ? undefined : 'noopener noreferrer'">{{ channel.value }}</a></dd>
        </template>
      </dl>
      <p>Укажите, о каком сервисе идёт речь: сайт, бот в Telegram, бот в MAX, приложение для Android или iOS.</p>
    </section>

    <section id="complaints" aria-labelledby="complaints-title">
      <h2 id="complaints-title">Жалобы на контент</h2>
      <p>Сообщите оператору о незаконном контенте или о нарушении <NuxtLink to="/terms">Условий использования</NuxtLink>. В жалобе укажите:</p>
      <ul>
        <li>сервис и примерные дату и время отправки фотографии;</li>
        <li>что нарушает закон или Условия использования;</li>
        <li>для ботов — ваш user ID или ID пользователя, на которого вы жалуетесь, если он известен.</li>
      </ul>
      <p>Оператор проверяет жалобу, удаляет незаконный контент и может ограничить доступ к сервису нарушителю. Оператор выполняет и требования платформ Telegram и MAX, а также уполномоченных государственных органов.</p>
    </section>

    <section id="data-requests" aria-labelledby="data-requests-title">
      <h2 id="data-requests-title">Запросы о персональных данных</h2>
      <p>Вы можете узнать, какие ваши данные хранит оператор, попросить исправить или удалить их и отозвать согласие. Права описаны в <NuxtLink to="/privacy#rights">Политике обработки персональных данных</NuxtLink>.</p>
      <p>Чтобы оператор нашёл ваши данные в боте, укажите ваш user ID:</p>
      <ul>
        <li>в MAX бот показывает ваш MAX user ID в ответе на команду /privacy;</li>
        <li>в Telegram укажите ваш username или пришлите сообщение с того аккаунта, которым вы пользовались ботом.</li>
      </ul>
      <p>Оператор отвечает на запрос в течение 10 рабочих дней.</p>
    </section>
  </LegalPage>
</template>
