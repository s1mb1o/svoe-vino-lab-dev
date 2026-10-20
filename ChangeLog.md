# Change log

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
  camera image and builds a planogram. The paths inside the folder do not change. Put
  `api_password.txt` in `shelf-lens/`. Read `shelf-lens/README.md`.

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
