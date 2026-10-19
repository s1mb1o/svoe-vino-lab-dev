import { appTokensRoute } from '../../../utils/account'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => appTokensRoute(event, runtimeAccountConfig(event)))
