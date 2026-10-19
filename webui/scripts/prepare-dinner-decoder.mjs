import assert from 'node:assert/strict'
import { copyFile, mkdir, readFile } from 'node:fs/promises'

const upstream = new URL('../node_modules/heic-to/', import.meta.url)
const version = JSON.parse(await readFile(new URL('package.json', upstream))).version
assert.equal(version, '1.6.6', 'Review the worker URL and source notice when upgrading the decoder')
const destination = new URL('../public/third-party/heic-to-1.6.6/', import.meta.url)
await mkdir(destination, { recursive: true })
await copyFile(new URL('dist/csp/heic-to.js', upstream), new URL('heic-to.js', destination))
