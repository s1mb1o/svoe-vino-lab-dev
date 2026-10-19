import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFile, readdir } from 'node:fs/promises'

const files = await readdir(new URL('../.output/public/_nuxt/', import.meta.url))
const decoders = []
for (const name of files.filter(name => name.endsWith('.js'))) {
  const bytes = await readFile(new URL('../.output/public/_nuxt/' + name, import.meta.url))
  if (bytes.includes(Buffer.from('heif_context_read_from_memory'))) decoders.push({ name, size: bytes.length })
}
assert.equal(decoders.length, 0, 'The decoder must remain separately replaceable, not bundled into application chunks')
const sw = await readFile(new URL('../.output/public/sw.js', import.meta.url), 'utf8')
const version = JSON.parse(await readFile(new URL('../node_modules/heic-to/package.json', import.meta.url))).version
const decoderPath = `third-party/heic-to-${version}/heic-to.js`
const decoder = await readFile(new URL('../.output/public/' + decoderPath, import.meta.url))
const decoderSource = await readFile(new URL('../node_modules/heic-to/dist/csp/heic-to.js', import.meta.url))
assert(decoder.equals(decoderSource), 'Ship the library module byte-for-byte without application code')
assert(!sw.includes(decoderPath), 'The large decoder must not be precached')
const worker = files.find(name => name.startsWith('dinner-heic.worker-') && name.endsWith('.js'))
assert(worker)
const workerCode = await readFile(new URL('../.output/public/_nuxt/' + worker, import.meta.url), 'utf8')
assert(workerCode.includes('/' + decoderPath) && workerCode.includes('heic-to-NOTICE.txt'))
const upstream = await readFile(new URL('../node_modules/heic-to/LICENSE', import.meta.url))
const shipped = await readFile(new URL('../.output/public/third-party/heic-to-LICENSE.txt', import.meta.url))
assert(upstream.equals(shipped), 'Ship the exact upstream license')
const notice = await readFile(new URL('../.output/public/third-party/heic-to-NOTICE.txt', import.meta.url), 'utf8')
const gpl = await readFile(new URL('../.output/public/third-party/GPL-3.0.txt', import.meta.url), 'utf8')
assert(gpl.includes('GNU GENERAL PUBLIC LICENSE') && gpl.includes('Version 3'))
assert(notice.includes(version) && notice.includes('replaceable') && notice.includes('GPL-3.0.txt') && notice.includes('github.com/hoppergee/heic-to/tree/'))
console.log(JSON.stringify({ passed: true, decoder: decoderPath, bytes: decoder.length, unchanged: true, precached: false, version, licenseSha256: createHash('sha256').update(shipped).digest('hex') }))
