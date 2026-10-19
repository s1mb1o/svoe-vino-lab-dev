# «Винный дневник»: account pages and server routes

Plan: [`../../docs/plans/04_user-accounts.md`](../../docs/plans/04_user-accounts.md) (issue #48).
Service: [`../../account/README.md`](../../account/README.md).

## Scope of this release

- The header link «Дневник» (phones: an icon with `aria-label="Винный дневник"`) goes to `/account`.
- `/account` has login by email code, login with Yandex ID, the sign-up step, the logged-in view,
  logout, and account deletion.
- The diary data (searches, photos, ratings, preferences) and onboarding come later. The service
  does not store them yet. The logged-in view says that they are coming.

## Configuration

| Variable | Meaning |
| --- | --- |
| `NUXT_ACCOUNT_ENDPOINT` | Base URL of the account service, for example `http://127.0.0.1:28008`. Empty: the feature is off. |
| `NUXT_ACCOUNT_TOKEN` | Bearer token of the `web` consumer of the service. At least 32 characters. |
| `NUXT_ACCOUNT_PUBLIC_ORIGIN` | Public origin of the site. Default `https://chtozavino.ru`. It builds the Yandex Redirect URI and is an allowed `Origin`. |

The browser never gets the endpoint or the token.

## Rules

- An empty endpoint hides the header link and turns the routes off (`account_disabled`). The
  server decides it during SSR (`useState('account-enabled')`). The header makes no account call.
- The account service is optional. Every call has a 2 s timeout and no retry. A failure gives
  `account_unavailable`; the page shows «Дневник временно недоступен». The scanner, the shelf
  mode, and SSR never call the service.
- Cookies (all `HttpOnly`, `Secure`, `Path=/`, `__Host-` prefix):

  | Cookie | Content | SameSite | Lifetime |
  | --- | --- | --- | --- |
  | `__Host-cv_session` | Session token | Lax | Until the session expires (30 days, extended by the service) |
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
  diary name. The page warns not to forward the link: the first Telegram user who opens it owns
  the code. Starting a link needs a login in the last 15 minutes; on `reauth_required` the chooser
  offers «Войти заново».
  `DELETE /api/account/identities/telegram` unlinks it without a fresh login (service rule for
  messengers). Login methods have no unlink route on the site.
- Account deletion needs a login in the last 15 minutes (service rule). On `reauth_required` the
  confirmation stays open and offers «Подтвердить кодом из письма» for the account's email
  (then «Подтвердить и удалить») or «Подтвердить через Яндекс ID» (`intent=reauth`,
  `next=/account?confirm=delete`). The confirmation names the account.
- A Yandex reauth MUST stay on the same account. The start route sets `__Host-cv_reauth`. The
  callback reads the user of the current session (`/v1/me`), then finishes the flow. It accepts the
  new session only for the same user ID. For another account or a Yandex identity without a diary,
  it keeps the current session, ends the new one, and returns `reauth_mismatch`. Without a valid
  current session it stops before the finish call. Follow-up: a service-side `reauth` purpose
  that checks the Yandex subject (reported by session svoe-vino-final-39).

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
  signature, the age (5 min), the single use of `query_id`, the signed `ip`, and a login in the last
  15 minutes. On `reauth_required` the page offers «Войти заново».
- The site: «Привязать мессенджер» → «MAX» shows the fixed deep link
  `NUXT_ACCOUNT_MAX_APP_LINK` (`https://max.ru/<bot>?startapp=account`, no code) and its QR code
  from `GET /api/account/max/qr.svg`. The person scans it, logs in inside MAX, and links there.
- The MAX choice appears only when the service reports `max_link` (`MAX_WEBAPP_KEY` is set) and the
  site has a valid `NUXT_ACCOUNT_MAX_APP_LINK`.
- `/max` has its own header and footer without links to other site pages. Metrika does not start
  there, and the Workbox page cache skips it.
- Host guard (`server/middleware/max-host.ts`): when the `Host` header equals
  `NUXT_ACCOUNT_MAX_HOST`, Nuxt answers `/` with 302 to `/max` and serves only `/max`, the layout
  assets, the legal pages, and the email, sign-up, session, deletion, and MAX routes. Other pages,
  Yandex ID, and the Telegram routes get 404. Nitro serves `public/` files (`/sw.js`,
  `/manifest.webmanifest`) before any middleware, so the Caddy block of the mini-app host MUST
  filter the paths too (plan 05, "Deployment"). Without `/sw.js` the mini app registers no service
  worker.

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
