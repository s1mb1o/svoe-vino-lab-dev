# «Винный дневник»: account pages and server routes

Plan: [`../../docs/plans/04_user-accounts.md`](../../docs/plans/04_user-accounts.md) (issue #48).
Service: [`../../account/README.md`](../../account/README.md).

## Scope of this release

- The header link «Дневник» (phones: an icon with `aria-label="Винный дневник"`) goes to `/account`.
- `/account` has login by email code, login with Yandex ID, the sign-up step, the logged-in view,
  logout, and account deletion.
- The logged-in view has three tabs: «Сохранённые» (the default), «История», «Настройки» (plan
  [`07_diary-history-and-saved.md`](../../docs/plans/07_diary-history-and-saved.md), issues #71 and
  #64). Photos of searches, ratings, preferences, and onboarding come later (#48).

## Configuration

| Variable | Meaning |
| --- | --- |
| `NUXT_ACCOUNT_ENDPOINT` | Base URL of the account service, for example `http://127.0.0.1:28008`. Empty: the feature is off. |
| `ACCOUNT_WEB_TOKEN` | Bearer token of the `web` consumer: a random secret of at least 32 characters, the same name and value as in the account service. The old name `NUXT_ACCOUNT_TOKEN` still works when `ACCOUNT_WEB_TOKEN` is empty. |
| `NUXT_ACCOUNT_PUBLIC_ORIGIN` | Public origin of the site. Default `https://chtozavino.ru`. It builds the Yandex Redirect URI and is an allowed `Origin`. |

The browser never gets the endpoint or the token.

## Rules

- An empty endpoint hides the header link and turns the routes off (`account_disabled`). The
  server decides it during SSR (`useState('account-enabled')`). The header makes no account call.
- The account service is optional. Every call has a 2 s timeout and no retry. A failure gives
  `account_unavailable`; the page shows «Дневник временно недоступен». SSR never calls the
  service. The scanner and the shelf mode never wait for it: the history record and the pin state
  load after the result is on screen, and a failure only hides the pin or the history note.
- Cookies (all `HttpOnly`, `Secure`, `Path=/`, `__Host-` prefix):

  | Cookie | Content | SameSite | Lifetime |
  | --- | --- | --- | --- |
  | `__Host-cv_session` | Session token | Lax | 400 days (the browser maximum), set again at every visit; the service session has no expiry |
  | `__Host-cv_email` | Email challenge ID | Strict | 10 minutes |
  | `__Host-cv_signup` | Sign-up ticket | Lax | 30 minutes |
  | `__Host-cv_yandex` | Yandex flow ID | Lax | 10 minutes |
  | `__Host-cv_next` | Same-site path after the Yandex login | Lax | 10 minutes |

- Every state-changing route requires `Origin` equal to `NUXT_ACCOUNT_PUBLIC_ORIGIN` or to the
  request origin. Account responses send `Cache-Control: no-store`.
- `X-Client-IP` for the service: Nuxt listens on loopback behind Caddy, so the last
  `X-Forwarded-For` entry is the client. A request from another address uses the socket address.
- `GET /api/account/yandex/callback` is the Redirect URI of the Yandex ID app. It answers only
  with HTTP 302 and `Referrer-Policy: no-referrer`. No page script sees `code` or `state`.
- `/account?next=<path>` returns the person after login. `safeNextPath` accepts only same-site
  paths and refuses `//host`, `/\`, control characters, `/api/`, and `/v1/`.
- Metrika does not start when a visit begins on `/account`, and the client plugin sends no hit
  for `/account*`. Metrika can still run after a navigation from another page; it then sees no
  account page view. The code field has `ym-disable-keys`; Session Replay stays off.
- The Workbox page cache skips `/account*`. The pages send `X-Robots-Tag: noindex`.
- Sign-up needs two separate unchecked boxes: the terms of use (`/terms`) and the consent to
  personal data processing (`/privacy`). The server refuses sign-up without both.
- «Способы входа» lists only email and Yandex ID. Telegram and MAX are under «Связанные мессенджеры»
  with «Через них нельзя войти в дневник: они только сохраняют находки» (owner rule, 2026-10-19).
  Never call Telegram a login method in the UI or in texts. The action is «Привязать мессенджер»
  (then Telegram, later MAX), shown in «Связанные мессенджеры» — never under «Способы входа».
- Telegram link (issue #51): `POST /api/account/links/telegram` (session, `Origin`) returns only the
  bot deep link and its lifetime. The server refuses any link other than
  `https://t.me/<bot>?start=link_<code>`. The person confirms in the bot chat, where the bot shows the
  diary name. «Открыть Telegram» opens the link by script, so the page holds no link with the code
  and Metrika link tracking cannot see it. The page warns not to forward the link: the first Telegram user who opens it owns
  the code. «Отвязать» asks «Отвязать Telegram от дневника?» first.
  Login methods have no unlink route on the site.
- No re-login (owner, 2026-10-19): dangerous actions only ask for a confirmation on the page.
  «Удалить аккаунт» → «Удалить аккаунт <имя> и все данные?» → «Удалить навсегда». «Отвязать» and
  «Отозвать» ask a yes/no question first. The Yandex re-login flow (`intent=reauth`) is removed.
- Sessions do not expire: a login lasts until «Выйти» or account deletion. The cookie is set again at
  every `/api/account/me`, because browsers keep a cookie at most 400 days.

## Application tokens

Issue #65. «Токены приложений» on `/account` (not in the MAX mini app).

- «Создать токен»: a name and a lifetime (30, 90 by default, or 365 days). The form says before
  creation that anyone with the token can read the diary.
- The page shows the token once, with «Скопировать токен» and the MCP client configuration. «Готово»
  removes the secret from the page. The token fields have `ym-disable-keys` and `ym-hide-content`.
- The list shows the name, the expiry, and the last use. «Отозвать» asks first, then revokes the token at once.
- `GET /api/app/v1/profile` and `GET /api/app/v1/wines` take `Authorization: Bearer cvpat_...` and
  pass the token on as `X-App-Token` with the client address. Nuxt keeps nothing and answers with
  `Cache-Control: no-store`. A missing or malformed header gets 401 without a service call. Errors:
  401 `unauthorized` with `WWW-Authenticate: Bearer` (the same for every refused token), 429
  `rate_limited` with `Retry-After`, 400 `invalid_request`, 503 `unavailable`. These routes need no
  `Origin`: they use no cookie.
- Deployment (open decision 1 of #65, option A): Caddy must exempt only `/api/app/*` from HTTP Basic
  and keep the `Authorization` header for it. The main `chtozavino.ru` block removes that header
  today. Every other path keeps HTTP Basic. This change needs the owner approval.

## MAX link

Plan 05, issue #50. MAX is a linked messenger. MAX login (`MAX_LOGIN_ENABLED`) stays off.

- MAX forbids a one-time code for login or linking in a bot message, a deep link, or a QR code
  (requirement 1.5). The only MAX identity is the signed launch data of the mini app.
- `/max` is the account page in MAX mode (`definePageMeta({ alias: ['/max'] })`). The page loads the
  MAX Bridge `https://st.max.ru/js/max-web-app.js` only there, and reads `window.WebApp.initData`.
- Outside MAX (no launch data) the page shows only «Откройте дневник в MAX», the fixed deep link,
  and its QR code. It shows no account data and no form.
- In MAX: login only by the email code (no Yandex ID on the mini-app host), then «Привязать
  MAX-аккаунт «Имя Фамилия» к дневнику …?». The name comes from `initDataUnsafe` for display only,
  so a person can stop a foreign launch. «Привязать» sends `initData` to
  `POST /api/account/max/link`; the server adds the client address. The service checks the
  signature, the age (5 min), the single use of `query_id`, and the signed `ip`.
- The site: «Привязать мессенджер» → «MAX» shows the fixed deep link
  `NUXT_ACCOUNT_MAX_APP_LINK` (`https://max.ru/<bot>?startapp=account`, no code) and its QR code
  from `GET /api/account/max/qr.svg`. The person scans it, logs in inside MAX, and links there.
- The MAX choice appears only when the service reports `max_link` (`MAX_WEBAPP_KEY` is set) and the
  site has a valid `NUXT_ACCOUNT_MAX_APP_LINK`.
- `/max` has its own header and footer without links to other site pages. Metrika does not start
  there, and the Workbox page cache skips it.
- Host guard (`server/middleware/max-host.ts`, `maxHostGuard`): when the `Host` header equals
  `NUXT_ACCOUNT_MAX_HOST` (case, port, and a trailing dot ignored), Nuxt answers `/` with 302 to
  `/max` and serves only `/max`, the layout assets, the legal pages, and the email, sign-up,
  session, deletion, and MAX routes. Other pages, Yandex ID, the Telegram routes, and the token
  routes get 404. The guard decides on the router path (`event.path`) and refuses dot segments,
  encoded dots or slashes, backslashes, and empty segments. On any other host `/max` redirects to
  `/account`: the MAX Bridge, a third-party script, never runs on the main site (and
  `/api/account/config` reports `maxApp: true` only on the mini-app host). Nitro serves `public/` files (`/sw.js`,
  `/manifest.webmanifest`) before any middleware, so the Caddy block of the mini-app host MUST
  filter the paths too (plan 05, "Deployment"). Without `/sw.js` the mini app registers no service
  worker.

## History and saved wines (plan 07)

- After a single-bottle match with `X-Prediction-Mode: upstream`, the browser sends
  `POST /api/account/history` `{slug, source: 'photo'}` once. A shelf bottle that the person opens
  on their own photo sends `source: 'shelf'` once per result. Examples and mock results send
  nothing. A logged-out browser gets 401 without a service call and shows nothing.
- The result card shows «Записано в историю дневника» and «Убрать» (deletes that day).
- `PinButton.vue` is the pin in the top right corner of a wine card: the photo result, the shelf
  bottle dialog, the product line map details, the Dinner Lens wine cards, and the history rows.
  The first pin of a page loads `GET /api/account/saved/slugs`; all pins share the state
  (`useDiary`). 401 gives the login offer; `account_disabled` or an outage hides the pins.
- The server builds the wine snapshot from the slug (`server/data/wines.json`, then the
  vino-svoe.ru API). It never takes a snapshot from the browser. An unknown wine gives 404
  `unknown_wine`; a catalogue timeout stores the wine without a snapshot. A status change
  (`change: true`) makes no catalogue request.
- The list routes accept service answers of up to 2 MiB (2,000 history wines).
- Wine slugs go only into API paths, never into page URLs. The tab is in `?tab=`. The vino-svoe.ru
  links of the lists have `ym-disable-tracklink`. `/account` opens «Сохранённые»; `?tab=history` and `?tab=settings`
  open the other tabs.
- The MAX mini-app host does not allow the list routes (its Caddy block and `MAX_HOST_ROUTES` are
  unchanged). The mini app shows only the settings view.

## Routes

| Route | Service call | Result |
| --- | --- | --- |
| `GET /api/account/config` | `GET /v1/config` | `{enabled, available, providers, consentVersion, termsVersion}` |
| `GET /api/account/me` | `GET /v1/me` | `{user, session}`; 401 removes the session cookie |
| `DELETE /api/account/me` | `DELETE /v1/me` | `{status: 'deleted'}` |
| `POST /api/account/logout` | `DELETE /v1/sessions/current` | `{status: 'logged_out'}`, also when the service is down |
| `POST /api/account/email/start` | `POST /v1/auth/email/start` | `{expiresIn}` and the challenge cookie |
| `POST /api/account/email/verify` | `POST /v1/auth/email/verify` | `{status: 'session'}` or `{status: 'signup_required'}` |
| `POST /api/account/signup` | `POST /v1/auth/signup` | `{status: 'session'}` |
| `GET /api/account/yandex/start` | `POST /v1/auth/yandex/start` | 302 to `https://oauth.yandex.ru/authorize` |
| `GET /api/account/yandex/callback` | `POST /v1/auth/yandex/finish` | 302 to `next`, `/account?step=signup`, or `/account?error=<code>` |
| `POST /api/account/links/telegram` | `POST /v1/me/links/telegram` | `{deepLink, expiresIn}` |
| `DELETE /api/account/identities/telegram` | `DELETE /v1/me/identities/telegram` | `{status: 'unlinked'}`, also when it was not linked |
| `POST /api/account/max/link` | `POST /v1/me/identities/max` | `{status: 'linked'}`; body `{initData}` up to 9 KiB |
| `DELETE /api/account/identities/max` | `DELETE /v1/me/identities/max` | `{status: 'unlinked'}`, also when it was not linked |
| `GET /api/account/max/qr.svg` | — | QR code of `NUXT_ACCOUNT_MAX_APP_LINK`; 404 when it is not set |
| `GET /api/account/app-tokens` | `GET /v1/me/app-tokens` | `{tokens: [{id, name, createdAt, expiresAt, lastUsedAt}]}` |
| `POST /api/account/app-tokens` | `POST /v1/me/app-tokens` | `{token, appToken}`; body `{name, lifetimeDays}` |
| `DELETE /api/account/app-tokens/[id]` | `DELETE /v1/me/app-tokens/{id}` | `{status: 'revoked'}` |
| `PATCH /api/account/me` | `PATCH /v1/me` | `{user}`; body `{saveHistory}` |
| `GET /api/account/history` | `GET /v1/me/history` | `{items: [HistoryItem], saveHistory}` |
| `GET /api/account/history/[slug]` | `GET /v1/me/history/{slug}` | `HistoryItem` with `days: [{metOn, source, firstAt}]` |
| `POST /api/account/history` | `POST /v1/me/history` | `{status: 'recorded' \| 'already' \| 'off', metOn?}`; body `{slug, source}`; 409 `mock_mode`, 404 `unknown_wine` |
| `DELETE /api/account/history` | `DELETE /v1/me/history` | `{status: 'cleared'}` |
| `DELETE /api/account/history/[slug]` | `DELETE /v1/me/history/{slug}` | `{status: 'removed'}` |
| `DELETE /api/account/history/[slug]/days/[day]` | `DELETE /v1/me/history/{slug}/days/{met_on}` | `{status: 'removed'}` |
| `GET /api/account/saved` | `GET /v1/me/saved` | `{items: [SavedItem]}` |
| `GET /api/account/saved/slugs` | `GET /v1/me/saved/slugs` | `{items: [{slug, status}]}` |
| `PUT /api/account/saved/[slug]` | `PUT /v1/me/saved/{slug}` | `SavedItem` (with `note`); body `{status, source, change?, note?}` up to 12 KiB; note at most 2,000 characters, `''` clears it; 400 `invalid_note`, 409 `saved_full` |
| `DELETE /api/account/saved/[slug]` | `DELETE /v1/me/saved/{slug}` | `{status: 'removed'}` |
| `GET /api/app/v1/profile` | `GET /v1/app/profile` | Bearer application token; profile |
| `GET /api/app/v1/wines` | `GET /v1/app/wines` | Bearer application token; `{items, next_cursor}` |

Errors have the form `{error, attemptsLeft?, retryAfter?}`. The page shows the Russian text of
`accountErrorMessage` and never the input.

## Security review, 2026-10-19

Codex (`gpt-6.1-sol`, xhigh) reviewed commit `cdeafd36` and the tunnel design. Fixed:

- The Metrika init script had a regular expression inside a template string. The escapes were
  lost, so the script did not parse on any page. The guard now compares strings. A unit test
  parses and runs the script; the browser check confirms Metrika on `/`.
- A chunked request body was read completely before the 4 KiB check. The routes now count
  bytes while they read and stop at the limit.
- The Yandex finish call had the general 2 s timeout, but the service can spend up to 10 s on
  Yandex. The callback now waits up to 15 s, so a slow Yandex does not lose a completed login.

Accepted, with the reason:

- A local process on the edge host could bind `127.0.0.1:28008` while the tunnel is down and
  receive the web token. Another local process could call Nuxt on `127.0.0.1:8153` directly and
  choose `X-Forwarded-For`. On 2026-10-19 the edge host had no login account except `root`;
  every other account is a system service. The matcher listener `127.0.0.1:28000` has the
  same exposure. Revisit with a Unix socket or a proxy secret when the host gets other users.

## Open items

- `/terms` and `/privacy` do not exist yet (#37). They MUST exist before people other than the
  owner sign up.
- The public route: the web server reaches the gx10 service through a reverse SSH tunnel.

## F04 diary reuse, 2026-10-20

Alternative and comparison cards use the existing `PinButton`, `useDiary`, saved API, and statuses.
The saved candidate has its own exact slug and the initiating `photo` source.
Saving it does not create a recognition-history event.
The server can resolve accepted candidates from the same pinned catalog.
The adapter supplies known sweetness through the existing diary snapshot contract.
The client verifies the current account before it activates a device-copy owner.
Account reset, deletion, or logout clears the separate public-card cache.
Generation checks reject stale save results after an account change.
A 401 write response clears stale state and exposes the existing login offer.
The cache does not contain the account response, statuses, private notes, or credentials.
Read [the F04 storage and acceptance contract](f04-result-journey.md).
