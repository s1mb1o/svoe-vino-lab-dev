# Мысхако map sources

Prepared on 2026-10-16. The map contains 92 distinct catalog records and 5 verified official additions.

## Scope

The input is `/Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace/svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl`. The exact producer value is `Мысхако`. The snapshot date is 2026-09-17.
Each catalog slug is one node. Similar names, different vintages, and different package records remain separate. No alias is inferred.
Catalog descriptions and grape lists are preserved. Category and style do not use a numeric slug suffix. A catalog color does not prove a production method.
The official additions are a verified selection. This map does not claim full coverage of the current official range. Current stock is not established.
The release status `catalog` means that the product has catalog evidence. It does not mean that the product is available for purchase.

## Positioning

The tier order is editorial. It is relative within this producer. It is not a quality ranking or a cross-producer price comparison. All numeric prices are null.
Official premium statements support the relevant group descriptions. Other tier assignments are editorial navigation choices. Groups with unclear collection or price evidence use the neutral tier.

## Catalog and image checks

The builder selects the exact producer field. It preserves every selected slug. Each local WebP is copied without re-encoding. The crosswalk records its SHA-256 hash.
Official bottle images use only the exact product page or product PDF. The asset preparation uses proportional resizing and WebP encoding. It does not replace the bottle or edit the label.

## Grouping notes

- Generic varietal bottle labels were inspected. They do not prove a specific collection or a relative price. These records use the neutral tier.
- Reserve and Grand Reserve tiers are editorial navigation choices based on named catalog collections. A current official price hierarchy was not established. The map does not claim official premium certification for these groups.
- The snapshot contains category anomalies. Orange from White and Quintessence Reserve Riesling have unexpected catalog colors. These input values are preserved and are not silently corrected.
- Some grape fields list only one grape while the product name names a blend. The saved grape field is preserved. The map does not invent proportions.
- Current Craft and Noble Age pages establish the five gray products. These products are not aliases of catalog varietal wines.
- The catalog contains distinct still and sparkling products in several families. A group method remains unspecified when the family uses multiple methods.

## Official sources

- `mys-official`: [Мысхако: официальный каталог тихих вин](https://myskhako.ru/catalog/vina-tihie/).
- `mys-sparkling`: [Мысхако: официальный каталог игристых вин](https://myskhako.ru/catalog/vina-igristye/).
- `mys-215`: [Крафт. Совиньон Блан — Шардоне](https://myskhako.ru/catalog/vina-tihie/vina-tihie_215.html).
- `mys-216`: [Крафт. Семильон — Русан](https://myskhako.ru/catalog/vina-tihie/vina-tihie_216.html).
- `mys-217`: [Крафт. Каберне Фран — Каладок](https://myskhako.ru/catalog/vina-tihie/vina-tihie_217.html).
- `mys-218`: [Крафт. Достойный — Саперави](https://myskhako.ru/catalog/vina-tihie/vina-tihie_218.html).
- `mys-200`: [Noble Age. 6 урожаев. Шардоне](https://myskhako.ru/catalog/vina-tihie/vina-tihie_200.html).

## Gray product checks

Every check compared the official product with all 92 rows for the exact producer. The check examined names, descriptions, grapes, and relevant bottle images. A missing match only applies to the saved snapshot.

### Крафт. Совиньон Блан — Шардоне

- Product: `official-mys-215`.
- Evidence: [Крафт. Совиньон Блан — Шардоне](https://myskhako.ru/catalog/vina-tihie/vina-tihie_215.html).
- Absence basis: No Craft card occurs among the 92 records. The snapshot Cuvee blends do not identify this 50/50 Craft product. The official 2025 Craft label is distinct.
- Image: https://myskhako.ru/netcat_files/14/5/h_de299950c974a84fdcc34f96e86df45c
- Preparation: Proportional resize to at most 480 pixels. WebP encoding. No retouching.

### Крафт. Семильон — Русан

- Product: `official-mys-216`.
- Evidence: [Крафт. Семильон — Русан](https://myskhako.ru/catalog/vina-tihie/vina-tihie_216.html).
- Absence basis: No Craft card or Roussanne product occurs among the 92 records. Semillon-Aligote Reserve and Sauvignon-Semillon Cuvee have different blends and collections.
- Image: https://myskhako.ru/netcat_files/14/5/h_4be6cf8bde0adabca767c611895876d3
- Preparation: Proportional resize to at most 480 pixels. WebP encoding. No retouching.

### Крафт. Каберне Фран — Каладок

- Product: `official-mys-217`.
- Evidence: [Крафт. Каберне Фран — Каладок](https://myskhako.ru/catalog/vina-tihie/vina-tihie_217.html).
- Absence basis: No Craft card or Caladoc product occurs among the 92 records. The standalone Cabernet Franc cards do not establish equivalence with this blend.
- Image: https://myskhako.ru/netcat_files/14/5/h_a8629645a081d984497edcb3880a7760
- Preparation: Proportional resize to at most 480 pixels. WebP encoding. No retouching.

### Крафт. Достойный — Саперави

- Product: `official-mys-218`.
- Evidence: [Крафт. Достойный — Саперави](https://myskhako.ru/catalog/vina-tihie/vina-tihie_218.html).
- Absence basis: No Craft card or Dostoynyi-Saperavi blend occurs among the 92 records. The named varietal blend and official Craft label confirm a distinct product.
- Image: https://myskhako.ru/netcat_files/14/5/h_e87a9b3f30eb706586432b8d526f2a21
- Preparation: Proportional resize to at most 480 pixels. WebP encoding. No retouching.

### Noble Age. 6 урожаев. Шардоне

- Product: `official-mys-200`.
- Evidence: [Noble Age. 6 урожаев. Шардоне](https://myskhako.ru/catalog/vina-tihie/vina-tihie_200.html).
- Absence basis: No Noble Age or six-harvest card occurs among the 92 records. The ordinary Chardonnay and Grand Reserve bottle labels were inspected and do not match this series.
- Image: https://myskhako.ru/netcat_files/14/5/h_adfb38eac00b5f43a61decad7402feff
- Preparation: Proportional resize to at most 480 pixels. WebP encoding. No retouching.


## Visible conflict handling

The orange wine card has a red category and a gold color. Its map style is «Оранжевое вино».
The Riesling Reserve card has a red category and a straw-gold color. Its map style is «Стиль уточняется».
Both products show «Данные источника расходятся».
The current official orange wine page describes a different blend. The map does not replace the saved grapes or description with that release.

## Visible image frames, 2026-10-16

The producer JSON records measured frame geometry for 97 images.
The frame uses the source alpha outline and a small transparent margin.
The frame changes image presentation only. Source image bytes and product facts are unchanged.
The renderer uses the frame for group previews, product nodes and product details.
Read [the sizing contract](../../product-image-sizing.md) for the measurement method.
