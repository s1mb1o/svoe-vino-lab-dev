# main-selector-imagegen-diverse-v3-20261020:SZ06

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--SZ06.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): На свадебном банкете · слева далеко от центра

Reference target description (source): Крайняя левая удерживаемая бутылка

Expected intent: `clear`. Accepted target proposals: `d2`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:SZ06`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--SZ06.png)

![Proposed target overlay](../target-overlays/diverse-v3--SZ06.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--SZ06-d2.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d2; reason: existing_scene_v1_rank; mode: legacy; crop 217×371 px. Target agreement: True. Target retention proxy: 99.9%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--SZ06-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--SZ06-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--SZ06-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d7: 100.0%, 17219 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d2; reason: unique_visible_hand_contact; mode: confident; crop 237×401 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d7 100.0%.

![semantic-v2 crop](../crops/diverse-v3--SZ06-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--SZ06-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--SZ06-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--SZ06-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d7: 100.0%, 17219 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1536×1024 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.7%; maximum other-bottle retention: 98.8%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--SZ06-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--SZ06-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--SZ06-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d7: 100.0%, 17219 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--SZ06-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--SZ06-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--SZ06-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--SZ06-d3.png) |
| d4 | wine label | [PNG](../masks/diverse-v3--SZ06-d4.png) |
| d5 | wine label | [PNG](../masks/diverse-v3--SZ06-d5.png) |
| d6 | wine label | [PNG](../masks/diverse-v3--SZ06-d6.png) |
| d7 | wine label | [PNG](../masks/diverse-v3--SZ06-d7.png) |
| d8 | hand | [PNG](../masks/diverse-v3--SZ06-d8.png) |
| d9 | hand | [PNG](../masks/diverse-v3--SZ06-d9.png) |
| d10 | hand | [PNG](../masks/diverse-v3--SZ06-d10.png) |
| d11 | hand | [PNG](../masks/diverse-v3--SZ06-d11.png) |
| d12 | hand | [PNG](../masks/diverse-v3--SZ06-d12.png) |
| d13 | hand | [PNG](../masks/diverse-v3--SZ06-d13.png) |
| d14 | wine glass | [PNG](../masks/diverse-v3--SZ06-d14.png) |
| d15 | wine glass | [PNG](../masks/diverse-v3--SZ06-d15.png) |
| d16 | wine glass | [PNG](../masks/diverse-v3--SZ06-d16.png) |
| d17 | wine glass | [PNG](../masks/diverse-v3--SZ06-d17.png) |
| d18 | wine glass | [PNG](../masks/diverse-v3--SZ06-d18.png) |
| d19 | wine glass | [PNG](../masks/diverse-v3--SZ06-d19.png) |
| d20 | wine glass | [PNG](../masks/diverse-v3--SZ06-d20.png) |
| d21 | wine glass | [PNG](../masks/diverse-v3--SZ06-d21.png) |
| d22 | wine glass | [PNG](../masks/diverse-v3--SZ06-d22.png) |
| d23 | wine glass | [PNG](../masks/diverse-v3--SZ06-d23.png) |
| d24 | wine glass | [PNG](../masks/diverse-v3--SZ06-d24.png) |
| d25 | wine glass | [PNG](../masks/diverse-v3--SZ06-d25.png) |
| d26 | wine glass | [PNG](../masks/diverse-v3--SZ06-d26.png) |
| d27 | wine glass | [PNG](../masks/diverse-v3--SZ06-d27.png) |
| d28 | wine glass | [PNG](../masks/diverse-v3--SZ06-d28.png) |
| d29 | wine glass | [PNG](../masks/diverse-v3--SZ06-d29.png) |
| d30 | wine glass | [PNG](../masks/diverse-v3--SZ06-d30.png) |
| d31 | wine glass | [PNG](../masks/diverse-v3--SZ06-d31.png) |
| d32 | wine glass | [PNG](../masks/diverse-v3--SZ06-d32.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--SZ06.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d33 | bottle held in hand | [PNG](../context-masks/diverse-v3--SZ06-d33.png) |
| d34 | bottle held in hand | [PNG](../context-masks/diverse-v3--SZ06-d34.png) |
| d35 | bottle held in hand | [PNG](../context-masks/diverse-v3--SZ06-d35.png) |
| d36 | bottle held in hand | [PNG](../context-masks/diverse-v3--SZ06-d36.png) |

[Raw frozen detector response](../detections/diverse-v3--SZ06.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, landscape 3:2, approximately 1536 by 1024 pixels. An adult guest at a long wedding banquet examines the leftmost wine bottle, several unattended bottles farther right. Show face, suit sleeve, table decorations and other guests. Wide horizontal tasting-table scene. A hand from left firmly holds a LEFTMOST red-label bottle near the edge, full label visible. Three unheld cream-label bottles stand center and right. Large empty table area separates target from center. Realistic grip and perspective. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: На свадебном банкете. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
