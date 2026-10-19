import { savedDeleteRoute } from '../../../utils/diary'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => savedDeleteRoute(event, runtimeAccountConfig(event), getRouterParam(event, 'slug')))
