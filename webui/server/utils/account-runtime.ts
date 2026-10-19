import type { H3Event } from 'h3'
import { accountConfig, type AccountConfigSource } from './account'

/** The account settings of this server: NUXT_ACCOUNT_ENDPOINT, ACCOUNT_WEB_TOKEN, NUXT_ACCOUNT_PUBLIC_ORIGIN, NUXT_ACCOUNT_MAX_APP_LINK. */
export function runtimeAccountConfig(event: H3Event): AccountConfigSource {
  return () => {
    const config = useRuntimeConfig(event)
    return accountConfig({
      endpoint: config.accountEndpoint,
      // ACCOUNT_WEB_TOKEN has the same name as in the account service. NUXT_ACCOUNT_TOKEN
      // (config.accountToken) is the old name, kept until the hosts use the new one.
      token: process.env.ACCOUNT_WEB_TOKEN || config.accountToken,
      publicOrigin: config.accountPublicOrigin,
      maxAppLink: config.accountMaxAppLink,
      maxHost: config.accountMaxHost,
    })
  }
}
