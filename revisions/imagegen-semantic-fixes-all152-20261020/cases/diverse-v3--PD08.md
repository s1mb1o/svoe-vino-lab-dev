# main-selector-imagegen-diverse-v3-20261020:PD08

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--PD08.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Бутылка и отражение

Reference target description (source): Настоящая бутылка слева от отражения

Expected intent: `clear`. Accepted target proposals: `d1`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:PD08`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--PD08.png)

![Proposed target overlay](../target-overlays/diverse-v3--PD08.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--PD08-d1.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d1; reason: existing_scene_v1_rank; mode: legacy; crop 227×897 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--PD08-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PD08-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--PD08-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d15: 100.0%, 65332 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d1; reason: single_substantial_bottle_in_scene_context; mode: confident; crop 254×965 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d15 100.0%.

![semantic-v2 crop](../crops/diverse-v3--PD08-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PD08-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--PD08-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--PD08-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d15: 100.0%, 65332 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1024×1245 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 99.9%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--PD08-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PD08-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--PD08-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d15: 100.0%, 65332 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--PD08-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--PD08-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--PD08-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--PD08-d3.png) |
| d4 | wine bottle | [PNG](../masks/diverse-v3--PD08-d4.png) |
| d5 | wine bottle | [PNG](../masks/diverse-v3--PD08-d5.png) |
| d6 | wine bottle | [PNG](../masks/diverse-v3--PD08-d6.png) |
| d7 | wine bottle | [PNG](../masks/diverse-v3--PD08-d7.png) |
| d8 | wine bottle | [PNG](../masks/diverse-v3--PD08-d8.png) |
| d9 | wine bottle | [PNG](../masks/diverse-v3--PD08-d9.png) |
| d10 | wine bottle | [PNG](../masks/diverse-v3--PD08-d10.png) |
| d11 | wine bottle | [PNG](../masks/diverse-v3--PD08-d11.png) |
| d12 | wine bottle | [PNG](../masks/diverse-v3--PD08-d12.png) |
| d13 | wine label | [PNG](../masks/diverse-v3--PD08-d13.png) |
| d14 | wine label | [PNG](../masks/diverse-v3--PD08-d14.png) |
| d15 | wine label | [PNG](../masks/diverse-v3--PD08-d15.png) |
| d16 | box | [PNG](../masks/diverse-v3--PD08-d16.png) |
| d17 | box | [PNG](../masks/diverse-v3--PD08-d17.png) |
| d18 | box | [PNG](../masks/diverse-v3--PD08-d18.png) |
| d19 | box | [PNG](../masks/diverse-v3--PD08-d19.png) |
| d20 | box | [PNG](../masks/diverse-v3--PD08-d20.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--PD08.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d21 | mirror | [PNG](../context-masks/diverse-v3--PD08-d21.png) |
| d22 | mirror | [PNG](../context-masks/diverse-v3--PD08-d22.png) |
| d23 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD08-d23.png) |
| d24 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD08-d24.png) |
| d25 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD08-d25.png) |

[Raw frozen detector response](../detections/diverse-v3--PD08.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate exactly ONE independent candid smartphone photograph. Show believable glass, paper, natural material imperfections, fictional wine branding, and anatomically plausible hands. No collage, grid, arrows, annotations, bounding boxes, highlights, watermark, UI overlay, or explanatory caption. Text is allowed on physical objects within the scene. Keep the target visible front label entirely inside the frame unless partial occlusion or close-up is explicitly requested. Image format: portrait 2:3, approximately 1024 by 1536 pixels. Setting: inside a real wine cellar. Use stone or brick walls, wooden wine racks, storage cubbies, a cellar tasting table and practical dim lights. Keep the described foreground inventory; background racks may be empty or softly blurred. Scene details: One real cream-label bottle stands LEFT foreground on a wooden tasting cabinet. At right a framed mirror reflects the same bottle larger due to angle. Show frame, reflected reversed label and believable perspective; do not add a second real bottle. No hands. Physical owner is the left foreground bottle.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Винный погреб. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
