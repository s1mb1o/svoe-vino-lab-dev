import { access, readFile, readdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { legalPaths } from '../app/data/legal'
import { sitemapSections } from '../app/data/sitemap'

const projectFile = (path: string) => fileURLToPath(new URL(`../${path}`, import.meta.url))
const source = (path: string) => readFile(projectFile(path), 'utf8')
const htmlPages = sitemapSections.flatMap(section => section.pages)
const htmlPaths = htmlPages.map(page => page.path)

async function xmlPaths(): Promise<string[]> {
  const xml = await source('public/sitemap.xml')
  return [...xml.matchAll(/<loc>https:\/\/chtozavino\.ru([^<]*)<\/loc>/g)].map(match => match[1] || '/')
}

// Route patterns that the server or the page itself marks as noindex.
async function noindexPatterns(): Promise<RegExp[]> {
  const config = await source('nuxt.config.ts')
  const fromRules = [...config.matchAll(/'([^']+)': \{ headers: \{ 'x-robots-tag': 'noindex/g)].map(match => match[1]!)
  const pageFiles = (await readdir(projectFile('app/pages'), { recursive: true })).filter(file => file.endsWith('.vue'))
  const fromPages: string[] = []
  for (const file of pageFiles) {
    if (!(await source(`app/pages/${file}`)).includes("robots: 'noindex")) continue
    fromPages.push(`/${file.replace(/\.vue$/, '').replace(/(^|\/)index$/, '').replace(/\[[^\]]+\]/g, '*')}`)
  }
  return [...fromRules, ...fromPages].map(pattern => new RegExp(`^${pattern.replace(/\*\*?/g, '[^]+')}$`))
}

describe('public site map', () => {
  it('lists the same pages as the XML sitemap', async () => {
    const xml = await xmlPaths()
    expect(xml).toContain('/sitemap')
    expect(new Set(htmlPaths).size).toBe(htmlPaths.length)
    expect([...htmlPaths].sort()).toEqual(xml.filter(path => path !== '/sitemap').sort())
  })

  it('includes the legal pages', () => {
    const legal = sitemapSections.find(section => section.id === 'legal')
    expect(legal?.pages.map(page => page.path)).toEqual(legalPaths)
  })

  it('omits the direct-access and noindex pages', async () => {
    const patterns = await noindexPatterns()
    expect(patterns.some(pattern => pattern.test('/lineup/abrau-durso'))).toBe(true)
    expect(patterns.some(pattern => pattern.test('/account'))).toBe(true)
    for (const path of [...htmlPaths, ...(await xmlPaths())]) {
      expect(patterns.filter(pattern => pattern.test(path)), path).toEqual([])
    }
  })

  it('links only to existing pages', async () => {
    for (const path of htmlPaths) {
      const file = path === '/' ? 'app/pages/index.vue' : `app/pages${path}.vue`
      const index = `app/pages${path}/index.vue`
      await expect(access(projectFile(file)).catch(() => access(projectFile(index))), path).resolves.toBeUndefined()
    }
  })

  it('gives every page a label, a description, and a defined icon', async () => {
    const icons = await source('app/components/AppIcon.vue')
    const page = await source('app/pages/sitemap.vue')
    const templateIcons = [...page.matchAll(/<AppIcon name="([a-z-]+)"/g)].map(match => match[1]!)
    for (const item of htmlPages) {
      expect(item.label.trim(), item.path).not.toBe('')
      expect(item.description.trim(), item.path).not.toBe('')
    }
    for (const icon of new Set([...htmlPages.map(item => item.icon), ...templateIcons])) {
      expect(icons, icon).toMatch(new RegExp(`^\\s+'?${icon}'?: '`, 'm'))
    }
  })

  it('is linked from the shared footer', async () => {
    const app = await source('app/app.vue')
    expect(app).toMatch(/<NuxtLink to="\/sitemap">Карта сайта/)
    expect(app).toContain("isSitemapPage ? 'Карта сайта'")
  })
})
