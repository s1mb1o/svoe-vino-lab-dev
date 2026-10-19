import assert from 'node:assert/strict'
import { mkdir, readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

assert(process.env.PLAYWRIGHT_MODULE, 'Set PLAYWRIGHT_MODULE to a local playwright/index.mjs.')
const { chromium, webkit } = await import(process.env.PLAYWRIGHT_MODULE)
const browserName = process.env.PLAYWRIGHT_BROWSER || 'chromium'
assert(['chromium', 'webkit'].includes(browserName), 'PLAYWRIGHT_BROWSER must be chromium or webkit.')
const origin = process.env.PORTAL_ORIGIN || 'http://127.0.0.1:8153'
const reportDirectory = browserName === 'chromium' ? 'reports/product-line-map' : 'reports/product-line-map/webkit'
const graph = JSON.parse(await readFile('shared/data/product-line-maps/abrau-durso.json', 'utf8'))
const alias = 'abrau-dyurso-victor-dravigny-bryut'
const initialId = 'victor-dravigny-brut'
const grayId = 'victor-dravigny-zero-dosage'
const initialProduct = graph.products.find(product => product.id === initialId)
const uploadPath = resolve(`public${initialProduct.image.src}`)
// The index holds the first image as a cover. The last image exists only in the map chunk.
const lastImageSrc = graph.products.filter(product => product.image).at(-1).image.src
const browser = await ({ chromium, webkit })[browserName].launch({ headless: true })
const errors = []
const checks = []
const popupStates = new WeakMap()
await mkdir(reportDirectory, { recursive: true })

function observe(page, label) {
  page.on('pageerror', error => errors.push(`${label}: ${error.message}`))
  page.on('console', message => {
    if (message.type() === 'error' || /hydration/i.test(message.text())) errors.push(`${label}: ${message.text()}`)
  })
}

async function newContext(width = 1440, height = 1000, theme = 'light') {
  const context = await browser.newContext({ viewport: { width, height }, colorScheme: theme, isMobile: width < 768, hasTouch: width < 768, reducedMotion: 'reduce', serviceWorkers: 'block' })
  await context.addInitScript(() => {
    localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes')
    localStorage.removeItem('svoe-vino.theme.v1')
  })
  return context
}

async function settle(page) {
  await page.evaluate(async () => {
    await document.fonts.ready
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
  })
}

async function screenshot(page, name, fullPage = true) {
  // Keep document scroll while a modal is open. Full-page captures start at the page top.
  if (fullPage) await page.evaluate(() => window.scrollTo({ top: 0, left: 0, behavior: 'instant' }))
  await settle(page)
  await page.screenshot({ path: `${reportDirectory}/${name}.png`, fullPage })
}

async function overflowAndImages(page, label) {
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${label}: document overflow`)
  const broken = await page.locator('img').evaluateAll(images => images.filter(image => image.complete && image.naturalWidth === 0).map(image => image.currentSrc || image.src))
  assert.deepEqual(broken, [], `${label}: broken images`)
}

async function assertControlVisible(control, label, requireViewport = true) {
  const visibility = await control.evaluate((element, inViewport) => {
    const box = element.getBoundingClientRect()
    const clippedBy = []
    const clipping = inViewport ? /(hidden|auto|scroll|clip)/ : /(hidden|clip)/
    for (let parent = element.parentElement; parent; parent = parent.parentElement) {
      const style = getComputedStyle(parent)
      const rect = parent.getBoundingClientRect()
      if (clipping.test(style.overflowY) && (box.top < rect.top - 2 || box.bottom > rect.bottom + 2)) clippedBy.push(parent.className || parent.tagName)
      if (clipping.test(style.overflowX) && (box.left < rect.left - 2 || box.right > rect.right + 2)) clippedBy.push(parent.className || parent.tagName)
      if (parent.tagName === 'DIALOG') break
    }
    const onScreen = box.top >= -2 && box.left >= -2 && box.bottom <= innerHeight + 2 && box.right <= innerWidth + 2
    const hit = onScreen ? document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2) : null
    return { clippedBy, onScreen, unobstructed: Boolean(hit && element.contains(hit)), width: box.width, height: box.height, requireViewport: inViewport }
  }, requireViewport)
  assert(visibility.width > 0 && visibility.height > 0, `${label}: empty control`)
  assert.deepEqual(visibility.clippedBy, [], `${label}: clipped by an ancestor`)
  if (requireViewport) {
    assert(visibility.onScreen, `${label}: outside the viewport`)
    assert(visibility.unobstructed, `${label}: covered by another element`)
  }
}

async function selection(map, id) {
  await map.locator(`[data-product-detail][data-selected-product="${id}"]`).waitFor({ state: 'attached' })
  assert.equal(await map.locator(`[data-product-id="${id}"]`).getAttribute('aria-pressed'), 'true')
}

async function assertCentered(map, id) {
  if (await map.getAttribute('data-map-layout') === 'page') {
    // The page layout centers the selected product in the window.
    await map.evaluate((root, productId) => new Promise((resolve, reject) => {
      const start = performance.now()
      const check = () => {
        const node = root.querySelector(`[data-product-id="${productId}"]`)
        if (!node) return reject(new Error(`Missing selected node ${productId}`))
        const n = node.getBoundingClientRect()
        const inset = (root.querySelector('.plm-toolbar')?.offsetHeight ?? 0) + 16
        const expectedTop = Math.max(0, Math.min(document.documentElement.scrollHeight - innerHeight, scrollY + n.top - Math.max(inset, (innerHeight - n.height) / 2)))
        const centered = Math.abs(scrollY - expectedTop) <= 4
        const visible = n.top >= -2 && n.bottom <= innerHeight + 2
        if (centered && visible) return resolve(true)
        if (performance.now() - start > 3000) return reject(new Error(`Selected node is not centered in the page: ${JSON.stringify({ productId, scrollY, expectedTop, visible })}`))
        requestAnimationFrame(check)
      }
      check()
    }), id)
    return
  }
  await map.locator('[data-map-viewport]').evaluate((frame, productId) => new Promise((resolve, reject) => {
    const start = performance.now()
    const check = () => {
      const node = frame.querySelector(`[data-product-id="${productId}"]`)
      if (!node) return reject(new Error(`Missing selected node ${productId}`))
      const f = frame.getBoundingClientRect()
      const n = node.getBoundingClientRect()
      const expectedLeft = Math.max(0, Math.min(frame.scrollWidth - frame.clientWidth, frame.scrollLeft + n.left - f.left - (frame.clientWidth - n.width) / 2))
      const expectedTop = Math.max(0, Math.min(frame.scrollHeight - frame.clientHeight, frame.scrollTop + n.top - f.top - (frame.clientHeight - n.height) / 2))
      const centered = Math.abs(frame.scrollLeft - expectedLeft) <= 4 && Math.abs(frame.scrollTop - expectedTop) <= 4
      const visible = n.left >= f.left - 2 && n.right <= f.right + 2 && n.top >= f.top - 2 && n.bottom <= f.bottom + 2
      if (centered && visible) return resolve(true)
      if (performance.now() - start > 3000) return reject(new Error(`Selected node is not centered: ${JSON.stringify({ productId, scrollTop: frame.scrollTop, expectedTop, scrollLeft: frame.scrollLeft, expectedLeft, visible })}`))
      requestAnimationFrame(check)
    }
    check()
  }), id)
}

async function canvasState(map) {
  return map.evaluate(root => {
    const frame = root.querySelector('[data-map-viewport]')
    return { left: frame.scrollLeft, top: frame.scrollTop, zoom: root.querySelector('.plm-zoom')?.textContent ?? null, selected: root.querySelector('[data-product-detail]').dataset.selectedProduct }
  })
}

function infoPopup(map) { return map.locator('dialog[data-product-detail]') }
function infoTrigger(map) { return map.getByRole('button', { name: 'О выбранном вине', exact: true }) }
// The page layout shows details in the popup at every width. The canvas layout uses it up to 767 px.
async function popupMode(map) { return map.evaluate(root => root.dataset.mapLayout === 'page' || innerWidth <= 767) }
function locateButton(map, recognized) { return map.getByRole('button', { name: recognized ? 'Показать ваше вино' : 'Показать исходное вино', exact: true }) }

// The guide dialog of a recognized wine keeps the pan and zoom canvas.
async function openDialogMap(page) {
  const fixture = wineFixture()
  await page.route('**/api/config', route => route.fulfill({ json: { apiAvailable: true, predictionMode: 'upstream', shelfAvailable: true } }))
  await page.route('**/api/predict', route => route.fulfill({ headers: { 'X-Prediction-Mode': 'upstream' }, json: { slug: fixture.slug } }))
  await page.route('**/api/wines/*', route => route.fulfill({ json: fixture }))
  // Client navigation makes the test-only config fixture independent of server configuration.
  await page.goto(`${origin}/lineup/abrau-durso`, { waitUntil: 'networkidle' })
  await page.getByRole('link', { name: 'К сканеру', exact: true }).click()
  await page.waitForURL(`${origin}/`)
  await page.getByLabel('Выбрать фотографию этикетки', { exact: true }).setInputFiles(uploadPath)
  const opener = page.getByRole('button', { name: /Путеводитель по линейке/ })
  await opener.waitFor()
  await opener.click()
  const map = page.locator('dialog.product-line-dialog[open] .product-line-map')
  await selection(map, initialId)
  return map
}

async function mapAndPageState(map) {
  return {
    canvas: await canvasState(map),
    outer: await map.evaluate(root => {
      const parent = root.closest('dialog')
      return { x: window.scrollX, y: window.scrollY, left: parent?.scrollLeft || 0, top: parent?.scrollTop || 0 }
    }),
  }
}

async function assertInfoPopup(map) {
  const popup = infoPopup(map)
  await popup.waitFor({ state: 'visible' })
  await settle(map.page())
  assert(await popup.evaluate(element => element.matches(':modal')), 'Mobile information must use a native modal dialog')
  assert(await popup.locator('.plm-detail-heading h3').evaluate(element => element === document.activeElement), 'Opening mobile details must focus its heading')
  await assertControlVisible(popup.locator('.plm-detail-heading h3'), 'The focused popup heading must be visible')
  assert.equal(await popup.getByRole('button', { name: 'Подробнее о вине', exact: true }).count(), 0, 'The popup must expose full details without a second expansion')
  assert(await popup.locator('.plm-detail-content').evaluate(element => element.clientHeight > 0), 'The popup must have readable content')
  await assertControlVisible(popup.getByRole('button', { name: /Закрыть/ }), 'Mobile popup close button')
}

async function openMobileInfo(map) {
  const opener = infoTrigger(map)
  await opener.scrollIntoViewIfNeeded()
  await settle(map.page())
  popupStates.set(map, { opener, state: await mapAndPageState(map) })
  await opener.click()
  await assertInfoPopup(map)
}

async function closeMobileInfo(map, method = 'return') {
  const popup = infoPopup(map)
  const previous = popupStates.get(map)
  assert(previous, 'The test must record the popup opener and scroll state')
  if (method === 'escape') await map.page().keyboard.press('Escape')
  else if (method === 'backdrop') {
    const bounds = await popup.boundingBox()
    assert(bounds.x > 2 || bounds.y > 2, 'The popup must leave a clickable backdrop')
    await map.page().mouse.click(bounds.x > 2 ? bounds.x / 2 : bounds.x + bounds.width / 2, bounds.x > 2 ? bounds.y + bounds.height / 2 : bounds.y / 2)
  } else {
    await popup.getByRole('button', { name: method === 'close' ? /Закрыть/ : 'Вернуться к карте', exact: method !== 'close' }).click()
  }
  await popup.waitFor({ state: 'hidden' })
  await settle(map.page())
  assert.deepEqual(await mapAndPageState(map), previous.state, `${method}: closing mobile details must preserve canvas, selection, zoom, and outer scroll`)
  assert(await previous.opener.evaluate(element => element === document.activeElement), `${method}: closing mobile details must restore its exact opener`)
  popupStates.delete(map)
}

async function assertInfoFocusTrap(map) {
  const popup = infoPopup(map)
  await popup.getByRole('button', { name: /Закрыть/ }).focus()
  for (const key of ['Shift+Tab', 'Tab', 'Tab', 'Tab', 'Tab']) {
    await map.page().keyboard.press(key)
    // Native dialogs can hand Tab focus to browser chrome, represented by an unfocused BODY.
    // Application controls outside the modal must never receive that focus.
    const focus = await popup.evaluate(element => ({
      inside: element.contains(document.activeElement), hasFocus: document.hasFocus(),
      tag: document.activeElement?.tagName, className: document.activeElement?.className,
      label: document.activeElement?.getAttribute('aria-label'),
    }))
    assert(focus.inside || (!focus.hasFocus && focus.tag === 'BODY'), `Modal keyboard navigation must not focus the underlying application: ${JSON.stringify({ key, ...focus })}`)
  }
  if (!await map.page().evaluate(() => document.hasFocus())) await map.page().keyboard.press('Tab')
  assert(await popup.evaluate(element => element.contains(document.activeElement)), 'Keyboard focus must return from browser chrome to the modal')
  const outsideTargets = [map.locator('[data-map-viewport]')]
  const shelfReturn = map.page().locator('dialog.shelf-dialog[open] .shelf-return')
  if (await shelfReturn.count()) outsideTargets.push(shelfReturn)
  for (const target of outsideTargets) {
    await target.evaluate(element => element.focus())
    const outsideAttempt = await popup.evaluate(element => ({ inside: element.contains(document.activeElement), tag: document.activeElement?.tagName, className: document.activeElement?.className, hasFocus: document.hasFocus() }))
    assert(outsideAttempt.inside, `The modal must contain focus after an underlying-control focus attempt: ${JSON.stringify(outsideAttempt)}`)
  }
}

async function chooseProduct(map, groupId, productId) {
  const mobile = await popupMode(map)
  if (mobile && await infoPopup(map).isVisible()) await closeMobileInfo(map)
  await map.getByRole('combobox', { name: 'Перейти к группе' }).selectOption(groupId)
  assert.equal(await map.locator(`[data-group-id="${groupId}"]`).getAttribute('aria-expanded'), 'true')
  const opener = map.locator(`[data-product-id="${productId}"]`)
  if (mobile) {
    await opener.scrollIntoViewIfNeeded()
    await settle(map.page())
    const state = await mapAndPageState(map)
    state.canvas.selected = productId
    popupStates.set(map, { opener, state })
  }
  await opener.click()
  await selection(map, productId)
  if (mobile) await assertInfoPopup(map)
}

async function delayedFontCentering() {
  const context = await newContext()
  const page = await context.newPage()
  let releaseFont
  const fontReady = new Promise(resolve => { releaseFont = resolve })
  try {
    await page.route('**/reference/playfair-display.woff2', async route => { await fontReady; await route.continue() })
    await page.goto(`${origin}/lineup/abrau-durso?wine=${alias}`, { waitUntil: 'domcontentloaded' })
    await page.waitForFunction(() => {
      const surface = document.querySelector('.plm-surface')
      return surface && surface.style.height !== '1800px' && document.fonts.status === 'loading'
    })
    releaseFont()
    await settle(page)
    const map = page.locator('.product-line-map')
    await selection(map, initialId)
    await assertCentered(map, initialId)
    checks.push('Initial selection stays centered after a delayed web font changes group height')
  } finally {
    releaseFont()
    await context.close()
  }
}

async function screenshotsAndResponsiveStates() {
  for (const layout of ['page', 'dialog']) {
  for (const theme of ['light', 'dark']) {
    for (const [width, height] of [[1440, 1000], [390, 844], [320, 740]]) {
      const context = await newContext(width, height, theme)
      const page = await context.newPage()
      const label = `${layout}-${width}-${theme}`
      observe(page, label)
      let map = page.locator('.product-line-map')
      if (layout === 'page') await page.goto(`${origin}/lineup/abrau-durso?wine=${alias}`, { waitUntil: 'networkidle' })
      else map = await openDialogMap(page)
      await settle(page)
      const recognized = layout === 'dialog'
      const popup = layout === 'page' || width < 768
      await selection(map, initialId)
      await assertCentered(map, initialId)
      if (recognized) assert.equal(await map.locator('[data-recognized="true"]').count(), 1, 'A recognized wine must be marked')
      else {
        assert.equal(await map.locator('[data-recognized="true"]').count(), 0, 'A deep link must not claim recognition')
        assert.equal(await map.locator('.plm-current-marker').count(), 0)
      }
      assert.equal(await page.locator('html').getAttribute('data-theme'), theme, 'The system theme must be respected')
      if (layout === 'page') {
        assert(await map.locator('[data-map-viewport]').evaluate(element => getComputedStyle(element).overflowY === 'visible' && element.scrollHeight <= element.clientHeight + 1), `${label}: the page map must not scroll inside the page`)
        assert.equal(await map.getByRole('button', { name: 'Увеличить карту', exact: true }).count(), 0, `${label}: the page map has no zoom buttons`)
      }
      if (popup) {
        assert.equal(await infoPopup(map).isVisible(), false, 'The initial selection must leave its information popup closed')
        assert.equal(await map.locator('aside[data-product-detail]').count(), 0, 'Popup details must not remain as a side or bottom card')
        await openMobileInfo(map)
        await assertInfoFocusTrap(map)
      }
      assert.equal(await map.locator('.plm-portal-link').getAttribute('href'), `https://vino-svoe.ru/wines/${initialProduct.wine_slug}`)
      assert.equal(await map.locator('.plm-portal-link').getAttribute('target'), '_blank')
      if (!popup) {
        assert(await map.evaluate(root => root.querySelector('[data-product-detail]').getBoundingClientRect().left > root.querySelector('[data-map-viewport]').getBoundingClientRect().right), `${label}: desktop card must sit beside map`)
      } else await closeMobileInfo(map, 'close')
      await overflowAndImages(page, label)
      if (width === 1440) await screenshot(page, `${label}-alias`)

      await chooseProduct(map, 'victor-dravigny', grayId)
      assert(await map.locator(`[data-product-id="${grayId}"]`).evaluate(element => element.classList.contains('is-unavailable')))
      assert.match(await map.locator(`[data-product-id="${grayId}"] img`).evaluate(element => getComputedStyle(element.closest('[data-image-frame]') || element).filter), /grayscale\(1\)/)
      const contrasts = await map.locator(`[data-product-id="${grayId}"]`).evaluate(element => {
        const luminance = color => {
          const channels = color.match(/[\d.]+/g).slice(0, 3).map(Number).map(value => {
            const channel = value / 255
            return channel <= .04045 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4
          })
          return channels[0] * .2126 + channels[1] * .7152 + channels[2] * .0722
        }
        const background = luminance(getComputedStyle(element).backgroundColor)
        return [...element.querySelectorAll('strong, .plm-product-style, .plm-unavailable-marker')].map(text => {
          const foreground = luminance(getComputedStyle(text).color)
          return { text: text.textContent, ratio: (Math.max(foreground, background) + .05) / (Math.min(foreground, background) + .05) }
        })
      })
      assert.equal(contrasts.length, 3)
      for (const contrast of contrasts) assert(contrast.ratio >= 4.5, `${label}: gray product text contrast is below 4.5:1: ${JSON.stringify(contrast)}`)
      assert.equal(await map.locator('.plm-portal-link').count(), 0, 'An unlinked product must not have a portal link')
      assert(await map.locator('.plm-detail-description').isVisible())
      assert.match(await map.locator('.plm-detail-description').innerText(), /2020.*2024/s)
      assert.match(await map.locator('.plm-availability').innerText(), /не означает/i)
      await overflowAndImages(page, `${label}-gray`)
      if (popup) {
        await screenshot(page, `${label}-gray-popup`, false)
        await closeMobileInfo(map)
        if (layout === 'dialog') {
          await map.getByRole('button', { name: 'Увеличить карту', exact: true }).click()
          await settle(page)
        }
        for (const method of ['return', 'escape', 'backdrop']) {
          await openMobileInfo(map)
          assert.equal(await infoPopup(map).getAttribute('data-selected-product'), grayId)
          await closeMobileInfo(map, method)
        }
      } else {
        await map.getByRole('button', { name: 'Увеличить карту', exact: true }).click()
        const beforeReturn = await canvasState(map)
        await map.getByRole('button', { name: 'Вернуться к карте', exact: true }).click()
        assert.deepEqual(await canvasState(map), beforeReturn, `${label}: return must preserve selection, zoom and canvas scroll`)
        await map.getByRole('button', { name: 'Показать карточку', exact: true }).click()
        assert.equal(await map.locator('[data-product-detail]').getAttribute('data-selected-product'), grayId)
      }
      await locateButton(map, recognized).click()
      await selection(map, initialId)
      await assertCentered(map, initialId)

      if (layout === 'dialog' && browserName === 'chromium' && width === 390 && theme === 'light') {
        const viewport = map.locator('[data-map-viewport]')
        await viewport.scrollIntoViewIfNeeded()
        const box = await viewport.boundingBox()
        const before = await viewport.evaluate(element => element.scrollTop)
        const session = await context.newCDPSession(page)
        const x = box.x + box.width * .6
        const y = box.y + box.height * .7
        await session.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] })
        for (let step = 1; step <= 8; step++) {
          await session.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x, y: y - step * 15 }] })
          await new Promise(resolve => setTimeout(resolve, 20))
        }
        await session.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] })
        await page.waitForFunction(([selector, top]) => document.querySelector(selector).scrollTop > top + 30, ['[data-map-viewport]', before])
        assert.equal(await map.locator('[data-product-detail]').getAttribute('data-selected-product'), initialId, 'Touch pan must not select a product')
        await session.detach()
        checks.push('Native touch pan')
      }
      await context.close()
    }
  }
  }
  checks.push('Page and dialog layouts at six viewport/theme combinations: alias selection/centering, no inner scroll on the page, popup details/focus trap/all close actions, gray details, portal links, preserved scroll state, locate; dialog touch pan')
}

async function overviewPage() {
  const context = await newContext()
  const page = await context.newPage()
  observe(page, 'overview-page')
  await page.goto(`${origin}/lineup/abrau-durso`, { waitUntil: 'networkidle' })
  const map = page.locator('.product-line-map')
  assert.equal(await map.locator('[data-product-detail]').getAttribute('data-selected-product'), '')
  assert.equal(await map.locator('[data-recognized="true"], .plm-current-marker').count(), 0)
  assert.equal(await map.locator('[data-group-id]').count(), graph.groups.length)
  assert.equal(await map.locator('[data-group-id][aria-expanded="true"]').count(), 0)
  assert.equal(await map.locator('[data-product-id]').count(), graph.products.length)
  const imperialToggle = map.locator('[data-group-id="imperial"]')
  await map.getByRole('button', { name: 'Открыть группу Империал', exact: true }).focus()
  await page.keyboard.press('Enter')
  await settle(page)
  assert.equal(await imperialToggle.getAttribute('aria-expanded'), 'true')
  assert(await imperialToggle.evaluate(element => element === document.activeElement), 'A removed collection preview must transfer focus to its stable toggle')
  await page.keyboard.press('Enter')
  assert.equal(await imperialToggle.getAttribute('aria-expanded'), 'false')

  const picker = map.getByRole('combobox', { name: 'Перейти к группе' })
  await picker.focus()
  await picker.selectOption('victor-dravigny')
  await settle(page)
  assert(await picker.evaluate(element => element === document.activeElement), 'Changing the native picker must retain focus')
  for (const groupId of ['reserve', 'imperatorskoe']) {
    await page.keyboard.press('ArrowDown')
    await page.keyboard.press('Escape')
    await settle(page)
    assert(await picker.evaluate(element => element === document.activeElement), 'Native picker keyboard navigation must retain focus')
    // Headless macOS cannot commit its native option popup with synthetic keys.
    // Commit an actual change event while the picker retains keyboard focus.
    await picker.selectOption(groupId)
    await settle(page)
    assert.equal(await picker.inputValue(), groupId)
    assert(await picker.evaluate(element => element === document.activeElement), 'Native picker option changes must retain focus')
  }
  const product = map.locator(`[data-product-id="${initialId}"]`)
  await product.focus()
  await page.keyboard.press('Enter')
  await selection(map, initialId)
  await infoPopup(map).waitFor({ state: 'visible' })
  assert(await map.locator('.plm-detail-heading h3').evaluate(element => element === document.activeElement), 'Selection must focus the detail heading')
  await infoPopup(map).getByRole('button', { name: 'Вернуться к карте', exact: true }).click()
  await infoPopup(map).waitFor({ state: 'hidden' })
  assert(await product.evaluate(element => element === document.activeElement), 'Closing the popup must return focus to the product')
  await infoTrigger(map).focus()
  await page.keyboard.press('Enter')
  await infoPopup(map).waitFor({ state: 'visible' })
  await settle(page)
  assert(await map.locator('.plm-detail-heading h3').evaluate(element => element === document.activeElement), 'Reopening details by keyboard must focus the detail heading')
  await page.keyboard.press('Escape')
  await infoPopup(map).waitFor({ state: 'hidden' })

  // The page scrolls. Expand all keeps the first visible group at the same window position.
  await map.locator('[data-group-container="fizz"]').evaluate(group => window.scrollTo({ top: window.scrollY + group.getBoundingClientRect().top - 16, left: 0, behavior: 'instant' }))
  await settle(page)
  const visibleAnchor = await map.evaluate(root => {
    const groups = [...root.querySelectorAll('[data-group-container]')]
      .map(element => ({ element, rect: element.getBoundingClientRect() }))
      .filter(({ rect }) => rect.bottom > 0 && rect.top < innerHeight)
      .sort((a, b) => a.rect.top - b.rect.top || a.rect.left - b.rect.left)
    const group = groups[0].element
    const heading = group.querySelector('[data-group-id]').getBoundingClientRect()
    return { id: group.dataset.groupContainer, top: heading.top, left: heading.left }
  })
  assert.equal(graph.groups.find(group => group.id === visibleAnchor.id)?.tier_id, 'formats', 'Page scrolling must reach the formats tier')
  // A click would first scroll the button at the top of the map into view. Activate it without a scroll.
  await map.getByRole('button', { name: 'Открыть все', exact: true }).evaluate(button => button.focus({ preventScroll: true }))
  await page.keyboard.press('Enter')
  await settle(page)
  assert.equal(await map.locator('[data-group-id][aria-expanded="true"]').count(), graph.groups.length)
  const afterExpand = await map.evaluate((root, id) => {
    const heading = root.querySelector(`[data-group-id="${id}"]`).getBoundingClientRect()
    return { top: heading.top, left: heading.left }
  }, visibleAnchor.id)
  assert(Math.abs(afterExpand.top - visibleAnchor.top) <= 2, 'Expand all must keep the visible group at its window position')
  assert(Math.abs(afterExpand.left - visibleAnchor.left) <= 2, 'Expand all must keep the visible group at its horizontal position')

  // The first toolbar row sticks to the window top inside the map and stops before the footer.
  const toolbar = map.locator('.plm-toolbar')
  assert(Math.abs(await toolbar.evaluate(element => element.getBoundingClientRect().top)) <= 1, 'The toolbar must stick to the window top while the map scrolls')
  await map.getByRole('combobox', { name: 'Перейти к группе' }).selectOption('reserve')
  await settle(page)
  const jump = await map.evaluate(root => ({ toolbar: root.querySelector('.plm-toolbar').getBoundingClientRect().bottom, group: root.querySelector('[data-group-container="reserve"]').getBoundingClientRect().top }))
  assert(jump.group >= jump.toolbar + 8 && jump.group <= jump.toolbar + 40, `A group jump must land below the sticky toolbar: ${JSON.stringify(jump)}`)
  await page.evaluate(() => window.scrollTo({ top: document.documentElement.scrollHeight, left: 0, behavior: 'instant' }))
  await settle(page)
  const end = await page.evaluate(() => ({ toolbar: document.querySelector('.plm-toolbar').getBoundingClientRect().bottom, footer: document.querySelector('footer')?.getBoundingClientRect().top ?? Infinity }))
  assert(end.toolbar <= end.footer + 1, `The sticky toolbar must not cover the footer: ${JSON.stringify(end)}`)
  await overflowAndImages(page, 'overview-page')

  const assets = await Promise.all(graph.products.map(async product => {
    const response = await context.request.get(`${origin}${product.image.src}`)
    assert.equal(response.status(), 200, `Missing asset ${product.id}`)
    assert.match(response.headers()['content-type'], /^image\/webp/)
    return product.id
  }))
  assert.equal(new Set(assets).size, graph.products.length)
  await context.close()
  checks.push('Page overview, preview/reopen focus, native picker keyboard focus, keyboard selection with popup details, expand-all anchor in the page scroll, sticky toolbar with group jumps below it, all registered Abrau asset responses')
}

async function canvasKeyboardAndPan() {
  const context = await newContext()
  const page = await context.newPage()
  observe(page, 'dialog-keyboard-pan')
  const map = await openDialogMap(page)
  await assertCentered(map, initialId)
  const product = map.locator(`[data-product-id="${initialId}"]`)
  await product.focus()
  await page.keyboard.press('Enter')
  await selection(map, initialId)
  assert(await map.locator('.plm-detail-heading h3').evaluate(element => element === document.activeElement), 'Selection must focus the detail heading')
  await map.getByRole('button', { name: 'Вернуться к карте', exact: true }).click()
  await map.getByRole('button', { name: 'Показать карточку', exact: true }).focus()
  await page.keyboard.press('Enter')
  await settle(page)
  assert(await map.locator('.plm-detail-heading h3').evaluate(element => element === document.activeElement), 'Reopening details by keyboard must focus the detail heading')
  const zoomBeforeKeyboard = Number.parseInt(await map.locator('.plm-zoom').textContent(), 10)
  await map.getByRole('button', { name: 'Увеличить карту', exact: true }).focus()
  await page.keyboard.press('Enter')
  assert.equal(Number.parseInt(await map.locator('.plm-zoom').textContent(), 10), zoomBeforeKeyboard + 10)
  const viewport = map.locator('[data-map-viewport]')
  await viewport.focus()
  const beforeArrow = await viewport.evaluate(element => element.scrollTop)
  await page.keyboard.press('ArrowDown')
  await page.waitForFunction(before => document.querySelector('[data-map-viewport]').scrollTop >= before + 100, beforeArrow)

  await locateButton(map, true).click()
  await assertCentered(map, initialId)
  const dragTarget = map.locator('[data-product-id="victor-dravigny-extra-brut"]')
  await dragTarget.scrollIntoViewIfNeeded()
  const frameBox = await viewport.boundingBox()
  const targetBox = await dragTarget.boundingBox()
  const startX = Math.max(frameBox.x + 10, Math.min(targetBox.x + targetBox.width / 2, frameBox.x + frameBox.width - 10))
  const startY = Math.max(frameBox.y + 20, Math.min(targetBox.y + targetBox.height / 2, frameBox.y + frameBox.height - 20))
  const beforePan = await canvasState(map)
  await page.mouse.move(startX, startY)
  await page.mouse.down()
  await page.mouse.move(startX - 60, startY - 100, { steps: 8 })
  await page.mouse.up()
  const afterPan = await canvasState(map)
  assert(afterPan.top > beforePan.top + 50 || afterPan.left > beforePan.left + 30, 'Mouse drag must pan the map')
  assert.equal(afterPan.selected, initialId, 'Mouse pan over another product must not select it')
  await overflowAndImages(page, 'keyboard-and-pan')

  // Scroll without using the picker. Its last selection must not define the expand-all anchor.
  await viewport.evaluate(frame => {
    const group = frame.querySelector('[data-group-container="fizz"]')
    const frameRect = frame.getBoundingClientRect()
    const groupRect = group.getBoundingClientRect()
    frame.scrollTo({ top: frame.scrollTop + groupRect.top - frameRect.top - 16, left: 0, behavior: 'instant' })
  })
  await settle(page)
  const visibleAnchor = await viewport.evaluate(frame => {
    const bounds = frame.getBoundingClientRect()
    const groups = [...frame.querySelectorAll('[data-group-container]')]
      .map(element => ({ element, rect: element.getBoundingClientRect() }))
      .filter(({ rect }) => rect.bottom > bounds.top && rect.top < bounds.bottom && rect.right > bounds.left && rect.left < bounds.right)
      .sort((a, b) => a.rect.top - b.rect.top || a.rect.left - b.rect.left)
    const group = groups[0].element
    const heading = group.querySelector('[data-group-id]').getBoundingClientRect()
    return { id: group.dataset.groupContainer, top: heading.top - bounds.top, left: heading.left - bounds.left }
  })
  assert.equal(graph.groups.find(group => group.id === visibleAnchor.id)?.tier_id, 'formats', 'Manual pan must reach the formats tier')
  await map.getByRole('button', { name: 'Открыть все', exact: true }).click()
  await settle(page)
  assert.equal(await map.locator('[data-group-id][aria-expanded="true"]').count(), graph.groups.length)
  const afterExpand = await viewport.evaluate((frame, id) => {
    const bounds = frame.getBoundingClientRect()
    const heading = frame.querySelector(`[data-group-id="${id}"]`).getBoundingClientRect()
    return { top: heading.top - bounds.top, left: heading.left - bounds.left }
  }, visibleAnchor.id)
  assert(Math.abs(afterExpand.top - visibleAnchor.top) <= 2, 'Expand all must preserve the visible group vertical position after manual pan')
  assert(Math.abs(afterExpand.left - visibleAnchor.left) <= 2, 'Expand all must preserve the visible group horizontal position after manual pan')

  await context.close()
  checks.push('Dialog canvas: side-card return/reopen focus, keyboard zoom and pan, mouse drag suppression, visible expand-all anchor')
}

const wineFixture = (slug = alias, overrides = {}) => ({
  slug, name: 'Victor Dravigny Brut', producer: 'Абрау-Дюрсо', region: 'Кубань', grapes: ['Пино Блан', 'Рислинг', 'Шардоне'],
  color: 'Белое', category: 'Брют', rating: 0, image: initialProduct.image.src, alcohol: null, servingTemperature: null,
  pairings: [], description: 'Описание вина для проверки перехода из результата распознавания.', source: `https://vino-svoe.ru/wines/${slug}`, ...overrides,
})

async function scannerAndShelf() {
  const context = await newContext()
  const page = await context.newPage()
  observe(page, 'scanner-shelf')
  let fixture = wineFixture()
  let predictionCalls = 0
  let shelfCalls = 0
  await page.route('**/api/config', route => route.fulfill({ json: { apiAvailable: true, predictionMode: 'upstream', shelfAvailable: true } }))
  await page.route('**/api/predict', route => {
    predictionCalls++
    assert.equal(route.request().method(), 'POST')
    assert.match(route.request().headers()['content-type'], /multipart\/form-data/)
    return route.fulfill({ status: 200, headers: { 'X-Prediction-Mode': 'upstream' }, json: { slug: fixture.slug } })
  })
  await page.route('**/api/wines/*', route => route.fulfill({ json: fixture }))
  // Client navigation makes the test-only config fixture independent of server configuration.
  await page.goto(`${origin}/lineup/abrau-durso`, { waitUntil: 'networkidle' })
  await page.getByRole('link', { name: 'К сканеру', exact: true }).click()
  await page.waitForURL(`${origin}/`)
  const upload = page.getByLabel('Выбрать фотографию этикетки', { exact: true })
  await upload.setInputFiles(uploadPath)
  const opener = page.getByRole('button', { name: /Путеводитель по линейке/ })
  await opener.waitFor()
  await opener.click()
  const dialog = page.locator('dialog.product-line-dialog[open]')
  const map = dialog.locator('.product-line-map')
  await selection(map, initialId)
  await assertCentered(map, initialId)
  assert.equal(await map.locator('[data-recognized="true"]').count(), 1)
  assert.equal(await map.locator(`[data-product-id="${initialId}"]`).getAttribute('data-recognized'), 'true')
  await screenshot(page, '1440-light-scanner-recognized', false)
  await page.keyboard.press('Escape')
  await dialog.waitFor({ state: 'detached' })
  await page.setViewportSize({ width: 390, height: 844 })
  await opener.click()
  await selection(map, initialId)
  await assertCentered(map, initialId)
  assert.equal(await infoPopup(map).isVisible(), false, 'Recognized mobile wine must start selected without opening its details')
  assert(await dialog.evaluate(element => element.getBoundingClientRect().width >= innerWidth - 2), 'The mobile map dialog must use the viewport width')
  await screenshot(page, '390-light-scanner-recognized', false)
  await chooseProduct(map, 'victor-dravigny', grayId)
  await overflowAndImages(page, '390-scanner-dialog')
  await screenshot(page, '390-light-scanner-gray-popup', false)
  await closeMobileInfo(map, 'escape')
  assert.equal(await dialog.count(), 1, 'Closing wine information must keep the producer map open')
  for (const method of ['close', 'backdrop', 'return']) {
    await openMobileInfo(map)
    await closeMobileInfo(map, method)
    assert.equal(await dialog.count(), 1, `${method}: closing information must keep the producer map open`)
  }
  await page.keyboard.press('Escape')
  await dialog.waitFor({ state: 'detached' })
  await page.setViewportSize({ width: 1440, height: 1000 })
  await opener.click()
  await selection(map, initialId)
  await chooseProduct(map, 'brut-dor', 'brut-dor-riesling')
  await page.keyboard.press('Escape')
  await dialog.waitFor({ state: 'detached' })
  assert(await opener.evaluate(element => element === document.activeElement), 'Escape must return focus to the opener')
  await opener.click()
  await selection(map, initialId)
  await assertCentered(map, initialId)
  await page.keyboard.press('Escape')
  await dialog.waitFor({ state: 'detached' })

  fixture = wineFixture('other-producer-test', { producer: 'Другой производитель', name: 'Другое вино' })
  await upload.setInputFiles(uploadPath)
  await page.locator('.match-copy h2').filter({ hasText: 'Другое вино' }).waitFor()
  await opener.click()
  assert.equal(await dialog.locator('.product-line-map').count(), 0)
  assert.match(await dialog.locator('.line-unavailable').innerText(), /пока не подготовлена/)
  const previewLink = dialog.getByRole('link', { name: 'Все карты производителей', exact: true })
  assert.equal(await previewLink.getAttribute('href'), '/lineup')
  assert.equal(await previewLink.getAttribute('target'), '_blank', 'The preview link must preserve the scanner tab')
  assert.match(await previewLink.getAttribute('rel'), /noopener/)
  await page.keyboard.press('Escape')
  await dialog.waitFor({ state: 'detached' })

  fixture = wineFixture('abrau-dyurso-unmapped-test', { name: 'Новая позиция Абрау-Дюрсо' })
  await upload.setInputFiles(uploadPath)
  await page.locator('.match-copy h2').filter({ hasText: fixture.name }).waitFor()
  await opener.click()
  await map.locator('[data-product-detail][data-selected-product="unmatched"]').waitFor()
  assert.equal(await map.locator('[data-product-id][data-selected="true"]').count(), 0)
  assert.equal(await map.locator('.plm-detail-badges').count(), 0, 'An unmapped wine must not acquire an invented tier')
  assert.match(await map.locator('.plm-availability').innerText(), /Группа и ценовой уровень не определены/)
  assert.equal(await map.locator('.plm-portal-link').getAttribute('href'), `https://vino-svoe.ru/wines/${fixture.slug}`)
  await page.setViewportSize({ width: 390, height: 844 })
  await settle(page)
  assert.equal(await infoPopup(map).isVisible(), false)
  await openMobileInfo(map)
  assert.equal(await infoPopup(map).getAttribute('data-selected-product'), 'unmatched')
  assert.equal(await infoPopup(map).locator('.plm-detail-badges').count(), 0)
  assert.equal(await infoPopup(map).locator('.plm-portal-link').getAttribute('href'), `https://vino-svoe.ru/wines/${fixture.slug}`)
  await closeMobileInfo(map)
  await page.keyboard.press('Escape')
  await dialog.waitFor({ state: 'detached' })
  assert.equal(predictionCalls, 3)

  const fixtureImages = await page.evaluate(async imagePath => {
    const image = new Image()
    image.src = imagePath
    await image.decode()
    const canvas = document.createElement('canvas')
    canvas.width = 600
    canvas.height = 600
    const context = canvas.getContext('2d')
    context.fillStyle = '#eee8dc'
    context.fillRect(0, 0, 600, 600)
    context.drawImage(image, 240, 60, 120, 480)
    const preview = canvas.toDataURL('image/jpeg')
    canvas.width = 20
    canvas.height = 80
    context.fillStyle = 'white'
    context.fillRect(0, 0, 20, 80)
    return { preview, mask: canvas.toDataURL('image/png') }
  }, initialProduct.image.src)
  await page.route('**/v1/group/match', route => {
    shelfCalls++
    return route.fulfill({ json: {
      pipeline: 'browser-test-fixture', latency_ms: 1, image: { width: 600, height: 600, preview: fixtureImages.preview }, detected_count: 1, truncated: false,
      bottles: [{ id: 'b1', segmentation_score: .99, box: [.4, .1, .6, .9], mask: fixtureImages.mask, match: { rank: 1, slug: alias, score: .99, wine: {
        name: 'Victor Dravigny Brut', page_url: `https://vino-svoe.ru/wines/${alias}`, producer: 'Абрау-Дюрсо', category: 'Игристое вино', region: 'Кубань', color: 'Белое', grapes: 'Пино Блан, Рислинг, Шардоне', sugar: 'Брют', image_url: initialProduct.image.src, qr_urls: [],
      } } }],
    } })
  })
  await page.setViewportSize({ width: 390, height: 844 })
  // The mode switch is a pair of links since the mode pages (/ and /shelf).
  await page.getByRole('link', { name: 'Вся полка', exact: true }).click()
  await page.waitForURL(/\/shelf$/)
  await page.getByLabel('Выбрать фотографию полки', { exact: true }).setInputFiles(uploadPath)
  const bottleOpener = page.getByRole('button', { name: 'Бутылка 1: открыть карточку', exact: true })
  await bottleOpener.click()
  const shelfDialog = page.locator('dialog.shelf-dialog[open]')
  const nestedOpener = shelfDialog.getByRole('button', { name: /Путеводитель по линейке/ })
  await nestedOpener.click()
  await selection(map, initialId)
  await assertCentered(map, initialId)
  assert.equal(await page.locator('dialog[open]').count(), 2)
  await openMobileInfo(map)
  await assertInfoFocusTrap(map)
  assert.equal(await page.locator('dialog[open]').count(), 3, 'Shelf, map, and wine information must form three native dialogs')
  await screenshot(page, '390-light-shelf-info-popup', false)
  await closeMobileInfo(map, 'escape')
  assert.equal(await page.locator('dialog[open]').count(), 2, 'Escape must close only the top wine-information popup')
  assert.equal(await shelfDialog.count(), 1)
  assert.equal(await dialog.count(), 1)
  await page.keyboard.press('Escape')
  await dialog.waitFor({ state: 'detached' })
  assert.equal(await shelfDialog.count(), 1, 'Closing the map must keep the shelf bottle dialog open')
  assert(await nestedOpener.evaluate(element => element === document.activeElement))
  await page.keyboard.press('Escape')
  await shelfDialog.waitFor({ state: 'detached' })
  assert(await bottleOpener.evaluate(element => element === document.activeElement))
  assert.equal(shelfCalls, 1)
  assert.equal(predictionCalls, 3, 'Shelf selection must not call the single-bottle predictor')
  await overflowAndImages(page, 'scanner-and-shelf')
  await context.close()
  checks.push('Scanner fixture recognition, reopen/reset, Escape focus, unsupported producer, unmatched Abrau, mobile parent-map preservation, three nested shelf dialogs without repeat prediction')
}

async function mapLoadRetry() {
  const context = await newContext()
  const page = await context.newPage()
  // The blocked chunk logs an expected console error. Uncaught page errors still fail the suite.
  page.on('pageerror', error => errors.push(`map-load-retry: ${error.message}`))
  const fixture = wineFixture()
  await page.route('**/api/config', route => route.fulfill({ json: { apiAvailable: true, predictionMode: 'upstream', shelfAvailable: true } }))
  await page.route('**/api/predict', route => route.fulfill({ headers: { 'X-Prediction-Mode': 'upstream' }, json: { slug: fixture.slug } }))
  await page.route('**/api/wines/*', route => route.fulfill({ json: fixture }))
  let blocked = true
  let blockedRequests = 0
  let release
  const held = new Promise(resolve => { release = resolve })
  // Only the map chunk holds the last image path of the producer.
  await page.route('**/_nuxt/*.js', async route => {
    const response = await route.fetch()
    const body = await response.text()
    if (body.includes(lastImageSrc)) {
      if (blocked) { blockedRequests++; return route.abort('internetdisconnected') }
      await held
    }
    return route.fulfill({ response, body })
  })
  await page.goto(`${origin}/lineup/abrau-durso`, { waitUntil: 'networkidle' })
  await page.getByRole('link', { name: 'К сканеру', exact: true }).click()
  await page.waitForURL(`${origin}/`)
  await page.getByLabel('Выбрать фотографию этикетки', { exact: true }).setInputFiles(uploadPath)
  const opener = page.getByRole('button', { name: /Путеводитель по линейке/ })
  await opener.waitFor()
  await opener.click()
  const dialog = page.locator('dialog.product-line-dialog[open]')
  const alert = dialog.getByRole('alert')
  await alert.waitFor()
  assert.match(await alert.innerText(), /Не удалось загрузить карту/)
  assert.equal(await dialog.locator('.product-line-map').count(), 0)
  assert(blockedRequests >= 1, 'The map chunk request must be blocked')
  blocked = false
  await dialog.getByRole('button', { name: 'Повторить', exact: true }).click()
  const status = dialog.getByRole('status')
  await status.waitFor()
  assert.match(await status.innerText(), /Загружаем карту линейки/)
  assert.equal(await dialog.getAttribute('aria-busy'), 'true')
  release()
  const map = dialog.locator('.product-line-map')
  await selection(map, initialId)
  await assertCentered(map, initialId)
  assert.equal(await dialog.getAttribute('aria-busy'), 'false')
  assert(await dialog.evaluate(element => element.contains(document.activeElement)), 'Focus must stay inside the dialog after a retry')
  await context.close()
  checks.push('Blocked map chunk: failure alert, announced loading state on retry, retry loads and centers the map, focus stays in the dialog')
}

async function shortHeightAndBoundary() {
  for (const [width, height] of [[844, 390], [667, 375], [700, 740], [701, 740], [767, 740], [768, 740], [800, 650], [1440, 720]]) {
    const context = await newContext(width, height)
    const page = await context.newPage()
    const label = `${width}x${height}`
    observe(page, label)
    const fixture = wineFixture()
    await page.route('**/api/config', route => route.fulfill({ json: { apiAvailable: true, predictionMode: 'upstream', shelfAvailable: true } }))
    await page.route('**/api/predict', route => route.fulfill({ headers: { 'X-Prediction-Mode': 'upstream' }, json: { slug: fixture.slug } }))
    await page.route('**/api/wines/*', route => route.fulfill({ json: fixture }))
    await page.goto(`${origin}/lineup/abrau-durso?wine=${alias}`, { waitUntil: 'networkidle' })
    let map = page.locator('.product-line-map')
    await chooseProduct(map, 'victor-dravigny', initialId)
    await assertControlVisible(map.locator('.plm-portal-link'), `${label} standalone portal action`, false)
    await assertControlVisible(map.getByRole('button', { name: 'Вернуться к карте', exact: true }), `${label} standalone return action`, false)
    await overflowAndImages(page, `${label} standalone`)
    if (width === 800 || (width === 1440 && height === 720)) await giftBoxDetails(page, map, `${label}-standalone`)
    // The standalone page shows details in the popup at every width.
    await closeMobileInfo(map)

    await page.getByRole('link', { name: 'К сканеру', exact: true }).click()
    await page.getByLabel('Выбрать фотографию этикетки', { exact: true }).setInputFiles(uploadPath)
    await page.getByRole('button', { name: /Путеводитель по линейке/ }).click()
    const dialog = page.locator('dialog.product-line-dialog[open]')
    map = dialog.locator('.product-line-map')
    await selection(map, initialId)
    await assertCentered(map, initialId)
    await chooseProduct(map, 'victor-dravigny', initialId)
    if (width < 768) await map.locator('.plm-portal-link').scrollIntoViewIfNeeded()
    await assertControlVisible(map.locator('.plm-portal-link'), `${label} dialog portal action`, width < 768)
    if (width < 768) await map.getByRole('button', { name: 'Вернуться к карте', exact: true }).scrollIntoViewIfNeeded()
    await assertControlVisible(map.getByRole('button', { name: 'Вернуться к карте', exact: true }), `${label} dialog return action`, width < 768)
    await chooseProduct(map, 'victor-dravigny', grayId)
    await assertControlVisible(map.getByRole('button', { name: 'Вернуться к карте', exact: true }), `${label} gray return action`, false)
    await overflowAndImages(page, `${label} dialog`)
    await screenshot(page, `${label}-scanner-gray`, false)
    if (width < 768) await closeMobileInfo(map)
    if (width === 667) {
      await map.getByRole('button', { name: 'Увеличить карту', exact: true }).click()
      await settle(page)
      await map.locator('[data-map-viewport]').evaluate(frame => frame.scrollTop += 25)
      await openMobileInfo(map)
      await closeMobileInfo(map)
      await assertControlVisible(infoTrigger(map), 'Landscape Return must restore the visible popup opener')
      await screenshot(page, `${label}-scanner-return`, false)
    }
    if (width === 800 || (width === 1440 && height === 720)) await giftBoxDetails(page, map, `${label}-scanner`)
    await page.keyboard.press('Escape')
    await dialog.waitFor({ state: 'detached' })
    await context.close()
  }
  checks.push('Landscape 844×390 and 667×375, popup Return scroll/focus, 700/701/767/768px boundaries, 800×650 and 1440×720 gift-box details, reachable actions')
}

async function giftBoxDetails(page, map, label) {
  await chooseProduct(map, 'cuvee-alexander-ii', 'cuvee-alexander-ii-gift-box')
  await settle(page)
  const content = map.locator('.plm-detail-content')
  assert(await content.evaluate(element => element.clientHeight > 0), `${label}: gift-box details must have a nonzero content height`)
  const description = map.locator('.plm-detail-description')
  await description.scrollIntoViewIfNeeded()
  await assertControlVisible(description, `${label}: gift-box description must be readable`)
  const actionsInsidePanel = await map.locator('[data-product-detail]').evaluate(panel => {
    const bounds = panel.getBoundingClientRect()
    return [...panel.querySelectorAll('.plm-detail-actions > *')].every(action => {
      const rect = action.getBoundingClientRect()
      return rect.top >= bounds.top - 2 && rect.bottom <= bounds.bottom + 2 && rect.left >= bounds.left - 2 && rect.right <= bounds.right + 2
    })
  })
  assert(actionsInsidePanel, `${label}: all gift-box actions must remain inside the detail panel`)
  for (const action of [map.locator('.plm-no-link'), map.getByRole('button', { name: 'Вернуться к карте', exact: true })]) {
    await action.scrollIntoViewIfNeeded()
    await assertControlVisible(action, `${label}: gift-box actions must remain reachable by outer scrolling`)
  }
  await overflowAndImages(page, label)
  await screenshot(page, `${label}-gift-box`, false)
}

async function popupBreakpointTransition() {
  const context = await newContext(767, 900)
  const page = await context.newPage()
  observe(page, 'popup-breakpoint-transition')
  // Only the canvas layout of the guide dialog switches between the side card and the popup.
  const map = await openDialogMap(page)
  await selection(map, initialId)
  await assertCentered(map, initialId)
  assert.equal(await infoPopup(map).isVisible(), false)
  await map.getByRole('button', { name: 'Увеличить карту', exact: true }).click()
  await settle(page)
  await openMobileInfo(map)
  const beforeResize = await canvasState(map)
  await page.setViewportSize({ width: 768, height: 900 })
  await map.locator('aside[data-product-detail]').waitFor({ state: 'visible' })
  await settle(page)
  assert.equal(await infoPopup(map).count(), 0, 'Crossing to desktop must remove the mobile native dialog')
  assert.deepEqual(await canvasState(map), beforeResize, 'Desktop transition must retain map selection, zoom, and scroll')
  assert(await page.evaluate(() => !document.querySelector('dialog[data-product-detail]:modal') && !document.querySelector('.plm-mobile-dialog[open]')), 'Desktop transition must close the information popup and release its scroll lock')
  assert(await map.locator('.plm-detail-description').isVisible(), 'Desktop transition must show the selected wine in the side panel')
  await page.setViewportSize({ width: 767, height: 900 })
  await infoPopup(map).waitFor({ state: 'attached' })
  await settle(page)
  assert.equal(await infoPopup(map).isVisible(), false, 'Returning to mobile must not reopen the information popup')
  assert.deepEqual(await canvasState(map), beforeResize, 'Returning to mobile must retain map selection, zoom, and scroll')
  await openMobileInfo(map)
  await closeMobileInfo(map)
  await overflowAndImages(page, 'popup-breakpoint-transition')
  await context.close()
  checks.push('767→768→767 transition: modal closes, desktop details remain, scroll lock releases, selection/zoom/scroll persist')
}

async function popupReadingPosition() {
  const context = await newContext(390, 640)
  const page = await context.newPage()
  observe(page, 'popup-reading-position')
  await page.goto(`${origin}/lineup/abrau-durso?wine=${alias}`, { waitUntil: 'networkidle' })
  const map = page.locator('.product-line-map')
  await openMobileInfo(map)
  const content = infoPopup(map).locator('.plm-detail-scroll')
  await content.evaluate(element => element.scrollTop = element.scrollHeight)
  assert(await content.evaluate(element => element.scrollTop > 0), 'The reading fixture must scroll within the popup')
  await closeMobileInfo(map)
  await openMobileInfo(map)
  assert.equal(await content.evaluate(element => element.scrollTop), 0, 'Reopening wine details must start at its heading')
  await content.evaluate(element => element.scrollTop = element.scrollHeight)
  await closeMobileInfo(map)
  await chooseProduct(map, 'cuvee-alexander-ii', 'cuvee-alexander-ii-gift-box')
  assert.equal(await content.evaluate(element => element.scrollTop), 0, 'Selecting a different wine must reset popup reading position')
  assert.match(await infoPopup(map).locator('.plm-detail-heading h3').innerText(), /подарочная коробка/)
  await closeMobileInfo(map)
  await context.close()
  checks.push('Popup reading position resets after reopening or selecting a different wine without moving the underlying map')
}

async function lineupIndexPage() {
  const index = JSON.parse(await readFile('shared/data/product-line-index.json', 'utf8'))
  for (const [width, height, theme] of [[1440, 1000, 'light'], [390, 844, 'dark'], [320, 740, 'light']]) {
    const context = await newContext(width, height, theme)
    const page = await context.newPage()
    const label = `lineup-index-${width}-${theme}`
    observe(page, label)
    const response = await page.goto(`${origin}/lineup`, { waitUntil: 'networkidle' })
    assert.equal(response.status(), 200)
    assert.equal(response.headers()['x-robots-tag'], undefined, 'The index /lineup must be indexable')
    assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'), 'https://chtozavino.ru/lineup')
    const cards = page.locator('[data-producer-card]')
    assert.equal(await cards.count(), index.producers.length)
    for (const [position, entry] of index.producers.entries()) {
      const card = cards.nth(position)
      assert.equal(await card.getAttribute('href'), `/lineup/${entry.producer.id}`)
      assert((await card.innerText()).includes(entry.producer.name), `${label}: card ${position} must name ${entry.producer.name}`)
    }
    await overflowAndImages(page, label)
    await screenshot(page, label)
    if (width === 1440) {
      for (const entry of index.producers) {
        const cover = await context.request.get(`${origin}${entry.summary.cover.src}`)
        assert.equal(cover.status(), 200, `Missing cover ${entry.producer.id}`)
      }
      await cards.first().click()
      await page.waitForURL(`**/lineup/${index.producers[0].producer.id}`)
      await page.getByRole('link', { name: 'Все карты производителей', exact: true }).click()
      await page.waitForURL(`${origin}/lineup`)
      const map = await context.request.get(`${origin}/lineup/abrau-durso`)
      assert.equal(map.headers()['x-robots-tag'], 'noindex, nofollow, noarchive', 'A producer map must stay noindex')
    }
    await context.close()
  }
  checks.push('Index /lineup: one card per producer with name and link, cover images, canonical URL, no noindex header, no overflow at 1440, 390, and 320 px, card and back-link navigation')
}

try {
  await lineupIndexPage()
  await delayedFontCentering()
  await screenshotsAndResponsiveStates()
  await overviewPage()
  await canvasKeyboardAndPan()
  await scannerAndShelf()
  await mapLoadRetry()
  await shortHeightAndBoundary()
  await popupBreakpointTransition()
  await popupReadingPosition()
  assert.deepEqual(errors, [], 'Browser errors or hydration warnings')
  console.log(`Browser: ${browserName}`)
  console.log(checks.join('\n'))
  console.log(`Screenshots: ${reportDirectory}`)
} finally {
  await browser.close()
}
