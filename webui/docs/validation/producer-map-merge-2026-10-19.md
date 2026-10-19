# Producer-map merge validation

Date: 2026-10-19.
Base: GitHub `main` at `910e11d7`.
Preview: `http://127.0.0.1:18553`.

## Merge scope

The merge adds Burnier from `7637b25d` and five maps from `2a7ed4b5`.
The five maps are Golubitskoe Estate, Chateau de Talu, AYA, Раевское and Имение Сикоры.
These six maps add 150 exact saved cards and seven null-slug additions: 157 products in 40 groups.

The index and page layout already exist on `main` in `6d0cae18` and `d9cdc6cd`.
The feature branch contains the equivalent commits `96a9d190` and `c61b428e`.
The merge preserves the current application code of `main`.
Log conflicts retain the current `main` entries and add the new producer sections.
The sitemap retains all current routes, including `/lineup`, `/dish`, `/game` and `/crocodile`.

The existing MCP loader reads the new maps without a runtime change.
Its pinned registry and Active-ID counts now match all 25 maps.
Only F-24 and F-48 were refreshed in `ASSESSMENT.md`. The general assessment header and historical scores remain unchanged.

## Current coverage

The source is the complete `official-2026-09-17` catalog snapshot with 2,103 unique cards.
Its SHA-256 is `e915493a0a960df040b4055d33c815940e48fb1a2994a7979a819786b2c41961`.

| Measure | Result |
| --- | ---: |
| Prepared producer maps | 25 |
| Product nodes | 1,203 |
| Groups | 272 |
| Null-slug products | 68 |
| Exact mapped snapshot slugs | 1,135 |
| Verified mapped aliases | 3 |
| Covered snapshot cards | 1,138 / 2,103 (54.1132%) |
| Covered cards of supported producers | 1,138 / 1,139 (99.9122%) |
| Unsupported snapshot cards | 964 |
| Intentionally unplaced supported card | 1 |

The intentional exclusion remains `rozovoe-polusladkoe-2` until exact bottle and collection identification.
Golubitskoe includes both verified exact source producer names. It remains one map.
Null-slug products and producer fallback do not increase catalog coverage.
The totals describe the saved snapshot, not the complete current winery assortments.
Both `catalog-lineup-coverage.json` and `catalog-lineup-coverage.md` were recomputed from the full snapshot.

The separate MCP bundle has 2,093 Active IDs.
Of these IDs, 1,127 resolve by exact slug and three by verified alias. The other 963 return unavailable.
The largest measured producer-line response is 50,126 bytes, below the 128 KiB bound.

## Combined checks

| Check | Result |
| --- | --- |
| Web UI unit suite with full pinned snapshot | 532 tests pass in 23 files; no skips |
| Type check | Pass |
| Production build and prebuild map validation | Pass; 145 map checks in prebuild |
| Generated-index freshness | Pass; 25 producers |
| Image dimensions, alpha and declared-frame containment | Pass; 1,203 images across 25 maps |
| First-load bundle and server-rendered map check | Pass; 25 separate lazy chunks |
| Producer maps, Chromium | 105 cases pass; no browser errors |
| Producer maps, WebKit | 105 cases pass; no browser errors |
| Abrau regressions, Chromium and WebKit | Pass in both engines |
| MCP JavaScript syntax checks | Pass |
| MCP unit and protocol suite | 49 tests pass; no skips |
| MCP SDK client demonstration | Pass |

The first-load JavaScript is 142.7 KB gzip for `/` and 143.0 KB gzip for `/shelf`.
No producer map data loads at first paint. Individual map chunks are 4.7–21.6 KB gzip.

The first local unit attempt could not bind its loopback fixture server inside the sandbox.
The permitted loopback run passes. No test timeout was increased.

The browser suites cover both themes, narrow viewports, exact and alias selection, null-slug products, image failures, portal links, page and canvas layouts, mobile popups, nested shelf dialogs and focus restoration.
The suites use emulated viewports. No physical-phone check was performed.
The previous producer-specific image and catalog evidence remains in the Burnier and five-map reports.

This update does not perform a production deployment.
