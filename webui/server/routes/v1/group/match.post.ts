import { readImage, predictionMode } from '../../../utils/prediction'
import { matchGroup } from '../../../utils/group'

export default defineEventHandler(async event => {
  const config = useRuntimeConfig(event)
  if (predictionMode(config.predictionMode) !== 'upstream') throw createError({ statusCode: 503, statusMessage: 'Group matching requires the upstream matcher' })
  setHeader(event, 'Cache-Control', 'no-store')
  const file = await readImage(event)
  const controller = new AbortController()
  const disconnect = () => { if (!event.node.res.writableEnded) controller.abort() }
  event.node.res.once('close', disconnect)
  try { return await matchGroup(file, config.predictionEndpoint, { signal: controller.signal }) }
  finally { event.node.res.off('close', disconnect) }
})
