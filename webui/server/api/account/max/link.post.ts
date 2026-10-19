import { maxLinkRoute } from '../../../utils/account'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => maxLinkRoute(event, runtimeAccountConfig(event)))
