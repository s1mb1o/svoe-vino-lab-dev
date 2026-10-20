# main-selector-imagegen-pilot-v1-20261019:VI02

**Scene confirmed; masks pending. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Семь бутылок и ведёрко

Reference target description (source): Удерживаемая бутылка справа в ведёрке

Expected intent: `clear`. Accepted target proposals: `d0`.

Scene group: `main-selector-imagegen-pilot-v1-20261019:VI02`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/pilot-v1--VI02.png)

![Proposed target overlay](../target-overlays/pilot-v1--VI02.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/pilot-v1--VI02-d0.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 349×760 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.8%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/pilot-v1--VI02-scene-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--VI02-scene-v1.png) · [Exact decision JSON](../results/pilot-v1--VI02-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d6: 99.8%, 81337 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d0; reason: unique_visible_hand_contact; mode: confident; crop 377×791 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 9.9%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d6 100.0%.

![semantic-v2 crop](../crops/pilot-v1--VI02-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--VI02-semantic-v2.png) · [Exact decision JSON](../results/pilot-v1--VI02-semantic-v2.json)

Returned label views: [label 1](../label-crops/pilot-v1--VI02-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d6: 100.0%, 81337 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1525×885 px. Target agreement: n/a (no native target ID). Target retention proxy: 97.4%; maximum other-bottle retention: 90.7%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/pilot-v1--VI02-dis-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--VI02-dis-v1.png) · [Exact decision JSON](../results/pilot-v1--VI02-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d6: 100.0%, 81337 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/pilot-v1--VI02-d0.png) |
| d1 | wine bottle | [PNG](../masks/pilot-v1--VI02-d1.png) |
| d2 | wine bottle | [PNG](../masks/pilot-v1--VI02-d2.png) |
| d3 | wine bottle | [PNG](../masks/pilot-v1--VI02-d3.png) |
| d4 | wine bottle | [PNG](../masks/pilot-v1--VI02-d4.png) |
| d5 | wine bottle | [PNG](../masks/pilot-v1--VI02-d5.png) |
| d6 | wine label | [PNG](../masks/pilot-v1--VI02-d6.png) |
| d7 | wine label | [PNG](../masks/pilot-v1--VI02-d7.png) |
| d8 | wine label | [PNG](../masks/pilot-v1--VI02-d8.png) |
| d9 | wine label | [PNG](../masks/pilot-v1--VI02-d9.png) |
| d10 | wine label | [PNG](../masks/pilot-v1--VI02-d10.png) |
| d11 | wine label | [PNG](../masks/pilot-v1--VI02-d11.png) |
| d12 | hand | [PNG](../masks/pilot-v1--VI02-d12.png) |
| d13 | hand | [PNG](../masks/pilot-v1--VI02-d13.png) |
| d14 | wine glass | [PNG](../masks/pilot-v1--VI02-d14.png) |
| d15 | wine glass | [PNG](../masks/pilot-v1--VI02-d15.png) |
| d16 | wine glass | [PNG](../masks/pilot-v1--VI02-d16.png) |
| d17 | wine glass | [PNG](../masks/pilot-v1--VI02-d17.png) |
| d18 | wine glass | [PNG](../masks/pilot-v1--VI02-d18.png) |
| d19 | wine glass | [PNG](../masks/pilot-v1--VI02-d19.png) |

[Raw frozen detector response](../detections/pilot-v1--VI02.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural.
Asset type: one independent synthetic smartphone photograph for a wine-subject selection test dataset.
Style: a believable candid phone photo with realistic optics, materials, shadows, depth and anatomically plausible hands when requested. Natural photographic imperfections, not a diagram, collage, 3D render, advertisement or contact sheet.
Bottle labels may use fictional wine names and normal small wine-label text. Labels must have complete physical paper boundaries and plausible printing. Do not add target markers, bounding boxes, arrows, captions, segmentation colors, watermarks or any explanation outside the scene.
Generate exactly one landscape photograph, approximately 1536 by 1024 pixels. Any wine identity is fictional; this tests selection and visible-label preservation, not catalogue recognition.
Scene request: Exactly seven physical wine bottles in a busy restaurant tasting scene. A person genuinely holds the off-center right foreground bottle by the neck; a metal ice bucket occludes its lower body, but most of the front label remains visible above the rim. Six smaller competing bottles stand in the background. Realistic hands and occlusion.
```

</details>

Source review notes (quoted reference data):

> Видны шесть бутылок вместо семи запрошенных. Сцену нельзя считать точным seven-bottle тестом без новой версии задания или перегенерации.
