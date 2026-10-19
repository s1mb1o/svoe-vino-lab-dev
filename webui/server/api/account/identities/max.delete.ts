import { unlinkMessengerRoute } from '../../../utils/account'
import { runtimeAccountConfig } from '../../../utils/account-runtime'

export default defineEventHandler(event => unlinkMessengerRoute(event, runtimeAccountConfig(event), 'max'))
