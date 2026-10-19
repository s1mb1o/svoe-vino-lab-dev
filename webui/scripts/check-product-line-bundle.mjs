// Checks the built output: the scanner pages do not load producer map data at first paint.
// Usage: npm run build && npm run test:bundle
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { createServer } from 'node:net'
import { gzipSync } from 'node:zlib'

const chunks = '.output/public/_nuxt'
assert(existsSync('.output/server/index.mjs'), 'Run `npm run build` first.')
const files = readdirSync(chunks).filter(name => name.endsWith('.js'))
const source = name => readFileSync(`${chunks}/${name}`, 'utf8')
const gzip = names => [...names].reduce((total, name) => total + gzipSync(readFileSync(`${chunks}/${name}`)).length, 0)
const kb = bytes => `${(bytes / 1024).toFixed(1)} KB gzip`

// The last product image of a producer exists only in the map data of that producer.
// The index holds the first image as the cover, so the first image cannot identify a map chunk.
const directory = 'shared/data/product-line-maps'
const maps = readdirSync(directory).filter(name => name.endsWith('.json')).map(name => JSON.parse(readFileSync(`${directory}/${name}`, 'utf8')))
const mapChunks = new Map()
for (const map of maps) {
  const images = map.products.filter(product => product.image).map(product => product.image.src)
  assert(images.length >= 2, `${map.producer.id}: two product images are needed to identify its chunk`)
  const marker = images.at(-1)
  const found = files.filter(name => source(name).includes(marker))
  assert.equal(found.length, 1, `${map.producer.id}: expected one chunk with ${marker}, found ${found.length}`)
  mapChunks.set(found[0], map.producer.id)
}
assert.equal(mapChunks.size, maps.length, 'Each producer map MUST be a separate chunk')

const port = await new Promise(resolve => {
  const probe = createServer().listen(0, '127.0.0.1', () => { const { port } = probe.address(); probe.close(() => resolve(port)) })
})
const origin = `http://127.0.0.1:${port}`
const server = spawn(process.execPath, ['.output/server/index.mjs'], { env: { ...process.env, HOST: '127.0.0.1', PORT: String(port) }, stdio: 'ignore' })
try {
  for (let attempt = 0; ; attempt++) {
    try { if ((await fetch(`${origin}/api/health`)).ok) break } catch {}
    assert(attempt < 60, 'The built server did not start')
    await new Promise(resolve => setTimeout(resolve, 500))
  }
  for (const path of ['/', '/shelf']) {
    const html = await (await fetch(`${origin}${path}`)).text()
    const prefetched = [...html.matchAll(/<link[^>]+rel="prefetch"[^>]+href="\/_nuxt\/([\w-]+\.js)"/g)].map(match => match[1])
    const roots = [...html.matchAll(/(?:<script[^>]+src|<link[^>]+rel="modulepreload"[^>]+href)="\/_nuxt\/([\w-]+\.js)"/g)].map(match => match[1])
    const firstLoad = new Set()
    const stack = [...roots]
    while (stack.length) {
      const name = stack.pop()
      if (firstLoad.has(name) || !files.includes(name)) continue
      firstLoad.add(name)
      // Static imports only. A dynamic import() runs when its code path runs.
      stack.push(...[...source(name).matchAll(/(?:from|import)\s*"\.\/([\w-]+\.js)"/g)].map(match => match[1]))
    }
    const loadedMaps = [...firstLoad].filter(name => mapChunks.has(name)).map(name => mapChunks.get(name))
    const prefetchedMaps = prefetched.filter(name => mapChunks.has(name)).map(name => mapChunks.get(name))
    console.log(`${path}: first-load JavaScript ${firstLoad.size} files, ${kb(gzip(firstLoad))}`)
    assert.deepEqual(loadedMaps, [], `${path} loads map data at first paint: ${loadedMaps.join(', ')}`)
    assert.deepEqual(prefetchedMaps, [], `${path} prefetches map data: ${prefetchedMaps.join(', ')}`)
  }
  const sizes = [...mapChunks.keys()].map(name => gzip([name]))
  console.log(`Producer map chunks: ${mapChunks.size}, ${kb(Math.min(...sizes))} to ${kb(Math.max(...sizes))}`)

  const page = await (await fetch(`${origin}/lineup/abrau-durso`)).text()
  assert(/class="plm product-line-map[^"]*"/.test(page), '/lineup/abrau-durso does not render the map on the server')
  const escaped = text => text.replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character])
  assert(page.includes(escaped(maps.find(map => map.producer.id === 'abrau-durso').products[0].name)), '/lineup/abrau-durso does not render its products on the server')
  console.log('/lineup/abrau-durso: the server renders the map.')
} finally {
  server.kill()
}
