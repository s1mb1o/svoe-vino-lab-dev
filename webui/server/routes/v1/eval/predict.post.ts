import { handlePrediction } from '../../../utils/prediction'

export default defineEventHandler(event => handlePrediction(event, useRuntimeConfig(event)))
