import wines from '../../data/wines.json'
import { fetchSourceWine } from '../../utils/wine-metadata'

export default defineEventHandler(async event => {
  const slug = getRouterParam(event, 'slug') || ''
  const local = wines.find(wine => wine.slug === slug)
  if (local) return local
  const wine = await fetchSourceWine(slug)
  if (!wine) throw createError({ statusCode: 404, statusMessage: 'Wine metadata is unavailable' })
  setHeader(event, 'Cache-Control', 'public, max-age=3600, stale-while-revalidate=86400, stale-if-error=86400')
  return wine
})
