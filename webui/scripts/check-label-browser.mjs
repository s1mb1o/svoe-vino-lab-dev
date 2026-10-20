import assert from 'node:assert/strict'
import { mkdir, readFile } from 'node:fs/promises'

assert(process.env.PLAYWRIGHT_MODULE, 'Set PLAYWRIGHT_MODULE to the installed playwright/index.mjs.')
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE)
const origin = process.env.PORTAL_ORIGIN || 'http://127.0.0.1:8153'
const wines = JSON.parse(await readFile(new URL('../server/data/wines.json', import.meta.url), 'utf8'))
const publishers = new Set(['rskrf.ru', 'rvwa.ru', 'vino.ru', 'swn.ru', 'magarach-institut.ru', 'magarach-journal.ru', 'journalkubansad.ru'])
const browser = await chromium.launch({ headless: true })
const errors = []
await mkdir('reports/label', { recursive: true })

async function preview(override) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, serviceWorkers: 'block' })
  await context.addInitScript(() => localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes'))
  if (override) await context.route('**/api/wines', route => route.fulfill({ json: wines.map(wine => wine.slug === wines[0].slug ? { ...wine, ...override } : wine) }))
  const page = await context.newPage()
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => { if (/hydration/i.test(message.text())) errors.push(message.text()) })
  // SPA navigation makes the preview metadata request observable to route interception.
  await page.goto(origin, { waitUntil: 'domcontentloaded' })
  await page.locator('.site-shell:not([inert])').waitFor()
  await page.locator('.site-footer a[href="/ideas"]').click()
  await page.waitForURL(`${origin}/ideas`)
  await page.locator('#idea-wine').waitFor()
  return { context, page }
}

async function openGuide(page) {
  await page.getByRole('button', { name: /Рассказать об этикетке/ }).click()
  const dialog = page.locator('.experience-dialog[open]')
  await dialog.locator('.label-guide').waitFor()
  return dialog
}

try {
  const { context, page } = await preview()
  await page.selectOption('#idea-wine', 'priboj-marchenko-rozovoe-polusuhoe')
  const dialog = await openGuide(page)
  assert.equal(await dialog.locator('.label-guide-note').count(), 2)
  assert.deepEqual(await dialog.locator('.label-guide-note h4').allTextContents(), ['Антей магарачский', 'Мерло'])
  assert((await dialog.textContent()).includes('один купаж'))
  assert(!(await dialog.textContent()).includes('фиксированный пример'))
  for (const section of ['grapes', 'sweetness', 'region', 'alcohol']) {
    await dialog.locator(`[data-label-section="${section}"]`).click()
    assert.equal(await dialog.locator(`[data-label-section="${section}"]`).getAttribute('aria-pressed'), 'true')
    for (const href of await dialog.locator('.label-guide-sources a').evaluateAll(elements => elements.map(element => element.href))) {
      const url = new URL(href)
      assert.equal(url.protocol, 'https:')
      assert(publishers.has(url.hostname.replace(/^www\./, '')), href)
    }
    assert(!/Нет данных|не приведены|не найдены|не указаны/.test(await dialog.textContent()))
  }
  await dialog.locator('[data-label-section="sweetness"]').click()
  assert((await dialog.textContent()).includes('лёгкой сладостью'))
  await dialog.locator('[data-label-section="region"]').click()
  assert((await dialog.textContent()).includes('Чёрным и Азовским'))
  await dialog.locator('[data-label-section="grapes"]').click()
  for (const theme of ['light', 'dark']) {
    await page.evaluate(value => document.documentElement.dataset.theme = value, theme)
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 })
      assert(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth + 1), `Dialog overflow at ${width}px in ${theme}`)
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `Page overflow at ${width}px`)
      await dialog.screenshot({ path: `reports/label/${theme}-${width}.png` })
    }
  }
  await page.keyboard.press('Escape')
  await dialog.waitFor({ state: 'hidden' })
  assert(await page.getByRole('button', { name: /Рассказать об этикетке/ }).evaluate(element => element === document.activeElement))
  await page.selectOption('#idea-wine', wines[0].slug)
  await openGuide(page)
  assert.equal(await page.locator('.label-guide-note').count(), 1)
  assert((await page.locator('.label-guide-note').textContent()).includes('Первенец Магарача'))
  await context.close()

  const sparse = await preview({ grapes: [], region: '', category: 'Полусухое', alcohol: null })
  const sparseDialog = await openGuide(sparse.page)
  assert.deepEqual(await sparseDialog.locator('[data-label-section]').evaluateAll(elements => elements.map(element => element.dataset.labelSection)), ['sweetness'])
  assert((await sparseDialog.textContent()).includes('лёгкой сладостью'))
  await sparse.context.close()

  const empty = await preview({ grapes: [], region: '', category: '', alcohol: null })
  assert.equal(await empty.page.getByRole('button', { name: /Рассказать об этикетке/ }).count(), 0)
  assert.equal(await empty.page.locator('.label-guide').count(), 0)
  assert.equal(await empty.page.locator('.experience-grid .experience-action').count(), 3)
  for (const width of [1440, 320]) {
    await empty.page.setViewportSize({ width, height: 1000 })
    assert(await empty.page.locator('.experience-grid').evaluate(element => element.scrollWidth <= element.clientWidth + 1), `Three-action layout overflows at ${width}px`)
  }
  await empty.context.close()

  assert.deepEqual(errors, [], 'Runtime errors or hydration warnings')
  console.log('Label guide passed: blend and single grape, Russian sources, sweetness and region copy, sparse/empty metadata, six viewport/theme combinations, Escape and focus recovery.')
} finally { await browser.close() }
