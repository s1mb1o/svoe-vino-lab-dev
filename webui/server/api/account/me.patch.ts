import { settingsRoute } from '../../utils/diary'
import { runtimeAccountConfig } from '../../utils/account-runtime'

export default defineEventHandler(event => settingsRoute(event, runtimeAccountConfig(event)))
