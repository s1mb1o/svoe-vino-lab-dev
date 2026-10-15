# Alma Valley: source record

Date: 2026-10-16.

## Scope

- The exact catalog producer value is `Alma Valley`.
- The map contains all 39 producer cards from `official-2026-09-17`.
- The map adds 2 products with official evidence and no confirmed snapshot identity.
- Each snapshot card has one product. All alias arrays are empty.
- Original catalog descriptions and grape lists are retained.
- Catalog WebP files are copied without modification. SHA-256 values are in `crosswalk.json`.
- Official PNG and JPEG bottle images are converted to lossless WebP without cropping or resizing. Original URLs and asset hashes are in the crosswalk.
- Numeric prices are null. Premium tiers are editorial relative positions.
- A neutral tier means that the current relative price is not verified. It does not mean low quality.
- A gray node means no confirmed card in the saved snapshot. It does not establish current shop availability.

## Official collection sources

- `official-collections`: https://www.alma-valley.ru/collection.html
- `official-varietal`: https://www.alma-valley.ru/varietal-wines.html
- `official-reserve`: https://www.alma-valley.ru/reserve-wines.html
- `official-gravity`: https://www.alma-valley.ru/gravity.html
- `official-svv`: https://www.alma-valley.ru/svv.html
- `official-sparkling`: https://www.alma-valley.ru/champagne-wines.html
- `official-sweet-special`: https://www.alma-valley.ru/tba-ice-wine.html
- `official-alma-x`: https://www.alma-valley.ru/almax.html
- `official-reserve-example`: https://www.alma-valley.ru/R_Chard.html
- `official-gravity-example`: https://www.alma-valley.ru/G_M_PN_KS.html
- `official-tba-example`: https://www.alma-valley.ru/o3_TBA_S.html
- `official-alma-x-cabernet-saperavi`: https://www.alma-valley.ru/X_CS_S.html
- `official-muscat-appassimento`: https://www.alma-valley.ru/o3_App_M.html

## Mapping decisions and limits

- The official Alma X white page names Pinot Blanc and Riesling, but its image also names Pinot Gris. The white candidate is excluded because the snapshot already contains Gravity white with that trio. No equivalence is asserted.
- The local Pinot Noir sparkling bottle label reads BLANC DE NOIR BRUT NATURE. The original catalog name stays unchanged.
- The snapshot attributes both Locantita cards to Alma Valley. The current official collection index and other-wines page do not verify this producer attribution or a current Alma Valley collection. Both cards remain in a neutral group. The group description states this limit.
- Reserve Merlot and Reserve Chardonnay have multiple snapshot cards. They remain separate products without aliases.
- Technology examples apply only to the named wine. They are not copied as fixed aging durations for all reserve or Gravity wines.
- Sweet wines and sparkling wines have no numeric price comparison with still wines.

- The varietal collection and Sun, Air, Grapes use one rank-1 tier named core. The two previous tiers had equal ranks. No evidence established a price order between them. The merge changes navigation only and does not introduce a new price rank.

## Official additions and absence checks

### official-alma-x-cabernet-saperavi

- Product page: https://www.alma-valley.ru/X_CS_S.html
- Exact bottle image: https://www.alma-valley.ru/img/catalog/all/X_CS_S.png
- Absence evidence: No Alma X name or slug occurs in the full snapshot. No Alma Valley card names a Cabernet Sauvignon-Saperavi blend. Existing Gravity red cards name Pinot Noir-Merlot-Cabernet Sauvignon. Locantita red names Merlot-Cabernet Franc. The general grape list in Locantita does not establish identity with this named Alma X product.
- The producer subset and the full 2,103-row catalog were searched. No available snapshot card is replaced.

### official-muscat-appassimento

- Product page: https://www.alma-valley.ru/o3_App_M.html
- Exact bottle image: https://www.alma-valley.ru/img/catalog/all/o3_App_M.png
- Absence evidence: No Alma Valley snapshot card names Muscat or Appassimento. The existing TBA Sauvignon has another grape and production method. Appassimento cards from other producers are not equivalent.
- The producer subset and the full 2,103-row catalog were searched. No available snapshot card is replaced.

## Collection coverage

| Group | Snapshot cards | Official additions |
| --- | ---: | ---: |
| Резервные вина | 11 | 0 |
| Альма Гравити | 3 | 0 |
| Сортовые вина | 16 | 0 |
| Солнце, воздух, виноград | 5 | 0 |
| Игристые вина | 1 | 0 |
| Айс Вайн, ТБА, Аппассименто | 1 | 1 |
| Альма Икс | 0 | 1 |
| Locantita | 2 | 0 |

## Image limits

Every catalog row has its original local WebP image.

All official addition images were visually checked against their product labels.
