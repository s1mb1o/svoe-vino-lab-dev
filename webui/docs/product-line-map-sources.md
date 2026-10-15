# Product line map sources

Date: 2026-10-15.

## Scope

The Abrau-Durso map reproduces the six prepared sheets from 2026-09-20.
The source catalog snapshot is `official-2026-09-17`.
The map covers sparkling wines and the drink packages on those sheets.
The map does not cover all still wines from the producer.
This work did not check the live catalog.
A missing `wine_slug` means that the supplied snapshot has no verified match.
It does not mean that the producer has stopped production.
It does not mean that the product is out of stock.

## Source paths

The source workspace is `/Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace`.
The sheet directory is `<workspace>/experiments/abrau-durso-lineups-2026-09-20`.
`render_lineups.py` defines all sheet products and image names.
`manifest.json` records source URLs and asset corrections.
`official-abrau-catalog-2025.pdf` is the recorded official catalog.
Pages 15 and 16 provide the package evidence.
`official-abrau-catalog-2025-assets/selected/` contains prepared official package images.
The catalog data is `<workspace>/svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl`.
The catalog image directory is `<workspace>/svoe-wino-hackaton/dataset/official-2026-09-17/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads/`.

The source registry in `shared/data/product-line-maps/abrau-durso.json` preserves the recorded public URLs.
The prepared sheet source has an empty URL because it is a local artifact.
The catalog source URL points to the source portal.
That URL is not a public download URL for the dated local snapshot.

## Data contract

Each producer has one JSON file.
`group_id` is the authoritative product membership relation.
The renderer derives graph containment edges from this relation.
The JSON does not duplicate these edges.
`wine_slug` is nullable.
`wine_slug_aliases` maps other verified catalog slugs to the same product node.
Catalog availability and release status are separate fields.
`release_status` uses `catalog`, `archive`, or `limited`.
The `catalog` value identifies recorded catalog evidence.
It does not assert current retail availability.
Every product has `price: null`.
Unknown methods use `Не указан в источнике`.
Unknown styles use `Стиль не уточнён`.
Unknown grape lists use an empty array.
The UI category for Abrau Collection remains `Категория не уточнена`.
The source sheet alone does not establish its exact beverage category.

## Coverage

`product-line-map-crosswalk.json` maps all 54 sheet entries to the 52 product IDs.
The two repeated entries are the white Fizz variants.
The unit test requires exact product coverage and six source sheets.

The graph contains 52 product nodes in 14 groups.
It has 32 canonical catalog slugs and 3 additional slug aliases.
It has 20 products without a verified catalog slug.

| Group | Products | Canonical slugs | Missing slugs |
| --- | ---: | ---: | ---: |
| `cuvee-alexander-ii` | 2 | 1 | 1 |
| `imperial` | 4 | 4 | 0 |
| `brut-dor` | 4 | 4 | 0 |
| `victor-dravigny` | 8 | 7 | 1 |
| `reserve` | 2 | 2 | 0 |
| `imperatorskoe` | 3 | 3 | 0 |
| `udelnoe-vedomstvo` | 2 | 2 | 0 |
| `russian-sparkling` | 8 | 6 | 2 |
| `spumante` | 3 | 1 | 2 |
| `fizz` | 4 | 2 | 2 |
| `light` | 2 | 0 | 2 |
| `fiori` | 4 | 0 | 4 |
| `collection` | 2 | 0 | 2 |
| `light-zero` | 4 | 0 | 4 |

The three main sparkling sheets contain 30 products.
The missing-products sheet adds 6 products.
The drink sheet contains 16 package variants.
Its manifest incorrectly states 14 products.
The renderer and the PNG both show 16 products.
The two white Fizz variants also appear on the separate Fizz sheet.
The graph includes each of these variants once.

## Identity rules and corrections

The asset filename provides an exact join to `catalog.upload_file` for 29 primary wine products.
Victor Dravigny Brut uses the explicit canonical slug below.
Its catalog image is a montage.
The map uses the recorded official single-bottle image instead.
The two white Fizz products use explicit catalog slugs and the official can images.
The source catalog supplies their descriptions and grapes.
The graph preserves kosher products as separate nodes.
The graph preserves different package formats as separate nodes.
The graph preserves both white Fiori packages.
The Fiori captions describe their label colors.
They do not infer flavors from those colors.
The graph preserves both Udelnoye Vedomstvo archive packages.
Zero Dosage 2020 is a limited release documented in the annual report for 2024.
It is not listed as a current product in the official 2025 catalog.
The standard Russian Sparkling Brut has no catalog match.
The kosher Brut does not replace that standard product.
Reserve Brut Rosé has a source catalog category error.
Its source name and color identify a rosé wine.
The map uses `Розовое брют` for this product.
Fizz is an `Игристое вино` in the separate sheet and on the package labels.
The map does not classify all products on the drink sheet as one legal beverage category.
The graph does not infer alcohol content from numeric slug suffixes.
The graph does not add unverified tasting notes for products without catalog descriptions.

| Alias | Canonical slug |
| --- | --- |
| `abrau-dyurso-victor-dravigny-bryut` | `abrau-dyurso-victor-dravigny-brut-shardone-beloe-bryut-12` |
| `abrau-dyurso-brut-dor-blanc-de-blancs-shardone-beloe-bryut-12` | `abrau-dyurso-brut-dor-blanc-de-blancs-shardone-beloe-bryut-125` |
| `abrau-dyurso-brut-dor-blanc-de-noirs-pino-nuar-beloe-bryut-115` | `abrau-dyurso-brut-dor-blanc-de-noirs-pino-nuar-beloe-bryut-125` |

## Positioning

The sources do not provide numeric retail prices.
The map uses relative editorial positioning.
The premium and accessible labels follow the prepared sheet headings.
The intermediate price levels are editorial assignments.
They are not measured price bands.
The source sheets identify the classic method for Victor Dravigny.
The source sheets identify the Charmat method for Reserve, Imperatorskoe, and Udelnoye Vedomstvo.
The other method fields remain unknown in this data file.

Premium groups have rank 4.
Victor Dravigny has rank 3.
Reserve, Imperatorskoe, and Udelnoye Vedomstvo have rank 2.
Russian Sparkling and Spumante have rank 1.
Fizz, Light, Fiori, Collection, and Light Zero use the neutral `formats` tier.
Its rank 0 identifies a separate display lane.
Rank 0 does not mean the lowest price or the lowest quality.
The format tier uses `Не сопоставляется` as its price label.
No rank is a quality score.
The UI disclaimer states these limits.

## Asset preparation

The graph uses 52 local WebP files.
The files retain the source alpha channel.
Preparation removes transparent outer margins.
Preparation limits height to 480 pixels.
Preparation does not enlarge a source image.
WebP quality is 88.
The WebP method setting is 6.
Preparation does not generate or repaint product labels.
The browser does not need a remote image request.

The following table maps every output asset to its recorded source.
A source name without a directory belongs to the catalog image directory.
A source name with a directory belongs to the sheet directory.

| Output file | Source image | Source ID | Output pixels |
| --- | --- | --- | --- |
| `cuvee-alexander-ii-magnum.webp` | `abrau_dyurso_aleksandr_ii_magnum_shardone_beloe_bryut_125_256840c1d1.webp` | `svoe-vino-2026-09-17` | 158 × 480 |
| `imperial-brut-lart-nouveau.webp` | `abrau_dyurso_imperial_brut_lart_nouveau_shardone_beloe_bryut_105_71076b0053.webp` | `svoe-vino-2026-09-17` | 154 × 480 |
| `imperial-brut-vintage.webp` | `abrau_dyurso_imperial_brut_vintage_shardone_beloe_bryut_12_8f6dbe7a71.webp` | `svoe-vino-2026-09-17` | 151 × 480 |
| `imperial-brut-rose.webp` | `abrau_dyurso_imperial_brut_rose_pino_nuar_rozovoe_bryut_12_3eafe20e40.webp` | `svoe-vino-2026-09-17` | 153 × 480 |
| `imperial-cuvee-rose.webp` | `abrau_dyurso_imperial_kyuve_pino_nuar_igristoe_bryut_rozovoe_125_99fe198335.webp` | `svoe-vino-2026-09-17` | 150 × 480 |
| `brut-dor-blanc-de-blancs.webp` | `abrau_dyurso_brut_dor_blanc_de_blancs_shardone_beloe_bryut_125_cf97076f41.webp` | `svoe-vino-2026-09-17` | 152 × 480 |
| `brut-dor-blanc-de-noirs.webp` | `abrau_dyurso_brut_dor_blanc_de_noirs_pino_nuar_beloe_bryut_125_2d16522a48.webp` | `svoe-vino-2026-09-17` | 152 × 480 |
| `brut-dor-riesling.webp` | `abrau_dyurso_brut_dor_riesling_risling_beloe_bryut_12_45b9c81ea5.webp` | `svoe-vino-2026-09-17` | 152 × 480 |
| `brut-dor-rose.webp` | `abrau_dyurso_brut_dor_rose_pino_nuar_rozovoe_bryut_12_8b5bd155e6.webp` | `svoe-vino-2026-09-17` | 152 × 480 |
| `victor-dravigny-brut.webp` | `official-abrau-catalog-2025-assets/selected/victor-dravigny-brut.png` | `official-catalog-2025` | 132 × 480 |
| `victor-dravigny-extra-brut.webp` | `abrau_dyurso_victor_dravigny_extra_brut_shardone_beloe_bryut_125_86dc223df3.webp` | `svoe-vino-2026-09-17` | 130 × 480 |
| `victor-dravigny-brut-rose.webp` | `abrau_dyurso_victor_dravigny_brut_rose_pino_nuar_rozovoe_bryut_12_c7199512eb.webp` | `svoe-vino-2026-09-17` | 129 × 480 |
| `victor-dravigny-semi-dry.webp` | `abrau_dyurso_victor_dravigny_polusuhoe_pino_blan_beloe_12_7b6de7aca6.webp` | `svoe-vino-2026-09-17` | 130 × 480 |
| `victor-dravigny-semi-sweet.webp` | `abrau_dyurso_victor_dravigny_polusladkoe_sovinon_blan_beloe_12_ec087df76c.webp` | `svoe-vino-2026-09-17` | 130 × 480 |
| `victor-dravigny-red-semi-sweet.webp` | `abrau_dyurso_victor_dravigny_krasnoe_polusladkoe_kaberne_sovinon_125_f0e4d2775c.webp` | `svoe-vino-2026-09-17` | 129 × 480 |
| `victor-dravigny-kosher-brut.webp` | `abrau_dyurso_victor_dravigny_koshernoe_bryut_shardone_beloe_125_662e4e2b51.webp` | `svoe-vino-2026-09-17` | 129 × 480 |
| `reserve-brut.webp` | `abrau_dyurso_abrau_durso_reserve_brut_shardone_beloe_bryut_115_c2d789063b.webp` | `svoe-vino-2026-09-17` | 135 × 480 |
| `reserve-brut-rose.webp` | `abrau_dyurso_abrau_durso_brut_rose_reserve_pino_nuar_beloe_bryut_12_bb364de705.webp` | `svoe-vino-2026-09-17` | 136 × 480 |
| `imperatorskoe-brut.webp` | `abrau_dyurso_imperatorskoe_bryut_shardone_beloe_12_d6c7ebb073.webp` | `svoe-vino-2026-09-17` | 136 × 480 |
| `imperatorskoe-semi-dry.webp` | `abrau_dyurso_imperatorskoe_polusuhoe_shardone_beloe_12_51385573f2.webp` | `svoe-vino-2026-09-17` | 136 × 480 |
| `imperatorskoe-semi-sweet.webp` | `abrau_dyurso_imperatorskoe_polusladkoe_shardone_beloe_12_956aaee80d.webp` | `svoe-vino-2026-09-17` | 136 × 480 |
| `udelnoe-vedomstvo-brut.webp` | `Abrau_Dyurso_Udelnoe_vedomtsvo_bryut_80a96f319c.webp` | `svoe-vino-2026-09-17` | 137 × 480 |
| `udelnoe-vedomstvo-semi-sweet.webp` | `Abrau_Dyurso_Udelnoe_Vedomstvo_Imperatorskoe_beloe_polusladkoe_fac98a6538.webp` | `svoe-vino-2026-09-17` | 136 × 480 |
| `russian-sparkling-semi-dry-white.webp` | `abrau_dyurso_russkoe_igristoe_polusuhoe_shardone_beloe_12_1dd99a0a33.webp` | `svoe-vino-2026-09-17` | 135 × 480 |
| `russian-sparkling-semi-sweet-white.webp` | `abrau_dyurso_russkoe_igristoe_polusladkoe_shardone_beloe_12_a8752d67f6.webp` | `svoe-vino-2026-09-17` | 135 × 480 |
| `russian-sparkling-semi-dry-rose.webp` | `abrau_dyurso_russkoe_igristoe_polusuhoe_rozovoe_pino_nuar_12_dafb6d988e.webp` | `svoe-vino-2026-09-17` | 135 × 480 |
| `russian-sparkling-semi-sweet-red.webp` | `abrau_dyurso_russkoe_igristoe_polusladkoe_krasnoe_kaberne_sovinon_12_d7c8d1c042.webp` | `svoe-vino-2026-09-17` | 135 × 480 |
| `russian-sparkling-kosher-brut.webp` | `abrau_dyurso_russkoe_igristoe_koshernoe_bryut_shardone_beloe_13_8b9ee7f9fe.webp` | `svoe-vino-2026-09-17` | 126 × 480 |
| `russian-sparkling-kosher-semi-sweet.webp` | `abrau_dyurso_russkoe_igristoe_koshernoe_polusladkoe_shardone_beloe_12_cce09fd580.webp` | `svoe-vino-2026-09-17` | 125 × 480 |
| `spumante-brut-rose.webp` | `abrau_dyurso_spumante_bryut_roze_shardone_igristoe_bryut_rozovoe_12_36f26aa26f.webp` | `svoe-vino-2026-09-17` | 142 × 480 |
| `cuvee-alexander-ii-gift-box.webp` | `official-abrau-catalog-2025-assets/selected/cuvee-alexander-ii-075-box.png` | `cuvee-box-image` | 311 × 480 |
| `victor-dravigny-zero-dosage.webp` | `official-abrau-catalog-2025-assets/selected/victor-dravigny-zero-dosage.png` | `zero-dosage-release-image` | 148 × 480 |
| `russian-sparkling-brut-white.webp` | `official-abrau-catalog-2025-assets/selected/russian-sparkling-brut.png` | `russian-brut-image` | 134 × 480 |
| `russian-sparkling-dry-white.webp` | `official-abrau-catalog-2025-assets/selected/russian-sparkling-dry.png` | `official-catalog-2025` | 137 × 480 |
| `spumante-brut-white.webp` | `official-abrau-catalog-2025-assets/selected/abrau-spumante-brut.png` | `spumante-brut-image` | 133 × 454 |
| `spumante-semi-dry-white.webp` | `official-abrau-catalog-2025-assets/selected/abrau-spumante-semi-dry.png` | `spumante-semi-dry-image` | 144 × 480 |
| `abrau-light-purple.webp` | `official-abrau-catalog-2025-assets/selected/abrau-light-purple.png` | `official-catalog-2025` | 142 × 480 |
| `abrau-light-pink.webp` | `official-abrau-catalog-2025-assets/selected/abrau-light-pink.png` | `official-catalog-2025` | 142 × 480 |
| `abrau-fiori-red.webp` | `official-abrau-catalog-2025-assets/selected/abrau-fiori-red.png` | `official-catalog-2025` | 144 × 480 |
| `abrau-fiori-white-green.webp` | `official-abrau-catalog-2025-assets/selected/abrau-fiori-white-green.png` | `official-catalog-2025` | 140 × 480 |
| `abrau-fiori-rose.webp` | `official-abrau-catalog-2025-assets/selected/abrau-fiori-rose.png` | `official-catalog-2025` | 140 × 480 |
| `abrau-fiori-white-purple.webp` | `official-abrau-catalog-2025-assets/selected/abrau-fiori-white-purple.png` | `official-catalog-2025` | 139 × 480 |
| `abrau-collection-white.webp` | `official-abrau-catalog-2025-assets/selected/abrau-collection-white.png` | `official-catalog-2025` | 137 × 341 |
| `abrau-collection-rose.webp` | `official-abrau-catalog-2025-assets/selected/abrau-collection-rose.png` | `official-catalog-2025` | 136 × 339 |
| `abrau-fizz-brut-white.webp` | `official-abrau-catalog-2025-assets/selected/abrau-fizz-brut-white.png` | `official-catalog-2025` | 132 × 340 |
| `abrau-fizz-brut-rose.webp` | `official-abrau-catalog-2025-assets/selected/abrau-fizz-brut-rose.png` | `official-catalog-2025` | 132 × 340 |
| `abrau-fizz-semi-sweet-white.webp` | `official-abrau-catalog-2025-assets/selected/abrau-fizz-semi-sweet-white.png` | `official-catalog-2025` | 131 × 338 |
| `abrau-fizz-semi-sweet-rose.webp` | `official-abrau-catalog-2025-assets/selected/abrau-fizz-semi-sweet-rose.png` | `official-catalog-2025` | 131 × 338 |
| `abrau-light-zero-purple-bottle.webp` | `official-abrau-catalog-2025-assets/selected/abrau-light-zero-purple-bottle.png` | `official-catalog-2025` | 142 × 480 |
| `abrau-light-zero-pink-bottle.webp` | `official-abrau-catalog-2025-assets/selected/abrau-light-zero-pink-bottle.png` | `official-catalog-2025` | 142 × 480 |
| `abrau-light-zero-purple-can.webp` | `official-abrau-catalog-2025-assets/selected/abrau-light-zero-purple-can.png` | `official-catalog-2025` | 119 × 287 |
| `abrau-light-zero-pink-can.webp` | `official-abrau-catalog-2025-assets/selected/abrau-light-zero-pink-can.png` | `official-catalog-2025` | 117 × 288 |

## Дербент Вино extension, 2026-10-16

Read [derbent-vino sources](product-line-maps/derbent-vino/sources.md).
The map includes 63 snapshot cards and 4 verified additions in 8 groups.
It does not claim complete live assortment coverage.

## Золотая Балка extension, 2026-10-16

Read [zolotaya-balka sources](product-line-maps/zolotaya-balka/sources.md).
The map includes 41 snapshot cards and 2 verified additions in 10 groups.
It does not claim complete live assortment coverage.

## Alma Valley extension, 2026-10-16

Read [alma-valley sources](product-line-maps/alma-valley/sources.md).
The map includes 39 snapshot cards and 2 verified additions in 8 groups.
It does not claim complete live assortment coverage.

## Инкерман extension, 2026-10-16

Read [inkerman sources](product-line-maps/inkerman/sources.md).
The map includes 15 snapshot cards and 2 verified additions in 6 groups.
It does not claim complete live assortment coverage.

## Массандра extension, 2026-10-16

Read [massandra sources](product-line-maps/massandra/sources.md).
The map includes 44 snapshot cards and 2 verified additions in 9 groups.
It does not claim complete live assortment coverage.

## Ведерниковъ extension, 2026-10-16

Read [vedernikov sources](product-line-maps/vedernikov/sources.md).
The map includes 43 snapshot cards and 2 verified additions in 10 groups.
It does not claim complete live assortment coverage.
