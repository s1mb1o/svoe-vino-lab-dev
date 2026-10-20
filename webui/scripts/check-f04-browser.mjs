import assert from 'node:assert/strict'
import { createServer, request as httpRequest } from 'node:http'
import { createServer as createHttpsServer } from 'node:https'
import { Agent } from 'undici'
import { spawn, spawnSync } from 'node:child_process'
import { readFile, writeFile, mkdir, mkdtemp } from 'node:fs/promises'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { build } from 'esbuild'

assert(process.env.PLAYWRIGHT_MODULE, 'Set PLAYWRIGHT_MODULE to a local Playwright index.mjs.')
assert(process.env.F04_PYTHON, 'Set F04_PYTHON to Python with the local account package installed.')
const { chromium, webkit } = await import(process.env.PLAYWRIGHT_MODULE)
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const dir = resolve(process.env.F04_REPORT_DIR || 'reports/f04')
await mkdir(dir, { recursive: true })
const data = JSON.parse(await readFile(resolve(root, 'server/data/alternative-catalog.json')))
const fixtureSlug = 'cantiani-cabernet-sauvignon'
const fixtureWine = data.wines.find(wine => wine.slug === fixtureSlug)
const photo = await readFile(resolve(root, `public/wines/${fixtureSlug}.webp`))
const children = []
let observedPhotoRequests = 0
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))
async function until(fn, label) {
  let error
  for (let i = 0; i < 150; i++) { try { const result = await fn(); if (result) return result } catch (e) { error = e }; await sleep(100) }
  throw new Error(`Timed out: ${label}. ${error?.message || ''}`)
}
const listen = server => new Promise(resolve => server.listen(0, '127.0.0.1', () => resolve(server.address().port)))
const reserve = createServer()
const port = await listen(reserve)
await new Promise(resolve => reserve.close(resolve))
const previewOrigin = `http://127.0.0.1:${port}`
const tlsDir = await mkdtemp(resolve(dir, 'private-tls-'))
const cert = resolve(tlsDir, 'cert.pem'), key = resolve(tlsDir, 'key.pem')
assert.equal(spawnSync('openssl', ['req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-subj', '/CN=localhost', '-addext', 'subjectAltName=IP:127.0.0.1,DNS:localhost', '-days', '1', '-keyout', key, '-out', cert], { stdio: 'ignore' }).status, 0)
const tlsProxy = createHttpsServer({ key: await readFile(key), cert: await readFile(cert) }, (req, res) => {
  if (req.url === '/api/predict' && req.method === 'POST') observedPhotoRequests++
  const upstream = httpRequest(previewOrigin + req.url, { method: req.method, headers: { ...req.headers, 'x-forwarded-proto': 'https' } }, answer => { res.writeHead(answer.statusCode, answer.headers); answer.pipe(res) })
  upstream.on('error', () => { if (!res.headersSent) res.writeHead(502); res.end() })
  req.pipe(upstream)
})
const tlsPort = await listen(tlsProxy)
const base = `https://127.0.0.1:${tlsPort}`
// Trust only this local self-signed test origin. Production TLS is unchanged.
const localTls = new Agent({ connect: { rejectUnauthorized: false } })
const fetch = (url, options = {}) => globalThis.fetch(url, { ...options, ...(String(url).startsWith(base + '/') ? { dispatcher: localTls } : {}) })
let predictions = 0
const matcher = createServer((req, res) => {
  req.resume()
  if (req.url === '/healthz') { res.writeHead(200, { 'content-type': 'application/json' }); return res.end('{"status":"ok"}') }
  if (req.url === '/v1/eval/predict' && req.method === 'POST') { predictions++; res.writeHead(200, { 'content-type': 'application/json' }); return res.end(JSON.stringify({ slug: fixtureSlug })) }
  res.writeHead(404).end()
})
const matcherPort = await listen(matcher)
const matcherEndpoint = process.env.F04_MATCHER_ENDPOINT || `http://127.0.0.1:${matcherPort}/v1/eval/predict`
const accountDir = await mkdtemp(resolve(dir, 'private-account-'))
const account = spawn(process.env.F04_PYTHON, [resolve(root, 'scripts/f04-account-harness.py'), accountDir], { stdio: ['ignore', 'ignore', 'pipe'] })
children.push(account)
let accountError = ''
account.stderr.on('data', chunk => { accountError += chunk.toString() })
const report = { startedAt: new Date().toISOString(), base, catalogVersion: data.version, account: 'Real account service, isolated SQLite, memory mail sink, test-code override disabled', recognition: process.env.F04_MATCHER_ENDPOINT ? 'Configured actual matcher' : 'Deterministic upstream fixture; no recognition quality claim', checks: {}, limitations: ['Browser automation is not physical-phone or screen-reader acceptance.', 'Memory mail does not establish SMTP delivery or ownership of a real email address.'] }
let browser
try {
  const accountPort = await until(async () => JSON.parse(await readFile(resolve(accountDir, 'account-port.json'))).port, 'account port')
  await until(async () => (await fetch(`http://127.0.0.1:${accountPort}/healthz`)).ok, `account health: ${accountError}`)
  const sessions = JSON.parse(await readFile(resolve(accountDir, 'sessions.json')))
  const preview = spawn(process.execPath, ['.output/server/index.mjs'], { cwd: root, env: { ...process.env, HOST: '127.0.0.1', PORT: String(port), NUXT_PREDICTION_MODE: 'upstream', NUXT_PREDICTION_ENDPOINT: matcherEndpoint, NUXT_ACCOUNT_ENDPOINT: `http://127.0.0.1:${accountPort}`, ACCOUNT_WEB_TOKEN: 'f04-local-web-' + 'w'.repeat(40), NUXT_ACCOUNT_PUBLIC_ORIGIN: base }, stdio: 'ignore' })
  children.push(preview)
  await until(async () => (await fetch(base + '/api/health')).ok, 'portal health')
  await writeFile(resolve(dir, 'runtime.json'), JSON.stringify({ base, accountPort, matcher: process.env.F04_MATCHER_ENDPOINT ? 'actual configured matcher' : 'local deterministic fixture', previewPid: preview.pid, accountPid: account.pid }))

  // Independent upload contract. No official evaluation files are opened.
  const form = new FormData(); form.set('image', new Blob([photo], { type: 'image/webp' }), 'public-catalog-bottle.webp')
  const success = await fetch(base + '/v1/eval/predict', { method: 'POST', body: form })
  assert.equal(success.status, 200)
  const prediction = await success.json()
  assert.equal(typeof prediction.slug, 'string')
  if (!process.env.F04_MATCHER_ENDPOINT) assert.deepEqual(prediction, { slug: fixtureSlug })
  assert.equal((await fetch(base + '/v1/eval/predict', { method: 'POST', body: new FormData() })).status, 400)
  assert.equal((await fetch(base + '/api/recommendations/alternatives?slug=../account')).status, 400)
  assert.equal((await fetch(base + '/api/recommendations/alternatives?slug=missing-public-wine')).status, 404)
  assert.equal((await fetch(base + `/api/recommendations/alternatives?slug=${fixtureSlug}&color=unknown`)).status, 400)
  report.checks.independentUploadContract = { exactSlugResponse: true, emptyUpload: 400, badFilter: 400, unknownWine: 404, returnedSlug: prediction.slug }
  const publicCardUrl = base + `/api/wines/${fixtureSlug}/offline`
  const publicCardResponse = await fetch(publicCardUrl)
  assert.equal(publicCardResponse.status, 200)
  assert.equal(publicCardResponse.headers.get('cache-control'), 'no-store')
  const publicCard = await publicCardResponse.json()
  assert.equal(publicCard.wine.slug, fixtureSlug)
  assert.equal(publicCard.version, data.version)
  assert.equal(publicCard.wine.image, '')
  assert(!('producerId' in publicCard.wine) && !('canonicalId' in publicCard.wine))
  assert.equal((await fetch(base + '/api/wines/missing-public-wine/offline')).status, 404)
  assert.equal((await fetch(base + '/api/wines/invalid%20id/offline')).status, 400)
  report.checks.publicCardLookup = { exactID: true, pinnedVersion: true, publicFieldsOnly: true, unknownWine: 404, invalidWine: 400 }

  const anchors = JSON.parse(await readFile(resolve(root, 'tests/data/f04-anchors-v2.json')))
  const outcomes = []
  for (const anchor of anchors.anchors) {
    const response = await fetch(base + '/api/recommendations/alternatives?' + new URLSearchParams({ slug: anchor.slug }))
    assert.equal(response.status, anchor.expectedStatus)
    if (response.status === 404) {
      outcomes.push({ slug: anchor.slug, count: 0, candidates: [], explanation: 'Retired exact ID; excluded from the current snapshot.' })
      continue
    }
    const answer = await response.json()
    assert.equal(answer.version, anchors.version)
    const canonical = new Set([answer.base.canonicalId])
    for (const { wine } of answer.results) {
      assert(wine.producerId && wine.producerId !== answer.base.producerId)
      assert(!canonical.has(wine.canonicalId)); canonical.add(wine.canonicalId)
      assert.equal(wine.color, anchor.color); assert.equal(wine.sweetness, anchor.sweetness)
      assert(data.wines.some(accepted => accepted.slug === wine.slug))
    }
    outcomes.push({ slug: anchor.slug, count: answer.results.length, candidates: answer.results.map(row => row.wine.slug), explanation: answer.explanation })
  }
  const withAlternatives = outcomes.filter(row => row.count > 0).length
  assert(withAlternatives >= 12)
  await writeFile(resolve(dir, 'anchor-results.json'), JSON.stringify({ selection: anchors.selection, version: data.version, withAlternatives, outcomes }, null, 2))
  report.checks.anchors = { reviewed: 20, withAlternatives, producerLeaks: 0, duplicateAliases: 0, hardFilterViolations: 0 }

  browser = await chromium.launch({ headless: true, args: ['--ignore-certificate-errors'] })
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: 'allow', ignoreHTTPSErrors: true })
  await context.addCookies([{ name: '__Host-cv_session', value: sessions.a.token, url: base, secure: true, httpOnly: true, sameSite: 'Lax' }])
  await context.addInitScript(() => localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes'))
  await context.route('https://**', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort())
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(base, { waitUntil: 'networkidle' })
  await page.locator('input[aria-label="Выбрать фотографию этикетки"]').setInputFiles({ name: 'public-catalog-bottle.webp', mimeType: 'image/webp', buffer: photo })
  // Save the original before opening alternatives. Lookup failure preserves the diary save.
  const originalPin = page.locator('.match-panel .pin')
  const originalHistory = await until(async () => {
    const history = await context.request.get(base + '/api/account/history').then(r => r.json())
    return history.items.some(item => item.slug === fixtureSlug) ? history : null
  }, 'Original recognition history')
  const recognitionRows = history => history.items.map(({ savedStatus: _savedStatus, ...row }) => row)
  const directRequests = observedPhotoRequests
  await page.route(publicCardUrl, route => route.fulfill({ status: 404, json: { statusMessage: 'Outside snapshot' } }))
  await originalPin.locator('.pin-button').click()
  await originalPin.getByText('Сохранено в дневнике. Копия для офлайн-открытия недоступна.', { exact: true }).waitFor()
  const originalSaved = await context.request.get(base + '/api/account/saved').then(r => r.json())
  assert.equal(originalSaved.items.filter(item => item.slug === fixtureSlug).length, 1)
  assert.equal(await page.locator('.f04-local-list li').count(), 0)
  await page.unroute(publicCardUrl)
  let heldPublicCard
  await page.route(publicCardUrl, route => { heldPublicCard = route })
  await originalPin.getByRole('button', { name: 'Сохранить копию на устройстве', exact: true }).click()
  await until(() => heldPublicCard, 'Held public card lookup')
  await until(() => originalPin.getByRole('button', { name: 'Сохранить копию на устройстве', exact: true }).isEnabled(), 'Public card lookup timeout')
  assert.equal(await originalPin.getByText('Доступно офлайн на этом устройстве.', { exact: true }).count(), 0)
  await heldPublicCard.abort().catch(() => {})
  await page.unroute(publicCardUrl)
  await originalPin.getByRole('button', { name: 'Сохранить копию на устройстве', exact: true }).click()
  await originalPin.getByText('Доступно офлайн на этом устройстве.', { exact: true }).waitFor()
  assert.equal(await page.locator('.f04-results>li').count(), 0)
  assert.equal(observedPhotoRequests, directRequests)
  assert.deepEqual(recognitionRows(await context.request.get(base + '/api/account/history').then(r => r.json())), recognitionRows(originalHistory))
  await page.evaluate(() => navigator.serviceWorker.ready)
  await page.reload({ waitUntil: 'networkidle' })
  await context.setOffline(true)
  await page.reload({ waitUntil: 'load' })
  await page.locator('.f04-local-list').getByRole('button', { name: fixtureWine.name, exact: true }).click()
  await page.locator('.f04-stored-card').waitFor()
  assert((await page.locator('.f04-stored-card').textContent()).includes(data.version))
  await page.screenshot({ path: resolve(dir, 'original-save-offline-mobile.png'), fullPage: true })
  assert.equal(observedPhotoRequests, directRequests)
  await context.setOffline(false)
  await page.reload({ waitUntil: 'networkidle' })
  // An existing saved wine can get a new device copy even when result metadata fails.
  await page.locator('.f04-local-list').getByRole('button', { name: 'Удалить копию: ' + fixtureWine.name, exact: true }).click()
  await page.route(base + `/api/wines/${fixtureSlug}`, route => route.fulfill({ status: 503, json: { statusMessage: 'Metadata unavailable' } }))
  await page.locator('input[aria-label="Выбрать фотографию этикетки"]').setInputFiles({ name: 'public-catalog-bottle.webp', mimeType: 'image/webp', buffer: photo })
  await page.locator('.missing-result').waitFor()
  await originalPin.locator('.pin-button').click()
  await originalPin.getByRole('button', { name: 'Сохранить копию на устройстве', exact: true }).click()
  await originalPin.getByText('Доступно офлайн на этом устройстве.', { exact: true }).waitFor()
  assert.equal((await context.request.get(base + '/api/account/saved').then(r => r.json())).items.filter(item => item.slug === fixtureSlug).length, 1)
  await originalPin.getByRole('button', { name: 'Убрать из сохранённых', exact: true }).click()
  await page.unroute(base + `/api/wines/${fixtureSlug}`)
  report.checks.originalSaveOffline = { beforeAlternatives: true, exactID: true, lookupFailurePreservesSave: true, boundedTimeout: true, explicitRetry: true, offlineReload: true, unchangedHistory: true, noRepeatRecognition: true, existingSavedCopy: true, unavailableResultMetadata: true }

  // Account reset during the new lookup cannot transfer A's pending copy to B.
  const snapshotRace = await browser.newContext({ serviceWorkers: 'block', ignoreHTTPSErrors: true })
  await snapshotRace.addCookies([{ name: '__Host-cv_session', value: sessions.a.token, url: base, secure: true, httpOnly: true, sameSite: 'Lax' }])
  await snapshotRace.addInitScript(() => localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes'))
  await snapshotRace.route('https://**', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort())
  const snapshotPage = await snapshotRace.newPage()
  await snapshotPage.goto(base, { waitUntil: 'networkidle' })
  await snapshotPage.locator('input[aria-label="Выбрать фотографию этикетки"]').setInputFiles({ name: 'public.webp', mimeType: 'image/webp', buffer: photo })
  let releaseSnapshot
  let finishSnapshot
  const snapshotFinished = new Promise(resolve => { finishSnapshot = resolve })
  await snapshotPage.route(publicCardUrl, route => { releaseSnapshot = async () => { await route.fulfill({ json: publicCard }); finishSnapshot() } })
  await snapshotPage.locator('.match-panel .pin-button').click()
  await until(() => releaseSnapshot, 'Held original public card')
  await snapshotRace.addCookies([{ name: '__Host-cv_session', value: sessions.b.token, url: base, secure: true, httpOnly: true, sameSite: 'Lax' }])
  await snapshotPage.getByRole('link', { name: 'Винный дневник', exact: true }).click()
  await snapshotPage.getByText('f04_b', { exact: true }).waitFor()
  await releaseSnapshot(); await snapshotFinished
  await snapshotPage.getByRole('link', { name: 'Что за вино? — поиск по фото', exact: true }).click()
  await snapshotPage.waitForLoadState('networkidle')
  assert.equal(await snapshotPage.locator('.f04-local-list li').count(), 0)
  assert.equal((await snapshotRace.request.get(base + '/api/account/saved').then(r => r.json())).items.length, 0)
  await context.request.delete(base + `/api/account/saved/${fixtureSlug}`, { headers: { Origin: base } })
  await snapshotRace.close()
  report.checks.publicCardLookupAccountSwitch = true

  await page.getByRole('button', { name: 'Найти альтернативы', exact: true }).click()
  await page.locator('.f04-results>li').first().waitFor()
  await page.route('**/api/recommendations/alternatives?*', route => route.fulfill({ status: 404, json: { statusMessage: 'Outside snapshot' } }))
  await page.getByRole('button', { name: 'Повторить подбор', exact: true }).click()
  await page.getByText('Этого точного вина нет в проверенном снимке каталога. Подбор альтернатив для него пока недоступен.', { exact: true }).waitFor()
  await page.unroute('**/api/recommendations/alternatives?*')
  await page.getByRole('button', { name: 'Повторить подбор', exact: true }).click()
  const first = page.locator('.f04-results>li').first()
  await first.waitFor()
  report.checks.outsideSnapshotIsExplicit = true

  // A failed or superseded lookup must leave the recognized result intact.
  const requestsBeforeFaults = observedPhotoRequests
  await page.route('**/api/recommendations/alternatives?*', route => route.fulfill({ status: 503, json: { statusMessage: 'Temporary fault' } }))
  await page.getByRole('button', { name: 'Повторить подбор', exact: true }).click()
  await page.getByText('Подбор временно недоступен. Исходное вино сохранено на экране. Попробуйте ещё раз.', { exact: true }).waitFor()
  await page.unroute('**/api/recommendations/alternatives?*')
  let heldTimeout
  await page.route('**/api/recommendations/alternatives?*', route => { heldTimeout = route })
  await page.getByRole('button', { name: 'Повторить подбор', exact: true }).click()
  await page.getByText('Подбор временно недоступен. Исходное вино сохранено на экране. Попробуйте ещё раз.', { exact: true }).waitFor({ timeout: 12000 })
  await heldTimeout.abort().catch(() => {})
  await page.unroute('**/api/recommendations/alternatives?*')
  let heldOld
  const white = await fetch(base + '/api/recommendations/alternatives?' + new URLSearchParams({ slug: fixtureSlug, color: 'Белое' })).then(r => r.json())
  await page.route('**/api/recommendations/alternatives?*', route => {
    if (new URL(route.request().url()).searchParams.get('color') === 'Белое') heldOld = route
    else return route.continue()
  })
  const colorSelect = page.locator('.f04-filters select').nth(0)
  await colorSelect.selectOption('Белое')
  await until(() => heldOld, 'held old filter response')
  await colorSelect.selectOption('Красное')
  await first.waitFor()
  const latest = await first.locator('a').getAttribute('href')
  await heldOld.fulfill({ json: white }).catch(() => {})
  await page.waitForTimeout(100)
  assert.equal(await first.locator('a').getAttribute('href'), latest)
  assert.equal(await colorSelect.inputValue(), 'Красное')
  assert.equal(observedPhotoRequests, requestsBeforeFaults, 'Alternative fault or filter change repeated recognition')
  await page.unroute('**/api/recommendations/alternatives?*')
  report.checks.alternativeFailureAndStaleResponse = { serviceFailure: true, realTimeout: true, supersededFilter: true, noExtraRecognition: true }
  const name = await first.locator('h3').textContent()
  const candidateSlug = await first.locator('a').getAttribute('href').then(url => decodeURIComponent(new URL(url).pathname.split('/').pop()))
  const countBefore = observedPhotoRequests
  await first.getByRole('button', { name: 'Сравнить', exact: true }).click()
  const dialog = page.locator('.f04-dialog[open]')
  await dialog.waitFor()
  assert.equal(await dialog.locator('.f04-facts>div').count(), 8)
  assert((await dialog.textContent()).includes('Нет данных'))
  for (const theme of ['light', 'dark']) {
    await page.emulateMedia({ colorScheme: theme })
    await until(async () => await page.locator('html').getAttribute('data-theme') === theme, `System ${theme} theme`)
    for (const width of [320, 390, 1280]) {
      await page.setViewportSize({ width, height: 844 })
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Horizontal page overflow')
      assert(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth + 1), 'Horizontal comparison overflow')
    }
    await page.setViewportSize({ width: 390, height: 844 })
    await page.screenshot({ path: resolve(dir, `comparison-${theme}-mobile.png`), fullPage: true })
  }
  await page.goBack()
  await until(async () => !(await page.locator('.f04-dialog[open]').count()), 'Back closes comparison')
  await first.getByRole('button', { name: 'Сравнить', exact: true }).click()
  await page.getByRole('button', { name: 'Закрыть сравнение', exact: true }).click()
  await until(() => first.getByRole('button', { name: 'Сравнить', exact: true }).evaluate(el => document.activeElement === el), 'comparison focus return')
  for (const [status, error, text] of [[503, 'account_unavailable', 'Не удалось сохранить'], [409, 'saved_full', 'В сохранённых уже 500 вин']]) {
    await page.route(`**/api/account/saved/${candidateSlug}`, route => route.fulfill({ status, json: { error } }))
    await first.locator('.pin-button').click()
    await first.locator('.pin-error').filter({ hasText: text }).waitFor()
    assert(await first.locator('.pin-panel').evaluate(el => { const box = el.getBoundingClientRect(); return box.left >= 0 && box.right <= innerWidth }), 'Save panel leaves viewport')
    const unchanged = await context.request.get(base + '/api/account/saved').then(r => r.json())
    assert.equal(unchanged.items.length, 0)
    await first.locator('.pin-button').click()
    await page.unroute(`**/api/account/saved/${candidateSlug}`)
  }
  report.checks.failedAndFullSaveHonest = true
  await first.locator('.pin-button').click()
  await first.getByText('Доступно офлайн на этом устройстве.', { exact: true }).waitFor()
  assert.equal(observedPhotoRequests, countBefore, 'Comparison and save must not repeat recognition')
  const realSaved = await context.request.get(base + '/api/account/saved').then(r => r.json())
  assert(realSaved.items.some(item => item.slug === candidateSlug))
  assert.equal(realSaved.items.filter(item => item.slug === candidateSlug).length, 1)
  assert.equal(realSaved.items.find(item => item.slug === candidateSlug).wine.sugar, 'Сухое')
  const history = await context.request.get(base + '/api/account/history').then(r => r.json())
  assert(history.items.some(item => item.slug === prediction.slug))
  assert(!history.items.some(item => item.slug === candidateSlug))
  await page.reload({ waitUntil: 'networkidle' })
  await page.locator('.f04-local-list').getByRole('button', { name, exact: true }).click()
  assert((await page.locator('.f04-stored-card').textContent()).includes(name))
  // Actual private note and status persistence use the existing account API and SQLite.
  const status = await context.request.put(base + `/api/account/saved/${candidateSlug}`, { headers: { Origin: base }, data: { source: 'photo', status: 'liked', change: true, note: 'F04 private note; MUST NOT enter offline storage' } })
  assert.equal(status.status(), 200)
  const loaded = await context.request.get(base + '/api/account/saved').then(r => r.json())
  assert.equal(loaded.items.find(item => item.slug === candidateSlug).note, 'F04 private note; MUST NOT enter offline storage')
  assert.equal(loaded.items.find(item => item.slug === candidateSlug).status, 'liked')
  await page.goto(base + '/account', { waitUntil: 'networkidle' })
  assert.equal(await page.locator(`#saved-note-${candidateSlug}`).inputValue(), 'F04 private note; MUST NOT enter offline storage')
  assert.equal(await page.locator(`#saved-status-${candidateSlug}`).inputValue(), 'liked')
  await page.goto(base, { waitUntil: 'networkidle' })
  await page.evaluate(() => navigator.serviceWorker.ready)
  await page.reload({ waitUntil: 'networkidle' })
  await context.setOffline(true)
  await page.reload({ waitUntil: 'load' })
  await page.locator('.f04-local-list').getByRole('button', { name, exact: true }).click()
  await page.locator('.f04-stored-card').waitFor()
  assert((await page.locator('.f04-stored-card').textContent()).includes('Нет сети'))
  const privateCache = await page.evaluate(async () => {
    const paths = []
    for (const key of await caches.keys()) for (const request of await (await caches.open(key)).keys()) paths.push(new URL(request.url).pathname)
    const request = indexedDB.open('chtozavino-offline-cards-v1', 1)
    const rows = await new Promise((resolve, reject) => { request.onsuccess = () => { const db = request.result, tx = db.transaction('cards'); const read = tx.objectStore('cards').getAll(); tx.oncomplete = () => { resolve(read.result); db.close() }; tx.onerror = () => reject(tx.error) }; request.onerror = () => reject(request.error) })
    return { paths, rows }
  })
  assert(!privateCache.paths.some(path => /^\/(api|v1|account|max)(\/|$)/.test(path)))
  assert(!JSON.stringify(privateCache.rows).includes('F04 private note'))
  assert(privateCache.rows.every(row => !('note' in row) && !('token' in row.wine)))
  await page.screenshot({ path: resolve(dir, 'offline-mobile.png'), fullPage: true })
  report.checks.continuousJourney = { exactCandidate: candidateSlug, comparison: true, focusReturn: true, browserBack: true, mainDiarySave: true, statusNoteReload: true, originalHistoryPreserved: true, noExtraRecognition: true, offlineReload: true, privateResponsesUncached: true, privateNotesExcluded: true }
  await context.setOffline(false)
  // A delayed save from A must not repopulate B after an in-place account change.
  const race = await browser.newContext({ serviceWorkers: 'block', ignoreHTTPSErrors: true })
  await race.addCookies([{ name: '__Host-cv_session', value: sessions.a.token, url: base, secure: true, httpOnly: true, sameSite: 'Lax' }])
  await race.addInitScript(() => localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes'))
  await race.route('https://**', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort())
  const racePage = await race.newPage()
  await racePage.goto(base, { waitUntil: 'networkidle' })
  await racePage.locator('input[aria-label="Выбрать фотографию этикетки"]').setInputFiles({ name: 'public.webp', mimeType: 'image/webp', buffer: photo })
  await racePage.getByRole('button', { name: 'Найти альтернативы', exact: true }).click()
  const second = racePage.locator('.f04-results>li').nth(1)
  const secondSlug = await second.locator('a').getAttribute('href').then(url => new URL(url).pathname.split('/').pop())
  let releaseWrite
  let writeFinished
  const completedWrite = new Promise(resolve => { writeFinished = resolve })
  await racePage.route(`**/api/account/saved/${secondSlug}`, route => new Promise(resolve => { releaseWrite = async () => { const response = await route.fetch({ headers: route.request().headers() }); await route.fulfill({ response }); resolve(); writeFinished() } }))
  await second.locator('.pin-button').click()
  await until(() => releaseWrite, 'Held A save')
  await race.addCookies([{ name: '__Host-cv_session', value: sessions.b.token, url: base, secure: true, httpOnly: true, sameSite: 'Lax' }])
  await racePage.getByRole('link', { name: 'Винный дневник', exact: true }).click()
  await racePage.getByText('f04_b', { exact: true }).waitFor()
  await releaseWrite(); await completedWrite
  await racePage.getByRole('link', { name: 'Что за вино? — поиск по фото', exact: true }).click()
  await racePage.waitForLoadState('networkidle')
  assert.equal(await racePage.locator('.f04-local-list li').count(), 0)
  assert.equal((await race.request.get(base + '/api/account/saved').then(r => r.json())).items.length, 0)
  report.checks.inFlightAccountSwitch = true
  await race.close()
  await page.goto(base + '/account?tab=settings', { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: 'Выйти', exact: true }).click()
  await page.goto(base, { waitUntil: 'networkidle' })
  assert.equal(await page.locator('.f04-local-list li').count(), 0)
  await context.addCookies([{ name: '__Host-cv_session', value: sessions.b.token, url: base, secure: true, httpOnly: true, sameSite: 'Lax' }])
  await page.reload({ waitUntil: 'networkidle' })
  assert.equal(await page.locator('.f04-local-list li').count(), 0)
  const bSaved = await context.request.get(base + '/api/account/saved').then(r => r.json())
  assert.equal(bSaved.items.length, 0)
  report.checks.logoutAndAccountIsolation = true

  // Exercise the actual IndexedDB module, including transactions and stale-owner writes.
  const bundled = await build({ entryPoints: [resolve(root, 'shared/offline-cards.ts')], bundle: true, platform: 'browser', format: 'iife', globalName: 'F04Offline', write: false })
  await page.addScriptTag({ content: bundled.outputFiles[0].text })
  report.checks.storage = await page.evaluate(async ({ wine, version }) => {
    const { createOfflineStore, makeOfflineCard } = window.F04Offline
    const store = createOfflineStore(indexedDB)
    await store.clear()
    // Corrupt records stay outside the public view. Unsupported versions fail closed.
    const db = await new Promise((resolve, reject) => { const request = indexedDB.open('chtozavino-offline-cards-v1', 1); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error) })
    await new Promise((resolve, reject) => { const tx = db.transaction('cards', 'readwrite'); tx.objectStore('cards').put({ slug: 'corrupt-card', note: 'private-corrupt-fixture', schemaVersion: 0 }); tx.oncomplete = resolve; tx.onerror = () => reject(tx.error) })
    if ((await store.list()).cards.length) throw new Error('Corrupt record was exposed')
    db.close()
    const unsupportedDb = await new Promise((resolve, reject) => { const request = indexedDB.open('f04-unsupported-schema', 2); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error) })
    unsupportedDb.close()
    const unsupported = createOfflineStore({ open: (_name, version) => indexedDB.open('f04-unsupported-schema', version) })
    let unsupportedRejected = false
    try { await unsupported.list() } catch { unsupportedRejected = true }
    if (!unsupportedRejected) throw new Error('Unsupported schema was accepted')
    const a = await store.activate('isolated-owner-a')
    for (let i = 0; i < 51; i++) await store.save(a, makeOfflineCard({ ...wine, slug: `bounded-wine-${i}` }, version, new Date(1800000000000 + i * 1000).toISOString()))
    let value = await store.list()
    if (value.cards.length !== 50 || value.cards.some(card => card.slug === 'bounded-wine-0')) throw new Error('Eviction failed')
    await store.activate('isolated-owner-b')
    let refused = false
    try { await store.save(a, makeOfflineCard(wine, version)) } catch { refused = true }
    value = await store.list()
    if (!refused || value.cards.length) throw new Error('Stale owner write survived')
    const b = await store.activate('isolated-owner-b')
    const originalPut = IDBObjectStore.prototype.put
    IDBObjectStore.prototype.put = function (...args) { if (this.name === 'cards') throw new DOMException('Quota fault', 'QuotaExceededError'); return originalPut.apply(this, args) }
    let quotaRejected = false
    try { await store.save(b, makeOfflineCard(wine, version)) } catch { quotaRejected = true }
    IDBObjectStore.prototype.put = originalPut
    if (!quotaRejected || (await store.list()).cards.length) throw new Error('Quota failure was not atomic')
    const pending = store.save(b, makeOfflineCard(wine, version)).catch(() => {})
    await store.clear()
    await pending
    if ((await store.list()).cards.length) throw new Error('In-flight write restored cleared data')
    return { corruptRecordsHidden: true, unsupportedSchemaRejected: true, quotaRejected: true, pendingWriteCannotRestoreClearedData: true, boundedAt50: true, oldestEvicted: true, staleOwnerWriteRejected: true, ownerChangeClears: true }
  }, { wine: fixtureWine, version: data.version })

  // A denied local store must not turn a server save into a false offline success.
  const denied = await browser.newContext({ serviceWorkers: 'block', ignoreHTTPSErrors: true })
  await denied.addCookies([{ name: '__Host-cv_session', value: sessions.b.token, url: base, secure: true, httpOnly: true, sameSite: 'Lax' }])
  await denied.addInitScript(() => { localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes'); IDBFactory.prototype.open = () => { throw new DOMException('Denied for test', 'SecurityError') } })
  await denied.route('https://**', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort())
  const deniedPage = await denied.newPage()
  await deniedPage.goto(base, { waitUntil: 'networkidle' })
  await deniedPage.locator('input[aria-label="Выбрать фотографию этикетки"]').setInputFiles({ name: 'public.webp', mimeType: 'image/webp', buffer: photo })
  const deniedOriginal = deniedPage.locator('.match-panel .pin')
  await deniedOriginal.locator('.pin-button').click()
  await deniedOriginal.getByText('Сохранено в дневнике. Копия для офлайн-открытия недоступна.', { exact: true }).waitFor()
  assert((await denied.request.get(base + '/api/account/saved').then(r => r.json())).items.some(item => item.slug === fixtureSlug))
  await deniedOriginal.getByRole('button', { name: 'Убрать из сохранённых', exact: true }).click()
  report.checks.originalSaveDeniedStoragePreservesOnlineSave = true
  await deniedPage.getByRole('button', { name: 'Найти альтернативы', exact: true }).click()
  await deniedPage.locator('.f04-results>li').first().locator('.pin-button').click()
  await deniedPage.getByText('Сохранено в дневнике. Копия для офлайн-открытия недоступна.', { exact: true }).waitFor()
  const bPersisted = await denied.request.get(base + '/api/account/saved').then(r => r.json())
  assert(bPersisted.items.some(item => item.slug === candidateSlug))
  report.checks.deniedStoragePreservesOnlineSave = true
  await deniedPage.keyboard.press('Escape')
  const expiredCard = deniedPage.locator('.f04-results>li').nth(1)
  const expiredSlug = await expiredCard.locator('a').getAttribute('href').then(url => new URL(url).pathname.split('/').pop())
  await deniedPage.route(`**/api/account/saved/${expiredSlug}`, route => route.fulfill({ status: 401, json: { error: 'session_invalid' } }))
  await expiredCard.locator('.pin-button').click()
  await expiredCard.getByRole('link', { name: 'Войти', exact: true }).waitFor()
  report.checks.expiredSessionOffersLogin = true
  await denied.close()
  const safari = await webkit.launch({ headless: true })
  try {
    const safariContext = await safari.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: 'allow', ignoreHTTPSErrors: true })
    await safariContext.addCookies([{ name: '__Host-cv_session', value: sessions.b.token, url: base, secure: true, httpOnly: true, sameSite: 'Lax' }])
    await safariContext.addInitScript(() => localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes'))
    await safariContext.route('https://**', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort())
    const safariPage = await safariContext.newPage()
    await safariPage.goto(base, { waitUntil: 'networkidle' })
    await safariPage.locator('input[aria-label="Выбрать фотографию этикетки"]').setInputFiles({ name: 'public.webp', mimeType: 'image/webp', buffer: photo })
    await safariPage.locator('.match-panel .pin-button').click()
    await safariPage.locator('.match-panel .pin').getByText('Доступно офлайн на этом устройстве.', { exact: true }).waitFor()
    await safariPage.keyboard.press('Escape')
    await safariPage.getByRole('button', { name: 'Найти альтернативы', exact: true }).click()
    const safariFirst = safariPage.locator('.f04-results>li').first()
    await safariFirst.getByRole('button', { name: 'Сравнить', exact: true }).click()
    await safariPage.locator('.f04-dialog[open]').waitFor()
    await safariPage.keyboard.press('Escape')
    const savedWhiteSlug = 'mont-blanc-blanc-de-blancs'
    const safariSaved = await safariContext.request.put(base + `/api/account/saved/${savedWhiteSlug}`, { headers: { Origin: base }, data: { status: 'liked', source: 'lineup' } })
    assert.equal(safariSaved.status(), 200)
    await safariPage.getByRole('button', { name: 'Сравнить с сохранённым', exact: true }).click()
    await safariPage.getByRole('searchbox', { name: 'Поиск в сохранённых' }).fill('Mont Blanc')
    await safariPage.locator('.f04-saved-options button').click()
    assert.equal(await safariPage.locator('.f04-dialog[open] .f04-facts>div').count(), 8)
    assert((await safariPage.locator('.f04-compare-cards').textContent()).includes(data.wines.find(wine => wine.slug === savedWhiteSlug).name))
    await safariPage.keyboard.press('Escape')
    report.checks.webkitSavedComparison = true
    await safariFirst.locator('.pin-button').click()
    await safariFirst.getByRole('button', { name: 'Сохранить копию на устройстве', exact: true }).click()
    await safariFirst.getByText('Доступно офлайн на этом устройстве.', { exact: true }).waitFor()
    await safariPage.evaluate(() => navigator.serviceWorker.ready)
    await safariPage.reload({ waitUntil: 'load' })
    await safariPage.locator('.f04-local-list li').first().waitFor()
    await safariContext.setOffline(true)
    await safariPage.reload({ waitUntil: 'load' })
    await safariPage.locator('.f04-local-list').getByRole('button', { name: fixtureWine.name, exact: true }).click()
    await safariPage.locator('.f04-stored-card').waitFor()
    report.checks.webkitOriginalSaveOffline = true
    await safariPage.locator('.f04-local-list').getByRole('button', { name, exact: true }).click()
    await safariPage.locator('.f04-stored-card').waitFor()
    report.checks.webkitJourney = { comparison: true, escape: true, existingSaveReused: true, explicitOfflineCopy: true, offlineReload: true }
    await safariContext.close()
  } finally { await safari.close() }

  const signup = await browser.newContext({ serviceWorkers: 'allow', ignoreHTTPSErrors: true })
  await signup.addInitScript(() => localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes'))
  await signup.route('https://**', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort())
  const signupPage = await signup.newPage()
  await signupPage.goto(base, { waitUntil: 'networkidle' })
  await signupPage.locator('input[aria-label="Выбрать фотографию этикетки"]').setInputFiles({ name: 'public.webp', mimeType: 'image/webp', buffer: photo })
  await signupPage.getByRole('button', { name: 'Найти альтернативы', exact: true }).click()
  const signupFirst = signupPage.locator('.f04-results>li').first()
  await signupFirst.getByRole('button', { name: 'Сравнить', exact: true }).click()
  await signupPage.locator('.f04-dialog[open] .pin-button').last().click()
  await signupPage.locator('.f04-dialog[open]').getByRole('link', { name: 'Войти', exact: true }).click()
  await signupPage.locator('#account-email').fill('f04-ui@example.invalid')
  await signupPage.getByRole('button', { name: 'Получить код', exact: true }).click()
  const mailCode = await until(async () => JSON.parse(await readFile(resolve(accountDir, 'outbox.json')))['f04-ui@example.invalid'], 'memory mail challenge')
  await signupPage.locator('#account-code').fill(mailCode)
  await signupPage.getByRole('button', { name: 'Войти', exact: true }).click()
  await signupPage.locator('#account-username').fill('f04_ui')
  for (const checkbox of await signupPage.locator('form').filter({ has: signupPage.locator('#account-username') }).getByRole('checkbox').all()) await checkbox.check()
  await signupPage.locator('form').filter({ has: signupPage.locator('#account-username') }).locator('button[type=submit]').click()
  await signupPage.getByRole('button', { name: 'Продолжить сравнение', exact: true }).click()
  assert.equal(await signupPage.locator('.match-badge').count(), 0, 'Login return must not pretend to recognize another photo')
  const restored = signupPage.locator('.f04-dialog[open]')
  assert((await restored.textContent()).includes(name))
  const empty = await signup.request.get(base + '/api/account/saved').then(r => r.json())
  assert.equal(empty.items.length, 0, 'Login must not save automatically')
  await restored.locator('.pin-button').last().click()
  await restored.getByText('Доступно офлайн на этом устройстве.', { exact: true }).waitFor()
  await signupPage.getByRole('button', { name: 'Закрыть сравнение', exact: true }).click()

  // Use the actual saved list. This choice is independent of alternative ranking and saving.
  const savedWhiteSlug = 'mont-blanc-blanc-de-blancs'
  const savedWhite = data.wines.find(wine => wine.slug === savedWhiteSlug)
  for (const slug of [fixtureSlug, savedWhiteSlug]) {
    const saved = await signup.request.put(base + `/api/account/saved/${slug}`, { headers: { Origin: base }, data: { status: 'liked', source: 'lineup', note: 'Private saved comparison note' } })
    assert.equal(saved.status(), 200)
  }
  // A retired exact ID stays visible with an explicit unavailable state.
  const signupSession = (await signup.cookies(base)).find(cookie => cookie.name === '__Host-cv_session').value
  const retired = await fetch(`http://127.0.0.1:${accountPort}/v1/me/saved/retired-comparison-wine`, { method: 'PUT', headers: { Authorization: 'Bearer f04-local-web-' + 'w'.repeat(40), 'X-Session-Token': signupSession, 'Content-Type': 'application/json' }, body: JSON.stringify({ status: 'want', source: 'lineup' }) })
  assert.equal(retired.status, 201)
  await signupPage.locator('input[aria-label="Выбрать фотографию этикетки"]').setInputFiles({ name: 'public.webp', mimeType: 'image/webp', buffer: photo })
  await signupPage.locator('.history-note').waitFor()
  const savedBefore = await signup.request.get(base + '/api/account/saved').then(r => r.json())
  const historyBefore = await signup.request.get(base + '/api/account/history').then(r => r.json())
  const requestsBeforeSaved = observedPhotoRequests
  const savedEntry = signupPage.getByRole('button', { name: 'Сравнить с сохранённым', exact: true })
  const savedDialog = signupPage.locator('.f04-dialog[open]')
  await savedEntry.click()
  await signupPage.getByRole('searchbox', { name: 'Поиск в сохранённых' }).waitFor()
  assert.equal(await savedDialog.locator('.f04-saved-options li').count(), 3)
  await savedDialog.getByText('Этого вина нет в снимке каталога. Сравнение пока недоступно.', { exact: true }).waitFor()
  const savedAnswer = await signup.request.get(base + `/api/account/saved/comparison?base=${fixtureSlug}`).then(r => r.json())
  assert(!savedAnswer.items.some(item => item.slug === fixtureSlug))
  assert(!JSON.stringify(savedAnswer).includes('Private saved comparison note'))
  for (const theme of ['light', 'dark']) {
    await signupPage.emulateMedia({ colorScheme: theme })
    await until(async () => await signupPage.locator('html').getAttribute('data-theme') === theme, `Saved picker ${theme} theme`)
    for (const width of [320, 390, 1280]) {
      await signupPage.setViewportSize({ width, height: 844 })
      assert(await savedDialog.evaluate(el => el.scrollWidth <= el.clientWidth + 1), 'Saved picker overflows horizontally')
    }
    await signupPage.setViewportSize({ width: 390, height: 844 })
    await savedDialog.screenshot({ path: resolve(dir, `saved-picker-${theme}-mobile.png`) })
  }
  const savedSearch = signupPage.getByRole('searchbox', { name: 'Поиск в сохранённых' })
  await savedSearch.fill('no matching saved name')
  await savedDialog.getByText('Ничего не найдено. Измените поиск.', { exact: true }).waitFor()
  await savedSearch.fill('Mont Blanc')
  await savedDialog.getByRole('button', { name: `Сравнить с «${savedWhite.name}»`, exact: true }).click()
  assert.equal(await savedDialog.locator('.f04-facts>div').count(), 8)
  assert.deepEqual(await savedDialog.locator('.f04-compare-cards h3').allTextContents(), [fixtureWine.name, savedWhite.name])
  await savedDialog.getByRole('button', { name: 'Выбрать из сохранённых', exact: true }).click()
  await savedSearch.waitFor()
  await savedDialog.getByRole('button', { name: 'Вернуться к сравнению', exact: true }).click()
  assert.deepEqual(await savedDialog.locator('.f04-compare-cards h3').allTextContents(), [fixtureWine.name, savedWhite.name])
  await savedDialog.screenshot({ path: resolve(dir, 'saved-comparison-dark-mobile.png') })
  await savedDialog.getByRole('button', { name: 'Выбрать из сохранённых', exact: true }).click()
  await savedSearch.waitFor()
  await savedDialog.getByRole('button', { name: `Сравнить с «${name}»`, exact: true }).click()
  assert.deepEqual(await savedDialog.locator('.f04-compare-cards h3').allTextContents(), [fixtureWine.name, name])
  await signupPage.keyboard.press('Escape')
  await until(() => savedEntry.evaluate(el => document.activeElement === el), 'Saved comparison returns original focus')
  await savedEntry.click()
  await savedSearch.waitFor()
  await signupPage.goBack()
  await until(async () => !(await savedDialog.count()), 'Back closes saved picker')
  await signupPage.route('**/api/account/saved/comparison?*', route => route.fulfill({ status: 503, json: { error: 'account_unavailable' } }))
  await savedEntry.click()
  await savedDialog.getByRole('alert').waitFor()
  await signupPage.unroute('**/api/account/saved/comparison?*')
  await savedDialog.getByRole('button', { name: 'Повторить', exact: true }).click()
  await savedSearch.waitFor()
  await signupPage.keyboard.press('Escape')
  await signupPage.route('**/api/account/saved/comparison?*', route => route.fulfill({ json: { ...savedAnswer, items: [] } }))
  await savedEntry.click()
  await savedDialog.getByText('В сохранённых пока нет другого вина. Сохраните вино значком булавки в его карточке.', { exact: true }).waitFor()
  await signupPage.keyboard.press('Escape')
  await signupPage.unroute('**/api/account/saved/comparison?*')
  assert.deepEqual(await signup.request.get(base + '/api/account/saved').then(r => r.json()), savedBefore)
  assert.deepEqual(await signup.request.get(base + '/api/account/history').then(r => r.json()), historyBefore)
  assert.equal(observedPhotoRequests, requestsBeforeSaved, 'Saved picker must not repeat recognition')
  report.checks.savedComparison = { savedExactChoice: true, otherStylesAndSameProducerAllowed: true, sourceExcluded: true, retiredWineExplicit: true, privateNotesExcluded: true, search: true, cancelPreservesPair: true, back: true, escape: true, focusReturn: true, bothThemes: true, widths: [320, 390, 1280], retry: true, empty: true, savedAndHistoryUnchanged: true, noExtraRecognition: true }

  // An anonymous picker preserves only the first public slug across the normal email login.
  const pickerLogin = await browser.newContext({ serviceWorkers: 'block', ignoreHTTPSErrors: true })
  await pickerLogin.addInitScript(() => localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes'))
  await pickerLogin.route('https://**', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort())
  const pickerLoginPage = await pickerLogin.newPage()
  await pickerLoginPage.goto(base, { waitUntil: 'networkidle' })
  await pickerLoginPage.locator('input[aria-label="Выбрать фотографию этикетки"]').setInputFiles({ name: 'public.webp', mimeType: 'image/webp', buffer: photo })
  await pickerLoginPage.getByRole('button', { name: 'Сравнить с сохранённым', exact: true }).click()
  await pickerLoginPage.locator('.f04-dialog[open]').getByRole('link', { name: 'Войти', exact: true }).click()
  await pickerLoginPage.locator('#account-email').fill('f04-b@example.invalid')
  async function startPickerLogin() {
    const pending = pickerLoginPage.waitForResponse(response => response.url() === base + '/api/account/email/start' && response.request().method() === 'POST')
    await pickerLoginPage.getByRole('button', { name: 'Получить код', exact: true }).click()
    return pending
  }
  let pickerStart = await startPickerLogin()
  if (pickerStart.status() === 429) {
    const limit = await pickerStart.json()
    assert(Number.isInteger(limit.retryAfter) && limit.retryAfter >= 0 && limit.retryAfter <= 60)
    // Respect the actual email cooldown. Do not weaken authentication for this browser check.
    for (let second = 0; second <= limit.retryAfter; second++) await sleep(1000)
    pickerStart = await startPickerLogin()
  }
  assert.equal(pickerStart.status(), 200)
  const pickerCode = await until(async () => JSON.parse(await readFile(resolve(accountDir, 'outbox.json')))['f04-b@example.invalid'], 'picker email challenge')
  await pickerLoginPage.locator('#account-code').fill(pickerCode)
  await pickerLoginPage.getByRole('button', { name: 'Войти', exact: true }).click()
  await pickerLoginPage.getByRole('button', { name: 'Продолжить сравнение', exact: true }).click()
  await pickerLoginPage.getByRole('searchbox', { name: 'Поиск в сохранённых' }).waitFor()
  assert.equal(await pickerLoginPage.locator('.match-badge').count(), 0)
  assert.equal(await pickerLoginPage.locator('.f04-saved-options li').count(), 2)
  report.checks.savedPickerLoginReturn = true
  await pickerLogin.close()

  const otherTab = await signup.newPage()
  await otherTab.goto(base, { waitUntil: 'networkidle' })
  await otherTab.locator('.f04-local-list li').first().waitFor()
  await signupPage.goto(base + '/account?tab=settings', { waitUntil: 'networkidle' })
  await signupPage.getByRole('button', { name: 'Удалить аккаунт', exact: true }).click()
  await signupPage.getByRole('button', { name: 'Удалить навсегда', exact: true }).click()
  await until(async () => (await otherTab.locator('.f04-local-list li').count()) === 0, 'Other tab clears after account deletion')
  report.checks.loginContinuation = { realCodeChallenge: true, overrideDisabled: true, restoredExactPair: true, noPhotoStored: true, noAutomaticSave: true, explicitSaveAfterReturn: true }
  report.checks.accountDeletionClearsOtherTab = true
  await signup.close()
  assert.deepEqual(errors, [])
  report.pageErrors = errors
  if (process.env.F04_ANDROID === '1') {
    const androidProbe = createServer()
    const androidPort = await listen(androidProbe)
    await new Promise(resolve => androidProbe.close(resolve))
    const androidOrigin = `http://localhost:${androidPort}`
    const androidPreview = spawn(process.execPath, ['.output/server/index.mjs'], { cwd: root, env: { ...process.env, HOST: '127.0.0.1', PORT: String(androidPort), NUXT_PREDICTION_MODE: 'upstream', NUXT_PREDICTION_ENDPOINT: matcherEndpoint, NUXT_ACCOUNT_ENDPOINT: `http://127.0.0.1:${accountPort}`, ACCOUNT_WEB_TOKEN: 'f04-local-web-' + 'w'.repeat(40), NUXT_ACCOUNT_PUBLIC_ORIGIN: androidOrigin }, stdio: 'ignore' })
    children.push(androidPreview)
    await until(async () => (await fetch(`http://127.0.0.1:${androidPort}/api/health`)).ok, 'Android localhost preview')
    const androidRuntime = resolve(dir, 'private-android-runtime.json')
    await writeFile(androidRuntime, JSON.stringify({ base: androidOrigin, sessionsPath: resolve(accountDir, 'sessions.json'), reportDir: dir, matcher: report.recognition }))
    const android = spawn(process.execPath, [resolve(root, 'scripts/check-f04-android.mjs')], { cwd: root, env: { ...process.env, F04_ANDROID_RUNTIME: androidRuntime }, stdio: 'inherit' })
    const result = await new Promise(resolve => android.on('exit', resolve))
    assert.equal(result, 0, 'Physical Pixel 8 journey failed')
    report.checks.pixel8 = JSON.parse(await readFile(resolve(dir, 'pixel8-report.json')))
  }
  report.photoRequests = observedPhotoRequests
  report.finishedAt = new Date().toISOString()
  report.status = 'PASS'
  await writeFile(resolve(dir, 'browser-report.json'), JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report, null, 2))
} catch (error) {
  report.status = 'FAIL'; report.error = error.stack; report.accountError = accountError
  await writeFile(resolve(dir, 'browser-report.json'), JSON.stringify(report, null, 2) + '\n')
  throw error
} finally {
  await browser?.close()
  for (const child of children.reverse()) child.kill('SIGTERM')
  matcher.closeAllConnections(); tlsProxy.closeAllConnections()
  await new Promise(resolve => matcher.close(resolve))
  await new Promise(resolve => tlsProxy.close(resolve))
  await localTls.close()
}
