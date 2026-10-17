# Change log

## 2026-10-17

- A rejected album gets one reply per image (age gate, rate limit, full queue), the same as
  Telegram. All the replies quote the album message. Platform difference 1 changed. When the
  receipt owner fails to enter the queue, the next admitted image claims a new receipt. A failed
  rejection notice is logged and does not stop the other images of the album.
- Accept HEIC and HEIF images sent through «Файл» (`.heic`, `.heif`). The worker converts them
  to JPEG with `pillow-heif` 1.8.0 before moderation: the HEIF rotation is applied, EXIF data
  (with the location) is removed, only the primary image is used, and the longest side is at
  most 4096 pixels. A converted copy MUST fit `BOT_MAX_IMAGE_BYTES`. `chto-za-vino-max-probe`
  converts HEIC first. Synced `image_types.py`, `moderation.py`, and `probe.py` from
  `../telegram-bot`. Specification FR 2.1, 221.2–221.4; rules 26.5, 56.1.
- Run image CPU work and photo persistence in worker threads, the same as the Telegram bot
  (`28bc6981`, `f6653377`). One persistence lock per processor serializes the writes; a
  cancelled job waits for an active write. MAX-only writes also use it: sent messages, the
  refreshed attachment URL, and the read of the accepted copy for an administration retry.
- Synced the shared `fingerprints.py`, `quality.py`, `pipeline_artifacts.py`, and
  `result_card.py` from `../telegram-bot`. `sync_shared.py` now also shares
  `test_artifact_png.py`, `test_fingerprint_parity.py`, and `test_quality_performance.py`.
  Ported `test_cpu_dispatch.py` and `test_storage_dispatch.py`.
- Show a tentative wine card for a low-confidence match, the same as the production Telegram
  bot (`svoe-vino-lab` commit `4ce43a8f0`). A low Top-1 score gives
  «Пришлите еще фотографию, но скорее всего, это:». A low margin gives «У меня есть пара
  вариантов, скорей всего это:». The request keeps status `abstained`; single-photo feedback
  and alternatives work. Only an empty matcher answer gives «Не уверен». Reason: the live
  MAX run `20261016T211135Z-max-918f4447` had 18 abstentions; their stored Top-1 candidates
  give 14 exact and 1 alternative match. Specification FR 103–103.6, rules 26.1–26.4.
- Accept an image sent through the MAX menu «Файл»: a `file` attachment with the file name
  suffix `.jpg`, `.jpeg`, `.png`, or `.webp` (any letter case) goes through the photo
  pipeline. Two such files make an album. Another file still gets «Пришлите фотографию
  бутылки или этикетки». Specification FR 2.1–2.2, rule 26.5.
- Live check on the local bot, 2026-10-17 10:43 MSK: a WebP photo sent as an image and the
  same photo sent through «Файл» both gave the tentative card «У меня есть пара вариантов…»
  (score 0.91, margin 0.013). The `file` update had `filename`, `size`, and
  `payload` {`fileId`, `token`, `url`}. «✅ Совпало» on the tentative card was saved.
- Reject an image with more than one frame (animated PNG or WebP) with «Файл не похож на
  поддерживаемую фотографию.» (Codex review finding). An image file keeps its original bytes,
  and moderation checks only the first frame. Shared `image_types.py`, specification FR 221.1.
  FR 32 now counts accepted image files in an album.
- Synced the shared `result_card.py` (`format_result_caption(introduction=...)`),
  `image_types.py`, and their tests from `../telegram-bot`. 27 new tests (569 in total).
- Fixed three Codex review findings of the held-photo fix: the minor choice and the adult
  replay no longer depend on a successful callback answer; a held row is removed only after
  its photo was admitted or explicitly rejected, so a restart during the replay loses no
  photo; scheduled retention removes held rows after 24 hours, not after the 30-day request
  retention. 4 new tests.
- Fixed two second-round Codex findings: an API failure in one chat (receipt or notice) no
  longer stops the replay of the other held photos.
- Fixed: a photo sent before the age confirmation was lost. After «Мне есть 18 лет» the
  bot answered only with the start text. Now the age gate keeps the message ID of the photo
  (table `age_pending_photos`, no image data). The adult choice reads the message again with
  `GET /messages/{messageId}` and queues its photos. The minor choice, the user data
  deletion, retention, and a 24-hour limit remove the held IDs. A message that cannot be read
  again gets «Не удалось получить фотографию, отправленную до подтверждения возраста.
  Отправьте её ещё раз.». Specification FR 225–227, README step 7, smoke test, 7 new tests.

## 2026-10-16

- Translated `README.md` to Russian (owner decision). Added the section «Первая настройка:
  токен и ID администратора»: where to get `MAX_BOT_TOKEN`, how to keep it in the macOS
  Keychain (service `chtozavino-max-bot-token`), how to check it with `GET /me`, how to write
  it into `config/max-bot.env` on gx10 without printing it, and how to find
  `BOT_ADMIN_USER_ID` with `GET /updates` or `/privacy`. Rule 7 of `CLAUDE.md` now names the
  exception.
- Removed the double point at the end of the queue receipt («около 40 сек..»), the same as in
  the Telegram bot (issue #11).
- Removed platform differences 9 to 12 from the specification. The Telegram bot now has the
  same fixes.

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
