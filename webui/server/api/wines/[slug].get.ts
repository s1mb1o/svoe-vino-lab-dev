import wines from '../../data/wines.json'
export default defineEventHandler(event => {
  const wine = wines.find(wine => wine.slug === getRouterParam(event, 'slug'))
  if (!wine) throw createError({ statusCode: 404, statusMessage: 'Wine is not in the demo catalog' })
  return wine
})
