import { createGlobusClient, globusStores } from '../../utils/globus'

export default defineEventHandler(async event => {
  setHeader(event, 'Cache-Control', 'no-store')
  return { provider: 'globus', stores: await globusStores(createGlobusClient()) }
})
