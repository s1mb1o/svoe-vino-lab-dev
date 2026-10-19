import { savedListRoute } from '../../../utils/diary'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => savedListRoute(event, runtimeAccountConfig(event)))
