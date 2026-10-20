# main-selector-imagegen-diverse-v3-20261020:PD09

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--PD09.jpg)

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): В руке: бутылка и вырезанная реклама

Reference target description (source): Удерживаемая настоящая бутылка справа от картонной фигуры

Expected intent: `clear`. Accepted target proposals: `d20`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:PD09`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--PD09.png)

![Proposed target overlay](../target-overlays/diverse-v3--PD09.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--PD09-d20.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d20; reason: existing_scene_v1_rank; mode: legacy; crop 347×965 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 93.1%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--PD09-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PD09-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--PD09-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d69: 93.1%, 111906 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d20; reason: unique_visible_hand_contact; mode: confident; crop 375×1003 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d69 100.0%.

![semantic-v2 crop](../crops/diverse-v3--PD09-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PD09-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--PD09-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--PD09-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d69: 100.0%, 111906 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 917×1024 px. Target agreement: n/a (no native target ID). Target retention proxy: 94.1%; maximum other-bottle retention: 99.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--PD09-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PD09-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--PD09-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d69: 100.0%, 111906 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--PD09-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--PD09-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--PD09-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--PD09-d3.png) |
| d4 | wine bottle | [PNG](../masks/diverse-v3--PD09-d4.png) |
| d5 | wine bottle | [PNG](../masks/diverse-v3--PD09-d5.png) |
| d6 | wine bottle | [PNG](../masks/diverse-v3--PD09-d6.png) |
| d7 | wine bottle | [PNG](../masks/diverse-v3--PD09-d7.png) |
| d8 | wine bottle | [PNG](../masks/diverse-v3--PD09-d8.png) |
| d9 | wine bottle | [PNG](../masks/diverse-v3--PD09-d9.png) |
| d10 | wine bottle | [PNG](../masks/diverse-v3--PD09-d10.png) |
| d11 | wine bottle | [PNG](../masks/diverse-v3--PD09-d11.png) |
| d12 | wine bottle | [PNG](../masks/diverse-v3--PD09-d12.png) |
| d13 | wine bottle | [PNG](../masks/diverse-v3--PD09-d13.png) |
| d14 | wine bottle | [PNG](../masks/diverse-v3--PD09-d14.png) |
| d15 | wine bottle | [PNG](../masks/diverse-v3--PD09-d15.png) |
| d16 | wine bottle | [PNG](../masks/diverse-v3--PD09-d16.png) |
| d17 | wine bottle | [PNG](../masks/diverse-v3--PD09-d17.png) |
| d18 | wine bottle | [PNG](../masks/diverse-v3--PD09-d18.png) |
| d19 | wine bottle | [PNG](../masks/diverse-v3--PD09-d19.png) |
| d20 | wine bottle | [PNG](../masks/diverse-v3--PD09-d20.png) |
| d21 | wine bottle | [PNG](../masks/diverse-v3--PD09-d21.png) |
| d22 | wine bottle | [PNG](../masks/diverse-v3--PD09-d22.png) |
| d23 | wine bottle | [PNG](../masks/diverse-v3--PD09-d23.png) |
| d24 | wine bottle | [PNG](../masks/diverse-v3--PD09-d24.png) |
| d25 | wine bottle | [PNG](../masks/diverse-v3--PD09-d25.png) |
| d26 | wine bottle | [PNG](../masks/diverse-v3--PD09-d26.png) |
| d27 | wine bottle | [PNG](../masks/diverse-v3--PD09-d27.png) |
| d28 | wine bottle | [PNG](../masks/diverse-v3--PD09-d28.png) |
| d29 | wine bottle | [PNG](../masks/diverse-v3--PD09-d29.png) |
| d30 | wine bottle | [PNG](../masks/diverse-v3--PD09-d30.png) |
| d31 | wine bottle | [PNG](../masks/diverse-v3--PD09-d31.png) |
| d32 | wine bottle | [PNG](../masks/diverse-v3--PD09-d32.png) |
| d33 | wine bottle | [PNG](../masks/diverse-v3--PD09-d33.png) |
| d34 | wine bottle | [PNG](../masks/diverse-v3--PD09-d34.png) |
| d35 | wine bottle | [PNG](../masks/diverse-v3--PD09-d35.png) |
| d36 | wine bottle | [PNG](../masks/diverse-v3--PD09-d36.png) |
| d37 | wine bottle | [PNG](../masks/diverse-v3--PD09-d37.png) |
| d38 | wine bottle | [PNG](../masks/diverse-v3--PD09-d38.png) |
| d39 | wine bottle | [PNG](../masks/diverse-v3--PD09-d39.png) |
| d40 | wine bottle | [PNG](../masks/diverse-v3--PD09-d40.png) |
| d41 | wine bottle | [PNG](../masks/diverse-v3--PD09-d41.png) |
| d42 | wine bottle | [PNG](../masks/diverse-v3--PD09-d42.png) |
| d43 | wine bottle | [PNG](../masks/diverse-v3--PD09-d43.png) |
| d44 | wine bottle | [PNG](../masks/diverse-v3--PD09-d44.png) |
| d45 | wine bottle | [PNG](../masks/diverse-v3--PD09-d45.png) |
| d46 | wine bottle | [PNG](../masks/diverse-v3--PD09-d46.png) |
| d47 | wine label | [PNG](../masks/diverse-v3--PD09-d47.png) |
| d48 | wine label | [PNG](../masks/diverse-v3--PD09-d48.png) |
| d49 | wine label | [PNG](../masks/diverse-v3--PD09-d49.png) |
| d50 | wine label | [PNG](../masks/diverse-v3--PD09-d50.png) |
| d51 | wine label | [PNG](../masks/diverse-v3--PD09-d51.png) |
| d52 | wine label | [PNG](../masks/diverse-v3--PD09-d52.png) |
| d53 | wine label | [PNG](../masks/diverse-v3--PD09-d53.png) |
| d54 | wine label | [PNG](../masks/diverse-v3--PD09-d54.png) |
| d55 | wine label | [PNG](../masks/diverse-v3--PD09-d55.png) |
| d56 | wine label | [PNG](../masks/diverse-v3--PD09-d56.png) |
| d57 | wine label | [PNG](../masks/diverse-v3--PD09-d57.png) |
| d58 | wine label | [PNG](../masks/diverse-v3--PD09-d58.png) |
| d59 | wine label | [PNG](../masks/diverse-v3--PD09-d59.png) |
| d60 | wine label | [PNG](../masks/diverse-v3--PD09-d60.png) |
| d61 | wine label | [PNG](../masks/diverse-v3--PD09-d61.png) |
| d62 | wine label | [PNG](../masks/diverse-v3--PD09-d62.png) |
| d63 | wine label | [PNG](../masks/diverse-v3--PD09-d63.png) |
| d64 | wine label | [PNG](../masks/diverse-v3--PD09-d64.png) |
| d65 | wine label | [PNG](../masks/diverse-v3--PD09-d65.png) |
| d66 | wine label | [PNG](../masks/diverse-v3--PD09-d66.png) |
| d67 | wine label | [PNG](../masks/diverse-v3--PD09-d67.png) |
| d68 | wine label | [PNG](../masks/diverse-v3--PD09-d68.png) |
| d69 | wine label | [PNG](../masks/diverse-v3--PD09-d69.png) |
| d70 | wine label | [PNG](../masks/diverse-v3--PD09-d70.png) |
| d71 | hand | [PNG](../masks/diverse-v3--PD09-d71.png) |
| d72 | price tag | [PNG](../masks/diverse-v3--PD09-d72.png) |
| d73 | price tag | [PNG](../masks/diverse-v3--PD09-d73.png) |
| d74 | price tag | [PNG](../masks/diverse-v3--PD09-d74.png) |
| d75 | price tag | [PNG](../masks/diverse-v3--PD09-d75.png) |
| d76 | price tag | [PNG](../masks/diverse-v3--PD09-d76.png) |
| d77 | price tag | [PNG](../masks/diverse-v3--PD09-d77.png) |
| d78 | price tag | [PNG](../masks/diverse-v3--PD09-d78.png) |
| d79 | price tag | [PNG](../masks/diverse-v3--PD09-d79.png) |
| d80 | price tag | [PNG](../masks/diverse-v3--PD09-d80.png) |
| d81 | price tag | [PNG](../masks/diverse-v3--PD09-d81.png) |
| d82 | price tag | [PNG](../masks/diverse-v3--PD09-d82.png) |
| d83 | price tag | [PNG](../masks/diverse-v3--PD09-d83.png) |
| d84 | price tag | [PNG](../masks/diverse-v3--PD09-d84.png) |
| d85 | price tag | [PNG](../masks/diverse-v3--PD09-d85.png) |
| d86 | price tag | [PNG](../masks/diverse-v3--PD09-d86.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--PD09.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d87 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d87.png) |
| d88 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d88.png) |
| d89 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d89.png) |
| d90 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d90.png) |
| d91 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d91.png) |
| d92 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d92.png) |
| d93 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d93.png) |
| d94 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d94.png) |
| d95 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d95.png) |
| d96 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d96.png) |
| d97 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d97.png) |
| d98 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d98.png) |
| d99 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d99.png) |
| d100 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d100.png) |
| d101 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d101.png) |
| d102 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d102.png) |
| d103 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d103.png) |
| d104 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d104.png) |
| d105 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d105.png) |
| d106 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d106.png) |
| d107 | bottle held in hand | [PNG](../context-masks/diverse-v3--PD09-d107.png) |

[Raw frozen detector response](../detections/diverse-v3--PD09.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate exactly ONE independent candid smartphone photograph. Show believable glass, paper, natural material imperfections, fictional wine branding, and anatomically plausible hands. No collage, grid, arrows, annotations, bounding boxes, highlights, watermark, UI overlay, or explanatory caption. Text is allowed on physical objects within the scene. Keep the target visible front label entirely inside the frame unless partial occlusion or close-up is explicitly requested. Image format: landscape 3:2, approximately 1536 by 1024 pixels. Setting: inside a real wine store. Use a shop tasting counter, bottle shelves with small price strips, retail aisle details and natural store lighting. Keep the described foreground inventory; background racks may be empty or softly blurred. Viewpoint: the customer is examining a wine bottle in their own hand while shopping or browsing the cellar, with the bottle front label turned toward the phone camera. Show the bottle, the holding hand and enough surrounding shelves or cellar details to establish the location. Scene details: One real pale-green bottle with pink label stands RIGHT. LEFT of it is a life-size cardboard bottle-shaped advertising cutout, held upright by a clearly visible folded cardboard stand and thin flat edge. The cutout has a bright dark-red printed label. No extra foreground real bottles. A visible hand from right firmly grips the REAL bottle around its mid-body, with thumb opposing curled fingers, presenting its visible label toward the phone. The graphic bottle remains on its flat medium.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Винный магазин. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
