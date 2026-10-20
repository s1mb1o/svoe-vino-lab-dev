# Account service of «Винный дневник»

This component holds the accounts of «Винный дневник» and every login and linking path.
Plans: [`../docs/plans/04_user-accounts.md`](../docs/plans/04_user-accounts.md) (issue #48),
[`../docs/plans/05_max-authorization.md`](../docs/plans/05_max-authorization.md) (issue #50), and
[`../docs/plans/07_diary-history-and-saved.md`](../docs/plans/07_diary-history-and-saved.md)
(issues #71 and #64). Telegram linking: issue #51. Email login: issue #52.

The service also keeps application tokens for MCP clients (#65) and two diary lists: the history
of found wines and «Сохранённые». Photos, ratings, and preferences come later.

## What it does

| Area | Behavior |
| --- | --- |
| Login by email code | A 6-digit code, valid 10 minutes, at most 5 tries. The code works only with the challenge ID that the requesting browser holds. Limits: 1 code per minute and 3 per hour for an address, 20 per hour for a client address. |
| Login by Yandex ID | OAuth 2.0 authorization code flow with PKCE (`S256`) and `state`. The service keeps the Yandex user ID only and discards the access token. Limit: 30 starts per hour for a client address; at most 10,000 open flows. |
| Same email | A login of an unknown identity joins the account that has the same email: an email identity by its address, a Yandex identity by the `default_email` that Yandex ID returns (permission «Доступ к адресу электронной почты»). Comparison after trim and lower case. No join when two accounts have the email or when the account already has an identity of this provider. The join trusts the Yandex address; Yandex ID confirms addresses of an account. |
| Sign-up | A new email or Yandex identity gets a sign-up ticket (30 minutes). Sign-up needs a username and the current consent and terms versions. |
| Sessions | No expiry (owner, 2026-10-19): a session ends at logout or account deletion. `max` sessions: 1 day (MAX login is off). |
| Linking | A session can link an email (this changes the address), Yandex ID, MAX, and Telegram. One identity per provider and account. An identity belongs to one account at most. |
| MAX | Checks the mini-app launch data: signature, age (5 minutes by default, at most 60), single-use `query_id` kept while the launch is valid, signed `ip` against the client address. MAX login is off by default (`MAX_LOGIN_ENABLED`, issue #50). |
| Telegram | A one-time link code (10 minutes, at most 10 per hour for an account) for `https://t.me/<bot>?start=link_<code>`. The bot reads the diary name, asks the person, then confirms. Telegram never opens a session. |
| History | One date for each wine and calendar day (Europe/Moscow) with the first source of the day: `photo` or `shelf` (the site), `telegram` or `max` (a linked chat). A repeated match on the same day changes nothing. The switch `save_history` (on by default) stops new records on the site and in the chats. Limits: 2,000 wines and 366 dates for each wine; at a limit the oldest record goes. |
| Saved | «Сохранённые»: a wine with one of four statuses (`not_tasted`, `want`, `liked`, `disliked`), the place where the person saved it, and an optional personal note (at most 2,000 characters). Independent of the history. At most 500 wines. |
| Deletion | Unlink and account deletion need no fresh login; the site asks for a confirmation. An account keeps at least one login method: email or Yandex ID. MAX login does not count. Account deletion removes both diary lists. |

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
are distinct. A consumer token (`ACCOUNT_WEB_TOKEN`, `ACCOUNT_TELEGRAM_TOKEN`, `ACCOUNT_MAX_TOKEN`)
is a random secret. The consumer reads it under the same name: the website, the Telegram bot, the
MAX bot. It is not a bot token of Telegram or MAX. The service refuses to start when a value is set
under the old names `ACCOUNT_TELEGRAM_BOT_TOKEN` or `ACCOUNT_MAX_BOT_TOKEN`. Leave `YANDEX_CLIENT_ID`, `MAX_WEBAPP_KEY`, or `TELEGRAM_BOT_USERNAME` empty to
turn that provider off. The service refuses to start with an invalid value.

Yandex ID setup (owner): register an app of the type «Для авторизации пользователей» at
<https://oauth.yandex.ru/client/new/id/>, platform «Веб-сервисы», Redirect URI
`https://chtozavino.ru/api/account/yandex/callback` (a Nuxt server route), no extra data access. Verify the service through Gosuslugi in the Yandex
OAuth cabinet; without it, Yandex shows users a warning.

## API

All routes except `/healthz` and `/readyz` need a client address from
`ACCOUNT_ALLOWED_NETWORKS` and `Authorization: Bearer <consumer token>`. The consumers are
`web` (the Nuxt server), `max-bot`, and `telegram-bot`. Both bots record the history of their
chats. The web consumer sends the session in `X-Session-Token` and the browser address in
`X-Client-IP`. Errors have the form `{"error": "<code>", "detail": "..."}`. Validation errors
have the form `{"error": "invalid_request", "fields": [...]}` and never echo the input.

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
| `GET /v1/me`, `DELETE /v1/me` | web | Account view with `save_history`; delete the account |
| `PATCH /v1/me` | web | `{save_history: bool}` → the `GET /v1/me` answer |
| `POST /v1/me/identities/max` | web | `{init_data}` → link MAX |
| `DELETE /v1/me/identities/{provider}` | web | Unlink `email`, `yandex`, `max`, or `telegram` |
| `POST /v1/me/links/telegram` | web | → `{code, deep_link, expires_in}`; a new code ends the open one |
| `POST /v1/bot/telegram/links/claim` | telegram-bot | `{code, telegram_user_id}` → `{username}` for the confirmation text. The first claimer owns the code |
| `POST /v1/bot/telegram/links/confirm` | telegram-bot | Link the Telegram user who claimed the code; a repeat answers `linked` again |
| `POST /v1/bot/telegram/unlink` | telegram-bot | Unlink by Telegram user ID |
| `GET /v1/me/history` | web | `{items: [HistoryItem], save_history}`: all wines, newest `last_met_at` first |
| `GET /v1/me/history/{slug}` | web | `HistoryItem` with `days: [{met_on, source, first_at}]`, newest first; 404 `not_found` |
| `POST /v1/me/history` | web | `{slug, source: photo\|shelf, wine_snapshot?}` → `{status: recorded\|already\|off, met_on?}` |
| `DELETE /v1/me/history/{slug}/days/{met_on}` | web | Remove one date; the last date removes the wine; 404 `not_found` |
| `DELETE /v1/me/history/{slug}` | web | Remove one wine; 404 `not_found` |
| `DELETE /v1/me/history` | web | Clear the history |
| `GET /v1/me/saved` | web | `{items: [SavedItem]}`, newest `updated_at` first |
| `GET /v1/me/saved/slugs` | web | `{items: [{slug, status}]}` for the pins of a page |
| `PUT /v1/me/saved/{slug}` | web | `{status, source, wine_snapshot?, note?}` → `SavedItem`: 201 for a new wine, 200 for a change; 409 `saved_full` |
| `DELETE /v1/me/saved/{slug}` | web | Remove a saved wine; 404 `not_found` |
| `POST /v1/bot/history` | telegram-bot, max-bot | `{user_id, slug, wine_snapshot?, replaces?, at?}` → `{status: recorded\|already\|off\|not_linked, met_on?}` |
| `POST /v1/bot/history/undo` | telegram-bot, max-bot | `{user_id, slug, at?}` → `{status: removed\|absent\|not_linked}` |
| `GET /v1/me/app-tokens` | web | Active application tokens, without secrets |
| `POST /v1/me/app-tokens` | web | `{name, lifetime_days}` → `{token, app_token}`; the token is in this answer only |
| `DELETE /v1/me/app-tokens/{id}` | web | Revoke a token |
| `GET /v1/app/profile` | web + `X-App-Token` | Username, creation date, preferences (`null` until #48) |
| `GET /v1/app/wines?cursor=&limit=` | web + `X-App-Token` | The history, newest first, `limit` 1–50 → `{items, next_cursor}`; 400 `invalid_cursor` |

Application tokens (#65) give an MCP client read-only access to its owner's diary. The format is
`cvpat_` and 32 random bytes in base64url; the service stores only the SHA-256 hash. A token never
opens a session and cannot manage tokens. Every refused token gets the same 401
`app_token_invalid`. Limits: 5 active tokens per account, 60 requests per minute per token, and 20
failed checks per minute per client address (HTTP 429 with `Retry-After`).

The Nuxt server keeps the session token, the email challenge ID, and the Yandex flow ID in
httpOnly cookies. The browser never sees the service.

## Diary lists

Plan 07 (issues #71 and #64). Code: [`diary.py`](src/chto_za_vino_account/diary.py). Schema:
`005_diary_lists.sql` and `006_saved_notes.sql` (`saved_wines.note`, `NULL` for no note). Times in
answers are ISO 8601 UTC.

- Wine slug: `^[a-z0-9](?:[a-z0-9_-]{0,198}[a-z0-9])?$`, in a path and in a body. Date of a path:
  `YYYY-MM-DD`.
- Wine snapshot: a JSON object with the optional fields `name`, `producer`, `color`, `sugar`,
  `region` (1–200 characters each) and `grapes` (at most 12 strings of 1–80 characters), at
  most 2,048 bytes of compact UTF-8 JSON. Another key, a longer value, or a larger object gets
  HTTP 422. The service keeps the snapshot so the lists render when the catalog is not
  available.
- Each writer (site history, chat history, saved `PUT`) merges a newer snapshot into the stored
  one: its keys override, and keys that it does not have keep the stored values. So a chat card
  without sugar or grapes does not erase the snapshot of the site. An empty object, an empty
  grape list, or no snapshot changes nothing. When the union is larger than 2,048 bytes, the
  newer snapshot replaces the stored one.
- `HistoryItem`: `slug`, `wine` (the snapshot or `null`), `first_met_at`, `last_met_at`,
  `days_count`, `sources` (the distinct sources of the dates, in the order `photo`, `shelf`,
  `telegram`, `max`), `saved_status` (`null` when not saved).
- `SavedItem`: `slug`, `wine`, `status`, `source`, `added_at`, `updated_at`, `in_history`,
  `note` (a string or `null`). `GET /v1/me/saved/slugs` and `GET /v1/app/wines` have no notes.
- Note of a saved wine (`note` in `PUT`): the service changes `\r\n` and `\r` to `\n`, then
  refuses a control character other than `\n` and `\t`, then removes the whitespace at the
  ends. At most 2,000 characters after this. No `note` key keeps the stored note. `""`, only
  whitespace, or `null` clears it. A new saved wine can have a note. A refusal is HTTP 422 with
  the field name `note` and never holds the text.
- When one list has no snapshot of a wine, the answer shows the snapshot of the other list.
- Day: the calendar day in Europe/Moscow. Without the time zone database, the service uses
  UTC+3 (Moscow has no daylight saving time since 2014).
- Record: a new day adds a date (`recorded`, with `met_on`). The same day keeps the first source
  and time and changes only the snapshot (`already`, with `met_on`). The switch off: `off`, and
  nothing is stored. A wine gets the earliest and the latest time of its dates.
- Removal of a date updates these times. The last date removes the wine. A saved wine stays
  when it leaves the history.
- `PUT` of a saved wine keeps `source` and `added_at`. It changes `status`, `updated_at`, and
  the snapshot when the body has one. Saved sources: `photo`, `shelf`, `lineup`, `dinner_lens`,
  `history`.
- Bots: the consumer gives the messenger (`telegram-bot` → `telegram`, `max-bot` → `max`).
  `user_id` is the Telegram or MAX user ID of a linked identity. A chat without a linked diary
  gets `not_linked` with HTTP 200. The chat records the alternative wine with the date of today.
- Bot removal: `undo` removes a date of `slug`. `replaces` is the wine that the person rejected
  before they selected this one: its date goes in the same transaction, also when the switch is
  off. `at` (integer, Unix seconds UTC) is the time of the result card. The date is the Moscow
  day of `at`. Without `at`, or with `at` outside [now − 48 h, now + 60 s], the date is today; this
  is not an error. Only a date with the source of this chat (`telegram` or `max`) goes. A date of
  another source stays, for example a site match of the same morning; `undo` then answers
  `absent`.
- `GET /v1/app/wines` item: `slug`, `name`, `producer`, `color`, `sugar` (from the snapshot or
  `null`), `first_met_at`, `last_met_at`, `days` (the number of dates), `sources`,
  `saved_status`. The cursor is opaque: it holds `last_met_at` and the slug of the last item in
  at most 184 base64url characters.
- The log has event names and sources only. Slugs go to the debug level. User IDs and notes
  never go to the log.

## Deployment

Docker Compose on the GPU host, in the same way as the matcher and the bots. See
[`Dockerfile`](Dockerfile) and [`deploy/compose.example.yaml`](deploy/compose.example.yaml).
Keep the real Compose file, the environment files, and the deployment record in the private
deployment repository, not here.

- Build: `git archive "$REV" account | ssh <host> "docker build -f account/Dockerfile --build-arg REVISION=$REV -t svoe-vino-lab-account:$REV -"`.
  The pinned base images support `linux/amd64` and `linux/arm64`.
- Tags: `svoe-vino-lab-account:<commit>`, then `:prod` and `:prod-prev` (or `:dev`, `:dev-prev`)
  for a rollback, like the other services.
- Ports: 28008 (production), 29008 (dev). The container listens on 8080.
- Data: `<root>/<env>/account/data/`, mounted at `/data`, owned by uid 1000, mode 0700.
  It holds `account.sqlite3` and its `-wal` and `-shm` files.
- Secrets: `config/account.env` and `config/yandex-oauth.env`, mode 0600, `format: raw`.
- Callers: the web server through its reverse SSH tunnel to the published port, and the bots
  at `<host LAN address>:28008`. Both arrive from Docker bridge addresses. Set
  `ACCOUNT_ALLOWED_NETWORKS` to the Docker bridge pools (172.16.0.0/12 on a default
  install). The service logs the address of each refused caller, so a wrong list shows up
  in `docker logs`.
- Health: the image checks `GET /readyz`. Liveness is `GET /healthz`.

Duplicate accounts made before the same-email rule. Back up the database first, then:

```sh
docker exec svoe-vino-lab-account-prod chto-za-vino-account merge --keep <username> --remove <username>
```

The command moves the login methods and the diary lists of `--remove` to `--keep` and deletes
`--remove` with its sessions. It changes nothing when both accounts have a login method of the
same provider. History: the union of the dates; for a date in both accounts, the date with the
earlier time stays; each wine gets the earliest and the latest time of its dates, and the
snapshot of `--keep` (or of `--remove` when `--keep` has none). Saved wines: for a wine in both
accounts, the row with the later `updated_at` stays with its note; when it has no note, it gets
the note of the other row. The switch of `--keep` stays. The list
limits apply again at the next record or save.

Backup. The image has no `sqlite3` program; the service has a command:

```sh
docker exec svoe-vino-lab-account-prod \
  chto-za-vino-account backup "/data/backups/account-$(date -u +%Y%m%dT%H%M%SZ).sqlite3"
find <root>/prod/account/data/backups -type f \
  \( -name 'account-*.sqlite3' -o -name '.backup-*.tmp' \) -mmin +10080 -delete
```

The command uses the SQLite online backup API. It writes a unique temporary file with mode
0600, publishes it with a hard link, and removes the temporary file in every case. It never
overwrites a file, also when two backups run at the same time. Keep backups 7 days (plan 04):
`-mmin +10080` is exactly 7 days (`-mtime +7` would keep files up to 9 days). Run the cleanup
at least once a day. Deleted accounts then leave the backups within 8 days at most.
