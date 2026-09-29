# Project review of chto-za-vino-bot

Date: 2026-09-29

## Scope

This review covers the whole project as it was on disk on 2026-09-29.
The working tree contained uncommitted changes to `admin_web.py` and `config.py`.
These changes add the administration authentication limiter (Safety rules 58 and 59).
The review includes these changes.

State at review time:

- `uv run ruff check .` passed.
- `uv run pytest -q` passed with 227 tests.

Column "Check" gives the verification method:

- `repro`: a scratch script reproduced the defect.
- `code`: the complete code path was read and it gives the defect.
- `lib`: the installed library source was read and it gives the defect.

## Fix status

| # | Status |
|---|---|
| H2 | Fixed on 2026-09-29. Regression test: `tests/test_processor_quality.py::test_unsafe_retry_removes_the_earlier_safe_copies`. |
| H3 | Fixed on 2026-09-29. Regression test: `tests/test_log_redaction.py::test_a_download_failure_log_does_not_contain_the_bot_token`. Limit: the uvicorn loggers keep their own handlers and do not use `SecretRedactingFormatter`. |
| All other items | Open. |

## High severity

| # | Defect | Location | Check |
|---|---|---|---|
| H1 | An administration retry writes the source file and the artifacts under the retry date. Retention and user deletion use the original `received_at`. The retry files are never deleted. The old `accepted/` file loses its `storage_path` reference and is never deleted. | `storage.py:1431`, `app.py:1623`, `storage.py:1617-1625` | code |
| H2 | A retry that moderation now rejects writes to `quarantine/`. The earlier copy stays under `accepted/`. The old full-fidelity artifact files also stay on disk. This violates Safety rule 5. | `app.py:346-361`, `storage.py:1371-1421` | code |
| H3 | The bot token can go into the log. aiogram downloads from `https://api.telegram.org/file/bot<TOKEN>/...` with `raise_for_status=True`. `aiohttp.ClientResponseError.__str__` contains the URL. `LOG.exception` writes it. This violates Safety rule 8. | `app.py:304-307` | lib |
| H4 | A defective catalogue image changes a `recognized` request to `internal_failed`. `SyntaxError` (bad PNG CRC), `DecompressionBombError`, and `httpx.InvalidURL` are not caught. The user gets an internal error instead of the result with the submitted photo. This violates Service rule 11. | `result_card.py:139`, `result_card.py:174`, `app.py:634`, `app.py:239-249` | code |
| H5 | Album photo 2 and later photos get no result when `send_photo` fails or when no result image exists. The fallback calls `_set_status`. `_set_status` returns immediately when `status_enabled` is false. The status stays `recognized`. This violates spec 34. | `app.py:642-649`, `app.py:674-682`, `app.py:742-743` | repro |

## Medium severity

| # | Defect | Location | Check |
|---|---|---|---|
| M1 | The bot writes the terminal status before result delivery. A restart during delivery loses the answer. `pending_requests` does not restore `recognized`, `abstained`, or `quarantined`. | `app.py:501-513`, `app.py:376-383`, `storage.py:1020` | code |
| M2 | Moderation checks only frame 0 without alpha. `convert("RGB")` drops the alpha channel. APNG and animated WebP frames after frame 0 are not checked. The exact bytes go to the matcher and to the `matcher_input` artifact. Only the HTTP API is exposed. Telegram photos arrive as JPEG. | `moderation.py:43-51`, `image_types.py:27-36`, `pipeline_artifacts.py:64-79` | code |
| M3 | An exception in a retention pass stops the bot. The startup pass then raises again before polling. A restart policy gives a crash loop. | `app.py:1598-1606`, `app.py:1708`, `app.py:1808-1810` | code |
| M4 | The retry watcher task is not in the `asyncio.wait` set and has no exception handling. One `sqlite3.OperationalError` stops all later administration retries without an alarm. | `app.py:1638-1650`, `app.py:1767`, `app.py:1798` | code |
| M5 | The image sets `BOT_ADMIN_WEB_HOST=127.0.0.1`. The prod compose file publishes `0.0.0.0:28003:8080`. The published port cannot reach a listener on container loopback. `deploy/gx10/telegram-bot-prod.md:21` still says that the HTTP API has no token. | `Dockerfile:44`, `<workspace>/deploy/gx10/telegram-bot-prod.compose.yaml:49`, `<workspace>/deploy/gx10/telegram-bot-prod.md:19-21` | code |
| M6 | After an administration retry, the old feedback buttons stay active. `request_retry` clears the feedback fields. A tap on an old button stores feedback for the new result. An old alternative button maps to the new candidate at that rank. | `storage.py:1395-1411`, `storage.py:721-755`, `storage.py:892-908` | code |
| M7 | A repeated callback does not restore the correct keyboard. The `feedback` handler selects the keyboard from the tapped button and not from the stored value. The `alternative` and `moderation_error` handlers do not change the keyboard on `already_saved`. This violates the "Common mistakes" rules in `CLAUDE.md`. | `app.py:1162-1197`, `app.py:1229-1231`, `app.py:1258-1260` | code |
| M8 | The log format does not contain the `extra` fields. About 24 log calls lose their `request_id`. Examples: "Image moderation failed" and "Telegram result photo failed". | `app.py:1665-1668` | code |

## Low severity

| # | Defect | Location | Check |
|---|---|---|---|
| L1 | A relative `BOT_DATA_ROOT` breaks every artifact save. `ArtifactStore` resolves `_data_root` but not `_root`. `relative_to` raises `ValueError` after the file write. The `.env.example` value `./data` gives this error. The Docker value `/data` does not. | `storage.py:1679-1707` | repro |
| L2 | Withdrawn. A matcher answer with one candidate always abstains because the margin is `0.0`. This is intended behavior. `tests/test_processor_quality.py::test_one_matcher_candidate_abstains_because_the_margin_is_zero` asserts it. | `matcher.py:36-40` | code |
| L3 | Retention deletes files while it holds the repository lock and a `BEGIN IMMEDIATE` transaction. All repository calls on the event loop wait. The administration process can get "database is locked". | `storage.py:1563-1614` | code |
| L4 | PIL work, pure-Python hashes, the Laplacian loop, and `fsync` run on the event loop. Each job stops Telegram polling and the HTTP API for its duration. More queue workers do not add CPU parallelism. | `app.py:318`, `app.py:344-347`, `quality.py:297`, `result_card.py:176` | code |
| L5 | A database error in the `finally` block of `process()` prevents `completion.set_result`. The HTTP API request waits forever and holds one in-flight slot. | `app.py:250-260`, `app.py:1515` | code |
| L6 | Malformed SAM3 JSON can raise `OverflowError` or `DecompressionBombError`. These are not `QualityUnavailable`. The request fails and recognition does not run. This violates Service rule 24. | `quality.py:62`, `quality.py:97`, `quality.py:142`, `app.py:402` | code |
| L7 | `UnicodeDecodeError` and `OverflowError` from the matcher answer, and `SyntaxError` from a corrupt PNG, are not caught. The HTTP API answers 500 instead of 502 or 422. The request still fails closed. | `matcher.py:122`, `image_types.py:32`, `moderation.py:52` | code |
| L8 | `_ratio` and `_positive_float` accept `nan` and `inf`. `BOT_QUEUE_ESTIMATE_SECONDS=nan` makes `enqueue_photo_message` raise after `reserve`. Each photo then uses quota and fails. | `config.py:171-191`, `work_queue.py:75` | code |
| L9 | The configuration does not enforce the moderation path `/upstream/shieldgemma-2-4b-it/classify`. This violates spec 79. | `config.py:91-94` | code |
| L10 | The API token, rate limit, and in-flight limit depend on an exact path string. A `root_path` or a mount under a parent application disables all three. The current prod configuration sets no `root_path`. | `http_api.py:142` | code |
| L11 | The administration form reader reads the complete body before the 8 KiB check. | `admin_web.py:233-235` | code |
| L12 | No code sets `Image.MAX_IMAGE_PIXELS`. A small PNG with about 170 megapixels passes the byte limit and is decoded several times. | `src/` | code |
| L13 | The artifact backfill raises when current moderation rejects a source. It does not record the new unsafe verdict. The full-fidelity artifacts stay available. | `artifact_backfill.py:48-49` | code |
| L14 | A `feedback:no` tap with no stored alternatives keeps the feedback keyboard. This violates spec 76. | `app.py:1169-1174` | code |
| L15 | Uncommitted limiter: behind a TLS proxy, all clients share one failure bucket. Ten bad attempts lock out the administrator. A valid request clears the failure history of all clients. Empty queues are not removed. The allow-list limits the number of keys. | `admin_web.py` (uncommitted diff) | code |

## Test gaps

1. No pipeline test proves that `ModerationUnavailable` stops storage and the matcher call (Safety rules 1 and 2).
2. No test checks that an unsafe image is only under `quarantine/`. No test checks the `0o700` and `0o600` permissions (Safety rules 5 and 6).
3. No test checks log content for tokens or user names (Safety rule 8).
4. All processor tests use `image_url=None`. The catalogue image path and its fallback have no test.
5. No test combines a retry with retention across two dates. `tests/test_admin_retry_queue.py:42` asserts the retry date that causes H1.
6. `tests/test_album.py:143-172` builds album jobs with `status_enabled=True`. Real album jobs 2 and later have `status_enabled=False`. The test cannot find H5.
7. No test repeats an `alternative` or `moderation_error` callback after a failed keyboard edit.

## Items checked without a defect

- The result page host allow-list rejects userinfo, other ports, `http`, look-alike hosts, a trailing dot, and bracketed hosts.
- The catalogue image loader does not follow redirects.
- Matcher requests send `k=4` and no pipeline name. They keep the JPEG, PNG, and WebP type.
- Secret and CSRF comparisons use `compare_digest`.
- The services do not trust `X-Forwarded-For`. IPv4-mapped IPv6 addresses do not bypass the allow-list.
- Administration pages escape all user and database values.
- The artifact route blocks path traversal. It decides exposure from the current moderation state.
- The moderation parser fails closed on unknown policies, NaN, and an inconsistent `flagged` list.
- The HTTP API checks the network, the token, the rate limit, and the in-flight limit before it reads the body.
- A queue capacity rejection does not use the user rate limit.
- `UNIQUE(chat_id, message_id)` ignores a duplicate Telegram update.
