import { preferencesRoute } from '../../utils/taste'
import { runtimeAccountConfig } from '../../utils/account-runtime'

export default defineEventHandler(event => preferencesRoute(event, runtimeAccountConfig(event)))
