import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'

assert(process.env.PLAYWRIGHT_MODULE, 'Set PLAYWRIGHT_MODULE to the installed playwright/index.mjs.')
const { chromium, webkit } = await import(process.env.PLAYWRIGHT_MODULE)
const origin = process.env.PORTAL_ORIGIN || 'http://127.0.0.1:18557'
const output = process.env.CROCODILE_REPORT_DIR || 'reports/crocodile'
const password = process.env.PORTAL_PASSWORD_FILE ? (await readFile(process.env.PORTAL_PASSWORD_FILE, 'utf8')).trimEnd() : null
const httpCredentials = password ? { username: 'chtozavino', password } : undefined
const headers = password ? { Authorization: `Basic ${Buffer.from(`chtozavino:${password}`).toString('base64')}` } : undefined
await mkdir(output, { recursive: true })
const manifest = JSON.parse(await readFile('docs/crocodile-media/asset-manifest.json', 'utf8'))
for (const name of ['cards-a4.pdf', 'box-a4.pdf']) {
  const response = await fetch(`${origin}/crocodile/downloads/${name}`, { headers })
  assert.equal(response.status, 200)
  const bytes = Buffer.from(await response.arrayBuffer())
  assert.equal(bytes.subarray(0, 5).toString(), '%PDF-')
  assert.equal(createHash('sha256').update(bytes).digest('hex'), manifest.assets[`public/crocodile/downloads/${name}`].sha256)
}
const results = []
for (const [engine, browserType] of [['chromium', chromium], ['webkit', webkit]]) {
  const browser = await browserType.launch({ headless: true })
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, serviceWorkers: 'block', colorScheme: 'light', httpCredentials })
    await context.route(/https:\/\/mc\.yandex\.(ru|com)\//, route => route.fulfill({ status: 200, body: '' }))
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    page.on('console', message => { if (/hydration/i.test(message.text())) errors.push(message.text()) })
    await page.goto(`${origin}/crocodile`, { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: 'Да, мне есть 18 лет', exact: true }).waitFor()
    assert(await page.locator('.site-shell').evaluate(node => node.inert))
    // The age confirmation belongs only to this synthetic local test visitor.
    await page.getByRole('button', { name: 'Да, мне есть 18 лет', exact: true }).click()
    await page.getByRole('dialog').waitFor({ state: 'detached' })
    await page.evaluate(() => document.fonts.ready)
    assert.equal(await page.locator('h1').count(), 1)
    assert.match(await page.title(), /Винный крокодил/)
    assert.equal(await page.locator('link[rel="canonical"]').count(), 1)
    assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'), 'https://chtozavino.ru/crocodile')
    assert.match(await page.locator('.header-section').innerText(), /Винный крокодил/)
    if (process.env.REQUIRE_ACCOUNT_LINK === '1') assert(await page.locator('.account-navigation').isVisible())
    assert.equal(await page.locator('.wc-card').count(), 6)
    for (const name of ['Красные', 'Белые', 'Розовые']) {
      await page.getByRole('button', { name, exact: true }).click()
      assert.equal(await page.locator('.wc-card').count(), 2)
    }
    await page.getByRole('button', { name: 'Белые', exact: true }).click()
    const card = page.getByTestId('crocodile-card-W08')
    assert.match(await card.innerText(), /Легенда|ЛЕГЕНДА/)
    assert.match(await card.innerText(), /История не подтверждена/)
    await card.click()
    assert.equal(await card.getAttribute('aria-pressed'), 'true')
    assert.equal(await card.locator('.wc-back-label').count(), 1)
    await card.press('Space')
    assert.equal(await card.getAttribute('aria-pressed'), 'false')
    await page.getByRole('button', { name: 'Все карточки', exact: true }).click()
    assert.equal(await page.locator('.wc-card').count(), 6)
    await page.getByText('Нужно ли открывать вино?', { exact: true }).click()
    assert(await page.getByText('Необязательно. Вино — тема игры, а не условие участия.', { exact: false }).isVisible())
    await page.getByText('Нужно ли открывать вино?', { exact: true }).press('Enter')
    assert.equal(await page.locator('details[open]').count(), 0)
    for (const image of await page.locator('.crocodile-page img').all()) {
      await image.scrollIntoViewIfNeeded()
      await image.evaluate(node => node.decode())
    }
    for (const theme of ['light', 'dark']) {
      await page.emulateMedia({ colorScheme: theme, reducedMotion: 'reduce' })
      await page.reload({ waitUntil: 'networkidle' })
      await page.evaluate(() => document.fonts.ready)
      assert.equal(await page.locator('html').getAttribute('data-theme'), theme)
      const colors = await page.evaluate(() => ({
        background: getComputedStyle(document.documentElement).backgroundColor,
        text: getComputedStyle(document.querySelector('.wc-hero-tagline')).color,
        quiet: getComputedStyle(document.querySelector('.wc-lead')).color,
        buttonText: getComputedStyle(document.querySelector('.wc-actions .primary')).color,
        buttonBackground: getComputedStyle(document.querySelector('.wc-actions .primary')).backgroundColor,
      }))
      function luminance(value) {
        const channels = value.match(/[\d.]+/g).slice(0, 3).map(Number).map(channel => channel / 255)
        return channels.map(channel => channel <= .04045 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4).reduce((sum, channel, index) => sum + channel * [.2126, .7152, .0722][index], 0)
      }
      function contrast(a, b) { const x = luminance(a), y = luminance(b); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05) }
      assert(theme === 'dark' ? luminance(colors.background) < .15 : luminance(colors.background) > .8, `${engine} ${theme} keeps the portal background`)
      assert(contrast(colors.text, colors.background) >= 7, `${engine} ${theme} main text contrast`)
      assert(contrast(colors.quiet, colors.background) >= 4.5, `${engine} ${theme} body text contrast`)
      assert(contrast(colors.buttonText, colors.buttonBackground) >= 4.5, `${engine} ${theme} primary button contrast`)

      for (const width of [1440, 768, 390, 320]) {
        await page.setViewportSize({ width, height: width < 768 ? 844 : 1000 })
        for (const image of await page.locator('.crocodile-page img').all()) {
          await image.scrollIntoViewIfNeeded()
          await image.evaluate(node => node.decode())
        }
        await page.evaluate(() => window.scrollTo(0, 0))
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), `${engine} ${theme} ${width}px horizontal overflow`)
        assert(await page.getByTestId('crocodile-rules').evaluate(node => node.getBoundingClientRect().height >= 44))
        for (const selector of ['.wc-hero-photo > img', '.wc-story figure img']) {
          const ratio = await page.locator(selector).evaluate(node => { const rect = node.getBoundingClientRect(); return rect.width / rect.height })
          assert(Math.abs(ratio - 4 / 3) < .02, `${engine} ${theme} ${width}px photo ratio ${selector}`)
        }
        if (width === 1440) await page.screenshot({ path: `${output}/${engine}-${theme}-hero.png`, fullPage: false })

        assert(await page.locator('.wc-card img').evaluateAll(images => images.every(node => node.complete && node.naturalWidth > 0)))
        if ([1440, 390].includes(width)) await page.screenshot({ path: `${output}/${engine}-${theme}-${width}.png`, fullPage: true })
        results.push({ engine, theme, width, passed: true })
      }
    }
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto(`${origin}/ideas`, { waitUntil: 'networkidle' })
    await page.getByTestId('ideas-crocodile-link').click()
    await page.waitForURL(`${origin}/crocodile`)
    await page.locator('#crocodile-title').waitFor()
    assert.deepEqual(errors, [], `${engine} browser errors`)
    await context.close()
  } finally {
    await browser.close()
  }
}
await writeFile(`${output}/results.json`, JSON.stringify({ passed: true, layouts: results, checks: ['age gate retained', 'metadata and navigation', 'mode filters', 'mouse and keyboard card flips', 'legend status', 'FAQ', 'exact print-master download hashes', 'system themes', 'local images', 'horizontal overflow'] }, null, 2) + '\n')
console.log(`Passed ${results.length} layouts in Chromium and WebKit, card interactions, FAQ, navigation, and PDF hashes.`)
