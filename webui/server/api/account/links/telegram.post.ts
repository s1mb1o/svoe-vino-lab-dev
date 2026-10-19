import { telegramLinkRoute } from '../../../utils/account'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => telegramLinkRoute(event, runtimeAccountConfig(event)))
