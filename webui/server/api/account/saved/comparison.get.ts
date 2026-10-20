import { savedComparisonRoute } from '../../../utils/diary'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => savedComparisonRoute(event, runtimeAccountConfig(event)))
