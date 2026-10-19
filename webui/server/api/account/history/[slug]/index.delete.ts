import { historyDeleteWineRoute } from '../../../../utils/diary'
import { runtimeAccountConfig } from '../../../../utils/account-runtime'

export default defineEventHandler(event => historyDeleteWineRoute(event, runtimeAccountConfig(event), getRouterParam(event, 'slug')))
