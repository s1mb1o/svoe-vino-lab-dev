# main-selector-imagegen-diverse-v3-20261020:WP08

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--WP08.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): На космической станции · часть фольги снята

Reference target description (source): Удерживаемая бутылка слева с отогнутой фольгой

Expected intent: `clear`. Accepted target proposals: `d1`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:WP08`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--WP08.png)

![Proposed target overlay](../target-overlays/diverse-v3--WP08.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--WP08-d1.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d1; reason: existing_scene_v1_rank; mode: legacy; crop 321×655 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.9%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--WP08-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--WP08-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--WP08-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 99.9%, 37647 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d1; reason: unique_visible_hand_contact; mode: confident; crop 345×703 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%.

![semantic-v2 crop](../crops/diverse-v3--WP08-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--WP08-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--WP08-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--WP08-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 37647 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1024×1488 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 98.2%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--WP08-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--WP08-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--WP08-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 37647 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--WP08-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--WP08-d1.png) |
| d2 | wine label | [PNG](../masks/diverse-v3--WP08-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--WP08-d3.png) |
| d4 | hand | [PNG](../masks/diverse-v3--WP08-d4.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--WP08.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d5 | screen | [PNG](../context-masks/diverse-v3--WP08-d5.png) |
| d6 | bottle held in hand | [PNG](../context-masks/diverse-v3--WP08-d6.png) |
| d7 | bottle held in hand | [PNG](../context-masks/diverse-v3--WP08-d7.png) |
| d8 | transparent wrapping | [PNG](../context-masks/diverse-v3--WP08-d8.png) |
| d9 | transparent wrapping | [PNG](../context-masks/diverse-v3--WP08-d9.png) |

[Raw frozen detector response](../detections/diverse-v3--WP08.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, portrait 2:3, approximately 1024 by 1536 pixels. A fictional adult astronaut with helmet raised examines a wine bottle in a realistic orbital-station cabin, white glove, equipment panels and Earth visible through a round window. Photorealistic science-fiction still, no cartoon. Bottle remains firmly held. A hand from left holds the LEFT wine bottle at mid-body. A reflective silver decorative wrapper covers only its neck and back half, peeled aside to expose the entire front paper label. The right unheld cream-label bottle is brighter. Show thumb and fingers touching glass on opposite edges. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: На космической станции. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
