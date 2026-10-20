# main-selector-imagegen-diverse-v3-20261020:HP05

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--HP05.jpg)

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): В парижском винном баре · правый хват и пальцы у соседней этикетки

Reference target description (source): Удерживаемая бутылка справа

Expected intent: `clear`. Accepted target proposals: `d0`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:HP05`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--HP05.png)

![Proposed target overlay](../target-overlays/diverse-v3--HP05.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--HP05-d0.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 347×713 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.4%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--HP05-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--HP05-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--HP05-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d6: 99.4%, 31421 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d0; reason: unique_visible_hand_contact; mode: confident; crop 371×766 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d6 100.0%.

![semantic-v2 crop](../crops/diverse-v3--HP05-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--HP05-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--HP05-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--HP05-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d6: 100.0%, 31421 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1254×1254 px. Target agreement: n/a (no native target ID). Target retention proxy: 41.4%; maximum other-bottle retention: 88.2%; minimum associated label retention: 99.9%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--HP05-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--HP05-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--HP05-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d6: 99.9%, 31421 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--HP05-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--HP05-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--HP05-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--HP05-d3.png) |
| d4 | wine bottle | [PNG](../masks/diverse-v3--HP05-d4.png) |
| d5 | wine bottle | [PNG](../masks/diverse-v3--HP05-d5.png) |
| d6 | wine label | [PNG](../masks/diverse-v3--HP05-d6.png) |
| d7 | wine label | [PNG](../masks/diverse-v3--HP05-d7.png) |
| d8 | wine label | [PNG](../masks/diverse-v3--HP05-d8.png) |
| d9 | wine label | [PNG](../masks/diverse-v3--HP05-d9.png) |
| d10 | hand | [PNG](../masks/diverse-v3--HP05-d10.png) |
| d11 | hand | [PNG](../masks/diverse-v3--HP05-d11.png) |
| d12 | wine glass | [PNG](../masks/diverse-v3--HP05-d12.png) |
| d13 | wine glass | [PNG](../masks/diverse-v3--HP05-d13.png) |
| d14 | wine glass | [PNG](../masks/diverse-v3--HP05-d14.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--HP05.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d15 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP05-d15.png) |
| d16 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP05-d16.png) |
| d17 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP05-d17.png) |

[Raw frozen detector response](../detections/diverse-v3--HP05.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, square, approximately 1024 by 1024 pixels. Inside a lively Paris neighborhood wine bar. A casually dressed adult guest examines a bottle while a friend gestures toward another. Include faces and candid bar surroundings. Two bottles in the described setting. A right-side hand firmly wraps the RIGHT burgundy-label bottle middle body. A second hand points toward the LEFT bottle but stops just short of its label, without grasping. The actual held bottle is clearly presented closer to camera. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: В парижском винном баре. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
