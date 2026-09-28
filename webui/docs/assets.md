# Asset provenance

Date: 2026-09-15.

The user requested the source portal look and feel.
Selected public visual assets are stored locally for this implementation.
Original rights remain with the source owners. This repository does not relicense these assets.
Source application scripts, analytics, and CSS bundles are not included.
The implementation uses its own CSS.

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

## Progressive Web App icon

- Source: `svoe-vino-lab/telegram-bot/assets/botpic.svg` and `botpic.png` in this workspace.
- Design: a wine glass and a question mark in burgundy and cream.
- `public/icons/pwa-icon.svg` keeps the source vector paths and colors.
- The 192 by 192 and 512 by 512 icons are direct exports of the 1024 px bot icon.
- The maskable icon scales the mark to the central safe area on a solid cream background.
- The Apple touch icon uses the same solid cream background.

## Catalog

The fixture has 12 wines. It is a demo subset.
See `catalog-provenance.json` for field sources.
Ratings and sugar categories were observed on the catalog page on 2026-09-15.
Descriptions come from the official CSV where available.
The source alcohol value `108%` for `muskat-ottonel-gusev` is invalid. The UI omits it.

## Shelf example

- Local file: `public/reference/shelf-example.jpg`.
- Source: [Sekt-im-supermarkt.jpg](https://commons.wikimedia.org/wiki/File:Sekt-im-supermarkt.jpg).
- Author: Ralf Roletschek.
- License: [CC BY 2.5](https://creativecommons.org/licenses/by/2.5/).
- Copy: the public 1280 × 853 Wikimedia thumbnail. No other image edit was applied.
- SHA-256: `ccc6c12e2e2a79976650b86e8c42b4f33c6698022c2e8f25ea3fd5003e940d0e`.

The UI shows author, source, license, and size-change attribution.
The photo shows a German supermarket shelf. It does not establish a Russian wine identity.
The example verifies segmentation. Wine identification remains explicitly mocked.
