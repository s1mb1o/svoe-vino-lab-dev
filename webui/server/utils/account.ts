// Server side of «Винный дневник»: the /api/account/* routes call the account service.
// The browser never sees the service address or the service token. Plan: docs/plans/04_user-accounts.md.
import { Buffer } from 'node:buffer'
import { isIP } from 'node:net'
import {
  deleteCookie, getCookie, getHeader, getQuery, getRequestURL, sendRedirect,
  setCookie, setHeader, setResponseStatus, type H3Event,
} from 'h3'
import { EMAIL_CODE_PATTERN, USERNAME_PATTERN, safeNextPath, type AccountErrorBody } from '#shared/account'

export const ACCOUNT_COOKIES = {
  session: '__Host-cv_session',
  email: '__Host-cv_email',
  yandex: '__Host-cv_yandex',
  signup: '__Host-cv_signup',
  next: '__Host-cv_next',
  reauth: '__Host-cv_reauth',
} as const

export const YANDEX_CALLBACK_PATH = '/api/account/yandex/callback'
const MAX_RESPONSE_BYTES = 64 * 1024
const MAX_REQUEST_BYTES = 4 * 1024
const SIGNUP_TTL_SECONDS = 30 * 60
const MIN_TOKEN_LENGTH = 32
// The service spends up to 5 s on the Yandex token exchange and 5 s on the user info call.
// The browser waits on this top-level navigation, so the finish call gets the whole budget.
const YANDEX_FINISH_TIMEOUT_MS = 15_000

export interface AccountConfig {
  endpoint: URL
  token: string
  publicOrigin: string
  timeoutMs: number
  fetch: typeof fetch
}

/** An answer of the account service, or a local check, that the route sends to the browser. */
export class AccountHttpError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly extra: { attemptsLeft?: number; retryAfter?: number } = {},
  ) {
    super(code)
  }

  body(): AccountErrorBody {
    return { error: this.code, ...this.extra }
  }
}

const unavailable = () => new AccountHttpError(503, 'account_unavailable')

/** Reads the settings when a route runs. Returns null when the feature is off; throws for invalid settings. */
export type AccountConfigSource = () => AccountConfig | null

/**
 * Reads the account settings. Returns null when NUXT_ACCOUNT_ENDPOINT is empty: the account
 * feature is off. A set but invalid endpoint or token makes the service unavailable.
 */
export function accountConfig(
  settings: { endpoint?: unknown; token?: unknown; publicOrigin?: unknown },
  options: { fetch?: typeof fetch; timeoutMs?: number } = {},
): AccountConfig | null {
  if (typeof settings.endpoint !== 'string' || !settings.endpoint.trim()) return null
  let endpoint: URL
  try {
    endpoint = new URL(settings.endpoint.trim())
  } catch {
    throw unavailable()
  }
  if (!['http:', 'https:'].includes(endpoint.protocol) || endpoint.username || endpoint.password || endpoint.search || endpoint.hash) {
    throw unavailable()
  }
  if (!endpoint.pathname.endsWith('/')) endpoint.pathname += '/'
  const token = typeof settings.token === 'string' ? settings.token.trim() : ''
  if (token.length < MIN_TOKEN_LENGTH) throw unavailable()
  let publicOrigin: string
  try {
    publicOrigin = new URL(typeof settings.publicOrigin === 'string' && settings.publicOrigin ? settings.publicOrigin : 'https://chtozavino.ru').origin
  } catch {
    throw unavailable()
  }
  return { endpoint, token, publicOrigin, timeoutMs: options.timeoutMs ?? 2000, fetch: options.fetch ?? fetch }
}

/** Calls the account service. Throws AccountHttpError for a refused request or an outage. */
export async function callAccount<T = Record<string, unknown>>(
  config: AccountConfig,
  method: 'GET' | 'POST' | 'DELETE',
  path: string,
  options: { body?: unknown; session?: string; clientIp?: string; timeoutMs?: number } = {},
): Promise<{ status: number; data: T }> {
  const headers: Record<string, string> = { Accept: 'application/json', Authorization: `Bearer ${config.token}` }
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (options.session) headers['X-Session-Token'] = options.session
  if (options.clientIp) headers['X-Client-IP'] = options.clientIp
  let response: Response
  try {
    response = await config.fetch(new URL(path.replace(/^\//, ''), config.endpoint), {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: AbortSignal.timeout(options.timeoutMs ?? config.timeoutMs),
      redirect: 'error',
      cache: 'no-store',
    })
  } catch {
    throw unavailable()
  }
  let text = ''
  try {
    const bytes = new Uint8Array(await response.arrayBuffer())
    if (bytes.byteLength > MAX_RESPONSE_BYTES) throw new Error('Response is too large')
    text = new TextDecoder().decode(bytes)
  } catch {
    throw unavailable()
  }
  let data: unknown = {}
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      throw unavailable()
    }
  }
  if (response.status >= 500) throw unavailable()
  if (response.status >= 400) {
    const body = (data && typeof data === 'object' ? data : {}) as Record<string, unknown>
    const code = typeof body.error === 'string' && /^[a-z_]{1,64}$/.test(body.error) ? body.error : 'request_rejected'
    const extra: { attemptsLeft?: number; retryAfter?: number } = {}
    if (typeof body.attempts_left === 'number') extra.attemptsLeft = body.attempts_left
    const retryAfter = Number(response.headers.get('retry-after'))
    if (Number.isFinite(retryAfter) && retryAfter > 0) extra.retryAfter = Math.ceil(retryAfter)
    // A refused service token or network is a configuration fault, not a browser error.
    if (response.status === 401 && code === 'unauthorized') throw unavailable()
    if (response.status === 403 && code === 'forbidden') throw unavailable()
    throw new AccountHttpError(response.status, code, extra)
  }
  return { status: response.status, data: data as T }
}

/** The browser address. Caddy on the same host is the only proxy, so its last X-Forwarded-For entry is the client. */
export function clientIp(event: H3Event): string {
  const remote = event.node.req.socket?.remoteAddress ?? ''
  const loopback = remote === '127.0.0.1' || remote === '::1' || remote === '::ffff:127.0.0.1'
  if (loopback) {
    const forwarded = (getHeader(event, 'x-forwarded-for') ?? '').split(',').map(item => item.trim()).filter(Boolean)
    const last = forwarded.at(-1)
    if (last && isIP(last)) return last
  }
  const plain = remote.startsWith('::ffff:') ? remote.slice(7) : remote
  return isIP(plain) ? plain : '127.0.0.1'
}

/** State-changing routes accept only a request from this site. */
export function checkOrigin(event: H3Event, config: AccountConfig): void {
  const origin = getHeader(event, 'origin')
  if (!origin) throw new AccountHttpError(403, 'origin_rejected')
  const own = getRequestURL(event, { xForwardedHost: true, xForwardedProto: true }).origin
  if (origin !== config.publicOrigin && origin !== own) throw new AccountHttpError(403, 'origin_rejected')
}

function cookieOptions(maxAge: number, sameSite: 'lax' | 'strict' = 'lax') {
  return { httpOnly: true, secure: true, sameSite, path: '/', maxAge: Math.max(0, Math.floor(maxAge)) }
}

function clearCookie(event: H3Event, name: string) {
  deleteCookie(event, name, { httpOnly: true, secure: true, sameSite: 'lax', path: '/' })
}

function secondsUntil(iso: unknown, fallback: number): number {
  const time = typeof iso === 'string' ? Date.parse(iso) : Number.NaN
  return Number.isFinite(time) ? Math.max(0, (time - Date.now()) / 1000) : fallback
}

/** Reads at most MAX_REQUEST_BYTES. A longer or chunked body stops the read at the limit. */
async function readLimitedBody(event: H3Event): Promise<string> {
  const length = Number(getHeader(event, 'content-length') ?? 0)
  if (length > MAX_REQUEST_BYTES) throw new AccountHttpError(413, 'request_too_large')
  const request = event.node.req
  const chunks: Buffer[] = []
  let size = 0
  for await (const chunk of request) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)
    size += buffer.byteLength
    if (size > MAX_REQUEST_BYTES) {
      request.destroy()
      throw new AccountHttpError(413, 'request_too_large')
    }
    chunks.push(buffer)
  }
  return Buffer.concat(chunks).toString('utf8')
}

async function readJson(event: H3Event): Promise<Record<string, unknown>> {
  const raw = await readLimitedBody(event)
  if (!raw) return {}
  try {
    const value = JSON.parse(raw) as unknown
    if (value && typeof value === 'object' && !Array.isArray(value)) return value as Record<string, unknown>
  } catch { /* handled below */ }
  throw new AccountHttpError(400, 'invalid_request')
}

type AuthAnswer = {
  status?: string
  session?: { token?: string; expires_at?: string; auth_method?: string }
  signup_ticket?: string
  provider?: string
  email?: string
  user?: unknown
}

/** Keeps the session or the sign-up ticket in httpOnly cookies. The browser gets neither value. */
function applyAuthAnswer(event: H3Event, answer: AuthAnswer) {
  if (answer.status === 'session' && typeof answer.session?.token === 'string') {
    setCookie(event, ACCOUNT_COOKIES.session, answer.session.token, cookieOptions(secondsUntil(answer.session.expires_at, 86400)))
    clearCookie(event, ACCOUNT_COOKIES.signup)
    return { status: 'session' as const, user: answer.user }
  }
  if (answer.status === 'signup_required' && typeof answer.signup_ticket === 'string') {
    setCookie(event, ACCOUNT_COOKIES.signup, answer.signup_ticket, cookieOptions(SIGNUP_TTL_SECONDS))
    return { status: 'signup_required' as const, provider: answer.provider, email: answer.email }
  }
  if (answer.status === 'linked') return { status: 'linked' as const, user: answer.user }
  throw unavailable()
}

/** Runs a JSON route: no caching, and a uniform error body { error, attemptsLeft?, retryAfter? }. */
export async function accountJson(event: H3Event, source: AccountConfigSource, run: (config: AccountConfig) => Promise<unknown>) {
  setHeader(event, 'Cache-Control', 'no-store')
  try {
    const config = source()
    if (!config) throw new AccountHttpError(404, 'account_disabled')
    return await run(config)
  } catch (error) {
    const failure = error instanceof AccountHttpError ? error : unavailable()
    setResponseStatus(event, failure.status)
    if (failure.extra.retryAfter) setHeader(event, 'Retry-After', failure.extra.retryAfter)
    return failure.body()
  }
}

// --------------------------------------------------------------------------- routes

export async function accountConfigRoute(event: H3Event, source: AccountConfigSource) {
  setHeader(event, 'Cache-Control', 'no-store')
  let config: AccountConfig | null
  try {
    config = source()
  } catch {
    return { enabled: true, available: false }
  }
  if (!config) return { enabled: false, available: false }
  try {
    const { data } = await callAccount<{ providers?: Record<string, boolean>; consent_version?: string; terms_version?: string }>(config, 'GET', '/v1/config')
    return {
      enabled: true,
      available: true,
      providers: { email: Boolean(data.providers?.email), yandex: Boolean(data.providers?.yandex) },
      consentVersion: data.consent_version ?? '',
      termsVersion: data.terms_version ?? '',
    }
  } catch {
    return { enabled: true, available: false }
  }
}

export function meRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    const session = getCookie(event, ACCOUNT_COOKIES.session)
    if (!session) throw new AccountHttpError(401, 'session_required')
    try {
      const { data } = await callAccount<{ user?: unknown; session?: { auth_method?: string; expires_at?: string } }>(config, 'GET', '/v1/me', { session })
      setCookie(event, ACCOUNT_COOKIES.session, session, cookieOptions(secondsUntil(data.session?.expires_at, 86400)))
      return { user: data.user, session: { authMethod: data.session?.auth_method, expiresAt: data.session?.expires_at } }
    } catch (error) {
      if (error instanceof AccountHttpError && error.status === 401) clearCookie(event, ACCOUNT_COOKIES.session)
      throw error
    }
  })
}

export function deleteMeRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    const session = getCookie(event, ACCOUNT_COOKIES.session)
    if (!session) throw new AccountHttpError(401, 'session_required')
    await callAccount(config, 'DELETE', '/v1/me', { session })
    clearCookie(event, ACCOUNT_COOKIES.session)
    return { status: 'deleted' }
  })
}

export function logoutRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    const session = getCookie(event, ACCOUNT_COOKIES.session)
    clearCookie(event, ACCOUNT_COOKIES.session)
    if (session) {
      try {
        await callAccount(config, 'DELETE', '/v1/sessions/current', { session })
      } catch { /* the cookie is gone; the service session expires on its own */ }
    }
    return { status: 'logged_out' }
  })
}

export function emailStartRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    const body = await readJson(event)
    const email = typeof body.email === 'string' ? body.email.trim() : ''
    if (email.length < 3 || email.length > 254) throw new AccountHttpError(400, 'invalid_email')
    const { data } = await callAccount<{ challenge_id?: string; expires_in?: number }>(
      config, 'POST', '/v1/auth/email/start', { body: { email, purpose: 'login' }, clientIp: clientIp(event) },
    )
    if (typeof data.challenge_id !== 'string') throw unavailable()
    const expiresIn = typeof data.expires_in === 'number' ? data.expires_in : 600
    setCookie(event, ACCOUNT_COOKIES.email, data.challenge_id, cookieOptions(expiresIn, 'strict'))
    return { expiresIn }
  })
}

export function emailVerifyRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    const body = await readJson(event)
    const code = typeof body.code === 'string' ? body.code.trim() : ''
    if (!EMAIL_CODE_PATTERN.test(code)) throw new AccountHttpError(400, 'invalid_code')
    const challengeId = getCookie(event, ACCOUNT_COOKIES.email)
    if (!challengeId) throw new AccountHttpError(400, 'invalid_challenge')
    try {
      const { data } = await callAccount<AuthAnswer>(config, 'POST', '/v1/auth/email/verify', { body: { challenge_id: challengeId, code } })
      clearCookie(event, ACCOUNT_COOKIES.email)
      return applyAuthAnswer(event, data)
    } catch (error) {
      if (error instanceof AccountHttpError && ['invalid_challenge', 'too_many_attempts'].includes(error.code)) {
        clearCookie(event, ACCOUNT_COOKIES.email)
      }
      throw error
    }
  })
}

export function signupRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    const body = await readJson(event)
    if (body.acceptTerms !== true || body.acceptConsent !== true) throw new AccountHttpError(400, 'consent_required')
    const username = typeof body.username === 'string' ? body.username.trim() : ''
    if (!USERNAME_PATTERN.test(username)) throw new AccountHttpError(400, 'invalid_username')
    const consentVersion = typeof body.consentVersion === 'string' ? body.consentVersion : ''
    const termsVersion = typeof body.termsVersion === 'string' ? body.termsVersion : ''
    const ticket = getCookie(event, ACCOUNT_COOKIES.signup)
    if (!ticket) throw new AccountHttpError(400, 'invalid_ticket')
    try {
      const { data } = await callAccount<AuthAnswer>(config, 'POST', '/v1/auth/signup', {
        body: { signup_ticket: ticket, username, consent_version: consentVersion, terms_version: termsVersion },
      })
      return applyAuthAnswer(event, data)
    } catch (error) {
      if (error instanceof AccountHttpError && error.code === 'invalid_ticket') clearCookie(event, ACCOUNT_COOKIES.signup)
      throw error
    }
  })
}

function accountPage(error?: string, step?: string): string {
  const query = new URLSearchParams()
  if (error) query.set('error', error)
  if (step) query.set('step', step)
  const text = query.toString()
  return text ? `/account?${text}` : '/account'
}

/** Starts Yandex ID login: a GET from the «Войти с Яндекс ID» link, answered with a redirect. */
export async function yandexStartRoute(event: H3Event, source: AccountConfigSource) {
  setHeader(event, 'Cache-Control', 'no-store')
  try {
    const config = source()
    if (!config) throw unavailable()
    const { data } = await callAccount<{ authorize_url?: string; flow_id?: string; expires_in?: number }>(config, 'POST', '/v1/auth/yandex/start', {
      body: { redirect_uri: `${config.publicOrigin}${YANDEX_CALLBACK_PATH}`, purpose: 'login' },
      clientIp: clientIp(event),
    })
    const target = typeof data.authorize_url === 'string' ? new URL(data.authorize_url) : null
    if (!target || target.protocol !== 'https:' || target.hostname !== 'oauth.yandex.ru' || typeof data.flow_id !== 'string') throw unavailable()
    const ttl = typeof data.expires_in === 'number' ? data.expires_in : 600
    setCookie(event, ACCOUNT_COOKIES.yandex, data.flow_id, cookieOptions(ttl))
    setCookie(event, ACCOUNT_COOKIES.next, safeNextPath(getQuery(event).next), cookieOptions(ttl))
    // A fresh login for a dangerous action (account deletion) must stay on the same account.
    if (getQuery(event).intent === 'reauth') setCookie(event, ACCOUNT_COOKIES.reauth, '1', cookieOptions(ttl))
    else clearCookie(event, ACCOUNT_COOKIES.reauth)
    return sendRedirect(event, target.href, 302)
  } catch (error) {
    return sendRedirect(event, accountPage(error instanceof AccountHttpError ? error.code : 'account_unavailable'), 302)
  }
}

/**
 * The Redirect URI of the Yandex ID app. It answers only with a redirect and no HTML, so no page
 * script (Metrika sends location.href) sees the one-time code.
 */
export async function yandexCallbackRoute(event: H3Event, source: AccountConfigSource) {
  setHeader(event, 'Cache-Control', 'no-store')
  setHeader(event, 'Referrer-Policy', 'no-referrer')
  const query = getQuery(event)
  const flowId = getCookie(event, ACCOUNT_COOKIES.yandex)
  const next = safeNextPath(getCookie(event, ACCOUNT_COOKIES.next))
  const reauth = getCookie(event, ACCOUNT_COOKIES.reauth) === '1'
  const currentSession = getCookie(event, ACCOUNT_COOKIES.session)
  clearCookie(event, ACCOUNT_COOKIES.yandex)
  clearCookie(event, ACCOUNT_COOKIES.next)
  clearCookie(event, ACCOUNT_COOKIES.reauth)
  let config: AccountConfig | null = null
  try {
    config = source()
  } catch { /* handled below */ }
  if (!config) return sendRedirect(event, accountPage('account_unavailable'), 302)
  const code = typeof query.code === 'string' ? query.code : ''
  const state = typeof query.state === 'string' ? query.state : ''
  if (query.error || !code || !state) return sendRedirect(event, accountPage('yandex_cancelled'), 302)
  if (!flowId) return sendRedirect(event, accountPage('invalid_flow'), 302)
  try {
    // For a reauth, read the account of the current session before the finish call.
    let currentUserId = ''
    if (reauth) {
      if (!currentSession) return sendRedirect(event, accountPage('session_required'), 302)
      const { data: me } = await callAccount<{ user?: { id?: string } }>(config, 'GET', '/v1/me', { session: currentSession })
      currentUserId = me.user?.id ?? ''
      if (!currentUserId) throw unavailable()
    }
    const { data } = await callAccount<AuthAnswer>(config, 'POST', '/v1/auth/yandex/finish', { body: { flow_id: flowId, state, code }, timeoutMs: YANDEX_FINISH_TIMEOUT_MS })
    if (reauth) {
      const newUserId = (data.user as { id?: string } | undefined)?.id
      if (data.status !== 'session' || newUserId !== currentUserId) {
        // Another Yandex account: keep the current session, end the new one, and cancel the action.
        if (data.status === 'session' && typeof data.session?.token === 'string') {
          try {
            await callAccount(config, 'DELETE', '/v1/sessions/current', { session: data.session.token })
          } catch { /* the new session expires on its own */ }
        }
        return sendRedirect(event, accountPage('reauth_mismatch'), 302)
      }
    }
    const result = applyAuthAnswer(event, data)
    if (result.status === 'signup_required') return sendRedirect(event, accountPage(undefined, 'signup'), 302)
    return sendRedirect(event, next, 302)
  } catch (error) {
    return sendRedirect(event, accountPage(error instanceof AccountHttpError ? error.code : 'account_unavailable'), 302)
  }
}
