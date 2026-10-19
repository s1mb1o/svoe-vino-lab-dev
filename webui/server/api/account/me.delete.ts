import { deleteMeRoute } from '../../utils/account'
import { runtimeAccountConfig } from '../../utils/account-runtime'

export default defineEventHandler(event => deleteMeRoute(event, runtimeAccountConfig(event)))
