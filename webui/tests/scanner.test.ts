import { afterEach, describe, expect, it, vi } from 'vitest'
import { effectScope, ref, type EffectScope } from 'vue'
import { useWineScanner } from '../app/composables/useWineScanner'
import wines from '../server/data/wines.json'
import { MAX_IMAGE_BYTES, MOCK_SLUG, sourceWineUrl } from '../shared/catalog'

const scopes: EffectScope[] = []
const photo = (name = 'label.webp') => new File(['example image content'], name, { type: 'image/webp' })
const response = (value: unknown, status = 200) => Response.json(value, { status })
function setup(request: ReturnType<typeof vi.fn>, mode: 'mock' | 'upstream' | undefined = 'mock', metadataTimeout = 4000) {
  const scope = effectScope()
  scopes.push(scope)
  let sequence = 0
  const release = vi.fn()
  const scanner = scope.run(() => useWineScanner(ref(mode), { fetch: request as typeof fetch, createObjectURL: () => `blob:test-${++sequence}`, revokeObjectURL: release, metadataTimeout }))!
  return { scanner, release }
}
afterEach(() => { scopes.splice(0).forEach(scope => scope.stop()) })

describe('automatic photo search', () => {
  it('submits exactly once on selection and shows one source-linked bottle', async () => {
    const request = vi.fn().mockResolvedValueOnce(response({ slug: MOCK_SLUG })).mockResolvedValueOnce(response(wines[0]))
    const { scanner } = setup(request)
    await scanner.select([photo()])
    expect(request).toHaveBeenCalledTimes(2)
    const [url, options] = request.mock.calls[0]!
    expect(url).toBe('/api/predict')
    expect(options.method).toBe('POST')
    expect([...options.body.keys()]).toEqual(['image'])
    expect(options.body.get('image').name).toBe('label.webp')
    expect(scanner.phase.value).toBe('matched')
    expect(scanner.wine.value?.name).toBe(wines[0]!.name)
    expect(scanner.wine.value?.image).toBe(wines[0]!.image)
    expect(scanner.portalUrl.value).toBe(sourceWineUrl(MOCK_SLUG))
    expect(scanner.mock.value).toBe(true)
  })

  it.each(['404', '500', 'json', 'network', 'wrong-slug', 'timeout'])('keeps the prediction and portal link after metadata failure: %s', async failure => {
    const request = vi.fn().mockResolvedValueOnce(response({ slug: MOCK_SLUG }))
    if (failure === 'network') request.mockRejectedValueOnce(new TypeError('Network unavailable'))
    else if (failure === 'json') request.mockResolvedValueOnce(new Response('not-json'))
    else if (failure === 'wrong-slug') request.mockResolvedValueOnce(response(wines[1]))
    else if (failure === 'timeout') request.mockImplementationOnce((_url, options) => new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))))
    else request.mockResolvedValueOnce(response({}, Number(failure)))
    const { scanner } = setup(request, 'upstream', 5)
    await scanner.select([photo()])
    expect(scanner.phase.value).toBe('matched')
    expect(scanner.slug.value).toBe(MOCK_SLUG)
    expect(scanner.portalUrl.value).toBe(sourceWineUrl(MOCK_SLUG))
    expect(scanner.wine.value).toBeNull()
    expect(scanner.metadataUnavailable.value).toBe(true)
    expect(scanner.error.value).toBe('')
  })

  it('never lets a slow previous image replace a newer result', async () => {
    let finishOld!: (response: Response) => void
    const request = vi.fn()
      .mockImplementationOnce(() => new Promise(resolve => { finishOld = resolve }))
      .mockResolvedValueOnce(response({ slug: wines[1]!.slug }))
      .mockResolvedValueOnce(response(wines[1]))
    const { scanner, release } = setup(request)
    const first = scanner.select([photo('first.webp')])
    const firstSignal = request.mock.calls[0]![1].signal
    await scanner.select([photo('second.webp')])
    expect(firstSignal.aborted).toBe(true)
    finishOld(response({ slug: MOCK_SLUG }))
    await first
    expect(scanner.slug.value).toBe(wines[1]!.slug)
    expect(scanner.file.value?.name).toBe('second.webp')
    expect(release).toHaveBeenCalledWith('blob:test-1')
    expect(request).toHaveBeenCalledTimes(3)
  })

  it('cancels a request, suppresses its result, and supports retry of the same file', async () => {
    let finish!: (response: Response) => void
    const request = vi.fn().mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
      .mockResolvedValueOnce(response({ slug: MOCK_SLUG })).mockResolvedValueOnce(response(wines[0]))
    const { scanner, release } = setup(request)
    const pending = scanner.select([photo()])
    scanner.cancel()
    finish(response({ slug: MOCK_SLUG }))
    await pending
    expect(scanner.phase.value).toBe('selected')
    expect(scanner.slug.value).toBe('')
    await scanner.submit()
    expect(scanner.phase.value).toBe('matched')
    scanner.reset()
    expect(scanner.file.value).toBeNull()
    expect(scanner.portalUrl.value).toBe('')
    expect(release).toHaveBeenCalledTimes(1)
  })

  it('rejects invalid selections before sending requests', async () => {
    const request = vi.fn()
    const { scanner } = setup(request)
    for (const files of [[], [photo(), photo()], [new File([], 'empty.jpg')], [new File(['text'], 'text.txt', { type: 'text/plain' })], [new File([new Uint8Array(MAX_IMAGE_BYTES + 1)], 'large.jpg', { type: 'image/jpeg' })]]) {
      await scanner.select(files)
      expect(scanner.phase.value).toBe('error')
      expect(scanner.file.value).toBeNull()
    }
    expect(request).not.toHaveBeenCalled()
  })

  it('uses the same automatic upload path for the example', async () => {
    const request = vi.fn().mockResolvedValueOnce(new Response('public example image'))
      .mockResolvedValueOnce(response({ slug: MOCK_SLUG })).mockResolvedValueOnce(response(wines[0]))
    const { scanner } = setup(request)
    await scanner.example()
    expect(request.mock.calls.filter(call => call[0] === '/api/predict')).toHaveLength(1)
    expect(scanner.phase.value).toBe('matched')
    expect(scanner.exampleLoading.value).toBe(false)
  })

  it('shows missing configuration instead of silently leaving the upload idle', async () => {
    const request = vi.fn()
    const scope = effectScope(); scopes.push(scope)
    const unconfigured = scope.run(() => useWineScanner(ref(undefined), { fetch: request as typeof fetch, createObjectURL: () => 'blob:config', revokeObjectURL: () => {} }))!
    await unconfigured.select([photo()])
    expect(unconfigured.phase.value).toBe('error')
    expect(unconfigured.error.value).toContain('недоступен')
    expect(request).not.toHaveBeenCalled()
  })

  it('does not show a mock success after a failed real prediction', async () => {
    const request = vi.fn().mockResolvedValueOnce(response({}, 502))
    const { scanner } = setup(request, 'upstream')
    await scanner.select([photo()])
    expect(scanner.phase.value).toBe('error')
    expect(scanner.slug.value).toBe('')
    expect(scanner.wine.value).toBeNull()
    expect(scanner.mock.value).toBe(false)
  })
})
