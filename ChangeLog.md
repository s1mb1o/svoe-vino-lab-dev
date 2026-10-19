# Change log

The change log of the repository. A project folder can have its own `ChangeLog.md`, for example
`telegram-bot/`, `max-bot/`, and `im-core/`.

## 2026-10-19

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
