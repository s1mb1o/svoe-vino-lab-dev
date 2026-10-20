# main-selector-imagegen-pilot-v1-20261019:VI01

**Scene confirmed; masks pending. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): Пять бутылок и бокал спереди

Reference target description (source): Крупная бутылка слева за бокалом

Expected intent: `clear`. Accepted target proposals: `d3`.

Scene group: `main-selector-imagegen-pilot-v1-20261019:VI01`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/pilot-v1--VI01.png)

![Proposed target overlay](../target-overlays/pilot-v1--VI01.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/pilot-v1--VI01-d3.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d3; reason: existing_scene_v1_rank; mode: legacy; crop 309×996 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 94.4%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/pilot-v1--VI01-scene-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--VI01-scene-v1.png) · [Exact decision JSON](../results/pilot-v1--VI01-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d9: 94.4%, 115115 source pixels

### semantic-v2: FAIL — provisional target/proxy

Selected: d3; reason: foreground_scale_and_lower_base; mode: confident; crop 336×1024 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d9 100.0%; d10 99.0%.

![semantic-v2 crop](../crops/pilot-v1--VI01-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--VI01-semantic-v2.png) · [Exact decision JSON](../results/pilot-v1--VI01-semantic-v2.json)

Returned label views: [label 1](../label-crops/pilot-v1--VI01-semantic-v2-0.png) · [label 2](../label-crops/pilot-v1--VI01-semantic-v2-1.png)

Associated label-mask retention proxies (unreviewed ownership): d9: 100.0%, 115115 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1338×1024 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.9%; maximum other-bottle retention: 99.8%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/pilot-v1--VI01-dis-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--VI01-dis-v1.png) · [Exact decision JSON](../results/pilot-v1--VI01-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d9: 100.0%, 115115 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/pilot-v1--VI01-d0.png) |
| d1 | wine bottle | [PNG](../masks/pilot-v1--VI01-d1.png) |
| d2 | wine bottle | [PNG](../masks/pilot-v1--VI01-d2.png) |
| d3 | wine bottle | [PNG](../masks/pilot-v1--VI01-d3.png) |
| d4 | wine bottle | [PNG](../masks/pilot-v1--VI01-d4.png) |
| d5 | wine label | [PNG](../masks/pilot-v1--VI01-d5.png) |
| d6 | wine label | [PNG](../masks/pilot-v1--VI01-d6.png) |
| d7 | wine label | [PNG](../masks/pilot-v1--VI01-d7.png) |
| d8 | wine label | [PNG](../masks/pilot-v1--VI01-d8.png) |
| d9 | wine label | [PNG](../masks/pilot-v1--VI01-d9.png) |
| d10 | wine label | [PNG](../masks/pilot-v1--VI01-d10.png) |
| d11 | wine label | [PNG](../masks/pilot-v1--VI01-d11.png) |
| d12 | wine glass | [PNG](../masks/pilot-v1--VI01-d12.png) |

[Raw frozen detector response](../detections/pilot-v1--VI01.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural.
Asset type: one independent synthetic smartphone photograph for a wine-subject selection test dataset.
Style: a believable candid phone photo with realistic optics, materials, shadows, depth and anatomically plausible hands when requested. Natural photographic imperfections, not a diagram, collage, 3D render, advertisement or contact sheet.
Bottle labels may use fictional wine names and normal small wine-label text. Labels must have complete physical paper boundaries and plausible printing. Do not add target markers, bounding boxes, arrows, captions, segmentation colors, watermarks or any explanation outside the scene.
Generate exactly one landscape photograph, approximately 1536 by 1024 pixels. Any wine identity is fictional; this tests selection and visible-label preservation, not catalogue recognition.
Scene request: Exactly five physical wine bottles in a tasting setting. One larger bottle is clearly in the left foreground and four smaller bottles are behind. A foreground empty wine glass partly occludes the lower glass of the main bottle but leaves most of its complete front label visible. No hands. Plausible perspective and contact shadows establish the main bottle.
```

</details>

Source review notes (quoted reference data):

> Бокал прозрачен и преломляет изображение. Не считать обычное вычитание непрозрачной маски бокала точной видимостью этикетки.
