import { savedPutRoute } from '../../../utils/diary'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => savedPutRoute(event, runtimeAccountConfig(event), getRouterParam(event, 'slug')))
