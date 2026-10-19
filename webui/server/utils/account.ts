// Server side of «Винный дневник»: the /api/account/* routes call the account service.
// The browser never sees the service address or the service token. Plan: docs/plans/04_user-accounts.md.
import { Buffer } from 'node:buffer'
import { isIP } from 'node:net'
import {
  deleteCookie, getCookie, getHeader, getQuery, getRequestURL, sendRedirect,
  setCookie, setHeader, setResponseStatus, type H3Event,
} from 'h3'
import { renderSVG } from 'uqr'
import { EMAIL_CODE_PATTERN, MAX_APP_LINK_PATTERN, USERNAME_PATTERN, isMaxAppPath, safeNextPath, type AccountErrorBody } from '#shared/account'

export const ACCOUNT_COOKIES = {
  session: '__Host-cv_session',
  email: '__Host-cv_email',
  yandex: '__Host-cv_yandex',
  signup: '__Host-cv_signup',
  next: '__Host-cv_next',
} as const

// Sessions do not expire in the service (owner, 2026-10-19). Browsers keep a cookie at most 400
// days, so every /api/account/me call sets it again: the login lasts while the person visits.
const SESSION_COOKIE_MAX_AGE = 400 * 86400
const sessionCookieAge = (expiresAt: unknown) => Math.min(secondsUntil(expiresAt, SESSION_COOKIE_MAX_AGE), SESSION_COOKIE_MAX_AGE)

export const YANDEX_CALLBACK_PATH = '/api/account/yandex/callback'
const MAX_RESPONSE_BYTES = 64 * 1024
const MAX_REQUEST_BYTES = 4 * 1024
// MAX launch data is up to 8 KiB in the service; the JSON wrapper adds a few bytes.
const MAX_LAUNCH_REQUEST_BYTES = 9 * 1024
const SIGNUP_TTL_SECONDS = 30 * 60
const MIN_TOKEN_LENGTH = 32
// The service spends up to 5 s on the Yandex token exchange and 5 s on the user info call.
// The browser waits on this top-level navigation, so the finish call gets the whole budget.
const YANDEX_FINISH_TIMEOUT_MS = 15_000

export interface AccountConfig {
  endpoint: URL
  token: string
  publicOrigin: string
  // The fixed MAX mini-app deep link, or '' when the site does not offer the MAX link.
  maxAppLink: string
  // The host of the MAX mini app (normalized), or '' when the mini app is off.
  maxHost: string
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
  settings: { endpoint?: unknown; token?: unknown; publicOrigin?: unknown; maxAppLink?: unknown; maxHost?: unknown },
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
  const maxAppLink = typeof settings.maxAppLink === 'string' && MAX_APP_LINK_PATTERN.test(settings.maxAppLink.trim()) ? settings.maxAppLink.trim() : ''
  const maxHost = normalizeHost(typeof settings.maxHost === 'string' ? settings.maxHost : '')
  return { endpoint, token, publicOrigin, maxAppLink, maxHost, timeoutMs: options.timeoutMs ?? 2000, fetch: options.fetch ?? fetch }
}

/** Calls the account service. Throws AccountHttpError for a refused request or an outage. */
export async function callAccount<T = Record<string, unknown>>(
  config: AccountConfig,
  method: 'GET' | 'POST' | 'DELETE',
  path: string,
  options: { body?: unknown; session?: string; clientIp?: string; appToken?: string; timeoutMs?: number } = {},
): Promise<{ status: number; data: T }> {
  const headers: Record<string, string> = { Accept: 'application/json', Authorization: `Bearer ${config.token}` }
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (options.session) headers['X-Session-Token'] = options.session
  if (options.clientIp) headers['X-Client-IP'] = options.clientIp
  if (options.appToken) headers['X-App-Token'] = options.appToken
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

// MAX runs the mini app in a frame of its own site. There the browser drops a SameSite=Lax or
// Strict cookie, so the email code fails with invalid_challenge (owner report, 2026-10-20). On the
// mini-app host (marked by maxHostGuard) the cookies are SameSite=None and Partitioned: the browser
// keeps them per top-level site, and checkOrigin still refuses a cross-site state change.
function embedded(event: H3Event): boolean {
  return event.context.accountEmbedded === true
}

function cookieOptions(event: H3Event, maxAge: number, sameSite: 'lax' | 'strict' = 'lax') {
  const base = { httpOnly: true, secure: true, path: '/', maxAge: Math.max(0, Math.floor(maxAge)) }
  return embedded(event) ? { ...base, sameSite: 'none' as const, partitioned: true } : { ...base, sameSite }
}

function clearCookie(event: H3Event, name: string) {
  deleteCookie(event, name, embedded(event)
    ? { httpOnly: true, secure: true, sameSite: 'none', partitioned: true, path: '/' }
    : { httpOnly: true, secure: true, sameSite: 'lax', path: '/' })
}

function secondsUntil(iso: unknown, fallback: number): number {
  const time = typeof iso === 'string' ? Date.parse(iso) : Number.NaN
  return Number.isFinite(time) ? Math.max(0, (time - Date.now()) / 1000) : fallback
}

/** Reads at most `limit` bytes. A longer or chunked body stops the read at the limit. */
async function readLimitedBody(event: H3Event, limit = MAX_REQUEST_BYTES): Promise<string> {
  const length = Number(getHeader(event, 'content-length') ?? 0)
  if (length > limit) throw new AccountHttpError(413, 'request_too_large')
  const request = event.node.req
  const chunks: Buffer[] = []
  let size = 0
  for await (const chunk of request) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)
    size += buffer.byteLength
    if (size > limit) {
      request.destroy()
      throw new AccountHttpError(413, 'request_too_large')
    }
    chunks.push(buffer)
  }
  return Buffer.concat(chunks).toString('utf8')
}

async function readJson(event: H3Event, limit = MAX_REQUEST_BYTES): Promise<Record<string, unknown>> {
  const raw = await readLimitedBody(event, limit)
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
    setCookie(event, ACCOUNT_COOKIES.session, answer.session.token, cookieOptions(event, sessionCookieAge(answer.session.expires_at)))
    clearCookie(event, ACCOUNT_COOKIES.signup)
    return { status: 'session' as const, user: answer.user }
  }
  if (answer.status === 'signup_required' && typeof answer.signup_ticket === 'string') {
    setCookie(event, ACCOUNT_COOKIES.signup, answer.signup_ticket, cookieOptions(event, SIGNUP_TTL_SECONDS))
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
      providers: {
        email: Boolean(data.providers?.email),
        yandex: Boolean(data.providers?.yandex),
        telegram: Boolean(data.providers?.telegram_link),
        max: Boolean(data.providers?.max_link) && Boolean(config.maxAppLink),
      },
      // The page runs the mini app (and loads the MAX Bridge) only on the mini-app host.
      maxApp: isMaxHost(event, config.maxHost),
      ...(data.providers?.max_link && config.maxAppLink ? { maxAppLink: config.maxAppLink } : {}),
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
      setCookie(event, ACCOUNT_COOKIES.session, session, cookieOptions(event, sessionCookieAge(data.session?.expires_at)))
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

// The deep link of the bot: https://t.me/<bot>?start=link_<code>. Telegram allows 64 characters in `start`.
const TELEGRAM_DEEP_LINK = /^https:\/\/t\.me\/[A-Za-z0-9_]{5,64}\?start=link_[A-Za-z0-9_-]{16,59}$/

/**
 * Starts a Telegram link (issue #51). Telegram is a linked messenger, never a login method.
 * The browser gets only the bot deep link; the bot confirms the link in the chat.
 */
export function telegramLinkRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    const session = getCookie(event, ACCOUNT_COOKIES.session)
    if (!session) throw new AccountHttpError(401, 'session_required')
    const { data } = await callAccount<{ deep_link?: string; expires_in?: number }>(config, 'POST', '/v1/me/links/telegram', { session })
    if (typeof data.deep_link !== 'string' || !TELEGRAM_DEEP_LINK.test(data.deep_link)) throw unavailable()
    return { deepLink: data.deep_link, expiresIn: typeof data.expires_in === 'number' ? data.expires_in : 600 }
  })
}

/**
 * Links MAX from the mini app (plan 05). The identity comes only from the signed launch data
 * (`window.WebApp.initData`); the service checks the signature, age, single use, and client address.
 * No code passes through MAX (MAX requirement 1.5).
 */
export function maxLinkRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    const session = getCookie(event, ACCOUNT_COOKIES.session)
    if (!session) throw new AccountHttpError(401, 'session_required')
    const body = await readJson(event, MAX_LAUNCH_REQUEST_BYTES)
    const initData = typeof body.initData === 'string' ? body.initData : ''
    if (!initData || initData.length > 8192) throw new AccountHttpError(400, 'invalid_launch')
    await callAccount(config, 'POST', '/v1/me/identities/max', { body: { init_data: initData }, session, clientIp: clientIp(event) })
    return { status: 'linked' }
  })
}

/** The QR code of the fixed mini-app deep link, for «Привязать мессенджер» → «MAX» on a computer. */
export function maxQrRoute(event: H3Event, source: AccountConfigSource) {
  let config: AccountConfig | null = null
  try {
    config = source()
  } catch { /* handled below */ }
  if (!config?.maxAppLink) {
    setResponseStatus(event, 404)
    setHeader(event, 'Cache-Control', 'no-store')
    return 'Not found'
  }
  setHeader(event, 'Content-Type', 'image/svg+xml')
  setHeader(event, 'Cache-Control', 'public, max-age=3600')
  return renderSVG(config.maxAppLink, { border: 2, whiteColor: '#ffffff', blackColor: '#211e1c' })
}

// The mini-app host (max.chtozavino.ru) serves only the diary. Caddy filters the paths too
// (plan 05, "Deployment"); this list is the second barrier. No Yandex ID, no Telegram link, and no
// service worker or manifest on that host.
const MAX_HOST_ROUTES: Array<[RegExp, string[]]> = [
  [/^\/max\/?$/, ['GET', 'HEAD']],
  [/^\/(_nuxt|reference|icons)\/[^?#]*$/, ['GET', 'HEAD']],
  [/^\/(privacy|terms|contacts|robots\.txt|__nuxt_error)$/, ['GET', 'HEAD']],
  [/^\/api\/account\/(config|max\/qr\.svg)$/, ['GET']],
  [/^\/api\/account\/me$/, ['GET', 'DELETE']],
  [/^\/api\/account\/(logout|signup|email\/start|email\/verify|max\/link)$/, ['POST']],
  [/^\/api\/account\/identities\/max$/, ['DELETE']],
]

/** What the mini-app host does with a request: serve it, redirect `/` to the mini app, or 404. */
export function maxHostDecision(method: string, pathname: string): 'allow' | 'redirect' | 'reject' {
  if (UNSAFE_PATH.test(pathname)) return 'reject'
  if (pathname === '/' && (method === 'GET' || method === 'HEAD')) return 'redirect'
  return MAX_HOST_ROUTES.some(([pattern, methods]) => pattern.test(pathname) && methods.includes(method)) ? 'allow' : 'reject'
}

// Dot segments, encoded dots or slashes, backslashes, and empty segments: the router and the URL
// parser can read such a path differently, so the mini-app host refuses it.
const UNSAFE_PATH = /\.\.|%2e|%2f|%5c|\\|\/\//i

/** Lower case, without a port and without a trailing dot: `MAX.chtozavino.ru.:443` → `max.chtozavino.ru`. */
export function normalizeHost(value: string): string {
  const host = value.trim().toLowerCase()
  const bare = host.startsWith('[') ? host.slice(0, host.indexOf(']') + 1) : host.replace(/:\d*$/, '')
  return bare.replace(/\.$/, '')
}

/** True when the request came through the mini-app host. Caddy keeps the original Host header. */
export function isMaxHost(event: H3Event, maxHost: string): boolean {
  const want = normalizeHost(maxHost)
  return Boolean(want) && normalizeHost(getHeader(event, 'host') ?? '') === want
}

/**
 * The host guard (server middleware). On the mini-app host it serves only the diary routes; on any
 * other host `/max` goes to `/account`, so the MAX Bridge never runs on the main site. It decides on
 * the path that the router uses (`event.path`) and also checks the raw request line.
 */
export function maxHostGuard(event: H3Event, maxHost: string) {
  const path = (event.path || '/').split('?')[0] || '/'
  if (!isMaxHost(event, maxHost)) {
    if (isMaxAppPath(path)) return sendRedirect(event, '/account', 302)
    return
  }
  event.context.accountEmbedded = true
  const raw = (event.node.req.url ?? '/').split('?')[0] ?? '/'
  const decision = UNSAFE_PATH.test(raw) ? 'reject' : maxHostDecision(event.method, path)
  if (decision === 'redirect') return sendRedirect(event, '/max', 302)
  if (decision === 'reject') {
    setResponseStatus(event, 404)
    setHeader(event, 'Cache-Control', 'no-store')
    return 'Not found'
  }
}

const MESSENGERS = new Set(['telegram', 'max'])

/** Unlinks a messenger. Login methods (email, Yandex ID) have no unlink action on the site. */
export function unlinkMessengerRoute(event: H3Event, source: AccountConfigSource, provider: string) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    if (!MESSENGERS.has(provider)) throw new AccountHttpError(404, 'not_found')
    const session = getCookie(event, ACCOUNT_COOKIES.session)
    if (!session) throw new AccountHttpError(401, 'session_required')
    try {
      await callAccount(config, 'DELETE', `/v1/me/identities/${provider}`, { session })
    } catch (error) {
      // Already gone: the page shows the same state as after an unlink.
      if (!(error instanceof AccountHttpError && error.code === 'not_linked')) throw error
    }
    return { status: 'unlinked' }
  })
}

// ------------------------------------------------------------ application tokens (#65)

const APP_TOKEN_ID = /^[0-9a-f]{16}$/
const APP_TOKEN = /^cvpat_[A-Za-z0-9_-]{43}$/
const APP_TOKEN_LIFETIMES = new Set([30, 90, 365])

type AppTokenView = { id?: string; name?: string; created_at?: string; expires_at?: string; last_used_at?: string | null }
const appTokenView = (item: AppTokenView) => ({
  id: item.id, name: item.name, createdAt: item.created_at, expiresAt: item.expires_at, lastUsedAt: item.last_used_at ?? null,
})

function sessionOf(event: H3Event): string {
  const session = getCookie(event, ACCOUNT_COOKIES.session)
  if (!session) throw new AccountHttpError(401, 'session_required')
  return session
}

/** The active application tokens of the account, without secrets. */
export function appTokensRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    const { data } = await callAccount<{ tokens?: AppTokenView[] }>(config, 'GET', '/v1/me/app-tokens', { session: sessionOf(event) })
    return { tokens: (data.tokens ?? []).map(appTokenView) }
  })
}

/** Creates a token. The answer has the secret once; the server keeps nothing. */
export function appTokenCreateRoute(event: H3Event, source: AccountConfigSource) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    const session = sessionOf(event)
    const body = await readJson(event)
    const name = typeof body.name === 'string' ? body.name.trim() : ''
    if (!name || name.length > 64) throw new AccountHttpError(400, 'invalid_name')
    const lifetimeDays = typeof body.lifetimeDays === 'number' ? body.lifetimeDays : 90
    if (!APP_TOKEN_LIFETIMES.has(lifetimeDays)) throw new AccountHttpError(400, 'invalid_lifetime')
    const { data } = await callAccount<{ token?: string; app_token?: AppTokenView }>(config, 'POST', '/v1/me/app-tokens', {
      body: { name, lifetime_days: lifetimeDays }, session,
    })
    if (typeof data.token !== 'string' || !APP_TOKEN.test(data.token) || !data.app_token) throw unavailable()
    return { token: data.token, appToken: appTokenView(data.app_token) }
  })
}

export function appTokenRevokeRoute(event: H3Event, source: AccountConfigSource, id: unknown) {
  return accountJson(event, source, async config => {
    checkOrigin(event, config)
    const session = sessionOf(event)
    if (typeof id !== 'string' || !APP_TOKEN_ID.test(id)) throw new AccountHttpError(404, 'not_found')
    await callAccount(config, 'DELETE', `/v1/me/app-tokens/${id}`, { session })
    return { status: 'revoked' }
  })
}

/**
 * Read routes for MCP clients: `Authorization: Bearer cvpat_...`. The server passes the token on as
 * X-App-Token and keeps nothing. Errors: 401 `unauthorized` (the same for every refused token),
 * 429 `rate_limited` with Retry-After, 400 `invalid_request`, 503 `unavailable`.
 */
export async function appReadRoute(event: H3Event, source: AccountConfigSource, resource: 'profile' | 'wines') {
  setHeader(event, 'Cache-Control', 'no-store')
  const refuse = (status: number, error: string, retryAfter?: number) => {
    setResponseStatus(event, status)
    if (status === 401) setHeader(event, 'WWW-Authenticate', 'Bearer')
    if (retryAfter) setHeader(event, 'Retry-After', retryAfter)
    return { error }
  }
  let config: AccountConfig | null
  try {
    config = source()
  } catch {
    return refuse(503, 'unavailable')
  }
  if (!config) return refuse(503, 'unavailable')
  const match = /^Bearer (\S+)$/.exec(getHeader(event, 'authorization') ?? '')
  if (!match || !APP_TOKEN.test(match[1]!)) return refuse(401, 'unauthorized')
  let path = '/v1/app/profile'
  if (resource === 'wines') {
    const query = getQuery(event)
    const params = new URLSearchParams()
    if (query.limit !== undefined) {
      const limit = Number(query.limit)
      if (!Number.isInteger(limit) || limit < 1 || limit > 50) return refuse(400, 'invalid_request')
      params.set('limit', String(limit))
    }
    if (query.cursor !== undefined) {
      if (typeof query.cursor !== 'string' || !/^[A-Za-z0-9_-]{1,200}$/.test(query.cursor)) return refuse(400, 'invalid_request')
      params.set('cursor', query.cursor)
    }
    path = params.size ? `/v1/app/wines?${params}` : '/v1/app/wines'
  }
  try {
    const { data } = await callAccount(config, 'GET', path, { appToken: match[1], clientIp: clientIp(event) })
    return data
  } catch (error) {
    if (error instanceof AccountHttpError) {
      if (error.code === 'app_token_invalid') return refuse(401, 'unauthorized')
      if (error.status === 429) return refuse(429, 'rate_limited', error.extra.retryAfter)
      if (error.status === 400 || error.status === 422) return refuse(400, 'invalid_request')
    }
    return refuse(503, 'unavailable')
  }
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
    setCookie(event, ACCOUNT_COOKIES.email, data.challenge_id, cookieOptions(event, expiresIn, 'strict'))
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
    setCookie(event, ACCOUNT_COOKIES.yandex, data.flow_id, cookieOptions(event, ttl))
    setCookie(event, ACCOUNT_COOKIES.next, safeNextPath(getQuery(event).next), cookieOptions(event, ttl))
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
  clearCookie(event, ACCOUNT_COOKIES.yandex)
  clearCookie(event, ACCOUNT_COOKIES.next)
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
    const { data } = await callAccount<AuthAnswer>(config, 'POST', '/v1/auth/yandex/finish', { body: { flow_id: flowId, state, code }, timeoutMs: YANDEX_FINISH_TIMEOUT_MS })
    const result = applyAuthAnswer(event, data)
    if (result.status === 'signup_required') return sendRedirect(event, accountPage(undefined, 'signup'), 302)
    return sendRedirect(event, next, 302)
  } catch (error) {
    return sendRedirect(event, accountPage(error instanceof AccountHttpError ? error.code : 'account_unavailable'), 302)
  }
}
