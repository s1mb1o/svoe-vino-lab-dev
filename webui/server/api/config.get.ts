import { MAX_IMAGE_BYTES } from '#shared/catalog'
import { predictionMode } from '../utils/prediction'
import { hasGroupMatchEndpoint } from '../utils/group'
import { predictionApiAvailable } from '../utils/upstream-health'

export default defineEventHandler(async event => {
  setHeader(event, 'Cache-Control', 'no-store')
  const config = useRuntimeConfig(event)
  const mode = predictionMode(config.predictionMode)
  const apiAvailable = mode === 'mock' || await predictionApiAvailable(config.predictionEndpoint)
  return {
    predictionMode: mode,
    apiAvailable,
    catalogMode: 'source-fallback',
    maxImageBytes: MAX_IMAGE_BYTES,
    shelfAvailable: apiAvailable && mode === 'upstream' && hasGroupMatchEndpoint(config.predictionEndpoint),
  }
})
