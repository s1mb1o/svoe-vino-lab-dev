import { maxQrRoute } from '../../../utils/account'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => maxQrRoute(event, runtimeAccountConfig(event)))
