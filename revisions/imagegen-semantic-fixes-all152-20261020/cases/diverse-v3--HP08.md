# main-selector-imagegen-diverse-v3-20261020:HP08

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--HP08.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Рука за стеклом бокала

Reference target description (source): Удерживаемая бутылка слева

Expected intent: `clear`. Accepted target proposals: `d6`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:HP08`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--HP08.png)

![Proposed target overlay](../target-overlays/diverse-v3--HP08.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--HP08-d6.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d6; reason: existing_scene_v1_rank; mode: legacy; crop 397×1103 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.8%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--HP08-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--HP08-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--HP08-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d32: 99.8%, 117658 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d6; reason: unique_visible_hand_contact; mode: confident; crop 428×1188 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d32 100.0%.

![semantic-v2 crop](../crops/diverse-v3--HP08-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--HP08-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--HP08-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--HP08-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d32: 100.0%, 117658 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 913×1187 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.3%; maximum other-bottle retention: 100.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--HP08-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--HP08-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--HP08-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d32: 100.0%, 117658 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--HP08-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--HP08-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--HP08-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--HP08-d3.png) |
| d4 | wine bottle | [PNG](../masks/diverse-v3--HP08-d4.png) |
| d5 | wine bottle | [PNG](../masks/diverse-v3--HP08-d5.png) |
| d6 | wine bottle | [PNG](../masks/diverse-v3--HP08-d6.png) |
| d7 | wine bottle | [PNG](../masks/diverse-v3--HP08-d7.png) |
| d8 | wine bottle | [PNG](../masks/diverse-v3--HP08-d8.png) |
| d9 | wine bottle | [PNG](../masks/diverse-v3--HP08-d9.png) |
| d10 | wine bottle | [PNG](../masks/diverse-v3--HP08-d10.png) |
| d11 | wine bottle | [PNG](../masks/diverse-v3--HP08-d11.png) |
| d12 | wine bottle | [PNG](../masks/diverse-v3--HP08-d12.png) |
| d13 | wine bottle | [PNG](../masks/diverse-v3--HP08-d13.png) |
| d14 | wine bottle | [PNG](../masks/diverse-v3--HP08-d14.png) |
| d15 | wine bottle | [PNG](../masks/diverse-v3--HP08-d15.png) |
| d16 | wine bottle | [PNG](../masks/diverse-v3--HP08-d16.png) |
| d17 | wine bottle | [PNG](../masks/diverse-v3--HP08-d17.png) |
| d18 | wine bottle | [PNG](../masks/diverse-v3--HP08-d18.png) |
| d19 | wine bottle | [PNG](../masks/diverse-v3--HP08-d19.png) |
| d20 | wine bottle | [PNG](../masks/diverse-v3--HP08-d20.png) |
| d21 | wine bottle | [PNG](../masks/diverse-v3--HP08-d21.png) |
| d22 | wine bottle | [PNG](../masks/diverse-v3--HP08-d22.png) |
| d23 | wine bottle | [PNG](../masks/diverse-v3--HP08-d23.png) |
| d24 | wine bottle | [PNG](../masks/diverse-v3--HP08-d24.png) |
| d25 | wine bottle | [PNG](../masks/diverse-v3--HP08-d25.png) |
| d26 | wine bottle | [PNG](../masks/diverse-v3--HP08-d26.png) |
| d27 | wine bottle | [PNG](../masks/diverse-v3--HP08-d27.png) |
| d28 | wine label | [PNG](../masks/diverse-v3--HP08-d28.png) |
| d29 | wine label | [PNG](../masks/diverse-v3--HP08-d29.png) |
| d30 | wine label | [PNG](../masks/diverse-v3--HP08-d30.png) |
| d31 | wine label | [PNG](../masks/diverse-v3--HP08-d31.png) |
| d32 | wine label | [PNG](../masks/diverse-v3--HP08-d32.png) |
| d33 | wine label | [PNG](../masks/diverse-v3--HP08-d33.png) |
| d34 | wine label | [PNG](../masks/diverse-v3--HP08-d34.png) |
| d35 | wine label | [PNG](../masks/diverse-v3--HP08-d35.png) |
| d36 | wine label | [PNG](../masks/diverse-v3--HP08-d36.png) |
| d37 | wine label | [PNG](../masks/diverse-v3--HP08-d37.png) |
| d38 | wine label | [PNG](../masks/diverse-v3--HP08-d38.png) |
| d39 | hand | [PNG](../masks/diverse-v3--HP08-d39.png) |
| d40 | hand | [PNG](../masks/diverse-v3--HP08-d40.png) |
| d41 | price tag | [PNG](../masks/diverse-v3--HP08-d41.png) |
| d42 | price tag | [PNG](../masks/diverse-v3--HP08-d42.png) |
| d43 | price tag | [PNG](../masks/diverse-v3--HP08-d43.png) |
| d44 | price tag | [PNG](../masks/diverse-v3--HP08-d44.png) |
| d45 | price tag | [PNG](../masks/diverse-v3--HP08-d45.png) |
| d46 | price tag | [PNG](../masks/diverse-v3--HP08-d46.png) |
| d47 | price tag | [PNG](../masks/diverse-v3--HP08-d47.png) |
| d48 | price tag | [PNG](../masks/diverse-v3--HP08-d48.png) |
| d49 | price tag | [PNG](../masks/diverse-v3--HP08-d49.png) |
| d50 | price tag | [PNG](../masks/diverse-v3--HP08-d50.png) |
| d51 | price tag | [PNG](../masks/diverse-v3--HP08-d51.png) |
| d52 | price tag | [PNG](../masks/diverse-v3--HP08-d52.png) |
| d53 | price tag | [PNG](../masks/diverse-v3--HP08-d53.png) |
| d54 | price tag | [PNG](../masks/diverse-v3--HP08-d54.png) |
| d55 | price tag | [PNG](../masks/diverse-v3--HP08-d55.png) |
| d56 | price tag | [PNG](../masks/diverse-v3--HP08-d56.png) |
| d57 | price tag | [PNG](../masks/diverse-v3--HP08-d57.png) |
| d58 | price tag | [PNG](../masks/diverse-v3--HP08-d58.png) |
| d59 | price tag | [PNG](../masks/diverse-v3--HP08-d59.png) |
| d60 | price tag | [PNG](../masks/diverse-v3--HP08-d60.png) |
| d61 | price tag | [PNG](../masks/diverse-v3--HP08-d61.png) |
| d62 | price tag | [PNG](../masks/diverse-v3--HP08-d62.png) |
| d63 | price tag | [PNG](../masks/diverse-v3--HP08-d63.png) |
| d64 | price tag | [PNG](../masks/diverse-v3--HP08-d64.png) |
| d65 | price tag | [PNG](../masks/diverse-v3--HP08-d65.png) |
| d66 | price tag | [PNG](../masks/diverse-v3--HP08-d66.png) |
| d67 | wine glass | [PNG](../masks/diverse-v3--HP08-d67.png) |
| d68 | wine glass | [PNG](../masks/diverse-v3--HP08-d68.png) |
| d69 | wine glass | [PNG](../masks/diverse-v3--HP08-d69.png) |
| d70 | wine glass | [PNG](../masks/diverse-v3--HP08-d70.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--HP08.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d71 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP08-d71.png) |
| d72 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP08-d72.png) |
| d73 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP08-d73.png) |
| d74 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP08-d74.png) |
| d75 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP08-d75.png) |

[Raw frozen detector response](../detections/diverse-v3--HP08.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate exactly ONE independent candid smartphone photograph. Show believable glass, paper, natural material imperfections, fictional wine branding, and anatomically plausible hands. No collage, grid, arrows, annotations, bounding boxes, highlights, watermark, UI overlay, or explanatory caption. Text is allowed on physical objects within the scene. Keep the target visible front label entirely inside the frame unless partial occlusion or close-up is explicitly requested. Image format: portrait 2:3, approximately 1024 by 1536 pixels. Setting: inside a real wine cellar. Use stone or brick walls, wooden wine racks, storage cubbies, a cellar tasting table and practical dim lights. Background wine bottles may be present on shelves but should remain clearly in the background. Viewpoint: the customer is examining a wine bottle in their own hand while shopping or browsing the cellar, with the bottle front label turned toward the phone camera. Show the bottle, the holding hand and enough surrounding shelves or cellar details to establish the location. Scene details: Two bottles on a table. The LEFT green-label bottle is firmly gripped at mid-body by a hand from left. A transparent empty wine glass stands before the unheld RIGHT bottle, refracting the image of another relaxed hand resting well behind it. Separate physical contact from optical overlap.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Винный погреб. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
