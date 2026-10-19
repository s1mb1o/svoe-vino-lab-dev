import { accountConfigRoute } from '../../utils/account'
import { runtimeAccountConfig } from '../../utils/account-runtime'

export default defineEventHandler(event => accountConfigRoute(event, runtimeAccountConfig(event)))
