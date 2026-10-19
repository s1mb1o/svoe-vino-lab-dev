# Five more producer maps

Date: 2026-10-19.
Preview origin: `http://127.0.0.1:18553`.

## Coverage

| Producer route | Saved cards | Official additions | Total products | Groups |
| --- | ---: | ---: | ---: | ---: |
| `/lineup/golubitskoe-estate` | 33 | 1 | 34 | 7 |
| `/lineup/chateau-de-talu` | 26 | 1 | 27 | 6 |
| `/lineup/aya` | 27 | 1 | 28 | 9 |
| `/lineup/raevskoe` | 23 | 1 | 24 | 6 |
| `/lineup/sikory` | 21 | 1 | 22 | 6 |
| Total | 130 | 5 | 135 | 34 |

The map registry now contains 25 producers.
The new source records are under `docs/product-line-maps/<producer-id>/`.
Each record includes a catalog baseline, crosswalk, reviewed source sections, retrieval dates and hashes.

The Golubitskoe baseline includes 31 `Golubitskoe Estate` records and two `Поместье Голубицкое` records.
Official producer evidence confirms the same winery. The source producer field remains verbatim in each crosswalk entry.
The full-catalog attribution test checks every entry against the independent producer projection.
The addition absence check must include both exact producer names.

The five selected additions are Tête de Cheval Semi-dry, main-collection Talu Shiraz, Purity in balance, Genesis Blanc de Blancs, and Sikory Riesling Extra Brut.
Each addition is selectable with a bottle image and local details. None receives an invented snapshot link.
This subset does not claim full current assortment coverage.

## Automated checks

| Check | Result |
| --- | --- |
| Full unit suite with the exact source snapshot | 329 tests pass in 17 files; no skipped tests |
| Type check | Pass |
| Production build and prebuild map validation | Pass |
| Generated-index freshness | Pass; 25 maps |
| Final scope-text copy and server rendering | Pass; all five routes return HTTP 200 and render the final wording |
| Pixel/frame checker | Pass; 1,203 images across 25 maps; no clipped alpha outlines |
| Production bundle check | Pass; 25 separate lazy map chunks; no full map data at scanner first paint |
| Targeted new-map browser checks, Chromium | 145 checks pass; no browser errors or hydration warnings |
| Targeted new-map browser checks, WebKit | 145 checks pass; no browser errors or hydration warnings |
| Producer browser suite, Chromium | 105 checks pass; no browser errors or hydration warnings |
| Producer browser suite, WebKit | 105 checks pass; no browser errors or hydration warnings |
| Abrau regression suite, Chromium and WebKit | Pass in both engines |

The full snapshot path is:
`/Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace/svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl`.
Set `PRODUCT_LINE_CATALOG_SNAPSHOT` to this path for independent baseline reproduction.
Its SHA-256 is `e915493a0a960df040b4055d33c815940e48fb1a2994a7979a819786b2c41961`.

Browser checks use:
`PLAYWRIGHT_MODULE=/Volumes/Storage/svoe-vino-final/code/wine-and-dine-merge/node_modules/playwright/index.mjs`.
Set `PORTAL_ORIGIN` to the preview origin. Set `PLAYWRIGHT_BROWSER=webkit` for WebKit.
The pixel checker uses the bundled Sharp entry at
`/Users/ashmelev/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs`.

## Targeted browser coverage

Both engines open all 130 exact saved `wine` query selections at 390 px.
Each selection must select the correct product, show its expected bottle asset, and retain the exact portal URL.
Both engines also check an initial linked selection at 1440 px, and all five official additions at both widths.
The checks verify popup bounds, return controls, complete map expansion and horizontal overflow.
They wait for fonts, image decoding and rendering before screenshots.
Analytics requests are isolated in this targeted check.

The first broad WebKit producer run passed 102 cases before a network-idle timeout on the existing Zolotaya Balka mobile page.
It recorded no browser errors. The producer suite now also isolates external analytics requests. The complete rerun passes all 105 WebKit cases.

## Images and visual inspection

All 129 unchanged catalog bottle assets retain their original WebP bytes.
One Southern Vertical Cabernet Franc asset uses a transparent display derivative made with built-in imagegen.
Its original source remains identity evidence. Its prompt and input, generated and output hashes are in `docs/product-line-maps/chateau-de-talu/imagegen-cutouts.json`.
The derivative keeps the complete bottle, capsule and main label artwork. Generated fine print does not establish product identity.
Four official additions use lossless PNG-to-WebP encoding. The Talu Shiraz addition retains the official WebP bytes.

Inspect the bottle outlines on flat light and dark surfaces at the actual map and popup sizes.
Inspect all five expanded desktop maps and their mobile dark popups.
The new frames preserve complete outlines and consistent bottle scale.
Same-name catalog records retain separate nodes and neutral card numbers where needed.
Independent sparkling, sweet and unconfirmed historical groups retain neutral ranks where required.

The ignored `reports/five-producer-maps/` directory contains the targeted check script and screenshots.
The general browser reports are in `reports/producer-maps/` and `reports/product-line-map/`.
These are emulated viewport checks. No physical-device check was made.
