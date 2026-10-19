# Golubitskoe Estate product-line map

Materials checked: 2026-10-19.
Route: `/lineup/golubitskoe-estate`.

## Coverage

The map contains 34 products in 7 groups.
It includes 31 exact `Golubitskoe Estate` rows, two exact `Поместье Голубицкое` rows, and one selected official addition.
The addition is selectable without a portal link. Current full coverage and retail availability are not asserted.

The source snapshot is `<workspace>/svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl`.
The workspace is `/Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace`.
Snapshot SHA-256: `e915493a0a960df040b4055d33c815940e48fb1a2994a7979a819786b2c41961`.
`catalog-baseline.json` retains the exact names, descriptions, grapes and slugs.
`crosswalk.json` records membership decisions and image input and output hashes.
`source-evidence.json` records source URLs, retrieval times, reviewed sections and content hashes.

## Sources

- [Поместье Голубицкое: классическая и резервная коллекции](https://www.golubitskoe-estate.ru/). Reviewed section: Classic and Reserve collection tabs and product modals. Hash content type: `text/html`.
- [NOVABEV GROUP: Golubitskoe Estate](https://novabev.com/brands/wine/russia/golubitskoe-estate/). Reviewed section: Classic, Reserve and Limited collections. Hash content type: `text/html`.
- [NOVABEV GROUP: Noble Selection · публикация 2022 года](https://novabev.com/press-room/lenta/new-wines-in-the-golubitskoe-estate-noble-selection-line/). Reviewed section: Noble Selection Cabernet Sauvignon and Red Blend. Hash content type: `text/html`.
- [NOVABEV GROUP: Tête de Cheval](https://novabev.com/brands/wine/russia/tete-de-cheval/). Reviewed section: Main and Reserve sparkling collections. Hash content type: `text/html`.

## Groups

| Group | Products | Rank | Membership basis |
| --- | ---: | ---: | --- |
| `reserve` | 6 | 3 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `classic` | 9 | 2 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `noble` | 5 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `winery` | 3 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `petnat` | 1 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `tete-reserve` | 4 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `tete` | 6 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |

## Identity and positioning

Every snapshot row remains a separate product. No slug aliases are added.
Repeated same-name cards use neutral catalog-card numbers when needed. These numbers do not claim a vintage, size, release order or quality difference.
Numeric slug suffixes do not establish prices, alcohol or vintages.
All prices remain null. Ranks are editorial collection guidance. Rank 0 means that no common relative price position is confirmed.
Current official production facts do not replace historical snapshot descriptions or grape lists.

The snapshot has 31 rows under Golubitskoe Estate and two under Поместье Голубицкое. Both names identify the same winery in official sources. Their separate source attributions and product identities are retained.
Classic Chardonnay is a linked snapshot card under the alternate producer name. It is not an official-only addition. Tête de Cheval Semi-dry is absent from both exact producer subsets.
The current Petnat White card describes Pinot Gris and Chardonnay, while the saved record names Riesling. Preserve the saved grapes and do not assert release equivalence.

## Images

Local assets use the exact saved WebP bytes, except the documented Southern Vertical display derivative in the Chateau de Talu map.
The selected official addition uses the exact official image or lossless PNG-to-WebP encoding. No source image is enlarged.
Every image has a frame measured from alpha values of at least 128, with a 0.5 percent margin of visible height.
The original source dimensions remain in frame metadata.
Inspect all bottle outlines on flat light and dark surfaces and at the actual map and popup sizes.
