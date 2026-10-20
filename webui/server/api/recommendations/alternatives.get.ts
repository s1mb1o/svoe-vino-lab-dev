import { ALTERNATIVE_COLORS, ALTERNATIVE_SUGAR, rankAlternatives } from '#shared/alternatives'
import { alternativeCatalog, alternativeVersion, alternativeWine } from '../../utils/alternative-catalog'

export default defineEventHandler(event => {
  const query = getQuery(event)
  const allowed = ['slug', 'color', 'sweetness', 'sparkle']
  if (Object.keys(query).some(key => !allowed.includes(key)) || Object.values(query).some(value => typeof value !== 'string')) throw createError({ statusCode: 400, statusMessage: 'Invalid alternative query' })
  const { slug, color, sweetness, sparkle } = query as Record<string, string>
  if (!slug || !/^[a-z0-9][a-z0-9_-]{0,199}$/.test(slug)
    || (color && !ALTERNATIVE_COLORS.includes(color)) || (sweetness && !Object.hasOwn(ALTERNATIVE_SUGAR, sweetness))
    || (sparkle && !['still', 'sparkling'].includes(sparkle))) throw createError({ statusCode: 400, statusMessage: 'Invalid alternative filter' })
  const base = alternativeWine(slug)
  if (!base) throw createError({ statusCode: 404, statusMessage: 'Wine is absent from this catalog snapshot' })
  const results = rankAlternatives(base, alternativeCatalog, { color, sweetness, sparkle })
  setHeader(event, 'Cache-Control', 'no-store')
  return { base, results, version: alternativeVersion, explanation: results.length ? '' : !base.producerId ? 'Производитель исходного вина не подтверждён. Строгий подбор недоступен.' : 'В снимке каталога нет вин другого подтверждённого производителя с общими сортами и выбранными характеристиками.' }
})
