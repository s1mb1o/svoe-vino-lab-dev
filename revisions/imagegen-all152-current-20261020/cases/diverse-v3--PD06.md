# main-selector-imagegen-diverse-v3-20261020:PD06

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): Бутылка и бумажный пакет

Reference target description (source): Настоящая бутылка слева от бумажного пакета

Expected intent: `clear`. Accepted target proposals: `d10`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:PD06`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--PD06.png)

![Proposed target overlay](../target-overlays/diverse-v3--PD06.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--PD06-d10.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d58; reason: existing_scene_v1_rank; mode: legacy; crop 462×939 px. Target agreement: False. Target retention proxy: 0.0%; maximum other-bottle retention: 97.4%; minimum associated label retention: 0.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--PD06-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PD06-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--PD06-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d45: 0.0%, 47087 source pixels; d47: 0.0%, 8277 source pixels

### semantic-v2: FAIL — provisional target/proxy

Selected: d58; reason: dominant_foreground_subject; mode: confident; crop 498×1007 px. Target agreement: False. Target retention proxy: 0.0%; maximum other-bottle retention: 100.0%; minimum associated label retention: 0.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d48 100.0%; d49 100.0%.

![semantic-v2 crop](../crops/diverse-v3--PD06-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PD06-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--PD06-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--PD06-semantic-v2-0.png) · [label 2](../label-crops/diverse-v3--PD06-semantic-v2-1.png)

Associated label-mask retention proxies (unreviewed ownership): d45: 0.0%, 47087 source pixels; d47: 0.0%, 8277 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 809×1008 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.9%; maximum other-bottle retention: 100.0%; minimum associated label retention: 98.6%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--PD06-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PD06-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--PD06-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d45: 100.0%, 47087 source pixels; d47: 98.6%, 8277 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--PD06-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--PD06-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--PD06-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--PD06-d3.png) |
| d4 | wine bottle | [PNG](../masks/diverse-v3--PD06-d4.png) |
| d5 | wine bottle | [PNG](../masks/diverse-v3--PD06-d5.png) |
| d6 | wine bottle | [PNG](../masks/diverse-v3--PD06-d6.png) |
| d7 | wine bottle | [PNG](../masks/diverse-v3--PD06-d7.png) |
| d8 | wine bottle | [PNG](../masks/diverse-v3--PD06-d8.png) |
| d9 | wine bottle | [PNG](../masks/diverse-v3--PD06-d9.png) |
| d10 | wine bottle | [PNG](../masks/diverse-v3--PD06-d10.png) |
| d11 | wine bottle | [PNG](../masks/diverse-v3--PD06-d11.png) |
| d12 | wine bottle | [PNG](../masks/diverse-v3--PD06-d12.png) |
| d13 | wine bottle | [PNG](../masks/diverse-v3--PD06-d13.png) |
| d14 | wine bottle | [PNG](../masks/diverse-v3--PD06-d14.png) |
| d15 | wine bottle | [PNG](../masks/diverse-v3--PD06-d15.png) |
| d16 | wine bottle | [PNG](../masks/diverse-v3--PD06-d16.png) |
| d17 | wine bottle | [PNG](../masks/diverse-v3--PD06-d17.png) |
| d18 | wine bottle | [PNG](../masks/diverse-v3--PD06-d18.png) |
| d19 | wine bottle | [PNG](../masks/diverse-v3--PD06-d19.png) |
| d20 | wine bottle | [PNG](../masks/diverse-v3--PD06-d20.png) |
| d21 | wine bottle | [PNG](../masks/diverse-v3--PD06-d21.png) |
| d22 | wine bottle | [PNG](../masks/diverse-v3--PD06-d22.png) |
| d23 | wine bottle | [PNG](../masks/diverse-v3--PD06-d23.png) |
| d24 | wine bottle | [PNG](../masks/diverse-v3--PD06-d24.png) |
| d25 | wine bottle | [PNG](../masks/diverse-v3--PD06-d25.png) |
| d26 | wine bottle | [PNG](../masks/diverse-v3--PD06-d26.png) |
| d27 | wine bottle | [PNG](../masks/diverse-v3--PD06-d27.png) |
| d28 | wine bottle | [PNG](../masks/diverse-v3--PD06-d28.png) |
| d29 | wine bottle | [PNG](../masks/diverse-v3--PD06-d29.png) |
| d30 | wine bottle | [PNG](../masks/diverse-v3--PD06-d30.png) |
| d31 | wine bottle | [PNG](../masks/diverse-v3--PD06-d31.png) |
| d32 | wine bottle | [PNG](../masks/diverse-v3--PD06-d32.png) |
| d33 | wine bottle | [PNG](../masks/diverse-v3--PD06-d33.png) |
| d34 | wine bottle | [PNG](../masks/diverse-v3--PD06-d34.png) |
| d35 | wine bottle | [PNG](../masks/diverse-v3--PD06-d35.png) |
| d36 | wine bottle | [PNG](../masks/diverse-v3--PD06-d36.png) |
| d37 | wine bottle | [PNG](../masks/diverse-v3--PD06-d37.png) |
| d38 | wine bottle | [PNG](../masks/diverse-v3--PD06-d38.png) |
| d39 | wine bottle | [PNG](../masks/diverse-v3--PD06-d39.png) |
| d40 | wine bottle | [PNG](../masks/diverse-v3--PD06-d40.png) |
| d41 | wine bottle | [PNG](../masks/diverse-v3--PD06-d41.png) |
| d42 | wine bottle | [PNG](../masks/diverse-v3--PD06-d42.png) |
| d43 | wine bottle | [PNG](../masks/diverse-v3--PD06-d43.png) |
| d44 | wine bottle | [PNG](../masks/diverse-v3--PD06-d44.png) |
| d45 | wine label | [PNG](../masks/diverse-v3--PD06-d45.png) |
| d46 | wine label | [PNG](../masks/diverse-v3--PD06-d46.png) |
| d47 | wine label | [PNG](../masks/diverse-v3--PD06-d47.png) |
| d48 | wine label | [PNG](../masks/diverse-v3--PD06-d48.png) |
| d49 | wine label | [PNG](../masks/diverse-v3--PD06-d49.png) |
| d50 | box | [PNG](../masks/diverse-v3--PD06-d50.png) |
| d51 | box | [PNG](../masks/diverse-v3--PD06-d51.png) |
| d52 | box | [PNG](../masks/diverse-v3--PD06-d52.png) |
| d53 | box | [PNG](../masks/diverse-v3--PD06-d53.png) |
| d54 | box | [PNG](../masks/diverse-v3--PD06-d54.png) |
| d55 | box | [PNG](../masks/diverse-v3--PD06-d55.png) |
| d56 | box | [PNG](../masks/diverse-v3--PD06-d56.png) |
| d57 | box | [PNG](../masks/diverse-v3--PD06-d57.png) |
| d58 | box | [PNG](../masks/diverse-v3--PD06-d58.png) |
| d59 | box | [PNG](../masks/diverse-v3--PD06-d59.png) |
| d60 | box | [PNG](../masks/diverse-v3--PD06-d60.png) |
| d61 | wine glass | [PNG](../masks/diverse-v3--PD06-d61.png) |
| d62 | wine glass | [PNG](../masks/diverse-v3--PD06-d62.png) |
| d63 | wine glass | [PNG](../masks/diverse-v3--PD06-d63.png) |

[Raw frozen detector response](../detections/diverse-v3--PD06.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate exactly ONE independent candid smartphone photograph. Show believable glass, paper, natural material imperfections, fictional wine branding, and anatomically plausible hands. No collage, grid, arrows, annotations, bounding boxes, highlights, watermark, UI overlay, or explanatory caption. Text is allowed on physical objects within the scene. Keep the target visible front label entirely inside the frame unless partial occlusion or close-up is explicitly requested. Image format: landscape 3:2, approximately 1536 by 1024 pixels. Setting: inside a real wine cellar. Use stone or brick walls, wooden wine racks, storage cubbies, a cellar tasting table and practical dim lights. Keep the described foreground inventory; background racks may be empty or softly blurred. Scene details: One real green wine bottle with blue label stands LEFT. Beside it at RIGHT is a tall kraft paper bag with a large printed photograph of a bottle, visible paper handles, folds and side gusset. The printed bottle is visually larger. No hands, physical bottle separate from bag.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Винный погреб. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
