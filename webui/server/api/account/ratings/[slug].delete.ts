import { ratingsRoute } from '../../../utils/taste'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => ratingsRoute(event, runtimeAccountConfig(event), getRouterParam(event, 'slug')))
