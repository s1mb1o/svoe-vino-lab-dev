# Кубань-Вино map sources

Prepared on 2026-10-16. The map contains 97 distinct catalog records and 6 verified official additions.

## Scope

The input is `/Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace/svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl`. The exact producer value is `Кубань-Вино`. The snapshot date is 2026-09-17.
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

- The map keeps Chateau Tamagne, Aristov, and Vysokiy Bereg under one producer. Each named series remains a separate group.
- The generic Cabernet de Tamagne, Krasnostop de Tamagne, and Saperavi de Tamagne labels were inspected. They belong to the main Chateau Tamagne visual range. They are not merged with similar cards.
- The official leaflets state Premium for Nude and Alta Rosso. They state Low premium for Resto. No ruble amount is inferred.
- Reserve includes distinct still and sparkling records. A method for one Reserve product is not assigned to every Reserve product.
- Aristov 8 package variants remain separate. Neutral placement avoids a false comparison with standard-strength products.
- The source catalog identifies Lesnaya Proseka as Aristov Arte. This is not inferred from the slug.

## Official sources

- `kuban-official`: [Кубань-Вино: материалы по брендам и коллекциям](https://kuban-vino.ru/partnerstvo/).
- `kuban-reserve`: [Кубань-Вино: коллекционное Саперави Reserve](https://kuban-vino.ru/upload/iblock/9ef/pqkaqauyk1mv55ltvox2kvtk3rxigw30/%D0%A8%D0%A2_%D0%A1%D0%B0%D0%BF%D0%B5%D1%80%D0%B0%D0%B2%D0%B8_2015.pdf).
- `kuban-nude-saperavi`: [Chateau Tamagne Nude. Саперави](https://kuban-vino.ru/upload/iblock/d43/9imq8isxmtbbplviev3j4sjz9ubzqeu0/%D0%A8%D0%A2%20%D1%81%D1%83%D1%85%D0%BE%D0%B5%20%D0%BA%D1%80%D0%B0%D1%81%D0%BD%D0%BE%D0%B5%20%D0%A1%D0%B0%D0%BF%D0%B5%D1%80%D0%B0%D0%B2%D0%B8%20%D0%9D%D0%AE%D0%94.pdf).
- `kuban-nude-rkatsiteli`: [Chateau Tamagne Nude. Ркацители](https://kuban-vino.ru/upload/iblock/89d/b8i3z2sfija3dkaox16nzxnhp9ep5apg/%D0%A8%D0%A2%20%D1%81%D1%83%D1%85%D0%BE%D0%B5%20%D0%B1%D0%B5%D0%BB%D0%BE%D0%B5%20%D0%A0%D0%BA%D0%B0%D1%86%D0%B8%D1%82%D0%B5%D0%BB%D0%B8%20%D0%9D%D0%AE%D0%94.pdf).
- `kuban-alta-rosso`: [Aristov Cuvée Alexander. Alta Rosso 2022](https://kuban-vino.ru/upload/iblock/2c3/q9ksyoig7r9c8r9v9wqksj0m2ohsg0ti/%D0%9A%D1%8E%D0%B2%D0%B5%20%D0%90%D0%BB%D0%B5%D0%BA%D1%81%D0%B0%D0%BD%D0%B4%D1%80.%20%D0%90%D0%BB%D1%8C%D1%82%D0%B0%20%D0%A0%D0%BE%D1%81%D1%81%D0%BE_%D0%B2%D1%8B%D0%B4%D0%B5%D1%80%D0%B6%D0%B0%D0%BD%D0%BD%D0%BE%D0%B5%20%D1%81%D1%83%D1%85%D0%BE%D0%B5%20%D0%BA%D1%80%D0%B0%D1%81%D0%BD%D0%BE%D0%B5.pdf).
- `kuban-resto-white`: [Высокий Берег Resto. Грюнер](https://kuban-vino.ru/upload/iblock/86c/l3zk0prbhm9wu3pvvpveba948a9qi2nh/%D0%92%D1%8B%D1%81%D0%BE%D0%BA%D0%B8%D0%B9%20%D0%91%D0%B5%D1%80%D0%B5%D0%B3_%D0%A0%D0%B5%D1%81%D1%82%D0%BE_%D1%81%D1%83%D1%85%D0%BE%D0%B5%20%D0%B1%D0%B5%D0%BB%D0%BE%D0%B5_%D0%93%D1%80%D1%8E%D0%BD%D0%B5%D1%80.pdf).
- `kuban-resto-red`: [Высокий Берег Resto. Сира, красное](https://kuban-vino.ru/upload/iblock/326/r07mbo9ujthmqmk2032z3omvefezga5o/%D0%92%D1%8B%D1%81%D0%BE%D0%BA%D0%B8%D0%B9%20%D0%91%D0%B5%D1%80%D0%B5%D0%B3_%D0%A0%D0%B5%D1%81%D1%82%D0%BE%20%D0%BA%D1%80%D0%B0%D1%81%D0%BDo%D0%B5%20%D1%81%D0%B8%D1%80%D0%B0.pdf).
- `kuban-resto-rose`: [Высокий Берег Resto. Сира, розовое](https://kuban-vino.ru/upload/iblock/eff/j4rza7j3vjyesgm7mlw2s8okod0qfyii/%D0%92%D1%8B%D1%81%D0%BE%D0%BA%D0%B8%D0%B9%20%D0%91%D0%B5%D1%80%D0%B5%D0%B3%20%D0%A0%D0%B5%D1%81%D1%82%D0%BE%20%D1%81%D1%83%D1%85%D0%BE%D0%B5%20%D1%80%D0%BE%D0%B7%D0%BE%D0%B2%D0%BE%D0%B5_%D0%A1%D0%B8%D1%80%D0%B0.pdf).

## Gray product checks

Every check compared the official product with all 97 rows for the exact producer. The check examined names, descriptions, grapes, and relevant bottle images. A missing match only applies to the saved snapshot.

### Chateau Tamagne Nude. Саперави

- Product: `official-kuban-nude-saperavi`.
- Evidence: [Chateau Tamagne Nude. Саперави](https://kuban-vino.ru/upload/iblock/d43/9imq8isxmtbbplviev3j4sjz9ubzqeu0/%D0%A8%D0%A2%20%D1%81%D1%83%D1%85%D0%BE%D0%B5%20%D0%BA%D1%80%D0%B0%D1%81%D0%BD%D0%BE%D0%B5%20%D0%A1%D0%B0%D0%BF%D0%B5%D1%80%D0%B0%D0%B2%D0%B8%20%D0%9D%D0%AE%D0%94.pdf).
- Absence basis: The snapshot has several ordinary Chateau Tamagne Saperavi cards. Their bottle labels were inspected and differ from the official NUDE NON FILTERED SAPERAVI label. No Nude card or Nude production description is present.
- Image: https://kuban-vino.ru/upload/iblock/d43/9imq8isxmtbbplviev3j4sjz9ubzqeu0/ШТ сухое красное Саперави НЮД.pdf PDF page 1.
- Preparation: Extracted the bottle image from PDF page 1. Proportional resize to at most 480 pixels. WebP encoding. No retouching.

### Chateau Tamagne Nude. Ркацители

- Product: `official-kuban-nude-rkatsiteli`.
- Evidence: [Chateau Tamagne Nude. Ркацители](https://kuban-vino.ru/upload/iblock/89d/b8i3z2sfija3dkaox16nzxnhp9ep5apg/%D0%A8%D0%A2%20%D1%81%D1%83%D1%85%D0%BE%D0%B5%20%D0%B1%D0%B5%D0%BB%D0%BE%D0%B5%20%D0%A0%D0%BA%D0%B0%D1%86%D0%B8%D1%82%D0%B5%D0%BB%D0%B8%20%D0%9D%D0%AE%D0%94.pdf).
- Absence basis: The snapshot has Rkatsiteli blends and Eno Amber. None is named Nude or has the verified NUDE NON FILTERED RKATSITELI label and matching production record.
- Image: https://kuban-vino.ru/upload/iblock/89d/b8i3z2sfija3dkaox16nzxnhp9ep5apg/ШТ сухое белое Ркацители НЮД.pdf PDF page 1.
- Preparation: Extracted the bottle image from PDF page 1. Proportional resize to at most 480 pixels. WebP encoding. No retouching.

### Aristov Cuvée Alexander. Alta Rosso 2022

- Product: `official-kuban-alta-rosso`.
- Evidence: [Aristov Cuvée Alexander. Alta Rosso 2022](https://kuban-vino.ru/upload/iblock/2c3/q9ksyoig7r9c8r9v9wqksj0m2ohsg0ti/%D0%9A%D1%8E%D0%B2%D0%B5%20%D0%90%D0%BB%D0%B5%D0%BA%D1%81%D0%B0%D0%BD%D0%B4%D1%80.%20%D0%90%D0%BB%D1%8C%D1%82%D0%B0%20%D0%A0%D0%BE%D1%81%D1%81%D0%BE_%D0%B2%D1%8B%D0%B4%D0%B5%D1%80%D0%B6%D0%B0%D0%BD%D0%BD%D0%BE%D0%B5%20%D1%81%D1%83%D1%85%D0%BE%D0%B5%20%D0%BA%D1%80%D0%B0%D1%81%D0%BD%D0%BE%D0%B5.pdf).
- Absence basis: All six Cuvée Alexander snapshot cards were checked. None is Alta Rosso or a still red Ancellotta wine. The official PDF identifies Alta Rosso 2022 explicitly.
- Image: https://kuban-vino.ru/upload/iblock/2c3/q9ksyoig7r9c8r9v9wqksj0m2ohsg0ti/Кюве Александр. Альта Россо_выдержанное сухое красное.pdf PDF page 1.
- Preparation: Extracted the bottle image from PDF page 1. Proportional resize to at most 480 pixels. WebP encoding. No retouching.

### Высокий Берег Resto. Грюнер

- Product: `official-kuban-resto-white`.
- Evidence: [Высокий Берег Resto. Грюнер](https://kuban-vino.ru/upload/iblock/86c/l3zk0prbhm9wu3pvvpveba948a9qi2nh/%D0%92%D1%8B%D1%81%D0%BE%D0%BA%D0%B8%D0%B9%20%D0%91%D0%B5%D1%80%D0%B5%D0%B3_%D0%A0%D0%B5%D1%81%D1%82%D0%BE_%D1%81%D1%83%D1%85%D0%BE%D0%B5%20%D0%B1%D0%B5%D0%BB%D0%BE%D0%B5_%D0%93%D1%80%D1%8E%D0%BD%D0%B5%D1%80.pdf).
- Absence basis: No Resto card or Gruner wine occurs among the 97 records. The Resto brand and grape are explicit in the official leaflet.
- Image: https://kuban-vino.ru/upload/iblock/86c/l3zk0prbhm9wu3pvvpveba948a9qi2nh/Высокий Берег_Ресто_сухое белое_Грюнер.pdf PDF page 1.
- Preparation: Extracted the bottle image from PDF page 1. Proportional resize to at most 480 pixels. WebP encoding. No retouching.

### Высокий Берег Resto. Сира, красное

- Product: `official-kuban-resto-red`.
- Evidence: [Высокий Берег Resto. Сира, красное](https://kuban-vino.ru/upload/iblock/326/r07mbo9ujthmqmk2032z3omvefezga5o/%D0%92%D1%8B%D1%81%D0%BE%D0%BA%D0%B8%D0%B9%20%D0%91%D0%B5%D1%80%D0%B5%D0%B3_%D0%A0%D0%B5%D1%81%D1%82%D0%BE%20%D0%BA%D1%80%D0%B0%D1%81%D0%BDo%D0%B5%20%D1%81%D0%B8%D1%80%D0%B0.pdf).
- Absence basis: No Resto card or High Coast Syrah card occurs among the 97 records. The official leaflet distinguishes the dry red wine from Resto dry rose.
- Image: https://kuban-vino.ru/upload/iblock/326/r07mbo9ujthmqmk2032z3omvefezga5o/Высокий Берег_Ресто краснoе сира.pdf PDF page 1.
- Preparation: Extracted the bottle image from PDF page 1. Proportional resize to at most 480 pixels. WebP encoding. No retouching.

### Высокий Берег Resto. Сира, розовое

- Product: `official-kuban-resto-rose`.
- Evidence: [Высокий Берег Resto. Сира, розовое](https://kuban-vino.ru/upload/iblock/eff/j4rza7j3vjyesgm7mlw2s8okod0qfyii/%D0%92%D1%8B%D1%81%D0%BE%D0%BA%D0%B8%D0%B9%20%D0%91%D0%B5%D1%80%D0%B5%D0%B3%20%D0%A0%D0%B5%D1%81%D1%82%D0%BE%20%D1%81%D1%83%D1%85%D0%BE%D0%B5%20%D1%80%D0%BE%D0%B7%D0%BE%D0%B2%D0%BE%D0%B5_%D0%A1%D0%B8%D1%80%D0%B0.pdf).
- Absence basis: The snapshot High Coast Graphite Rose card belongs to Graphite. No Resto card exists. The official Resto rose label differs and the leaflet identifies Syrah explicitly.
- Image: https://kuban-vino.ru/upload/iblock/eff/j4rza7j3vjyesgm7mlw2s8okod0qfyii/Высокий Берег Ресто сухое розовое_Сира.pdf PDF page 1.
- Preparation: Extracted the bottle image from PDF page 1. Proportional resize to at most 480 pixels. WebP encoding. No retouching.

## Background extraction, 2026-10-16

50 display images use transparent cutouts from the built-in `image_gen` tool.
Read [imagegen-cutouts.json](imagegen-cutouts.json) for every exact prompt, source hash, generated PNG hash, output hash, and review note.
The review checks product identity, main label text, cap, color, and artwork at the UI display size.
Imagegen resamples fine print and reflections. The generated images are not evidence for label microtext.
The product facts remain sourced from the catalog and official pages.
The final frame excludes faint transparent outliers. The conversion preserves alpha and fits the cropped image into 720 px height before padding.
The WebP quality is 88. The alpha quality is 100. Each file has 6 px transparent padding.
Unedited images retain their previous bytes. Original edited-image bytes remain in Git revision `89aa3780`.

## Visible image frames, 2026-10-16

The producer JSON records measured frame geometry for 103 images.
The frame uses the source alpha outline and a small transparent margin.
The frame changes image presentation only. Source image bytes and product facts are unchanged.
The renderer uses the frame for group previews, product nodes and product details.
Read [the sizing contract](../../product-image-sizing.md) for the measurement method.
