# main-selector-imagegen-diverse-v3-20261020:LB03

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): На гастрономической ярмарке · текст прямо на стекле

Reference target description (source): Правая удерживаемая бутылка с печатью на стекле

Expected intent: `clear`. Accepted target proposals: `d0`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:LB03`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--LB03.png)

![Proposed target overlay](../target-overlays/diverse-v3--LB03.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--LB03-d0.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 316×636 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 98.6%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--LB03-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LB03-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--LB03-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 98.6%, 5608 source pixels; d3: 100.0%, 40191 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d0; reason: unique_visible_hand_contact; mode: confident; crop 342×685 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%; d2 100.0%.

![semantic-v2 crop](../crops/diverse-v3--LB03-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LB03-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--LB03-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--LB03-semantic-v2-0.png) · [label 2](../label-crops/diverse-v3--LB03-semantic-v2-1.png)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 5608 source pixels; d3: 100.0%, 40191 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1002×1395 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 100.0%; minimum associated label retention: 99.5%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--LB03-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LB03-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--LB03-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 99.5%, 5608 source pixels; d3: 100.0%, 40191 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--LB03-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--LB03-d1.png) |
| d2 | wine label | [PNG](../masks/diverse-v3--LB03-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--LB03-d3.png) |
| d4 | wine label | [PNG](../masks/diverse-v3--LB03-d4.png) |
| d5 | wine label | [PNG](../masks/diverse-v3--LB03-d5.png) |
| d6 | hand | [PNG](../masks/diverse-v3--LB03-d6.png) |
| d7 | hand | [PNG](../masks/diverse-v3--LB03-d7.png) |
| d8 | hand | [PNG](../masks/diverse-v3--LB03-d8.png) |
| d9 | box | [PNG](../masks/diverse-v3--LB03-d9.png) |

[Raw frozen detector response](../detections/diverse-v3--LB03.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, portrait 2:3, approximately 1024 by 1536 pixels. An adult chef examines a bottle printed directly on glass at a street-food fair, food trucks, paper lanterns and festival crowd. Include face, apron and grasp. Two bottles. A hand from right grips the RIGHT dark bottle below a large white decorative text print directly on glass, with no front paper label. A small neck label is present. LEFT unheld bottle has a vivid ivory paper label. Target visible printing all within frame. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: На гастрономической ярмарке. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
