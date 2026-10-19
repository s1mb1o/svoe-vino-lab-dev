import { appTokenCreateRoute } from '../../../utils/account'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => appTokenCreateRoute(event, runtimeAccountConfig(event)))
