import { signupRoute } from '../../utils/account'
import { runtimeAccountConfig } from '../../utils/account-runtime'

export default defineEventHandler(event => signupRoute(event, runtimeAccountConfig(event)))
