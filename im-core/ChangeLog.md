# Change log

## 2026-10-20

- Review fix: `DiaryHistory.undo(..., at=...)` and `DiaryHistory.record(..., replaces=...,
  at=...)` send the optional `at` (Unix time of the result card). The account service then
  changes the Moscow day of the card (at most 48 hours back), not the day of the button press.
  A card at 23:58 and a press at 00:02 no longer answer `absent`. An unknown time is omitted.
  1 new test (27 in `tests/test_diary.py`).
- New module `diary.py` for the «Винный дневник» history of both bots (plan
  `../docs/plans/07_diary-history-and-saved.md`, issue #71). `DiaryHistory.record()` sends
  `POST /v1/bot/history` (with `replaces` for a selected alternative) and `DiaryHistory.undo()`
  sends `POST /v1/bot/history/undo`. Both return at once and never raise: a background task, one
  attempt, a 2 s timeout, at most 8 calls at the same time. A failure gets one warning with the
  HTTP status or the exception type only, never the user ID, the slug, or the token.
  `wine_snapshot()` builds the snapshot within the service limits (strings of 1 to 200
  characters, at most 12 grapes of 1 to 80 characters, at most 2,048 bytes). The diary color is
  the matcher `category` («Красное»); the tint `color` is the fallback. A card without data
  (`unknown_wine`) gives no snapshot.
- `Wine` has the optional `region` of the matcher card. `wine_card()` stores it. An absent or
  invalid region gives None and does not refuse the card.
- New tests: `tests/test_diary.py` (26) and one region test in `tests/test_wine.py` (4 cases).

## 2026-10-19

- `CatalogImageLoader` accepts the static wine images of `https://chtozavino.ru` (plan
  `../docs/plans/06_wine-images.md`) and still accepts `https://api.vino-svoe.ru` until each
  matcher gives the new addresses (`CATALOG_IMAGE_HOSTS`). The parameter `allowed_host` is now
  `allowed_hosts`; no caller passed it. New test:
  `test_catalog_image_loader_accepts_the_static_wine_images`. 160 tests pass; the Telegram bot
  (251) and the MAX bot (486) pass with the change.

## 2026-10-18

- Fixed `ArtifactStore` for a relative data root, for example `BOT_DATA_ROOT=./data` of
  `.env.example`. `save()` failed in `relative_to`, so no pipeline artifact was stored. The
  artifact root is now absolute. New test: `tests/test_files.py` (issue #10, comment 6.2).

## 2026-10-17

- Created the package from the 12 modules that `max-bot/scripts/sync_shared.py` copied from
  `telegram-bot/`: `fingerprints`, `host_demo`, `http_api`, `image_types`, `matcher`,
  `moderation`, `pipeline_artifacts`, `probe`, `quality`, `result_card`, `wine`, `work_queue`.
  Their 11 tests moved here too.
- Added `files.py` (`ArtifactRecord`, `ArtifactWrite`, `ImageStore`, `ArtifactStore`) and
  `texts.py` (`LEGAL_NOTICE`). Both were identical in the two bots.
- Platform values are parameters: `result_artifact(platform=..., platform_title=...)` and
  `Matcher(upload_name=...)`. The moderation error, the HTTP API description, and the queue logger
  name (`chto_za_vino_core.queue`) are platform-neutral. `probe.main(upload_name=...)` takes the
  upload name of the calling bot. Plan: `../docs/plans/01_im-core-package.md`.
