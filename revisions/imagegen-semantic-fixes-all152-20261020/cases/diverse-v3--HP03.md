# main-selector-imagegen-diverse-v3-20261020:HP03

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--HP03.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Хват и рука возле горлышка

Reference target description (source): Удерживаемая средняя бутылка

Expected intent: `clear`. Accepted target proposals: `d48`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:HP03`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--HP03.png)

![Proposed target overlay](../target-overlays/diverse-v3--HP03.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--HP03-d48.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d48; reason: existing_scene_v1_rank; mode: legacy; crop 264×971 px. Target agreement: True. Target retention proxy: 99.9%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.9%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--HP03-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--HP03-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--HP03-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d97: 99.9%, 97769 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d48; reason: unique_visible_hand_contact; mode: confident; crop 285×1049 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d97 100.0%.

![semantic-v2 crop](../crops/diverse-v3--HP03-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--HP03-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--HP03-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--HP03-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d97: 100.0%, 97769 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 942×1357 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 100.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--HP03-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--HP03-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--HP03-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d97: 100.0%, 97769 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--HP03-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--HP03-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--HP03-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--HP03-d3.png) |
| d4 | wine bottle | [PNG](../masks/diverse-v3--HP03-d4.png) |
| d5 | wine bottle | [PNG](../masks/diverse-v3--HP03-d5.png) |
| d6 | wine bottle | [PNG](../masks/diverse-v3--HP03-d6.png) |
| d7 | wine bottle | [PNG](../masks/diverse-v3--HP03-d7.png) |
| d8 | wine bottle | [PNG](../masks/diverse-v3--HP03-d8.png) |
| d9 | wine bottle | [PNG](../masks/diverse-v3--HP03-d9.png) |
| d10 | wine bottle | [PNG](../masks/diverse-v3--HP03-d10.png) |
| d11 | wine bottle | [PNG](../masks/diverse-v3--HP03-d11.png) |
| d12 | wine bottle | [PNG](../masks/diverse-v3--HP03-d12.png) |
| d13 | wine bottle | [PNG](../masks/diverse-v3--HP03-d13.png) |
| d14 | wine bottle | [PNG](../masks/diverse-v3--HP03-d14.png) |
| d15 | wine bottle | [PNG](../masks/diverse-v3--HP03-d15.png) |
| d16 | wine bottle | [PNG](../masks/diverse-v3--HP03-d16.png) |
| d17 | wine bottle | [PNG](../masks/diverse-v3--HP03-d17.png) |
| d18 | wine bottle | [PNG](../masks/diverse-v3--HP03-d18.png) |
| d19 | wine bottle | [PNG](../masks/diverse-v3--HP03-d19.png) |
| d20 | wine bottle | [PNG](../masks/diverse-v3--HP03-d20.png) |
| d21 | wine bottle | [PNG](../masks/diverse-v3--HP03-d21.png) |
| d22 | wine bottle | [PNG](../masks/diverse-v3--HP03-d22.png) |
| d23 | wine bottle | [PNG](../masks/diverse-v3--HP03-d23.png) |
| d24 | wine bottle | [PNG](../masks/diverse-v3--HP03-d24.png) |
| d25 | wine bottle | [PNG](../masks/diverse-v3--HP03-d25.png) |
| d26 | wine bottle | [PNG](../masks/diverse-v3--HP03-d26.png) |
| d27 | wine bottle | [PNG](../masks/diverse-v3--HP03-d27.png) |
| d28 | wine bottle | [PNG](../masks/diverse-v3--HP03-d28.png) |
| d29 | wine bottle | [PNG](../masks/diverse-v3--HP03-d29.png) |
| d30 | wine bottle | [PNG](../masks/diverse-v3--HP03-d30.png) |
| d31 | wine bottle | [PNG](../masks/diverse-v3--HP03-d31.png) |
| d32 | wine bottle | [PNG](../masks/diverse-v3--HP03-d32.png) |
| d33 | wine bottle | [PNG](../masks/diverse-v3--HP03-d33.png) |
| d34 | wine bottle | [PNG](../masks/diverse-v3--HP03-d34.png) |
| d35 | wine bottle | [PNG](../masks/diverse-v3--HP03-d35.png) |
| d36 | wine bottle | [PNG](../masks/diverse-v3--HP03-d36.png) |
| d37 | wine bottle | [PNG](../masks/diverse-v3--HP03-d37.png) |
| d38 | wine bottle | [PNG](../masks/diverse-v3--HP03-d38.png) |
| d39 | wine bottle | [PNG](../masks/diverse-v3--HP03-d39.png) |
| d40 | wine bottle | [PNG](../masks/diverse-v3--HP03-d40.png) |
| d41 | wine bottle | [PNG](../masks/diverse-v3--HP03-d41.png) |
| d42 | wine bottle | [PNG](../masks/diverse-v3--HP03-d42.png) |
| d43 | wine bottle | [PNG](../masks/diverse-v3--HP03-d43.png) |
| d44 | wine bottle | [PNG](../masks/diverse-v3--HP03-d44.png) |
| d45 | wine bottle | [PNG](../masks/diverse-v3--HP03-d45.png) |
| d46 | wine bottle | [PNG](../masks/diverse-v3--HP03-d46.png) |
| d47 | wine bottle | [PNG](../masks/diverse-v3--HP03-d47.png) |
| d48 | wine bottle | [PNG](../masks/diverse-v3--HP03-d48.png) |
| d49 | wine bottle | [PNG](../masks/diverse-v3--HP03-d49.png) |
| d50 | wine bottle | [PNG](../masks/diverse-v3--HP03-d50.png) |
| d51 | wine bottle | [PNG](../masks/diverse-v3--HP03-d51.png) |
| d52 | wine bottle | [PNG](../masks/diverse-v3--HP03-d52.png) |
| d53 | wine bottle | [PNG](../masks/diverse-v3--HP03-d53.png) |
| d54 | wine bottle | [PNG](../masks/diverse-v3--HP03-d54.png) |
| d55 | wine bottle | [PNG](../masks/diverse-v3--HP03-d55.png) |
| d56 | wine bottle | [PNG](../masks/diverse-v3--HP03-d56.png) |
| d57 | wine bottle | [PNG](../masks/diverse-v3--HP03-d57.png) |
| d58 | wine bottle | [PNG](../masks/diverse-v3--HP03-d58.png) |
| d59 | wine bottle | [PNG](../masks/diverse-v3--HP03-d59.png) |
| d60 | wine bottle | [PNG](../masks/diverse-v3--HP03-d60.png) |
| d61 | wine bottle | [PNG](../masks/diverse-v3--HP03-d61.png) |
| d62 | wine label | [PNG](../masks/diverse-v3--HP03-d62.png) |
| d63 | wine label | [PNG](../masks/diverse-v3--HP03-d63.png) |
| d64 | wine label | [PNG](../masks/diverse-v3--HP03-d64.png) |
| d65 | wine label | [PNG](../masks/diverse-v3--HP03-d65.png) |
| d66 | wine label | [PNG](../masks/diverse-v3--HP03-d66.png) |
| d67 | wine label | [PNG](../masks/diverse-v3--HP03-d67.png) |
| d68 | wine label | [PNG](../masks/diverse-v3--HP03-d68.png) |
| d69 | wine label | [PNG](../masks/diverse-v3--HP03-d69.png) |
| d70 | wine label | [PNG](../masks/diverse-v3--HP03-d70.png) |
| d71 | wine label | [PNG](../masks/diverse-v3--HP03-d71.png) |
| d72 | wine label | [PNG](../masks/diverse-v3--HP03-d72.png) |
| d73 | wine label | [PNG](../masks/diverse-v3--HP03-d73.png) |
| d74 | wine label | [PNG](../masks/diverse-v3--HP03-d74.png) |
| d75 | wine label | [PNG](../masks/diverse-v3--HP03-d75.png) |
| d76 | wine label | [PNG](../masks/diverse-v3--HP03-d76.png) |
| d77 | wine label | [PNG](../masks/diverse-v3--HP03-d77.png) |
| d78 | wine label | [PNG](../masks/diverse-v3--HP03-d78.png) |
| d79 | wine label | [PNG](../masks/diverse-v3--HP03-d79.png) |
| d80 | wine label | [PNG](../masks/diverse-v3--HP03-d80.png) |
| d81 | wine label | [PNG](../masks/diverse-v3--HP03-d81.png) |
| d82 | wine label | [PNG](../masks/diverse-v3--HP03-d82.png) |
| d83 | wine label | [PNG](../masks/diverse-v3--HP03-d83.png) |
| d84 | wine label | [PNG](../masks/diverse-v3--HP03-d84.png) |
| d85 | wine label | [PNG](../masks/diverse-v3--HP03-d85.png) |
| d86 | wine label | [PNG](../masks/diverse-v3--HP03-d86.png) |
| d87 | wine label | [PNG](../masks/diverse-v3--HP03-d87.png) |
| d88 | wine label | [PNG](../masks/diverse-v3--HP03-d88.png) |
| d89 | wine label | [PNG](../masks/diverse-v3--HP03-d89.png) |
| d90 | wine label | [PNG](../masks/diverse-v3--HP03-d90.png) |
| d91 | wine label | [PNG](../masks/diverse-v3--HP03-d91.png) |
| d92 | wine label | [PNG](../masks/diverse-v3--HP03-d92.png) |
| d93 | wine label | [PNG](../masks/diverse-v3--HP03-d93.png) |
| d94 | wine label | [PNG](../masks/diverse-v3--HP03-d94.png) |
| d95 | wine label | [PNG](../masks/diverse-v3--HP03-d95.png) |
| d96 | wine label | [PNG](../masks/diverse-v3--HP03-d96.png) |
| d97 | wine label | [PNG](../masks/diverse-v3--HP03-d97.png) |
| d98 | wine label | [PNG](../masks/diverse-v3--HP03-d98.png) |
| d99 | wine label | [PNG](../masks/diverse-v3--HP03-d99.png) |
| d100 | wine label | [PNG](../masks/diverse-v3--HP03-d100.png) |
| d101 | wine label | [PNG](../masks/diverse-v3--HP03-d101.png) |
| d102 | wine label | [PNG](../masks/diverse-v3--HP03-d102.png) |
| d103 | wine label | [PNG](../masks/diverse-v3--HP03-d103.png) |
| d104 | wine label | [PNG](../masks/diverse-v3--HP03-d104.png) |
| d105 | wine label | [PNG](../masks/diverse-v3--HP03-d105.png) |
| d106 | hand | [PNG](../masks/diverse-v3--HP03-d106.png) |
| d107 | hand | [PNG](../masks/diverse-v3--HP03-d107.png) |
| d108 | hand | [PNG](../masks/diverse-v3--HP03-d108.png) |
| d109 | box | [PNG](../masks/diverse-v3--HP03-d109.png) |
| d110 | box | [PNG](../masks/diverse-v3--HP03-d110.png) |
| d111 | box | [PNG](../masks/diverse-v3--HP03-d111.png) |
| d112 | box | [PNG](../masks/diverse-v3--HP03-d112.png) |
| d113 | box | [PNG](../masks/diverse-v3--HP03-d113.png) |
| d114 | box | [PNG](../masks/diverse-v3--HP03-d114.png) |
| d115 | box | [PNG](../masks/diverse-v3--HP03-d115.png) |
| d116 | box | [PNG](../masks/diverse-v3--HP03-d116.png) |
| d117 | box | [PNG](../masks/diverse-v3--HP03-d117.png) |
| d118 | box | [PNG](../masks/diverse-v3--HP03-d118.png) |
| d119 | box | [PNG](../masks/diverse-v3--HP03-d119.png) |
| d120 | box | [PNG](../masks/diverse-v3--HP03-d120.png) |
| d121 | box | [PNG](../masks/diverse-v3--HP03-d121.png) |
| d122 | box | [PNG](../masks/diverse-v3--HP03-d122.png) |
| d123 | box | [PNG](../masks/diverse-v3--HP03-d123.png) |
| d124 | box | [PNG](../masks/diverse-v3--HP03-d124.png) |
| d125 | box | [PNG](../masks/diverse-v3--HP03-d125.png) |
| d126 | box | [PNG](../masks/diverse-v3--HP03-d126.png) |
| d127 | box | [PNG](../masks/diverse-v3--HP03-d127.png) |
| d128 | box | [PNG](../masks/diverse-v3--HP03-d128.png) |
| d129 | box | [PNG](../masks/diverse-v3--HP03-d129.png) |
| d130 | box | [PNG](../masks/diverse-v3--HP03-d130.png) |
| d131 | price tag | [PNG](../masks/diverse-v3--HP03-d131.png) |
| d132 | price tag | [PNG](../masks/diverse-v3--HP03-d132.png) |
| d133 | price tag | [PNG](../masks/diverse-v3--HP03-d133.png) |
| d134 | price tag | [PNG](../masks/diverse-v3--HP03-d134.png) |
| d135 | price tag | [PNG](../masks/diverse-v3--HP03-d135.png) |
| d136 | price tag | [PNG](../masks/diverse-v3--HP03-d136.png) |
| d137 | price tag | [PNG](../masks/diverse-v3--HP03-d137.png) |
| d138 | price tag | [PNG](../masks/diverse-v3--HP03-d138.png) |
| d139 | price tag | [PNG](../masks/diverse-v3--HP03-d139.png) |
| d140 | price tag | [PNG](../masks/diverse-v3--HP03-d140.png) |
| d141 | price tag | [PNG](../masks/diverse-v3--HP03-d141.png) |
| d142 | price tag | [PNG](../masks/diverse-v3--HP03-d142.png) |
| d143 | price tag | [PNG](../masks/diverse-v3--HP03-d143.png) |
| d144 | price tag | [PNG](../masks/diverse-v3--HP03-d144.png) |
| d145 | price tag | [PNG](../masks/diverse-v3--HP03-d145.png) |
| d146 | price tag | [PNG](../masks/diverse-v3--HP03-d146.png) |
| d147 | price tag | [PNG](../masks/diverse-v3--HP03-d147.png) |
| d148 | price tag | [PNG](../masks/diverse-v3--HP03-d148.png) |
| d149 | price tag | [PNG](../masks/diverse-v3--HP03-d149.png) |
| d150 | price tag | [PNG](../masks/diverse-v3--HP03-d150.png) |
| d151 | price tag | [PNG](../masks/diverse-v3--HP03-d151.png) |
| d152 | price tag | [PNG](../masks/diverse-v3--HP03-d152.png) |
| d153 | price tag | [PNG](../masks/diverse-v3--HP03-d153.png) |
| d154 | price tag | [PNG](../masks/diverse-v3--HP03-d154.png) |
| d155 | price tag | [PNG](../masks/diverse-v3--HP03-d155.png) |
| d156 | price tag | [PNG](../masks/diverse-v3--HP03-d156.png) |
| d157 | price tag | [PNG](../masks/diverse-v3--HP03-d157.png) |
| d158 | price tag | [PNG](../masks/diverse-v3--HP03-d158.png) |
| d159 | price tag | [PNG](../masks/diverse-v3--HP03-d159.png) |
| d160 | price tag | [PNG](../masks/diverse-v3--HP03-d160.png) |
| d161 | price tag | [PNG](../masks/diverse-v3--HP03-d161.png) |
| d162 | price tag | [PNG](../masks/diverse-v3--HP03-d162.png) |
| d163 | price tag | [PNG](../masks/diverse-v3--HP03-d163.png) |
| d164 | price tag | [PNG](../masks/diverse-v3--HP03-d164.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--HP03.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d165 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d165.png) |
| d166 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d166.png) |
| d167 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d167.png) |
| d168 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d168.png) |
| d169 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d169.png) |
| d170 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d170.png) |
| d171 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d171.png) |
| d172 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d172.png) |
| d173 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d173.png) |
| d174 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d174.png) |
| d175 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d175.png) |
| d176 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d176.png) |
| d177 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d177.png) |
| d178 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d178.png) |
| d179 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d179.png) |
| d180 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d180.png) |
| d181 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d181.png) |
| d182 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d182.png) |
| d183 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d183.png) |
| d184 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d184.png) |
| d185 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d185.png) |
| d186 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d186.png) |
| d187 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d187.png) |
| d188 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d188.png) |
| d189 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d189.png) |
| d190 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d190.png) |
| d191 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d191.png) |
| d192 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d192.png) |
| d193 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d193.png) |
| d194 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP03-d194.png) |

[Raw frozen detector response](../detections/diverse-v3--HP03.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate exactly ONE independent candid smartphone photograph. Show believable glass, paper, natural material imperfections, fictional wine branding, and anatomically plausible hands. No collage, grid, arrows, annotations, bounding boxes, highlights, watermark, UI overlay, or explanatory caption. Text is allowed on physical objects within the scene. Keep the target visible front label entirely inside the frame unless partial occlusion or close-up is explicitly requested. Image format: portrait 2:3, approximately 1024 by 1536 pixels. Setting: inside a real wine store. Use a shop tasting counter, bottle shelves with small price strips, retail aisle details and natural store lighting. Background wine bottles may be present on shelves but should remain clearly in the background. Viewpoint: the customer is examining a wine bottle in their own hand while shopping or browsing the cellar, with the bottle front label turned toward the phone camera. Show the bottle, the holding hand and enough surrounding shelves or cellar details to establish the location. Scene details: Three bottles on a counter. One hand holds the CENTER red-label bottle around its middle, thumb and fingers visible on opposite sides. Another hand reaches behind the left bottle neck but is separated from it by a visible gap; the right bottle is unattended.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Винный магазин. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
