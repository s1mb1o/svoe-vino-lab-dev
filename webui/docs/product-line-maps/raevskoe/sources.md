# Раевское product-line map

Materials checked: 2026-10-19.
Route: `/lineup/raevskoe`.

## Coverage

The map contains 24 products in 6 groups.
It includes all 23 exact `Раевское` snapshot rows and one selected official addition.
The addition is selectable without a portal link. Current full coverage and retail availability are not asserted.

The source snapshot is `<workspace>/svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl`.
The workspace is `/Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace`.
Snapshot SHA-256: `e915493a0a960df040b4055d33c815940e48fb1a2994a7979a819786b2c41961`.
`catalog-baseline.json` retains the exact names, descriptions, grapes and slugs.
`crosswalk.json` records membership decisions and image input and output hashes.
`source-evidence.json` records source URLs, retrieval times, reviewed sections and content hashes.

## Sources

- [Раевское: описание коллекций](https://raevskoe.com/). Reviewed section: Collection sections and winery history. Hash content type: `text/html`.
- [Раевское: официальный ассортимент](https://raevskoe.com/catalog/). Reviewed section: Collection filter and product cards. Hash content type: `text/html`.
- [Раевское: Генезис Бланк Де Бланкс](https://raevskoe.com/assortiment/genezis/genezis-blank-de-blanks). Reviewed section: Grape composition and production method. Hash content type: `text/html`.

## Groups

| Group | Products | Rank | Membership basis |
| --- | ---: | ---: | --- |
| `genesis` | 3 | 3 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `renaissance` | 12 | 3 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `parfum` | 6 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `genesis-sparkling` | 1 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `eklego` | 1 | 0 | Exact snapshot name and original package only. |
| `glow` | 1 | 0 | Exact snapshot name and original package only. |

## Identity and positioning

Every snapshot row remains a separate product. No slug aliases are added.
Repeated same-name cards use neutral catalog-card numbers when needed. These numbers do not claim a vintage, size, release order or quality difference.
Numeric slug suffixes do not establish prices, alcohol or vintages.
All prices remain null. Ranks are editorial collection guidance. Rank 0 means that no common relative price position is confirmed.
Current official production facts do not replace historical snapshot descriptions or grape lists.

All 23 exact saved cards remain linked. The separate Genesis sparkling wine is an official addition without a snapshot link.
Renaissance and Genesis share one editorial premium band. The producer evidence does not establish a measured price order between them.
Eklego and Glow are snapshot-only groups at rank 0.

## Images

Local assets use the exact saved WebP bytes, except the documented Southern Vertical display derivative in the Chateau de Talu map.
The selected official addition uses the exact official image or lossless PNG-to-WebP encoding. No source image is enlarged.
Every image has a frame measured from alpha values of at least 128, with a 0.5 percent margin of visible height.
The original source dimensions remain in frame metadata.
Inspect all bottle outlines on flat light and dark surfaces and at the actual map and popup sizes.
