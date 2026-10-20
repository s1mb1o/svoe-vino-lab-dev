# main-selector-imagegen-diverse-v3-20261020:LT10

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): Утром в саду · конденсат и утреннее солнце

Reference target description (source): Левая удерживаемая холодная бутылка

Expected intent: `clear`. Accepted target proposals: `d1`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:LT10`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--LT10.png)

![Proposed target overlay](../target-overlays/diverse-v3--LT10.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--LT10-d1.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 173×659 px. Target agreement: False. Target retention proxy: 0.0%; maximum other-bottle retention: 100.0%; minimum associated label retention: 0.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--LT10-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LT10-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--LT10-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 0.0%, 19877 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d1; reason: fallback_nearest_center; mode: fallback; crop 339×700 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%.

![semantic-v2 crop](../crops/diverse-v3--LT10-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LT10-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--LT10-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--LT10-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 19877 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1141×1254 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.8%; maximum other-bottle retention: 99.9%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--LT10-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LT10-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--LT10-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 19877 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--LT10-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--LT10-d1.png) |
| d2 | wine label | [PNG](../masks/diverse-v3--LT10-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--LT10-d3.png) |
| d4 | hand | [PNG](../masks/diverse-v3--LT10-d4.png) |
| d5 | hand | [PNG](../masks/diverse-v3--LT10-d5.png) |
| d6 | hand | [PNG](../masks/diverse-v3--LT10-d6.png) |
| d7 | hand | [PNG](../masks/diverse-v3--LT10-d7.png) |

[Raw frozen detector response](../detections/diverse-v3--LT10.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, square, approximately 1024 by 1024 pixels. An adult gardener in a straw hat examines a cold wine bottle on a dew-covered garden terrace. Morning sun, condensation, flowers and green foliage; include face and hands. Two bottles in the described setting. A hand from left wraps the LEFT chilled pale-green bottle body, condensation and sun highlights partly obscuring its mint label. RIGHT dry unheld bottle has a clear cream label. Visible thumb and fingers on opposite sides, full target paper within frame. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Утром в саду. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
