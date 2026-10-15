# Золотая Балка: source record

Date: 2026-10-16.

## Scope

- The exact catalog producer value is `Золотая Балка`.
- The map contains all 41 producer cards from `official-2026-09-17`.
- The map adds 2 products with official evidence and no confirmed snapshot identity.
- Each snapshot card has one product. All alias arrays are empty.
- Original catalog descriptions and grape lists are retained.
- Catalog WebP files are copied without modification. SHA-256 values are in `crosswalk.json`.
- Official PNG and JPEG bottle images are converted to lossless WebP without cropping or resizing. Original URLs and asset hashes are in the crosswalk.
- Numeric prices are null. Premium tiers are editorial relative positions.
- A neutral tier means that the current relative price is not verified. It does not mean low quality.
- A gray node means no confirmed card in the saved snapshot. It does not establish current shop availability.

## Official collection sources

- `official-collections`: https://zolotayabalka.ru/product/
- `official-black-prince`: https://zolotayabalka.ru/product/black-prince/
- `official-cuvee-de-vitmer`: https://zolotayabalka.ru/product/cuvee-de-vitmer/
- `official-balaklava`: https://zolotayabalka.ru/product/balaklava/
- `official-zb-classic`: https://zolotayabalka.ru/product/zolotaya-balka/
- `official-zb-spumante`: https://zolotayabalka.ru/product/zb-spumante/
- `official-zb-moscato`: https://zolotayabalka.ru/product/zb-moscato/
- `official-zb-frizzante`: https://zolotayabalka.ru/product/zb-frizzante/
- `official-zb-still`: https://zolotayabalka.ru/product/zbwine/
- `official-more-nebo`: https://zolotayabalka.ru/product/more-nebo/
- `official-loco-menu`: https://zolotayabalka.ru/pdf/zb_wines_06-2025.pdf
- `official-more-nebo-red`: https://zolotayabalka.ru/product/more-nebo/more-nebo-polusukhoe-krasnoe/
- `official-more-nebo-white`: https://zolotayabalka.ru/product/more-nebo/more-nebo-bryut-beloe/

## Mapping decisions and limits

- Two generic rose cards use the base Zolotaya Balka labels. The local label images confirm this assignment.
- Blanc de Neige and Pink appear as Loco Cimbali in the official restaurant PDF. The PDF is evidence for collection identity only. Restaurant prices are not copied or used as current retail prices.
- The historical Moscato, Spumante, Frizzante, and Balaklava cards remain separate. Similar names do not establish equivalent slugs.
- The neutral tier contains Frizzante, Loco Cimbali, and More & Nebo. Their current retail position is not verified.

## Official additions and absence checks

### official-more-nebo-red-semi-dry

- Product page: https://zolotayabalka.ru/product/more-nebo/more-nebo-polusukhoe-krasnoe/
- Exact bottle image: https://zolotayabalka.ru/upload/resize_cache/iblock/cfc/800_800_0/nvjnssh23cmwtfk2xssu0jvro95mlj9k.jpg
- Absence evidence: No Zolotaya Balka catalog card names the More & Nebo collection. The full 2,103-row search only finds an unrelated Locantita More card from Skalisty Bereg. Syrah alone does not identify this product.
- The producer subset and the full 2,103-row catalog were searched. No available snapshot card is replaced.

### official-more-nebo-white-brut

- Product page: https://zolotayabalka.ru/product/more-nebo/more-nebo-bryut-beloe/
- Exact bottle image: https://zolotayabalka.ru/upload/resize_cache/iblock/beb/800_800_0/qz5af68fwwyxn9crel1nuxkimqdm94ae.jpg
- Absence evidence: The More & Nebo collection is absent from all 41 producer cards. Other white bruts have different brand labels. No equivalent identity is asserted.
- The producer subset and the full 2,103-row catalog were searched. No available snapshot card is replaced.

## Collection coverage

| Group | Snapshot cards | Official additions |
| --- | ---: | ---: |
| Чёрный Принц | 2 | 0 |
| Cuvée de Vitmer | 2 | 0 |
| Балаклава | 6 | 0 |
| Золотая Балка | 9 | 0 |
| ZB Spumante | 6 | 0 |
| ZB Moscato / Мускатные | 4 | 0 |
| ZB Wine · тихие вина | 5 | 0 |
| ZB Frizzante / Жемчужные | 5 | 0 |
| Loco Cimbali | 2 | 0 |
| Море & Небо | 0 | 2 |

## Image limits

The following catalog rows have `local_path: null`. The map uses `image: null` and the explicit UI placeholder. No other bottle image is substituted.

- `polusladkoe-krasnoe-zb-vajn-frizzante`
- `polusladkoe-krasnoe-zolotaya-balka`
- `polusladkoe-rozovoe-zolotaya-balka`
- `polusuhoe-rozovoe-zb-vajn-frizzante`
- `suhoe-beloe-zb-vajn-frizzante`
- `zb-vajn-risling-polusuhoe-beloe`
- `zb-vajn-roze-suhoe-rozovoe`
- `zb-vajn-spumante-polusuhoe-beloe`

All official addition images were visually checked against their product labels.
