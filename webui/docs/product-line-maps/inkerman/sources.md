# Инкерман: source record

Date: 2026-10-16.

## Scope

- The exact catalog producer value is `Инкерманский ЗМВ`.
- The map contains all 15 producer cards from `official-2026-09-17`.
- The map adds 2 products with official evidence and no confirmed snapshot identity.
- Each snapshot card has one product. All alias arrays are empty.
- Original catalog descriptions and grape lists are retained.
- Catalog WebP files are copied without modification. SHA-256 values are in `crosswalk.json`.
- Official PNG and JPEG bottle images are converted to lossless WebP without cropping or resizing. Original URLs and asset hashes are in the crosswalk.
- Numeric prices are null. Premium tiers are editorial relative positions.
- A neutral tier means that the current relative price is not verified. It does not mean low quality.
- A gray node means no confirmed card in the saved snapshot. It does not establish current shop availability.

## Official collection sources

- `official-collections`: https://inkerman.ru/catalog/
- `official-special-reserve`: https://inkerman.ru/catalog/special-reserve/
- `official-grand-reserve`: https://inkerman.ru/catalog/grand-reserve/
- `official-winemaker-still`: https://inkerman.ru/catalog/winemakers-selection/
- `official-winemaker-sparkling`: https://inkerman.ru/catalog/winemaker-s-selection/
- `official-base-still`: https://inkerman.ru/catalog/kollektsiya-molodykh-vin/
- `official-sparkling`: https://inkerman.ru/catalog/igristye-vina/
- `official-grand-cabernet`: https://inkerman.ru/catalog/grand-reserve/cabernet-kachinskoe-grand-reserve/
- `official-grand-pearl`: https://inkerman.ru/catalog/grand-reserve/zhemchuzhina-inkermana-grand-reserve/

## Mapping decisions and limits

- The exact catalog producer field is Инкерманский ЗМВ. All 15 rows are included.
- The Saperavi Winemaker Selection card is sparkling. Both its description and the official sparkling collection confirm the classification.
- The generic Winemaker selection card has a Riesling label. It belongs to the still collection.
- The old green brut and pink semi-sweet bottle designs remain in the sparkling collection. They are not merged with newer cards.
- The shared Rkatsiteli grape does not make Special Reserve and Grand Reserve Zhemchuzhina the same product.

## Official additions and absence checks

### official-grand-reserve-cabernet

- Product page: https://inkerman.ru/catalog/grand-reserve/cabernet-kachinskoe-grand-reserve/
- Exact bottle image: https://inkerman.ru/upload/iblock/517/8b41ownq14b7ql92i87e2td7nlyumiox/kaberne.png
- Absence evidence: No Inkerman snapshot card names Grand Reserve or Cabernet Kachinskoe. Grand Reserve cards from other producers in the full snapshot are unrelated.
- The producer subset and the full 2,103-row catalog were searched. No available snapshot card is replaced.

### official-grand-reserve-pearl

- Product page: https://inkerman.ru/catalog/grand-reserve/zhemchuzhina-inkermana-grand-reserve/
- Exact bottle image: https://inkerman.ru/upload/iblock/25d/uniztzx7zr028r0gt2g7sgn1y3xqunyy/zhemchuzhina.png
- Absence evidence: No Inkerman snapshot card names Zhemchuzhina or Grand Reserve. The existing Special Reserve Rkatsiteli has a different collection and must remain a linked product.
- The producer subset and the full 2,103-row catalog were searched. No available snapshot card is replaced.

## Collection coverage

| Group | Snapshot cards | Official additions |
| --- | ---: | ---: |
| Special Reserve | 1 | 0 |
| Grand Reserve | 0 | 2 |
| Winemaker’s Selection · тихие | 1 | 0 |
| Базовая коллекция | 3 | 0 |
| Игристые вина | 9 | 0 |
| Winemaker’s Selection · игристые | 1 | 0 |

## Image limits

Every catalog row has its original local WebP image.

All official addition images were visually checked against their product labels.
