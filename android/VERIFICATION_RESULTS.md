# Model and vector verification

Date: 2026-09-28

## Result

The verification passed.
The Android LiteRT model and the GX10 timm model produce compatible vectors when they
use the same timm image preprocessing.
The two 2026-09-28 catalogue snapshots contained 2,271 finite 768-dimensional vectors
and zero failures.

The Android model-pack pipeline ID is `dis-white-square-timm-crop090-v2`.
The application and the model-pack builder reject a different pipeline or model file.

## Model identity

| Component | Repository | Revision | Verified file SHA-256 |
|---|---|---|---|
| GX10 SigLIP2 | `timm/vit_base_patch16_siglip_224.v2_webli` | `4c3661e5ac879a276ddc5ddc6d3f0ecc78fd5d82` | The Hugging Face revision identifies the weights. |
| Android SigLIP2 | `litert-community/SigLIP2-base-patch16-224` | `509b5cbcf1a849f37696be08f8297c6cd3050bf4` | `a30ebb7b3ee15eaa68a18f9ab6a2ed740c15c343d25d898dc482317473320854` |
| Android DIS | `litert-community/DIS-ISNet-LiteRT` | `1b966dbe2f33bd5ca1299cf94fbab59265210b6b` | `0c3c93b6a2a65e7c69137ec82596944e6bfb97d982c75bab03acb0738dbaa087` |

The SigLIP2 LiteRT input shape is `[1, 3, 224, 224]`.
The output shape is `[1, 768]`.
The GX10 service used float32 on CUDA.
The comparison used LiteRT 2.2.0 on CPU.

## Catalogue build results

| Workbench entry | Vectors | Failures | Shape | Vector norm range | Time |
|---|---:|---:|---|---|---:|
| `android-siglip2-base-224-dis-white` | 2,271 | 0 | `[2271, 768]` float32 | 0.99999988 to 1.00000012 | 3,832.6 s |
| `android-siglip2-base-224-sam3-white` | 2,271 | 0 | `[2271, 768]` float32 | 0.99999982 to 1.00000012 | 282.1 s |

The DIS vector file is `vectors-657a9232.npy`.
Its SHA-256 is
`657a923256823807a4c2a7986177c81927eb2ff28e3c7f50de202cb8f15e0e5f`.
The DIS `index.json` SHA-256 is
`8ee2145f9fb95ba8392dadc38bbfdc2c0c6f39180f54a365560557a27d019115`.
The SAM3 vector file is `vectors-19d44e9a.npy`.
Its SHA-256 is
`19d44e9a9c205257f0e97de3907c943997c6d3eb794a64f7e7d490a0c8c0903a`.
The SAM3 `index.json` SHA-256 is
`1d676da18d8da68b313f19f8811adb9355fd472ee710e3d02217a1dc92347edb`.

## Vector comparison

The test selected 32 evenly spaced rows from each completed index.
It ran the same prepared PNG through the Android SigLIP2 LiteRT file.
It compared the normalized LiteRT vector with the saved GX10 vector by cosine.
The recorded pass threshold was a minimum cosine of 0.99999.

| Workbench entry | Minimum | Mean | Maximum | Result |
|---|---:|---:|---:|---|
| `android-siglip2-base-224-dis-white` | 0.99999851 | 0.99999954 | 0.99999994 | PASS |
| `android-siglip2-base-224-sam3-white` | 0.99999905 | 0.99999963 | 0.99999988 | PASS |

The timm processor uses `crop_pct=0.9`.
For the saved 224 by 224 PNG, it resizes to 248 by 248 pixels and takes the centered
224 by 224 crop.
The Android encoder now applies the same operation.

A control test omitted this operation.
The control did not match the catalogue vectors.
The DIS control had cosine 0.85844940 minimum and 0.92879066 mean.
The SAM3 control had cosine 0.81030792 minimum and 0.91484264 mean.
This control found the preprocessing mismatch before the Android change.

Use this command to repeat the comparison:

```text
python3 tools/verify_model_vectors.py \
  --index ../workbench/data/catalog/embeddings/<entry>/index.json \
  --model /path/to/siglip2_base_224_fp16.tflite \
  --sample-size 32
```

## Automated checks

- The 75 focused workbench tests passed.
- `./gradlew lintDebug` passed.
- `./gradlew test assembleDebug` passed.
- Three model-pack builder tests passed.
- The debug and release variants each passed three catalogue tests and three DIS mask
  tests.

## Built-in DIS pack

Date: 2026-09-29

The refreshed `android-siglip2-base-224-dis-white` index has 2,270 current vectors and
zero failures.
The vector file is `vectors-ade2a70e.npy`.
Its SHA-256 is
`ade2a70ee267100eec76154155949a03b20a34311ff53eaa585512cda5fdaefc`.
The `index.json` SHA-256 is
`fe36733699bc9e436b6fc64d0efa29d6a305851c0807033a8351a89a2762a2d0`.

The Android selection contains 2,093 active wines.
It contains one vector and one selected catalogue image for each included wine.
The selection contains 23 `main_patched` images and 2,070 `main` images.
Five active wines have no eligible image and were omitted.

The omitted wines are:

- `polusladkoe-krasnoe-zb-vajn-frizzante`
- `polusladkoe-krasnoe-zolotaya-balka`
- `polusuhoe-rozovoe-zb-vajn-frizzante`
- `suhoe-beloe-zb-vajn-frizzante`
- `vibes-silvaner-barrel-fermented-2022`

The generated format version 2 pack has these properties:

- Pack size: 531,950,661 bytes.
- Pack SHA-256:
  `da8a079c5e599c663e3a844d743af5103a9b8b896aa15f1660f07c1cdea56684`.
- Vector payload SHA-256:
  `b1201937b4df6069177221be85ba70d1f2bd08c3c2644ec7caa781363a451ff5`.
- Vector shape: `[2093, 768]` float32.
- Vector norm range: 0.99999988 to 1.00000012.
- Catalogue image count: 2,093.
- Local code relation count: 135.

Five Python pack-builder tests passed.
The debug and release variants each passed four catalogue index tests, three DIS mask
tests, and four SigLIP2 vector tests.
`lintDebug`, `test`, and `assembleDebug` passed.
The debug APK contains the pack as an uncompressed asset.

## Physical Android correction verification

Date: 2026-09-29

The owner reproduced `SigLIP2 вернул пустой вектор` on the arm64 Android 14 phone.
The new output validation found a non-finite GPU result.
The application retried the same SigLIP2 input on CPU.
The CPU output was valid.

The test used the catalogue image for
`a-gordienko-m-nikolaev-pino-nuar-krasnoe-suhoe-135`.
The best result was the source wine `Пино Нуар` at cosine 0.910.

The first corrected run reported these times:

- DIS GPU: 6,444 ms.
- SigLIP2 GPU failure and CPU retry: 11,780 ms.
- Local search: 947 ms.

The repeated run disabled the SigLIP2 GPU attempt in the same process.
It reported these times:

- DIS GPU: 6,307 ms.
- SigLIP2 CPU: 2,920 ms.
- Local search: 236 ms.

The settings page showed the pack version and both 2,093 counts.
The main screen showed compact icon buttons for camera and gallery.
The main screen did not show a model-pack replacement action.

Google Code Scanner opened successfully.
It showed the manual-input action.
The catalogue unit test confirmed that EAN-13 `4631168664979` resolves the stored
GTIN-14 `04631168664979`.
A physical camera scan of an EAN-13 code remains pending.

## Per-model accelerator and launcher verification

Date: 2026-09-29

The application version is `0.1.2` with version code 3.
The application tests DIS and SigLIP2 separately on the first start.
The settings page provides `Авто`, `GPU`, and `CPU` for each model.
The application saves the settings and the automatic selections.

The Realme RMX3890 runs Android 14.
Its first automatic check selected these accelerators:

- DIS: GPU.
- SigLIP2: CPU.

The settings page showed both automatic selections.
The DIS setting saved an explicit CPU selection.
The DIS setting saved `Авто` again after the test.

A complete run in `Авто` mode used the catalogue image for
`a-gordienko-m-nikolaev-pino-nuar-krasnoe-suhoe-135`.
The best result was `Пино Нуар` at cosine 0.910.
The run reported these times:

- DIS GPU: 6,454 ms.
- SigLIP2 CPU: 3,027 ms.
- Local search: 201 ms.

The launcher icon uses the shared `assets/product-logo-640x640.png` artwork.
The APK contains adaptive, round, and fallback launcher resources.

The debug and release variants each passed these unit tests:

- Four accelerator-selection tests.
- Four catalogue index tests.
- Four DIS mask tests.
- Four SigLIP2 vector tests.

`lintDebug`, `test`, and `assembleDebug` passed.
The final debug APK size is 576,832,975 bytes.
Its SHA-256 is
`173ee058ad5681242d275a9fb0bb6a28035fd0f261df30323ff44ca269d2f980`.

The Google Pixel 8 has serial `41231FDJH002WZ`.
It runs Android 17 at API level 37.

The phone had 1.2 GB of free data storage before installation.
The 576,832,975-byte production APK did not install.
Standard and incremental installation both returned
`INSTALL_FAILED_INSUFFICIENT_STORAGE`.

The device test used a compact format version 2 pack.
The pack kept these production artifacts without a change:

- The verified DIS model file.
- The verified SigLIP2 model file.
- The `Пино Нуар` catalogue vector.
- The `Пино Нуар` catalogue image.

The pack had one vector, one wine, and one image.
Its size was 361,695,609 bytes.
Its SHA-256 was
`3fc21f173b4a90453d08342ce6584f62635df2b66e1476154cff2d9fc764de17`.
The test APK size was 406,246,869 bytes.
Its SHA-256 was
`d40d80d39bf56c53c1b139516acd777f16c085bb821cfc0ef1c9d54294ba5431`.

The first-start check selected these accelerators:

- DIS: GPU.
- SigLIP2: GPU.

The application saved both selections.
The selections remained after an application restart.
The application did not repeat the automatic check after the restart.

The complete image pipeline matched `Пино Нуар` at cosine 0.909.
The run reported these times:

- DIS GPU: 2,546 ms.
- SigLIP2 GPU: 2,287 ms.
- One-vector local search: 2 ms.

The debug section showed the DIS mask, crop, and white-background image.
The temporary test application and image were removed from the Pixel 8 after the test.

## Version 0.1.3 interface and history verification

Date: 2026-09-29

The debug APK has version code 4 and version name 0.1.3.
The distribution file is `chtozavino_debug.apk`.
Its size is 576,503,277 bytes.
Its SHA-256 is
`be7a24ca7db3d182a87c931b6c7d154f69892e28735e7f211a45e4650f55a828`.

The Realme RMX3890 kept its application data during the version update.
The history preferences file contained an empty map before the new recognition.
The empty map was written when the earlier device-test rows were cleared.

The new test used the same `Пино Нуар` catalogue image.
The result score was 0.9097248.
The result page showed `Сходство: 91%`.
The application added a persistent history row.
The history page showed `Фото · сходство 91%`.
The history page showed the same row after an application restart.

The main page showed the new recognition and history vector icons at 30 dp.
The main page showed `Не требует интернета`.
The settings page showed version 0.1.3 and `Сайт «Что за вино?»`.

The phone used the light system theme before the test.
The application used its dark color scheme after the system changed to dark mode.
The application used its light color scheme after the original system setting was
restored.

`lintDebug`, debug and release unit tests, and `assembleDebug` passed.
Each variant passed two new similarity-format tests.

## Lowercase application ID verification

Date: 2026-09-29

The debug APK has application ID `chtozavino.alolalab.com`.
It has version code 5 and version name 0.1.4.
Its size is 576,503,269 bytes.
Its SHA-256 is
`e22d166c8922936dd75acb63ec0b860334ef982caf5bbde36c5bb5c079227c26`.

The Pixel 8 did not contain `Chtozavino.alolalab.com` before installation.
The full APK installed on the Pixel 8.
The Pixel 8 had 6.1 GB of free data storage before installation.
The installed private files use approximately 667 MiB.
The installed pack has 2,093 images, 2,093 wines, and 2,093 vectors.
The installed image directory contains 2,093 files.
The automatic accelerator check selected GPU for DIS and SigLIP2.
The application process stayed active and no application crash was present in logcat.

The owner unlocked the Pixel 8 after installation.
The direct UI verification then completed.
The main page showed `Не требует интернета` and both automatic GPU selections.

The full recognition used the `Пино Нуар` catalogue image.
The best result was `Пино Нуар` at `Сходство: 91%`.
The run reported these times:

- DIS GPU: 2,463 ms.
- SigLIP2 GPU: 2,134 ms.
- Local search: 100 ms.

The debug section showed the DIS mask.
The history page showed `Фото · сходство 91%`.
The history row stayed after an application restart.

The history result opened this exact URL in Chrome:
`https://vino-svoe.ru/wines/a-gordienko-m-nikolaev-pino-nuar-krasnoe-suhoe-135`.
The Chrome address bar showed the same wine path.

The settings page showed these values and controls:

- Pack version `20260929-dis-main`.
- 2,093 images and 2,093 wines.
- Selected `Авто` controls for DIS and SigLIP2.
- Automatic selections DIS GPU and SigLIP2 GPU.
- The `Проверить GPU снова` action.
- Application version 0.1.4.
- The `Сайт «Что за вино?»` link.

The complete settings page rendered correctly in the Pixel 8 dark system theme.
The product-site link opened `https://vino-svoe.ru` in Chrome.
The Chrome address bar showed `vino-svoe.ru`.

The Realme contained `Chtozavino.alolalab.com` before cleanup.
The old package was removed from the Realme.
This removal also removed the old local application data.
The unrelated `com.alolalab.storagetracker*` packages stayed unchanged.

`lintDebug`, debug and release unit tests, and `assembleDebug` passed.

## Scope limit

The vector comparison used the LiteRT CPU interpreter on macOS.
It verified the model artifact, tensor shapes, normalization, and preprocessing.
The 32-image vector comparison did not run on a physical Android device.
The physical device tests used one catalogue image.
The Realme test found an invalid GPU SigLIP2 result and verified the CPU recovery path.
The Pixel 8 test verified successful GPU inference for both models.
The Pixel 8 test used a one-vector catalogue because the full APK did not fit in the
available storage.

## Workbench recognition comparison

Date: 2026-09-29

The workbench ran the permanent DIS and SAM3 pipelines on all 2,226 queries of `my`.
Both final runs used the same query bytes and the same catalogue coverage.
Each refreshed index had 2,270 current items and covered 2,093 wines.
Barcode was absent from both pipelines.

SAM3 reached 49.91% positive R@1 and 79.36% positive R@5.
DIS reached 43.05% positive R@1 and 73.10% positive R@5.
The SAM3 R@1 gain was 6.86 percentage points.
The paired exact McNemar p-value was `9.013745e-09`.

DIS rejected 84.97% of negative queries at rank 1.
SAM3 rejected 82.90%.
This difference was not statistically significant (`p=0.218518`).

DIS returned no foreground for five queries that represent four unique images.
SAM3 returned no error.

Read the full [DIS and SAM3 comparison](../workbench/docs/reports/2026-09-29_android-dis-sam3-comparison.md).
