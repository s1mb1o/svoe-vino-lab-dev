import type { AccountErrorBody } from '#shared/account'
import type { SavedComparisonAnswer } from '#shared/alternatives'
import type { HistoryItem, HistoryRecordStatus, HistorySource, SavedItem, SavedSource, SavedStatus } from '#shared/diary'

export interface AccountIdentity { provider: string; linked_at?: string; email?: string }
export interface AccountUser { id: string; username: string; created_at?: string; identities: AccountIdentity[]; save_history?: boolean }
export interface AccountSiteConfig {
  enabled: boolean
  available: boolean
  providers?: { email: boolean; yandex: boolean; telegram?: boolean; max?: boolean }
  maxAppLink?: string
  // True only on the MAX mini-app host.
  maxApp?: boolean
  consentVersion?: string
  termsVersion?: string
}
export interface AppToken { id: string; name: string; createdAt: string; expiresAt: string; lastUsedAt: string | null }
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
    linkTelegram: () => request<{ deepLink: string; expiresIn: number }>('POST', '/api/account/links/telegram', {}),
    linkMax: (initData: string) => request<{ status: string }>('POST', '/api/account/max/link', { initData }),
    unlinkMessenger: (provider: 'telegram' | 'max') => request<{ status: string }>('DELETE', `/api/account/identities/${provider}`),
    appTokens: () => request<{ tokens: AppToken[] }>('GET', '/api/account/app-tokens'),
    createAppToken: (name: string, lifetimeDays: number) => request<{ token: string; appToken: AppToken }>('POST', '/api/account/app-tokens', { name, lifetimeDays }),
    revokeAppToken: (id: string) => request<{ status: string }>('DELETE', `/api/account/app-tokens/${encodeURIComponent(id)}`),
    // «История» and «Сохранённые» (plan 07). Slugs go only into API paths, never into page URLs.
    history: () => request<{ items: HistoryItem[]; saveHistory: boolean }>('GET', '/api/account/history'),
    historyItem: (slug: string) => request<HistoryItem>('GET', `/api/account/history/${encodeURIComponent(slug)}`),
    recordHistory: (slug: string, source: Extract<HistorySource, 'photo' | 'shelf'>) =>
      request<{ status: HistoryRecordStatus; metOn?: string }>('POST', '/api/account/history', { slug, source }),
    deleteHistoryDay: (slug: string, metOn: string) => request<{ status: string }>('DELETE', `/api/account/history/${encodeURIComponent(slug)}/days/${encodeURIComponent(metOn)}`),
    deleteHistoryWine: (slug: string) => request<{ status: string }>('DELETE', `/api/account/history/${encodeURIComponent(slug)}`),
    clearHistory: () => request<{ status: string }>('DELETE', '/api/account/history'),
    setSaveHistory: (saveHistory: boolean) => request<{ user: AccountUser }>('PATCH', '/api/account/me', { saveHistory }),
    saved: () => request<{ items: SavedItem[] }>('GET', '/api/account/saved'),
    savedSlugs: () => request<{ items: Array<{ slug: string; status: SavedStatus }> }>('GET', '/api/account/saved/slugs'),
    savedComparison: (base: string) => request<SavedComparisonAnswer>('GET', `/api/account/saved/comparison?${new URLSearchParams({ base })}`),
    putSaved: (slug: string, status: SavedStatus, source: SavedSource, change = false, note?: string) =>
      request<SavedItem>('PUT', `/api/account/saved/${encodeURIComponent(slug)}`, { status, source, ...(change ? { change: true } : {}), ...(note === undefined ? {} : { note }) }),
    deleteSaved: (slug: string) => request<{ status: string }>('DELETE', `/api/account/saved/${encodeURIComponent(slug)}`),
  }
}
