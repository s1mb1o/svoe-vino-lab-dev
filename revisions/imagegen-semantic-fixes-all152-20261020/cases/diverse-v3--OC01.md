# main-selector-imagegen-diverse-v3-20261020:OC01

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--OC01.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): У шеф-повара · бокал перед этикеткой

Reference target description (source): Удерживаемая бутылка справа за бокалом

Expected intent: `clear`. Accepted target proposals: `d0`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:OC01`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--OC01.png)

![Proposed target overlay](../target-overlays/diverse-v3--OC01.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--OC01-d0.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 361×606 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: n/a. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--OC01-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--OC01-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--OC01-scene-v1.json)

### semantic-v2: No automatic failure flag; usability pending

Selected: d0; reason: unique_visible_hand_contact; mode: confident; crop 389×653 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: n/a. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d2 100.0%.

![semantic-v2 crop](../crops/diverse-v3--OC01-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--OC01-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--OC01-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--OC01-semantic-v2-0.png)

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1220×1024 px. Target agreement: n/a (no native target ID). Target retention proxy: 98.5%; maximum other-bottle retention: 99.9%; minimum associated label retention: n/a. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--OC01-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--OC01-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--OC01-dis-v1.json)

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--OC01-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--OC01-d1.png) |
| d2 | wine label | [PNG](../masks/diverse-v3--OC01-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--OC01-d3.png) |
| d4 | hand | [PNG](../masks/diverse-v3--OC01-d4.png) |
| d5 | hand | [PNG](../masks/diverse-v3--OC01-d5.png) |
| d6 | hand | [PNG](../masks/diverse-v3--OC01-d6.png) |
| d7 | hand | [PNG](../masks/diverse-v3--OC01-d7.png) |
| d8 | wine glass | [PNG](../masks/diverse-v3--OC01-d8.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--OC01.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d9 | bottle held in hand | [PNG](../context-masks/diverse-v3--OC01-d9.png) |
| d10 | bottle held in hand | [PNG](../context-masks/diverse-v3--OC01-d10.png) |

[Raw frozen detector response](../detections/diverse-v3--OC01.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, landscape 3:2, approximately 1536 by 1024 pixels. An adult chef in a white jacket examines a bottle at the pass of a busy restaurant kitchen. Show face, stainless surfaces, hanging pans and warm service lights, with realistic foreground glass occlusion. Two bottles in the described setting. A hand from right firmly holds the RIGHT cream-label bottle body. A transparent empty stemmed glass in front partly refracts its label, but the hand contact is clearly visible on both side edges. A separate blue-label bottle stands LEFT, unattended. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: У шеф-повара. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
