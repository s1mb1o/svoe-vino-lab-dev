# Новый Свет: source evidence

Date: 2026-10-16.

Include all 44 exact catalog cards for `Новый Свет. Дом шампанских вин`.
Use the independent catalog baseline and crosswalk in this directory.
Preserve catalog names, descriptions, grapes, and separate identities.
Do not infer vintage, alcohol, or price from slug suffixes.
Do not treat this map as the complete live assortment.

## Collections and positioning

Ranks are editorial navigation. Numeric prices are not available.
Rank 0 does not assert price equivalence with other collections.
The official collection structure can differ from historical labels.
Keep the historical package image when the snapshot supplies that image.

- `prestige`: [Кюве Де Престиж](https://nsvet-crimea.ru/shampain/kyuve-de-prestizh/). Rank 3. Catalog row indices: 7, 10, 12, 13, 26, 32, 34.
- `limited`: [Лимитированные и особые кюве](https://nsvet-crimea.ru/shampain/). Rank 3. Catalog row indices: 1, 6, 15, 22, 27, 28, 29, 31, 33, 0, 21, 41, 42.
- `collection`: [Коллекционное](https://nsvet-crimea.ru/shampain/rossiyskoe-shampanskoe-kollektsionnoe/). Rank 2. Catalog row indices: 5, 9, 11, 30, 35, 36, 37, 38.
- `aged`: [Выдержанное](https://nsvet-crimea.ru/shampain/rossiyskoe-shampanskoe-vyderzhannoe/). Rank 1. Catalog row indices: 2, 3, 4, 8, 14, 16, 17, 18, 19, 20, 23, 24, 25, 39, 40, 43.
- `crown`: [Коронационное](https://nsvet-crimea.ru/shampain/koronatsionnoe/). Rank 4. Catalog row indices: .

## Images

Read the crosswalk for every source URL, input hash, and output hash.
Crop transparent margins. Downsize to at most 720 px. Add transparent padding.
Compute image.frame from alpha values of at least 128 after WebP encoding.
Inspect every image on light and dark surfaces.
Do not use generated lettering as product evidence.

## Additional products

Include 1 verified official additions with null wine_slug.
Read official_additions in crosswalk.json for each absence check.
