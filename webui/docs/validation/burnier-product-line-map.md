# Burnier map validation

Date: 2026-10-19.
Preview: `http://127.0.0.1:18553/lineup/burnier`.
Source record: `../product-line-maps/burnier/sources.md`.

## Results

| Check | Result |
| --- | --- |
| Full unit suite with the exact catalog snapshot | 304 tests pass in 17 files; no skipped tests |
| Type check | Pass |
| Production build and map prebuild validation | Pass |
| Generated index freshness | Pass; 20 producers |
| Image-frame pixel checker | Pass; 1,068 images across 20 producers; all frames contain the visible alpha outline |
| Production bundle check | Pass; 20 lazy map chunks; no full map data on the scanner pages at first paint |
| Producer browser suite, Chromium | 85 checks pass; no browser errors or hydration warnings |
| Producer browser suite, WebKit | 85 checks pass; no browser errors or hydration warnings |
| Abrau browser regression suite, Chromium and WebKit | Pass in both engines |
| Burnier-specific browser checks, Chromium | 25 checks pass |
| Burnier-specific browser checks, WebKit | 25 checks pass |
| Diff whitespace check | Pass |

The exact snapshot environment variable is:
`PRODUCT_LINE_CATALOG_SNAPSHOT=/Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace/svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl`.

The browser suites use `PORTAL_ORIGIN=http://127.0.0.1:18553`.
The installed matching Chromium and WebKit module is:
`PLAYWRIGHT_MODULE=/Volumes/Storage/svoe-vino-final/code/wine-and-dine-merge/node_modules/playwright/index.mjs`.
The full Chromium producer suite and bundle check also pass with the bundled runtime Playwright module.
The pixel checker uses the bundled Sharp entry at
`/Users/ashmelev/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs`.

The first sandboxed unit run could not bind its local HTTP fixture server.
The rerun with localhost access passed all 304 tests.
The first WebKit launch used a runtime version without a matching installed browser.
The rerun used the installed matching module and passed.

## Burnier-specific coverage

The map has 22 products: 20 exact snapshot identities and two official additions.
The saved baseline reproduces all 20 exact producer rows from the checksummed snapshot.
All descriptions, names and grape lists for linked wines match the snapshot.
Every source URL, image input checksum and output checksum is recorded.
Nineteen snapshot image files retain their original bytes.

Both engines check all 20 exact `wine` query selections at 390 px.
Each selection opens the popup with the original portal URL and the expected bottle asset.
The checks also cover a linked selection at 1440 px and both unlinked Exponat wines at each width.
The Exponat popups have no portal links.
The Pinot Blanc popup uses the corrected official Pinot Blanc image.

The broader producer suite checks desktop light and dark themes, 390 px light, and 320 px dark.
It checks popup return state, group descriptions, unavailable markers, source images, navigation and page overflow.
The Abrau suite also checks the producer index, scan-result and shelf integration, map loading, dialog controls, delayed fonts and breakpoint transitions.

## Visual inspection

Inspect all 22 source outlines on flat light and dark surfaces at map-node and detail sizes.
The bottle contours have no opaque background rectangles or clipped edges.
Inspect the expanded desktop map, mobile dark popups, both Exponat additions and the corrected Pinot Blanc bottle.
The complete product images fit the measured frames.

Local screenshots and the Burnier verification script are in the ignored `reports/burnier/` directory.
The generic suite reports are in `reports/producer-maps/` and `reports/product-line-map/`.
These checks use emulated viewports. No physical device check was made.
The Burnier-specific check isolates analytics requests to prevent unrelated network errors.
