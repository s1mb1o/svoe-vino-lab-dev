# Asset provenance

Date: 2026-09-15.

The user requested the source portal look and feel.
Selected public visual assets are stored locally for this implementation.
Original rights remain with the source owners. This repository does not relicense these assets.
Source application scripts, analytics, and CSS bundles are not included.
The implementation uses its own CSS.

## Presentation files

Date: 2026-09-29

The owner supplied `../../svoe-wino-hackaton/presentation/chtozavino-presentation.pptx`.
The public PowerPoint copy has the same bytes as the source file.
LibreOffice exports its PDF version from that copy.
Both files are in the ignored `public/presentations/` directory.
The `/presentation` page links to these local files.

## Android application screenshots

Date: 2026-09-29

The Android landing page uses six screenshots from the verified Android 0.1.4 set.
The source directory is
`../../android/docs/screenshots/android-0.1.4/web/`.
The public copies are in `public/screenshots/android/`.

The screenshots came from the installed application on a Google Pixel 8.
The phone ran Android 17 at API level 37.
The screenshots show real application states.
The photo example matched `Пино Нуар` at 91%.
The barcode example matched `Шато Тамань. Каберне Совиньон` at 100%.

The selected files are:

- `02_bottle_selected_light.webp`
- `03_bottle_selected_dark.webp`
- `04_recognition_result_dark.webp`
- `05_processing_pipeline_dark.webp`
- `07_settings_dark.webp`
- `08_barcode_result_dark.webp`

The source and public copies have the same bytes.
No third-party screenshot or generated marketing mockup is used.

## Sources

- [PlayfairDisplay-VariableFont_wght.woff2](https://vino-svoe.ru/fonts/Playfair/PlayfairDisplay-VariableFont_wght.woff2)
- [scanner.svg](https://vino-svoe.ru/svg/scanner.svg)
- [public-rating.svg](https://vino-svoe.ru/svg/public-rating.svg)
- [svoe-vino-logo.svg](https://vino-svoe.ru/svg/logo/svoe-vino-logo.svg)
- [Priboj_Marchenko_krasnoe_no_bg_preview_carve_photos_6e051269ba.webp](https://api.vino-svoe.ru/v1/img/str-api/540/540/resize/uploads/Priboj_Marchenko_krasnoe_no_bg_preview_carve_photos_6e051269ba.webp)
- [Priboj_Marchenko_rozovoe_no_bg_preview_carve_photos_a85f40aeb6.webp](https://api.vino-svoe.ru/v1/img/str-api/540/540/resize/uploads/Priboj_Marchenko_rozovoe_no_bg_preview_carve_photos_a85f40aeb6.webp)
- [priboj_Marchenko_beloe_no_bg_preview_carve_photos_de18758756.webp](https://api.vino-svoe.ru/v1/img/str-api/540/540/resize/uploads/priboj_Marchenko_beloe_no_bg_preview_carve_photos_de18758756.webp)
- [Znoj_denisov_vajneri_no_bg_preview_carve_photos_0452c989d8.webp](https://api.vino-svoe.ru/v1/img/str-api/540/540/resize/uploads/Znoj_denisov_vajneri_no_bg_preview_carve_photos_0452c989d8.webp)
- [petnat_fioletovyj_no_bg_preview_carve_photos_e4ddd605bc.webp](https://api.vino-svoe.ru/v1/img/str-api/540/540/resize/uploads/petnat_fioletovyj_no_bg_preview_carve_photos_e4ddd605bc.webp)
- [Gevyurcztraminer_Oranzh_Usadba_Petovskih_f3d914f332.webp](https://api.vino-svoe.ru/v1/img/str-api/540/540/resize/uploads/Gevyurcztraminer_Oranzh_Usadba_Petovskih_f3d914f332.webp)
- [petnat_muskat_no_bg_preview_carve_photos_2296dc8b1a.webp](https://api.vino-svoe.ru/v1/img/str-api/540/540/resize/uploads/petnat_muskat_no_bg_preview_carve_photos_2296dc8b1a.webp)
- [zakat_denisov_vajneri_no_bg_preview_carve_photos_1_6ae9baa13d.webp](https://api.vino-svoe.ru/v1/img/str-api/540/540/resize/uploads/zakat_denisov_vajneri_no_bg_preview_carve_photos_1_6ae9baa13d.webp)
- [Cantiani_Caber_Sauv_vid_042024_Photoroom_834a144a19.webp](https://api.vino-svoe.ru/v1/img/str-api/540/540/resize/uploads/Cantiani_Caber_Sauv_vid_042024_Photoroom_834a144a19.webp)
- [MB_igrist_Blanc_vid_032026_kopiya_5c6680d1ef.webp](https://api.vino-svoe.ru/v1/img/str-api/540/540/resize/uploads/MB_igrist_Blanc_vid_032026_kopiya_5c6680d1ef.webp)
- [Cantiani_Reserve_1_e1bd881754.webp](https://api.vino-svoe.ru/v1/img/str-api/540/540/resize/uploads/Cantiani_Reserve_1_e1bd881754.webp)
- [MB_igrist_Cuvee_vid_032026_kopiya_8bb830fcc2.webp](https://api.vino-svoe.ru/v1/img/str-api/540/540/resize/uploads/MB_igrist_Cuvee_vid_032026_kopiya_8bb830fcc2.webp)
- [favicon.svg](https://vino-svoe.ru/favicon.svg)
- [background.webp](https://vino-svoe.ru/images/bg/default-layout-bg.webp)

## Product-line bottle images

The product-line map uses the local `Своё Вино` catalog snapshot from 2026-09-17.
The selection uses the `patched` image when the patch directory contains the wine slug.
The selection uses the catalog `main` image for all other wines.
The cropped PNG derivative removes transparent outer space only.
ImageMagick resized each derivative to a maximum height of 360 pixels.
ImageMagick removed metadata and exported transparent WebP files at quality 90.

- `public/line-wines/abrau-dyurso-udelnoe-vedomstvo-imperatorskoe-beloe-bryut.webp` uses the `patched` source. The source file is `svoe-wino-hackaton/dataset/patched-official-2026-09-17/abrau-dyurso-udelnoe-vedomstvo-imperatorskoe-beloe-bryut.webp`. The output is 97 by 360 pixels. Its SHA-256 is `62573a73294b2fb47a2cd12d57eae9c03bc51e7d7b1c67515bda1e9b1c291405`.
- `public/line-wines/abrau-dyurso-victor-dravigny-bryut.webp` uses the catalog `main` source. The [source image](https://api.vino-svoe.ru/v1/img/str-api/1920/1920/resize/uploads/Abrau_Dyurso_Viktor_Dravini_bryut_4b532f42da.webp) is public. The output is 104 by 360 pixels. Its SHA-256 is `ff54898730c5973fbbb6b8088340b9e798bc73de294e777796510e01a7d3642f`.
- `public/line-wines/abrau-dyurso-abrau-durso-brut-rose-reserve-pino-nuar-beloe-bryut-12.webp` uses the catalog `main` source. The [source image](https://api.vino-svoe.ru/v1/img/str-api/1920/1920/resize/uploads/abrau_dyurso_abrau_durso_brut_rose_reserve_pino_nuar_beloe_bryut_12_bb364de705.webp) is public. The output is 102 by 360 pixels. Its SHA-256 is `0933c53789e92c3d2b48367715f0949b2c80bf6f6e8b09ff01b372c75571574c`.
- `public/line-wines/abrau-dyurso-abrau-dyurso-pino-nuar-krasnoe-suhoe-13.webp` uses the catalog `main` source. The [source image](https://api.vino-svoe.ru/v1/img/str-api/1920/1920/resize/uploads/abrau_dyurso_abrau_dyurso_pino_nuar_krasnoe_suhoe_13_2c1e6330fe.webp) is public. The output is 112 by 360 pixels. Its SHA-256 is `53a3788ec98cbd2926c52d80db3ce4cd45b48233efcfb32e9efbe092102e3428`.
- `public/line-wines/abrau-dyurso-fizz-beloe-bryut.webp` uses the catalog `main` source. The [source image](https://api.vino-svoe.ru/v1/img/str-api/1920/1920/resize/uploads/Abrau_Dyurso_fizz_bryut_2a15c7f74f.webp) is public. The output is 139 by 360 pixels. Its SHA-256 is `dac55a3ab11bc9394b16fb2e2baf7a3160e30e72cf3c0c1124b925f55f1dce9d`.
- `public/line-wines/abrau-dyurso-fizz-beloe-polusladkoe.webp` uses the catalog `main` source. The [source image](https://api.vino-svoe.ru/v1/img/str-api/1920/1920/resize/uploads/Abrau_Dyurso_fizz_polusladkoe_031d93d5e0.webp) is public. The output is 141 by 360 pixels. Its SHA-256 is `fb23381ea9c7fa4b4b6b3494cdb95d54772aabbd810044bd54feca42a6667162`.

## Open dataset aggregate

- Source: [Wine Reviews on Kaggle](https://www.kaggle.com/datasets/zynicide/wine-reviews), file `winemag-data-130k-v2.csv`.
- License: `CC BY-NC-SA 4.0`.
- Download date: 2026-09-29.
- Source ZIP SHA-256: `8e6b7df797df88929c34b41b93cf60643cefa4c93b9af7396ff2196efdf47551`.
- Source CSV SHA-256: `52af2643c8ac29f010f0cc629dfbdda1c74aa0f332d11762af9ef3de4e567ac9`.
- Generated file: `shared/data/wine-style-priors.json`.
- Generated file SHA-256: `09a19fa5be08515fedc4d89fad3d23c6db609308494270399bbd827e103486a9`.
- Builder: `scripts/build-wine-style-priors.py`.
- The generated file contains aggregates for 18 grape varieties and 66,562 matched reviews.
- The generated file contains no review text and no critic score.
- The raw dataset is not stored in this repository.
- See `shared/data/WINE_STYLE_PRIORS_LICENSE.md` for the license notice.

## Generated dish illustrations

OpenAI ImageGen generated the three source PNG files on 2026-09-29.
ImageMagick made a centered 640 by 400 crop and removed metadata.
The application uses the WebP files.
The original generated PNG files remain in the local Codex generated-image directory.

### Расстегай с судаком

- File: `public/dishes/rasstegai-s-sudakom.webp`.
- Dimensions: 640 by 400 pixels.
- SHA-256: `cd530202827beca5c94c598d86e718b64b3203fb96f1f08e5cfead5a2c69f0c9`.
- Original generated file: `exec-f882e32c-efe2-481e-a88c-1dc8b289b9b0.png`.
- Prompt:

```text
Create a polished editorial food illustration for a Russian wine-pairing website dish card. Exact dish: "Расстегай с судаком" — one traditional Russian open-topped boat-shaped yeast pastry, golden baked crust, the center visibly filled with tender pieces of cooked zander fish, a little onion and fresh dill. Show the characteristic open seam on top; do not depict a closed pie, dumpling, pizza, or generic fish fillet. Three-quarter overhead view on a simple warm ivory ceramic plate, pale linen and a subtle burgundy napkin accent. Natural appetizing textures, softly painterly realism, restrained cream, wheat-gold, sage, and deep burgundy palette, diffuse daylight, clean background, card-ready 3:2 horizontal composition. No wine, no alcohol, no bottles, no people, no hands, no cutlery, no flags, no text, no typography, no logo, no watermark.
```

### Чуду с зеленью и сыром

- File: `public/dishes/chudu-s-zelenyu-i-syrom.webp`.
- Dimensions: 640 by 400 pixels.
- SHA-256: `56b4476661616cd0563c35856ff38735c4b9d876b2268f5e5417845014c51a75`.
- Original generated file: `exec-e839c976-d9d2-43ec-a8c3-f6c545afab4c.png`.
- Prompt:

```text
Create a polished editorial food illustration for a Russian regional cuisine wine-pairing website dish card. Exact dish: "Чуду с зеленью и сыром" from Dagestani cuisine — a thin round pan-cooked flatbread, folded into a half-moon and cut to reveal a generous filling of finely chopped fresh herbs and crumbly white cheese; lightly browned spots, brushed with a small amount of butter. It must look thin and flat, not like khachapuri, pizza, a puffy pie, or a dumpling. Three-quarter overhead view on a simple warm ivory ceramic plate, pale linen and a subtle burgundy napkin accent. Natural appetizing textures, softly painterly realism, restrained cream, wheat-gold, leafy green, and deep burgundy palette, diffuse daylight, clean background, card-ready 3:2 horizontal composition. No wine, no alcohol, no bottles, no people, no hands, no cutlery, no flags, no text, no typography, no logo, no watermark.
```

### Халюж с адыгейским сыром

- File: `public/dishes/khalyuzh-s-adygeiskim-syrom.webp`.
- Dimensions: 640 by 400 pixels.
- SHA-256: `e8ce6491681e0da6a1227098757c18b14f09bd915c9b398c9d01f061fd0c1e0b`.
- Original generated file: `exec-42780de6-72b9-4008-bf1d-eebee18ed529.png`.
- Prompt:

```text
Create a polished editorial food illustration for a Russian regional cuisine wine-pairing website dish card. Exact dish: "Халюж с адыгейским сыром" from Adyghe cuisine — several small crescent-shaped fried pastries with delicate blistered golden dough; one pastry is cut open to show a simple white Adyghe cheese filling with a few green herb flecks. Do not depict chebureki with meat, dumplings, empanadas, or khachapuri. Three-quarter overhead view on a simple warm ivory ceramic plate, pale linen and a subtle burgundy napkin accent. Natural appetizing textures, softly painterly realism, restrained cream, wheat-gold, sage, and deep burgundy palette, diffuse daylight, clean background, card-ready 3:2 horizontal composition. No wine, no alcohol, no bottles, no people, no hands, no cutlery, no flags, no text, no typography, no logo, no watermark.
```

## Progressive Web App icon

- Source: `../assets/product-logo-640x640.png` and `../assets/product-logo-640x640.svg`.
- Design: a wine bottle with a question mark inside scanner marks.
- `public/icons/product-logo.svg` is an exact copy of the shared SVG. The favicon, header, and age gate use this file.
- `ProductBrand` displays the shared artwork beside the `Что за вино?` name. Both themes preserve the source artwork colors.
- The 192 by 192 and 512 by 512 install icons are resized from the shared PNG.
- The maskable icon places a 400 by 400 copy of the shared PNG in the center of a 512 by 512 `#fff8ea` canvas.
- The Apple touch icon is a 180 by 180 export of the shared PNG.
- Shared PNG SHA-256: `ebff41f926b210d6ae22250e0ff7e5eb2ff5a680b227cef59208e3f1fc028729`.
- Shared and public SVG SHA-256: `97153903dba33b7c19b9722fb19aab0da39dedd2ab1f27fbd125a15c2f42d49b`.

## Manifest screenshots

- Source: Playwright screenshots of `https://chtozavino.ru/` in the light theme on 2026-09-29.
- The capture confirmed the age gate in advance, so the gate does not appear in the screenshots.
- The screenshots show only the home page of this project with the local copies of the source portal assets.
- `public/screenshots/home-narrow.jpg`: 432 by 768 CSS pixels at scale 2.5, 1080 by 1920 pixels, JPEG quality 84, SHA-256 `6380bfedba98d305bfcedb9b3d9bc478d1b59ad8e38fd6292021409dcdf13d3c`.
- `public/screenshots/home-wide.jpg`: 1280 by 800 CSS pixels at scale 1.5, 1920 by 1200 pixels, JPEG quality 84, SHA-256 `211710c6fff44d2ef2c4688869a1d55a4f5da6efc9cfbb22c8f1b830d0f5d24f`.
- Capture new screenshots when the home page layout changes.

## Hackathon landing screenshots

- Source: Playwright captures of the current local WebApp at `http://127.0.0.1:8154/` on 2026-09-29.
- The captures use the light theme and confirmed age state. They show the current `Что за вино?` header.
- `public/screenshots/hackaton/web-desktop.jpg`: 1280 by 880 CSS pixels at scale 1.5, 1920 by 1320 pixels, JPEG quality 86, SHA-256 `89d9c8acd8f8292ecf33c02c9bf8c29756b2175c0a978f55307b406cb4cf5ca2`.
- `public/screenshots/hackaton/web-mobile.jpg`: 432 by 864 CSS pixels at scale 2.5, 1080 by 2160 pixels, JPEG quality 86, SHA-256 `94ab2b8d6378a75d8099039457d073c417f0df15486212f7dda56f1df30c8476`.
- The `/hackaton` page reuses `public/screenshots/android/04_recognition_result_dark.webp` from the verified Android screenshot set.
- The Telegram panel is an HTML illustration of the documented bot flow. It is not a screenshot or a recorded recognition result.

## Catalog

The fixture has 12 wines. It is a demo subset.
See `catalog-provenance.json` for field sources.
Ratings and sugar categories were observed on the catalog page on 2026-09-15.
Descriptions come from the official CSV where available.
The source alcohol value `108%` for `muskat-ottonel-gusev` is invalid. The UI omits it.

## Shelf example

- Source: the project owner supplied four photographs on 2026-09-29.
- The fourth photograph was a byte-for-byte duplicate of the first photograph. The repository stores one copy.
- The conversion reduced each unique photograph to 2560 by 1928 pixels.
- The conversion used WebP quality 86 and removed embedded metadata.
- `public/reference/shelf-example-abrau-close.webp`: SHA-256 `2bec4ea50d91f40778cf74a347b27196523a061723135c18d07c0e84adb0dc1a`.
- `public/reference/shelf-example-abrau-wide.webp`: SHA-256 `825aba3b4c122f56fed2467c4e50bb36a5c51d8b3c35e115f17042ed03f52dc8`.
- `public/reference/shelf-example-sparkling-display.webp`: SHA-256 `530b8026aadd2327000afec44b618514d8b74cce0847c57ca0fed6d7a2555983`.

The UI lets the visitor select any of the three unique photographs.
The selected photograph uses the normal group-match route.
