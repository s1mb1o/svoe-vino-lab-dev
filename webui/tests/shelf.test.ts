import { describe, expect, it, vi } from 'vitest'
import wines from '../server/data/wines.json'
import { groupMatchUrl, hasGroupMatchEndpoint, matchGroup } from '../server/utils/group'
import { groupCandidateWine, validBox, validShelfResult } from '../shared/shelf'

const wine = wines[0]!
const fixture = {
  pipeline: 'sam3+matcher',
  latency_ms: 842.4,
  image: { width: 60, height: 40, preview: 'data:image/jpeg;base64,/9j/2Q==' },
  detected_count: 1,
  truncated: false,
  bottles: [{
    id: 'b1',
    segmentation_score: 0.93,
    box: [0.1, 0.05, 0.4, 0.95],
    mask: 'data:image/png;base64,eA==',
    match: {
      rank: 1,
      slug: wine.slug,
      score: 0.89,
      wine: {
        name: wine.name,
        page_url: wine.source,
        producer: wine.producer,
        category: wine.category,
        region: wine.region,
        color: wine.color,
        grapes: wine.grapes.join(', '),
        sugar: wine.category,
        image_url: wine.image,
        qr_urls: [],
      },
    },
  }],
}
const endpoint = 'http://matcher.test/upstream/v1/eval/predict'
const photo = () => new File(['image'], 'shelf.jpg', { type: 'image/jpeg' })

describe('shelf group-match proxy', () => {
  it('derives the group route from the configured prediction endpoint', () => {
    expect(groupMatchUrl(endpoint).href).toBe('http://matcher.test/upstream/v1/group/match')
    expect(groupMatchUrl('https://matcher.test/v1/eval/predict/').href).toBe('https://matcher.test/v1/group/match')
    expect(hasGroupMatchEndpoint(endpoint)).toBe(true)
  })

  it.each(['', 'not-a-url', 'ftp://matcher.test/v1/eval/predict', 'http://matcher.test/v1/group/match', 'http://matcher.test/v1/eval/predict?token=x'])('rejects an unusable prediction endpoint: %s', value => {
    expect(hasGroupMatchEndpoint(value)).toBe(false)
    expect(() => groupMatchUrl(value)).toThrowError(expect.objectContaining({ statusCode: 503 }))
  })

  it('forwards the image to the derived route and validates the response', async () => {
    const request = vi.fn().mockResolvedValue(Response.json(fixture))

    const result = await matchGroup(photo(), endpoint, { fetch: request as typeof fetch })

    expect(result).toEqual(fixture)
    expect(request).toHaveBeenCalledTimes(1)
    const [url, options] = request.mock.calls[0]!
    expect((url as URL).href).toBe('http://matcher.test/upstream/v1/group/match')
    expect(options.method).toBe('POST')
    expect(options.redirect).toBe('error')
    expect((options.body as FormData).get('image')).toBeInstanceOf(File)
  })

  it.each([400, 401, 408, 413, 415, 502, 503, 504])('preserves actionable upstream status %i', async status => {
    const request = vi.fn().mockResolvedValue(new Response('', { status }))
    await expect(matchGroup(photo(), endpoint, { fetch: request })).rejects.toMatchObject({ statusCode: status })
  })

  it('maps an unexpected upstream status to 502', async () => {
    const request = vi.fn().mockResolvedValue(new Response('', { status: 429 }))
    await expect(matchGroup(photo(), endpoint, { fetch: request })).rejects.toMatchObject({ statusCode: 502 })
  })

  it.each([
    ['bad-json', new Response('invalid')],
    ['bad-shape', Response.json({ ...fixture, detected_count: 0 })],
    ['bad-mask', Response.json({ ...fixture, bottles: [{ ...fixture.bottles[0], mask: 'data:image/png;base64,!!!' }] })],
    ['too-large', new Response('{}', { headers: { 'content-length': String(13 * 1024 * 1024) } })],
  ])('rejects invalid matcher data: %s', async (_name, response) => {
    const request = vi.fn().mockResolvedValue(response)
    await expect(matchGroup(photo(), endpoint, { fetch: request })).rejects.toMatchObject({ statusCode: 502 })
  })

  it('reports timeout when the matcher does not respond', async () => {
    const request = vi.fn((_url: URL, options: RequestInit) => new Promise<Response>((_resolve, reject) => {
      options.signal!.addEventListener('abort', () => reject(new Error('aborted')))
    }))
    await expect(matchGroup(photo(), endpoint, { fetch: request as typeof fetch, timeout: 20 })).rejects.toMatchObject({ statusCode: 504 })
    expect(request).toHaveBeenCalledTimes(1)
  })

  it('converts a matcher wine card for the existing result experience', () => {
    const result = groupCandidateWine(fixture.bottles[0]!.match)
    expect(result).toMatchObject({ slug: wine.slug, name: wine.name, source: wine.source, grapes: wine.grapes })
  })

  it('validates normalized hit areas and complete matcher responses', () => {
    expect(validShelfResult(fixture)).toBe(true)
    expect(validBox([0, 0.2, 1, 0.9])).toBe(true)
    for (const box of [[0, 0, 2, 1], [1, 1, 0, 0], [0, Number.NaN, 1, 1]]) expect(validBox(box)).toBe(false)
    for (const value of [null, {}, { ...fixture, pipeline: '' }, { ...fixture, bottles: [null] }]) expect(validShelfResult(value)).toBe(false)
  })
})
