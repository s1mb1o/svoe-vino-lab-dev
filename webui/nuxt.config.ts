export default defineNuxtConfig({
  compatibilityDate: '2026-09-15',
  devtools: { enabled: false },
  css: ['~/assets/main.css'],
  runtimeConfig: {
    predictionMode: 'mock',
    predictionEndpoint: '',
    shelfMode: 'disabled',
  },
  app: {
    head: {
      htmlAttrs: { lang: 'ru' },
      title: 'Найти вино по фото — Свое Вино',
      meta: [{ name: 'description', content: 'Сфотографируйте этикетку российского вина. Найдите название, фото бутылки и карточку на портале «Свое Вино».' }],
      link: [{ rel: 'icon', type: 'image/svg+xml', href: '/reference/favicon.svg' }],
    },
  },
  routeRules: { '/wines': { redirect: '/' }, '/wines/': { redirect: '/' } },
  nitro: { preset: 'node-server' },
})
