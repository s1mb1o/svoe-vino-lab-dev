import assert from 'node:assert/strict'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

assert(process.env.PLAYWRIGHT_MODULE, 'Set PLAYWRIGHT_MODULE to an installed Playwright index.mjs.')
const { chromium, webkit } = await import(process.env.PLAYWRIGHT_MODULE)
const origin = process.env.PORTAL_ORIGIN || 'http://127.0.0.1:18573'
const output = process.env.BROWSER_ARTIFACT_DIR || '/tmp/dinner-upload-check'
await mkdir(output, { recursive: true })
const heic = [...await readFile(new URL('../tests/data/dinner-rotated.heic', import.meta.url))]
const unknown = { status: 'needs_category', resolved_node_id: null, results: [], needs_clarification: true, clarification_question: 'Выберите категорию блюда.' }
const receipts = []
const credentials = process.env.PORTAL_BASIC_USER && process.env.PORTAL_BASIC_PASSWORD
  ? { username: process.env.PORTAL_BASIC_USER, password: process.env.PORTAL_BASIC_PASSWORD } : undefined

async function dataTransfer(page, files) {
  return page.evaluateHandle(files => {
    const transfer = new DataTransfer()
    for (const file of files) transfer.items.add(new File([new Uint8Array(file.bytes || file.size || 0)], file.name, { type: file.type }))
    return transfer
  }, files)
}
async function drop(page, files, screenshot) {
  const transfer = await dataTransfer(page, files)
  try {
    const panel = page.getByRole('region', { name: 'Загрузка фото блюда', exact: true })
    await panel.dispatchEvent('dragenter', { dataTransfer: transfer })
    await panel.dispatchEvent('dragover', { dataTransfer: transfer })
    if (files.length) {
      assert(await panel.evaluate(node => node.classList.contains('dragging')))
      await page.locator('.dinner-photo-copy').dispatchEvent('dragenter', { dataTransfer: transfer })
      await page.locator('.dinner-photo-copy').dispatchEvent('dragleave', { dataTransfer: transfer })
      assert(await panel.evaluate(node => node.classList.contains('dragging')), 'Nested targets must keep the drop highlight')
      if (screenshot) await panel.screenshot({ path: screenshot })
    }
    await panel.dispatchEvent('drop', { dataTransfer: transfer })
    assert.equal(await panel.evaluate(node => node.classList.contains('dragging')), false)
  } finally { await transfer.dispose() }
}
async function idle(page) { await page.waitForFunction(() => !document.querySelector('.dinner-progress'), undefined, { timeout: 70_000 }) }

for (const [name, engine, viewport, mobile, colorScheme] of [
  ['desktop-dark', chromium, { width: 1440, height: 1000 }, false, 'dark'],
  ['desktop-light', chromium, { width: 1440, height: 1000 }, false, 'light'],
  ['mobile-320', chromium, { width: 320, height: 740 }, true, 'dark'],
  ['mobile-webkit', webkit, { width: 390, height: 844 }, true, 'dark'],
]) {
  const browser = await engine.launch({ headless: true })
  const context = await browser.newContext({ viewport, isMobile: mobile, hasTouch: mobile, colorScheme, httpCredentials: credentials })
  await context.addInitScript(() => localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes'))
  await context.route('https://mc.yandex.ru/**', route => route.abort())
  const page = await context.newPage(); const calls = []; const errors = []; const decoderRequests = []
  page.on('request', request => { if (request.url().includes('/third-party/heic-to-')) decoderRequests.push(request.url()) })
  page.on('pageerror', error => errors.push(error.message))
  await context.route('**/api/dinner/recognize', route => { calls.push(route.request().postDataJSON()); return route.fulfill({ json: unknown }) })
  try {
    await page.goto(origin + '/dish', { waitUntil: 'networkidle' })
    const accept = await page.locator('input[aria-label="Фото блюда"]').getAttribute('accept')
    for (const extension of ['.jpg', '.jpeg', '.heic', '.heif', '.png', '.webp']) assert(accept.includes(extension))
    const cameraAccept = await page.locator('input[capture="environment"]').getAttribute('accept')
    for (const type of ['image/jpeg', 'image/heic', 'image/png', 'image/webp']) assert(cameraAccept.includes(type))
    assert(!cameraAccept.includes('.heic'), 'The camera intent uses MIME types rather than extension filters')
    const raster = await page.evaluate(() => {
      const canvas = document.createElement('canvas'); canvas.width = 64; canvas.height = 32
      const context = canvas.getContext('2d'); context.fillStyle = 'red'; context.fillRect(0, 0, 32, 32)
      context.fillStyle = 'blue'; context.fillRect(32, 0, 32, 32)
      return Object.fromEntries(['image/jpeg', 'image/png', 'image/webp'].map(type => [type, canvas.toDataURL(type).split(',')[1]]))
    })
    const fixtures = [
      { name: 'dish.jpg', type: 'image/jpeg', bytes: [...Buffer.from(raster['image/jpeg'], 'base64')] },
      { name: 'dish.JPEG', type: '', bytes: [...Buffer.from(raster['image/jpeg'], 'base64')] },
      { name: 'dish.png', type: 'image/png', bytes: [...Buffer.from(raster['image/png'], 'base64')] },
      { name: 'dish.webp', type: 'application/octet-stream', bytes: [...Buffer.from(raster['image/webp'], 'base64')] },
      { name: 'dish.heic', type: 'image/heic', bytes: heic },
      { name: 'dish.HEIC', type: 'application/octet-stream', bytes: heic },
      { name: 'dish.heif', type: '', bytes: heic },
    ]
    const privateMarker = 'private-upload-test-marker'
    for (const fixture of fixtures.filter(file => /jpe?g/i.test(file.name))) {
      const comment = [...Buffer.from(privateMarker)]
      fixture.bytes = [...fixture.bytes.slice(0, 2), 255, 254, 0, comment.length + 2, ...comment, ...fixture.bytes.slice(2)]
    }
    const formats = []
    for (const fixture of fixtures) {
      if (fixture.name === 'dish.heic') assert.equal(decoderRequests.length, 0, 'The HEIC decoder must not load for ordinary images or first paint')
      const before = calls.length
      await drop(page, [fixture], fixture.name === 'dish.jpg' ? resolve(output, name + '-drop.png') : undefined)
      await page.waitForFunction(() => document.querySelector('.dinner-question'))
      await idle(page)
      assert.equal(calls.length, before + 1)
      assert(calls.at(-1).image_base64.startsWith('data:image/jpeg;base64,'))
      assert(!Buffer.from(calls.at(-1).image_base64.split(',')[1], 'base64').includes(Buffer.from(privateMarker)), 'Source metadata must not be copied; browser-generated image properties are allowed')
      assert.equal(await page.locator('.dinner-wine').count(), 0, 'No wine can appear before explicit confirmation')
      assert.equal(await page.locator('.dinner-error').count(), 0)
      if (/heic|heif/i.test(fixture.name)) {
        const pixels = await page.evaluate(async () => {
          const image = document.querySelector('.dinner-preview img'); await image.decode()
          const canvas = document.createElement('canvas'); canvas.width = image.naturalWidth; canvas.height = image.naturalHeight
          const context = canvas.getContext('2d'); context.drawImage(image, 0, 0)
          return { width: canvas.width, height: canvas.height, top: [...context.getImageData(canvas.width / 2, 2, 1, 1).data], bottom: [...context.getImageData(canvas.width / 2, canvas.height - 3, 1, 1).data] }
        })
        assert.equal(pixels.width, 32); assert.equal(pixels.height, 64)
        assert(pixels.top[0] > 200 && pixels.top[2] < 60 && pixels.bottom[0] < 60 && pixels.bottom[2] > 200, 'HEIC orientation must be applied once')
      }
      formats.push({ name: fixture.name, normalized: 'image/jpeg', passed: true })
    }
    const before = calls.length
    await drop(page, []); assert.equal(calls.length, before)
    await drop(page, [fixtures[0], fixtures[1]])
    await page.getByRole('alert').filter({ hasText: 'одну фотографию' }).waitFor()
    assert.equal(calls.length, before)
    await drop(page, [{ name: 'fake.jpg', type: 'image/jpeg', bytes: [...Buffer.from('<svg></svg>')] }])
    await page.getByRole('alert').filter({ hasText: 'HEIC' }).waitFor()
    assert.equal(calls.length, before, 'Invalid images must never reach the model')
    await drop(page, [{ name: 'broken.heic', type: 'image/heic', bytes: heic.slice(0, 100) }])
    await idle(page); await page.getByRole('alert').waitFor(); assert.equal(calls.length, before)
    await drop(page, [{ name: 'oversized.jpg', type: 'image/jpeg', size: 10 * 1024 * 1024 + 1 }])
    await page.getByRole('alert').filter({ hasText: '10 МБ' }).waitFor(); assert.equal(calls.length, before)
    await page.locator('input[aria-label="Фото блюда"]').setInputFiles({ name: 'picker.heic', mimeType: 'image/heic', buffer: Buffer.from(heic) })
    await page.waitForFunction(() => document.querySelector('.dinner-question')); await idle(page)
    assert.equal(calls.length, before + 1, 'The picker must use the same HEIC normalization')
    assert(decoderRequests.length > 0)
    let release; let firstSeen
    const held = new Promise(resolve => { release = resolve }); const seen = new Promise(resolve => { firstSeen = resolve })
    let holdFirst = true
    await context.route('**/api/dinner/recognize', async route => {
      calls.push(route.request().postDataJSON())
      const obsolete = holdFirst; holdFirst = false
      if (obsolete) { firstSeen(); await held }
      await route.fulfill({ json: { ...unknown, clarification_question: obsolete ? 'Obsolete test response.' : unknown.clarification_question } }).catch(() => {})
    })
    await drop(page, [fixtures[0]]); await seen
    await drop(page, [fixtures[2]])
    await page.locator('.dinner-question').filter({ hasText: unknown.clarification_question }).waitFor(); await idle(page)
    release()
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
    assert.equal(await page.locator('#dinner-dish').inputValue(), '')
    assert.equal(await page.locator('.dinner-question').textContent(), unknown.clarification_question)
    assert.equal(await page.locator('.dinner-preview img').getAttribute('src'), calls.at(-1).image_base64)
    const outside = await dataTransfer(page, [fixtures[0]])
    assert(await page.locator('.hero h1').evaluate((target, transfer) => !target.dispatchEvent(new DragEvent('drop', { dataTransfer: transfer, bubbles: true, cancelable: true })), outside), 'Outside file drops must prevent browser navigation')
    await outside.dispose()
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    assert.deepEqual(errors, [])
    await page.screenshot({ path: resolve(output, name + '-confirmed.png'), fullPage: true })
    receipts.push({ name, viewport, formats, invalidUploadsRejected: true, pickerHeic: true, pendingReplacement: true, lazyDecoder: true, noBrowserErrors: true })
  } finally { await context.close(); await browser.close() }
}
if (process.env.DINNER_HEIC_LIVE_IMAGE) {
  const browser = await chromium.launch({ headless: true }); const context = await browser.newContext({ httpCredentials: credentials })
  await context.addInitScript(() => localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes'))
  await context.route('https://mc.yandex.ru/**', route => route.abort())
  const page = await context.newPage()
  try {
    await page.goto(origin + '/dish', { waitUntil: 'networkidle' })
    const response = page.waitForResponse(response => response.url().endsWith('/api/dinner/recognize'), { timeout: 200_000 })
    await drop(page, [{ name: 'dish.heic', type: 'image/heic', bytes: [...await readFile(process.env.DINNER_HEIC_LIVE_IMAGE)] }])
    assert.equal((await response).status(), 200); await idle(page)
    assert.equal(await page.locator('.dinner-wine').count(), 0)
    await page.locator('#dinner-dish').fill('Стейк рибай на гриле')
    await page.getByRole('button', { name: 'Подтвердить и подобрать вино', exact: true }).click()
    await page.locator('.dinner-wine').first().waitFor()
    receipts.push({ name: 'real-service-heic-drop', passed: true, recognitionAndConfirmation: true })
  } finally { await context.close(); await browser.close() }
}
await writeFile(resolve(output, 'results.json'), JSON.stringify({ origin, receipts }, null, 2) + '\n')
console.log(JSON.stringify({ passed: true, origin, suites: receipts.length, output }))
