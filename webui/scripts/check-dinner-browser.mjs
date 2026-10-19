import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

assert(process.env.PLAYWRIGHT_MODULE, 'Set PLAYWRIGHT_MODULE to an installed Playwright index.mjs.')
const { chromium, webkit } = await import(process.env.PLAYWRIGHT_MODULE)
const origin = process.env.PORTAL_ORIGIN || 'http://127.0.0.1:18573'
const output = process.env.BROWSER_ARTIFACT_DIR || '/tmp/dinner-lens-ui-check'
await mkdir(output, { recursive: true })
const wine = n => ({ wine_slug: `dinner-fixture-${n}`, name: `Fixture wine ${n}`, producer: `Fixture producer ${n}`,
  source_url: `https://vino-svoe.ru/wines/dinner-fixture-${n}`, selection_source: n <= 3 ? 'curated' : 'embedding',
  reason: 'A deterministic browser test fixture.', facts: { color: 'red', sweetness: 'dry', wine_kind: 'still', alcohol_percent: 13, reported_grapes: ['Cabernet Sauvignon'] } })
const pageValue = (more = false) => ({ status: 'ok', resolved_node_id: 'ribeye_grilled', results: (more ? [4, 5, 6] : [1, 2, 3]).map(wine),
  next_cursor: more ? null : 'fixture-cursor', shown_count: more ? 6 : 3, total_eligible: 6, needs_clarification: false, clarification_question: null })
const receipts = []

async function contextFor(browser, options = {}) {
  const httpCredentials = process.env.PORTAL_BASIC_USER && process.env.PORTAL_BASIC_PASSWORD
    ? { username: process.env.PORTAL_BASIC_USER, password: process.env.PORTAL_BASIC_PASSWORD } : undefined
  const context = await browser.newContext({ colorScheme: 'dark', httpCredentials, ...options })
  await context.addInitScript(() => localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes'))
  await context.route('https://mc.yandex.ru/**', route => route.abort())
  return context
}
async function modeLayout(page, width) {
  await page.evaluate(() => document.fonts.ready)
  const buttons = page.locator('.scan-mode-switch a')
  assert.equal(await buttons.count(), 3)
  assert.deepEqual(await buttons.allTextContents(), ['Одна бутылка', 'Вся полка', 'Вино к блюду'])
  for (const button of await buttons.all()) {
    const box = await button.boundingBox()
    assert(box && box.x >= 0 && box.x + box.width <= width + 1 && box.height >= 44, 'Every mode must fit and remain touch-accessible')
  }
  assert.equal(await page.locator('.scan-mode-switch [aria-current="page"]').count(), 1)
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'The page must not scroll horizontally')
  const contrasts = await page.locator('.upload-actions>.button:not(:disabled)').evaluateAll(buttons => {
    const light = color => {
      const channels = color.match(/[\d.]+/g).slice(0, 3).map(Number).map(n => n / 255).map(n => n <= 0.04045 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4)
      return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722
    }
    return buttons.map(button => { const style = getComputedStyle(button); const a = light(style.color); const b = light(style.backgroundColor); return (Math.max(a, b) + .05) / (Math.min(a, b) + .05) })
  })
  assert(contrasts.every(ratio => ratio >= 4.5), 'Upload actions must keep readable text in the current theme')
}

for (const [name, engine, viewport, mobile, colorScheme] of [
  ['desktop-chromium', chromium, { width: 1440, height: 1000 }, false, 'dark'],
  ['mobile-chromium-320', chromium, { width: 320, height: 740 }, true, 'dark'],
  ['mobile-webkit-390', webkit, { width: 390, height: 844 }, true, 'dark'],
  ['desktop-chromium-light', chromium, { width: 1440, height: 1000 }, false, 'light'],
  ['mobile-webkit-390-light', webkit, { width: 390, height: 844 }, true, 'light'],
]) {
  const browser = await engine.launch({ headless: true })
  const context = await contextFor(browser, { viewport, isMobile: mobile, hasTouch: mobile, colorScheme })
  const page = await context.newPage(); const errors = []; const calls = []
  page.on('pageerror', error => errors.push(error.message))
  await context.route('**/api/config', route => route.fulfill({ json: { predictionMode: 'mock', apiAvailable: true, shelfAvailable: false, dinnerAvailable: true } }))
  await context.route('**/api/dinner/**', route => {
    const action = new URL(route.request().url()).pathname.split('/').at(-1)
    const body = route.request().postDataJSON(); calls.push({ action, body })
    return route.fulfill({ json: pageValue(action === 'more') })
  })
  try {
    await page.goto(origin + '/', { waitUntil: 'networkidle' }); await modeLayout(page, viewport.width)
    await page.screenshot({ path: resolve(output, name + '-home.png'), fullPage: true })
    await page.getByRole('link', { name: 'Вино к блюду', exact: true }).click()
    await page.locator('#dinner-dish').waitFor(); await modeLayout(page, viewport.width)
    assert.equal(await page.locator('input[capture="environment"]').count(), 1)
    await page.locator('#dinner-dish').fill('Стейк рибай на гриле')
    await page.getByRole('button', { name: 'Подобрать вино', exact: true }).click()
    await page.locator('.dinner-wine').first().waitFor()
    assert.equal(await page.locator('.dinner-wine').count(), 3)
    await page.getByRole('button', { name: 'Показать ещё', exact: true }).click()
    await page.waitForFunction(() => document.querySelectorAll('.dinner-wine').length === 6)
    assert.deepEqual(calls.at(-1), { action: 'more', body: { cursor: 'fixture-cursor' } })
    assert.equal(await page.getByRole('button', { name: 'Показать ещё', exact: true }).count(), 0)
    await page.locator('.dinner-options summary').click()
    await page.getByLabel('Сливочный соус', { exact: true }).selectOption('yes')
    assert.equal(await page.locator('.dinner-wine').count(), 0, 'Changed sauce must discard the previous context')
    await page.getByRole('button', { name: 'Подобрать вино', exact: true }).click()
    await page.locator('.dinner-wine').first().waitFor()
    assert.equal(calls.at(-1).body.confirmed_attributes.fatty_cream_sauce, true)
    await modeLayout(page, viewport.width)
    await page.screenshot({ path: resolve(output, name + '-dish.png'), fullPage: true })
    await page.getByRole('link', { name: 'Одна бутылка', exact: true }).click()
    await page.getByRole('link', { name: 'Вино к блюду', exact: true }).click()
    await page.locator('#dinner-dish').waitFor()
    assert.equal(await page.locator('#dinner-dish').inputValue(), '')
    assert.equal(await page.locator('.dinner-wine').count(), 0)
    await context.route('**/api/dinner/recommendations', route => route.fulfill({ json: {
      status: 'needs_category', resolved_node_id: null, results: [], next_cursor: null,
      shown_count: 0, total_eligible: 0, needs_clarification: true,
      clarification_question: 'Выберите общую категорию блюда.',
    } }))
    await page.locator('#dinner-dish').fill('Неизвестное блюдо')
    await page.getByRole('button', { name: 'Подобрать вино', exact: true }).click()
    await page.getByRole('status').filter({ hasText: 'Выберите общую категорию блюда.' }).waitFor()
    assert.equal(await page.locator('.dinner-wine').count(), 0)
    await context.route('**/api/dinner/recommendations', route => route.fulfill({ status: 503, json: { message: 'Service unavailable' } }))
    await page.locator('#dinner-dish').fill('Стейк рибай на гриле')
    await page.getByRole('button', { name: 'Подобрать вино', exact: true }).click()
    await page.getByRole('alert').waitFor(); assert.equal(await page.locator('.dinner-wine').count(), 0)
    assert.deepEqual(errors, [])
    receipts.push({ browser: name, viewport, colorScheme, passed: true, checks: ['three touch-accessible modes', 'route reset', 'sauce context invalidation', 'full continuation', 'unknown dish clarification', 'upstream failure', 'readable upload actions', 'no horizontal overflow', 'no browser errors'] })
  } finally { await context.close(); await browser.close() }
}

if (process.env.DINNER_LIVE_CHECK === '1') {
  const browser = await chromium.launch({ headless: true }); const context = await contextFor(browser, { viewport: { width: 1280, height: 1000 } }); const page = await context.newPage()
  const pages = []; let photoRequests = 0
  page.on('request', request => { if (request.url().endsWith('/api/dinner/recognize')) photoRequests++ })
  try {
    await page.goto(origin + '/dish', { waitUntil: 'networkidle' })
    for (const dish of ['Стейк рибай на гриле', 'Оливье с докторской колбасой', 'Камчатский краб на пару с топлёным маслом']) {
      await page.locator('#dinner-dish').fill(dish)
      const response = page.waitForResponse(response => response.url().endsWith('/api/dinner/recommendations'))
      await page.getByRole('button', { name: 'Подобрать вино', exact: true }).click()
      const first = await (await response).json(); assert.equal(first.status, 'ok')
      await page.waitForFunction(count => document.querySelectorAll('.dinner-wine').length === count, first.results.length)
      const slugs = first.results.map(w => w.wine_slug); const sources = first.results.map(w => w.selection_source); let cursor = first.next_cursor; let count = 1
      while (cursor) {
        assert(count < 100)
        const next = page.waitForResponse(response => response.url().endsWith('/api/dinner/more'))
        await page.getByRole('button', { name: 'Показать ещё', exact: true }).click()
        const value = await (await next).json(); assert.equal(value.resolved_node_id, first.resolved_node_id)
        slugs.push(...value.results.map(w => w.wine_slug)); sources.push(...value.results.map(w => w.selection_source)); cursor = value.next_cursor; count++
        await page.waitForFunction(total => document.querySelectorAll('.dinner-wine').length === total, slugs.length)
      }
      assert.equal(slugs.length, first.total_eligible); assert.equal(new Set(slugs).size, slugs.length)
      assert(sources.includes('embedding'), 'A live case must exercise discovery beyond curation')
      pages.push({ dish, node: first.resolved_node_id, pages: count, slugs, sources })
    }
    if (process.env.DINNER_TEST_IMAGE) {
      const response = page.waitForResponse(response => response.url().endsWith('/api/dinner/recognize'), { timeout: 200_000 })
      await page.locator('input[aria-label="Фото блюда"]').setInputFiles(process.env.DINNER_TEST_IMAGE)
      const imageResponse = await response; assert.equal(imageResponse.status(), 200)
      await page.waitForFunction(() => !document.querySelector('.dinner-progress'))
      assert.equal(await page.locator('.dinner-wine').count(), 0, 'Photo wines must await explicit confirmation')
      await page.locator('#dinner-dish').fill('Камчатский краб на пару с топлёным маслом')
      await page.getByRole('button', { name: 'Подтвердить и подобрать вино', exact: true }).click()
      await page.locator('.dinner-wine').first().waitFor(); assert.equal(photoRequests, 1)
    }
    await page.screenshot({ path: resolve(output, 'live-dinner-confirmed.png'), fullPage: true })
    receipts.push({ mode: 'real gx10 Dinner Lens through the Nuxt proxy', passed: true, cases: pages, photoRequests })
  } finally { await context.close(); await browser.close() }
}
await writeFile(resolve(output, 'results.json'), JSON.stringify({ origin, receipts }, null, 2) + '\n')
console.log(JSON.stringify({ passed: true, origin, output, suites: receipts.length }))
