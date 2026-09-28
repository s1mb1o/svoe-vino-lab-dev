import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const projectFile = (path: string) => fileURLToPath(new URL(`../${path}`, import.meta.url))
const source = (path: string) => readFile(projectFile(path), 'utf8')

describe('search discovery', () => {
  it('keeps the page server-rendered behind the age overlay', async () => {
    const app = await source('app/app.vue')
    const gate = await source('app/components/AgeGate.vue')
    expect(app).toContain('computed(() => !ageChecked.value || !ageConfirmed.value)')
    expect(app.indexOf('<NuxtPage />')).toBeLessThan(app.indexOf('<AgeGate'))
    expect(app).toContain(':inert="ageGateOpen"')
    expect(app).toContain('<AgeGate v-if="ageGateOpen"')
    expect(app).not.toContain('v-else class="site-shell"')
    expect(gate).toContain('<h2 id="age-heading">')
    expect(gate).not.toContain('<main')
  })

  it('declares the canonical page and public metadata', async () => {
    const config = await source('nuxt.config.ts')
    expect(config).toContain("const siteUrl = 'https://chtozavino.ru/'")
    expect(config).toContain("{ rel: 'canonical', href: siteUrl }")
    expect(config).toContain("{ property: 'og:url', content: siteUrl }")
    expect(config).toContain("{ name: 'twitter:card', content: 'summary' }")
    expect(config).toContain("'@type': 'WebSite'")
    expect(config).toContain("'@type': 'WebApplication'")
  })

  it('publishes crawl discovery files', async () => {
    const robots = await source('public/robots.txt')
    const sitemap = await source('public/sitemap.xml')
    expect(robots).toContain('Sitemap: https://chtozavino.ru/sitemap.xml')
    expect(robots).toContain('Disallow: /api/')
    expect(sitemap).toContain('<loc>https://chtozavino.ru/</loc>')
  })

  it('uses permanent compatibility redirects and bounded static caching', async () => {
    const config = await source('nuxt.config.ts')
    const detailRedirect = await source('server/routes/wines/[slug].get.ts')
    expect(config).toContain("redirect: { to: '/', statusCode: 308 }")
    expect(config).toContain("'/reference/**': { headers: { 'cache-control': 'public, max-age=604800, stale-while-revalidate=86400' } }")
    expect(detailRedirect).toContain(', 308)')
  })
})
