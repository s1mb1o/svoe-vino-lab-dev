import { meRoute } from '../../utils/account'
import { runtimeAccountConfig } from '../../utils/account-runtime'

export default defineEventHandler(event => meRoute(event, runtimeAccountConfig(event)))
