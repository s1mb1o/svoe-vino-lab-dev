# ESSE: source evidence

Date: 2026-10-16.

Include all 53 exact catalog cards for `ESSE`.
Use the independent catalog baseline and crosswalk in this directory.
Preserve catalog names, descriptions, grapes, and separate identities.
Do not infer vintage, alcohol, or price from slug suffixes.
Do not treat this map as the complete live assortment.

## Collections and positioning

Ranks are editorial navigation. Numeric prices are not available.
Rank 0 does not assert price equivalence with other collections.
The official collection structure can differ from historical labels.
Keep the historical package image when the snapshot supplies that image.

- `kacha-valley`: [KACHA VALLEY](https://essewine.com/wines). Rank 3. Catalog row indices: 4, 6, 7, 26, 27, 32, 42, 45, 46, 49.
- `classic`: [ESSE classic](https://essewine.com/wines). Rank 2. Catalog row indices: 11, 12, 13, 14, 16, 19, 36, 39, 43, 44, 47, 51, 52.
- `stones`: [ESSE stones / Отборное](https://essewine.com/wines). Rank 1. Catalog row indices: 15, 20, 21, 23, 37, 48, 50.
- `unplugged`: [Unplugged · авторские стили](https://essewine.com/wines). Rank 0. Catalog row indices: 17, 18, 24, 28, 29, 30, 31, 35, 38.
- `natural-sweet`: [Природно полусладкие](https://essewine.com/wines). Rank 0. Catalog row indices: 33, 34.
- `sparkling`: [ESSE sparkling](https://essewine.com/wines). Rank 0. Catalog row indices: 0, 1, 2, 3, 5, 8, 9, 10, 22, 25, 40, 41.

## Images

Read the crosswalk for every source URL, input hash, and output hash.
Crop transparent margins. Downsize to at most 720 px. Add transparent padding.
Compute image.frame from alpha values of at least 128 after WebP encoding.
Inspect every image on light and dark surfaces.
Do not use generated lettering as product evidence.

## Additional products

Include 1 verified official additions with null wine_slug.
Read official_additions in crosswalk.json for each absence check.

The snapshot has one separate Сатера producer card.
This baseline contains the 53 ESSE producer cards.
Do not use a broad Сатера alias to claim that the separate card is covered.
