# Change log

## 2026-09-28

- Added the producer to the Telegram result caption.
- Preserved the JPEG, PNG, or WebP media type of the exact matcher input artifact.
- Updated the smoke tests for matcher-owned pipeline selection and advisory quality checks.
- Added `config.yaml` with the moderation, SAM3, and matcher endpoints. Each endpoint
  accepts a literal HTTP(S) URL or an exact `"{env:NAME}"` reference.
- Switched recognition to `POST /v1/match?k=4` of `svoe-vino-lab/matcher` (plan 06,
  decision 017). The bot sends no pipeline name. The matcher selects the pipeline.
- Took the wine card of each candidate from the matcher answer. Removed the local
  catalogue loader, `CATALOG_FILE`, `WINE_CODE_MAP_FILE`, and `MATCHER_PIPELINE`.
- Renamed `catalog.py` to `wine.py`. The QR URL normalization and the sugar rules moved
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
  units are stopped and disabled. The document is `deploy/gx10/telegram-bot-prod.md` in
  the workspace root.
- Recorded decision 016: keep the bot on gx10 and do not move it to `avalon`.
- Moved the project working tree to `svoe-vino-lab/telegram-bot`.
- Removed the nested Git repository boundary from the imported working tree.
- Kept the project package name, deployment paths, service names, and runtime behavior.

## 2026-09-27

- Added optional QR URLs to matched wine and candidate HTTP API objects.
- Loaded QR URLs by `wine_slug` from the shared matcher wine code map.
- Rejected non-HTTP QR URL values and omitted empty QR URL fields.
- Added a synchronous LAN HTTP recognition API on port `8180`.
- Sent HTTP and Telegram images through one shared FIFO queue.
- Returned moderation, quality, wine parameters, candidates, profile, and timings as JSON.
- Kept unmoderated HTTP uploads in bounded memory without temporary files.
- Added API request source tracking and safe restart handling.
- Deployed the API on GX10 and verified a complete HTTP 200 recognition response.
- Verified that matcher timeouts return structured HTTP 502 responses with step timings.
- Selected `rerank-siglip2-512-crop` explicitly for every matcher request.
- Added `MATCHER_PIPELINE` with the production profile as its default.
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
- Added the `chto-za-vino-admin.service` user service template on port `8172`.
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
- Added administrator aggregate statistics for Telegram user ID `207286210`.
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
- Added wine recognition through `svoe-vino-matcher`.
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
