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

describe('PWA assets', () => {
  it('uses the Nuxt PWA module with generated Workbox output', async () => {
    const config = await readFile(fileURLToPath(new URL('../nuxt.config.ts', import.meta.url)), 'utf8')
    const packageJson = JSON.parse(await readFile(fileURLToPath(new URL('../package.json', import.meta.url)), 'utf8'))
    expect(packageJson.devDependencies['@vite-pwa/nuxt']).toBe('^1.1.1')
    expect(config).toContain("modules: ['@vite-pwa/nuxt']")
    expect(config).toContain("registerType: 'autoUpdate'")
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

  it('provides each owner-supplied shelf example as an uploadable WebP file', async () => {
    for (const example of SHELF_EXAMPLES) {
      const image = await readFile(publicFile(example.src.slice(1)))
      expect(image.subarray(0, 4).toString()).toBe('RIFF')
      expect(image.subarray(8, 12).toString()).toBe('WEBP')
      expect(image.byteLength).toBeLessThan(MAX_IMAGE_BYTES)
    }
  })
})
