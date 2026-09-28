import assert from 'node:assert/strict'
import { readFile, mkdir, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { spawnSync } from 'node:child_process'
import { resolve } from 'node:path'

const origin = process.env.PORTAL_ORIGIN || 'http://127.0.0.1:8153'
const source = resolve(process.env.OFFICIAL_EVAL_DIR || '../../svoe-wino-hackaton/dataset/official-2026-09-17/eval')
const reportDir = resolve('reports', new Date().toISOString().replaceAll(':', '-'))
await mkdir(reportDir, { recursive: true })
const config = await fetch(`${origin}/api/config`).then(response => response.json())
assert.equal(config.predictionMode, 'mock', 'This check requires mock mode. It must not send official photos to an upstream.')
assert.equal(config.apiAvailable, true)
assert.equal(config.catalogMode, 'source-fallback')
const script = resolve(source, 'participant_test.sh')
const before = createHash('sha256').update(await readFile(script)).digest('hex')
const output = resolve(reportDir, 'predictions.jsonl')
const run = spawnSync('bash', [script, '--images-dir', resolve(source, 'queries'), '--manifest', resolve(source, 'queries.tsv'), '--endpoint', `${origin}/v1/eval/predict`, '--output', output], { encoding: 'utf8', timeout: 40000 })
assert.equal(run.status, 0, run.stderr || run.stdout)
const rows = (await readFile(output, 'utf8')).trim().split('\n').map(row => JSON.parse(row))
const manifest = (await readFile(resolve(source, 'queries.tsv'), 'utf8')).trim().split('\n').slice(1)
assert.equal(rows.length, manifest.length)
for (const [index, row] of rows.entries()) {
  const [queryId, imagePath] = manifest[index].split('\t')
  assert.equal(row.query_id, queryId)
  assert.equal(row.image_path, imagePath)
  assert.equal(row.predicted_slug, 'priboj-marchenko-beloe-polusuhoe')
  assert.match(row.image_sha256, /^[a-f0-9]{64}$/)
  assert(row.latency_ms < 10000)
}
assert.equal(createHash('sha256').update(await readFile(script)).digest('hex'), before)

const checks = []
for (const [path, expectedStatus] of [['/', 200], ['/wines', 200], ['/wines/', 200], ['/api/wines/not-in-demo', 404], ['/api/health', 200]]) {
  const response = await fetch(origin + path)
  assert.equal(response.status, expectedStatus, path)
  if (path === '/') {
    const html = await response.text()
    assert(html.includes('Найти вино'))
    assert(html.includes('Проверяем подтверждение возраста'))
    assert(html.includes('age-loading'))
    assert(!html.includes('Фильтры каталога'))
    assert(!html.includes('wine-grid'))
  }
  checks.push({ path, status: response.status })
}
const manifestResponse = await fetch(origin + '/manifest.webmanifest')
assert.equal(manifestResponse.status, 200)
const webManifest = await manifestResponse.json()
assert.equal(webManifest.start_url, '/')
assert.equal(webManifest.display, 'standalone')
assert(webManifest.icons.some(icon => icon.sizes === '192x192' && icon.purpose === 'any'))
assert(webManifest.icons.some(icon => icon.sizes === '512x512' && icon.purpose === 'any'))
assert(webManifest.icons.some(icon => icon.sizes === '512x512' && icon.purpose === 'maskable'))
checks.push({ path: '/manifest.webmanifest', status: manifestResponse.status })
const serviceWorker = await fetch(origin + '/sw.js')
assert.equal(serviceWorker.status, 200)
const serviceWorkerSource = await serviceWorker.text()
assert(serviceWorkerSource.includes('NetworkFirst'))
assert(serviceWorkerSource.includes('svoe-vino-pages'))
assert(serviceWorkerSource.includes('/api/'))
assert(serviceWorkerSource.includes('/v1/'))
checks.push({ path: '/sw.js', status: serviceWorker.status })
for (const icon of ['/icons/pwa-192.png', '/icons/pwa-512.png', '/icons/pwa-maskable-512.png', '/icons/apple-touch-icon.png']) {
  const response = await fetch(origin + icon)
  assert.equal(response.status, 200)
  assert(response.headers.get('content-type')?.startsWith('image/png'))
  checks.push({ path: icon, status: response.status })
}
const oldDetail = await fetch(`${origin}/wines/priboj-marchenko-beloe-polusuhoe`, { redirect: 'manual' })
assert.equal(oldDetail.status, 302)
assert.equal(oldDetail.headers.get('location'), 'https://vino-svoe.ru/wines/priboj-marchenko-beloe-polusuhoe')
checks.push({ path: '/wines/priboj-marchenko-beloe-polusuhoe', status: 302 })
const catalog = await fetch(origin + '/api/wines').then(response => response.json())
assert.equal(catalog.length, 12)
for (const wine of catalog) {
  const detail = await fetch(`${origin}/api/wines/${encodeURIComponent(wine.slug)}`).then(response => response.json())
  assert.equal(detail.slug, wine.slug)
  const image = await fetch(origin + wine.image, { redirect: 'manual' })
  assert.equal(image.status, 200)
  assert(image.headers.get('content-type')?.startsWith('image/'))
}
const summary = { date: new Date().toISOString(), origin, mode: 'mock', catalogSize: catalog.length, evaluatorScriptSha256: before, evaluatorRequests: rows.length, predictions: rows, httpChecks: checks, limitation: 'Compatibility check only. The mock returns a fixed slug. This is not an accuracy result.' }
await writeFile(resolve(reportDir, 'summary.json'), JSON.stringify(summary, null, 2) + '\n')
console.log(JSON.stringify({ ok: true, evaluatorRequests: rows.length, catalogSize: catalog.length, report: resolve(reportDir, 'summary.json') }, null, 2))
