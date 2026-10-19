import { historyRecordRoute } from '../../../utils/diary'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

// Only an upstream prediction is the person's wine: mock mode (or no valid mode) records nothing.
export default defineEventHandler(event => historyRecordRoute(event, runtimeAccountConfig(event), {
  mock: useRuntimeConfig(event).predictionMode !== 'upstream',
}))
