# main-selector-imagegen-diverse-v3-20261020:CT01

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): Равная пара на яхте · равнозначная пара без рук

Reference target description (source): Неоднозначная пара — предварительный fallback

Expected intent: `ambiguous`. Accepted target proposals: `d1`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:CT01`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--CT01.png)

![Proposed target overlay](../target-overlays/diverse-v3--CT01.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--CT01-d1.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 170×590 px. Target agreement: False. Target retention proxy: 0.0%; maximum other-bottle retention: 100.0%; minimum associated label retention: 0.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--CT01-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--CT01-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--CT01-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 0.0%, 26768 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d1; reason: fallback_nearest_center; mode: fallback; crop 185×629 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%.

![semantic-v2 crop](../crops/diverse-v3--CT01-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--CT01-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--CT01-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--CT01-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 26768 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1069×640 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.8%; maximum other-bottle retention: 99.8%; minimum associated label retention: 99.7%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--CT01-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--CT01-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--CT01-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 99.7%, 26768 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--CT01-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--CT01-d1.png) |
| d2 | wine label | [PNG](../masks/diverse-v3--CT01-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--CT01-d3.png) |

[Raw frozen detector response](../detections/diverse-v3--CT01.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, landscape 3:2, approximately 1536 by 1024 pixels. A small unoccupied yacht bar in daylight. Two equal bottles are displayed symmetrically on a teak table, with railings and sea behind. No hands; preserve genuine ambiguity. Exactly two identical-size upright wine bottles stand symmetrically LEFT and RIGHT on the same table, same depth, equally lit, with matching cream-label size. Empty air gap at photo center, no hands, no foreground cue, no other bottles. A genuinely balanced ambiguous pair, natural phone photo. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Равная пара на яхте. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
