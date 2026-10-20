# main-selector-imagegen-diverse-v3-20261020:LT02

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): В красном свете джаз-клуба · красный свет бара

Reference target description (source): Левая удерживаемая бутылка при красном свете

Expected intent: `clear`. Accepted target proposals: `d1`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:LT02`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--LT02.png)

![Proposed target overlay](../target-overlays/diverse-v3--LT02.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--LT02-d1.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d1; reason: existing_scene_v1_rank; mode: legacy; crop 241×388 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.6%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--LT02-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LT02-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--LT02-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 99.6%, 14173 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d1; reason: fallback_nearest_center; mode: fallback; crop 260×417 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%.

![semantic-v2 crop](../crops/diverse-v3--LT02-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LT02-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--LT02-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--LT02-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 14173 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1207×1024 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 17.2%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--LT02-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LT02-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--LT02-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 14173 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--LT02-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--LT02-d1.png) |
| d2 | wine label | [PNG](../masks/diverse-v3--LT02-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--LT02-d3.png) |
| d4 | hand | [PNG](../masks/diverse-v3--LT02-d4.png) |
| d5 | hand | [PNG](../masks/diverse-v3--LT02-d5.png) |
| d6 | hand | [PNG](../masks/diverse-v3--LT02-d6.png) |
| d7 | box | [PNG](../masks/diverse-v3--LT02-d7.png) |
| d8 | box | [PNG](../masks/diverse-v3--LT02-d8.png) |
| d9 | box | [PNG](../masks/diverse-v3--LT02-d9.png) |
| d10 | box | [PNG](../masks/diverse-v3--LT02-d10.png) |

[Raw frozen detector response](../detections/diverse-v3--LT02.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, landscape 3:2, approximately 1536 by 1024 pixels. An adult jazz musician in a dark suit examines a bottle backstage at a jazz club, red stage light, saxophone case and velvet curtain. Include face and hands. Two bottles in the described setting illuminated mainly by red neon. A hand from left wraps the LEFT cream-label bottle mid-body; contact remains visible despite colored light. RIGHT unheld bottle has a larger white label. Natural dark phone noise, no illegible black frame. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: В красном свете джаз-клуба. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
