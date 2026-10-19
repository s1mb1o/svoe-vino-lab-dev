import { historyClearRoute } from '../../../utils/diary'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => historyClearRoute(event, runtimeAccountConfig(event)))
