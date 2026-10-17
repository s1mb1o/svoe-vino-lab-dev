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
const producerMaps = maps.filter(line => line.producer.id !== 'abrau-durso')
let status = 'failed'
let failure
let activeCase

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

async function imageFailureBeforeHydration() {
  activeCase = 'image-failure-before-hydration'
  const line = producerMaps.find(line => line.products.some(product => product.wine_slug && product.image))
  const product = line.products.find(product => product.wine_slug && product.image)
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, serviceWorkers: 'block' })
  let releaseScripts
  const scriptsReady = new Promise(resolve => { releaseScripts = resolve })
  try {
    await context.addInitScript(() => localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes'))
    const page = await context.newPage()
    const pageErrors = []
    page.on('pageerror', error => pageErrors.push(error.message))
    await page.route('**/_nuxt/*.js', async route => { await scriptsReady; await route.continue() })
    await page.route(`**${product.image.src}`, route => route.fulfill({ status: 404, body: '' }))
    await page.goto(`${origin}/lineup/${line.producer.id}?wine=${encodeURIComponent(product.wine_slug)}`, { waitUntil: 'commit' })
    await page.waitForFunction(src => [...document.querySelectorAll('img[data-map-image]')].some(image => image.dataset.mapImage === src && image.complete && image.naturalWidth === 0), product.image.src)
    releaseScripts()
    await page.locator('.plm-detail-image .plm-image-placeholder').waitFor({ state: 'visible' })
    await page.waitForFunction(src => ![...document.querySelectorAll('img[data-map-image]')].some(image => image.dataset.mapImage === src), product.image.src)
    assert.deepEqual(pageErrors, [])
    checks.push(activeCase)
  } finally {
    releaseScripts()
    await context.close()
  }
}

try {
  for (const [lineIndex, line] of producerMaps.entries()) {
    const initial = line.producer.id === 'novy-svet'
      ? line.products.filter(product => product.wine_slug).sort((a, b) => b.name.length - a.name.length)[0]
      : line.products.find(product => product.wine_slug)
    const gray = line.products.find(product => product.wine_slug === null)
    assert(initial && gray, `${line.producer.id}: linked and unlinked evidence required`)
    const viewports = [[1440, 'light'], [1440, 'dark'], [390, 'light'], [320, 'dark']]
    if (line.producer.id === 'soyuz-vino') viewports.push([767, 'light'], [768, 'dark'])
    for (const [width, theme] of viewports) {
      const mobile = width < 768
      const label = `${line.producer.id}-${width}-${theme}`
      activeCase = label
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
        await page.locator('[data-product-dialog]').waitFor({ state: 'attached' })
        assert.equal(await details.getAttribute('open'), null, `${label}: popup must stay closed on entry`)
        const before = await viewportState(page)
        await page.getByRole('button', { name: 'О выбранном вине', exact: true }).click()
        assert.equal(await details.getAttribute('open'), '')
        assert.equal(await details.locator('.plm-portal-link').getAttribute('href'), `https://vino-svoe.ru/wines/${initial.wine_slug}`)
        await assertLayout(page, `${label}-initial-popup`)
        const bounds = await details.boundingBox()
        assert(bounds && bounds.x >= 0 && bounds.y >= 0 && bounds.width <= width && bounds.y + bounds.height <= 845, `${label}: popup exceeds viewport`)
        await details.getByRole('button', { name: 'Вернуться к карте', exact: true }).click()
        assert.equal(await details.getAttribute('open'), null)
        assert.deepEqual(await viewportState(page), before, `${label}: return changed map position`)
      } else {
        assert.equal(await details.evaluate(element => element.tagName), 'ASIDE')
        assert.equal(await details.locator('.plm-portal-link').getAttribute('href'), `https://vino-svoe.ru/wines/${initial.wine_slug}`)
      }
      await assertLayout(page, `${label}-initial`)
      await openProduct(page, gray)
      assert(await page.locator(`[data-product-id="${gray.id}"]`).evaluate(element => element.classList.contains('is-unavailable')))
      assert.equal(await details.locator('.plm-portal-link').count(), 0)
      assert(await details.locator('.plm-detail-description').innerText())
      const grayGroup = line.groups.find(group => group.id === gray.group_id)
      assert.equal(await details.locator('.plm-detail-group-description').innerText(), grayGroup.description)
      assert.equal(await page.locator(`[data-group-container="${gray.group_id}"] .plm-group-description`).innerText(), grayGroup.description)
      assert.equal(await page.locator(`[data-product-id="${gray.id}"] .plm-unavailable-marker`).innerText(), 'Нет карточки')
      const methodFact = details.locator('.plm-facts > div').filter({ has: page.locator('dt', { hasText: 'Производство в группе' }) })
      assert.equal(await methodFact.count(), /^(?:Метод )?не указан/i.test(grayGroup.method.trim()) ? 0 : 1)
      if (gray.image?.frame) {
        const frame = details.locator('.plm-detail-image > [data-image-frame]')
        assert(await frame.evaluate(element => element.classList.contains('is-unavailable')), `${label}: gray frame class missing`)
        assert.equal(await frame.locator('img').evaluate(image => getComputedStyle(image).filter), 'none', `${label}: gray filter applied twice`)
        assert.equal(await page.locator(`[data-product-id="${gray.id}"] [data-image-frame] img`).evaluate(image => getComputedStyle(image).filter), 'none', `${label}: tile filter applied twice`)
        assert.equal(await frame.locator('img').getAttribute('class'), null, `${label}: consumer class leaked to the image`)
        assert(await frame.evaluate(element => element.getBoundingClientRect().height > 0), `${label}: empty frame`)
      }
      if (!gray.image) assert.equal(await details.locator('.plm-image-placeholder').innerText(), 'Нет изображения')
      if (mobile) assert.equal(await details.getAttribute('open'), '')
      await assertLayout(page, label)
      if (['derbent-vino', 'fanagoria', 'massandra', 'soyuz-vino', 'esse', 'chateau-pinot', 'valery-zakharyin', 'novy-svet', 'belbek', 'sober-bash', 'agora'].includes(line.producer.id)) await page.screenshot({ path: `${report}/${label}.png`, fullPage: !mobile })
      if (mobile) await details.getByRole('button', { name: 'Закрыть информацию о вине', exact: true }).click()
      const missingImage = line.products.find(product => !product.image && product.wine_slug)
      if (missingImage) {
        await openProduct(page, missingImage)
        assert.equal(await details.locator('.plm-image-placeholder').innerText(), 'Нет изображения')
        assert.equal(await details.locator('.plm-portal-link').getAttribute('href'), `https://vino-svoe.ru/wines/${missingImage.wine_slug}`)
        if (mobile) await page.keyboard.press('Escape')
      }
      if (['fanagoria', 'kuban-vino', 'soyuz-vino'].includes(line.producer.id) && ((width === 1440 && theme === 'light') || (width === 320 && theme === 'dark'))) {
        await page.getByRole('button', { name: 'Открыть все', exact: true }).click()
        await page.waitForFunction(count => {
          const groups = [...document.querySelectorAll('[data-group-id]')]
          return groups.length === count && groups.every(group => group.getAttribute('aria-expanded') === 'true')
        }, line.groups.length)
        await assertLayout(page, `${label}-expanded`)
        await page.getByRole('button', { name: 'Свернуть все', exact: true }).click()
        await page.waitForFunction(count => {
          const groups = [...document.querySelectorAll('[data-group-id]')]
          return groups.length === count && groups.every(group => group.getAttribute('aria-expanded') === 'false')
        }, line.groups.length)
        await assertLayout(page, `${label}-collapsed`)
        checks.push(`${label}-expand-collapse-all`)
      }
      const next = producerMaps[(lineIndex + 1) % producerMaps.length]
      await page.getByRole('combobox', { name: 'Производитель', exact: true }).selectOption(next.producer.id)
      assert.equal(new URL(page.url()).pathname, `/lineup/${line.producer.id}`, 'Changing the producer selection must not navigate before submission')
      await page.getByRole('button', { name: 'Открыть карту', exact: true }).click()
      await page.waitForURL(`**/lineup/${next.producer.id}`)
      await page.waitForFunction(id => document.querySelector('.product-line-map')?.dataset.producerId === id && document.querySelector('[data-product-detail]')?.getAttribute('data-selected-product') === '', next.producer.id)
      if (mobile) await page.locator('[data-product-dialog]').waitFor({ state: 'attached' })
      assert.equal(await page.locator('[data-product-dialog][open]').count(), 0)
      await assertLayout(page, `${label}-navigation`)
      checks.push(label)
      await context.close()
    }
  }
  await imageFailureBeforeHydration()
  assert.deepEqual(errors, [])
  status = 'passed'
  console.log(JSON.stringify({ browser: browserName, status, checks: checks.length, errors }, null, 2))
} catch (error) {
  failure = { case: activeCase, message: error instanceof Error ? error.message : String(error), stack: error instanceof Error ? error.stack : undefined }
  throw error
} finally {
  try {
    await writeFile(`${report}/results.json`, JSON.stringify({ browser: browserName, status, checks, errors, failure }, null, 2) + '\n')
  } finally {
    await browser.close()
  }
}
