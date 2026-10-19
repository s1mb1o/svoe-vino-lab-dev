import { yandexStartRoute } from '../../../utils/account'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => yandexStartRoute(event, runtimeAccountConfig(event)))
