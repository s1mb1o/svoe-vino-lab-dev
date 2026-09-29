import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { MAX_IMAGE_BYTES } from '../shared/catalog'
import { SHELF_EXAMPLES } from '../shared/shelf'

const publicFile = (path: string) => fileURLToPath(new URL(`../public/${path}`, import.meta.url))
const sharedAssetFile = (path: string) => fileURLToPath(new URL(`../../assets/${path}`, import.meta.url))

async function pngSize(path: string) {
  const png = await readFile(publicFile(path))
  expect(png.subarray(1, 4).toString()).toBe('PNG')
  return { width: png.readUInt32BE(16), height: png.readUInt32BE(20) }
}

async function jpegSize(path: string) {
  const jpeg = await readFile(publicFile(path))
  expect(jpeg.readUInt16BE(0)).toBe(0xffd8)
  for (let offset = 2; offset < jpeg.length;) {
    const marker = jpeg.readUInt16BE(offset)
    if (marker >= 0xffc0 && marker <= 0xffc2) return { width: jpeg.readUInt16BE(offset + 7), height: jpeg.readUInt16BE(offset + 5) }
    offset += 2 + jpeg.readUInt16BE(offset + 2)
  }
  throw new Error(`${path} has no JPEG frame header`)
}

describe('PWA assets', () => {
  it('uses the Nuxt PWA module with generated Workbox output', async () => {
    const config = await readFile(fileURLToPath(new URL('../nuxt.config.ts', import.meta.url)), 'utf8')
    const packageJson = JSON.parse(await readFile(fileURLToPath(new URL('../package.json', import.meta.url)), 'utf8'))
    expect(packageJson.devDependencies['@vite-pwa/nuxt']).toBe('^1.1.1')
    expect(config).toContain("modules: ['@vite-pwa/nuxt']")
    expect(config).toContain("registerType: 'prompt'")
    expect(config).toContain("{ name: 'theme-color', media: '(prefers-color-scheme: light)', content: '#7b3528' }")
    expect(config).toContain("{ name: 'theme-color', media: '(prefers-color-scheme: dark)', content: '#211e1c' }")
    expect(config).toContain("'_nuxt/**/*.{js,css}'")
    expect(config).toContain('navigateFallback: null')
    expect(config).toContain("!url.pathname.startsWith('/api/')")
    expect(config).toContain("!url.pathname.startsWith('/v1/')")
    expect(await readFile(fileURLToPath(new URL('../app/app.vue', import.meta.url)), 'utf8')).toContain('<NuxtPwaManifest />')
  })

  it('provides icons at their declared sizes', async () => {
    const config = await readFile(fileURLToPath(new URL('../nuxt.config.ts', import.meta.url)), 'utf8')
    const sharedLogo = await readFile(sharedAssetFile('product-logo-640x640.svg'))
    expect(config).toContain("{ rel: 'icon', type: 'image/svg+xml', href: '/icons/product-logo.svg' }")
    await expect(readFile(publicFile('icons/product-logo.svg'))).resolves.toEqual(sharedLogo)
    await expect(pngSize('icons/pwa-192.png')).resolves.toEqual({ width: 192, height: 192 })
    await expect(pngSize('icons/pwa-512.png')).resolves.toEqual({ width: 512, height: 512 })
    await expect(pngSize('icons/pwa-maskable-512.png')).resolves.toEqual({ width: 512, height: 512 })
    await expect(pngSize('icons/apple-touch-icon.png')).resolves.toEqual({ width: 180, height: 180 })
  })

  it('provides manifest screenshots at their declared sizes', async () => {
    const config = await readFile(fileURLToPath(new URL('../nuxt.config.ts', import.meta.url)), 'utf8')
    expect(config).toContain("src: '/screenshots/home-narrow.jpg', sizes: '1080x1920', type: 'image/jpeg', form_factor: 'narrow'")
    expect(config).toContain("src: '/screenshots/home-wide.jpg', sizes: '1920x1200', type: 'image/jpeg', form_factor: 'wide'")
    await expect(jpegSize('screenshots/home-narrow.jpg')).resolves.toEqual({ width: 1080, height: 1920 })
    await expect(jpegSize('screenshots/home-wide.jpg')).resolves.toEqual({ width: 1920, height: 1200 })
  })

  it('provides each owner-supplied shelf example as an uploadable WebP file', async () => {
    for (const example of SHELF_EXAMPLES) {
      const image = await readFile(publicFile(example.src.slice(1)))
      expect(image.subarray(0, 4).toString()).toBe('RIFF')
      expect(image.subarray(8, 12).toString()).toBe('WEBP')
      expect(image.byteLength).toBeLessThan(MAX_IMAGE_BYTES)
    }
  })
})
