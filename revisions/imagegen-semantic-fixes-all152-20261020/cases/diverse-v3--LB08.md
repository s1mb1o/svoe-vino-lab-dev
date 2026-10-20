# main-selector-imagegen-diverse-v3-20261020:LB08

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--LB08.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Старая бутылка в частном погребе · потёртая этикетка

Reference target description (source): Левая удерживаемая бутылка с потёртой этикеткой

Expected intent: `clear`. Accepted target proposals: `d3`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:LB08`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--LB08.png)

![Proposed target overlay](../target-overlays/diverse-v3--LB08.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--LB08-d3.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d3; reason: existing_scene_v1_rank; mode: legacy; crop 372×623 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.7%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--LB08-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LB08-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--LB08-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d5: 99.7%, 42643 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d3; reason: unique_visible_hand_contact; mode: confident; crop 396×674 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d5 100.0%.

![semantic-v2 crop](../crops/diverse-v3--LB08-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LB08-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--LB08-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--LB08-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d5: 100.0%, 42643 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 940×1507 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 97.8%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--LB08-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LB08-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--LB08-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d5: 100.0%, 42643 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--LB08-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--LB08-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--LB08-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--LB08-d3.png) |
| d4 | wine label | [PNG](../masks/diverse-v3--LB08-d4.png) |
| d5 | wine label | [PNG](../masks/diverse-v3--LB08-d5.png) |
| d6 | hand | [PNG](../masks/diverse-v3--LB08-d6.png) |
| d7 | box | [PNG](../masks/diverse-v3--LB08-d7.png) |
| d8 | box | [PNG](../masks/diverse-v3--LB08-d8.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--LB08.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d9 | bottle held in hand | [PNG](../context-masks/diverse-v3--LB08-d9.png) |
| d10 | bottle held in hand | [PNG](../context-masks/diverse-v3--LB08-d10.png) |

[Raw frozen detector response](../detections/diverse-v3--LB08.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, portrait 2:3, approximately 1024 by 1536 pixels. An adult elderly collector examines a dusty bottle with worn label in an old private cellar, shelves, stone arches and a single work lamp. Show face and aged hands, respectful documentary style. Two bottles in a cellar. A hand from left grips the LEFT dusty dark bottle below its aged cream paper label, paper stained and partly torn but visible outline identifiable. RIGHT unheld bottle has a pristine white label. Keep wear realistic and hand contact obvious. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Старая бутылка в частном погребе. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
