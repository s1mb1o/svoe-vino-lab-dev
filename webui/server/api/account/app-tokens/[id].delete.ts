import { appTokenRevokeRoute } from '../../../utils/account'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => appTokenRevokeRoute(event, runtimeAccountConfig(event), getRouterParam(event, 'id')))
