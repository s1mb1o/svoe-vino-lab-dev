import wines from '../../data/wines.json'
import { createGlobusClient, recommendGlobus, validateFoodRequest } from '../../utils/globus'

export default defineEventHandler(async event => {
  setHeader(event, 'Cache-Control', 'no-store')
  if (!getHeader(event, 'content-type')?.startsWith('application/json')) throw createError({ statusCode: 415, statusMessage: 'Send JSON' })
  const chunks: Buffer[] = []
  let size = 0
  for await (const chunk of event.node.req) {
    size += chunk.length
    if (size > 2048) throw createError({ statusCode: 413, statusMessage: 'Request too large' })
    chunks.push(Buffer.from(chunk))
  }
  let body: unknown
  try { body = JSON.parse(Buffer.concat(chunks).toString('utf8')) }
  catch { throw createError({ statusCode: 400, statusMessage: 'Invalid JSON' }) }
  const { slug, selection } = validateFoodRequest(body)
  const wine = wines.find(w => w.slug === slug)
  if (!wine) throw createError({ statusCode: 422, statusMessage: 'Wine metadata is required for food recommendations' })
  const controller = new AbortController()
  const disconnect = () => { if (!event.node.res.writableEnded) controller.abort() }
  event.node.res.once('close', disconnect)
  try { return await recommendGlobus(wine, selection, createGlobusClient(fetch, AbortSignal.any([controller.signal, AbortSignal.timeout(20000)]))) }
  finally { event.node.res.off('close', disconnect) }
})
