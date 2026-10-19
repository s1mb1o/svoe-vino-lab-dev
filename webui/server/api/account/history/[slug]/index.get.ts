import { historyItemRoute } from '../../../../utils/diary'
import { runtimeAccountConfig } from '../../../../utils/account-runtime'

export default defineEventHandler(event => historyItemRoute(event, runtimeAccountConfig(event), getRouterParam(event, 'slug')))
