import type { H3Event } from 'h3'
import { accountConfig, type AccountConfigSource } from './account'

/** The account settings of this server: NUXT_ACCOUNT_ENDPOINT, NUXT_ACCOUNT_TOKEN, NUXT_ACCOUNT_PUBLIC_ORIGIN. */
export function runtimeAccountConfig(event: H3Event): AccountConfigSource {
  return () => {
    const config = useRuntimeConfig(event)
    return accountConfig({ endpoint: config.accountEndpoint, token: config.accountToken, publicOrigin: config.accountPublicOrigin })
  }
}
