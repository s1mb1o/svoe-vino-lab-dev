# Koktebel product line sources

Checked on 2026-10-16. The map includes all 26 snapshot cards whose producer equals `ЗМВ Коктебель`. Each card has one node. Aliases are empty. The original descriptions and grapes are preserved. No numeric slug suffix supplies alcohol, price, vintage, volume, or aging.

## Collection evidence

[The official catalog](https://vinokoktebel.ru/catalog/) lists current collections. Four pages were checked. The current site does not cover every saved snapshot package.

- The saved labels confirm `CASA` for Bastardo, Grand Cuvee, Merlot, and Chardonnay. The fifth card explicitly names Casa white blend. These cards use one group. The labels state oak and bottle aging. The group does not assume one common aging duration.
- The saved labels confirm `Драгоценности` for Pinot Gris, both Rkatsiteli cards, and Traminer. Each inspected label states eight years in oak and a limited release. The four snapshot cards remain separate. Their labels are primary evidence.
- The [official catalog](https://vinokoktebel.ru/catalog/) groups Blanc Aligote, Orange Rkatsiteli, Rose Merlot, and Rouge Ruby Magarach under `Магнетизм`. [The Rouge page](https://vinokoktebel.ru/catalog/index.php?ELEMENT_ID=409&SECTION_ID=) confirms the collection.
- [The Madeira page](https://vinokoktebel.ru/catalog/index.php?ELEMENT_ID=419&SECTION_ID=) and saved labels confirm `1879` for Madeira and the two ports.
- `Атмосфера` is explicit in five snapshot names.
- `Десертные вина` and `Выдержанные игристые` are navigation groups. They do not claim an official collection identity. Kagor remains separate.

The tier order is editorial. The two higher tiers use explicit aging and release evidence. Other groups use the neutral tier. No numeric prices are asserted. The official site shows zero-ruble placeholders. Those placeholders are not retail prices.

## Verified additions

1. [Geometry Pinot Gris](https://vinokoktebel.ru/catalog/index.php?ELEMENT_ID=628&SECTION_ID=) is white dry wine in a 0.75 L bottle.
2. [Planerskoe Traminer](https://vinokoktebel.ru/catalog/index.php?ELEMENT_ID=463&SECTION_ID=) is white semi-sweet wine in a 1.5 L bottle.

The snapshot Pinot Gris and Traminer belong to Precious dessert wines. They do not identify either addition. The additional nodes have null wine slugs. The crosswalk has exact source and image URLs. The product names include both the wine identity and the verified bottle volume. The variant fields are empty. This keeps the wine identity visible on map tiles.

This map covers the full snapshot plus two verified additions. It does not claim every current official product. The Geometry Kokur page was rejected as an addition because its title and characteristics conflict on color and sweetness. No conflicting facts from that page enter the map.

## Assets and retrieval limits

The initial import copied the 26 existing WebP assets without change. The crosswalk preserves their source evidence. The current official-image derivatives are documented below. Original asset bytes remain in Git revision `89aa3780`.

The website certificate did not validate in the local Python certificate store. Public catalog files were read with a per-request certificate-check exception. No credentials, cookies, or private data were sent. Web search independently indexed the official product pages.

## Background extraction, 2026-10-16

2 display images use transparent cutouts from the built-in `image_gen` tool.
Read [imagegen-cutouts.json](imagegen-cutouts.json) for every exact prompt, source hash, generated PNG hash, output hash, and review note.
The review checks product identity, main label text, cap, color, and artwork at the UI display size.
Imagegen resamples fine print and reflections. The generated images are not evidence for label microtext.
The product facts remain sourced from the catalog and official pages.
The final frame excludes faint transparent outliers. The conversion preserves alpha and fits the cropped image into 720 px height before padding.
The WebP quality is 88. The alpha quality is 100. Each file has 6 px transparent padding.
Unedited images retain their previous bytes. Original edited-image bytes remain in Git revision `89aa3780`.
