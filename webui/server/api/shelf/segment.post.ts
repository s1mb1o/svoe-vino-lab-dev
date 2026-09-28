import { readImage } from '../../utils/prediction'
import { requireShelfMode, segmentShelf } from '../../utils/shelf'

export default defineEventHandler(async event => {
  setHeader(event, 'Cache-Control', 'no-store')
  requireShelfMode(useRuntimeConfig(event).shelfMode)
  const file = await readImage(event)
  const controller = new AbortController()
  const disconnect = () => { if (!event.node.res.writableEnded) controller.abort() }
  event.node.res.once('close', disconnect)
  try { return await segmentShelf(file, { endpoint: process.env.SAM3_ENDPOINT || '', signal: controller.signal }) }
  finally { event.node.res.off('close', disconnect) }
})
