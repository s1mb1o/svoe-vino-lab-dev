import { describe, expect, it, vi } from 'vitest'
import { fetchSourceWine, normalizeSourceWine } from '../server/utils/wine-metadata'

const slug = 'massandra-muskat-rozovyy-pozdnego-sbora-rozovoe-sladkoe-10'
const source = {
  alcohol: 10,
  category: { name: 'Розовое сладкое' },
  color: 'Янтарно-розовый, насыщенный',
  description: 'Аромат тёплый.',
  dishes: [{ name: 'Выпечка и десерты' }, { name: 'Десерты' }],
  grapes: [{ name: 'Мускат' }],
  image: { altText: 'Мускат розовый позднего сбора', url: '/uploads/massandra_bottle.webp' },
  manufacturer: { name: 'Массандра', slug: 'massandra' },
  publicRating: 5,
  region: { name: 'Крым' },
  slug,
  temperature: '8-10',
  title: 'Мускат розовый позднего сбора',
}

describe('source wine metadata', () => {
  it('normalizes the official wine response for the result card', () => {
    expect(normalizeSourceWine(source, slug)).toEqual({
      slug,
      name: 'Мускат розовый позднего сбора',
      producer: 'Массандра',
      region: 'Крым',
      grapes: ['Мускат'],
      color: 'Розовое',
      category: 'сладкое',
      rating: 5,
      image: 'https://api.vino-svoe.ru/v1/img/str-api/640/640/resize/uploads/massandra_bottle.webp',
      alcohol: '10%',
      servingTemperature: '8-10°C',
      pairings: ['Выпечка и десерты', 'Десерты'],
      description: 'Аромат тёплый.',
      source: `https://vino-svoe.ru/wines/${slug}`,
    })
  })

  it.each([
    null,
    { ...source, slug: 'other' },
    { ...source, title: '' },
    { ...source, image: { url: 'https://evil.example/bottle.webp' } },
    { ...source, image: { url: '/uploads/../private/bottle.webp' } },
  ])('rejects invalid or untrusted source metadata', value => {
    expect(normalizeSourceWine(value, slug)).toBeNull()
  })

  it('loads one exact slug from the official JSON API', async () => {
    const request = vi.fn().mockResolvedValue(Response.json(source))
    const wine = await fetchSourceWine(slug, { fetch: request as typeof fetch })

    expect(wine?.slug).toBe(slug)
    expect(wine?.image).toContain('/resize/uploads/massandra_bottle.webp')
    expect(request).toHaveBeenCalledWith(`https://api.vino-svoe.ru/v1/wines/${slug}`, expect.objectContaining({
      headers: { accept: 'application/json' },
      redirect: 'error',
    }))
  })

  it('returns no metadata for a missing or invalid slug', async () => {
    const missing = vi.fn().mockResolvedValue(Response.json({}, { status: 404 }))
    await expect(fetchSourceWine('missing-wine', { fetch: missing as typeof fetch })).resolves.toBeNull()
    const unused = vi.fn()
    await expect(fetchSourceWine('//evil.example', { fetch: unused as typeof fetch })).resolves.toBeNull()
    expect(unused).not.toHaveBeenCalled()
  })

  it('maps invalid, oversized, and timed-out source responses to controlled errors', async () => {
    await expect(fetchSourceWine(slug, { fetch: vi.fn().mockResolvedValue(Response.json({ slug })) as typeof fetch })).rejects.toMatchObject({ statusCode: 502 })
    await expect(fetchSourceWine(slug, { fetch: vi.fn().mockResolvedValue(new Response('{}', { headers: { 'content-length': String(300 * 1024) } })) as typeof fetch })).rejects.toMatchObject({ statusCode: 502 })
    const waiting = vi.fn((_url, options) => new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))))
    await expect(fetchSourceWine(slug, { fetch: waiting as typeof fetch, timeoutMs: 5 })).rejects.toMatchObject({ statusCode: 504 })
  })
})
