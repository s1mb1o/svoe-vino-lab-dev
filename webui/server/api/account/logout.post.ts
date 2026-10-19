import { logoutRoute } from '../../utils/account'
import { runtimeAccountConfig } from '../../utils/account-runtime'

export default defineEventHandler(event => logoutRoute(event, runtimeAccountConfig(event)))
