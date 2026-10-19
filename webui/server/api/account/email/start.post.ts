import { emailStartRoute } from '../../../utils/account'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => emailStartRoute(event, runtimeAccountConfig(event)))
