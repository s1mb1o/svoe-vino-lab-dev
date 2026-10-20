import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const projectFile = (path: string) => fileURLToPath(new URL(`../${path}`, import.meta.url))
const source = (path: string) => readFile(projectFile(path), 'utf8')

describe('iPhone landing page', () => {
  it('publishes verified iPhone capabilities and the release-status link', async () => {
    const page = await source('app/pages/iphone.vue')
    for (const text of [
      'iOS 17.2+',
      '2 093 вина',
      'Core ML и Neural Engine',
      'SigLIP2 Base NaFlex p512',
      'DIS или YOLO26n-seg',
      'VoiceOver',
      'Dynamic Type',
    ]) expect(page).toContain(text)
    expect(page).toContain('https://github.com/s1mb1o/svoe-vino-lab-dev/issues/36')
    expect(page).not.toContain('TestFlight готовится')
    expect(page).not.toContain('Публичной ссылки на установку пока нет')
    expect(page).not.toContain('Веб-сканер уже доступен')
    expect(page).not.toContain('downloadUrl:')
  })

  it('provides the verified simulator screenshots as WebP', async () => {
    for (const filename of ['01-main.webp', '02-settings.webp']) {
      const image = await readFile(projectFile(`public/screenshots/iphone/${filename}`))
      expect(image.subarray(0, 4).toString()).toBe('RIFF')
      expect(image.subarray(8, 12).toString()).toBe('WEBP')
      expect(image.byteLength).toBeGreaterThan(40_000)
    }
  })

  it('publishes metadata, navigation, and cache policy for the iPhone route', async () => {
    const [page, app, sitemap, config] = await Promise.all([
      source('app/pages/iphone.vue'),
      source('app/app.vue'),
      source('public/sitemap.xml'),
      source('nuxt.config.ts'),
    ])
    expect(page).toContain("href: 'https://chtozavino.ru/iphone'")
    expect(page).toContain("'@type': 'SoftwareApplication'")
    expect(app).toContain("route.path.startsWith('/iphone')")
    expect(app).toContain('<NuxtLink to="/android">Android<AppIcon name="arrow-up-right" /></NuxtLink><NuxtLink to="/iphone">iPhone<AppIcon name="arrow-up-right" /></NuxtLink>')
    expect(sitemap).toContain('<loc>https://chtozavino.ru/iphone</loc>')
    expect(config).toContain("'/screenshots/iphone/**'")
  })
})
