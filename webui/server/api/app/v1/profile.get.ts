import { appReadRoute } from '../../../utils/account'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => appReadRoute(event, runtimeAccountConfig(event), 'profile'))
