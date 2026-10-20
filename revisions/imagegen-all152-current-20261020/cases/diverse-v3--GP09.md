# main-selector-imagegen-diverse-v3-20261020:GP09

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): За кулисами театра · хват у нижнего края этикетки

Reference target description (source): Правая бутылка с хватом под этикеткой

Expected intent: `clear`. Accepted target proposals: `d0`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:GP09`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--GP09.png)

![Proposed target overlay](../target-overlays/diverse-v3--GP09.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--GP09-d0.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 266×435 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.7%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--GP09-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--GP09-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--GP09-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 99.7%, 14077 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d0; reason: unique_visible_hand_contact; mode: confident; crop 290×467 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%.

![semantic-v2 crop](../crops/diverse-v3--GP09-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--GP09-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--GP09-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--GP09-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 14077 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 997×1020 px. Target agreement: n/a (no native target ID). Target retention proxy: 52.4%; maximum other-bottle retention: 99.2%; minimum associated label retention: 99.9%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--GP09-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--GP09-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--GP09-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 99.9%, 14077 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--GP09-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--GP09-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--GP09-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--GP09-d3.png) |
| d4 | wine label | [PNG](../masks/diverse-v3--GP09-d4.png) |
| d5 | hand | [PNG](../masks/diverse-v3--GP09-d5.png) |
| d6 | hand | [PNG](../masks/diverse-v3--GP09-d6.png) |
| d7 | hand | [PNG](../masks/diverse-v3--GP09-d7.png) |
| d8 | box | [PNG](../masks/diverse-v3--GP09-d8.png) |
| d9 | box | [PNG](../masks/diverse-v3--GP09-d9.png) |
| d10 | box | [PNG](../masks/diverse-v3--GP09-d10.png) |
| d11 | box | [PNG](../masks/diverse-v3--GP09-d11.png) |
| d12 | box | [PNG](../masks/diverse-v3--GP09-d12.png) |
| d13 | box | [PNG](../masks/diverse-v3--GP09-d13.png) |
| d14 | box | [PNG](../masks/diverse-v3--GP09-d14.png) |

[Raw frozen detector response](../detections/diverse-v3--GP09.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, landscape 3:2, approximately 1536 by 1024 pixels. An adult actor in a colorful stage costume examines a wine bottle backstage. Include face, makeup mirror bulbs, hanging costumes and a cluttered prop table. No bottle artwork masquerading as the physical bottle. Two bottles in the described setting. A hand from right grips the RIGHT navy-label bottle just below the label, with thumb and naturally bent fingers wrapping opposite sides of the lower glass body. The left unheld bottle is centered more prominently and has a white label. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: За кулисами театра. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
