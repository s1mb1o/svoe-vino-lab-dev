import { afterEach, describe, expect, it, vi } from 'vitest'
import { effectScope, ref, type EffectScope } from 'vue'
import { useShelfScanner } from '../app/composables/useShelfScanner'
import wines from '../server/data/wines.json'
import { MAX_IMAGE_BYTES } from '../shared/catalog'
const scopes: EffectScope[] = []
const crop = 'data:image/jpeg;base64,/9j/2Q=='
const shelf = { image: { width: 60, height: 40, preview: crop }, bottles: [{ id: 'b1', box: [0, .1, .3, .9], mask: 'data:image/png;base64,eA==', crop }, { id: 'b2', box: [.5, .1, .8, .9], mask: 'data:image/png;base64,eA==', crop }], detectedCount: 2, truncated: false }
const photo = () => new File(['image'], 'shelf.jpg', { type: 'image/jpeg' })
function setup(request: ReturnType<typeof vi.fn>) {
  const scope = effectScope(); scopes.push(scope)
  const release = vi.fn()
  const scanner = scope.run(() => useShelfScanner(ref('mock'), { fetch: request as typeof fetch, createObjectURL: () => 'blob:example', revokeObjectURL: release }))!
  return { scanner, release, scope }
}
afterEach(() => scopes.splice(0).forEach(s => s.stop()))

describe('shelf UI state', () => {
  it('segments once and defers recognition until a specific bottle is selected', async () => {
    const request = vi.fn().mockResolvedValueOnce(Response.json(shelf)).mockResolvedValueOnce(Response.json({ slug: wines[0]!.slug })).mockResolvedValueOnce(Response.json(wines[0]))
    const { scanner } = setup(request)
    await scanner.select([photo()])
    expect(request).toHaveBeenCalledTimes(1)
    expect(request.mock.calls[0]![0]).toBe('/api/shelf/segment')
    expect(scanner.selectedId.value).toBe('')
    await scanner.selectBottle('b2')
    expect(scanner.selectedId.value).toBe('b2')
    expect(request.mock.calls[1]![0]).toBe('/v1/eval/predict')
    expect(request.mock.calls[1]![1].body.get('image').name).toBe('b2.jpg')
    expect(scanner.wineScanner.wine.value?.name).toBe(wines[0]!.name)
    expect(scanner.wineScanner.mock.value).toBe(true)
    scanner.closeBottle()
    expect(scanner.selectedId.value).toBe('')
    expect(scanner.result.value?.bottles).toHaveLength(2)
    expect(scanner.wineScanner.file.value).toBeNull()
  })
  it('rejects unknown bottle IDs before changing popup state', async () => {
    const request = vi.fn().mockResolvedValueOnce(Response.json(shelf))
    const { scanner } = setup(request); await scanner.select([photo()])
    await expect(scanner.selectBottle('other')).rejects.toThrow()
    expect(scanner.selectedId.value).toBe(''); expect(request).toHaveBeenCalledTimes(1)
  })
  it('suppresses old segmentation results after replacement', async () => {
    let finish!: (r: Response) => void
    const request = vi.fn().mockImplementationOnce(() => new Promise(r => { finish = r })).mockResolvedValueOnce(Response.json({ ...shelf, bottles: [], detectedCount: 0 }))
    const { scanner, release } = setup(request)
    const old = scanner.select([photo()]); await scanner.select([photo()])
    finish(Response.json(shelf)); await old
    expect(request.mock.calls[0]![1].signal.aborted).toBe(true)
    expect(scanner.result.value?.bottles).toEqual([])
    expect(release).toHaveBeenCalledTimes(1)
  })
  it('closes the popup and cancels selected-bottle recognition on mode unmount', async () => {
    let finish!: (r: Response) => void
    const request = vi.fn().mockResolvedValueOnce(Response.json(shelf)).mockImplementationOnce(() => new Promise(r => { finish = r }))
    const { scanner, scope } = setup(request); await scanner.select([photo()])
    const pending = scanner.selectBottle('b1'); scope.stop(); finish(Response.json({ slug: wines[0]!.slug })); await pending
    expect(scanner.selectedId.value).toBe(''); expect(scanner.result.value).toBeNull()
    expect(scanner.wineScanner.slug.value).toBe('')
    expect(request.mock.calls[1]![1].signal.aborted).toBe(true)
  })
  it('cancels processing without discarding the photo needed for retry', async () => {
    let finish!: (r: Response) => void
    const request = vi.fn().mockImplementationOnce(() => new Promise(r => { finish = r })).mockResolvedValueOnce(Response.json(shelf))
    const { scanner } = setup(request); const first = scanner.select([photo()]); scanner.cancel(); finish(Response.json(shelf)); await first
    expect(scanner.phase.value).toBe('selected'); expect(scanner.result.value).toBeNull()
    await scanner.submit(); expect(scanner.phase.value).toBe('ready')
  })
  it('uses the public example through the same portal segmentation flow', async () => {
    const request = vi.fn().mockResolvedValueOnce(new Response('example')).mockResolvedValueOnce(Response.json(shelf))
    const { scanner } = setup(request); await scanner.example()
    expect(request.mock.calls.map(c => c[0])).toEqual(['/reference/shelf-example.jpg', '/api/shelf/segment'])
    expect(scanner.phase.value).toBe('ready')
  })
  it('does not substitute demo boxes after a service failure', async () => {
    const { scanner } = setup(vi.fn().mockResolvedValueOnce(Response.json({}, { status: 502 })))
    await scanner.select([photo()]); expect(scanner.phase.value).toBe('error'); expect(scanner.result.value).toBeNull()
  })
  it('rejects invalid crop data before a user can open it', async () => {
    const invalid = { ...shelf, bottles: [{ ...shelf.bottles[0], crop: 'data:image/jpeg;base64,!!!' }] }
    const { scanner } = setup(vi.fn().mockResolvedValueOnce(Response.json(invalid)))
    await scanner.select([photo()])
    expect(scanner.phase.value).toBe('error'); expect(scanner.result.value).toBeNull()
  })
  it('rejects multiple, empty, unsupported, and oversized photos before requests', async () => {
    const request = vi.fn(); const { scanner } = setup(request)
    for (const files of [[photo(), photo()], [new File([], 'empty.jpg')], [new File(['x'], 'x.heic', { type: 'image/heic' })], [new File([new Uint8Array(MAX_IMAGE_BYTES + 1)], 'big.jpg', { type: 'image/jpeg' })]]) {
      await scanner.select(files); expect(scanner.phase.value).toBe('error')
    }
    expect(request).not.toHaveBeenCalled()
  })
})
