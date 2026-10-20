import { PORTAL_UPSTREAM_TIMEOUT_MS } from '#shared/prediction'
import { handlePrediction } from '../utils/prediction'

export default defineEventHandler(event => handlePrediction(event, useRuntimeConfig(event), PORTAL_UPSTREAM_TIMEOUT_MS))
