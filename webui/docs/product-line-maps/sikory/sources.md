# Имение Сикоры product-line map

Materials checked: 2026-10-19.
Route: `/lineup/sikory`.

## Coverage

The map contains 22 products in 6 groups.
It includes all 21 exact `Имение Сикоры` snapshot rows and one selected official addition.
The addition is selectable without a portal link. Current full coverage and retail availability are not asserted.

The source snapshot is `<workspace>/svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl`.
The workspace is `/Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace`.
Snapshot SHA-256: `e915493a0a960df040b4055d33c815940e48fb1a2994a7979a819786b2c41961`.
`catalog-baseline.json` retains the exact names, descriptions, grapes and slugs.
`crosswalk.json` records membership decisions and image input and output hashes.
`source-evidence.json` records source URLs, retrieval times, reviewed sections and content hashes.

## Sources

- [Имение Сикоры: ассортимент](https://sikory.ru/wine/). Reviewed section: Category filters and wine cards. Hash content type: `text/html`.
- [Имение Сикоры: Семейное Наследие](https://sikory.ru/semejnoe-nasledie2020). Reviewed section: Creation history of Family Heritage 2020. Hash content type: `text/html`.
- [Имение Сикоры: Riesling Extra Brut](https://sikory.ru/riesling). Reviewed section: Riesling sparkling product characteristics. Hash content type: `text/html`.

## Groups

| Group | Products | Rank | Membership basis |
| --- | ---: | ---: | --- |
| `heritage` | 1 | 4 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `family-reserve` | 7 | 3 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `core` | 9 | 2 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `terraces` | 2 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `late-harvest` | 2 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |
| `sparkling` | 1 | 0 | Exact snapshot identity and official named family. No release equivalence is inferred. |

## Identity and positioning

Every snapshot row remains a separate product. No slug aliases are added.
Repeated same-name cards use neutral catalog-card numbers when needed. These numbers do not claim a vintage, size, release order or quality difference.
Numeric slug suffixes do not establish prices, alcohol or vintages.
All prices remain null. Ranks are editorial collection guidance. Rank 0 means that no common relative price position is confirmed.
Current official production facts do not replace historical snapshot descriptions or grape lists.

All 21 exact producer rows remain separate. The official extra-brut Riesling addition has no counterpart among these still-wine records.
Heritage positioning is editorial and follows the selected-plot and bottle-aging evidence for the official 2020 release. It does not assert the vintage of the saved card.
The reserve and main bands follow named producer collections. Sweet, terrace and sparkling wines remain outside their common price comparison.

## Images

Local assets use the exact saved WebP bytes, except the documented Southern Vertical display derivative in the Chateau de Talu map.
The selected official addition uses the exact official image or lossless PNG-to-WebP encoding. No source image is enlarged.
Every image has a frame measured from alpha values of at least 128, with a 0.5 percent margin of visible height.
The original source dimensions remain in frame metadata.
Inspect all bottle outlines on flat light and dark surfaces and at the actual map and popup sizes.
