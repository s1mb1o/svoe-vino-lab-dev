import assert from 'node:assert/strict'
import { createServer } from 'node:http'

// Playwright is not a project dependency. Point PLAYWRIGHT_MODULE at a local playwright/index.mjs.
const origin = process.env.PORTAL_ORIGIN || 'http://127.0.0.1:8153'
assert(process.env.PLAYWRIGHT_MODULE, 'Set PLAYWRIGHT_MODULE to the index.mjs of a local Playwright package.')
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE)
const heading = 'Найти вино по фото'
const hopHeaders = new Set(['content-encoding', 'content-length', 'transfer-encoding', 'connection'])

// The loopback proxy publishes a changed sw.js, so the update check needs no second build.
let workerSuffix = ''
const proxy = createServer(async (request, response) => {
  if (!['GET', 'HEAD'].includes(request.method || '')) return response.writeHead(405).end()
  try {
    const upstream = await fetch(origin + request.url, { method: request.method, headers: { accept: request.headers.accept || '*/*' }, redirect: 'manual' })
    let body = Buffer.from(await upstream.arrayBuffer())
    if (request.url === '/sw.js' && workerSuffix) body = Buffer.concat([body, Buffer.from(workerSuffix)])
    response.writeHead(upstream.status, Object.fromEntries([...upstream.headers].filter(([name]) => !hopHeaders.has(name))))
    response.end(body)
  } catch (error) {
    response.writeHead(502).end(String(error))
  }
})
await new Promise(resolve => proxy.listen(0, '127.0.0.1', resolve))
const base = `http://127.0.0.1:${proxy.address().port}`
const browser = await chromium.launch({ headless: true })

try {
  const context = await browser.newContext({ serviceWorkers: 'allow' })
  const page = await context.newPage()
  const cacheState = () => page.evaluate(async () => {
    const entries = {}
    for (const name of await caches.keys()) entries[name] = (await (await caches.open(name)).keys()).map(request => new URL(request.url).pathname)
    return entries
  })
  const offlineReload = async () => {
    await context.setOffline(true)
    try {
      const response = await page.reload({ waitUntil: 'load', timeout: 15000 })
      return { status: response?.status(), fromServiceWorker: response?.fromServiceWorker(), heading: (await page.locator('h1').first().textContent())?.trim() }
    } catch (error) {
      return { error: String(error.message).split('\n')[0] }
    } finally {
      await context.setOffline(false)
    }
  }

  await page.goto(base + '/', { waitUntil: 'load' })
  await page.evaluate(() => navigator.serviceWorker.ready)
  const cdp = await context.newCDPSession(page)
  const { installabilityErrors } = await cdp.send('Page.getInstallabilityErrors')
  assert.deepEqual(installabilityErrors, [], 'Chrome reports installability errors.')
  const { errors: manifestErrors } = await cdp.send('Page.getAppManifest')
  assert.deepEqual(manifestErrors, [], 'Chrome reports manifest errors.')
  const firstCaches = await cacheState()
  const precache = Object.entries(firstCaches).find(([name]) => name.includes('precache'))
  assert(precache, 'The Workbox precache is missing.')
  const stored = Object.values(firstCaches).flat()
  assert(!stored.some(path => path.startsWith('/api/') || path.startsWith('/v1/')), 'A cache stores an API route.')
  assert(!stored.some(path => path.startsWith('/screenshots/') || path.includes('shelf-example')), 'A cache stores a large optional image.')

  // Documented limit: the first navigation happens before the worker is active.
  const firstVisitOffline = await offlineReload()

  await page.goto(base + '/', { waitUntil: 'load' })
  await page.waitForFunction(async () => await caches.has('svoe-vino-pages') && (await (await caches.open('svoe-vino-pages')).keys()).length > 0, null, { timeout: 10000 })
  assert.deepEqual((await cacheState())['svoe-vino-pages'], ['/'])
  const secondVisitOffline = await offlineReload()
  assert.equal(secondVisitOffline.status, 200, 'The cached page did not open offline.')
  assert.equal(secondVisitOffline.fromServiceWorker, true)
  assert.equal(secondVisitOffline.heading, heading)
  await context.setOffline(true)
  const apiOffline = await page.evaluate(() => fetch('/api/config').then(response => `HTTP ${response.status}`, error => error.name))
  await context.setOffline(false)
  assert.equal(apiOffline, 'TypeError', 'An API response came from a cache while offline.')

  await page.goto(base + '/', { waitUntil: 'load' })
  await page.evaluate(() => { window.__pwaProbe = 'kept' })
  workerSuffix = `\n// update probe ${Date.now()}\n`
  let update
  try {
    update = await page.evaluate(async () => {
      const registration = await navigator.serviceWorker.getRegistration()
      await registration.update()
      const deadline = Date.now() + 15000
      while (!registration.waiting && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 200))
      return { waiting: Boolean(registration.waiting) }
    })
    await page.waitForTimeout(2000)
    update.pageKept = await page.evaluate(() => window.__pwaProbe === 'kept')
  } catch (error) {
    assert.fail(`The page reloaded after a service-worker update: ${String(error.message).split('\n')[0]}`)
  }
  assert.equal(update.waiting, true, 'The updated service worker did not wait.')
  assert.equal(update.pageKept, true, 'The page reloaded after a service-worker update.')

  console.log(JSON.stringify({ ok: true, origin, precacheEntries: precache[1].length, firstVisitOffline, secondVisitOffline, apiOffline, update }, null, 2))
} finally {
  await browser.close()
  proxy.close()
}
