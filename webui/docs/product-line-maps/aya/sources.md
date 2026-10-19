# AYA Organic Wine & Vineyards product-line map

Materials checked: 2026-10-19.
Route: `/lineup/aya`.

## Coverage

The map contains 28 products in 9 groups.
It includes all 27 exact `AYA Organic Wine & Vineyards` snapshot rows and one selected official addition.
The addition is selectable without a portal link. Current full coverage and retail availability are not asserted.

The source snapshot is `<workspace>/svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl`.
The workspace is `/Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace`.
Snapshot SHA-256: `e915493a0a960df040b4055d33c815940e48fb1a2994a7979a819786b2c41961`.
`catalog-baseline.json` retains the exact names, descriptions, grapes and slugs.
`crosswalk.json` records membership decisions and image input and output hashes.
`source-evidence.json` records source URLs, retrieval times, reviewed sections and content hashes.

## Sources

- [AYA: официальный каталог вин](https://www.aya-wine.ru/wine). Reviewed section: Named family sections in the wine catalog. Hash content type: `text/html`.
- [AYA: Purity in balance](https://www.aya-wine.ru/wine/purity-in-balance/2025). Reviewed section: Purity in balance 2025: grape composition and production. Hash content type: `text/html`.

## Groups

| Group | Products | Rank | Membership basis |
| --- | ---: | ---: | --- |
| `evolution-reserve` | 1 | 3 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `marquetry` | 3 | 3 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `appassimento` | 1 | 3 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `evolution` | 3 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `evolution-sparkling` | 2 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `purity` | 6 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `khrustaleva` | 4 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `toile` | 4 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `blush` | 4 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |

## Identity and positioning

Every snapshot row remains a separate product. No slug aliases are added.
Repeated same-name cards use neutral catalog-card numbers when needed. These numbers do not claim a vintage, size, release order or quality difference.
Numeric slug suffixes do not establish prices, alcohol or vintages.
All prices remain null. Ranks are editorial collection guidance. Rank 0 means that no common relative price position is confirmed.
Current official production facts do not replace historical snapshot descriptions or grape lists.

The map covers all 27 exact saved identities and one verified Purity addition. It is not a complete current catalog.
The oak band is editorial technology guidance. Its twelve-month values come from the exact saved descriptions; it does not claim current retail price bands.
The ambiguous historical Khrustaleva Merlot card retains its saved name, grapes and description. No sweetness or sparkling status is inferred from its image alone.

## Images

Local assets use the exact saved WebP bytes, except the documented Southern Vertical display derivative in the Chateau de Talu map.
The selected official addition uses the exact official image or lossless PNG-to-WebP encoding. No source image is enlarged.
Every image has a frame measured from alpha values of at least 128, with a 0.5 percent margin of visible height.
The original source dimensions remain in frame metadata.
Inspect all bottle outlines on flat light and dark surfaces and at the actual map and popup sizes.
