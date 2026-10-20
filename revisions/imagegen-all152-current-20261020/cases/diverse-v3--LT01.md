# main-selector-imagegen-diverse-v3-20261020:LT01

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): У окна винного магазина · сильная контровая засветка

Reference target description (source): Правая удерживаемая бутылка в контровом свете

Expected intent: `clear`. Accepted target proposals: `d2`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:LT01`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--LT01.png)

![Proposed target overlay](../target-overlays/diverse-v3--LT01.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--LT01-d2.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d2; reason: existing_scene_v1_rank; mode: legacy; crop 329×966 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.8%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--LT01-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LT01-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--LT01-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d30: 99.8%, 87012 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d2; reason: unique_visible_hand_contact; mode: confident; crop 353×1024 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d30 100.0%.

![semantic-v2 crop](../crops/diverse-v3--LT01-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LT01-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--LT01-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--LT01-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d30: 100.0%, 87012 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1260×1024 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 100.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--LT01-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LT01-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--LT01-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d30: 100.0%, 87012 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--LT01-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--LT01-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--LT01-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--LT01-d3.png) |
| d4 | wine bottle | [PNG](../masks/diverse-v3--LT01-d4.png) |
| d5 | wine bottle | [PNG](../masks/diverse-v3--LT01-d5.png) |
| d6 | wine bottle | [PNG](../masks/diverse-v3--LT01-d6.png) |
| d7 | wine bottle | [PNG](../masks/diverse-v3--LT01-d7.png) |
| d8 | wine bottle | [PNG](../masks/diverse-v3--LT01-d8.png) |
| d9 | wine bottle | [PNG](../masks/diverse-v3--LT01-d9.png) |
| d10 | wine bottle | [PNG](../masks/diverse-v3--LT01-d10.png) |
| d11 | wine bottle | [PNG](../masks/diverse-v3--LT01-d11.png) |
| d12 | wine bottle | [PNG](../masks/diverse-v3--LT01-d12.png) |
| d13 | wine bottle | [PNG](../masks/diverse-v3--LT01-d13.png) |
| d14 | wine bottle | [PNG](../masks/diverse-v3--LT01-d14.png) |
| d15 | wine bottle | [PNG](../masks/diverse-v3--LT01-d15.png) |
| d16 | wine bottle | [PNG](../masks/diverse-v3--LT01-d16.png) |
| d17 | wine bottle | [PNG](../masks/diverse-v3--LT01-d17.png) |
| d18 | wine bottle | [PNG](../masks/diverse-v3--LT01-d18.png) |
| d19 | wine bottle | [PNG](../masks/diverse-v3--LT01-d19.png) |
| d20 | wine bottle | [PNG](../masks/diverse-v3--LT01-d20.png) |
| d21 | wine bottle | [PNG](../masks/diverse-v3--LT01-d21.png) |
| d22 | wine bottle | [PNG](../masks/diverse-v3--LT01-d22.png) |
| d23 | wine bottle | [PNG](../masks/diverse-v3--LT01-d23.png) |
| d24 | wine bottle | [PNG](../masks/diverse-v3--LT01-d24.png) |
| d25 | wine bottle | [PNG](../masks/diverse-v3--LT01-d25.png) |
| d26 | wine bottle | [PNG](../masks/diverse-v3--LT01-d26.png) |
| d27 | wine bottle | [PNG](../masks/diverse-v3--LT01-d27.png) |
| d28 | wine label | [PNG](../masks/diverse-v3--LT01-d28.png) |
| d29 | wine label | [PNG](../masks/diverse-v3--LT01-d29.png) |
| d30 | wine label | [PNG](../masks/diverse-v3--LT01-d30.png) |
| d31 | wine label | [PNG](../masks/diverse-v3--LT01-d31.png) |
| d32 | wine label | [PNG](../masks/diverse-v3--LT01-d32.png) |
| d33 | wine label | [PNG](../masks/diverse-v3--LT01-d33.png) |
| d34 | wine label | [PNG](../masks/diverse-v3--LT01-d34.png) |
| d35 | wine label | [PNG](../masks/diverse-v3--LT01-d35.png) |
| d36 | wine label | [PNG](../masks/diverse-v3--LT01-d36.png) |
| d37 | wine label | [PNG](../masks/diverse-v3--LT01-d37.png) |
| d38 | wine label | [PNG](../masks/diverse-v3--LT01-d38.png) |
| d39 | wine label | [PNG](../masks/diverse-v3--LT01-d39.png) |
| d40 | wine label | [PNG](../masks/diverse-v3--LT01-d40.png) |
| d41 | wine label | [PNG](../masks/diverse-v3--LT01-d41.png) |
| d42 | wine label | [PNG](../masks/diverse-v3--LT01-d42.png) |
| d43 | wine label | [PNG](../masks/diverse-v3--LT01-d43.png) |
| d44 | wine label | [PNG](../masks/diverse-v3--LT01-d44.png) |
| d45 | wine label | [PNG](../masks/diverse-v3--LT01-d45.png) |
| d46 | wine label | [PNG](../masks/diverse-v3--LT01-d46.png) |
| d47 | wine label | [PNG](../masks/diverse-v3--LT01-d47.png) |
| d48 | hand | [PNG](../masks/diverse-v3--LT01-d48.png) |
| d49 | price tag | [PNG](../masks/diverse-v3--LT01-d49.png) |
| d50 | price tag | [PNG](../masks/diverse-v3--LT01-d50.png) |
| d51 | price tag | [PNG](../masks/diverse-v3--LT01-d51.png) |
| d52 | price tag | [PNG](../masks/diverse-v3--LT01-d52.png) |

[Raw frozen detector response](../detections/diverse-v3--LT01.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, landscape 3:2, approximately 1536 by 1024 pixels. First-person customer examines a bottle against a large sunlit wine-store window, backlit shelves, street and price labels. Preserve realistic limited phone dynamic range. Two bottles before a bright window. A hand from right firmly grips the RIGHT dark bottle middle body, thumb and fingers clear in silhouette, navy label outline discernible. LEFT unheld bottle has a brighter white label. Bright window backlight and realistic limited phone dynamic range. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: У окна винного магазина. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
