# Change log

## 2026-10-15

- Added the MAX messenger bot «Что за вино?» (`@se14697933_bot`), a port of the Telegram bot
  with the same user flows, safety rules, data rules, administration tools, and HTTP API.
- Added a thin MAX Bot API client with header authentication, the bundled Russian Trusted Root
  CA, per-chat and global rate limits, `success: false` detection, `attachment.not.ready`
  retries, and a reply fallback that cannot duplicate a message.
- Added a durable SQLite update inbox for the webhook and long polling modes, with persistent
  duplicate keys and replay after a restart.
- Added MAX album handling: one message with two or more images or videos.
- Added per-message storage of keyboard messages, so a callback rebuilds the clicked message.
- Added `scripts/sync_shared.py` and a drift test for the core modules copied from the
  Telegram bot.
- Fixed after the code review: administration retries use the accepted local copy also after a
  restart; forward-only messages without a body are accepted; one failed album receipt no
  longer drops the album; album results reach the user when the result photo fails; repeated
  callbacks repair a stale keyboard; the global rate limit applies at the send time; huge
  `/users` pages and `/reset_limit` IDs get an answer; command arguments after a line break
  are read.
- Fixed after the commit review: retry files keep the first receipt date, so retention and
  user deletion find them; both rate limits are checked at the send time; a stale feedback
  button follows the stored answer; the README describes album moderation rejections correctly.
