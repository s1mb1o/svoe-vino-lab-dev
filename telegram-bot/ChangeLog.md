# Change log

## 2026-10-19

- Service rule 10: the catalogue result images come from `https://chtozavino.ru` (plan
  `../docs/plans/06_wine-images.md`, owner decision of 2026-10-19), and from
  `https://api.vino-svoe.ru` until each matcher gives the new addresses. The code is in
  `../im-core` (`CATALOG_IMAGE_HOSTS`).

- «Винный дневник» link (issue #51): `/start link_<code>` shows the diary name with «Привязать» and
  «Отмена»; «Привязать» links the Telegram user ID in the account service; `/unlink` removes it.
  Private chats only. Account calls run as background tasks with a 2 s timeout, so a slow service
  does not hold the update dispatcher. New settings `BOT_ACCOUNT_ENDPOINT` and `BOT_ACCOUNT_TOKEN`
  (empty endpoint: off). The log redaction also covers the account token. `PRIVACY.ru.md` names
  the link. Module `account.py`, 18 new tests.
- Review fixes: only the refusals `invalid_link_code`, `identity_in_use`, `provider_already_linked`
  (own text), and `provider_disabled` reach the person; any other answer counts as an outage and is
  logged. At most 8 account calls run at the same time. 4 more tests (22 in total).

## 2026-10-18

- Added «Удалить запрос» to the request page of the administration interface (MAX issue #10, section
  2.4). After CSRF and an explicit confirmation, it deletes the request row with its candidate,
  timing, and artifact rows, the source image of each attempt, and the artifact files. It refuses an
  active request. Codex review found three races with work that continues after the final status. A
  worker that still sends the result, and an artifact reconstruction, remove the artifact files they
  wrote for a deleted request. An HTTP API call whose request was deleted before the response gets
  HTTP 410 with the status `deleted` instead of HTTP 500. New: `Repository.delete_request_data()`,
  `data_lifecycle.delete_request_data()`. FR 144.1–144.4, service rule 31.1, `SMOKE_TESTS.md`. 6 new
  tests.
- `BOT_DATA_ROOT=./data` of `.env.example` now stores the pipeline artifacts: the shared
  `ArtifactStore` accepts a relative data root. `.env.example` uses the gx10 LAN address for
  `MODERATION_ENDPOINT`, as for `SAM3_ENDPOINT`. `127.0.0.1` worked only on gx10.
- Removed `.dockerignore`. Docker reads it only at the root of the build context, and the
  context is now the repository root. `Dockerfile.dockerignore` applies only to the Compose
  host-demo build. A `git archive` build from standard input uses no ignore file. See
  `../max-bot/ResearchLog.md` (2026-10-18).

## 2026-10-17

- Moved the 12 modules that the MAX bot copied, and their 11 tests, to the shared package
  `chto_za_vino_core` in `../im-core`, an editable `uv` path dependency. `ArtifactRecord`,
  `ArtifactWrite`, `ImageStore`, `ArtifactStore`, and `LEGAL_NOTICE` moved there too. The artifact
  key `telegram_result` and the matcher upload name `telegram-photo` are now parameters of the
  core. The Docker build context is the repository root:
  `git archive "$REV" im-core telegram-bot | docker build -f telegram-bot/Dockerfile -`.
  `chto-za-vino-probe` stays a bot command (`probe.py`) and sends the upload name
  `telegram-photo`. `compose.host-demo.yaml` builds from the repository root;
  `Dockerfile.dockerignore` keeps only `im-core/` and `telegram-bot/` in the context.
  Plan: `../docs/plans/01_im-core-package.md`.
- Accept HEIC and HEIF documents (`image/heic`, `image/heif`). The worker converts them to JPEG
  with `pillow-heif` 1.8.0 before moderation: the HEIF rotation is applied and EXIF data (with the
  location) is removed. A raw HEIC image still fails the type check, so every path converts it
  first. A converted image is scaled to at most 4096 pixels and MUST fit `BOT_MAX_IMAGE_BYTES`.
  The probe command converts HEIC first. Shared `image_types.py`, `moderation.py`, and
  `probe.py`. Specification FR 2.1, 221.2–221.4; rules 26.5, 56.1. 379 tests pass.
- Accept an image that the user sends as a file: a document with the MIME type
  `image/jpeg`, `image/png`, or `image/webp` goes through the photo pipeline, the age gate,
  and the rate limit. Another document still gets «Пришлите фотографию бутылки или
  этикетки». Specification FR 2.1–2.2, rule 26.5.
- Reject an image with more than one frame (animated PNG or WebP) with «Файл не похож на
  поддерживаемую фотографию.» (Codex review finding). A document keeps its original bytes,
  and moderation checks only the first frame. Specification FR 221.1. 19 new tests (283 in total).
- Cherry-picked the `telegram-bot` part of `svoe-vino-lab` commit `4ce43a8f0`: tentative wine
  cards for a low-confidence match (see 2026-10-05). The `result_card.py` part was already here.
- Fixed three Codex review findings of the held-photo fix: the minor choice and the adult
  replay no longer depend on a successful callback answer; a held row is removed only after
  its photo was admitted or explicitly rejected, so a restart during the replay loses no
  photo; scheduled retention removes held rows after 24 hours, not after the 30-day request
  retention. 4 new tests.
- Fixed two second-round Codex findings: an API failure in one chat (receipt or notice) no
  longer stops the replay of the other held photos; the Telegram held photos keep the arrival order
  when two photos have the same second (insertion order breaks the tie).
- Fixed: a photo sent before the age confirmation was lost. After «Мне есть 18 лет» the
  bot answered only with the start text. Now the age gate keeps the Telegram file reference
  of the photo (table `age_pending_photos`: `file_id`, `file_unique_id`, chat, message, and
  media group IDs; no image data). The adult choice queues the held photos through
  `HeldPhotoMessage`; an album still gets one receipt. The minor choice, the user data
  deletion, retention, and a 24-hour limit remove the held photos. A failed receipt gets
  «Не удалось получить фотографию, отправленную до подтверждения возраста. Отправьте её
  ещё раз.». Specification FR 225–227, README, smoke test, 5 new tests. The MAX bot has the
  same fix.

## 2026-10-16

Fixed the defects of issue #11. The tests of the MAX port found them.

- `/users` with a page offset beyond the SQLite integer range now answers
  `Страница не найдена`. `/reset_limit` with a user ID beyond the SQLite integer range now
  answers `Пользователь не найден`. Before, the handler failed and the administrator got no
  answer.
- An album photo without the queue receipt now gets the result text as a reply to the source
  photo when the result photo fails or no result image is available. Before, the user got no
  result.
- An administration retry now writes the source copy and the artifacts under the date directory
  of the first receipt. Before, a retry on another UTC day wrote them under the retry date, and
  retention and user deletion did not find them. The queue wait still starts at the retry.
  Files that earlier retries wrote under a retry date are not moved.
- A repeated feedback press now follows the stored feedback value. A stale `❌ Не совпало`
  button after a positive answer removes the keyboard and does not show alternatives that
  cannot be saved.
- Removed the double point at the end of the queue receipt («около 40 сек..»).
- Tests: 253 pass. `ruff check .` passes.

## 2026-10-06: Photo persistence worker

- Run photo writes, artifact writes, unsafe-copy cleanup, and photo-processing database writes in worker threads.
- Serialize these operations through one persistence lock per photo processor.
- Wait for an active persistence operation before cancellation returns.
- Keep moderation order, file synchronization, atomic replacement, and artifact metadata order.
- Record step timings through the same persistence worker.
- Validation: all 326 bot tests pass. `ruff check .` passes. No deployment.
- Evidence: `../internal/queue-persistence-2026-10-06/README.md`.

## 2026-10-06: Measured CPU bottlenecks

- Compute blur with signed Pillow image arithmetic and an exact value histogram.
- Compute glare with Pillow channel operations. Preserve all quality values.
- Reuse horizontal DCT sums. Compute both image hashes after one decode.
- Run image preparation, hashes, quality processing, artifacts, and result images in worker threads.
- Keep moderation, storage, recognition, and delivery in the same order.
- Encode administration PNGs at compression level 6. Preserve every image pixel.
- Validation: 314 tests pass. `ruff check .` passes. No deployment.
- Evidence: `../internal/other-bottlenecks-2026-10-06/README.md`.

## 2026-10-05

- Show the Top-1 wine card when a score or margin check fails.
- Use the owner-selected tentative wording for each failed confidence condition.
- Give low-score wording precedence when both confidence conditions fail.
- Keep the `abstained` status and the false HTTP confidence flag for a tentative card.
- Permit feedback and alternative selection for a tentative single-photo card.
- Keep an empty matcher answer as a text abstention.
- Add processor, feedback, and caption length checks.
- Validation: 252 tests pass. `ruff check .` passes. The deterministic host demo passes.
- Deploy production patch `874fbd6` from deployed base `49fb414` at 10:16 MSK.
  Validate the exact production patch with 244 tests and an isolated image demo.
  Verify bot readiness, administration readiness, and HTTP authentication.
- Verify the live tentative wine card for query 043 with margin `0.0`.
  Verify that the deployed source matches the production commit and the matcher stays unchanged.

## 2026-09-29

- Added a confidence line to each result and each `Не уверен` answer in the private chat of
  the administrator. The line shows the Top-1 score, the margin, and both thresholds.
- Redacted the Telegram bot token and the HTTP API token from every bot log line, including
  the traceback text (Safety rule 8). An aiogram download error contains the file URL, and that
  URL contains the bot token.
- Deleted the earlier `accepted/` copies and full-fidelity artifact directories of a request
  when an administration retry moderates the image as unsafe (Safety rule 5). The deletion
  checks every date directory, because an earlier attempt can use another date directory.
- Added the project review `docs/reviews/2026-09-29-project-review.md`.
- Required at least 32 characters in the administration password.
- Added a configurable per-client limit for failed administration authentication attempts.
- Rejected administration page numbers that exceed the SQLite integer range.
- Added a repository guard for every paginated administration query.
- Represented a disabled moderation check as `safe=null`, `performed=false`, and
  `bypassed=true` instead of a successful safety verdict.
- Restricted the moderation bypass to local development and tests.
- Made production refuse to start when moderation is disabled.
- Required an explicit Telegram administrator ID and removed the real account default.
- Required a separate HTTP API bearer token with at least 32 characters.
- Added API client rate and global in-flight limits before upload parsing.
- Restricted the administration listener to loopback or an asserted TLS proxy route.
- Restricted matcher result links to the `vino-svoe.ru` catalogue hosts.
- Added dependency readiness checks while retaining a separate liveness route.
- Added 30-day deletion for terminal requests, source images, complete artifact directories,
  and inactive user profiles.
- Added an operator command for an early user-requested data deletion.
- Preserved JPEG, PNG, and WebP types in source storage and matcher requests.
- Added a deterministic host demo, a restricted host-demo Compose file, and one verification
  script for local or CI use.
- Pinned the Docker base images by version and digest and added `.dockerignore`.
- Documented that the project does not grant reuse or distribution rights.
- Removed the deprecated systemd service assets. Production uses Docker Compose only.
- Tests: 227 pass. `ruff check .` passes. The self-contained host demo passes.

## 2026-09-28

- Updated production smoke endpoints to ports `28002` and `28003`.
- Removed legacy matcher, pipeline, endpoint, and port identifiers from active bot material.
- Marked the pre-Docker port documents as superseded deployment records.
- Updated the Russian help text for one photo or a Telegram album.
- Added `moderation.enabled` to `config.yaml`. A false value bypasses ShieldGemma,
  does not require `MODERATION_ENDPOINT`, and records the category `disabled`.
- Added the producer to the Telegram result caption.
- Preserved the JPEG, PNG, or WebP media type of the exact matcher input artifact.
- Updated the smoke tests for matcher-owned pipeline selection and advisory quality checks.
- Added `config.yaml` with the moderation, SAM3, and matcher endpoints. Each endpoint
  accepts a literal HTTP(S) URL or an exact `"{env:NAME}"` reference.
- Switched recognition to `POST /v1/match?k=4` of `svoe-vino-lab/matcher` (plan 06,
  decision 017). The bot sends no pipeline name. The matcher selects the pipeline.
- Took the wine card of each candidate from the matcher answer. Removed the local
  catalogue loader and the bot-owned catalogue, code-map, and pipeline settings.
- Replaced the local catalogue module with `wine.py`. The QR URL normalization and sugar rules moved
  to the matcher.
- Accepted 0 to 4 candidates. An empty answer gives `Не уверен` with status `abstained`.
  An answer that breaks the contract fails closed with status `recognition_failed`.
- Stored each candidate card in `request_candidates.wine_json` and the pipeline name in
  `requests.matcher_pipeline`. An old database gets both columns at start.
- Read the negative feedback alternatives and the HTTP API cards from the stored cards.
  The feedback action shows the available alternatives when fewer than three exist.
- Required `MATCHER_ENDPOINT` to name the path `/v1/match`. The default is
  `http://192.168.86.14:28000/v1/match`.
- Added `Dockerfile`. One image runs the bot and the administration interface.
- Kept the thresholds 0.70 and 0.015 after a calibration on the lab runs.
- Tests: 169 pass (129 before the change). `ruff check .` passes.
- Deployed commit `c0d483e` in Docker on gx10: HTTP API on port 28002, administration on
  port 28003, data in `/srv/svoe-vino-lab/prod/telegram-bot/data`. The old systemd user
  units are stopped and disabled. The document is
  `<workspace>/deploy/gx10/telegram-bot-prod.md`.
- Recorded decision 016: keep the bot on gx10 and do not move it to `avalon`.
- Moved the project working tree to `svoe-vino-lab/telegram-bot`.
- Removed the nested Git repository boundary from the imported working tree.
- Kept the project package name, deployment paths, service names, and runtime behavior.

## 2026-09-27

- Added optional QR URLs to matched wine and candidate HTTP API objects.
- Loaded QR URLs by `wine_slug` from the shared matcher wine code map.
- Rejected non-HTTP QR URL values and omitted empty QR URL fields.
- Added a synchronous LAN HTTP recognition API on a dedicated port.
- Sent HTTP and Telegram images through one shared FIFO queue.
- Returned moderation, quality, wine parameters, candidates, profile, and timings as JSON.
- Kept unmoderated HTTP uploads in bounded memory without temporary files.
- Added API request source tracking and safe restart handling.
- Deployed the API on GX10 and verified a complete HTTP 200 recognition response.
- Verified that matcher timeouts return structured HTTP 502 responses with step timings.
- Selected a matcher pipeline explicitly for every matcher request.
- Added a bot-owned pipeline setting with the production profile as its default.
- Deployed the profile selection to GX10.

## 2026-09-26

- Added irreversible server-side blurred previews for quarantined administration requests.
- Added strict `safe` and `censored` artifact exposure classes.
- Added censored preview reconstruction for existing quarantined requests.
- Kept quarantine source files outside the administration HTTP surface.
- Added an ordered visual pipeline inspector to each safe administration request.
- Added persisted matcher input, moderation input, SAM3 masks, overlay, crops, cutouts, and result artifacts.
- Enabled full-size SAM3 masks with strict base64, format, size, and dimension validation.
- Added safe artifact routes with authentication, LAN restrictions, path confinement, and current moderation checks.
- Added advisory artifact generation timings without blocking recognition.
- Added `chto-za-vino-artifacts` for safe reconstruction without Telegram output.
- Prevented unspaced moderation metadata from widening the mobile request page.
- Fixed narrow administration request cards that rendered values one character per line.
- Separated compact statistic tiles from the responsive two-column request detail layout.
- Added a separate password-protected FastAPI administration interface.
- Added LAN CIDR access control and CSRF protection for administration actions.
- Added administration pages for statistics, users, requests, timings, and filter errors.
- Added administration rate-limit reset and safe retry actions.
- Added persistent `retry_requested` coordination with the bot FIFO queue.
- Required moderation to run again for every administration retry.
- Prevented the administration interface from serving accepted source files, quarantine images, or storage paths.
- Added the `chto-za-vino-admin.service` user service template on a dedicated port.
- Added an atomic deployment helper for the protected administration environment values.
- Changed image quality checks from blocking gates to advisory metadata.
- Continued recognition when SAM3 fails or reports a quality issue.
- Accepted small SAM3 box coordinates outside the image boundary by clamping them.
- Shortened the informational notice in bot messages.
- Added persistent queue wait and per-step processing timings.
- Added safe per-step timing records to the service journal.
- Made negative feedback restore alternatives after a repeated callback.
- Added a new-message fallback when Telegram cannot edit the alternative keyboard.
- Required exactly four matcher candidates for a confident result.
- Added three ranked alternatives and `Ничего из этого` after negative feedback.
- Added confidence abstention from the Top-1 score and score margin.
- Added local blur and glare checks before recognition.
- Added SAM3 bottle and label checks before recognition.
- Added perceptual hash and difference hash storage.
- Added persistent moderation filter error reports.
- Added one editable queue receipt with position and approximate wait.
- Added an inline wine page button to every successful result.
- Added the supplied rejection illustration for inappropriate content.
- Added a text fallback for rejection illustration delivery failures.
- Replaced prompt-based image moderation with `shieldgemma-2-4b-it`.
- Added strict validation for `dangerous`, `sexual`, and `violence` scores.
- Added fail-closed validation for the ShieldGemma `flagged` list and threshold.
- Added one-time match feedback buttons to successful single-photo results.
- Added persistent request-linked feedback storage.
- Restricted feedback submission to the source Telegram user.
- Restricted public `/stats` responses to the current user's data.
- Added administrator aggregate statistics for the configured Telegram administrator.
- Added administrator-only `/users` and `/reset_limit` commands.
- Added persistent rate-limit resets that preserve request history.
- Increased the default and production user rate limit to 50 images per hour.
- Reduced Telegram album queue acknowledgements to one message per album.
- Added foreground-aware 4:5 catalogue image preparation for Telegram previews.
- Added a persistent soft 18+ confirmation before photo processing.
- Added the alcohol notice to the confirmation screen and recognition result.
- Added separate ordered processing and replies for each photo in a Telegram album.
- Added a photo result card with the official catalogue image.
- Added color, sugar class, and grape varieties to the result caption.
- Added a safe submitted-photo fallback for an unavailable catalogue image.
- Added strict catalogue image host, size, format, and dimension validation.
- Added a bounded FIFO photo processing queue.
- Added configurable queue workers and queue capacity.
- Added recovery for received, queued, and interrupted requests.
- Added live queue counts to `/stats`.
- Excluded queue-capacity rejections from the user rate limit.
- Created the `@ChtoZaVinoBot` project.
- Added Telegram long polling.
- Added the rolling user rate limit.
- Added fail-closed image moderation through `llama-swap`.
- Added separate accepted and quarantine storage.
- Added SQLite request and identity records.
- Added wine recognition through the legacy matcher service.
- Added `/start`, `/help`, `/stats`, and `/privacy`.
- Added bot profile text synchronization.
- Added a live moderation and matcher probe.
- Added the Russian privacy policy.
- Added the public Telegram privacy deep link.
- Added the `gx10` systemd unit template.
- Configured the unit as a persistent user service.
- Kept the production Python environment on the `gx10` local SSD.
- Added the bot profile image source.
- Added the 640 by 360 bot description picture.
- Added a 640 by 360 scanner-style bot description picture.
- Added four 640 by 640 bot avatar variants and a comparison sheet.
