import { yandexCallbackRoute } from '../../../utils/account'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => yandexCallbackRoute(event, runtimeAccountConfig(event)))
