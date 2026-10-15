# Product image background extraction

Date: 2026-10-16.
Branch: `product-line-map`.
Source asset revision: `89aa3780`.
Local origin: `http://127.0.0.1:18553`.

## Scope and result

The audit checked 638 referenced images across eleven producer maps.
84 images had a background. These images contained 83 unique source hashes.
The built-in `image_gen` tool produced 82 accepted display cutouts from 81 unique source images.
One pair of byte-identical source images reuses one generated result.
Two source photos do not establish the required product package. Those nodes use the existing labeled placeholder.
The maps now reference 636 image files. Eleven products use a placeholder.
Product IDs, groups, wine slugs, recognized selection, and portal link rules are unchanged.

| Producer | Edited files | New placeholders | Exact prompts and hashes |
| --- | ---: | ---: | --- |
| Дербент Вино | 5 | 1 | [Manifest](../product-line-maps/derbent-vino/imagegen-cutouts.json) |
| Кубань-Вино | 50 | 0 | [Manifest](../product-line-maps/kuban-vino/imagegen-cutouts.json) |
| Фанагория | 14 | 1 | [Manifest](../product-line-maps/fanagoria/imagegen-cutouts.json) |
| Золотая Балка | 10 | 0 | [Manifest](../product-line-maps/zolotaya-balka/imagegen-cutouts.json) |
| Alma Valley | 1 | 0 | [Manifest](../product-line-maps/alma-valley/imagegen-cutouts.json) |
| ЗМВ Коктебель | 2 | 0 | [Manifest](../product-line-maps/koktebel/imagegen-cutouts.json) |

Files remain under `public/product-line-maps/<producer>/` at their original URLs.
Each crosswalk records the original input hash and the new output hash.
The generated PNG hash identifies the selected imagegen output.
Original asset bytes remain in Git. The source catalog snapshot is unchanged.

## Method and limits

The user selected imagegen. SAM3 was not used.
Each distinct source image had its own built-in tool call.
Prompts requested background extraction, actual transparency, and unchanged bottle identity.
Review compared the main brand, grape, vintage, cap, colors, and label artwork at the UI size.
Outputs with a wrong main label were rejected and retried.
Imagegen resamples fine print and reflections. The result is not pixel-identical to the source.
Generated images MUST NOT be used as evidence for label microtext or QR codes.
The two accepted 5000 images reconstruct small base regions that rocks covered in the source photos.

Faint transparent outliers can leave an excessively wide image frame.
A frame from alpha values of at least 128 removes these outer fields from the crop calculation.
The crop adds 8 source pixels around that frame. The crop does not change alpha values inside the frame.
The conversion fits the cropped image into 720 px height. The conversion adds 6 px transparent padding on every side.
WebP uses quality 88 and alpha quality 100. The 82 files total 2,149,084 bytes.
This conversion preserves the generated alpha and reduces mobile transfer size.

## Rejected source photos

`fanagoria/wine-ona-skazala-da` had a wedding scene with several bottles labeled WEDDING Bliss.
The scene does not establish the exact wine package. The catalog link remains available.

The [official 5000 page](https://derbentwine.ru/catalog/spetsproekt/5000/) captions the red product as Cabernet Sauvignon.
Its supplied bottle image reads Cabernet Franc.
`derbent-vino/official-5000-cabernet-sauvignon` retains the official product name and uses the image placeholder.
The crosswalk retains the original image URL and hash. No false label was generated for this product.

## Verification

- 231 tests passed with the full catalog snapshot.
- Type checks passed.
- The production build passed, including map validation in prebuild.
- All 82 output images have alpha values from 0 to 255. All four 6 px borders are fully transparent.
- The independent geometry check found no reduced bottle scale after reframing.
- Monte Garu rose renders at about 171 px in the desktop detail image and 105 px on mobile.
- The final scan found no fully opaque image among the 636 referenced files. High-fill exceptions are tightly framed cans.
- Chromium and WebKit passed 24 screen and interaction cases each, for 48 cases in total.
- Each engine verified server bytes, recorded hashes, image decode, and alpha for all 82 edited files.
- Desktop light theme used 1440 × 1000. Mobile dark theme used 390 × 844.
- Selected products, portal links, mobile popup controls, map position, zoom, and both placeholders passed.
- No broken images, document overflow, browser errors, or hydration errors were observed.
- Read [product-image-cutouts-browser.json](product-image-cutouts-browser.json) for the saved browser summary.

## Reproduction

Read the producer manifests for the exact prompts and selected output hashes.
Open the local producer maps in light and dark themes at desktop and mobile sizes.
Select the edited bottles. Check the canvas, the detail image, and the mobile popup.
Close the popup. Check that selection, map position, and the portal action remain available.
For the two rejected source photos, check the labeled placeholder and the existing link availability rule.
Run the existing registry tests with the full catalog snapshot.
These checks use emulated viewports. No physical device test was performed.

## Winery commits

Each producer has a separate image commit. The branch was not pushed.

| Producer | Commit |
| --- | --- |
| `derbent-vino` | `68ed81d6` |
| `zolotaya-balka` | `7c17cf6b` |
| `alma-valley` | `856b024e` |
| `koktebel` | `bbb06f3a` |
| `fanagoria` | `d6b82dd6` |
| `kuban-vino` | `6565d343` |
