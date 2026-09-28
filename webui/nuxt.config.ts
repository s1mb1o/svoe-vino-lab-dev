export default defineNuxtConfig({
  compatibilityDate: '2026-09-15',
  devtools: { enabled: false },
  modules: ['@vite-pwa/nuxt'],
  css: ['~/assets/main.css'],
  runtimeConfig: {
    predictionMode: 'mock',
    predictionEndpoint: '',
  },
  app: {
    head: {
      htmlAttrs: { lang: 'ru' },
      title: 'Найти вино по фото — Свое Вино',
      meta: [
        { name: 'description', content: 'Сфотографируйте этикетку российского вина. Найдите название, фото бутылки и карточку на портале «Свое Вино».' },
        { name: 'theme-color', content: '#7b3528' },
        { name: 'mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-status-bar-style', content: 'default' },
        { name: 'apple-mobile-web-app-title', content: 'Свое Вино' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/icons/pwa-icon.svg' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/icons/apple-touch-icon.png' },
      ],
    },
  },
  pwa: {
    registerType: 'autoUpdate',
    registerWebManifestInRouteRules: true,
    includeAssets: [
      'icons/pwa-icon.svg',
      'icons/apple-touch-icon.png',
      'reference/logo.svg',
      'reference/background.webp',
      'reference/playfair-display.woff2',
    ],
    manifest: {
      id: '/',
      name: 'Свое Вино — поиск по фото',
      short_name: 'Свое Вино',
      description: 'Поиск российского вина по фотографии этикетки.',
      lang: 'ru',
      start_url: '/',
      scope: '/',
      display: 'standalone',
      background_color: '#fefdfa',
      theme_color: '#7b3528',
      icons: [
        { src: '/icons/pwa-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
        { src: '/icons/pwa-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
        { src: '/icons/pwa-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
      ],
    },
    workbox: {
      cacheId: 'svoe-vino-webui',
      cleanupOutdatedCaches: true,
      globPatterns: [
        '_nuxt/**/*.{js,css}',
        'icons/*.{png,svg}',
        'reference/{logo.svg,background.webp,playfair-display.woff2}',
      ],
      navigateFallback: null,
      runtimeCaching: [{
        urlPattern: ({ request, url }) => request.mode === 'navigate'
          && !url.pathname.startsWith('/api/')
          && !url.pathname.startsWith('/v1/'),
        handler: 'NetworkFirst',
        options: {
          cacheName: 'svoe-vino-pages',
          networkTimeoutSeconds: 5,
          cacheableResponse: { statuses: [0, 200] },
          expiration: { maxEntries: 4, maxAgeSeconds: 7 * 24 * 60 * 60 },
        },
      }],
    },
    devOptions: { enabled: false },
  },
  routeRules: { '/wines': { redirect: '/' }, '/wines/': { redirect: '/' } },
  nitro: { preset: 'node-server' },
})
