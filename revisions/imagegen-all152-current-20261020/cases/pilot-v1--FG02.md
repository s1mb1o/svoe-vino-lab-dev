# main-selector-imagegen-pilot-v1-20261019:FG02

**Scene confirmed; masks pending. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Три бутылки: передняя справа

Reference target description (source): Передняя бутылка справа

Expected intent: `clear`. Accepted target proposals: `d0`.

Scene group: `main-selector-imagegen-pilot-v1-20261019:FG02`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/pilot-v1--FG02.png)

![Proposed target overlay](../target-overlays/pilot-v1--FG02.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/pilot-v1--FG02-d0.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 344×1017 px. Target agreement: True. Target retention proxy: 99.6%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.8%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/pilot-v1--FG02-scene-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--FG02-scene-v1.png) · [Exact decision JSON](../results/pilot-v1--FG02-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 99.8%, 202450 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d0; reason: dominant_edge_subject; mode: confident; crop 358×1024 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%.

![semantic-v2 crop](../crops/pilot-v1--FG02-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--FG02-semantic-v2.png) · [Exact decision JSON](../results/pilot-v1--FG02-semantic-v2.json)

Returned label views: [label 1](../label-crops/pilot-v1--FG02-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 202450 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1010×875 px. Target agreement: n/a (no native target ID). Target retention proxy: 61.0%; maximum other-bottle retention: 99.9%; minimum associated label retention: 65.7%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/pilot-v1--FG02-dis-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--FG02-dis-v1.png) · [Exact decision JSON](../results/pilot-v1--FG02-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 65.7%, 202450 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/pilot-v1--FG02-d0.png) |
| d1 | wine bottle | [PNG](../masks/pilot-v1--FG02-d1.png) |
| d2 | wine bottle | [PNG](../masks/pilot-v1--FG02-d2.png) |
| d3 | wine label | [PNG](../masks/pilot-v1--FG02-d3.png) |
| d4 | wine label | [PNG](../masks/pilot-v1--FG02-d4.png) |
| d5 | wine label | [PNG](../masks/pilot-v1--FG02-d5.png) |

[Raw frozen detector response](../detections/pilot-v1--FG02.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural.
Asset type: one independent synthetic smartphone photograph for a wine-subject selection test dataset.
Style: a believable candid phone photo with realistic optics, materials, shadows, depth and anatomically plausible hands when requested. Natural photographic imperfections, not a diagram, collage, 3D render, advertisement or contact sheet.
Bottle labels may use fictional wine names and normal small wine-label text. Labels must have complete physical paper boundaries and plausible printing. Do not add target markers, bounding boxes, arrows, captions, segmentation colors, watermarks or any explanation outside the scene.
Generate exactly one landscape photograph, approximately 1536 by 1024 pixels. Any wine identity is fictional; this tests selection and visible-label preservation, not catalogue recognition.
Scene request: Exactly three physical wine bottles on an outdoor tasting table. A clearly nearer standard wine bottle stands at the right edge, partially clipped at the shoulder but with its complete front label visible. Two more distant bottles stand near the photo center. Plausible perspective and overlap make the right bottle the obvious foreground subject. No hands or printed bottle images.
```

</details>

Source review notes (quoted reference data):

> Правая часть основной этикетки уходит за край кадра: требование полностью видимой этикетки исходного рецепта не выполнено. Решите, оставить как отдельный тест обрезки или перегенерировать.
