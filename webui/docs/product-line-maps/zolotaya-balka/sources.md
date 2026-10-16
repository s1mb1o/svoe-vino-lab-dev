# Золотая Балка: source record

Date: 2026-10-16.

## Scope

- The exact catalog producer value is `Золотая Балка`.
- The map contains all 41 producer cards from `official-2026-09-17`.
- The map adds 2 products with official evidence and no confirmed snapshot identity.
- Each snapshot card has one product. All alias arrays are empty.
- Original catalog descriptions and grape lists are retained.
- The initial import copied catalog WebP files without modification. The current hashes and transformations are in `crosswalk.json`.
- Official PNG and JPEG bottle images are converted to lossless WebP without cropping or resizing. Original URLs and asset hashes are in the crosswalk.
- Numeric prices are null. Premium tiers are editorial relative positions.
- A neutral tier means that the current relative price is not verified. It does not mean low quality.
- A gray node means no confirmed card in the saved snapshot. It does not establish current shop availability.

## Official collection sources

- `official-collections`: https://zolotayabalka.ru/product/
- `official-black-prince`: https://zolotayabalka.ru/product/black-prince/
- `official-cuvee-de-vitmer`: https://zolotayabalka.ru/product/cuvee-de-vitmer/
- `official-balaklava`: https://zolotayabalka.ru/product/balaklava/
- `official-zb-classic`: https://zolotayabalka.ru/product/zolotaya-balka/
- `official-zb-spumante`: https://zolotayabalka.ru/product/zb-spumante/
- `official-zb-moscato`: https://zolotayabalka.ru/product/zb-moscato/
- `official-zb-frizzante`: https://zolotayabalka.ru/product/zb-frizzante/
- `official-zb-still`: https://zolotayabalka.ru/product/zbwine/
- `official-more-nebo`: https://zolotayabalka.ru/product/more-nebo/
- `official-loco-menu`: https://zolotayabalka.ru/pdf/zb_wines_06-2025.pdf
- `official-more-nebo-red`: https://zolotayabalka.ru/product/more-nebo/more-nebo-polusukhoe-krasnoe/
- `official-more-nebo-white`: https://zolotayabalka.ru/product/more-nebo/more-nebo-bryut-beloe/

## Mapping decisions and limits

- Two generic rose cards use the base Zolotaya Balka labels. The local label images confirm this assignment.
- Blanc de Neige and Pink appear as Loco Cimbali in the official restaurant PDF. The PDF is evidence for collection identity only. Restaurant prices are not copied or used as current retail prices.
- The historical Moscato, Spumante, Frizzante, and Balaklava cards remain separate. Similar names do not establish equivalent slugs.
- The neutral tier contains Frizzante, Loco Cimbali, and More & Nebo. Their current retail position is not verified.

## Official additions and absence checks

### official-more-nebo-red-semi-dry

- Product page: https://zolotayabalka.ru/product/more-nebo/more-nebo-polusukhoe-krasnoe/
- Exact bottle image: https://zolotayabalka.ru/upload/resize_cache/iblock/cfc/800_800_0/nvjnssh23cmwtfk2xssu0jvro95mlj9k.jpg
- Absence evidence: No Zolotaya Balka catalog card names the More & Nebo collection. The full 2,103-row search only finds an unrelated Locantita More card from Skalisty Bereg. Syrah alone does not identify this product.
- The producer subset and the full 2,103-row catalog were searched. No available snapshot card is replaced.

### official-more-nebo-white-brut

- Product page: https://zolotayabalka.ru/product/more-nebo/more-nebo-bryut-beloe/
- Exact bottle image: https://zolotayabalka.ru/upload/resize_cache/iblock/beb/800_800_0/qz5af68fwwyxn9crel1nuxkimqdm94ae.jpg
- Absence evidence: The More & Nebo collection is absent from all 41 producer cards. Other white bruts have different brand labels. No equivalent identity is asserted.
- The producer subset and the full 2,103-row catalog were searched. No available snapshot card is replaced.

## Collection coverage

| Group | Snapshot cards | Official additions |
| --- | ---: | ---: |
| Чёрный Принц | 2 | 0 |
| Cuvée de Vitmer | 2 | 0 |
| Балаклава | 6 | 0 |
| Золотая Балка | 9 | 0 |
| ZB Spumante | 6 | 0 |
| ZB Moscato / Мускатные | 4 | 0 |
| ZB Wine · тихие вина | 5 | 0 |
| ZB Frizzante / Жемчужные | 5 | 0 |
| Loco Cimbali | 2 | 0 |
| Море & Небо | 0 | 2 |

## Image limits

The following catalog rows have `local_path: null`. The map uses `image: null` and the explicit UI placeholder. No other bottle image is substituted.

- `polusladkoe-krasnoe-zb-vajn-frizzante`
- `polusladkoe-krasnoe-zolotaya-balka`
- `polusladkoe-rozovoe-zolotaya-balka`
- `polusuhoe-rozovoe-zb-vajn-frizzante`
- `suhoe-beloe-zb-vajn-frizzante`
- `zb-vajn-risling-polusuhoe-beloe`
- `zb-vajn-roze-suhoe-rozovoe`
- `zb-vajn-spumante-polusuhoe-beloe`

All official addition images were visually checked against their product labels.

## Background extraction, 2026-10-16

10 display images use transparent cutouts from the built-in `image_gen` tool.
Read [imagegen-cutouts.json](imagegen-cutouts.json) for every exact prompt, source hash, generated PNG hash, output hash, and review note.
The review checks product identity, main label text, cap, color, and artwork at the UI display size.
Imagegen resamples fine print and reflections. The generated images are not evidence for label microtext.
The product facts remain sourced from the catalog and official pages.
The final frame excludes faint transparent outliers. The conversion preserves alpha and fits the cropped image into 720 px height before padding.
The WebP quality is 88. The alpha quality is 100. Each file has 6 px transparent padding.
Unedited images retain their previous bytes. Original edited-image bytes remain in Git revision `89aa3780`.

## Visible image frames, 2026-10-16

The producer JSON records measured frame geometry for 35 images.
The frame uses the source alpha outline and a small transparent margin.
The frame changes image presentation only. Source image bytes and product facts are unchanged.
The renderer uses the frame for group previews, product nodes and product details.
Read [the sizing contract](../../product-image-sizing.md) for the measurement method.

## Missing bottle-image recovery, 2026-10-16

Restore 8 empty bottle-image slots from exact official product pages.
Read [image-recovery.json](image-recovery.json) for source URLs, original hashes, exact prompts, output hashes, and measured frames.
The earlier placeholder notes describe the previous state. This recovery supersedes those notes.
Eight exact official product photos replace unresolved snapshot images. All eight use built-in imagegen for background extraction. Keep the main label identity. Reject halo remnants on the rose semi-sweet image.
