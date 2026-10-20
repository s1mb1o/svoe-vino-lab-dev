// Disposable account -> built portal -> real stdio MCP, with browser editing.
import assert from 'node:assert/strict'
import { spawn, spawnSync } from 'node:child_process'
import { createServer, request as httpRequest } from 'node:http'
import { createServer as createHttpsServer } from 'node:https'
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import { tmpdir } from 'node:os'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

assert(process.env.PLAYWRIGHT_MODULE, 'Set PLAYWRIGHT_MODULE to the local Playwright index.mjs.')
assert(process.env.ACCOUNT_TASTE_PYTHON, 'Set ACCOUNT_TASTE_PYTHON to Python with the account package installed.')
const { chromium, webkit } = await import(process.env.PLAYWRIGHT_MODULE)
const browserName = process.env.ACCOUNT_TASTE_BROWSER || 'chromium'
assert(['chromium', 'webkit'].includes(browserName), 'Unsupported test browser.')
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const mcpRequire = createRequire(resolve(root, '../mcp/package.json'))
const { Client } = await import(mcpRequire.resolve('@modelcontextprotocol/client'))
const { StdioClientTransport } = await import(mcpRequire.resolve('@modelcontextprotocol/client/stdio'))
const reportDir = resolve(process.env.ACCOUNT_TASTE_REPORT_DIR || resolve(tmpdir(), 'account-taste-report'))
await mkdir(reportDir, { recursive: true })
const privateDir = await mkdtemp(resolve(tmpdir(), 'account-taste-private-'))
const children = []
const reports = { browser: browserName, checks: {}, limitations: ['Disposable accounts and synthetic tokens only; no production deployment or real email delivery.'] }
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))
async function until(fn) {
  let error
  for (let i = 0; i < 150; i++) { try { const answer = await fn(); if (answer) return answer } catch (failure) { error = failure }; await sleep(100) }
  throw error || new Error('Timed out waiting for the local test stack.')
}
const listen = server => new Promise(resolve => server.listen(0, '127.0.0.1', () => resolve(server.address().port)))
const reserve = createServer()
const port = await listen(reserve)
await new Promise(resolve => reserve.close(resolve))
const cert = resolve(privateDir, 'cert.pem'), key = resolve(privateDir, 'key.pem')
assert.equal(spawnSync('openssl', ['req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-subj', '/CN=localhost', '-addext', 'subjectAltName=IP:127.0.0.1,DNS:localhost', '-days', '1', '-keyout', key, '-out', cert], { stdio: 'ignore' }).status, 0)
const proxy = createHttpsServer({ key: await readFile(key), cert: await readFile(cert) }, (req, res) => {
  const upstream = httpRequest(`http://127.0.0.1:${port}${req.url}`, { method: req.method, headers: { ...req.headers, 'x-forwarded-proto': 'https' } }, answer => { res.writeHead(answer.statusCode, answer.headers); answer.pipe(res) })
  upstream.on('error', () => { if (!res.headersSent) res.writeHead(502); res.end() })
  req.pipe(upstream)
})
const base = `https://127.0.0.1:${await listen(proxy)}`
let browser, client
try {
  const account = spawn(process.env.ACCOUNT_TASTE_PYTHON, [resolve(root, 'scripts/f04-account-harness.py'), privateDir], { stdio: 'ignore' })
  children.push(account)
  const accountPort = await until(async () => JSON.parse(await readFile(resolve(privateDir, 'account-port.json'))).port)
  await until(async () => (await fetch(`http://127.0.0.1:${accountPort}/healthz`)).ok)
  const sessions = JSON.parse(await readFile(resolve(privateDir, 'sessions.json')))
  const preview = spawn(process.execPath, ['.output/server/index.mjs'], { cwd: root, env: { ...process.env, HOST: '127.0.0.1', PORT: String(port), NUXT_ACCOUNT_ENDPOINT: `http://127.0.0.1:${accountPort}`, ACCOUNT_WEB_TOKEN: 'f04-local-web-' + 'w'.repeat(40), NUXT_ACCOUNT_PUBLIC_ORIGIN: base }, stdio: 'ignore' })
  children.push(preview)
  await until(async () => (await fetch(`http://127.0.0.1:${port}/api/health`)).ok)
  async function owner(method, path, body, person = 'a') {
    const response = await fetch(`http://127.0.0.1:${accountPort}${path}`, { method, headers: { Authorization: 'Bearer f04-local-web-' + 'w'.repeat(40), 'X-Session-Token': sessions[person].token, 'X-Client-IP': '127.0.0.1', 'Content-Type': 'application/json' }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) })
    assert(response.ok, `Local owner request failed: ${method} ${path}: ${response.status}`)
    return response.status === 204 ? null : response.json()
  }
  const slug = 'cantiani-cabernet-sauvignon'
  await owner('POST', '/v1/me/history', { slug, source: 'photo', wine_snapshot: { name: 'Disposable tasting fixture', producer: 'Test producer' } })
  await owner('PUT', `/v1/me/saved/${slug}`, { status: 'liked', source: 'history', note: 'Private saved note must not reach MCP.' })
  browser = await (browserName === 'webkit' ? webkit : chromium).launch({ headless: true })
  const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1280, height: 900 } })
  await context.addCookies([{ name: '__Host-cv_session', value: sessions.a.token, url: base, secure: true, httpOnly: true, sameSite: 'Lax' }])
  await context.addInitScript(() => localStorage.setItem('svoe-vino.age-confirmed.v1', 'yes'))
  await context.route(/mc\.yandex\.ru/, route => route.abort())
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(base + '/account?tab=settings')
  await page.getByLabel('Белое', { exact: true }).check()
  await page.locator('#taste-sparkling').selectOption('yes')
  await page.getByLabel('Сухое', { exact: true }).check()
  await page.locator('#taste-body').selectOption('light')
  await page.locator('#taste-freshness').selectOption('fresh')
  await page.locator('#taste-grapes').fill('Рислинг, Шардоне')
  await page.getByRole('button', { name: 'Сохранить предпочтения', exact: true }).click()
  await page.getByText('Предпочтения сохранены.', { exact: true }).waitFor()
  await page.reload()
  await page.locator('#taste-grapes').waitFor()
  assert(await page.getByLabel('Белое', { exact: true }).isChecked())
  assert.equal(await page.locator('#taste-grapes').inputValue(), 'Рислинг, Шардоне')
  reports.checks.preferences_edit_reload = true
  await page.goto(base + '/account?tab=history')
  await page.getByRole('button', { name: 'Оценить вино', exact: true }).click()
  await page.getByLabel('Ваша оценка', { exact: true }).selectOption('5')
  await page.getByLabel('Заметка к оценке', { exact: true }).fill('A tasting note shared with my apps.')
  await page.getByRole('button', { name: 'Сохранить оценку', exact: true }).click()
  await page.getByRole('button', { name: 'Оценка: 5 из 5', exact: true }).waitFor()
  reports.checks.rating_and_note_edit = true
  const token = (await owner('POST', '/v1/me/app-tokens', { name: 'Disposable MCP check', lifetime_days: 30 })).token
  const publicProfile = await context.request.get(base + '/api/app/v1/profile', { headers: { authorization: `Bearer ${token}` } })
  assert.equal(publicProfile.status(), 200, 'Public app profile request failed.')
  const transport = new StdioClientTransport({ command: process.execPath, args: [resolve(root, '../mcp/src/cli.mjs')], stderr: 'pipe', env: { ...process.env, NODE_EXTRA_CA_CERTS: cert, CHTOZAVINO_ACCOUNT_TOKEN: token, CHTOZAVINO_ACCOUNT_URL: base } })
  let stderr = ''
  transport.stderr.on('data', data => { stderr += data })
  client = new Client({ name: 'disposable-account-taste-check', version: '1.0.0' })
  await client.connect(transport)
  async function tool(name, args = {}) {
    const result = await client.callTool({ name, arguments: args })
    assert(!JSON.stringify(result).includes(token), 'Token appeared in a tool result.')
    assert(!result.isError, `MCP ${name} failed: ${JSON.stringify(result.structuredContent)}`)
    return result.structuredContent
  }
  assert.equal((await client.listTools()).tools.length, 7)
  const profile = await tool('get_my_profile')
  assert.deepEqual(profile.profile.preferences.grapes, ['Рислинг', 'Шардоне'])
  const history = await tool('list_my_wines')
  assert.equal(history.items[0].rating, 5)
  assert.equal(history.items[0].note, 'A tasting note shared with my apps.')
  assert(!JSON.stringify(history).includes('Private saved note'))
  reports.checks.real_account_portal_stdio_mcp = true
  await owner('DELETE', '/v1/me/history')
  assert.equal((await tool('list_my_wines')).items.length, 0)
  assert.equal((await tool('list_my_wines', { collection: 'rated' })).items[0].rating, 5)
  reports.checks.rating_survives_history_removal = true
  assert.deepEqual((await owner('GET', '/v1/me/ratings', undefined, 'b')).items, [])
  reports.checks.account_isolation = true
  await page.goto(base + '/account?tab=settings')
  await page.getByRole('button', { name: 'Оценка: 5 из 5', exact: true }).waitFor()
  await page.screenshot({ path: resolve(reportDir, 'settings-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 375, height: 812 })
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Mobile page overflows horizontally.')
  await page.screenshot({ path: resolve(reportDir, 'settings-mobile.png'), fullPage: true })
  await page.getByRole('button', { name: 'Оценка: 5 из 5', exact: true }).click()
  await page.getByLabel('Ваша оценка', { exact: true }).selectOption('1')
  await page.getByLabel('Заметка к оценке', { exact: true }).fill('')
  await page.getByRole('button', { name: 'Сохранить оценку', exact: true }).click()
  await page.getByRole('button', { name: 'Оценка: 1 из 5', exact: true }).waitFor()
  const changed = (await tool('list_my_wines', { collection: 'rated' })).items[0]
  assert.equal(changed.rating, 1); assert.equal(changed.note, null)
  await page.getByRole('button', { name: 'Оценка: 1 из 5', exact: true }).click()
  await page.getByRole('button', { name: 'Удалить оценку', exact: true }).click()
  await page.getByText('Оценок пока нет.', { exact: true }).waitFor()
  assert.equal((await tool('list_my_wines', { collection: 'rated' })).items.length, 0)
  await page.getByRole('button', { name: 'Сбросить', exact: true }).click()
  await page.getByText('Предпочтения сброшены.', { exact: true }).waitFor()
  assert.equal((await tool('get_my_profile')).profile.preferences, null)
  assert.equal((await owner('GET', '/v1/me/saved')).items[0].note, 'Private saved note must not reach MCP.')
  reports.checks.rating_update_clear_delete_preferences_reset = true
  assert.equal(stderr, '')
  assert.deepEqual(errors, [])
  reports.checks.no_browser_or_mcp_errors = true
  await writeFile(resolve(reportDir, 'report.json'), JSON.stringify(reports, null, 2))
  console.log(JSON.stringify(reports, null, 2))
} finally {
  await client?.close()
  await browser?.close()
  for (const child of children.reverse()) {
    child.kill('SIGTERM')
    await Promise.race([new Promise(resolve => child.once('exit', resolve)), sleep(3000)])
    if (child.exitCode === null) child.kill('SIGKILL')
  }
  proxy.closeAllConnections()
  await new Promise(resolve => proxy.close(resolve))
  await rm(privateDir, { recursive: true, force: true })
}
