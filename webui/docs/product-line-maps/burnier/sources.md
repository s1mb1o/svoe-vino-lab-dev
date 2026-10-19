# Burnier product-line map

Materials checked: 2026-10-19.
Route: `/lineup/burnier`.

## Coverage and identity

The map contains 22 products in six groups.
It covers all 20 records whose exact producer is `Винодельня Бюрнье` in `official-2026-09-17`.
Two official Exponat wines have no verified snapshot slug. They remain selectable without a portal link.
The map does not assert current retail availability or complete current coverage.

The snapshot is `<workspace>/svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl`.
The workspace is `/Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace`.
Its SHA-256 is `e915493a0a960df040b4055d33c815940e48fb1a2994a7979a819786b2c41961`.
`catalog-baseline.json` retains the exact source names, descriptions, grapes and slugs.
`crosswalk.json` records each membership decision and each image checksum.
`source-evidence.json` records the exact source URLs, retrieval times, HTML hashes and reviewed sections.

No snapshot identities are merged. There are no slug aliases.
Classic Krasnostop and Syrah remain separate from Elite Krasnostop and Syrah.
Dry Pinot Gris remains separate from sweet late-harvest Pinot Gris.
Numeric slug suffixes do not establish an alcohol content, vintage or price.
Official card vintages do not replace historical snapshot metadata.

## Sources and groups

The requested [winery page](https://vino-svoe.ru/wineries/vinodelnya-byurne) identifies the producer and the new collections.
The [official wine catalog](https://burnier.vin/wines.html) lists 22 wine cards.
Each official product page is also recorded in the source registry.

| Group | Products | Membership evidence | Rank |
| --- | ---: | --- | ---: |
| Elite Series | 3 | Original dark labels and wax capsules; official catalog image alt text names the Elite Series. The three official product pages specify 36 months in French barriques. | 3 |
| Classic varietal wines | 10 | Exact snapshot names and grapes; original light labels; corresponding official varietal cards. The portal names new Classic releases. This is a navigation group with different production methods. | 0 |
| Lyublyu | 3 | Exact collection names, colors and original hand artwork; three official cards. | 0 |
| Vinisazh | 3 | Exact collection names, colors and original painting artwork; three official cards. | 0 |
| Exponat | 2 | Official white and red Exponat cards and bottle images. No Exponat name or package occurs in the 20 exact snapshot rows. | 0 |
| Pinot Gris Late Harvest | 1 | Exact snapshot sweet late-harvest identity and separate official product card. | 0 |

The Elite rank is an editorial premium cue from the official series name and production evidence.
It is not a measured price band or quality score.
The sources do not establish the price order of the other collections. Their rank stays 0.
All numeric prices are null.

## Images

Nineteen bottle assets retain the exact saved WebP bytes.
The Exponat bottle images come from the individual official pages.
The Pinot Blanc bottle also comes from the official Pinot Blanc page.
These three PNG files are encoded as lossless WebP. No source pixels are repainted, cropped or enlarged.
All images have a measured frame. The frame contains alpha values of at least 128, with a margin of 0.5% of visible height.
The source dimensions remain in the frame metadata.

The snapshot Pinot Blanc row incorrectly uses `Vione_2023_13d6c1ebf6.webp`, the same asset as Viognier.
The original label reads Viognier. It must not represent Pinot Blanc in this map.
The map uses [the official Pinot Blanc bottle](https://burnier.vin/wines/pinot_blanc.html).
The crosswalk retains the original erroneous image hash and the official replacement hash.
The corrected display image does not assert an exact vintage match.
The underlying snapshot and catalog metadata remain unchanged.

Exponat descriptions are short editorial summaries of the official cards.
Snapshot descriptions remain verbatim.
No image generation is used.
