# main-selector-imagegen-diverse-v3-20261020:WP04

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): В погребе замка · сетка на бутылке

Reference target description (source): Удерживаемая бутылка слева в сетке

Expected intent: `clear`. Accepted target proposals: `d1`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:WP04`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--WP04.png)

![Proposed target overlay](../target-overlays/diverse-v3--WP04.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--WP04-d1.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d1; reason: existing_scene_v1_rank; mode: legacy; crop 269×543 px. Target agreement: True. Target retention proxy: 99.9%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.8%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--WP04-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--WP04-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--WP04-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d19: 99.8%, 19822 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d1; reason: unique_visible_hand_contact; mode: confident; crop 294×584 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d19 100.0%.

![semantic-v2 crop](../crops/diverse-v3--WP04-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--WP04-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--WP04-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--WP04-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d19: 100.0%, 19822 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1405×1024 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.4%; maximum other-bottle retention: 99.8%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--WP04-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--WP04-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--WP04-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d19: 100.0%, 19822 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--WP04-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--WP04-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--WP04-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--WP04-d3.png) |
| d4 | wine bottle | [PNG](../masks/diverse-v3--WP04-d4.png) |
| d5 | wine bottle | [PNG](../masks/diverse-v3--WP04-d5.png) |
| d6 | wine bottle | [PNG](../masks/diverse-v3--WP04-d6.png) |
| d7 | wine bottle | [PNG](../masks/diverse-v3--WP04-d7.png) |
| d8 | wine bottle | [PNG](../masks/diverse-v3--WP04-d8.png) |
| d9 | wine bottle | [PNG](../masks/diverse-v3--WP04-d9.png) |
| d10 | wine bottle | [PNG](../masks/diverse-v3--WP04-d10.png) |
| d11 | wine bottle | [PNG](../masks/diverse-v3--WP04-d11.png) |
| d12 | wine bottle | [PNG](../masks/diverse-v3--WP04-d12.png) |
| d13 | wine bottle | [PNG](../masks/diverse-v3--WP04-d13.png) |
| d14 | wine bottle | [PNG](../masks/diverse-v3--WP04-d14.png) |
| d15 | wine bottle | [PNG](../masks/diverse-v3--WP04-d15.png) |
| d16 | wine bottle | [PNG](../masks/diverse-v3--WP04-d16.png) |
| d17 | wine label | [PNG](../masks/diverse-v3--WP04-d17.png) |
| d18 | wine label | [PNG](../masks/diverse-v3--WP04-d18.png) |
| d19 | wine label | [PNG](../masks/diverse-v3--WP04-d19.png) |
| d20 | hand | [PNG](../masks/diverse-v3--WP04-d20.png) |
| d21 | hand | [PNG](../masks/diverse-v3--WP04-d21.png) |

[Raw frozen detector response](../detections/diverse-v3--WP04.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, landscape 3:2, approximately 1536 by 1024 pixels. A chateau cellar keeper in a dark waistcoat examines a decorative wine bottle among old stone arches, dusty wooden racks and oak barrels. Include face, hands and period-like cellar surroundings. A hand from left visibly wraps around the LEFT burgundy-label bottle mid-body through a loose gold decorative wire mesh. Glass and complete label outline remain visible between thin mesh strands. An unwrapped unheld bottle stands RIGHT. Warm tasting-room light, two bottles only. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: В погребе замка. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
