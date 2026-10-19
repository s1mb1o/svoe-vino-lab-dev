import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'

assert(process.env.PLAYWRIGHT_MODULE, 'Set PLAYWRIGHT_MODULE to a local playwright/index.mjs.')
const { chromium, webkit } = await import(process.env.PLAYWRIGHT_MODULE)
const origin = process.env.PORTAL_ORIGIN || 'http://127.0.0.1:8153'
const output = process.env.GAME_LANDING_REPORT_DIR || 'reports/game-landing'
await mkdir(output, { recursive: true })
const results = []

for (const [engine, browserType] of [['chromium', chromium], ['webkit', webkit]]) {
  const browser = await browserType.launch({ headless: true })
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, serviceWorkers: 'block', colorScheme: 'light' })
    // Keep analytics out of local browser tests.
    await context.route(/https:\/\/mc\.yandex\.(ru|com)\//, route => route.fulfill({ status: 200, body: '' }))
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    page.on('console', message => { if (/hydration/i.test(message.text())) errors.push(message.text()) })

    await page.goto(`${origin}/game`, { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: 'Да, мне есть 18 лет', exact: true }).waitFor()
    assert(await page.locator('.site-shell').evaluate(node => node.inert), 'Keep the existing portal age gate')
    // This is a synthetic local test visitor, not an assertion about a real visitor.
    await page.getByRole('button', { name: 'Да, мне есть 18 лет', exact: true }).click()
    await page.getByRole('dialog').waitFor({ state: 'detached' })
    await page.evaluate(() => document.fonts.ready)
    assert.equal(await page.locator('h1').count(), 1)
    assert.equal(await page.locator('link[rel="canonical"]').count(), 1)
    assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'), 'https://chtozavino.ru/game')
    assert.match(await page.title(), /Wine&Dine Merge/)
    assert.match(await page.locator('.header-section').innerText(), /Wine&Dine/)
    assert.equal(await page.getByTestId('game-play').getAttribute('href'), 'https://game.chtozavino.ru/')
    assert.equal(await page.getByTestId('game-play-final').getAttribute('href'), 'https://game.chtozavino.ru/')
    assert.equal(await page.getByTestId('game-pour').getAttribute('href'), 'https://game.chtozavino.ru/?mode=pour')
    assert.equal(await page.evaluate(() => localStorage.getItem('wine-dine-save-v1')), null, 'The landing must not create a campaign save')

    for (const name of ['Краснодарский край', 'Дагестан', 'Ростовская область']) {
      await page.getByRole('tab', { name, exact: true }).click()
      assert.equal(await page.getByRole('tab', { name, exact: true }).getAttribute('aria-selected'), 'true')
      assert.match(await page.getByRole('tabpanel').innerText(), new RegExp(name))
      await page.getByRole('tabpanel').locator('img').evaluate(image => image.decode())
      assert(await page.getByRole('tabpanel').locator('img').evaluate(image => image.complete && image.naturalWidth > 0))
    }
    await page.getByRole('tab', { name: 'Ростовская область', exact: true }).press('ArrowLeft')
    assert.equal(await page.getByRole('tab', { name: 'Дагестан', exact: true }).getAttribute('aria-selected'), 'true')
    assert.equal(await page.evaluate(() => document.activeElement.id), 'region-tab-dagestan')
    await page.getByRole('tab', { name: 'Дагестан', exact: true }).press('Home')
    assert.equal(await page.evaluate(() => document.activeElement.id), 'region-tab-rostov')
    await page.getByText('Это курс сомелье?', { exact: true }).click()
    assert(await page.getByText(/пока не прошли экспертную проверку/).isVisible())
    await page.getByText('Это курс сомелье?', { exact: true }).press('Enter')
    assert.equal(await page.locator('details[open]').count(), 0)

    for (const theme of ['light', 'dark']) {
      await page.emulateMedia({ colorScheme: theme, reducedMotion: 'reduce' })
      await page.reload({ waitUntil: 'networkidle' })
      await page.evaluate(() => document.fonts.ready)
      assert.equal(await page.locator('html').getAttribute('data-theme'), theme, 'Follow the system theme')
      for (const width of [1440, 768, 390, 320]) {
        await page.setViewportSize({ width, height: width < 768 ? 844 : 1050 })
        await page.locator('.game-finale').scrollIntoViewIfNeeded()
        await page.locator('#game-title').scrollIntoViewIfNeeded()
        await page.evaluate(() => window.scrollTo(0, 0))
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), `${engine} ${theme} ${width}px overflow`)
        assert(await page.locator('.game-page img').evaluateAll(images => images.every(image => image.complete && image.naturalWidth > 0)), 'All local illustrations load')
        assert(await page.getByTestId('game-play').evaluate(node => node.getBoundingClientRect().height >= 44), 'Play target stays large enough')
        if (width === 1440 || width === 390) await page.screenshot({ path: `${output}/${engine}-${theme}-${width}.png`, fullPage: width === 390 })
        results.push({ engine, theme, width, passed: true })
      }
    }

    await page.setViewportSize({ width: 1440, height: 1050 })
    await page.goto(`${origin}/hackaton`, { waitUntil: 'networkidle' })
    await page.getByRole('link', { name: 'Идеи за пределами распознавания', exact: true }).first().click()
    await page.waitForURL(`${origin}/ideas`)
    await page.getByTestId('ideas-game-link').waitFor()
    assert.equal(await page.getByTestId('ideas-game-link').getAttribute('href'), '/game')
    await page.getByTestId('ideas-game-link').click()
    await page.waitForURL(`${origin}/game`)
    await page.getByRole('heading', { name: 'Хороший вкус начинается с игры.', exact: true }).waitFor()
    assert.match(await page.locator('.header-section').innerText(), /Wine&Dine/)
    await page.getByRole('link', { name: 'Все идеи', exact: true }).click()
    await page.waitForURL(`${origin}/ideas`)
    await page.setViewportSize({ width: 320, height: 740 })
    await page.getByTestId('ideas-game-link').scrollIntoViewIfNeeded()
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), 'Ideas invitation fits narrow phones')
    assert.deepEqual(errors, [], `${engine} browser errors or hydration warnings`)
    await context.close()
  } finally {
    await browser.close()
  }
}
await writeFile(`${output}/results.json`, `${JSON.stringify({ passed: true, layouts: results, checks: ['portal age gate', 'campaign and pouring links', 'region selection and keyboard focus', 'FAQ disclosure', 'system themes', 'local illustrations', 'metadata', 'hackaton → ideas → game navigation'] }, null, 2)}\n`)
console.log(`Passed ${results.length} responsive layouts in Chromium and WebKit, navigation, interactions, and metadata.`)
