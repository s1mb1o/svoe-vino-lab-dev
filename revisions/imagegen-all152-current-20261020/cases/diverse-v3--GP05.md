# main-selector-imagegen-diverse-v3-20261020:GP05

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): В вагоне-ресторане · бутылка лежит на ладони справа

Reference target description (source): Бутылка справа на ладони

Expected intent: `clear`. Accepted target proposals: `d0`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:GP05`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--GP05.png)

![Proposed target overlay](../target-overlays/diverse-v3--GP05.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--GP05-d0.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 403×719 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--GP05-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--GP05-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--GP05-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 63801 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d0; reason: explicit_pointing_gesture; mode: confident; crop 433×776 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d2 100.0%.

![semantic-v2 crop](../crops/diverse-v3--GP05-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--GP05-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--GP05-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--GP05-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 63801 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1098×1246 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 99.8%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--GP05-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--GP05-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--GP05-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 63801 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--GP05-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--GP05-d1.png) |
| d2 | wine label | [PNG](../masks/diverse-v3--GP05-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--GP05-d3.png) |
| d4 | hand | [PNG](../masks/diverse-v3--GP05-d4.png) |
| d5 | hand | [PNG](../masks/diverse-v3--GP05-d5.png) |
| d6 | wine glass | [PNG](../masks/diverse-v3--GP05-d6.png) |

[Raw frozen detector response](../detections/diverse-v3--GP05.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, square, approximately 1024 by 1024 pixels. An adult sommelier on a vintage dining train examines and presents a wine bottle beside a white-clothed table. Include face, uniform, brass fittings and scenery through the window. The train is an interior setting, not a bottle graphic. A single palm from right visibly supports a wine bottle lying diagonally across the RIGHT foreground, fingers wrapping its lower body from below; front orange label faces camera. A second upright unheld bottle stands at LEFT. Show physical weight and contact, not levitation. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: В вагоне-ресторане. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
