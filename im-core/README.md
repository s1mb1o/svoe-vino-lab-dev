# im-core

Shared core of the bots «Что за вино?» for Telegram (`../telegram-bot`) and MAX (`../max-bot`).
Python package: `chto_za_vino_core`.

## Contents

| Module | Purpose |
|---|---|
| `image_types.py` | JPEG, PNG, and WebP detection; HEIC and HEIF conversion to JPEG. |
| `moderation.py` | ShieldGemma moderation client and the moderation JPEG. |
| `quality.py` | Blur, glare, and SAM3 bottle and label checks. |
| `fingerprints.py` | Perceptual and difference image hashes. |
| `matcher.py` | Client of the matcher `/v1/match` endpoint. |
| `wine.py` | Wine card model. |
| `result_card.py` | Result caption and catalogue result image. |
| `pipeline_artifacts.py` | Pipeline artifacts for the administration inspector. |
| `files.py` | File stores for source images and artifacts. |
| `texts.py` | User texts that both bots show. |
| `work_queue.py` | Shared FIFO work queue. |
| `http_api.py` | Internal synchronous recognition API. |
| `diary.py` | Background history records of «Винный дневник» (`DiaryHistory`) and the wine snapshot. |
| `probe.py`, `host_demo.py` | Diagnostic commands. |

A platform value is a parameter. Examples: `result_artifact(platform=...)` and
`Matcher(upload_name=...)`. The bots keep their stored keys `telegram_result` and `max_result`.

The bots use the package as an editable path dependency:

```toml
[tool.uv.sources]
chto-za-vino-core = { path = "../im-core", editable = true }
```

## Verification

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest -q
```

## Docker

A bot image needs this folder in its build context. Build from the repository root:

```bash
git archive "$REV" im-core max-bot | docker build -f max-bot/Dockerfile -
```
