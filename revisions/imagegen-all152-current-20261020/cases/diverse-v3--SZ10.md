# main-selector-imagegen-diverse-v3-20261020:SZ10

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Сверху на балконе кафе · высокий ракурс и бутылка слева

Reference target description (source): Левая удерживаемая бутылка в ракурсе сверху

Expected intent: `clear`. Accepted target proposals: `d1`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:SZ10`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--SZ10.png)

![Proposed target overlay](../target-overlays/diverse-v3--SZ10.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--SZ10-d1.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d1; reason: existing_scene_v1_rank; mode: legacy; crop 279×530 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--SZ10-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--SZ10-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--SZ10-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 28394 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d1; reason: fallback_center_contains; mode: fallback; crop 297×571 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%.

![semantic-v2 crop](../crops/diverse-v3--SZ10-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--SZ10-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--SZ10-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--SZ10-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 28394 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 782×979 px. Target agreement: n/a (no native target ID). Target retention proxy: 93.5%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--SZ10-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--SZ10-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--SZ10-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 28394 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--SZ10-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--SZ10-d1.png) |
| d2 | wine label | [PNG](../masks/diverse-v3--SZ10-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--SZ10-d3.png) |
| d4 | hand | [PNG](../masks/diverse-v3--SZ10-d4.png) |
| d5 | hand | [PNG](../masks/diverse-v3--SZ10-d5.png) |
| d6 | hand | [PNG](../masks/diverse-v3--SZ10-d6.png) |
| d7 | wine glass | [PNG](../masks/diverse-v3--SZ10-d7.png) |
| d8 | wine glass | [PNG](../masks/diverse-v3--SZ10-d8.png) |

[Raw frozen detector response](../detections/diverse-v3--SZ10.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, square, approximately 1024 by 1024 pixels. An adult diner examines a bottle on a small cafe balcony overlooking a canal. Steep oblique overhead framing, their arms and face partly visible, neighboring bottle on the table. A steep oblique overhead photo of a tasting table. A hand from left grips a LEFT green-label bottle body, tilted slightly toward camera; a larger unheld cream-label bottle stands RIGHT. Bases and shoulders foreshorten naturally, full target front label remains visible. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Сверху на балконе кафе. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
