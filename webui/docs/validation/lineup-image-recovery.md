# Missing bottle-image validation

Date: 2026-10-16.
Scope: all 11 producer maps and all 647 product nodes.

## Result

Every current product has a local bottle image and a measured image frame.
The check restores 11 empty image slots. It retains the bytes of all 636 existing images.
Derbent Vino, Fanagoria and Massandra each receive one image. Zolotaya Balka receives eight images.
All product identities, wine_slug values, descriptions, grapes and groups remain unchanged.
Derbent Vino has one new badge. The badge identifies the conflict between the official page caption and its bottle label.

## Sources and transformations

Each changed producer has an `image-recovery.json` manifest.

| Producer | Final assets | Sources and exact prompts |
| --- | --- | --- |
| Derbent Vino | [Images](../../public/product-line-maps/derbent-vino/) | [Manifest](../product-line-maps/derbent-vino/image-recovery.json) |
| Fanagoria | [Images](../../public/product-line-maps/fanagoria/) | [Manifest](../product-line-maps/fanagoria/image-recovery.json) |
| Massandra | [Images](../../public/product-line-maps/massandra/) | [Manifest](../product-line-maps/massandra/image-recovery.json) |
| Zolotaya Balka | [Images](../../public/product-line-maps/zolotaya-balka/) | [Manifest](../product-line-maps/zolotaya-balka/image-recovery.json) |

The manifests record exact official product pages, source image URLs, input hashes and output hashes.
Nine images use the built-in imagegen tool for background extraction.
The Fanagoria and Massandra sources already have transparent backgrounds. Their preparation uses alpha-preserving resize and WebP encoding.
All 11 images receive measured frame geometry. No bottle is stretched or clipped.
Two rejected Zolotaya Balka rose edits kept a halo. The accepted edit uses the original small photo.
Generated fine print and reflections can differ from the original. Use the official source for product facts.

## Checks

- Decode all 647 files. Match source dimensions to each JSON frame.
- Confirm that the alpha outline is inside the frame.
- Confirm that all 11 new bottles occupy at least 96% of each normal image-height slot.
- Compare all 636 previous asset hashes with the previous Git revision.
- Compare all product facts with the previous Git revision.
- Inspect all 11 new images on flat light and dark backgrounds.
- Pass 233 unit tests in 16 files with the full catalog snapshot enabled.
- Pass the production build.
- Pass 44 browser cases in Chromium and 44 browser cases in WebKit.
- Decode every product-node image in every browser case. Check 5,176 node renderings.
- Open the restored product details in 88 desktop or mobile cases.
- Check 320 px and 390 px mobile widths, 1440 px desktop width, and light and dark themes.
- Verify served bytes, Content-Length and HTTP 200 for all 11 new assets in both engines.

Mobile checks use browser emulation. No physical-device check is claimed.
Read `lineup-image-recovery.json` for the results.
Ignored visual evidence is in `reports/lineup-image-recovery/`.

## Repeat

Set `PRODUCT_LINE_CATALOG_SNAPSHOT` to the recorded full snapshot. Run `npm test` and `npm run build`.
Run `npm run test:producer-maps` with `PORTAL_ORIGIN=http://127.0.0.1:18553` and the installed Playwright module.
Set `SHARP_MODULE` and run `node scripts/measure-product-image-frames.mjs` to measure the source outlines again.
Inspect recovered images in every changed producer's map. Block one image request to verify the labeled failure placeholder.
