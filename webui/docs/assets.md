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

- Source: the project owner supplied four photographs on 2026-09-29.
- The fourth photograph was a byte-for-byte duplicate of the first photograph. The repository stores one copy.
- The conversion reduced each unique photograph to 2560 by 1928 pixels.
- The conversion used WebP quality 86 and removed embedded metadata.
- `public/reference/shelf-example-abrau-close.webp`: SHA-256 `2bec4ea50d91f40778cf74a347b27196523a061723135c18d07c0e84adb0dc1a`.
- `public/reference/shelf-example-abrau-wide.webp`: SHA-256 `825aba3b4c122f56fed2467c4e50bb36a5c51d8b3c35e115f17042ed03f52dc8`.
- `public/reference/shelf-example-sparkling-display.webp`: SHA-256 `530b8026aadd2327000afec44b618514d8b74cce0847c57ca0fed6d7a2555983`.

The UI lets the visitor select any of the three unique photographs.
The selected photograph uses the normal group-match route.
