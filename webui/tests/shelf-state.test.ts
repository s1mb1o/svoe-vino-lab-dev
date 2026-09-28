import { afterEach, describe, expect, it, vi } from 'vitest'
import { effectScope, type EffectScope } from 'vue'
import { useShelfScanner } from '../app/composables/useShelfScanner'
import wines from '../server/data/wines.json'
import { MAX_IMAGE_BYTES } from '../shared/catalog'

const scopes: EffectScope[] = []
const preview = 'data:image/jpeg;base64,/9j/2Q=='
const mask = 'data:image/png;base64,eA=='
const matchedWine = wines[0]!
const match = {
  rank: 1,
  slug: matchedWine.slug,
  score: 0.91,
  wine: {
    name: matchedWine.name,
    page_url: matchedWine.source,
    producer: matchedWine.producer,
    category: matchedWine.category,
    region: matchedWine.region,
    color: matchedWine.color,
    grapes: matchedWine.grapes.join(', '),
    sugar: matchedWine.category,
    image_url: matchedWine.image,
    qr_urls: [],
  },
}
const shelf = {
  pipeline: 'sam3+matcher',
  latency_ms: 1250,
  image: { width: 60, height: 40, preview },
  bottles: [
    { id: 'b1', segmentation_score: 0.94, box: [0, 0.1, 0.3, 0.9], mask, match },
    { id: 'b2', segmentation_score: 0.88, box: [0.5, 0.1, 0.8, 0.9], mask, match: null },
  ],
  detected_count: 2,
  truncated: false,
}
const photo = () => new File(['image'], 'shelf.jpg', { type: 'image/jpeg' })

function setup(request: ReturnType<typeof vi.fn>) {
  const scope = effectScope()
  scopes.push(scope)
  const release = vi.fn()
  const scanner = scope.run(() => useShelfScanner({ fetch: request as typeof fetch, createObjectURL: () => 'blob:example', revokeObjectURL: release }))!
  return { scanner, release, scope }
}

afterEach(() => scopes.splice(0).forEach(scope => scope.stop()))

describe('shelf UI state', () => {
  it('matches the group once and opens ready bottle results without another request', async () => {
    const request = vi.fn().mockResolvedValueOnce(Response.json(shelf))
    const { scanner } = setup(request)

    await scanner.select([photo()])

    expect(request).toHaveBeenCalledTimes(1)
    expect(request.mock.calls[0]![0]).toBe('/v1/group/match')
    expect(scanner.selectedId.value).toBe('')

    scanner.selectBottle('b1')

    expect(request).toHaveBeenCalledTimes(1)
    expect(scanner.selectedWine.value?.name).toBe(matchedWine.name)
    expect(scanner.selectedMatch.value?.slug).toBe(matchedWine.slug)
    expect(scanner.portalUrl.value).toBe(matchedWine.source)
    scanner.closeBottle()
    expect(scanner.selectedId.value).toBe('')
    expect(scanner.result.value?.bottles).toHaveLength(2)
  })

  it('opens an unmatched bottle without inventing a wine', async () => {
    const request = vi.fn().mockResolvedValueOnce(Response.json(shelf))
    const { scanner } = setup(request)
    await scanner.select([photo()])

    scanner.selectBottle('b2')

    expect(scanner.selectedMatch.value).toBeNull()
    expect(scanner.selectedWine.value).toBeNull()
    expect(request).toHaveBeenCalledTimes(1)
  })

  it('rejects unknown bottle IDs before changing popup state', async () => {
    const request = vi.fn().mockResolvedValueOnce(Response.json(shelf))
    const { scanner } = setup(request)
    await scanner.select([photo()])

    expect(() => scanner.selectBottle('other')).toThrow()
    expect(scanner.selectedId.value).toBe('')
    expect(request).toHaveBeenCalledTimes(1)
  })

  it('suppresses old group-match results after replacement', async () => {
    let finish!: (response: Response) => void
    const empty = { ...shelf, bottles: [], detected_count: 0 }
    const request = vi.fn().mockImplementationOnce(() => new Promise(resolve => { finish = resolve })).mockResolvedValueOnce(Response.json(empty))
    const { scanner, release } = setup(request)

    const old = scanner.select([photo()])
    await scanner.select([photo()])
    finish(Response.json(shelf))
    await old

    expect(request.mock.calls[0]![1].signal.aborted).toBe(true)
    expect(scanner.result.value?.bottles).toEqual([])
    expect(release).toHaveBeenCalledTimes(1)
  })

  it('clears the selected match and group result on mode unmount', async () => {
    const request = vi.fn().mockResolvedValueOnce(Response.json(shelf))
    const { scanner, scope } = setup(request)
    await scanner.select([photo()])
    scanner.selectBottle('b1')

    scope.stop()

    expect(scanner.selectedId.value).toBe('')
    expect(scanner.result.value).toBeNull()
    expect(scanner.selectedMatch.value).toBeNull()
    expect(request).toHaveBeenCalledTimes(1)
  })

  it('cancels processing without discarding the photo needed for retry', async () => {
    let finish!: (response: Response) => void
    const request = vi.fn().mockImplementationOnce(() => new Promise(resolve => { finish = resolve })).mockResolvedValueOnce(Response.json(shelf))
    const { scanner } = setup(request)
    const first = scanner.select([photo()])
    scanner.cancel()
    finish(Response.json(shelf))
    await first

    expect(scanner.phase.value).toBe('selected')
    expect(scanner.result.value).toBeNull()
    await scanner.submit()
    expect(scanner.phase.value).toBe('ready')
  })

  it('uses the public example through the same group-match route', async () => {
    const request = vi.fn().mockResolvedValueOnce(new Response('example')).mockResolvedValueOnce(Response.json(shelf))
    const { scanner } = setup(request)
    await scanner.example()

    expect(request.mock.calls.map(call => call[0])).toEqual(['/reference/shelf-example.jpg', '/v1/group/match'])
    expect(scanner.phase.value).toBe('ready')
  })

  it('does not substitute demo results after a service failure', async () => {
    const { scanner } = setup(vi.fn().mockResolvedValueOnce(Response.json({}, { status: 502 })))
    await scanner.select([photo()])
    expect(scanner.phase.value).toBe('error')
    expect(scanner.result.value).toBeNull()
  })

  it('rejects invalid mask data before a user can open a result', async () => {
    const invalid = { ...shelf, bottles: [{ ...shelf.bottles[0], mask: 'data:image/png;base64,!!!' }] }
    const { scanner } = setup(vi.fn().mockResolvedValueOnce(Response.json(invalid)))
    await scanner.select([photo()])
    expect(scanner.phase.value).toBe('error')
    expect(scanner.result.value).toBeNull()
  })

  it('rejects multiple, empty, unsupported, and oversized photos before requests', async () => {
    const request = vi.fn()
    const { scanner } = setup(request)
    const invalid = [
      [photo(), photo()],
      [new File([], 'empty.jpg')],
      [new File(['x'], 'x.heic', { type: 'image/heic' })],
      [new File([new Uint8Array(MAX_IMAGE_BYTES + 1)], 'big.jpg', { type: 'image/jpeg' })],
    ]
    for (const files of invalid) {
      await scanner.select(files)
      expect(scanner.phase.value).toBe('error')
    }
    expect(request).not.toHaveBeenCalled()
  })
})
