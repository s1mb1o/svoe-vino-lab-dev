# Account service of «Винный дневник»

This component holds the accounts of «Винный дневник» and every login and linking path.
Plans: [`../docs/plans/03_user-accounts.md`](../docs/plans/03_user-accounts.md) (issue #48) and
[`../docs/plans/04_max-authorization.md`](../docs/plans/04_max-authorization.md) (issue #50).
Telegram linking: issue #51. Email login: issue #52.

The first version covers authorization only. The diary data (searches, photos, ratings,
preferences, application tokens) comes later.

## What it does

| Area | Behavior |
| --- | --- |
| Login by email code | A 6-digit code, valid 10 minutes, at most 5 tries. The code works only with the challenge ID that the requesting browser holds. Limits: 1 code per minute and 3 per hour for an address, 20 per hour for a client address. |
| Login by Yandex ID | OAuth 2.0 authorization code flow with PKCE (`S256`) and `state`. The service keeps the Yandex user ID only and discards the access token. Limit: 30 starts per hour for a client address; at most 10,000 open flows. |
| Sign-up | A new email or Yandex identity gets a sign-up ticket (30 minutes). Sign-up needs a username and the current consent and terms versions. |
| Sessions | 30 days, extended at most once a day. `max` sessions: 1 day. |
| Linking | A session can link an email (this changes the address), Yandex ID, MAX, and Telegram. Linking email, Yandex ID, or MAX needs a login in the last 15 minutes, at the start and at the end. One identity per provider and account. An identity belongs to one account at most. |
| MAX | Checks the mini-app launch data: signature, age (5 minutes by default, at most 60), single-use `query_id` kept while the launch is valid, signed `ip` against the client address. MAX login is off by default (`MAX_LOGIN_ENABLED`, issue #50). |
| Telegram | A one-time link code (10 minutes, at most 10 per hour for an account) for `https://t.me/<bot>?start=link_<code>`. The bot reads the diary name, asks the person, then confirms. Telegram never opens a session. |
| Deletion | Unlink and account deletion need a login in the last 15 minutes. An account keeps at least one login method: email or Yandex ID. MAX login does not count. |

Russian law (149-FZ art. 8 p. 10, KoAP 13.55 since 7 July 2026) forbids login through a
foreign service. Do not add login through Telegram, Google, or Apple. Telegram is only linked.

## Requirements and commands

Python 3.12 and [uv](https://docs.astral.sh/uv/).

```sh
cd account
./scripts/verify.sh            # lock check, sync, ruff, pytest
cp .env.example .env           # then set the secrets
set -a && . ./.env && set +a
uv run chto-za-vino-account    # listens on ACCOUNT_HOST:ACCOUNT_PORT (default 127.0.0.1:28008)
```

The development email backend `console` writes each message, with the code, to stderr.
Production refuses it and requires `smtp`.

Compute `MAX_WEBAPP_KEY` once from the MAX bot token. The service never gets the bot token:

```sh
uv run chto-za-vino-account max-key < file-with-the-bot-token
```

## Configuration

See [`.env.example`](.env.example). Each secret has at least 32 characters, and all secrets
are distinct. Leave `YANDEX_CLIENT_ID`, `MAX_WEBAPP_KEY`, or `TELEGRAM_BOT_USERNAME` empty to
turn that provider off. The service refuses to start with an invalid value.

Yandex ID setup (owner): register an app of the type «Для авторизации пользователей» at
<https://oauth.yandex.ru/client/new/id/>, platform «Веб-сервисы», the Redirect URIs of the
Nuxt callback page, no extra data access. Verify the service through Gosuslugi in the Yandex
OAuth cabinet; without it, Yandex shows users a warning.

## API

All routes except `/healthz` and `/readyz` need a client address from
`ACCOUNT_ALLOWED_NETWORKS` and `Authorization: Bearer <consumer token>`. The consumers are
`web` (the Nuxt server), `max-bot`, and `telegram-bot`. The web consumer sends the session in
`X-Session-Token` and the browser address in `X-Client-IP`. Errors have the form
`{"error": "<code>", "detail": "..."}`. Validation errors never echo the input.

| Route | Consumer | Purpose |
| --- | --- | --- |
| `GET /healthz`, `GET /readyz` | none | Liveness; database check |
| `GET /v1/config` | web | Enabled providers, current consent and terms versions |
| `POST /v1/auth/email/start` | web | `{email, purpose: login\|link}` → `{challenge_id, expires_in}` |
| `POST /v1/auth/email/verify` | web | `{challenge_id, code}` → session, sign-up ticket, or linked |
| `POST /v1/auth/yandex/start` | web | `{redirect_uri, purpose}` and `X-Client-IP` → `{authorize_url, flow_id, expires_in}` |
| `POST /v1/auth/yandex/finish` | web | `{flow_id, state, code}` → session, sign-up ticket, or linked |
| `POST /v1/auth/signup` | web | `{signup_ticket, username, consent_version, terms_version}` → session |
| `POST /v1/auth/max/session` | web | `{init_data}` → session or `not_linked` (only with `MAX_LOGIN_ENABLED`) |
| `DELETE /v1/sessions/current` | web | Log out |
| `GET /v1/me`, `DELETE /v1/me` | web | Account view; delete the account |
| `POST /v1/me/identities/max` | web | `{init_data}` → link MAX |
| `DELETE /v1/me/identities/{provider}` | web | Unlink `email`, `yandex`, `max`, or `telegram` |
| `POST /v1/me/links/telegram` | web | → `{code, deep_link, expires_in}` |
| `POST /v1/bot/telegram/links/claim` | telegram-bot | `{code, telegram_user_id}` → `{username}` for the confirmation text |
| `POST /v1/bot/telegram/links/confirm` | telegram-bot | Link the Telegram user |
| `POST /v1/bot/telegram/unlink` | telegram-bot | Unlink by Telegram user ID |

The Nuxt server keeps the session token, the email challenge ID, and the Yandex flow ID in
httpOnly cookies. The browser never sees the service.

## Deployment

Docker Compose on gx10, like the MAX bot. See [`Dockerfile`](Dockerfile) and
[`deploy/compose.example.yaml`](deploy/compose.example.yaml). Keep the real Compose file,
the environment file, and the deployment record outside this repository. Back up
`/data/account.sqlite3` with `sqlite3 account.sqlite3 ".backup ..."`.
