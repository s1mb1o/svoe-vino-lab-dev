# main-selector-imagegen-diverse-v3-20261020:OC08

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--OC08.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): В альпийской хижине · пакет и бокал одновременно

Reference target description (source): Удерживаемая бутылка слева за плёнкой и бокалом

Expected intent: `clear`. Accepted target proposals: `d1`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:OC08`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--OC08.png)

![Proposed target overlay](../target-overlays/diverse-v3--OC08.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--OC08-d1.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d1; reason: existing_scene_v1_rank; mode: legacy; crop 374×578 px. Target agreement: True. Target retention proxy: 99.8%; maximum other-bottle retention: 0.0%; minimum associated label retention: n/a. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--OC08-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--OC08-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--OC08-scene-v1.json)

### semantic-v2: No automatic failure flag; usability pending

Selected: d1; reason: unique_visible_hand_contact; mode: confident; crop 404×624 px. Target agreement: True. Target retention proxy: 99.8%; maximum other-bottle retention: 0.0%; minimum associated label retention: n/a. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%.

![semantic-v2 crop](../crops/diverse-v3--OC08-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--OC08-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--OC08-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--OC08-semantic-v2-0.png)

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 994×1478 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 98.0%; minimum associated label retention: n/a. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--OC08-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--OC08-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--OC08-dis-v1.json)

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--OC08-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--OC08-d1.png) |
| d2 | wine label | [PNG](../masks/diverse-v3--OC08-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--OC08-d3.png) |
| d4 | hand | [PNG](../masks/diverse-v3--OC08-d4.png) |
| d5 | box | [PNG](../masks/diverse-v3--OC08-d5.png) |
| d6 | box | [PNG](../masks/diverse-v3--OC08-d6.png) |
| d7 | wine glass | [PNG](../masks/diverse-v3--OC08-d7.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--OC08.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d8 | bottle held in hand | [PNG](../context-masks/diverse-v3--OC08-d8.png) |
| d9 | bottle held in hand | [PNG](../context-masks/diverse-v3--OC08-d9.png) |
| d10 | bottle held in hand | [PNG](../context-masks/diverse-v3--OC08-d10.png) |
| d11 | transparent wrapping | [PNG](../context-masks/diverse-v3--OC08-d11.png) |
| d12 | transparent wrapping | [PNG](../context-masks/diverse-v3--OC08-d12.png) |

[Raw frozen detector response](../detections/diverse-v3--OC08.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, portrait 2:3, approximately 1024 by 1536 pixels. An adult guest examines a wine gift inside a rustic Alpine lodge, knitted sweater, timber window frames and snowy slopes outside. Transparent wrapping and a glass create layered occlusion. Two bottles. A hand from left grips the LEFT pale pink-label bottle through loose transparent cellophane. An empty wine glass in front partly refracts its lower label. The right unheld cream-label bottle is clearer. Preserve obvious grip and believable layered transparency without opaque fog. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: В альпийской хижине. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
> Обе бутылки находятся в коробке с прозрачной упаковкой. Целевую держат за горлышко, а не за корпус, как было задумано.
