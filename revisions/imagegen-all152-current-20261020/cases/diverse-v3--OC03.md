# main-selector-imagegen-diverse-v3-20261020:OC03

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): В оранжерее · цветы перекрывают часть бутылки

Reference target description (source): Удерживаемая бутылка справа за стеблями

Expected intent: `clear`. Accepted target proposals: `d0`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:OC03`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--OC03.png)

![Proposed target overlay](../target-overlays/diverse-v3--OC03.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--OC03-d0.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 361×528 px. Target agreement: True. Target retention proxy: 99.9%; maximum other-bottle retention: 0.0%; minimum associated label retention: 98.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--OC03-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--OC03-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--OC03-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 98.0%, 19671 source pixels

### semantic-v2: FAIL — provisional target/proxy

Selected: d1; reason: fallback_nearest_center; mode: fallback; crop 178×650 px. Target agreement: False. Target retention proxy: 0.0%; maximum other-bottle retention: 100.0%; minimum associated label retention: 0.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%.

![semantic-v2 crop](../crops/diverse-v3--OC03-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--OC03-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--OC03-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--OC03-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d2: 0.0%, 19671 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1024×1503 px. Target agreement: n/a (no native target ID). Target retention proxy: 98.0%; maximum other-bottle retention: 100.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--OC03-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--OC03-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--OC03-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 19671 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--OC03-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--OC03-d1.png) |
| d2 | wine label | [PNG](../masks/diverse-v3--OC03-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--OC03-d3.png) |
| d4 | hand | [PNG](../masks/diverse-v3--OC03-d4.png) |
| d5 | hand | [PNG](../masks/diverse-v3--OC03-d5.png) |
| d6 | hand | [PNG](../masks/diverse-v3--OC03-d6.png) |

[Raw frozen detector response](../detections/diverse-v3--OC03.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, portrait 2:3, approximately 1024 by 1536 pixels. An adult botanist in a linen shirt examines a wine bottle in a lush greenhouse. Flowers and thin stems partly cross the foreground, glass panes and plant benches establish location. Include face and hands. Two bottles in the described setting. A hand from right wraps the RIGHT dark bottle mid-body, thumb and fingers visible. Thin flower stems in a small foreground vase cross part of its white label; visible paper elsewhere must remain. LEFT unheld bottle has a clear blue label. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: В оранжерее. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
