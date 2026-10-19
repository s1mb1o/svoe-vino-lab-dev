# ChangeLog

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
