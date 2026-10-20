# main-selector-imagegen-diverse-v3-20261020:LT04

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): На солнечном винограднике · слепящая полоса на бумаге

Reference target description (source): Левая удерживаемая бутылка с широким бликом

Expected intent: `clear`. Accepted target proposals: `d1`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:LT04`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--LT04.png)

![Proposed target overlay](../target-overlays/diverse-v3--LT04.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--LT04-d1.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d1; reason: existing_scene_v1_rank; mode: legacy; crop 318×555 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--LT04-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LT04-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--LT04-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 30992 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d1; reason: fallback_nearest_center; mode: fallback; crop 344×598 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%.

![semantic-v2 crop](../crops/diverse-v3--LT04-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LT04-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--LT04-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--LT04-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 30992 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1435×1024 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.9%; maximum other-bottle retention: 99.9%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--LT04-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LT04-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--LT04-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 30992 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--LT04-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--LT04-d1.png) |
| d2 | wine label | [PNG](../masks/diverse-v3--LT04-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--LT04-d3.png) |
| d4 | hand | [PNG](../masks/diverse-v3--LT04-d4.png) |
| d5 | hand | [PNG](../masks/diverse-v3--LT04-d5.png) |
| d6 | hand | [PNG](../masks/diverse-v3--LT04-d6.png) |
| d7 | hand | [PNG](../masks/diverse-v3--LT04-d7.png) |

[Raw frozen detector response](../detections/diverse-v3--LT04.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, landscape 3:2, approximately 1536 by 1024 pixels. An adult winemaker examines a silver-label bottle outdoors beside vine rows. Show face and hand; strong oblique sunlight creates a broad glare stripe. Documentary photo, no studio backdrop. Two bottles. A hand from left holds the LEFT silver-label bottle body; a broad bright white reflection washes out a third of the label but all paper edges remain visible. RIGHT unheld bottle has a perfectly clear red label. Strong window reflection, realistic grip. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: На солнечном винограднике. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
