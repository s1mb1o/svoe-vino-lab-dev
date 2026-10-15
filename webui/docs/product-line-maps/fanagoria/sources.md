# Фанагория map sources

Prepared on 2026-10-16. The map contains 102 distinct catalog records and 6 verified official additions.

## Scope

The input is `/Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace/svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl`. The exact producer value is `Фанагория`. The snapshot date is 2026-09-17.
Each catalog slug is one node. Similar names, different vintages, and different package records remain separate. No alias is inferred.
Catalog descriptions and grape lists are preserved. Category and style do not use a numeric slug suffix. A catalog color does not prove a production method.
The official additions are a verified selection. This map does not claim full coverage of the current official range. Current stock is not established.
The release status `catalog` means that the product has catalog evidence. It does not mean that the product is available for purchase.

## Positioning

The tier order is editorial. It is relative within this producer. It is not a quality ranking or a cross-producer price comparison. All numeric prices are null.
Official premium statements support the relevant group descriptions. Other tier assignments are editorial navigation choices. Groups with unclear collection or price evidence use the neutral tier.

## Catalog and image checks

The builder selects the exact producer field. It preserves every selected slug. The initial import copied each local WebP without re-encoding. The crosswalk records current SHA-256 hashes and later transformations.
Official bottle images use only the exact product page or product PDF. The initial asset preparation used proportional resizing and WebP encoding. Later background extraction is documented below.

## Grouping notes

- The official 100/101 Shades, Cru Lermont, Sur Lie, and Primum Alveus pages explicitly describe premium collections. The map keeps the relative order editorial.
- Brule includes different methods. The group does not claim one method for every product.
- Generic sparkling names remain separate. The map does not infer aliases from similar descriptions or grape names.
- Alta Qortis, SAQRA, and the generic rose card retain neutral price placement. The saved descriptions remain unchanged.
- The two failed exploratory collection URL requests were not used as sources.

## Official sources

- `fan-official`: [Фанагория: официальный ассортимент](https://www.fanagoria.ru/assortiment).
- `fan-group-cru-lermont`: [Фанагория: Cru Lermont](https://www.fanagoria.ru/collection/cru-lermont).
- `fan-group-primum-alveus`: [Фанагория: Primum Alveus](https://www.fanagoria.ru/collection/primum-alveus).
- `fan-group-100-ottenkov`: [Фанагория: 100 и 101 оттенок](https://www.fanagoria.ru/collection/100-ottenkov).
- `fan-group-sur-lie`: [Фанагория: Sur Lie](https://www.fanagoria.ru/collection/sur-lie).
- `fan-group-alveus-ultra-cuvee`: [Фанагория: Alveus Ultra Cuvée](https://www.fanagoria.ru/collection/alveus-ultra-cuvee).
- `fan-group-brule`: [Фанагория: Brûlé](https://www.fanagoria.ru/collection/brule).
- `fan-group-solera`: [Фанагория: Solera](https://www.fanagoria.ru/collection/solera).
- `fan-group-petnat`: [Фанагория: PetNat](https://www.fanagoria.ru/collection/petnat).
- `fan-5-elements-aligote-shardone-sovinon`: [5 Elements. Алиготе — Шардоне — Совиньон](https://www.fanagoria.ru/collection/avtorskij-stil-fanagoria/5-elements-aligote-shardone-sovinon).
- `fan-5-elements-kaberne-rubin`: [5 Elements. Каберне — Рубин](https://www.fanagoria.ru/collection/avtorskij-stil-fanagoria/5-elements-kaberne-rubin).
- `fan-hay-bay-risling`: [Hay Bay. Рислинг](https://www.fanagoria.ru/collection/avtorskij-stil-fanagoria/hay-bay-risling).
- `fan-the-lines-petnat-kaberne-fran`: [PetNat. Каберне Фран](https://www.fanagoria.ru/collection/petnat/the-lines-petnat-kaberne-fran).
- `fan-the-lines-petnat-kaberne-sovinon`: [PetNat. Каберне Совиньон](https://www.fanagoria.ru/collection/petnat/the-lines-petnat-kaberne-sovinon).
- `fan-the-lines-petnat-sovinon-blan-aligote-pino-seryj`: [PetNat. Совиньон Блан — Алиготе — Менье](https://www.fanagoria.ru/collection/petnat/the-lines-petnat-sovinon-blan-aligote-pino-seryj).

## Gray product checks

Every check compared the official product with all 102 rows for the exact producer. The check examined names, descriptions, grapes, and relevant bottle images. A missing match only applies to the saved snapshot.

### 5 Elements. Алиготе — Шардоне — Совиньон

- Product: `official-fan-5-elements-aligote-shardone-sovinon`.
- Evidence: [5 Elements. Алиготе — Шардоне — Совиньон](https://www.fanagoria.ru/collection/avtorskij-stil-fanagoria/5-elements-aligote-shardone-sovinon).
- Absence basis: The snapshot has only two 5 Elements sparkling brut cards. Neither card is this still white blend.
- Image: https://www.fanagoria.ru/storage/resize/400/storage/app/uploads/public/668/403/814/6684038147826738150052.png
- Preparation: Proportional resize to at most 480 pixels. WebP encoding. No retouching.

### 5 Elements. Каберне — Рубин

- Product: `official-fan-5-elements-kaberne-rubin`.
- Evidence: [5 Elements. Каберне — Рубин](https://www.fanagoria.ru/collection/avtorskij-stil-fanagoria/5-elements-kaberne-rubin).
- Absence basis: The snapshot has only two 5 Elements sparkling brut cards. Neither card is this still red blend.
- Image: https://www.fanagoria.ru/storage/resize/400/storage/app/uploads/public/668/403/933/6684039335c26604717415.png
- Preparation: Proportional resize to at most 480 pixels. WebP encoding. No retouching.

### Hay Bay. Рислинг

- Product: `official-fan-hay-bay-risling`.
- Evidence: [Hay Bay. Рислинг](https://www.fanagoria.ru/collection/avtorskij-stil-fanagoria/hay-bay-risling).
- Absence basis: The only Hay Bay snapshot card is Chardonnay. No Hay Bay Riesling card exists.
- Image: https://www.fanagoria.ru/storage/resize/400/storage/app/uploads/public/613/208/fd5/613208fd5630b432203578.png
- Preparation: Proportional resize to at most 480 pixels. WebP encoding. No retouching.

### PetNat. Каберне Фран

- Product: `official-fan-the-lines-petnat-kaberne-fran`.
- Evidence: [PetNat. Каберне Фран](https://www.fanagoria.ru/collection/petnat/the-lines-petnat-kaberne-fran).
- Absence basis: No PetNat collection or ancestral-method card occurs among the 102 producer records. Other Cabernet Franc cards belong to named still or Brule collections.
- Image: https://www.fanagoria.ru/storage/resize/400/storage/app/uploads/public/65c/f1d/e29/65cf1de29c9ad876745487.png
- Preparation: Proportional resize to at most 480 pixels. WebP encoding. No retouching.

### PetNat. Каберне Совиньон

- Product: `official-fan-the-lines-petnat-kaberne-sovinon`.
- Evidence: [PetNat. Каберне Совиньон](https://www.fanagoria.ru/collection/petnat/the-lines-petnat-kaberne-sovinon).
- Absence basis: No PetNat collection or ancestral-method card occurs among the 102 producer records. Cabernet Sauvignon alone does not establish equivalence with another collection.
- Image: https://www.fanagoria.ru/storage/resize/400/storage/app/uploads/public/65c/f20/70d/65cf2070d696f189254210.png
- Preparation: Proportional resize to at most 480 pixels. WebP encoding. No retouching.

### PetNat. Совиньон Блан — Алиготе — Менье

- Product: `official-fan-the-lines-petnat-sovinon-blan-aligote-pino-seryj`.
- Evidence: [PetNat. Совиньон Блан — Алиготе — Менье](https://www.fanagoria.ru/collection/petnat/the-lines-petnat-sovinon-blan-aligote-pino-seryj).
- Absence basis: No PetNat collection or ancestral-method card occurs among the 102 producer records. The official page confirms Meunier; the historical URL spelling is not used to infer grapes.
- Image: https://www.fanagoria.ru/storage/resize/400/storage/app/uploads/public/65c/f1c/b75/65cf1cb75b904898363233.png
- Preparation: Proportional resize to at most 480 pixels. WebP encoding. No retouching.

## Background extraction, 2026-10-16

14 display images use transparent cutouts from the built-in `image_gen` tool.
Read [imagegen-cutouts.json](imagegen-cutouts.json) for every exact prompt, source hash, generated PNG hash, output hash, and review note.
The review checks product identity, main label text, cap, color, and artwork at the UI display size.
Imagegen resamples fine print and reflections. The generated images are not evidence for label microtext.
The product facts remain sourced from the catalog and official pages.
The final frame excludes faint transparent outliers. The conversion preserves alpha and fits the cropped image into 720 px height before padding.
The WebP quality is 88. The alpha quality is 100. Each file has 6 px transparent padding.
Unedited images retain their previous bytes. Original edited-image bytes remain in Git revision `89aa3780`.

The generic `ona-skazala-da` snapshot photo shows a wedding scene with several bottles labeled WEDDING Bliss.
The photo does not establish this product package. The map uses the labeled image placeholder.
The product node and its catalog link remain available. The crosswalk preserves the source filename and hash.
