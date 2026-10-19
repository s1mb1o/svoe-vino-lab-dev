import { emailVerifyRoute } from '../../../utils/account'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => emailVerifyRoute(event, runtimeAccountConfig(event)))
