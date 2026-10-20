# main-selector-imagegen-diverse-v3-20261020:SZ03

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--SZ03.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): На пикнике после сбора урожая · передняя маленькая и задняя большая

Reference target description (source): Передняя удерживаемая бутылка справа

Expected intent: `clear`. Accepted target proposals: `d2`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:SZ03`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--SZ03.png)

![Proposed target overlay](../target-overlays/diverse-v3--SZ03.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--SZ03-d2.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d2; reason: existing_scene_v1_rank; mode: legacy; crop 224×755 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.9%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--SZ03-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--SZ03-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--SZ03-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 99.9%, 54662 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d2; reason: unique_visible_hand_contact; mode: confident; crop 242×813 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%.

![semantic-v2 crop](../crops/diverse-v3--SZ03-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--SZ03-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--SZ03-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--SZ03-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 54662 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 971×1402 px. Target agreement: n/a (no native target ID). Target retention proxy: 98.7%; maximum other-bottle retention: 99.7%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--SZ03-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--SZ03-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--SZ03-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 54662 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--SZ03-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--SZ03-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--SZ03-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--SZ03-d3.png) |
| d4 | wine label | [PNG](../masks/diverse-v3--SZ03-d4.png) |
| d5 | hand | [PNG](../masks/diverse-v3--SZ03-d5.png) |
| d6 | hand | [PNG](../masks/diverse-v3--SZ03-d6.png) |
| d7 | hand | [PNG](../masks/diverse-v3--SZ03-d7.png) |
| d8 | hand | [PNG](../masks/diverse-v3--SZ03-d8.png) |
| d9 | box | [PNG](../masks/diverse-v3--SZ03-d9.png) |
| d10 | box | [PNG](../masks/diverse-v3--SZ03-d10.png) |
| d11 | box | [PNG](../masks/diverse-v3--SZ03-d11.png) |
| d12 | box | [PNG](../masks/diverse-v3--SZ03-d12.png) |
| d13 | wine glass | [PNG](../masks/diverse-v3--SZ03-d13.png) |
| d14 | wine glass | [PNG](../masks/diverse-v3--SZ03-d14.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--SZ03.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d15 | bottle held in hand | [PNG](../context-masks/diverse-v3--SZ03-d15.png) |
| d16 | bottle held in hand | [PNG](../context-masks/diverse-v3--SZ03-d16.png) |
| d17 | bottle held in hand | [PNG](../context-masks/diverse-v3--SZ03-d17.png) |

[Raw frozen detector response](../detections/diverse-v3--SZ03.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, portrait 2:3, approximately 1024 by 1536 pixels. An adult vineyard worker examines a half-size bottle during a harvest picnic, large unattended magnum nearby, grape baskets and rows of vines behind. Candid wide phone photo. Two bottles on the same tasting table. A hand from right grips the RIGHT foreground half-size green-label bottle body. A much larger unheld magnum stands LEFT farther back and appears taller. Perspective and size conflict, but grip is obvious and target label inside frame. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: На пикнике после сбора урожая. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
> Помимо крупной бутылки на переднем плане, в глубине человек держит ещё одну. Предварительная цель — бутылка в руке фотографирующего; проверьте однозначность.
