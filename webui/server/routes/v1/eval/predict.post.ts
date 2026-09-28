import { readImage, predict, predictionMode } from '../../../utils/prediction'

export default defineEventHandler(async event => {
  const config = useRuntimeConfig(event)
  const mode = predictionMode(config.predictionMode)
  setHeader(event, 'Cache-Control', 'no-store')
  setHeader(event, 'X-Prediction-Mode', mode)
  const file = await readImage(event)
  const controller = new AbortController()
  const disconnect = () => { if (!event.node.res.writableEnded) controller.abort() }
  event.node.res.once('close', disconnect)
  try { return await predict(file, mode, config.predictionEndpoint, 8000, controller.signal) }
  finally { event.node.res.off('close', disconnect) }
})
