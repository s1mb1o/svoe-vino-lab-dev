import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { existsSync } from 'node:fs'
import { mkdir, readFile } from 'node:fs/promises'

assert(process.env.PLAYWRIGHT_MODULE, 'Set PLAYWRIGHT_MODULE to a local playwright/index.mjs.')
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE)
const origin = process.env.PORTAL_ORIGIN || 'http://127.0.0.1:8153'
const browser = await chromium.launch({ headless: true })
const errors = []
const digest = buffer => createHash('sha256').update(buffer).digest('hex')
await mkdir('reports/presentation', { recursive: true })

try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: 'dark', serviceWorkers: 'block' })
  const page = await context.newPage()
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => {
    if (message.type() === 'error' && message.location().url === `${origin}/presentation/video.mp4` && message.text().includes('404')) return
    if (message.type() === 'error' || /hydration/i.test(message.text())) errors.push(message.text())
  })
  await page.goto(`${origin}/presentation`, { waitUntil: 'networkidle' })
  assert(await page.getByRole('dialog').isVisible())
  assert(await page.locator('.site-shell').evaluate(element => element.inert))
  await page.getByRole('button', { name: 'Да, мне есть 18 лет', exact: true }).click()
  await page.getByRole('dialog').waitFor({ state: 'detached' })
  await page.evaluate(() => document.fonts.ready)
  assert.equal(await page.locator('h1').count(), 1)
  assert.equal(await page.locator('.site-header, .site-footer').count(), 0)
  assert.equal(await page.locator('link[rel="canonical"]').count(), 1)
  assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'), 'https://chtozavino.ru/presentation')

  const links = page.locator('.presentation-links a')
  assert.equal(await links.count(), 2)
  assert.equal(await links.nth(0).getAttribute('href'), '/presentations/chtozavino-presentation.pptx')
  assert.equal(await links.nth(0).getAttribute('download'), 'chtozavino-presentation.pptx')
  assert.equal(await links.nth(1).getAttribute('href'), '/presentations/chtozavino-presentation.pdf')
  assert.equal(await links.nth(1).getAttribute('target'), '_blank')
  const video = page.locator('.presentation-video video')
  assert.equal(await video.getAttribute('src'), '/presentation/video.mp4')
  if (!existsSync('public/presentation/video.mp4')) await page.getByRole('status').filter({ hasText: 'Видео появится после записи' }).waitFor()

  for (const theme of ['light', 'dark']) {
    await page.evaluate(value => localStorage.setItem('svoe-vino.theme.v1', value), theme)
    await page.reload({ waitUntil: 'networkidle' })
    for (const [width, height] of [[1440, 900], [768, 1024], [390, 844], [320, 740]]) {
      await page.setViewportSize({ width, height })
      const boxes = await links.evaluateAll(elements => elements.map(element => {
        const box = element.getBoundingClientRect()
        return { x: box.x, y: box.y, width: box.width, height: box.height }
      }))
      assert(Math.abs(boxes[0].y - boxes[1].y) < 1, `Links must stay side by side at ${width}px`)
      assert(boxes[0].x + boxes[0].width < boxes[1].x)
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Overflow at ${width}px`)
      assert.equal(await page.locator('.presentation-page').evaluate(element => getComputedStyle(element).backgroundColor), 'rgb(255, 255, 255)')
      if (theme === 'light' && [1440, 320].includes(width)) await page.screenshot({ path: `reports/presentation/${width}-files.png`, fullPage: true })
    }
  }

  for (const [extension, contentType, signature] of [
    ['pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'PK'],
    ['pdf', 'application/pdf', '%PDF-'],
  ]) {
    const filename = `chtozavino-presentation.${extension}`
    const localFile = await readFile(`public/presentations/${filename}`)
    const response = await context.request.get(`${origin}/presentations/${filename}`)
    assert.equal(response.status(), 200)
    assert(response.headers()['content-type'].startsWith(contentType))
    const body = await response.body()
    assert.equal(body.subarray(0, signature.length).toString(), signature)
    assert.equal(digest(body), digest(localFile), `File bytes differ: ${filename}`)
  }
  const downloadPromise = page.waitForEvent('download')
  await links.nth(0).click()
  const download = await downloadPromise
  assert.equal(download.suggestedFilename(), 'chtozavino-presentation.pptx')
  assert.equal(await download.failure(), null)

  await page.locator('.presentation-brand').click()
  await page.waitForURL(`${origin}/`)
  assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark')
  await page.goto(`${origin}/presentation`, { waitUntil: 'networkidle' })
  await page.waitForURL(`${origin}/presentation`)
  assert.equal(await links.count(), 2)
  assert.deepEqual(errors, [], 'Browser errors or hydration warnings')
  console.log('Age gate, adjacent links at four widths in both themes, file bytes, download, metadata, and navigation passed.')
} finally { await browser.close() }
