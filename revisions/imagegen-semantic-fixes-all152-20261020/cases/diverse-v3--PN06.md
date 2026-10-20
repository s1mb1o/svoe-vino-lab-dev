# main-selector-imagegen-diverse-v3-20261020:PN06

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--PN06.jpg)

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): Палец рядом с мини-бутылкой

Reference target description (source): Маленькая бутылка слева

Expected intent: `clear`. Accepted target proposals: `d27`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:PN06`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--PN06.png)

![Proposed target overlay](../target-overlays/diverse-v3--PN06.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--PN06-d27.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d2; reason: existing_scene_v1_rank; mode: legacy; crop 276×898 px. Target agreement: False. Target retention proxy: 0.0%; maximum other-bottle retention: 99.7%; minimum associated label retention: 0.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--PN06-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PN06-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--PN06-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d35: 0.0%, 21977 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d27; reason: explicit_pointing_gesture; mode: confident; crop 142×504 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d35 100.0%.

![semantic-v2 crop](../crops/diverse-v3--PN06-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PN06-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--PN06-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--PN06-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d35: 100.0%, 21977 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 982×944 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.4%; maximum other-bottle retention: 99.7%; minimum associated label retention: 99.2%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--PN06-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PN06-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--PN06-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d35: 99.2%, 21977 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--PN06-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--PN06-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--PN06-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--PN06-d3.png) |
| d4 | wine bottle | [PNG](../masks/diverse-v3--PN06-d4.png) |
| d5 | wine bottle | [PNG](../masks/diverse-v3--PN06-d5.png) |
| d6 | wine bottle | [PNG](../masks/diverse-v3--PN06-d6.png) |
| d7 | wine bottle | [PNG](../masks/diverse-v3--PN06-d7.png) |
| d8 | wine bottle | [PNG](../masks/diverse-v3--PN06-d8.png) |
| d9 | wine bottle | [PNG](../masks/diverse-v3--PN06-d9.png) |
| d10 | wine bottle | [PNG](../masks/diverse-v3--PN06-d10.png) |
| d11 | wine bottle | [PNG](../masks/diverse-v3--PN06-d11.png) |
| d12 | wine bottle | [PNG](../masks/diverse-v3--PN06-d12.png) |
| d13 | wine bottle | [PNG](../masks/diverse-v3--PN06-d13.png) |
| d14 | wine bottle | [PNG](../masks/diverse-v3--PN06-d14.png) |
| d15 | wine bottle | [PNG](../masks/diverse-v3--PN06-d15.png) |
| d16 | wine bottle | [PNG](../masks/diverse-v3--PN06-d16.png) |
| d17 | wine bottle | [PNG](../masks/diverse-v3--PN06-d17.png) |
| d18 | wine bottle | [PNG](../masks/diverse-v3--PN06-d18.png) |
| d19 | wine bottle | [PNG](../masks/diverse-v3--PN06-d19.png) |
| d20 | wine bottle | [PNG](../masks/diverse-v3--PN06-d20.png) |
| d21 | wine bottle | [PNG](../masks/diverse-v3--PN06-d21.png) |
| d22 | wine bottle | [PNG](../masks/diverse-v3--PN06-d22.png) |
| d23 | wine bottle | [PNG](../masks/diverse-v3--PN06-d23.png) |
| d24 | wine bottle | [PNG](../masks/diverse-v3--PN06-d24.png) |
| d25 | wine bottle | [PNG](../masks/diverse-v3--PN06-d25.png) |
| d26 | wine bottle | [PNG](../masks/diverse-v3--PN06-d26.png) |
| d27 | wine bottle | [PNG](../masks/diverse-v3--PN06-d27.png) |
| d28 | wine bottle | [PNG](../masks/diverse-v3--PN06-d28.png) |
| d29 | wine bottle | [PNG](../masks/diverse-v3--PN06-d29.png) |
| d30 | wine bottle | [PNG](../masks/diverse-v3--PN06-d30.png) |
| d31 | wine bottle | [PNG](../masks/diverse-v3--PN06-d31.png) |
| d32 | wine bottle | [PNG](../masks/diverse-v3--PN06-d32.png) |
| d33 | wine bottle | [PNG](../masks/diverse-v3--PN06-d33.png) |
| d34 | wine label | [PNG](../masks/diverse-v3--PN06-d34.png) |
| d35 | wine label | [PNG](../masks/diverse-v3--PN06-d35.png) |
| d36 | hand | [PNG](../masks/diverse-v3--PN06-d36.png) |
| d37 | box | [PNG](../masks/diverse-v3--PN06-d37.png) |
| d38 | box | [PNG](../masks/diverse-v3--PN06-d38.png) |
| d39 | box | [PNG](../masks/diverse-v3--PN06-d39.png) |
| d40 | box | [PNG](../masks/diverse-v3--PN06-d40.png) |
| d41 | box | [PNG](../masks/diverse-v3--PN06-d41.png) |
| d42 | box | [PNG](../masks/diverse-v3--PN06-d42.png) |
| d43 | box | [PNG](../masks/diverse-v3--PN06-d43.png) |
| d44 | box | [PNG](../masks/diverse-v3--PN06-d44.png) |
| d45 | box | [PNG](../masks/diverse-v3--PN06-d45.png) |
| d46 | box | [PNG](../masks/diverse-v3--PN06-d46.png) |
| d47 | box | [PNG](../masks/diverse-v3--PN06-d47.png) |
| d48 | box | [PNG](../masks/diverse-v3--PN06-d48.png) |
| d49 | box | [PNG](../masks/diverse-v3--PN06-d49.png) |
| d50 | box | [PNG](../masks/diverse-v3--PN06-d50.png) |
| d51 | box | [PNG](../masks/diverse-v3--PN06-d51.png) |
| d52 | wine glass | [PNG](../masks/diverse-v3--PN06-d52.png) |
| d53 | wine glass | [PNG](../masks/diverse-v3--PN06-d53.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--PN06.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d54 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN06-d54.png) |
| d55 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN06-d55.png) |
| d56 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN06-d56.png) |

[Raw frozen detector response](../detections/diverse-v3--PN06.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate exactly ONE independent candid smartphone photograph. Show believable glass, paper, natural material imperfections, fictional wine branding, and anatomically plausible hands. No collage, grid, arrows, annotations, bounding boxes, highlights, watermark, UI overlay, or explanatory caption. Text is allowed on physical objects within the scene. Keep the target visible front label entirely inside the frame unless partial occlusion or close-up is explicitly requested. Image format: landscape 3:2, approximately 1536 by 1024 pixels. Setting: inside a real wine cellar. Use stone or brick walls, wooden wine racks, storage cubbies, a cellar tasting table and practical dim lights. Keep the described foreground inventory; background racks may be empty or softly blurred. Scene details: A tiny 187 ml bottle with a mint label stands LEFT, a large magnum with a cream label stands RIGHT on a tasting counter. A hand from lower left points upward at the small left bottle, fingertip ending just short of its label. No bottle is held.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Винный погреб. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
