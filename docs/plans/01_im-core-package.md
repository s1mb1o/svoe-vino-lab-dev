# Plan 01: Shared core package `im-core`

Date: 2026-10-17. Branch: `feature/im-bot`.

## Goal

Remove the copied modules of `telegram-bot/` and `max-bot/`.
Put them in one package that both bots use.

## Owner decisions

- Folder `im-core/`, Python package `chto_za_vino_core`.
- Move 12 modules: `fingerprints`, `host_demo`, `http_api`, `image_types`, `matcher`, `moderation`,
  `pipeline_artifacts`, `probe`, `quality`, `result_card`, `wine`, `work_queue`.
- Move the identical storage parts `ArtifactRecord`, `ArtifactWrite`, `ImageStore`, and
  `ArtifactStore` (new module `files`), and `LEGAL_NOTICE` (new module `texts`).
- Keep `admin_web`, `artifact_backfill`, and `data_lifecycle` in both bots. They use the
  `Repository` and `Settings` of each bot. `max-bot/scripts/sync_shared.py` keeps copying them.

## Design

1. `im-core/` is a uv project with `hatchling`, its own tests, `README.md`, `CLAUDE.md`, and
   `ChangeLog.md`.
2. Each bot depends on `chto-za-vino-core` through `[tool.uv.sources]` with
   `path = "../im-core"` and `editable = true`.
3. A value that the sync script changed per platform becomes a parameter, so stored data does not
   change:
   - `pipeline_artifacts.result_artifact(body, platform=..., platform_title=...)` keeps the
     artifact keys `telegram_result` and `max_result` and their titles.
   - `Matcher(..., upload_name=...)` keeps the upload names `telegram-photo` and `max-photo`.
4. Internal texts become neutral: the moderation error, the HTTP API description, and the queue
   logger name `chto_za_vino_core.queue`. Both bots attach the redacting log handler to the root
   logger, so the core logs keep the redaction.
5. The 11 shared tests of the moved modules move to `im-core/tests/`. `test_assets.py` stays
   synced, because it checks the asset of each bot.
6. The Docker build context becomes the repository root subset `im-core/` plus the bot folder:
   `git archive "$REV" im-core max-bot | docker build -f max-bot/Dockerfile -`.

## Verification

- `uv run pytest` and `uv run ruff check .` in `im-core/`, `telegram-bot/`, and `max-bot/`.
- `max-bot/scripts/verify.sh`, which also runs the core checks.
- The Docker build is not tested locally: the Docker daemon on the Mac does not answer.

## Risks

- Production Telegram is built from `svoe-vino-lab` (GitLab). This change does not reach it.
- The gx10 build commands in the runbooks change. An old command fails, because the build context
  has no `im-core/`.
