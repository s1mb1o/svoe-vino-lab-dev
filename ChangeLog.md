# Change log

## 2026-10-20 — Correct the comprehensive review findings

- Accept real underscore wine identifiers in Web UI metadata lookup. Preserve path validation.
- Add an explicit local matcher configuration. Correct the setup and evaluator instructions.
- Restore the canonical `SAM3_ENDPOINT` override for all matcher SAM3 clients.
- Declare the lightweight Workbench server dependencies, including jsonschema.
- Record R4 as not applicable on `main`. Commit `906bd778` adds the Android evidence, and all local links in `ASSESSMENT.md` resolve.
- Document the existing Dinner Lens Web UI integration and its required settings.
- Isolate matcher fixtures and CI from an inherited production SAM3 endpoint.
- Pass 625 Web UI tests with 26 existing skips, type checking, the production build, and the bundle check.
- Pass 285 matcher tests with one optional integration skip. Pass 16 focused Workbench tests in a fresh lightweight environment.
- Verify all local links in the corrected entry documents and in `ASSESSMENT.md`.
- Mark R1, R2, R3, and R5 resolved and R4 not applicable in `docs/reviews/2026-10-20-comprehensive-review.md`.

## 2026-10-20 — SEO audit of chtozavino.ru

- Add the SEO audit in `docs/seo-audit/`: technical, performance, content and deployment findings, a prioritised backlog, evidence files, and draft GitHub issues (`github-issues/`, not created yet).
- The audit is read-only. It records production observations of 2026-10-20 and the source baseline `cd8b063e`.

## 2026-10-20 — Vector product logo

- Replace `assets/product-logo-640x640.svg` with a 2,810-byte vector redraw of the PNG. The previous SVG embedded the PNG and was 171,311 bytes.
- Keep `assets/product-logo-640x640.png` unchanged for raster consumers: Android, iOS, the MAX bot card, and the PWA icons.
- Use the same file for `webui/public/icons/product-logo.svg` (SEO-002).
- Replace the other six SVG files that embedded a PNG with vector redraws. Each PNG stays unchanged and remains the runtime file.
  - `telegram-bot/assets/botpic-v3-scanner.svg`: the product logo SVG (171,305 → 2,810 bytes).
  - `telegram-bot/assets/description-picture-v2-scanner.svg`: the vector logo plus traced text (76,563 → 17,996 bytes).
  - `telegram-bot/assets/description-picture-selected-640x360.svg` and `description-variants/description-light-640x360.svg` (353,795 → 22,645 bytes).
  - `telegram-bot/assets/content-rejected-monkey-640x640.svg` and its `max-bot/assets/` copy (662,389 → 39,136 bytes).
- The redraws use flat colours, fitted circles for dots, and fitted strokes for thin lines. Paper grain and soft gradients are not kept.
- Chrome renders each SVG within a mean difference of 0.9–2.8 of 255 per channel from its PNG. No tracked SVG embeds a bitmap now.

## 2026-10-20 — Comprehensive repository review

- Review the README, setup, assessment evidence, main service paths, tests, and packaging.
- Record five findings in `docs/reviews/2026-10-20-comprehensive-review.md`.
- Verify the metadata identifier defect and the obsolete matcher environment settings without external service calls.
- Run the available Web UI, matcher, account, MCP, bot, bootstrap, and focused workbench checks.
- Preserve application source and record the remaining verification limits.

## 2026-10-20 — Android 0.3.0 GitHub release

- Publish GitHub prerelease `android-v0.3.0` with the verified 753111053-byte test-signed APK.
- Attach release notes, benchmark results, the portable research archive, and SHA-256 checksums.
- Verify the source tag, every uploaded asset digest, and the checker from the extracted evidence ZIP.
- Record the private-repository access limit. Keep the website as the public download option.
- Update Android release records and assessment F-85. Change no runtime, model, benchmark, or website deployment.

## 2026-10-20 — Android 0.3.0 release assessment verification

- Extend `ASSESSMENT.md` with the recorded release host tests, website tests, signed-APK acceptance, replay parity, and sampled resource limits.
- Record 46.56/84.58/89.67% Top-1/5/10 on 668 hard assignments and request median/P95 1372/1832 ms.
- Keep the separate Eval.zip result at 86/100 accepted, with 14 mismatches and comparison status `FAIL`.
- Record publication source `40a54074` and time `2026-10-20T19:22:28Z`. Keep the test-key and missing full-`my` custom-default limits explicit.
- Pass the portable Android checker: 32 file hashes, 23 result series, 15,364 hard-cohort observations, and 100 Eval.zip observations. Pass all eight verifier tests.
- Hash the archived signed APK. Match all 753111053 bytes and the full SHA-256 against the committed contract and saved publication receipt.
- Preserve the existing research assessment and historical results. Run no new device inference, build, browser acceptance, or live download.

## 2026-10-20 — Android research preservation and assessment

- Consolidate the complete Pixel research in `ANDROID-RESEARCH-AND-RESULTS-20261020.md`.
- Record the model port, failed split runtimes, four pooling variants, query-frame controls,
  DIS resolution specialization, ten SO400M mobile recipes, and production parity checks.
- Preserve 23 result series with 15,364 hard-case observations and 100 Eval.zip observations.
  Exclude photos, masks, weights, reference answers, APKs, credentials, and private owner messages.
- Add source-file hashes, a portable standard-library verifier, and eight focused verifier tests.
- Update `ASSESSMENT.md` for format 7, the selectable complete pipelines, release 0.3.0,
  completed research, and explicit quality, heat, timing, continuation, and signing limits.
- Correct the merged-manifest permission claim. Offline model inference does not require
  absence of the `INTERNET` permission that dependencies add.
- Keep the historical full-`my`, development-selected hard cohort, and Eval.zip results separate.
  This task starts no device, benchmark, inference, service, or deployment.

## 2026-10-20 — Refresh benchmark summaries

- Review the metric references in the current overview documents and the dated evidence.
- Update `README.md`, `BENCHMARKS.md`, the workbench README, the submission-template context, and the Android implementation comparison.
- Surface research recipe R011 at 90.77% R@1 on 2,970 positive assignments. Retain the earlier 84.67% score with its separate 1,644-positive cohort.
- Add the best hard-cohort research scores and the recorded matcher and Android results with exact cohort and pipeline labels.
- Link the newer Android 0.3.0 evidence at committed `origin/main` revision `6bd4abed`. Keep its 46.56% hard-cohort result separate from the earlier 72.29% full-`my` experiment and the 95/100 server submission.
- Preserve frozen research reports, predictions, release records, and historical test counts.
- Pass the portable research checker. Independently recalculate all 668 saved Android 0.3.0 replay assignments: 311/565/599 Top-1/5/10 hits and a 1,372.026 ms median. Run no new inference or device benchmark.

## 2026-10-20 — Configurable matcher rejection threshold (#79)

- Add the default 0.7 single-image score floor in matcher YAML.
- Handle rejected predictions on the website as a normal no-match result with no diary entry.
- Document the measured 100-photo / 36-control comparison and the limits of score filtering.

## 2026-10-20 — Account test verification for the assessment

- Install the account runtime and development dependencies from `account/uv.lock` in a separate temporary environment.
- Run `account/scripts/verify.sh` against account source at `121c7f08` with Python 3.13.7.
- Pass the lockfile check and Ruff check. Pass all 159 account tests in 9.70 seconds with no failures, errors, or skips.
- Update `ASSESSMENT.md` with the result, dependency versions, repeat command, and test limits. Replace the missing-`pytest` limitation.
- Preserve the earlier component results. Leave the account source and lockfile unchanged.

## 2026-10-20 — Source assessment refresh

- Review `ASSESSMENT.md` against committed source `7cb1044c` and the existing local MCP and alternatives changes.
- Add evidence for alternatives, factual comparison, diary history, saved wines, private notes, device copies, the label guide, bot landings, and production-error review.
- Correct the database export, Active catalogue count, OpenAPI inventory, sitemap count, evaluator time budget, and stale missing-feature claims.
- Mark uncommitted source and untracked evidence. Keep historical acceptance, local tests, and deployment records separate.
- Verify 616 Web UI tests (26 skipped), 51 MCP tests, 8 database-export tests, and 16 production-error tests. Verify the alternatives source check, schema-36 restore, all 5 matcher payload hashes, and the portable retrieval checker.
- Record that account tests could not start without `pytest`. Do not claim a new full-suite, model, mobile, browser, or live-service check.

## 2026-10-20 — Shelf Lens dataset link

- Add the Google Drive link to the Shelf Lens dataset (`shelf-bottles-dataset.zip`) in `shelf-lens/README.md`.

## 2026-10-20 — Shelf Lens assessment coverage

- Update `ASSESSMENT.md` against `main` at `06f3b78c`.
- Add F-113 to F-116 for video scanning, spatial ReID, AR ratings, planograms, and the integrated landing.
- Link each claim to the committed code, prototype tests, recording, images, or validation record.
- Separate the Android video workflow from the Web photograph scanner and the offline Android application.
- Record internet, tracker, APK credential, and benchmark limits. Keep bottle search, AR navigation, taste highlighting, and compliance checks in planned work.
- Add the Shelf Lens test command and component entry. Update the public sitemap count to 16 pages.

## 2026-10-20 — F04 Web result journey, issue #73

- Implement strict cross-producer alternatives, factual comparison, existing diary saves, login return, and bounded public offline cards in `webui/`.
- Base the separate `codex/issue-73-f04` branch on current main `a30827d6`. Keep the protected validation checkout unchanged.
- Add source checks, twenty-anchor coverage, failure checks, Chromium/WebKit acceptance, and a physical Pixel 8 journey with the running matcher. Read `webui/docs/f04-acceptance-2026-10-20.md` for limits and remaining human acceptance. No backend migration, main merge, or deployment is included.

The change log of the repository. A project folder can have its own `ChangeLog.md`, for example
`telegram-bot/`, `max-bot/`, and `im-core/`.

## 2026-10-20

- Added `shelf-lens/`, the Android app «Полка вина». It comes from the separate repository
  `shelf-reid` with its 16 commits. The app films a shelf, finds bottles on the phone, and sends
  one crop of each bottle to `/v1/match`. It shows frames and the vino-svoe.ru rating over the
  camera image and builds a planogram. The paths inside the folder do not change. Read
  `shelf-lens/README.md`.
- The application ID and the Java package of «Полка вина» are now `com.alolalab.shelflens`
  (was `ru.svoevino.shelfreid`), with the same prefix as `com.alolalab.chtozavino`. Android
  installs it as a new application. Push demo videos again to the folder of the new ID.
- The «Полка вина» APK build MUST have the environment variable `CHTOZAVINO_API_PASSWORD`, the
  password of the API user `evaluator`. Without it, the APK build stops with an error. The build
  puts the password into the APK assets. The file `shelf-lens/api_password.txt` is no longer
  used. `clean`, the Android Studio project sync, and the Python scripts work without the
  variable. Read `shelf-lens/README.md`, «Сборка и запуск».

- Updated `ASSESSMENT.md` to `main` at `db288cc9`. Added Dinner Lens and wine for a dish
  (F-27 to F-29), the workbench research rows (F-14 to F-19), experiment tracking and run
  comparison (F-49), the RTX 4090 cascade run (F-66), the Android 0.2.0 work (F-87 to F-93),
  the iPhone app (F-94 to F-98), «Винный дневник» accounts (F-99 to F-103), the legal pages,
  the site map, the Crocodile and game landings, static wine images (F-104 to F-108), and the
  workbench catalogue tools (F-109 to F-111). Rewrote the Android rows F-80 to F-85 for the
  p512 default and release 0.2.0. Corrected F-10 (runs moved to `workbench/runs-1/`), F-21
  (result labels), and F-46 (operation inventory). Recorded the failing matcher CI run (F-33),
  the open workbench port gaps, the test suites that need files outside Git, and the
  `issue-34-review-assets-v2` branch. Removed the `android/current` row: `main` has its content.

## 2026-10-19

- Added the shared legal pages `/terms`, `/privacy`, and `/contacts` to `webui/` (#37). They cover
  the website, both bots, and both mobile apps. The bot texts will link to them (#10). Do not
  deploy them before the matcher archive has a 30-day cleanup job. Read `webui/docs/legal-pages.md`.
  The pages also cover «Винный дневник» and the wine-for-dish mode. Do not deploy them before the
  Dinner Lens cloud fallback is off.

- Static wine images, release format 2 (plan 06 D10–D11): each file comes from the SAM3 or
  alpha package cut of the lab, with transparent, white, and black borders trimmed and no
  margin. 2,189 of 2,193 images now have a transparent background. Read `workbench/ChangeLog.md`.

- Dinner Lens 0.7.0 accepts direct HEIC/HEIF and WebP uploads as raw base64 or
  inline data URLs. It selects the HEIF primary image, preserves orientation and
  transparency, strips metadata, and keeps the existing byte and pixel limits.
  All 125 package tests pass, including API requests and malformed image rejection.

- Deployed the 25-map Web UI release `772a396e`. Verified all 25 live map routes and the exact bytes of 157 added bottle assets. Passed 15 staging and 15 live browser cases in each engine, 193 HTTP/asset checks in each phase, and seven edge/presentation checks. Updated only the deployment status of F-24 in `ASSESSMENT.md`.

- Merge six additional producer maps and refresh the current coverage reports: 25 maps, 1,203 products, and 1,138 of 2,103 saved catalogue cards (54.1132%). Recheck only F-24 and F-48 in `ASSESSMENT.md`. The six-map expansion awaits deployment.

- Implemented plan `docs/plans/06_wine-images.md` on `feature/wine-images` (not deployed).
  `workbench/scripts/build_wine_images.py` builds a release of static wine images
  (`/img/wines/{1600,400}/<slug>.webp` and a SHA-256 manifest), and
  `check_wine_images.py` checks a release or the published files against a catalogue database.
  The matcher and the bundle builder give `image_url` = the 1600 px address, or `null` for a
  wine with no image. im-core accepts both `chtozavino.ru` and `api.vino-svoe.ru` during the
  transition (bot service rule 10 updated). The web UI uses the static image in
  `/api/wines/[slug]`, shows a 400 px image in each Dinner Lens card, and shows a bottle
  silhouette when an image does not load (`WineImage.vue`). A real build: 2,193 images of
  2,198 Active wines, 104 MB, no check difference. Tests: matcher 263, workbench image and
  bundle suites, im-core 160, Telegram bot 251, MAX bot 486, web UI Vitest 482 and the 7
  Dinner Lens browser suites pass. See the component change logs.

- Added plan `docs/plans/06_wine-images.md`: static wine images on chtozavino.ru at
  `/img/wines/{1600,400}/<slug>.webp` (`main_patched`, else `main`) with a SHA-256
  manifest and a blocking check at each image and matcher catalogue deploy. The plan
  records owner decisions D1–D9 and has no open questions: no placeholder files on the
  server, a web UI placeholder on image errors, and `image_url` = `null` in the matcher
  card of a wine with no image (the current behavior). Issue #69 tracks the
  5 Active wines with no image and the wrong image of
  `vibes-vermentino-viognier-barrel-fermented-2022`. No code changes.


- Dinner Lens now explains the alcohol choice for spicy food with the actual wine
  strength. Russian copy formats whole percentages without decimals and fractional
  percentages with a comma. All 114 package tests pass, including continuation pages,
  11% and 12% source facts, decimal formatting, and non-spicy dishes.

- Added the public index `/lineup` of the producer maps and moved `/lineup/<producer>` to a page layout
  without an inner scroll box. Read `webui/docs/plans/05_lineup-index-and-page-layout.md`. Updated F-24 in
  `ASSESSMENT.md`: the maps are deployed since release `7d8e80ea`.

- Added local-first Dinner Lens recognition on gx10 Qwen3.5-9B-NVFP4 with Qwen3.8-Flash
  fallback. YAML selects protocols, exact response model aliases, optional credentials
  and per-provider limits. Fallback covers provider failures and invalid output; valid
  uncertain answers retain clarification. Model receipts identify the actual selected
  provider. The English prompt, data, wine filters and embedding ranking are unchanged.

- Dinner Lens v0.5.0 moves public service settings to validated YAML. Secrets remain
  environment variables. Added persistent service cursor secrets, configurable model
  adapters and limits, public artifact readiness, a pinned Docker build and configuration
  regression tests. The food/wine rules, datasets, embedding vectors and English prompt
  remain unchanged.

- Moved matcher public settings to YAML. Added validated `matcher.limits` and
  `matcher.sam3_endpoint`. Shelf matching, hand selection, and readiness share the
  configured segmentation endpoint. Secret tokens stay environment references.
  Removed public environment lookups and the Docker output-directory default.
  Updated HTTP tests and configuration documentation. HTTP factory overrides now
  require numeric YAML-compatible types; numeric strings are rejected.

- Producer maps in `webui/` now load on demand. The first-load JavaScript of `/` dropped from 296 KB to 139 KB gzip.
  The MCP server reads the map list from `webui/shared/data/product-line-index.json`. Read `webui/docs/plans/04_lazy-product-line-maps.md`.
- Merged the producer product-line maps into `webui/` (branch `product-line-map`): 19 producers and 1,046 products.
  Read `webui/ChangeLog.md`.
- Replaced the six-node Abrau demo of the MCP tool `get_producer_line` with these maps (#25).
  Read `mcp/ChangeLog.md` and `docs/plans/03_mcp-producer-line-maps.md`.
- Updated F-24 and F-48 in `ASSESSMENT.md` for these changes. The other entries and the header still describe
  the check at `0621952`.
- Corrected Dinner Lens sauce composition and later-page suitability in v3: preserve
  chilli/glaze when cream is added, retain meat weight for sweet sauces, and enforce
  source-linked reviewed style families before embedding continuation. Added 15
  regression tests and a blind 42-context audit plus 12 held-out contexts.

- Expanded Dinner Lens v2 to 200 dishes, 104 intermediate classes and 16 broad
  fallback classes, with 1,270 editorial catalog links. Preserved the original
  dataset and image benchmark, reused identical verified embedding inputs, and
  added 348 text contracts for hierarchy, eligibility and continuation.
- Added the standalone `dinner-lens/` food-to-wine API for #28: code-enforced
  eligibility, editorial choices before real embedding discovery, authenticated
  photo recognition with English prompts, and signed continuation cursors. The
  service includes the frozen 75-dish hierarchy, behavioral tests and a ground-truth
  HTTP benchmark runner. See `dinner-lens/README.md` for setup and catalog limits.
- Updated `ASSESSMENT.md` to `main` at `0621952`. Added F-13 shelf pipeline with label
  evidence (port of the production matcher), F-48 read-only catalogue MCP server (#25), and
  F-86 HEIF (HEIC) photos (#24). Highlight 10 now covers WebMCP (F-77) and the MCP server
  (F-48). Added `mcp/` to the test commands and the component layout. Removed the
  `feature/mcp` row: the branch is merged into `main` and deleted.

## 2026-10-18

- Added `ASSESSMENT.md`: an index of the features on `main` for the hackathon organizers and the
  jury. It is not development documentation. Each feature has its status, entry point, proofs,
  and a verify step. `README.md` links to it (#42).
- Ported the Yandex.Metrika counter `113460637` of the production web UI to `webui/` (#40).
  The source is the lab repository `svoe-vino-lab`, branch `codex/metrika-release`, commits
  `10632011` and `af36345e`. Read `webui/ChangeLog.md`.

## 2026-10-02

- Added the evaluation results: `predictions.jsonl` with 100 predictions (`aca12e6d`) and their
  summary in `README.md` (`d935c652`, `20a9903e`).

## 2026-09-29

- Froze the repository for the hackathon submission (`e8787cf4`).
