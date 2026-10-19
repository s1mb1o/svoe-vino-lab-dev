import { historyDeleteDayRoute } from '../../../../../utils/diary'
import { runtimeAccountConfig } from '../../../../../utils/account-runtime'

export default defineEventHandler(event => historyDeleteDayRoute(event, runtimeAccountConfig(event), getRouterParam(event, 'slug'), getRouterParam(event, 'day')))
