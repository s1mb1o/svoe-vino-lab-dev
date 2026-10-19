import { historyListRoute } from '../../../utils/diary'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => historyListRoute(event, runtimeAccountConfig(event)))
