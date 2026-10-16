# Собер Баш: source evidence

Date: 2026-10-16.

Include all 37 exact catalog cards for `Собер Баш`.
Use the independent catalog baseline and crosswalk in this directory.
Preserve catalog names, descriptions, grapes, and separate identities.
Do not infer vintage, alcohol, or price from slug suffixes.
Do not treat this map as the complete live assortment.

## Collections and positioning

Ranks are editorial navigation. Numeric prices are not available.
Rank 0 does not assert price equivalence with other collections.
The official collection structure can differ from historical labels.
Keep the historical package image when the snapshot supplies that image.

- `reserve`: [Резервные вина](https://soberbashvino.ru/wine/kollekcija-rezervnoe/). Rank 3. Catalog row indices: 0, 15, 19, 24, 26, 29.
- `amphora`: [Грани · Амфора](https://soberbashvino.ru/wine/kollekcija-rezervnoe/). Rank 2. Catalog row indices: 12, 18, 25, 28.
- `grani`: [Грани](https://soberbashvino.ru/wine/kollekcija-grani/). Rank 2. Catalog row indices: 9, 10, 11, 2, 13, 27.
- `classic`: [Классика](https://soberbashvino.ru/wine/kollekcija-klassika/). Rank 1. Catalog row indices: 1, 14, 16, 17, 20, 21, 22, 23.
- `two-valleys`: [Две долины](https://soberbashvino.ru/wine/dve-dolini/). Rank 1. Catalog row indices: 3, 4, 5, 6, 7, 8.
- `sober-head`: [Трезвая голова](https://soberbashvino.ru/wine/kollekcija-trezvaja-golova/). Rank 0. Catalog row indices: 30, 31, 32, 33, 34, 35, 36.

## Images

Read the crosswalk for every source URL, input hash, and output hash.
Crop transparent margins. Downsize to at most 720 px. Add transparent padding.
Compute image.frame from alpha values of at least 128 after WebP encoding.
Inspect every image on light and dark surfaces.
Do not use generated lettering as product evidence.

## Additional products

Include 1 verified official additions with null wine_slug.
Read official_additions in crosswalk.json for each absence check.
