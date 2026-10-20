import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { readFile, writeFile } from 'node:fs/promises'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE)
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const runtime = JSON.parse(await readFile(process.env.F04_ANDROID_RUNTIME))
const sessions = JSON.parse(await readFile(runtime.sessionsPath))
const base = runtime.base
const port = new URL(base).port
const adb = (...args) => execFileSync('adb', args, { encoding: 'utf8', timeout: 15000 }).trim()
assert(!adb('reverse', '--list').split('\n').some(line => line.split(/\s+/).includes(`tcp:${port}`)), 'The test port already has a device mapping.')
const cdpPort = adb('forward', 'tcp:0', 'localabstract:chrome_devtools_remote')
let browser, page, client, context
let previousCookies = []
let reversed = false
const report = { device: adb('shell', 'getprop', 'ro.product.model'), startedAt: new Date().toISOString(), recognition: runtime.matcher, limitations: ['File bytes enter the real phone browser through the file input. Native camera/gallery selection is not checked.', 'Origin reachability is removed through ADB and browser network emulation. OS airplane mode and TalkBack are not checked.'] }
try {
  adb('reverse', `tcp:${port}`, `tcp:${port}`); reversed = true
  browser = await chromium.connectOverCDP(`http://127.0.0.1:${cdpPort}`, { noDefaults: true })
  context = browser.contexts()[0]
  previousCookies = (await context.cookies(base)).filter(cookie => cookie.name === '__Host-cv_session')
  await context.addCookies([{ name: '__Host-cv_session', value: sessions.b.token, url: base.replace(/^http:/, 'https:'), secure: true, httpOnly: true, sameSite: 'Lax' }])
  page = await context.newPage()
  client = await context.newCDPSession(page)
  // Only this temporary test session trusts the disposable local HTTPS certificate.
  if (base.startsWith('https:')) await client.send('Security.setIgnoreCertificateErrors', { ignore: true })
  await page.route('https://**', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort())
  await page.goto(base, { waitUntil: 'load' })
  const age = page.getByRole('button', { name: 'Да, мне есть 18 лет', exact: true })
  if (await age.count()) await age.click()
  await page.locator('input[aria-label="Выбрать фотографию этикетки"]').waitFor({ state: 'attached' })
  const photo = await readFile(resolve(root, 'public/wines/cantiani-cabernet-sauvignon.webp'))
  await page.evaluate(bytes => {
    const input = document.querySelector('input[aria-label="Выбрать фотографию этикетки"]')
    const transfer = new DataTransfer()
    transfer.items.add(new File([new Uint8Array(bytes)], 'public-catalog-bottle.webp', { type: 'image/webp' }))
    input.files = transfer.files
    input.dispatchEvent(new Event('change', { bubbles: true }))
  }, [...photo])
  await page.getByRole('button', { name: 'Найти альтернативы', exact: true }).click()
  const card = page.locator('.f04-results>li').nth(2)
  await card.waitFor()
  const name = await card.locator('h3').textContent()
  const slug = await card.locator('a').getAttribute('href').then(url => new URL(url).pathname.split('/').pop())
  await card.getByRole('button', { name: 'Сравнить', exact: true }).click()
  await page.locator('.f04-dialog[open]').waitFor()
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1))
  await page.screenshot({ path: resolve(runtime.reportDir, 'pixel8-comparison.png') })
  await page.getByRole('button', { name: 'Закрыть сравнение', exact: true }).click()
  await card.locator('.pin-button').click()
  await card.getByText('Доступно офлайн на этом устройстве.', { exact: true }).waitFor()
  const saved = await page.evaluate(() => fetch('/api/account/saved', { cache: 'no-store' }).then(r => r.json()))
  assert(saved.items.some(item => item.slug === slug))
  await page.evaluate(() => Promise.race([navigator.serviceWorker.ready, new Promise((_, reject) => setTimeout(() => reject(new Error('Service worker did not register in the secure test context')), 10000))]))
  await page.reload({ waitUntil: 'load' })
  await page.locator('.f04-local-list').getByRole('button', { name, exact: true }).waitFor()
  await page.reload({ waitUntil: 'load' })
  await page.locator('.f04-local-list').getByRole('button', { name, exact: true }).waitFor()
  report.viewport = await page.evaluate(() => ({ width: innerWidth, height: innerHeight, devicePixelRatio, theme: document.documentElement.dataset.theme }))
  // Remove only this test origin's reverse mapping. Other phone traffic stays available.
  adb('reverse', '--remove', `tcp:${port}`); reversed = false
  await client.send('Network.enable')
  await client.send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0 })
  await page.reload({ waitUntil: 'load' })
  await page.locator('.f04-local-list').getByRole('button', { name, exact: true }).click()
  await page.locator('.f04-stored-card').waitFor()
  assert((await page.locator('.f04-stored-card').textContent()).includes(name))
  await page.screenshot({ path: resolve(runtime.reportDir, 'pixel8-offline.png'), fullPage: true })
  report.status = 'PASS'
  report.exactCandidate = slug
  report.checks = { actualPhoneRenderer: true, alternatives: true, comparison: true, mainDiarySave: true, reload: true, offlineOriginUnreachable: true, offlineCardOpened: true, noHorizontalOverflow: true }
} catch (error) {
  report.status = 'FAIL'; report.error = error.stack
  if (page) await page.screenshot({ path: resolve(runtime.reportDir, 'pixel8-failure.png') }).catch(() => {})
  throw error
} finally {
  report.finishedAt = new Date().toISOString()
  await writeFile(resolve(runtime.reportDir, 'pixel8-report.json'), JSON.stringify(report, null, 2) + '\n')
  if (client) {
    await client.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }).catch(() => {})
    await client.send('Storage.clearDataForOrigin', { origin: base, storageTypes: 'indexeddb,local_storage,service_workers,cache_storage' }).catch(() => {})
    if (base.startsWith('https:')) await client.send('Security.setIgnoreCertificateErrors', { ignore: false }).catch(() => {})
  }
  await page?.close().catch(() => {})
  if (context) {
    await context.clearCookies({ name: '__Host-cv_session', domain: new URL(base).hostname })
    if (previousCookies.length) await context.addCookies(previousCookies.map(({ domain, path, ...cookie }) => ({ ...cookie, url: base.replace(/^http:/, 'https:') })))
  }
  // connectOverCDP.close disconnects this transport. It does not stop the phone Chrome process.
  await browser?.close()
  if (reversed) adb('reverse', '--remove', `tcp:${port}`)
  adb('forward', '--remove', `tcp:${cdpPort}`)
}
