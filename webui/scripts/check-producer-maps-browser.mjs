import assert from 'node:assert/strict'
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises'

assert(process.env.PLAYWRIGHT_MODULE, 'Set PLAYWRIGHT_MODULE to a local playwright/index.mjs.')
const { chromium, webkit } = await import(process.env.PLAYWRIGHT_MODULE)
const browserName = process.env.PLAYWRIGHT_BROWSER || 'chromium'
const browser = await ({ chromium, webkit })[browserName].launch({ headless: true })
const origin = process.env.PORTAL_ORIGIN || 'http://127.0.0.1:18553'
const directory = 'shared/data/product-line-maps'
const maps = await Promise.all((await readdir(directory)).filter(name => name.endsWith('.json')).map(async name => JSON.parse(await readFile(`${directory}/${name}`, 'utf8'))))
const report = `reports/producer-maps/${browserName}`
await mkdir(report, { recursive: true })
const errors = []
const checks = []

async function viewportState(page) {
  return page.locator('[data-map-viewport]').evaluate(element => ({ left: element.scrollLeft, top: element.scrollTop }))
}
async function assertSelected(page, id) {
  await page.waitForFunction(id => document.querySelector('[data-product-detail]')?.getAttribute('data-selected-product') === id, id)
  assert.equal(await page.locator(`[data-product-id="${id}"]`).getAttribute('data-selected'), 'true')
}
async function openProduct(page, product) {
  const group = page.locator(`[data-group-id="${product.group_id}"]`)
  if (await group.getAttribute('aria-expanded') !== 'true') await group.click()
  await page.locator(`[data-product-id="${product.id}"]`).click()
  await assertSelected(page, product.id)
}
async function assertLayout(page, label) {
  // Lazy images must finish before a visual assertion. Ignore images outside clipped regions.
  await page.waitForFunction(() => [...document.images].every(image => {
    const bounds = image.getBoundingClientRect()
    const style = getComputedStyle(image)
    if (!bounds.width || !bounds.height || style.visibility === 'hidden') return true
    let left = Math.max(0, bounds.left)
    let top = Math.max(0, bounds.top)
    let right = Math.min(innerWidth, bounds.right)
    let bottom = Math.min(innerHeight, bounds.bottom)
    for (let parent = image.parentElement; parent; parent = parent.parentElement) {
      const parentStyle = getComputedStyle(parent)
      const clip = parent.getBoundingClientRect()
      if (/(hidden|auto|scroll|clip)/.test(parentStyle.overflowX)) {
        left = Math.max(left, clip.left)
        right = Math.min(right, clip.right)
      }
      if (/(hidden|auto|scroll|clip)/.test(parentStyle.overflowY)) {
        top = Math.max(top, clip.top)
        bottom = Math.min(bottom, clip.bottom)
      }
    }
    return right <= left || bottom <= top || (image.complete && image.naturalWidth > 0)
  }))
  await page.evaluate(async () => {
    await Promise.all([...document.images].filter(image => image.complete && image.naturalWidth).map(image => image.decode()))
    await document.fonts.ready
  })
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${label}: horizontal page overflow`)
  const broken = await page.locator('img').evaluateAll(images => images.filter(image => image.complete && !image.naturalWidth).map(image => image.src))
  assert.deepEqual(broken, [], `${label}: broken images`)
}

try {
  for (const line of maps.filter(line => line.producer.id !== 'abrau-durso')) {
    const initial = line.products.find(product => product.wine_slug)
    const gray = line.products.find(product => product.wine_slug === null)
    assert(initial && gray, `${line.producer.id}: linked and unlinked evidence required`)
    for (const [width, theme] of [[1440, 'light'], [1440, 'dark'], [390, 'light'], [320, 'dark']]) {
      const mobile = width < 768
      const label = `${line.producer.id}-${width}-${theme}`
      const context = await browser.newContext({ viewport: { width, height: mobile ? 844 : 1000 }, colorScheme: theme, isMobile: mobile, hasTouch: mobile, reducedMotion: 'reduce', serviceWorkers: 'block' })
      await context.addInitScript(() => {
        localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes')
        localStorage.removeItem('svoe-vino.theme.v1')
      })
      const page = await context.newPage()
      page.on('pageerror', error => errors.push(`${label}: ${error.message}`))
      page.on('console', message => { if (message.type() === 'error' || /hydration/i.test(message.text())) errors.push(`${label}: ${message.text()}`) })
      await page.goto(`${origin}/lineup/${line.producer.id}?wine=${encodeURIComponent(initial.wine_slug)}`, { waitUntil: 'networkidle' })
      await assertSelected(page, initial.id)
      assert.equal(await page.locator(`[data-group-id="${initial.group_id}"]`).getAttribute('aria-expanded'), 'true')
      const details = page.locator('[data-product-detail]')
      if (mobile) {
        assert.equal(await details.getAttribute('open'), null, `${label}: popup must stay closed on entry`)
        const before = await viewportState(page)
        await page.getByRole('button', { name: 'О выбранном вине', exact: true }).click()
        assert.equal(await details.getAttribute('open'), '')
        assert.equal(await details.locator('.plm-portal-link').getAttribute('href'), `https://vino-svoe.ru/wines/${initial.wine_slug}`)
        await details.getByRole('button', { name: 'Вернуться к карте', exact: true }).click()
        assert.equal(await details.getAttribute('open'), null)
        assert.deepEqual(await viewportState(page), before, `${label}: return changed map position`)
      } else {
        assert.equal(await details.evaluate(element => element.tagName), 'ASIDE')
        assert.equal(await details.locator('.plm-portal-link').getAttribute('href'), `https://vino-svoe.ru/wines/${initial.wine_slug}`)
      }
      await openProduct(page, gray)
      assert(await page.locator(`[data-product-id="${gray.id}"]`).evaluate(element => element.classList.contains('is-unavailable')))
      assert.equal(await details.locator('.plm-portal-link').count(), 0)
      assert(await details.locator('.plm-detail-description').innerText())
      if (!gray.image) assert.equal(await details.locator('.plm-image-placeholder').innerText(), 'Нет изображения')
      if (mobile) assert.equal(await details.getAttribute('open'), '')
      await assertLayout(page, label)
      if (['derbent-vino', 'fanagoria', 'massandra'].includes(line.producer.id)) await page.screenshot({ path: `${report}/${label}.png`, fullPage: !mobile })
      if (mobile) await details.getByRole('button', { name: 'Закрыть информацию о вине', exact: true }).click()
      const missingImage = line.products.find(product => !product.image && product.wine_slug)
      if (missingImage) {
        await openProduct(page, missingImage)
        assert.equal(await details.locator('.plm-image-placeholder').innerText(), 'Нет изображения')
        assert.equal(await details.locator('.plm-portal-link').getAttribute('href'), `https://vino-svoe.ru/wines/${missingImage.wine_slug}`)
        if (mobile) await page.keyboard.press('Escape')
      }
      const next = maps.find(other => other.producer.id !== line.producer.id)
      await page.getByRole('combobox', { name: 'Выбрать производителя', exact: true }).selectOption(next.producer.id)
      await page.waitForURL(`**/lineup/${next.producer.id}`)
      assert.equal(await page.locator('[data-product-detail]').getAttribute('data-selected-product'), '')
      assert.equal(await page.locator('[data-product-dialog][open]').count(), 0)
      await assertLayout(page, `${label}-navigation`)
      checks.push(label)
      await context.close()
    }
  }
  assert.deepEqual(errors, [])
  await writeFile(`${report}/results.json`, JSON.stringify({ browser: browserName, checks, errors }, null, 2) + '\n')
  console.log(JSON.stringify({ browser: browserName, checks: checks.length, errors }, null, 2))
} finally {
  await browser.close()
}
