# main-selector-imagegen-diverse-v3-20261020:PN07

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): Указание при двух видимых руках

Reference target description (source): Правая бутылка с белой этикеткой

Expected intent: `clear`. Accepted target proposals: `d45`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:PN07`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--PN07.png)

![Proposed target overlay](../target-overlays/diverse-v3--PN07.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--PN07-d45.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d12; reason: existing_scene_v1_rank; mode: legacy; crop 215×800 px. Target agreement: False. Target retention proxy: 0.0%; maximum other-bottle retention: 99.9%; minimum associated label retention: 0.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--PN07-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PN07-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--PN07-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d62: 0.0%, 6285 source pixels; d79: 0.0%, 39655 source pixels

### semantic-v2: FAIL — provisional target/proxy

Selected: d41; reason: unique_visible_hand_contact; mode: confident; crop 37×150 px. Target agreement: False. Target retention proxy: 0.0%; maximum other-bottle retention: 97.7%; minimum associated label retention: 0.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d69 100.0%.

![semantic-v2 crop](../crops/diverse-v3--PN07-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PN07-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--PN07-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--PN07-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d62: 0.0%, 6285 source pixels; d79: 0.0%, 39655 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1536×908 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 100.0%; minimum associated label retention: 99.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--PN07-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PN07-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--PN07-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d62: 99.0%, 6285 source pixels; d79: 100.0%, 39655 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--PN07-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--PN07-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--PN07-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--PN07-d3.png) |
| d4 | wine bottle | [PNG](../masks/diverse-v3--PN07-d4.png) |
| d5 | wine bottle | [PNG](../masks/diverse-v3--PN07-d5.png) |
| d6 | wine bottle | [PNG](../masks/diverse-v3--PN07-d6.png) |
| d7 | wine bottle | [PNG](../masks/diverse-v3--PN07-d7.png) |
| d8 | wine bottle | [PNG](../masks/diverse-v3--PN07-d8.png) |
| d9 | wine bottle | [PNG](../masks/diverse-v3--PN07-d9.png) |
| d10 | wine bottle | [PNG](../masks/diverse-v3--PN07-d10.png) |
| d11 | wine bottle | [PNG](../masks/diverse-v3--PN07-d11.png) |
| d12 | wine bottle | [PNG](../masks/diverse-v3--PN07-d12.png) |
| d13 | wine bottle | [PNG](../masks/diverse-v3--PN07-d13.png) |
| d14 | wine bottle | [PNG](../masks/diverse-v3--PN07-d14.png) |
| d15 | wine bottle | [PNG](../masks/diverse-v3--PN07-d15.png) |
| d16 | wine bottle | [PNG](../masks/diverse-v3--PN07-d16.png) |
| d17 | wine bottle | [PNG](../masks/diverse-v3--PN07-d17.png) |
| d18 | wine bottle | [PNG](../masks/diverse-v3--PN07-d18.png) |
| d19 | wine bottle | [PNG](../masks/diverse-v3--PN07-d19.png) |
| d20 | wine bottle | [PNG](../masks/diverse-v3--PN07-d20.png) |
| d21 | wine bottle | [PNG](../masks/diverse-v3--PN07-d21.png) |
| d22 | wine bottle | [PNG](../masks/diverse-v3--PN07-d22.png) |
| d23 | wine bottle | [PNG](../masks/diverse-v3--PN07-d23.png) |
| d24 | wine bottle | [PNG](../masks/diverse-v3--PN07-d24.png) |
| d25 | wine bottle | [PNG](../masks/diverse-v3--PN07-d25.png) |
| d26 | wine bottle | [PNG](../masks/diverse-v3--PN07-d26.png) |
| d27 | wine bottle | [PNG](../masks/diverse-v3--PN07-d27.png) |
| d28 | wine bottle | [PNG](../masks/diverse-v3--PN07-d28.png) |
| d29 | wine bottle | [PNG](../masks/diverse-v3--PN07-d29.png) |
| d30 | wine bottle | [PNG](../masks/diverse-v3--PN07-d30.png) |
| d31 | wine bottle | [PNG](../masks/diverse-v3--PN07-d31.png) |
| d32 | wine bottle | [PNG](../masks/diverse-v3--PN07-d32.png) |
| d33 | wine bottle | [PNG](../masks/diverse-v3--PN07-d33.png) |
| d34 | wine bottle | [PNG](../masks/diverse-v3--PN07-d34.png) |
| d35 | wine bottle | [PNG](../masks/diverse-v3--PN07-d35.png) |
| d36 | wine bottle | [PNG](../masks/diverse-v3--PN07-d36.png) |
| d37 | wine bottle | [PNG](../masks/diverse-v3--PN07-d37.png) |
| d38 | wine bottle | [PNG](../masks/diverse-v3--PN07-d38.png) |
| d39 | wine bottle | [PNG](../masks/diverse-v3--PN07-d39.png) |
| d40 | wine bottle | [PNG](../masks/diverse-v3--PN07-d40.png) |
| d41 | wine bottle | [PNG](../masks/diverse-v3--PN07-d41.png) |
| d42 | wine bottle | [PNG](../masks/diverse-v3--PN07-d42.png) |
| d43 | wine bottle | [PNG](../masks/diverse-v3--PN07-d43.png) |
| d44 | wine bottle | [PNG](../masks/diverse-v3--PN07-d44.png) |
| d45 | wine bottle | [PNG](../masks/diverse-v3--PN07-d45.png) |
| d46 | wine bottle | [PNG](../masks/diverse-v3--PN07-d46.png) |
| d47 | wine bottle | [PNG](../masks/diverse-v3--PN07-d47.png) |
| d48 | wine bottle | [PNG](../masks/diverse-v3--PN07-d48.png) |
| d49 | wine bottle | [PNG](../masks/diverse-v3--PN07-d49.png) |
| d50 | wine bottle | [PNG](../masks/diverse-v3--PN07-d50.png) |
| d51 | wine bottle | [PNG](../masks/diverse-v3--PN07-d51.png) |
| d52 | wine bottle | [PNG](../masks/diverse-v3--PN07-d52.png) |
| d53 | wine bottle | [PNG](../masks/diverse-v3--PN07-d53.png) |
| d54 | wine bottle | [PNG](../masks/diverse-v3--PN07-d54.png) |
| d55 | wine label | [PNG](../masks/diverse-v3--PN07-d55.png) |
| d56 | wine label | [PNG](../masks/diverse-v3--PN07-d56.png) |
| d57 | wine label | [PNG](../masks/diverse-v3--PN07-d57.png) |
| d58 | wine label | [PNG](../masks/diverse-v3--PN07-d58.png) |
| d59 | wine label | [PNG](../masks/diverse-v3--PN07-d59.png) |
| d60 | wine label | [PNG](../masks/diverse-v3--PN07-d60.png) |
| d61 | wine label | [PNG](../masks/diverse-v3--PN07-d61.png) |
| d62 | wine label | [PNG](../masks/diverse-v3--PN07-d62.png) |
| d63 | wine label | [PNG](../masks/diverse-v3--PN07-d63.png) |
| d64 | wine label | [PNG](../masks/diverse-v3--PN07-d64.png) |
| d65 | wine label | [PNG](../masks/diverse-v3--PN07-d65.png) |
| d66 | wine label | [PNG](../masks/diverse-v3--PN07-d66.png) |
| d67 | wine label | [PNG](../masks/diverse-v3--PN07-d67.png) |
| d68 | wine label | [PNG](../masks/diverse-v3--PN07-d68.png) |
| d69 | wine label | [PNG](../masks/diverse-v3--PN07-d69.png) |
| d70 | wine label | [PNG](../masks/diverse-v3--PN07-d70.png) |
| d71 | wine label | [PNG](../masks/diverse-v3--PN07-d71.png) |
| d72 | wine label | [PNG](../masks/diverse-v3--PN07-d72.png) |
| d73 | wine label | [PNG](../masks/diverse-v3--PN07-d73.png) |
| d74 | wine label | [PNG](../masks/diverse-v3--PN07-d74.png) |
| d75 | wine label | [PNG](../masks/diverse-v3--PN07-d75.png) |
| d76 | wine label | [PNG](../masks/diverse-v3--PN07-d76.png) |
| d77 | wine label | [PNG](../masks/diverse-v3--PN07-d77.png) |
| d78 | wine label | [PNG](../masks/diverse-v3--PN07-d78.png) |
| d79 | wine label | [PNG](../masks/diverse-v3--PN07-d79.png) |
| d80 | wine label | [PNG](../masks/diverse-v3--PN07-d80.png) |
| d81 | wine label | [PNG](../masks/diverse-v3--PN07-d81.png) |
| d82 | wine label | [PNG](../masks/diverse-v3--PN07-d82.png) |
| d83 | wine label | [PNG](../masks/diverse-v3--PN07-d83.png) |
| d84 | wine label | [PNG](../masks/diverse-v3--PN07-d84.png) |
| d85 | wine label | [PNG](../masks/diverse-v3--PN07-d85.png) |
| d86 | wine label | [PNG](../masks/diverse-v3--PN07-d86.png) |
| d87 | wine label | [PNG](../masks/diverse-v3--PN07-d87.png) |
| d88 | wine label | [PNG](../masks/diverse-v3--PN07-d88.png) |
| d89 | wine label | [PNG](../masks/diverse-v3--PN07-d89.png) |
| d90 | wine label | [PNG](../masks/diverse-v3--PN07-d90.png) |
| d91 | wine label | [PNG](../masks/diverse-v3--PN07-d91.png) |
| d92 | wine label | [PNG](../masks/diverse-v3--PN07-d92.png) |
| d93 | wine label | [PNG](../masks/diverse-v3--PN07-d93.png) |
| d94 | wine label | [PNG](../masks/diverse-v3--PN07-d94.png) |
| d95 | wine label | [PNG](../masks/diverse-v3--PN07-d95.png) |
| d96 | wine label | [PNG](../masks/diverse-v3--PN07-d96.png) |
| d97 | wine label | [PNG](../masks/diverse-v3--PN07-d97.png) |
| d98 | wine label | [PNG](../masks/diverse-v3--PN07-d98.png) |
| d99 | wine label | [PNG](../masks/diverse-v3--PN07-d99.png) |
| d100 | wine label | [PNG](../masks/diverse-v3--PN07-d100.png) |
| d101 | wine label | [PNG](../masks/diverse-v3--PN07-d101.png) |
| d102 | wine label | [PNG](../masks/diverse-v3--PN07-d102.png) |
| d103 | wine label | [PNG](../masks/diverse-v3--PN07-d103.png) |
| d104 | wine label | [PNG](../masks/diverse-v3--PN07-d104.png) |
| d105 | hand | [PNG](../masks/diverse-v3--PN07-d105.png) |
| d106 | hand | [PNG](../masks/diverse-v3--PN07-d106.png) |
| d107 | box | [PNG](../masks/diverse-v3--PN07-d107.png) |
| d108 | box | [PNG](../masks/diverse-v3--PN07-d108.png) |
| d109 | box | [PNG](../masks/diverse-v3--PN07-d109.png) |
| d110 | box | [PNG](../masks/diverse-v3--PN07-d110.png) |
| d111 | box | [PNG](../masks/diverse-v3--PN07-d111.png) |
| d112 | box | [PNG](../masks/diverse-v3--PN07-d112.png) |
| d113 | box | [PNG](../masks/diverse-v3--PN07-d113.png) |
| d114 | box | [PNG](../masks/diverse-v3--PN07-d114.png) |
| d115 | box | [PNG](../masks/diverse-v3--PN07-d115.png) |
| d116 | box | [PNG](../masks/diverse-v3--PN07-d116.png) |
| d117 | box | [PNG](../masks/diverse-v3--PN07-d117.png) |
| d118 | box | [PNG](../masks/diverse-v3--PN07-d118.png) |
| d119 | price tag | [PNG](../masks/diverse-v3--PN07-d119.png) |
| d120 | price tag | [PNG](../masks/diverse-v3--PN07-d120.png) |
| d121 | price tag | [PNG](../masks/diverse-v3--PN07-d121.png) |
| d122 | price tag | [PNG](../masks/diverse-v3--PN07-d122.png) |
| d123 | price tag | [PNG](../masks/diverse-v3--PN07-d123.png) |
| d124 | price tag | [PNG](../masks/diverse-v3--PN07-d124.png) |
| d125 | price tag | [PNG](../masks/diverse-v3--PN07-d125.png) |
| d126 | price tag | [PNG](../masks/diverse-v3--PN07-d126.png) |
| d127 | price tag | [PNG](../masks/diverse-v3--PN07-d127.png) |
| d128 | price tag | [PNG](../masks/diverse-v3--PN07-d128.png) |
| d129 | price tag | [PNG](../masks/diverse-v3--PN07-d129.png) |
| d130 | price tag | [PNG](../masks/diverse-v3--PN07-d130.png) |
| d131 | price tag | [PNG](../masks/diverse-v3--PN07-d131.png) |
| d132 | price tag | [PNG](../masks/diverse-v3--PN07-d132.png) |
| d133 | wine glass | [PNG](../masks/diverse-v3--PN07-d133.png) |

[Raw frozen detector response](../detections/diverse-v3--PN07.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate exactly ONE independent candid smartphone photograph. Show believable glass, paper, natural material imperfections, fictional wine branding, and anatomically plausible hands. No collage, grid, arrows, annotations, bounding boxes, highlights, watermark, UI overlay, or explanatory caption. Text is allowed on physical objects within the scene. Keep the target visible front label entirely inside the frame unless partial occlusion or close-up is explicitly requested. Image format: landscape 3:2, approximately 1536 by 1024 pixels. Setting: inside a real wine store. Use a shop tasting counter, bottle shelves with small price strips, retail aisle details and natural store lighting. Keep the described foreground inventory; background racks may be empty or softly blurred. Scene details: Three bottles on a tasting table. A RIGHT foreground hand with visible palm points down at the rightmost white-label bottle. A different relaxed open hand rests far left on the table, separated from all bottles. Neither hand grips a bottle. The middle bottle is visually larger.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Винный магазин. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
