import type { AccountErrorBody } from '#shared/account'

export interface AccountIdentity { provider: string; linked_at?: string; email?: string }
export interface AccountUser { id: string; username: string; created_at?: string; identities: AccountIdentity[] }
export interface AccountSiteConfig {
  enabled: boolean
  available: boolean
  providers?: { email: boolean; yandex: boolean }
  consentVersion?: string
  termsVersion?: string
}
export type AuthResult =
  | { status: 'session'; user?: AccountUser }
  | { status: 'signup_required'; provider?: string; email?: string }

export class AccountRequestError extends Error {
  constructor(readonly status: number, readonly body: Partial<AccountErrorBody>) {
    super(body.error || `HTTP ${status}`)
  }
}

/** Calls the same-site /api/account/* routes. The session stays in an httpOnly cookie. */
export function useAccountApi(fetchImpl: typeof fetch = (...args) => fetch(...args)) {
  async function request<T>(method: string, path: string, body?: unknown, timeoutMs = 8000): Promise<T> {
    let response: Response
    try {
      response = await fetchImpl(path, {
        method,
        headers: body === undefined ? { Accept: 'application/json' } : { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
        credentials: 'same-origin',
        cache: 'no-store',
        signal: AbortSignal.timeout(timeoutMs),
      })
    } catch {
      throw new AccountRequestError(503, { error: 'account_unavailable' })
    }
    const data = await response.json().catch(() => ({})) as T & Partial<AccountErrorBody>
    if (!response.ok) throw new AccountRequestError(response.status, data)
    return data
  }

  return {
    config: () => request<AccountSiteConfig>('GET', '/api/account/config'),
    me: () => request<{ user: AccountUser; session: { authMethod?: string; expiresAt?: string } }>('GET', '/api/account/me'),
    emailStart: (email: string) => request<{ expiresIn: number }>('POST', '/api/account/email/start', { email }),
    emailVerify: (code: string) => request<AuthResult>('POST', '/api/account/email/verify', { code }),
    signup: (input: { username: string; acceptTerms: boolean; acceptConsent: boolean; consentVersion: string; termsVersion: string }) =>
      request<AuthResult>('POST', '/api/account/signup', input),
    logout: () => request<{ status: string }>('POST', '/api/account/logout', {}),
    deleteAccount: () => request<{ status: string }>('DELETE', '/api/account/me'),
  }
}
