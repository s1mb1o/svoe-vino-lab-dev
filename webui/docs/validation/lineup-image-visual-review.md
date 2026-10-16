# Lineup image visual review

Date: 2026-10-16.
Input revision: `41cef258`.
Branch: `product-line-map`.

## Scope

The review covers all 636 referenced image files across eleven producer maps.
The maps also contain eleven labeled image placeholders.
Every image was reviewed on flat light and dark backgrounds in 22 contact sheets.
The contact sheet fits each image into a 106 × 186 px cell.
A suspect image was then inspected at full asset size.
This review checks visible outlines, background remnants and image framing at the stated sizes.
It does not validate label microtext or inspect every original pixel.

## Findings

One additional background defect was confirmed.
Fanagoria Decanter Saperavi 2017 had opaque white rectangles beside the right neck contour.
A new built-in imagegen edit uses the original catalog image.
The corrected WebP keeps the existing URL.
The main bottle identity and label layout match the source at UI sizes.
The other 635 reviewed images have no additional visible background remnant at the review size.
Read [the Fanagoria prompt manifest](../product-line-maps/fanagoria/imagegen-cutouts.json) for the exact prompt, hashes and rejected output.

The review also found 31 images with an approximate desktop bottle height below 130 px.
Before correction, the image files contained large transparent fields that reduced the visible bottle under the CSS max-width limit.
These framing observations are resolved by the measured-frame renderer.
Read [the sizing validation](product-image-sizing.md) for the implementation and checks.

| Producer | Reviewed images | Corrected backgrounds | Resolved framing observations |
| --- | ---: | ---: | ---: |
| fanagoria | 107 | 1 | 6 |
| abrau-durso | 52 | 0 | 0 |
| alma-valley | 41 | 0 | 3 |
| derbent-vino | 66 | 0 | 5 |
| inkerman | 17 | 0 | 5 |
| koktebel | 28 | 0 | 1 |
| kuban-vino | 103 | 0 | 3 |
| massandra | 45 | 0 | 4 |
| myskhako | 97 | 0 | 0 |
| vedernikov | 45 | 0 | 1 |
| zolotaya-balka | 35 | 0 | 3 |

## Verification

All 65 map and registry tests passed with the full catalog snapshot.
The production build passed.
The local server was rebuilt and restarted on port 18553.
Chromium and WebKit each passed four corrected-image cases: desktop and mobile in light and dark themes.
Each case checks served SHA-256, transparent samples beside the neck, label visibility, selection and the portal link.
Mobile cases also check the native popup and the preserved map position after return.
Flat composites were inspected at 350 px, 176 px and 108 px image heights.
These checks use emulated viewports. No physical device test was performed.

Read [the complete review record](lineup-image-visual-review.json) for every asset hash, observation and browser result.

## Local proof files

The ignored directory `reports/lineup-image-review/` contains all 22 contact sheets.
The `saperavi/` subdirectory contains the corrected-asset screenshots and browser JSON results.
The contact sheets show the audit inputs. The Saperavi proof files show the correction.
Keep the ignored proof files outside Git. The committed JSON record preserves the complete reviewed asset list.

## Resolved framing observations

The height estimate uses the visible alpha frame and the desktop CSS limits.
The observations identify scale differences. They do not indicate a remaining opaque background.

| Producer | Product | Approximate visible height before correction, px |
| --- | --- | ---: |
| fanagoria | [100 оттенков красного. Пино Нуар](../../public/product-line-maps/fanagoria/wine-fanagoriya-100-ottenkov-krasnogo-pino-nuar-krasnoe-suhoe-135.webp) | 120 |
| fanagoria | [Blanc de Blancs](../../public/product-line-maps/fanagoria/wine-fanagoriya-blanc-de-blancs-shardone-beloe-bryut-12.webp) | 120 |
| fanagoria | [Blanc de Noirs Менье](../../public/product-line-maps/fanagoria/wine-fanagoriya-blanc-de-noirs-mene-pino-mene-beloe-ekstra-bryut-12.webp) | 120 |
| fanagoria | [Формула Q](../../public/product-line-maps/fanagoria/wine-fanagoriya-formula-q-kaberne-sovinon-krasnoe-suhoe-135.webp) | 120 |
| fanagoria | [Ледяное вино. Мускат](../../public/product-line-maps/fanagoria/wine-fanagoriya-ledyanoe-vino-muskat-muskat-ottonel-beloe-sladkoe-11.webp) | 120 |
| fanagoria | [SAQRA](../../public/product-line-maps/fanagoria/wine-fanagoriya-saqra-saperavi-krasnoe-suhoe-135.webp) | 120 |
| alma-valley | [Альма Гравити. Пино Нуар - Мерло - Каберне Совиньон](../../public/product-line-maps/alma-valley/wine-alma-valley-alma-graviti-pino-nuar-merlo-kaberne-sovinon-krasnoe-suhoe-14.webp) | 120 |
| alma-valley | [Мерло Резерв](../../public/product-line-maps/alma-valley/wine-alma-valley-merlo-rezerv-krasnoe-suhoe-14.webp) | 120 |
| alma-valley | [Шардоне Резерв](../../public/product-line-maps/alma-valley/wine-alma-valley-shardone-rezerv-beloe-suhoe-135.webp) | 120 |
| derbent-vino | [Ди Каспико Фиори ди Маре Верде](../../public/product-line-maps/derbent-vino/wine-derbent-vino-di-kaspiko-fiori-di-mare-verde-avgustin-rozovoe-polusuhoe-10.webp) | 118.9 |
| derbent-vino | [Эндемы Рислинг](../../public/product-line-maps/derbent-vino/wine-derbent-vino-endemy-risling-beloe-bryut-105-125.webp) | 120 |
| derbent-vino | [Эндемы Шардоне](../../public/product-line-maps/derbent-vino/wine-derbent-vino-endemy-shardone-beloe-bryut-105-125.webp) | 120 |
| derbent-vino | [Эндемы Шардоне](../../public/product-line-maps/derbent-vino/wine-derbent-vino-endemy-shardone-beloe-suhoe-13.webp) | 120 |
| derbent-vino | [Эндемы Совиньон](../../public/product-line-maps/derbent-vino/wine-derbent-vino-endemy-sovinon-beloe-bryut-105-125.webp) | 120 |
| inkerman | [Inkerman брют](../../public/product-line-maps/inkerman/wine-inkermanskiy-zmv-inkerman-bryut-shardone-beloe-135.webp) | 120 |
| inkerman | [Inkerman полусладкое розе](../../public/product-line-maps/inkerman/wine-inkermanskiy-zmv-inkerman-polusladkoe-roze-aligote-rozovoe-135.webp) | 120 |
| inkerman | [Кокур Белый экстра брют](../../public/product-line-maps/inkerman/wine-inkermanskiy-zmv-kokur-belyy-ekstra-bryut-beloe-135.webp) | 120 |
| inkerman | [Special Reserve. Ркацители](../../public/product-line-maps/inkerman/wine-inkermanskiy-zmv-special-reserve-rkatsiteli-beloe-suhoe-13.webp) | 120 |
| inkerman | [Winemaker's Selection Саперави](../../public/product-line-maps/inkerman/wine-inkermanskiy-zmv-winemakers-selection-saperavi-krasnoe-polusladkoe-12.webp) | 120 |
| koktebel | [Ркацители](../../public/product-line-maps/koktebel/wine-zmv-koktebel-rkatsiteli-beloe-sladkoe-135.webp) | 120 |
| kuban-vino | [Аристов. Кюве Александр Blanc de Blancs 36](../../public/product-line-maps/kuban-vino/wine-kuban-vino-aristov-kyuve-aleksandr-blanc-de-blancs-36-shardone-beloe-ekstra-bryut-12.webp) | 120 |
| kuban-vino | [Аристов. Кюве Александр. Миллезимато](../../public/product-line-maps/kuban-vino/wine-kuban-vino-aristov-kyuve-aleksandr-millezimato-shardone-beloe-ekstra-bryut-12.webp) | 120 |
| kuban-vino | [Аристов. Кюве Александр Rose de Pinot](../../public/product-line-maps/kuban-vino/wine-kuban-vino-aristov-kyuve-aleksandr-rose-de-pinot-pino-nuar-rozovoe-ekstra-bryut-12.webp) | 120 |
| massandra | [Массандра Херес](../../public/product-line-maps/massandra/wine-massandra-heres.webp) | 117.7 |
| massandra | [Мускат Белый Южнобережный](../../public/product-line-maps/massandra/wine-massandra-muskat-belyy-yuzhnoberezhnyy-beloe-sladkoe-16.webp) | 120 |
| massandra | [Мускат позднего сбора](../../public/product-line-maps/massandra/wine-massandra-muskat-pozdnego-sbora-muskat-belyy-beloe-sladkoe-16.webp) | 120 |
| massandra | [Портвейн Белый Гурзуф](../../public/product-line-maps/massandra/wine-massandra-portveyn-belyy-gurzuf-kokur-belyy-beloe-sladkoe-135.webp) | 120 |
| vedernikov | [Цимлянский Черный брют розе](../../public/product-line-maps/vedernikov/wine-vinodelnya-vedernikov-tsimlyanskiy-chernyy-bryut-roze-rozovoe-14.webp) | 120 |
| zolotaya-balka | [Брют Белое Золотая Балка](../../public/product-line-maps/zolotaya-balka/wine-bryut-beloe-zolotaya-balka.webp) | 127.3 |
| zolotaya-balka | [Черный Принц](../../public/product-line-maps/zolotaya-balka/wine-zolotaya-balka-chernyy-prints-shardone-beloe-ekstra-bryut-12.webp) | 118.9 |
| zolotaya-balka | [Cuvee de Vitmer rose](../../public/product-line-maps/zolotaya-balka/wine-zolotaya-balka-cuvee-de-vitmer-rose-pino-blan-rozovoe-bryut-12.webp) | 120 |
