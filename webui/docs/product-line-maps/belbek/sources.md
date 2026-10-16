# Бельбек: source evidence

Date: 2026-10-16.

Include all 39 exact catalog cards for `Бельбек`.
Use the independent catalog baseline and crosswalk in this directory.
Preserve catalog names, descriptions, grapes, and separate identities.
Do not infer vintage, alcohol, or price from slug suffixes.
Do not treat this map as the complete live assortment.

## Collections and positioning

Ranks are editorial navigation. Numeric prices are not available.
Rank 0 does not assert price equivalence with other collections.
The official collection structure can differ from historical labels.
Keep the historical package image when the snapshot supplies that image.

- `reserve`: [Резерв и Баррик](https://belbekwine.com/red-wines/). Rank 3. Catalog row indices: 9, 10, 13, 25, 29, 34, 35, 36.
- `red`: [Красные сортовые и купажи](https://belbekwine.com/red-wines/). Rank 2. Catalog row indices: 2, 3, 4, 6, 7, 12, 14, 16, 17, 19, 20, 23, 24, 32, 33.
- `white`: [Белые сортовые](https://belbekwine.com/white-wines/). Rank 2. Catalog row indices: 0, 5, 8, 18, 21, 28, 30, 37.
- `rose`: [Розовые вина](https://belbekwine.com/rose-wines/). Rank 0. Catalog row indices: 11, 26, 31.
- `orange`: [Мускат Оранж](https://belbekwine.com/orange-wines/). Rank 0. Catalog row indices: 22.
- `sweet`: [Фиолент и Поздний сбор](https://belbekwine.com/white-wines/). Rank 0. Catalog row indices: 1, 27.
- `zakat`: [Закат](https://belbekwine.com/red-wines/). Rank 0. Catalog row indices: 38.
- `unresolved`: [Карточка с противоречием](https://belbekwine.com/). Rank 0. Catalog row indices: 15.

## Images

Read the crosswalk for every source URL, input hash, and output hash.
Crop transparent margins. Downsize to at most 720 px. Add transparent padding.
Compute image.frame from alpha values of at least 128 after WebP encoding.
Inspect every image on light and dark surfaces.
Do not use generated lettering as product evidence.

## Additional products

Include 1 verified official additions with null wine_slug.
Read official_additions in crosswalk.json for each absence check.

The snapshot card Белое сухое contradicts its red color and Cabernet metadata.
Keep this card in the unresolved group. Do not resolve the conflict by guessing.
