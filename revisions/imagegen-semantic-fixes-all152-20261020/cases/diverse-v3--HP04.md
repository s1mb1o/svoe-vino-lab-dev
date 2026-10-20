# main-selector-imagegen-diverse-v3-20261020:HP04

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--HP04.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Предплечье перед соседней бутылкой

Reference target description (source): Маленькая удерживаемая бутылка слева

Expected intent: `clear`. Accepted target proposals: `d13`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:HP04`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--HP04.png)

![Proposed target overlay](../target-overlays/diverse-v3--HP04.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--HP04-d13.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d13; reason: existing_scene_v1_rank; mode: legacy; crop 249×750 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--HP04-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--HP04-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--HP04-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d30: 100.0%, 54600 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d13; reason: unique_visible_hand_contact; mode: confident; crop 269×808 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d30 100.0%.

![semantic-v2 crop](../crops/diverse-v3--HP04-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--HP04-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--HP04-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--HP04-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d30: 100.0%, 54600 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1270×1024 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 99.8%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--HP04-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--HP04-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--HP04-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d30: 100.0%, 54600 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--HP04-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--HP04-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--HP04-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--HP04-d3.png) |
| d4 | wine bottle | [PNG](../masks/diverse-v3--HP04-d4.png) |
| d5 | wine bottle | [PNG](../masks/diverse-v3--HP04-d5.png) |
| d6 | wine bottle | [PNG](../masks/diverse-v3--HP04-d6.png) |
| d7 | wine bottle | [PNG](../masks/diverse-v3--HP04-d7.png) |
| d8 | wine bottle | [PNG](../masks/diverse-v3--HP04-d8.png) |
| d9 | wine bottle | [PNG](../masks/diverse-v3--HP04-d9.png) |
| d10 | wine bottle | [PNG](../masks/diverse-v3--HP04-d10.png) |
| d11 | wine bottle | [PNG](../masks/diverse-v3--HP04-d11.png) |
| d12 | wine bottle | [PNG](../masks/diverse-v3--HP04-d12.png) |
| d13 | wine bottle | [PNG](../masks/diverse-v3--HP04-d13.png) |
| d14 | wine bottle | [PNG](../masks/diverse-v3--HP04-d14.png) |
| d15 | wine bottle | [PNG](../masks/diverse-v3--HP04-d15.png) |
| d16 | wine bottle | [PNG](../masks/diverse-v3--HP04-d16.png) |
| d17 | wine bottle | [PNG](../masks/diverse-v3--HP04-d17.png) |
| d18 | wine bottle | [PNG](../masks/diverse-v3--HP04-d18.png) |
| d19 | wine bottle | [PNG](../masks/diverse-v3--HP04-d19.png) |
| d20 | wine bottle | [PNG](../masks/diverse-v3--HP04-d20.png) |
| d21 | wine bottle | [PNG](../masks/diverse-v3--HP04-d21.png) |
| d22 | wine bottle | [PNG](../masks/diverse-v3--HP04-d22.png) |
| d23 | wine bottle | [PNG](../masks/diverse-v3--HP04-d23.png) |
| d24 | wine bottle | [PNG](../masks/diverse-v3--HP04-d24.png) |
| d25 | wine bottle | [PNG](../masks/diverse-v3--HP04-d25.png) |
| d26 | wine bottle | [PNG](../masks/diverse-v3--HP04-d26.png) |
| d27 | wine bottle | [PNG](../masks/diverse-v3--HP04-d27.png) |
| d28 | wine bottle | [PNG](../masks/diverse-v3--HP04-d28.png) |
| d29 | wine label | [PNG](../masks/diverse-v3--HP04-d29.png) |
| d30 | wine label | [PNG](../masks/diverse-v3--HP04-d30.png) |
| d31 | hand | [PNG](../masks/diverse-v3--HP04-d31.png) |
| d32 | box | [PNG](../masks/diverse-v3--HP04-d32.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--HP04.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d33 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d33.png) |
| d34 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d34.png) |
| d35 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d35.png) |
| d36 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d36.png) |
| d37 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d37.png) |
| d38 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d38.png) |
| d39 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d39.png) |
| d40 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d40.png) |
| d41 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d41.png) |
| d42 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d42.png) |
| d43 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d43.png) |
| d44 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d44.png) |
| d45 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d45.png) |
| d46 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d46.png) |
| d47 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d47.png) |
| d48 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d48.png) |
| d49 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d49.png) |
| d50 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d50.png) |
| d51 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d51.png) |
| d52 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d52.png) |
| d53 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d53.png) |
| d54 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d54.png) |
| d55 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d55.png) |
| d56 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d56.png) |
| d57 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d57.png) |
| d58 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d58.png) |
| d59 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d59.png) |
| d60 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP04-d60.png) |

[Raw frozen detector response](../detections/diverse-v3--HP04.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate exactly ONE independent candid smartphone photograph. Show believable glass, paper, natural material imperfections, fictional wine branding, and anatomically plausible hands. No collage, grid, arrows, annotations, bounding boxes, highlights, watermark, UI overlay, or explanatory caption. Text is allowed on physical objects within the scene. Keep the target visible front label entirely inside the frame unless partial occlusion or close-up is explicitly requested. Image format: landscape 3:2, approximately 1536 by 1024 pixels. Setting: inside a real wine cellar. Use stone or brick walls, wooden wine racks, storage cubbies, a cellar tasting table and practical dim lights. Background wine bottles may be present on shelves but should remain clearly in the background. Viewpoint: the customer is examining a wine bottle in their own hand while shopping or browsing the cellar, with the bottle front label turned toward the phone camera. Show the bottle, the holding hand and enough surrounding shelves or cellar details to establish the location. Scene details: A hand from left holds a small LEFT white-label bottle at mid-body, fingers wrapping glass. Its forearm extends across the scene in front of a larger RIGHT blue-label bottle without touching that right bottle. Two bottles only. Bright natural window light.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Винный погреб. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
