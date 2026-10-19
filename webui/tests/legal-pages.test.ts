import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { contactChannels, legalLinks, legalPaths, legalRevision, operator } from '../app/data/legal'

const projectFile = (path: string) => fileURLToPath(new URL(`../${path}`, import.meta.url))
const source = (path: string) => readFile(projectFile(path), 'utf8')
const pages = { '/terms': 'app/pages/terms.vue', '/privacy': 'app/pages/privacy.vue', '/contacts': 'app/pages/contacts.vue' }

function validPersonalInn(inn: string): boolean {
  if (!/^\d{12}$/.test(inn)) return false
  const digits = [...inn].map(Number)
  const check = (weights: number[]) => weights.reduce((sum, weight, index) => sum + weight * digits[index]!, 0) % 11 % 10
  return check([7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) === digits[10] && check([3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) === digits[11]
}

describe('legal pages', () => {
  it('publishes the three shared paths', () => {
    expect(legalPaths).toEqual(['/terms', '/privacy', '/contacts'])
    expect(legalLinks.map(link => link.label)).toEqual(['Условия использования', 'Политика обработки персональных данных', 'Контакты'])
  })

  it('identifies the operator with a valid personal INN', () => {
    expect(operator.name).toBe('Шмелев Александр Сергеевич')
    expect(operator.status).toContain('плательщик налога на профессиональный доход')
    expect(validPersonalInn(operator.inn)).toBe(true)
    expect(validPersonalInn('772326685407')).toBe(false)
  })

  it('uses an ISO revision date', () => {
    expect(legalRevision).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('offers only HTTPS and mail contact links', () => {
    expect(contactChannels.map(channel => channel.id)).toContain('email')
    for (const channel of contactChannels) expect(channel.href).toMatch(/^(https:\/\/|mailto:)/)
  })

  it('renders each page with the shared layout and its canonical path', async () => {
    for (const [path, file] of Object.entries(pages)) {
      const page = await source(file)
      expect(page).toContain('<LegalPage')
      expect(page).toContain(`path="${path}"`)
    }
    const layout = await source('app/components/LegalPage.vue')
    expect(layout).toContain("const canonical = `https://chtozavino.ru${props.path}`")
    expect(layout).toContain('<main id="main-content" class="legal-page">')
    expect(layout).toContain('Редакция от {{ legalRevisionLabel }}')
  })

  it('opens the legal pages without the age gate', async () => {
    const app = await source('app/app.vue')
    expect(app).toContain("const isLegalPage = computed(() => legalPaths.includes(route.path.replace(/\\/$/, '')))")
    expect(app).toContain('computed(() => !isLegalPage.value && (!ageChecked.value || !ageConfirmed.value))')
  })

  it('links the pages from the footer and the XML sitemap', async () => {
    const app = await source('app/app.vue')
    const sitemap = await source('public/sitemap.xml')
    expect(app).toContain('<nav class="legal-navigation" aria-label="Правовая информация">')
    for (const path of legalPaths) expect(sitemap).toContain(`<loc>https://chtozavino.ru${path}</loc>`)
  })

  it('keeps a stable fragment for every service in the terms and the policy', async () => {
    for (const file of [pages['/terms'], pages['/privacy']]) {
      const page = await source(file)
      for (const id of ['site', 'telegram', 'max', 'android', 'ios']) expect(page).toContain(`<section id="${id}" aria-labelledby="${id}-title">`)
    }
  })

  it('states the retention and does not claim Metrika consent before the banner exists', async () => {
    const privacy = await source(pages['/privacy'])
    const scanner = await source('app/components/PhotoScanner.vue')
    expect(privacy).toContain('включая резервные копии, хранятся 30 дней')
    expect(privacy).toContain('https://yandex.ru/support/metrica/general/opt-out.html')
    expect(privacy).not.toMatch(/согласи/i)
    expect(scanner).not.toContain('Фото не сохраняется')
    expect(scanner).toContain('<NuxtLink to="/privacy#site">Фото хранится 30 дней</NuxtLink>')
  })

  it('gives every table-of-contents entry a matching section', async () => {
    for (const file of Object.values(pages)) {
      const page = await source(file)
      const ids = [...page.matchAll(/\{ id: '([a-z-]+)', title: /g)].map(match => match[1])
      expect(ids.length).toBeGreaterThan(0)
      for (const id of ids) expect(page).toContain(`<section id="${id}" aria-labelledby="${id}-title">`)
    }
  })
})
