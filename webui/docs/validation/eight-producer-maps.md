# Eight producer map extension

Date: 2026-10-17.
Branch: `product-line-map`.
Local preview: `http://127.0.0.1:18553`.

## Scope

Add 370 exact snapshot cards and eight verified official additions.
The extension contains 378 product nodes in 81 groups.
Keep one JSON and one implementation commit per winery.
Do not merge distinct catalog cards.
Keep numeric prices null. Use editorial relative tiers.
Use rank 0 when price comparison lacks evidence.

| Producer ID | Catalog cards | Gray additions | Groups | Commit |
| --- | ---: | ---: | ---: | --- |
| `soyuz-vino` | 69 | 1 | 19 | `b2d39a20` |
| `esse` | 53 | 1 | 6 | `d4f791e6` |
| `chateau-pinot` | 50 | 1 | 13 | `c8d90377` |
| `valery-zakharyin` | 46 | 1 | 14 | `ecfaf230` |
| `novy-svet` | 44 | 1 | 6 | `97ffca61` |
| `belbek` | 39 | 1 | 8 | `0ea8c714` |
| `sober-bash` | 37 | 1 | 6 | `09cfcf0a` |
| `agora` | 32 | 1 | 9 | `2b207ff3` |

## Verification

All 276 unit tests passed with the full snapshot.
Type checks and the production build passed.
The producer browser suite passed 81 cases in Chromium and 81 cases in WebKit.
The complete Abrau regression suite passed in both engines.
The Abrau suite includes scanner and shelf entry, delayed fonts, touch and mouse controls, nested dialogs, keyboard focus, landscape viewports, and breakpoint transitions.
The final git diff check passed.
The suites check 1440 px in both themes, 390 px in light theme, and 320 px in dark theme.
They check exact initial selection, group expansion, gray details, portal links, producer navigation, popup entry, and map return state.
All 1046 current product image references decode and have measured alpha outlines.
All 378 new image frames match their final asset dimensions.
Inspect final contact sheets at logical bottle sizes on light and dark surfaces.
There are 67 selected imagegen derivatives.
Keep input, generated, and output hashes and exact prompts in producer provenance.
Generated fine print is not product evidence.
Browser checks use device emulation. No physical phone was tested.

## Source limitations

The separate Сатера snapshot card is outside the 53-card ESSE baseline.
Do not claim that a producer-name fallback represents that card.
The Бельбек Белое сухое card contradicts its red color and Cabernet metadata.
Keep that card isolated with a visible conflict badge.
The Собер Баш Аза 2016 addition is an archive product.
The live La Petite Perle home-page promotion shows an alcohol-free can.
Use the exact alcoholic can photo from the alcoholic collection page instead.
The public Novy Svet site had an expired TLS certificate during source retrieval.
Use the verified public collection information. Do not send credentials.

## External review

The owner approved the exact packet on 2026-10-17.
Claude Opus 5.5 with effort max completed the review.
Read [the resolution and evidence](../reviews/2026-10-17-eight-producer-maps-resolution.md).
Confirmed findings were corrected and validated locally.
No second external approval is claimed.
The corrected maps retain 370 catalog cards and eight official additions.
The two new neutral groups bring the total to 81 groups.

## Catalog coverage

Read [current catalog coverage](catalog-lineup-coverage.md).
The 19 maps cover 988 of 2103 snapshot cards (46.9805%).
Supported producer coverage is 988 of 989 cards.
Keep the owner-approved Abrau exclusion until exact identification.

## Review verification, 2026-10-17

The full snapshot run passed 276 tests with no skipped tests.
The producer suite passed 81 cases in each engine.
The complete Abrau suite passed in each engine.
Type checks, the production build, all 1046 pixel/frame checks, all 370 linked input hashes, and all 67 imagegen records passed.
Read `source-evidence.json` and `group_basis` for each reviewed producer.
