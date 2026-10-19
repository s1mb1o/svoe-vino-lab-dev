# Change log

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
