# ChangeLog

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

Codex reviewed commit `abc49baa`. Fixed and covered by tests (`tests/test_review_fixes.py`):

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
