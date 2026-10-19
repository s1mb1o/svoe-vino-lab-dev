# ChangeLog

## 2026-10-19 — First version: authorization only

- Login by email code and by Yandex ID (OAuth 2.0 code flow with PKCE), sign-up with a
  username and the consent and terms versions, sessions, logout.
- Linking: email (address change), Yandex ID, MAX (signed mini-app launch data), Telegram
  (one-time deep-link code with bot confirmation). MAX login is off by default.
- Unlink and account deletion with a recent login; at least one login method stays.
- Network allow-list, consumer bearer tokens, a 16 KiB body limit, email send limits.
- Docker image and Compose example. No deployment yet.
- Checks: `./scripts/verify.sh`.
