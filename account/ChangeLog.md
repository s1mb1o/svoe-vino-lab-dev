# ChangeLog

## 2026-10-20 — Review fixes for the diary lists

Review of the plan 07 commit `614cc635`. Fixed:

- `POST /v1/bot/history/undo` and `POST /v1/bot/history` (for `replaces`) accept `at`: the time of the
  result card, integer Unix seconds UTC. The date to remove is the Moscow day of `at`, so a tap after
  midnight removes the date of the card, not of today. Without `at`, or with `at` outside
  [now − 48 h, now + 60 s], the date is today (no error).
- A chat removes only a date of its own source (`telegram` or `max`). A date of another source stays,
  for example a site match of the same morning; `undo` then answers `absent`.
- Snapshots merge: the keys of a newer snapshot override, and missing keys keep the stored values, for
  the site history, the chat history, and saved `PUT`. A chat card without sugar or grapes no longer
  erases the snapshot of the site. A union above 2,048 bytes takes the newer snapshot.
- `merge` sets `first_met_at` and `last_met_at` of the kept wines from their dates, so `last_met_at` is
  never later than the newest date.
- 8 new tests (152 in total).

## 2026-10-20 — History and saved wines (plan 07, #71, #64)

Owner request: a history of every wine that a person matched on the site and in the linked chats,
and a second list «Сохранённые» with four statuses. Plan: `../docs/plans/07_diary-history-and-saved.md`.

- Schema `005_diary_lists.sql`: `users.save_history` (on by default), `history_wines`,
  `history_days`, `saved_wines`. Account deletion removes both lists (`ON DELETE CASCADE`).
- New module `diary.py`. Site routes (consumer `web`, session): `PATCH /v1/me` (`save_history`),
  `GET`/`POST`/`DELETE /v1/me/history`, `GET`/`DELETE /v1/me/history/{slug}`,
  `DELETE /v1/me/history/{slug}/days/{met_on}`, `GET /v1/me/saved`, `GET /v1/me/saved/slugs`,
  `PUT`/`DELETE /v1/me/saved/{slug}`. `GET /v1/me` shows `save_history`.
- One date for each wine and calendar day in Europe/Moscow. The first source and time of the day
  stay. A repeat on the same day changes only the snapshot. Limits: 2,000 wines and 366 dates for
  each wine (the oldest record goes), 500 saved wines (409 `saved_full`).
- Bot routes `POST /v1/bot/history` and `POST /v1/bot/history/undo` for `telegram-bot` and
  `max-bot`. The consumer gives the messenger. A chat without a linked diary gets `not_linked`
  with HTTP 200. `replaces` removes today's date of the rejected wine. These are the first routes
  of the `max-bot` consumer.
- `GET /v1/app/wines` returns the history with an opaque cursor of at most 184 characters
  (`last_met_at` and the slug). A bad cursor gets 400 `invalid_cursor`.
- Wine snapshots: known keys only, strings of 1–200 characters, at most 12 grapes of 1–80
  characters, at most 2,048 bytes of JSON; else 422 with the field name only.
- Without the time zone database, the service uses UTC+3 for Moscow.
- The operator command `merge` moves both lists.
- 42 new tests (144 in total after the rebase on the MAX and email fixes).

## 2026-10-20 — Code email in HTML

Owner request: show the code as clearly as the Link (Stripe) email does.

- The code email is `multipart/alternative`: the same text, and an HTML card with the title, one line of
  text, and the code in 40 px type in two groups (`317 220`; a copy gives the digits without a space).
  No images and no links.
- The subject starts with the code: «317 220 — код для входа в «Винный дневник»».
- 102 tests.

## 2026-10-20 — Forms of MAX launch data

The refusal log of the first real link said «launch data has no hash»: the MAX client did not give the plain
launch string. The service now unwraps the URL fragment form (`WebAppData=…&WebAppPlatform=…`) and the launch
string that is URL-encoded once more, then runs the same signature check. A «no hash» refusal names the keys
(never the values). 101 tests.

## 2026-10-20 — MAX launch date and refusal logs

The first real MAX link failed with `launch_expired` twice, also with `MAX_INITDATA_MAX_AGE_SECONDS=3600`.

- `auth_date` above 10^11 is milliseconds (the MAX documentation says seconds).
- A refused launch logs its reason (signature, expired with the age, ip missing or mismatch, reused). The log
  never holds the launch data. 100 tests.

## 2026-10-19 — One name per consumer token

Owner: `ACCOUNT_TELEGRAM_BOT_TOKEN` read like the Telegram bot token; keep one name for each token in
the service and in its consumer.

- `ACCOUNT_TELEGRAM_BOT_TOKEN` → `ACCOUNT_TELEGRAM_TOKEN`, `ACCOUNT_MAX_BOT_TOKEN` → `ACCOUNT_MAX_TOKEN`.
  `ACCOUNT_WEB_TOKEN` keeps its name. The website and the Telegram bot read the same names. A value
  under an old name stops the start with a message that names the new one.
- `.env.example` and `README.md` say that a consumer token is a random secret, not a bot token.

## 2026-10-19 — No recent-login rule; sessions without expiry

Owner decision: "remove 15 minutes period for account operations", "only ask confirmations",
"keep account logged in endlessly".

- Removed the 15-minute recent-login rule (`reauth_required`) from account deletion, unlink, email and
  Yandex ID linking, Telegram link codes, MAX linking, and application token creation. The site asks
  for a confirmation instead.
- Web sessions have no expiry (`SESSION_TTL` of 100 years): a session ends at logout or account
  deletion. `max` sessions keep 1 day (MAX login is off).
- Tests rewritten for the new rules (98 in total).

## 2026-10-19 — Review fixes for application tokens

Review of `99015725` and `2ada337b` (a Claude review agent) found nothing high-severity. Fixed:

- The failed-token limit groups IPv6 clients by /64, and a budget of 600 failed checks per minute for
  all clients stops address rotation from making unlimited lookups.
- `SlidingWindow` prunes old keys at most once a window instead of on every event above 50,000 keys.
- 3 new tests (98 in total).

## 2026-10-19 — Application tokens (#65)

- Schema `004_app_tokens.sql`. `GET/POST /v1/me/app-tokens`, `DELETE /v1/me/app-tokens/{id}` (session;
  creation needs a login in the last 15 minutes). Format `cvpat_` + 32 random bytes; only the SHA-256
  hash is stored. Lifetime 30, 90, or 365 days; at most 5 active tokens.
- `GET /v1/app/profile` and `GET /v1/app/wines` for the `web` consumer with `X-App-Token` and
  `X-Client-IP`. Every refused token gets the same 401 `app_token_invalid`. 60 requests per minute per
  token; 20 failed checks per minute per client address, then 429 with `Retry-After`.
  `last_used_at` is written at most once a minute. A token is never a session.
- Preferences are `null` and wines are an empty list until the diary part of #48 exists.
- Account deletion removes the tokens; logout keeps them. The purge removes tokens 30 days after
  their end. 15 new tests (95 in total).

## 2026-10-19 — Telegram link review fixes

Review of `ffbde5c8` (a Claude review agent; Codex was over its usage limit). Fixed:

- A link code belongs to the first Telegram user who claims it (schema `003_link_claim.sql`,
  `link_codes.claimed_by`). Another user gets `invalid_link_code` for claim and confirm. A confirm
  without a claim is refused. A repeated confirm by the same user answers `linked` again while the
  link exists, so a double tap does not show an error.
- `POST /v1/me/links/telegram` needs a login in the last 15 minutes. A stolen old session can no
  longer replace the owner's Telegram with its own. A new code deletes the open codes of the account.
- 5 new tests (80 in total).

## 2026-10-19 — Messenger unlink without a fresh login

- `DELETE /v1/me/identities/{provider}` needs a login in the last 15 minutes only for a login
  method (email, Yandex ID). Unlinking Telegram or MAX only removes access, so the site can offer
  «Отвязать» without a new login. 2 new tests (75 in total).

## 2026-10-19 — Accounts with the same email join

- A login of an unknown identity joins the one account with the same email instead of a new sign-up: Yandex ID by its `default_email`, an email code by the address of a Yandex identity (owner request; the owner had two accounts for one address).
- Schema `002_identity_email.sql`: `identities.email` (filled for email identities), an index, and `signup_tickets.email`.
- New operator command `chto-za-vino-account merge --keep <username> --remove <username>` for duplicates made before this rule.
- 8 new tests (73 in total).

## 2026-10-19 — Second review fixes, manual tests

Codex reviewed `64545eb5..330a5c2d`. Fixed:

- The Compose example sets `ACCOUNT_ENVIRONMENT`, `ACCOUNT_DATABASE`, `ACCOUNT_HOST`, and
  `ACCOUNT_PORT` in `environment`. Before, values copied from `.env.example` into
  `config/account.env` moved the database into the read-only root, bound the server to
  loopback, and allowed the console mailer.
- `backup` writes a unique temporary file (mode 0600), publishes it with a hard link, and
  removes the temporary file in every case. Two backups with one name cannot overwrite each
  other; an interrupted backup leaves no file behind.
- The retention command uses `-mmin +10080` (exactly 7 days) and also removes old temporary
  files.

Also:

- `MANUAL_TESTS.md`: the tests that need gx10, real mailboxes, a real Yandex account, other
  LAN hosts, and phones.
- The image builds and runs on `linux/arm64` (checked with emulation: `uname -m` is
  `aarch64`, `/readyz` answers, `backup` works). A request from the host arrived from the
  Docker bridge gateway `172.17.0.1`, and the refused-caller log named it.

## 2026-10-19 — Ready for the GPU host

- The Compose example follows the matcher and the bots: project and container names
  `svoe-vino-lab-account-<env>`, published port `0.0.0.0:28008`, `init`, two raw environment
  files (the Yandex ID file is optional). No external Docker network.
- The pinned base images support `linux/arm64` and `linux/amd64` (checked with
  `docker buildx imagetools inspect`). The image builds for `linux/amd64`.
- The service logs the address of a refused caller.
- New command `chto-za-vino-account backup <file>` (SQLite online backup, mode 0600).

## 2026-10-19 — Port 28008

- The default port is 28008 (production) and 29008 (dev). Slot 07 belongs to dinner-lens.

## 2026-10-19 — Review fixes

Codex reviewed commit `64545eb5`. Fixed and covered by tests (`tests/test_review_fixes.py`):

- Linking email, Yandex ID, or MAX needs a recent login at the start and the end. Before, an
  old session could replace the email and then log in through it to delete the account.
- `uv.lock` is committed (the root `.gitignore` ignores `*.lock`). The Docker build needs it.
- Email send limits are checked and recorded atomically.
- Yandex ID start needs `X-Client-IP`: 30 per hour per address, at most 10,000 open flows.
  Telegram link codes: 10 per hour per account.
- The login-method rule counts only email and Yandex ID, also with MAX login on.
- A used MAX launch ID is kept while the launch is valid. `MAX_INITDATA_MAX_AGE_SECONDS` is
  at most 3600.
- Sessions, sign-up tickets, mail, and request models hide secrets in `repr`.
- Validation errors name an unknown key `unknown_field` instead of echoing it.
- Malformed percent-encoding in MAX launch data gives `invalid_launch`, not HTTP 500.
- A MAX test vector computed with OpenSSL checks the signature algorithm independently.

## 2026-10-19 — First version: authorization only

- Login by email code and by Yandex ID (OAuth 2.0 code flow with PKCE), sign-up with a
  username and the consent and terms versions, sessions, logout.
- Linking: email (address change), Yandex ID, MAX (signed mini-app launch data), Telegram
  (one-time deep-link code with bot confirmation). MAX login is off by default.
- Unlink and account deletion with a recent login; at least one login method stays.
- Network allow-list, consumer bearer tokens, a 16 KiB body limit, email send limits.
- Docker image and Compose example. No deployment yet.
- Checks: `./scripts/verify.sh`.
