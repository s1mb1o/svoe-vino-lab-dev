# main-selector-imagegen-diverse-v3-20261020:SZ05

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): Широкоугольное фото в бистро · широкоугольный край справа

Reference target description (source): Правая удерживаемая бутылка у края кадра

Expected intent: `clear`. Accepted target proposals: `d12`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:SZ05`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--SZ05.png)

![Proposed target overlay](../target-overlays/diverse-v3--SZ05.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--SZ05-d12.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d12; reason: existing_scene_v1_rank; mode: legacy; crop 317×734 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 96.2%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--SZ05-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--SZ05-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--SZ05-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d35: 99.8%, 75168 source pixels; d38: 96.2%, 5603 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d12; reason: unique_visible_hand_contact; mode: confident; crop 344×762 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d35 100.0%; d38 100.0%.

![semantic-v2 crop](../crops/diverse-v3--SZ05-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--SZ05-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--SZ05-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--SZ05-semantic-v2-0.png) · [label 2](../label-crops/diverse-v3--SZ05-semantic-v2-1.png)

Associated label-mask retention proxies (unreviewed ownership): d35: 100.0%, 75168 source pixels; d38: 100.0%, 5603 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1254×1254 px. Target agreement: n/a (no native target ID). Target retention proxy: 94.6%; maximum other-bottle retention: 100.0%; minimum associated label retention: 10.4%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--SZ05-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--SZ05-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--SZ05-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d35: 100.0%, 75168 source pixels; d38: 10.4%, 5603 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d3.png) |
| d4 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d4.png) |
| d5 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d5.png) |
| d6 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d6.png) |
| d7 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d7.png) |
| d8 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d8.png) |
| d9 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d9.png) |
| d10 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d10.png) |
| d11 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d11.png) |
| d12 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d12.png) |
| d13 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d13.png) |
| d14 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d14.png) |
| d15 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d15.png) |
| d16 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d16.png) |
| d17 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d17.png) |
| d18 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d18.png) |
| d19 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d19.png) |
| d20 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d20.png) |
| d21 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d21.png) |
| d22 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d22.png) |
| d23 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d23.png) |
| d24 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d24.png) |
| d25 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d25.png) |
| d26 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d26.png) |
| d27 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d27.png) |
| d28 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d28.png) |
| d29 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d29.png) |
| d30 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d30.png) |
| d31 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d31.png) |
| d32 | wine bottle | [PNG](../masks/diverse-v3--SZ05-d32.png) |
| d33 | wine label | [PNG](../masks/diverse-v3--SZ05-d33.png) |
| d34 | wine label | [PNG](../masks/diverse-v3--SZ05-d34.png) |
| d35 | wine label | [PNG](../masks/diverse-v3--SZ05-d35.png) |
| d36 | wine label | [PNG](../masks/diverse-v3--SZ05-d36.png) |
| d37 | wine label | [PNG](../masks/diverse-v3--SZ05-d37.png) |
| d38 | wine label | [PNG](../masks/diverse-v3--SZ05-d38.png) |
| d39 | wine label | [PNG](../masks/diverse-v3--SZ05-d39.png) |
| d40 | wine label | [PNG](../masks/diverse-v3--SZ05-d40.png) |
| d41 | wine label | [PNG](../masks/diverse-v3--SZ05-d41.png) |
| d42 | wine label | [PNG](../masks/diverse-v3--SZ05-d42.png) |
| d43 | wine label | [PNG](../masks/diverse-v3--SZ05-d43.png) |
| d44 | hand | [PNG](../masks/diverse-v3--SZ05-d44.png) |
| d45 | hand | [PNG](../masks/diverse-v3--SZ05-d45.png) |
| d46 | hand | [PNG](../masks/diverse-v3--SZ05-d46.png) |
| d47 | hand | [PNG](../masks/diverse-v3--SZ05-d47.png) |
| d48 | wine glass | [PNG](../masks/diverse-v3--SZ05-d48.png) |
| d49 | wine glass | [PNG](../masks/diverse-v3--SZ05-d49.png) |
| d50 | wine glass | [PNG](../masks/diverse-v3--SZ05-d50.png) |
| d51 | wine glass | [PNG](../masks/diverse-v3--SZ05-d51.png) |
| d52 | wine glass | [PNG](../masks/diverse-v3--SZ05-d52.png) |

[Raw frozen detector response](../detections/diverse-v3--SZ05.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, square, approximately 1024 by 1024 pixels. An adult server examines wine at the edge of a busy bistro table, tiled floor, diners and open doorway behind. Wide-angle phone perspective, label retained inside frame. A wide-angle phone photo in the described setting. A hand from right grips the RIGHT bottle close to the frame edge, ivory label fully visible despite mild lens stretch. Two smaller unheld bottles stand center-left. All glass silhouettes remain within frame; target is held. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Широкоугольное фото в бистро. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
