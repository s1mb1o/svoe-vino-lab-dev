import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'

const { chromium, webkit } = await import(process.env.PLAYWRIGHT_MODULE)
const origin = process.env.PORTAL_ORIGIN || 'http://127.0.0.1:18573'
const output = process.env.BROWSER_ARTIFACT_DIR || '/tmp/dinner-picker-check'
const fixtureRun = process.env.DINNER_MOCK === '1'
await mkdir(output, { recursive: true })
const receipts = []
const cases = origin.startsWith('https:') ? [['desktop', 1440, chromium, 'dark'], ['mobile', 390, webkit, 'light']] : [
  ['desktop', 1440, chromium, 'dark'], ['desktop-1024', 1024, chromium, 'light'], ['tablet', 820, chromium, 'light'],
  ['above-breakpoint', 601, chromium, 'dark'], ['at-breakpoint', 600, chromium, 'dark'],
  ['mobile', 390, webkit, 'light'], ['small-mobile', 320, chromium, 'dark'],
]
for (const [name, width, engine, colorScheme] of cases) {
  const browser = await engine.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width, height: 1100 }, isMobile: width <= 600, hasTouch: width <= 600, colorScheme,
    httpCredentials: process.env.PORTAL_BASIC_PASSWORD ? { username: 'chtozavino', password: process.env.PORTAL_BASIC_PASSWORD } : undefined })
  try {
    await context.addInitScript(() => localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes'))
    await context.route('https://mc.yandex.ru/**', route => route.abort())
    if (fixtureRun) {
      await context.route('**/api/config', route => route.fulfill({ json: { predictionMode: 'mock', apiAvailable: true, dinnerAvailable: true, shelfAvailable: false } }))
      await context.route('**/api/dinner/recommendations', route => {
        const body = route.request().postDataJSON()
        const unknown = !!body.confirmed_dish
        return route.fulfill({ json: { status: unknown ? 'needs_category' : 'ok', resolved_node_id: body.node_id || null,
          results: unknown ? [] : [{ wine_slug: 'picker-fixture', name: 'Picker fixture', producer: 'Fixture', source_url: 'https://vino-svoe.ru/wines/picker-fixture',
            selection_source: 'curated', reason: 'A deterministic browser fixture.', facts: { color: 'red', sweetness: 'dry', wine_kind: 'still', alcohol_percent: 12, reported_grapes: [] } }],
          next_cursor: null, shown_count: unknown ? 0 : 1, total_eligible: unknown ? 0 : 1, needs_clarification: unknown,
          clarification_question: unknown ? 'Выберите общую категорию блюда.' : null } })
      })
    }
    const page = await context.newPage()
    const errors = []; const responses = []; let consumed = 0
    page.on('response', response => { if (response.url().endsWith('/api/dinner/recommendations')) responses.push(response) })
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(origin + '/dish', { waitUntil: 'networkidle' })
    const input = page.getByRole('combobox', { name: 'Название блюда', exact: true })
    assert.equal(await page.locator('.dinner-form input:not([type=file])').count(), 1)
    assert.equal(await page.locator('.dinner-form select, .dinner-form datalist, .dinner-form button[type=submit]').count(), 0)
    const categories = page.getByRole('button', { name: 'Показать категории блюд', exact: true })
    const option = id => page.locator('#dinner-option-' + id)
    const expand = id => option(id).locator('.dish-picker-expand').click()
    const choose = id => option(id).locator('.dish-picker-copy').click()
    async function awaitAutoResult(expected) {
      let response
      for (let attempt = 0; attempt < 1000; attempt++) {
        response = responses.slice(consumed).find(value => {
          const body = value.request().postDataJSON()
          return body.node_id === expected.node_id && body.confirmed_dish === expected.confirmed_dish
        })
        if (response) break
        await new Promise(resolve => setTimeout(resolve, 30))
      }
      assert(response, 'An edit must automatically request the latest selection')
      consumed = responses.length
      assert.equal(response.status(), 200)
      const body = response.request().postDataJSON()
      assert.equal(body.node_id, expected.node_id)
      assert.equal(body.confirmed_dish, expected.confirmed_dish)
      return response.json()
    }
    await categories.click()
    assert.equal(await page.getByRole('treeitem').count(), 16)
    await expand('meat')
    assert.equal(await option('meat_steak').getAttribute('aria-level'), '2')
    await expand('meat_steak')
    assert.equal(await option('ribeye_grilled').getAttribute('aria-level'), '3')
    await page.locator('.dinner-form').screenshot({ path: output + '/' + name + '-hierarchy.png' })
    await choose('ribeye_grilled')
    assert.equal(await input.inputValue(), 'Стейк рибай на гриле')
    assert.equal(await input.getAttribute('aria-expanded'), 'false')
    const liveRequests = ['desktop', 'mobile'].includes(name)
    if (liveRequests) {
      assert.equal((await awaitAutoResult({ node_id: 'ribeye_grilled' })).status, 'ok')
      await page.locator('.dinner-wine').first().waitFor()
      await input.fill('Стейк из мяса')
      await choose('meat_steak')
      assert.equal((await awaitAutoResult({ node_id: 'meat_steak' })).resolved_node_id, 'meat_steak')
      await page.locator('.dinner-wine').first().waitFor()
    }
    await categories.click()
    await input.press('ArrowDown')
    const firstId = (await input.getAttribute('aria-activedescendant')).replace('dinner-option-', '')
    await input.press('ArrowRight')
    assert.equal(await option(firstId).getAttribute('aria-expanded'), 'true')
    await input.press('ArrowDown')
    assert.notEqual(await input.getAttribute('aria-activedescendant'), 'dinner-option-' + firstId)
    await input.press('ArrowLeft')
    assert.equal(await input.getAttribute('aria-activedescendant'), 'dinner-option-' + firstId)
    await input.press('ArrowLeft')
    assert.equal(await option(firstId).getAttribute('aria-expanded'), 'false')
    await input.press('Enter')
    assert.equal(await input.getAttribute('aria-expanded'), 'false')
    assert(await input.inputValue())
    if (liveRequests) {
      const result = await awaitAutoResult({ node_id: firstId })
      assert.equal(result.resolved_node_id, firstId)
      await page.locator('.dinner-wine').first().waitFor()
    }
    await input.fill('мясо рибай')
    assert.equal(await page.getByRole('treeitem').count(), 1)
    assert.equal(await input.getAttribute('aria-activedescendant'), null, 'Typing must not preselect a suggestion')
    await input.press('ArrowDown'); await input.press('Enter')
    assert.equal(await input.inputValue(), 'Стейк рибай на гриле')
    await input.fill('краб')
    assert((await page.getByRole('treeitem').count()) >= 2)
    await page.locator('.dinner-form').screenshot({ path: output + '/' + name + '-search.png' })
    await input.press('Escape')
    assert.equal(await input.getAttribute('aria-expanded'), 'false')
    await input.focus()
    await categories.click()
    await page.locator('.dinner-form h2').click()
    assert.equal(await input.getAttribute('aria-expanded'), 'false', 'An outside click closes the popup')
    if (liveRequests) {
      await input.fill('Неизвестное блюдо xyz')
      const result = await awaitAutoResult({ confirmed_dish: 'Неизвестное блюдо xyz' })
      assert.equal(result.status, 'needs_category')
      await page.waitForFunction(() => document.activeElement?.id === 'dinner-dish' && document.querySelector('.dinner-question'))
      assert.equal(await input.inputValue(), 'Неизвестное блюдо xyz')
      await categories.click()
      await choose('meat')
      assert.equal(await input.inputValue(), 'Мясо')
      await input.fill('Своё блюдо xyz')
      assert.equal((await awaitAutoResult({ confirmed_dish: 'Своё блюдо xyz' })).status, 'needs_category')
    }
    for (const row of await page.getByRole('treeitem').all()) {
      assert(Number(await row.getAttribute('aria-level')) <= 3)
      const box = await row.boundingBox()
      assert(box.width >= 44 && box.height >= 44)
    }
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false)
    assert.deepEqual(errors, [])
    receipts.push({ name, width, colorScheme, passed: true, liveRequests,
      checks: ['single editable field', 'three-level browsing', 'broad category selection', 'keyboard navigation', 'cross-category search', 'custom text', '44px rows', 'no overflow', ...(liveRequests ? ['dish/category request IDs', 'unknown dish clarification', 'stale selection cleared'] : [])] })
  } finally { await context.close(); await browser.close() }
}
await writeFile(output + '/results.json', JSON.stringify({ origin, receipts, passed: true }, null, 2) + '\n')
console.log(JSON.stringify({ passed: true, origin, configurations: receipts.length }))
