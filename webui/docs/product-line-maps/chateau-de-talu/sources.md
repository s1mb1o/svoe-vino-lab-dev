# Chateau de Talu product-line map

Materials checked: 2026-10-19.
Route: `/lineup/chateau-de-talu`.

## Coverage

The map contains 27 products in 6 groups.
It includes all 26 exact `Chateau de Talu` snapshot rows and one selected official addition.
The addition is selectable without a portal link. Current full coverage and retail availability are not asserted.

The source snapshot is `<workspace>/svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl`.
The workspace is `/Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace`.
Snapshot SHA-256: `e915493a0a960df040b4055d33c815940e48fb1a2994a7979a819786b2c41961`.
`catalog-baseline.json` retains the exact names, descriptions, grapes and slugs.
`crosswalk.json` records membership decisions and image input and output hashes.
`source-evidence.json` records source URLs, retrieval times, reviewed sections and content hashes.

## Sources

- [Шато де Талю: коллекции вин](https://chateaudetalu.ru/wine-collections/). Reviewed section: Collection headings and wine lists. Hash content type: `web-extracted-text`.
- [Шато де Талю: Шираз основной коллекции](https://chateaudetalu.ru/wine-collections/chateau_de_talu/ch-teau-de-talu-shiraz/). Reviewed section: Main collection Shiraz: grape, style and production. Hash content type: `web-extracted-text`.

## Groups

| Group | Products | Rank | Membership basis |
| --- | ---: | ---: | --- |
| `exclusive` | 2 | 4 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `reserve` | 6 | 3 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `chateau` | 7 | 2 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `french-lessons` | 7 | 1 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `southern-vertical` | 3 | 0 | Exact snapshot name and original package only. |
| `miroir` | 2 | 0 | Exact snapshot name and original package only. |

## Identity and positioning

Every snapshot row remains a separate product. No slug aliases are added.
Repeated same-name cards use neutral catalog-card numbers when needed. These numbers do not claim a vintage, size, release order or quality difference.
Numeric slug suffixes do not establish prices, alcohol or vintages.
All prices remain null. Ranks are editorial collection guidance. Rank 0 means that no common relative price position is confirmed.
Current official production facts do not replace historical snapshot descriptions or grape lists.

The map covers all 26 saved cards. The main Shiraz addition is absent from the snapshot; Reserve Shiraz does not replace it.
Direct HTML requests for the official collection and Shiraz pages returned HTTP 502. The source hashes identify the retrieved web-extracted text, not HTML bytes.
Southern Vertical and Miroir use snapshot-only group evidence and rank 0. The premium and reserve words in their saved names do not establish a numeric price band.

## Images

Local assets use the exact saved WebP bytes, except the documented Southern Vertical display derivative in the Chateau de Talu map.
The selected official addition uses the exact official image or lossless PNG-to-WebP encoding. No source image is enlarged.
Every image has a frame measured from alpha values of at least 128, with a 0.5 percent margin of visible height.
The original source dimensions remain in frame metadata.
Inspect all bottle outlines on flat light and dark surfaces and at the actual map and popup sizes.
