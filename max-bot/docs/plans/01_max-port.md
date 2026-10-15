# Port of the Telegram bot to the MAX messenger

Date: 2026-10-15

Status: Accepted after review (Codex gpt-6.1-sol, 2026-10-15). See "Review changes".

## Goal

Add `max-bot/`, a MAX messenger bot with the same functionality as `telegram-bot/`.
The MAX bot is registered as «Что за вино?» with the nickname `@se14697933_bot`.
The bot MUST keep every user flow, safety rule, data rule, and operator tool of the
Telegram bot. A difference is permitted only where the MAX platform has no equivalent.
Each difference MUST be listed in `docs/specification.md`, section "Platform differences".

## Sources

- MAX documentation: <https://dev.max.ru/docs>, <https://dev.max.ru/docs-api>.
- Official OpenAPI schema: <https://github.com/max-messenger/api-schema> (version 0.0.33).
- Official MAX agent skill: <https://github.com/max-messenger/max-agents-skill>.
- Snapshots of these sources: `<workspace>/wiki/raw/`.

## Package layout

`max-bot/` is a separate Python project. It does not import `telegram-bot/`.
The reason: the Docker image builds from one directory (`git archive "$REV:max-bot"`),
and the MAX bot must not depend on `aiogram`.

```
max-bot/
  pyproject.toml        package chto-za-vino-max-bot, Python 3.12, uv
  config.yaml           the same endpoint configuration as telegram-bot
  certs/russian_trusted_root_ca.pem
  src/chto_za_vino_max_bot/
    max_api.py          thin async MAX Bot API client (httpx)
    updates.py          normalized update model, update parser
    polling.py          long polling with a persistent marker
    webhook.py          webhook receiver (FastAPI) with secret check
    app.py              handlers, PhotoProcessor, run()
    config.py storage.py profile.py profile_sync.py admin_web.py   adapted copies
    work_queue.py matcher.py moderation.py quality.py pipeline_artifacts.py wine.py
    result_card.py fingerprints.py image_types.py http_api.py data_lifecycle.py
    artifact_backfill.py probe.py host_demo.py                       shared copies
  tests/
```

## Shared modules

The shared modules are copies of the `telegram-bot` modules.
`tests/test_shared_modules.py` applies a fixed substitution table to each Telegram module and
compares the result with the MAX module. The test fails on any other difference.
The test skips when `../telegram-bot` is not present (for example, in a Docker build).
The substitution table contains only names: the package name, the word `Telegram`, and the
artifact key `telegram_result`. A logic change in a shared module MUST be made in both bots.

## MAX API client

- Base URL `https://platform-api2.max.ru`. The value is configurable (`MAX_API_BASE_URL`).
- Authentication: header `Authorization: <token>`. No `Bearer` prefix. No query token.
- TLS: the system trust store plus the Russian Trusted Root CA from `certs/`.
  A test checks the certificate SHA-256 fingerprint
  `D2:6D:2D:02:31:B7:C3:9F:92:CC:73:85:12:BA:54:10:35:19:E4:40:5D:68:B5:BD:70:3E:97:88:CA:8E:CF:31`.
  Upload and download hosts use the normal trust store.
- Rate limits: one global token bucket at 30 requests per second.
  One bucket per chat at 2 operations per second for send, edit, delete, and callback answer.
- Errors: a non-2xx status raises `MaxApiError(status, code, message)`.
  A 2xx `SimpleQueryResult` with `success=false` also raises `MaxApiError`.
  HTTP 429 and 5xx retry three times with backoff.
- `attachment.not.ready`: the send retries after 1, 2, and 4 seconds.
- Reply: a send with a reply link that MAX rejects with HTTP 400 or 404 is sent once more
  without the link. This copies the Telegram `allow_sending_without_reply=True` behavior.
  A rejected request did not create a message, so this cannot duplicate a message.
  A send is not repeated after a 5xx answer or a transport error, because the first send can
  have succeeded. Only HTTP 429 is repeated for a send.
- Image send: `POST /uploads?type=image`, multipart field `data` to the returned URL, then the
  photo token map in the `image` attachment.
- Methods: `get_me`, `get_updates`, `send_message`, `edit_message`, `delete_message`,
  `answer_callback`, `upload_image`, `download_image`, `get_message`, `set_commands`,
  `get_subscriptions`, `subscribe`, `unsubscribe`.
- Logs: the client never logs a token, an image URL, or a message text. Client exceptions do
  not contain a URL and are raised `from None`, so a traceback does not contain the URL of an
  `httpx` error. The `httpx` and `httpcore` loggers are set to `WARNING` because `httpx` logs
  each request URL at `INFO`. The log formatter redacts the bot token, the HTTP API token, and
  the webhook secret.

## Update delivery

MAX documentation requires a webhook for production. Long polling is limited in rate and in
event retention (`docs-api/methods/GET/updates`). The bot supports both modes with
`MAX_UPDATE_MODE`. The default is `webhook` when `BOT_ENVIRONMENT=production` and `polling`
otherwise. Production polling requires the explicit override `MAX_ALLOW_PRODUCTION_POLLING=true`.

- `webhook`: a separate FastAPI listener (`MAX_WEBHOOK_HOST`, `MAX_WEBHOOK_PORT=28006`,
  `MAX_WEBHOOK_PATH`). A TLS proxy publishes it on `https://<host>/<path>` port 443.
  The receiver compares `X-Max-Bot-Api-Secret` in constant time, writes the update to the
  durable inbox, and answers HTTP 200. When the inbox write fails, it answers HTTP 503, and MAX
  repeats the delivery. At startup the bot calls `POST /subscriptions` with the URL, the update
  types, and the secret when `MAX_WEBHOOK_SUBSCRIBE=true`.
- `polling`: `GET /updates` with `timeout=30`, `limit=100`, and the types `message_created`,
  `message_callback`, `bot_started`. One SQLite transaction writes the batch to the inbox and
  stores the next marker. The minimum interval between calls is 300 ms. Errors use backoff from
  1 to 30 seconds. The bot refuses to start in polling mode when a webhook subscription exists,
  because MAX does not deliver long polling events while a subscription is active.

### Durable inbox

Both modes write each update to the SQLite table `update_inbox` before it is handled. The inbox
gives the arrival order (`inbox_id`) and at-least-once handling after a crash. One dispatcher
task handles the inbox rows in order and marks each row as processed. One failed update MUST NOT
stop delivery: the dispatcher logs the failure and marks the row. A crash before the mark
replays the row at the next start; photo reservations are idempotent by
`(chat_id, message_id, photo_index)`.
The unique `update_key` drops a repeated delivery:
`message_created:<mid>`, `message_callback:<callback_id>`,
`bot_started:<chat_id>:<user_id>:<timestamp>:<payload>`.
Retention deletes processed rows after one day and all rows after the data retention period.
User deletion deletes the rows of the user.

## Telegram to MAX mapping

| Telegram | MAX |
|---|---|
| `/start` command, `/start privacy` deep link | `bot_started` update with `payload`, and the text `/start [args]` |
| `t.me/ChtoZaVinoBot?start=privacy` | `max.ru/se14697933_bot?start=privacy` |
| Private chat: `chat.id == user.id` | Dialog: `recipient.chat_type == "dialog"`; the chat ID differs from the user ID |
| `message.photo[-1].file_id` | `image` attachment: `photo_id`, `token`, `url` |
| Album: one message per photo with `media_group_id` | One message with two or more `image` attachments |
| `message.reply(...)` | `POST /messages` with `link={type: reply, mid}` |
| `send_photo(caption, reply_markup)` | upload, then one message with text, `image` attachment, and `inline_keyboard` attachment |
| `edit_message_text` | `PUT /messages` with text and the complete attachment list |
| `edit_reply_markup` on `callback.message` | `PUT /messages` on the clicked message ID, with its stored text, format, and image token plus the new keyboard |
| `callback.answer(text, show_alert)` | `POST /answers` with `notification`; MAX has no alert dialog |
| `parse_mode=HTML` | `format: "html"` |
| `LinkPreviewOptions(is_disabled=True)` | `disable_link_preview=true` on `POST /messages` (edits have no such option) |
| `set_my_commands` with an admin chat scope | `PATCH /me/commands` with public commands only; MAX has no command scope |
| `set_my_description`, `set_my_short_description` | No API. The description is set on business.max.ru and passes moderation |

## Album behavior

One MAX message can contain up to 12 images and videos. The bot treats a message with two or
more image or video attachments as an album, the same as a Telegram media group with a photo
and a video. Only the images are processed, in attachment order. Each image is a separate request in the rate limit, the queue, and storage.
The first image request owns the album receipt. Album results have no feedback buttons.
Each result replies to the source message. A rate-limit, queue-capacity, or age-gate rejection
gives one reply for the message, not one reply for each image. When the limit is reached in the
middle of an album, the admitted images keep their requests, and the remaining images use no
quota. A replay of the update admits only the images that do not have a request yet.

The bot accepts `image` attachments of the message body. For a forwarded message, the bot
accepts the `image` attachments of the forwarded message. Files and other attachments get the
fallback text, the same as a Telegram document.

## Storage changes

The MAX bot uses its own SQLite database and data root. The request table changes:

- `message_id TEXT` (MAX `mid`), `photo_index INTEGER`, and `UNIQUE(chat_id, message_id, photo_index)`.
- `chat_type TEXT` for the admin check of a restored request.
- `max_photo_id`, `max_photo_url`, `max_photo_token` replace the Telegram file fields.
- `photo_source` (`body` or `forward`): where the image attachment is in the source message.
- Table `sent_messages(message_id, request_id, chat_id, text, text_format, photo_token)`:
  every bot message with a callback keyboard (result, rejection, alternative list). A callback
  edits the clicked message (`callback.message.mid`) and rebuilds its body from this table.
  When the row is absent, the callback uses the plain text and the image tokens of the callback
  message. When the callback has no message, the bot answers the callback and does not edit.
- Table `update_inbox`: see "Durable inbox".
- `request_source` is `max` or `api`. An API request uses `message_id = "api:<request_id>"`.
- `bot_state(key, value)` keeps the long polling marker.

## Image download

A queue job keeps the image URL, the message ID, and the photo index. It does not keep image
bytes while it waits. The worker downloads the image with the configured size limit.
Only HTTPS URLs are accepted. `MAX_MEDIA_ALLOWED_HOSTS` can restrict the host suffixes.
When the download fails, the worker reads the message again with `GET /messages/{mid}` and
retries once with the URL of the same `photo_id` (best effort: MAX does not document URL
renewal). An administration retry reads the accepted local copy and moderates it again; it does
not download the image again.

## Configuration

Shared settings keep the `BOT_*` names and defaults of the Telegram bot, except the ports:
`BOT_HTTP_API_PORT=28004`, `BOT_ADMIN_WEB_PORT=28005`. The Telegram bot uses 28002 and 28003.
New settings: `MAX_BOT_TOKEN`, `MAX_API_BASE_URL`, `MAX_API_CA_FILE`, `MAX_UPDATE_MODE`,
`MAX_ALLOW_PRODUCTION_POLLING`,
`MAX_POLL_TIMEOUT_SECONDS`, `MAX_WEBHOOK_URL`, `MAX_WEBHOOK_SECRET` (at least 32 characters,
`[A-Za-z0-9_-]`), `MAX_WEBHOOK_HOST`, `MAX_WEBHOOK_PORT`, `MAX_WEBHOOK_PATH`,
`MAX_WEBHOOK_SUBSCRIBE`, `MAX_MEDIA_ALLOWED_HOSTS`.
`BOT_ADMIN_USER_ID` is a MAX user ID.

## User-visible text

The Russian text is the same as the Telegram bot text. Only platform names change:
"Telegram user ID" becomes "MAX user ID". The privacy answer adds the user's own MAX user ID,
because a MAX user has no simple way to find it.

## Tests

- Copies of the shared module tests, with the same substitution table.
- Rewritten transport tests: age gate, admin commands, feedback, album, processor, profile.
- New tests: API client (auth header, errors, `success=false`, 429 retry, upload,
  `attachment.not.ready`, reply fallback), update parser, polling marker persistence and order,
  webhook secret and duplicate filter, CA fingerprint, shared module drift.
- `scripts/verify.sh` runs the lock check, Ruff, pytest, and the host demo.

## Open items for the owner

1. Production update mode: a webhook needs a public HTTPS name on port 443 that forwards to
   `gx10`. Long polling works without it, but MAX does not recommend it for production.
2. Platform requirements 2.1 and 3.1 (`https://dev.max.ru/docs/legal/requirements`): the
   operator details and an explicit acceptance of the content rules. The owner decides the text.
3. The contact `@s1mb1o` in the start text is a Telegram username.
4. The bot card description on business.max.ru: at most 200 characters, no 18+ content.

## Review changes

Codex reviewed this plan on 2026-10-15. The plan now has these changes:

1. Production uses a webhook by default. Production polling needs an explicit override.
2. A durable SQLite inbox replaces the in-memory webhook queue, with persistent deduplication.
3. The deduplication keys contain the message, callback, or chat and user identity.
4. A send is repeated only after HTTP 429. The reply fallback runs only after HTTP 400 or 404.
5. Callback edits target the clicked message and use per-message stored text and format.
6. A message with an image and a video is an album.
7. String message IDs, the photo source, the user ID, and the chat type are restored after a
   restart. An administration retry uses the accepted local copy.
8. Exceptions do not carry URLs into logs; the webhook secret is redacted.

Not changed: the Telegram bot records `recognized` before it delivers the result, so a crash
between the two steps loses the result message. The MAX bot keeps this behavior for parity.

## Code review changes

Codex reviewed the implementation on 2026-10-16. The tests of the port found the same defects.
The implementation now has these changes:

1. An administration retry takes the accepted local path from storage when it enters the queue,
   and a restart restores the path. Processing clears the moderation fields, so a later lookup
   cannot find the path.
2. A message that contains only a forwarded message can have no body. The bot gives it the ID
   `forward:<chat_id>:<timestamp>:<original mid>`, never uses it as a reply target, and does not
   read it again with `GET /messages/{mid}`.
3. A failed album receipt loses only its image. The next image claims the receipt, as in the
   Telegram bot, where each album photo is a separate update.
4. An album image without the receipt gets its result as a reply when the result photo fails.
   The Telegram bot has the same defect and sends no result.
5. A repeated alternative choice or filter appeal removes the keyboard again.
6. The client takes the chat slot before the global slot, so the global limit applies to the
   actual send time.
7. `/users` with a huge page number and `/reset_limit` with a huge user ID answer instead of
   failing. The Telegram bot has the same defects.
8. Command arguments start after any whitespace, the same as aiogram.

## Commit review changes

Codex reviewed the commits on 2026-10-16. The implementation now has these changes:

1. An administration retry keeps the date directory of the first receipt for its source copy and
   its artifacts. Before, a retry on another UTC day wrote files under the retry date, and
   retention and user deletion did not find them. The Telegram bot has the same defect.
2. The client marks the chat limit and the global limit together at the send time. A FIFO
   lock per chat and a FIFO global lock keep the waiting order, so a new request cannot overtake
   a waiting one (a follow-up review found starvation in a lock-free variant). A late wakeup
   marks the actual time.
3. A repeated feedback press follows the stored value. A stale "❌ Не совпало" button after a
   saved positive answer removes the keyboard instead of showing alternatives that cannot be
   saved. The Telegram bot has the same defect.
4. The README states that a moderation rejection still gives one illustration per album photo.
