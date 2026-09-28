import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { createServer, type Server } from 'node:http'
import { readFileSync } from 'node:fs'
import { Buffer } from 'node:buffer'
import { createApp, eventHandler, toNodeListener } from 'h3'
import { predict, readImage, predictionMode } from '../server/utils/prediction'
import { MOCK_SLUG } from '../shared/catalog'

let server: Server
let origin: string
let received: { key: string; type: string; size: number }[] = []
const fixture = readFileSync('public/wines/priboj-marchenko-beloe-polusuhoe.webp')
const file = () => new File([fixture], 'label.webp', { type: 'image/webp' })

beforeAll(async () => {
  const app = createApp()
  app.use('/upload', eventHandler(async event => {
    const uploaded = await readImage(event)
    return predict(uploaded, 'mock', '')
  }))
  server = createServer((req, res) => {
    if (req.url?.startsWith('/upload')) { toNodeListener(app)(req, res); return }
    if (req.url === '/timeout') return
    if (req.url === '/redirect') { res.writeHead(302, { location: '/valid' }); res.end(); return }
    if (req.url === '/fail') { res.writeHead(500); res.end(); return }
    if (req.url === '/wrong-status') { res.writeHead(202); res.end('{"slug":"queued"}'); return }
    const chunks: Buffer[] = []
    req.on('data', chunk => chunks.push(chunk))
    req.on('end', async () => {
      const form = await new Response(Buffer.concat(chunks), { headers: { 'content-type': req.headers['content-type']! } }).formData()
      received = [...form.entries()].map(([key, value]) => ({ key, type: typeof value === 'string' ? 'text' : value.type, size: typeof value === 'string' ? value.length : value.size }))
      res.setHeader('Content-Type', 'application/json')
      if (req.url === '/bad-json') res.end('not json')
      else if (req.url === '/empty') res.end('{"slug":""}')
      else if (req.url === '/wrong-key') res.end('{"wine_slug":"wrong"}')
      else if (req.url === '/large') res.end('x'.repeat(70 * 1024))
      else if (req.url === '/array') { res.writeHead(201); res.end('[{"slug":"Exact-Slug_2024"}]') }
      else res.end('{"slug":"Exact-Slug_2024"}')
    })
  })
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
  const address = server.address()
  if (!address || typeof address === 'string') throw new Error('No test port')
  origin = `http://127.0.0.1:${address.port}`
})
afterAll(async () => { server.closeAllConnections(); await new Promise<void>(resolve => server.close(() => resolve())) })

describe('prediction provider', () => {
  it('returns the declared demo result without an upstream', async () => {
    expect(await predict(file(), 'mock', '')).toEqual({ slug: MOCK_SLUG })
  })
  it.each(['/valid', '/array'])('forwards only image and preserves the exact returned slug: %s', async path => {
    expect(await predict(file(), 'upstream', origin + path)).toEqual({ slug: 'Exact-Slug_2024' })
    expect(received).toEqual([{ key: 'image', type: 'image/webp', size: fixture.length }])
  })
  it.each(['/fail', '/redirect', '/bad-json', '/empty', '/wrong-key', '/large', '/wrong-status'])('does not substitute mock output for %s', async path => {
    await expect(predict(file(), 'upstream', origin + path)).rejects.toMatchObject({ statusCode: 502 })
  })
  it('bounds the complete upstream request time', async () => {
    await expect(predict(file(), 'upstream', origin + '/timeout', 40)).rejects.toMatchObject({ statusCode: 504 })
  })
  it('propagates cancellation to a pending upstream request', async () => {
    const controller = new AbortController()
    const pending = predict(file(), 'upstream', origin + '/timeout', 8000, controller.signal)
    setTimeout(() => controller.abort(), 20)
    await expect(pending).rejects.toMatchObject({ statusCode: 504 })
  })
  it('rejects invalid deployment configuration', async () => {
    expect(() => predictionMode('typo')).toThrow()
    await expect(predict(file(), 'upstream', 'file:///etc/passwd')).rejects.toMatchObject({ statusCode: 503 })
  })
})

describe('upload validation over HTTP', () => {
  it('accepts a real WebP with the official field name', async () => {
    const body = new FormData(); body.set('image', file())
    const response = await fetch(origin + '/upload', { method: 'POST', body })
    expect(response.status).toBe(200)
    expect(await response.json()).toEqual({ slug: MOCK_SLUG })
  })
  it('rejects multiple image files', async () => {
    const body = new FormData(); body.append('image', file()); body.append('image', file())
    expect((await fetch(origin + '/upload', { method: 'POST', body })).status).toBe(400)
  })
  it('rejects a renamed non-image despite its claimed MIME type', async () => {
    const body = new FormData(); body.set('image', new File(['not an image'], 'fake.jpg', { type: 'image/jpeg' }))
    expect((await fetch(origin + '/upload', { method: 'POST', body })).status).toBe(415)
  })
  it('rejects wrong field names and string fields', async () => {
    const wrong = new FormData(); wrong.set('photo', file())
    expect((await fetch(origin + '/upload', { method: 'POST', body: wrong })).status).toBe(400)
    expect((await fetch(origin + '/upload', { method: 'POST', body: new FormData() })).status).toBe(400)
    const body = new FormData(); body.set('image', 'not a file')
    expect((await fetch(origin + '/upload', { method: 'POST', body })).status).toBe(400)
  })
  it('rejects oversized uploads before forwarding them', async () => {
    const body = new FormData(); body.set('image', new File([new Uint8Array(10 * 1024 * 1024 + 1)], 'large.jpg', { type: 'image/jpeg' }))
    expect((await fetch(origin + '/upload', { method: 'POST', body })).status).toBe(413)
  })
})
