import { access, readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { isMaxAppPath } from '../shared/account'
import { maxBot, telegramBot } from '../app/data/botLandings'
import { sitemapSections } from '../app/data/sitemap'

const projectFile = (path: string) => fileURLToPath(new URL(`../${path}`, import.meta.url))
const source = (path: string) => readFile(projectFile(path), 'utf8')

describe('bot landing pages', () => {
  it('links each page to its bot', () => {
    expect(telegramBot).toMatchObject({ path: '/telegram-bot', platform: 'Telegram', handle: '@ChtoZaVinoBot', url: 'https://t.me/ChtoZaVinoBot', privacyAnchor: 'telegram' })
    expect(maxBot).toMatchObject({ path: '/max-bot', platform: 'MAX', handle: '@se14697933_bot', url: 'https://max.ru/se14697933_bot', privacyAnchor: 'max' })
  })

  it('keeps the MAX page off the mini-app path', () => {
    expect(isMaxAppPath(maxBot.path)).toBe(false)
    expect(isMaxAppPath(telegramBot.path)).toBe(false)
  })

  it('lists the bot features', () => {
    for (const bot of [telegramBot, maxBot]) {
      const text = JSON.stringify(bot)
      for (const feature of ['HEIC', 'альбом', 'Открыть страницу вина', '✅ Совпало', '❌ Не совпало', 'три варианта', 'Винный дневник', '18 лет', '30 дней', '/help', '/stats', '/privacy']) {
        expect(text, `${bot.platform}: ${feature}`).toContain(feature)
      }
      expect(bot.benefits).toHaveLength(8)
      expect(bot.steps.map(step => step.number)).toEqual(['01', '02', '03', '04'])
    }
    // Only the Telegram bot has /unlink. MAX is linked and unlinked in the diary.
    expect(telegramBot.commands.map(command => command.name)).toContain('/unlink')
    expect(maxBot.commands.map(command => command.name)).not.toContain('/unlink')
  })

  it('renders both routes with the shared component and labels the example chat', async () => {
    const [telegram, max, component, privacy] = await Promise.all([
      source('app/pages/telegram-bot.vue'),
      source('app/pages/max-bot.vue'),
      source('app/components/BotLanding.vue'),
      source('app/pages/privacy.vue'),
    ])
    expect(telegram).toContain('<BotLanding :bot="telegramBot" />')
    expect(max).toContain('<BotLanding :bot="maxBot" />')
    expect(component).toContain('const canonical = `https://chtozavino.ru${bot.path}`')
    expect(component).toContain("link: [{ rel: 'canonical', href: canonical }]")
    expect(component).toContain('role="img" :aria-label="chatLabel"')
    expect(component).toContain('Пример переписки · не снимок экрана')
    expect(component.match(/<h1 /g)).toHaveLength(1)
    expect(component).not.toContain("robots: 'noindex")
    for (const anchor of [telegramBot.privacyAnchor, maxBot.privacyAnchor]) expect(privacy).toContain(`<section id="${anchor}"`)
    const image = component.match(/image: '([^']+\.webp)'/)?.[1]
    expect(image).toBeTruthy()
    await expect(access(projectFile(`public${image}`))).resolves.toBeUndefined()
  })

  it('publishes both routes in the site map, the XML sitemap, and the header', async () => {
    const [app, xml] = await Promise.all([source('app/app.vue'), source('public/sitemap.xml')])
    const applications = sitemapSections.find(section => section.id === 'applications')
    expect(applications?.pages.map(page => page.path)).toEqual(['/hackaton', '/shelf-lens', '/android', '/iphone', '/telegram-bot', '/max-bot'])
    for (const path of ['/telegram-bot', '/max-bot']) expect(xml).toContain(`<loc>https://chtozavino.ru${path}</loc>`)
    expect(app).toContain("isTelegramBotPage ? 'Бот в Telegram' : isMaxBotPage ? 'Бот в MAX'")
  })
})
