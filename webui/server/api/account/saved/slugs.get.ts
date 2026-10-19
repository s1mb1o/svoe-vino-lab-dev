import { savedSlugsRoute } from '../../../utils/diary'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => savedSlugsRoute(event, runtimeAccountConfig(event)))
