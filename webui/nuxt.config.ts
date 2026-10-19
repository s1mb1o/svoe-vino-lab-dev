import { fileURLToPath } from 'node:url'
import { THEME_INIT_SCRIPT } from './shared/theme'
import { ANDROID_RELEASE, DEFAULT_ANDROID_APK_URL } from './shared/android'
import { METRIKA_INIT_SCRIPT, METRIKA_NOSCRIPT } from './shared/metrika'

const siteUrl = 'https://chtozavino.ru/'
const siteTitle = 'Найти вино по фото — Что за вино?'
const siteDescription = 'Сфотографируйте этикетку российского вина. Найдите название, фото бутылки и карточку на портале «Свое Вино».'
const socialImage = `${siteUrl}icons/pwa-512.png`
const defaultAndroidApkPath = fileURLToPath(new URL(`../android/app/build/outputs/apk/friendly/${ANDROID_RELEASE.apkFileName}`, import.meta.url))

export default defineNuxtConfig({
  compatibilityDate: '2026-09-15',
  devtools: { enabled: false },
  modules: ['@vite-pwa/nuxt'],
  css: ['~/assets/main.css'],
  vite: { worker: { format: 'es' } },
  runtimeConfig: {
    androidApkPath: defaultAndroidApkPath,
    predictionMode: 'mock',
    predictionEndpoint: '',
    dinnerLensEndpoint: '',
    dinnerLensApiToken: '',
    // «Винный дневник». An empty endpoint turns the account feature off (no header link, no calls).
    accountEndpoint: '',
    // Old name NUXT_ACCOUNT_TOKEN. The server reads ACCOUNT_WEB_TOKEN first (server/utils/account-runtime.ts).
    accountToken: '',
    accountPublicOrigin: 'https://chtozavino.ru',
    // MAX mini app (plan 05). The fixed deep link https://max.ru/<bot>?startapp=account, and the
    // host of the mini-app pages (max.chtozavino.ru). Empty values turn the MAX link off.
    accountMaxAppLink: '',
    accountMaxHost: '',
    public: {
      androidApkUrl: DEFAULT_ANDROID_APK_URL,
    },
  },
  app: {
    head: {
      htmlAttrs: { lang: 'ru' },
      title: siteTitle,
      meta: [
        { name: 'description', content: siteDescription },
        { property: 'og:type', content: 'website' },
        { property: 'og:title', content: siteTitle },
        { property: 'og:description', content: siteDescription },
        { property: 'og:url', content: siteUrl },
        { property: 'og:image', content: socialImage },
        { property: 'og:image:alt', content: 'Что за вино? — поиск российского вина по фотографии' },
        { property: 'og:locale', content: 'ru_RU' },
        { name: 'twitter:card', content: 'summary' },
        { name: 'twitter:title', content: siteTitle },
        { name: 'twitter:description', content: siteDescription },
        { name: 'twitter:image', content: socialImage },
        { name: 'theme-color', media: '(prefers-color-scheme: light)', content: '#7b3528' },
        { name: 'theme-color', media: '(prefers-color-scheme: dark)', content: '#211e1c' },
        { name: 'mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-status-bar-style', content: 'default' },
        { name: 'apple-mobile-web-app-title', content: 'Что за вино?' },
      ],
      link: [
        { rel: 'canonical', href: siteUrl },
        { rel: 'icon', type: 'image/svg+xml', href: '/icons/product-logo.svg' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/icons/apple-touch-icon.png' },
      ],
      noscript: [{ key: 'yandex-metrika', innerHTML: METRIKA_NOSCRIPT, tagPosition: 'bodyOpen' }],
      script: [{ key: 'theme-init', innerHTML: THEME_INIT_SCRIPT, tagPriority: 'critical' }, {
        key: 'yandex-metrika',
        type: 'text/javascript',
        innerHTML: METRIKA_INIT_SCRIPT,
      }, {
        type: 'application/ld+json',
        innerHTML: JSON.stringify({
          '@context': 'https://schema.org',
          '@graph': [
            {
              '@type': 'WebSite',
              '@id': `${siteUrl}#website`,
              url: siteUrl,
              name: 'Что за вино? — поиск по фото',
              description: siteDescription,
              inLanguage: 'ru',
            },
            {
              '@type': 'WebApplication',
              '@id': `${siteUrl}#webapp`,
              url: siteUrl,
              name: 'Что за вино? — поиск по фото',
              description: siteDescription,
              applicationCategory: 'LifestyleApplication',
              operatingSystem: 'Any',
              inLanguage: 'ru',
              isPartOf: { '@id': `${siteUrl}#website` },
              offers: { '@type': 'Offer', price: '0', priceCurrency: 'RUB' },
            },
          ],
        }),
      }],
    },
  },
  pwa: {
    registerType: 'prompt',
    registerWebManifestInRouteRules: true,
    includeAssets: [
      'icons/product-logo.svg',
      'icons/apple-touch-icon.png',
      'reference/logo.svg',
      'reference/background.webp',
      'reference/playfair-display.woff2',
    ],
    manifest: {
      id: '/',
      name: 'Что за вино? — поиск по фото',
      short_name: 'Что за вино?',
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
      screenshots: [
        { src: '/screenshots/home-narrow.jpg', sizes: '1080x1920', type: 'image/jpeg', form_factor: 'narrow', label: 'Поиск вина по фото на телефоне' },
        { src: '/screenshots/home-wide.jpg', sizes: '1920x1200', type: 'image/jpeg', form_factor: 'wide', label: 'Поиск вина по фото на компьютере' },
      ],
    },
    workbox: {
      cacheId: 'svoe-vino-webui',
      cleanupOutdatedCaches: true,
      // Load the large HEIC decoder only when a user selects HEIC, never at first visit.
      globIgnores: ['**/dinner-heic.worker-*.js'],
      globPatterns: [
        '_nuxt/**/*.{js,css}',
        'icons/*.{png,svg}',
        'reference/{logo.svg,background.webp,playfair-display.woff2}',
      ],
      navigateFallback: null,
      runtimeCaching: [{
        urlPattern: ({ request, url }) => request.mode === 'navigate'
          && !url.pathname.startsWith('/api/')
          && !url.pathname.startsWith('/v1/')
          && url.pathname !== '/account' && !url.pathname.startsWith('/account/')
          && url.pathname !== '/max' && !url.pathname.startsWith('/max/'),
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
  routeRules: {
    // The index /lineup is public. Each producer map stays a noindex review page.
    '/lineup/*': { headers: { 'x-robots-tag': 'noindex, nofollow, noarchive' } },
    '/hackaton': { headers: { 'x-robots-tag': 'noindex, nofollow, noarchive' } },
    '/account': { headers: { 'x-robots-tag': 'noindex, nofollow, noarchive', 'cache-control': 'no-store' } },
    '/account/**': { headers: { 'x-robots-tag': 'noindex, nofollow, noarchive', 'cache-control': 'no-store' } },
    '/max': { headers: { 'x-robots-tag': 'noindex, nofollow, noarchive', 'cache-control': 'no-store' } },
    '/max/**': { headers: { 'x-robots-tag': 'noindex, nofollow, noarchive', 'cache-control': 'no-store' } },
    '/hackaton/**': { headers: { 'x-robots-tag': 'noindex, nofollow, noarchive' } },
    '/wines': { redirect: { to: '/', statusCode: 308 } },
    '/wines/': { redirect: { to: '/', statusCode: 308 } },
    '/reference/**': { headers: { 'cache-control': 'public, max-age=604800, stale-while-revalidate=86400' } },
    '/screenshots/android/**': { headers: { 'cache-control': 'public, max-age=604800, stale-while-revalidate=86400' } },
    '/screenshots/iphone/**': { headers: { 'cache-control': 'public, max-age=604800, stale-while-revalidate=86400' } },
  },
  nitro: { preset: 'node-server' },
})
