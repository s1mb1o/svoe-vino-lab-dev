import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { ANDROID_RELEASE, DEFAULT_ANDROID_APK_URL } from '../shared/android'

const projectFile = (path: string) => fileURLToPath(new URL(`../${path}`, import.meta.url))
const source = (path: string) => readFile(projectFile(path), 'utf8')

describe('Android landing page', () => {
  it('publishes the selected product benefits and verified examples', async () => {
    const page = await source('app/pages/android.vue')
    for (const text of [
      'Работает без интернета',
      'Поиск по изображению',
      'QR и штрихкоды',
      'Обработка на устройстве',
      '2 093 вина внутри',
      'Автоматический ускоритель',
      'История результатов',
      'Светлая и тёмная темы',
      'Пино Нуар',
      'Шато Тамань. Каберне Совиньон',
    ]) expect(page).toContain(text)
    expect(page).toContain('data-testid="android-download"')
    expect(page).toContain(':href="apkUrl"')
    expect(page).toContain(':download="ANDROID_RELEASE.apkFileName"')
    expect(page).toContain('Тестовая версия подписана ключом разработчика')
  })

  it('keeps one versioned release contract for the page and download route', async () => {
    expect(ANDROID_RELEASE).toMatchObject({
      version: '0.2.0',
      versionCode: 6,
      applicationId: 'com.alolalab.chtozavino',
      minAndroid: 9,
      catalogueSize: 2093,
      apkFileName: 'chtozavino-0.2.0-release-test-signed.apk',
      apkBytes: 414_941_197,
      sha256: '6c9ba0c364f762023818cd6d6885e16359c146e23bc84d8316343a9836c34cb3',
    })
    expect(DEFAULT_ANDROID_APK_URL).toBe('/downloads/chtozavino-0.2.0-release-test-signed.apk')
    const route = await source('server/routes/downloads/[filename].get.ts')
    expect(route).toContain("filename !== ANDROID_RELEASE.apkFileName")
    expect(route).toContain("'Content-Type': 'application/vnd.android.package-archive'")
    expect(route).toContain("'Content-Length': String(apkStat.size)")
    expect(route).toContain('attachment; filename=')
    expect(route).toContain('createReadStream(apkPath)')
  })

  it('distinguishes the new encoder and package from historical screenshots', async () => {
    const page = await source('app/pages/android.vue')
    expect(page).toContain('SigLIP2 Base NaFlex p512')
    expect(page).toContain('весь кадр без сегментации')
    expect(page).toContain('Скриншоты ниже сделаны в версии 0.1.4')
    expect(page).toContain('история автоматически не переносится')
  })

  it('provides every verified Android screenshot as WebP', async () => {
    const screenshots = [
      '02_bottle_selected_light.webp',
      '03_bottle_selected_dark.webp',
      '04_recognition_result_dark.webp',
      '05_processing_pipeline_dark.webp',
      '07_settings_dark.webp',
      '08_barcode_result_dark.webp',
    ]
    for (const filename of screenshots) {
      const image = await readFile(projectFile(`public/screenshots/android/${filename}`))
      expect(image.subarray(0, 4).toString()).toBe('RIFF')
      expect(image.subarray(8, 12).toString()).toBe('WEBP')
      expect(image.byteLength).toBeGreaterThan(30_000)
    }
  })

  it('publishes search metadata and navigation for the Android route', async () => {
    const [page, app, sitemap, config] = await Promise.all([
      source('app/pages/android.vue'),
      source('app/app.vue'),
      source('public/sitemap.xml'),
      source('nuxt.config.ts'),
    ])
    expect(page).toContain("href: 'https://chtozavino.ru/android'")
    expect(page).toContain("'@type': 'SoftwareApplication'")
    expect(app).toContain("(isAndroidPage || isIphonePage) ? '/' : '/android'")
    expect(sitemap).toContain('<loc>https://chtozavino.ru/android</loc>')
    expect(config).toContain('androidApkPath: defaultAndroidApkPath')
    expect(config).toContain('androidApkUrl: DEFAULT_ANDROID_APK_URL')
    expect(config).toContain("'/screenshots/android/**'")
  })
})
