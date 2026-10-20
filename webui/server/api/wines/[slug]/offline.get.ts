import { publicWine } from '#shared/alternatives'
import { alternativeVersion, alternativeWine } from '../../../utils/alternative-catalog'

export default defineEventHandler(event => {
  setHeader(event, 'Cache-Control', 'no-store')
  const slug = getRouterParam(event, 'slug') || ''
  if (!/^[a-z0-9][a-z0-9_-]{0,199}$/.test(slug)) throw createError({ statusCode: 400, statusMessage: 'Invalid wine ID' })
  const wine = alternativeWine(slug)
  if (!wine) throw createError({ statusCode: 404, statusMessage: 'Wine is absent from this catalog snapshot' })
  return { wine: publicWine(wine), version: alternativeVersion }
})
