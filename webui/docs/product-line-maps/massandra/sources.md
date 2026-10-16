# Массандра: source record

Date: 2026-10-16.

## Scope

- The exact catalog producer value is `Массандра`.
- The map contains all 44 producer cards from `official-2026-09-17`.
- The map adds 2 products with official evidence and no confirmed snapshot identity.
- Each snapshot card has one product. All alias arrays are empty.
- Original catalog descriptions and grape lists are retained.
- Catalog WebP files are copied without modification. SHA-256 values are in `crosswalk.json`.
- Official PNG and JPEG bottle images are converted to lossless WebP without cropping or resizing. Original URLs and asset hashes are in the crosswalk.
- Numeric prices are null. Premium tiers are editorial relative positions.
- A neutral tier means that the current relative price is not verified. It does not mean low quality.
- A gray node means no confirmed card in the saved snapshot. It does not establish current shop availability.

## Official collection sources

- `official-collections`: https://massandra.ru/catalog/
- `official-premium`: https://massandra.ru/catalog/vino-tikhoe/premium/
- `official-author`: https://massandra.ru/catalog/vino-tikhoe/avtorskie/
- `official-base`: https://massandra.ru/catalog/vino-tikhoe/bazovaya-lineyka/
- `official-late-harvest`: https://massandra.ru/catalog/vino-tikhoe/muskat-pozdnego-sbora/
- `official-port`: https://massandra.ru/catalog/vina-tikhie-kreplenye/portveyn/
- `official-sherry`: https://massandra.ru/catalog/vina-tikhie-kreplenye/kheres/
- `official-madeira`: https://massandra.ru/catalog/vina-tikhie-kreplenye/madera/
- `official-cahors`: https://massandra.ru/catalog/vina-tikhie-kreplenye/kagor/
- `official-dessert`: https://massandra.ru/catalog/vina-tikhie-kreplenye/desertnye/
- `official-malaga`: https://massandra.ru/catalog/vina-tikhie-kreplenye/desertnye/marochnoe-vino/klassika-massandry/malaga-massandra/
- `official-black-muscat`: https://massandra.ru/catalog/vina-tikhie-kreplenye/desertnye/marochnoe-vino/muskaty/muskat-chernyy-massandra/

## Mapping decisions and limits

- The current official premium page lists Kokur Premium and Stolovoe Krasnoe Alushta. Premium Sangiovese remains from the historical snapshot; its name supports the premium grouping but does not prove current availability.
- The catalog spelling Херес Ореадна is preserved. No alias to the current Херес Ореанда product is created.
- Late-harvest cards with similar names remain separate. No alcohol value or production year is derived from slug suffixes.
- Fortified styles contain both ordinary and aged products. They use a neutral tier instead of one invented premium ranking.
- Muscatel black is not the added Muscat black. Both identities remain separate.

## Official additions and absence checks

### official-malaga

- Product page: https://massandra.ru/catalog/vina-tikhie-kreplenye/desertnye/marochnoe-vino/klassika-massandry/malaga-massandra/
- Exact bottle image: https://massandra.ru/upload/iblock/205/fcswy6poi8plxzxkbb4q29yhu63hugj5.png
- Absence evidence: No Malaga name or slug occurs anywhere in the full 2,103-row snapshot. Massandra fortified blends with similar grapes have different product identities.
- The producer subset and the full 2,103-row catalog were searched. No available snapshot card is replaced.

### official-black-muscat

- Product page: https://massandra.ru/catalog/vina-tikhie-kreplenye/desertnye/marochnoe-vino/muskaty/muskat-chernyy-massandra/
- Exact bottle image: https://massandra.ru/upload/iblock/593/wruwbjbd11yr7eyrvqxy2einkk1l1790.png
- Absence evidence: The full snapshot has a black Muscat card from AGORA WINERY only. Massandra Muscatel black is a different product type and name. Neither is substituted.
- The producer subset and the full 2,103-row catalog were searched. No available snapshot card is replaced.

## Collection coverage

| Group | Snapshot cards | Official additions |
| --- | ---: | ---: |
| Премиум | 2 | 0 |
| Авторское вино | 12 | 0 |
| Базовая линейка | 6 | 0 |
| Мускат позднего сбора | 4 | 0 |
| Портвейны | 6 | 0 |
| Хересы | 2 | 0 |
| Мадеры | 1 | 0 |
| Кагоры | 2 | 0 |
| Десертные вина | 9 | 2 |

## Image limits

The following catalog rows have `local_path: null`. The map uses `image: null` and the explicit UI placeholder. No other bottle image is substituted.

- `beloe-polusladkoe`

All official addition images were visually checked against their product labels.

## Visible image frames, 2026-10-16

The producer JSON records measured frame geometry for 45 images.
The frame uses the source alpha outline and a small transparent margin.
The frame changes image presentation only. Source image bytes and product facts are unchanged.
The renderer uses the frame for group previews, product nodes and product details.
Read [the sizing contract](../../product-image-sizing.md) for the measurement method.

## Missing bottle-image recovery, 2026-10-16

Restore 1 empty bottle-image slots from exact official product pages.
Read [image-recovery.json](image-recovery.json) for source URLs, original hashes, exact prompts, output hashes, and measured frames.
The earlier placeholder notes describe the previous state. This recovery supersedes those notes.
The official base-collection white semi-sweet product supplies the missing transparent photo. Preserve its existing label year as image content. Do not add that year to product facts.
