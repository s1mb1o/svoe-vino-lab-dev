import { MAX_IMAGE_BYTES } from '#shared/catalog'
import { predictionMode } from '../utils/prediction'

export default defineEventHandler(event => {
  setHeader(event, 'Cache-Control', 'no-store')
  const config = useRuntimeConfig(event)
  return { predictionMode: predictionMode(config.predictionMode), catalogMode: 'demo', maxImageBytes: MAX_IMAGE_BYTES, shelfAvailable: config.shelfMode === 'enabled' && Boolean(process.env.SAM3_ENDPOINT) }
})
