# main-selector-imagegen-diverse-v3-20261020:HP09

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--HP09.jpg)

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): Хват справа и отражение руки

Reference target description (source): Удерживаемая правая бутылка

Expected intent: `clear`. Accepted target proposals: `d34`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:HP09`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--HP09.png)

![Proposed target overlay](../target-overlays/diverse-v3--HP09.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--HP09-d34.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d34; reason: existing_scene_v1_rank; mode: legacy; crop 309×943 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 1.4%; minimum associated label retention: 96.4%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--HP09-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--HP09-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--HP09-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d109: 96.4%, 83819 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d34; reason: unique_visible_hand_contact; mode: confident; crop 336×989 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 1.4%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d109 100.0%.

![semantic-v2 crop](../crops/diverse-v3--HP09-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--HP09-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--HP09-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--HP09-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d109: 100.0%, 83819 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1276×1024 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 98.7%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--HP09-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--HP09-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--HP09-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d109: 100.0%, 83819 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--HP09-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--HP09-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--HP09-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--HP09-d3.png) |
| d4 | wine bottle | [PNG](../masks/diverse-v3--HP09-d4.png) |
| d5 | wine bottle | [PNG](../masks/diverse-v3--HP09-d5.png) |
| d6 | wine bottle | [PNG](../masks/diverse-v3--HP09-d6.png) |
| d7 | wine bottle | [PNG](../masks/diverse-v3--HP09-d7.png) |
| d8 | wine bottle | [PNG](../masks/diverse-v3--HP09-d8.png) |
| d9 | wine bottle | [PNG](../masks/diverse-v3--HP09-d9.png) |
| d10 | wine bottle | [PNG](../masks/diverse-v3--HP09-d10.png) |
| d11 | wine bottle | [PNG](../masks/diverse-v3--HP09-d11.png) |
| d12 | wine bottle | [PNG](../masks/diverse-v3--HP09-d12.png) |
| d13 | wine bottle | [PNG](../masks/diverse-v3--HP09-d13.png) |
| d14 | wine bottle | [PNG](../masks/diverse-v3--HP09-d14.png) |
| d15 | wine bottle | [PNG](../masks/diverse-v3--HP09-d15.png) |
| d16 | wine bottle | [PNG](../masks/diverse-v3--HP09-d16.png) |
| d17 | wine bottle | [PNG](../masks/diverse-v3--HP09-d17.png) |
| d18 | wine bottle | [PNG](../masks/diverse-v3--HP09-d18.png) |
| d19 | wine bottle | [PNG](../masks/diverse-v3--HP09-d19.png) |
| d20 | wine bottle | [PNG](../masks/diverse-v3--HP09-d20.png) |
| d21 | wine bottle | [PNG](../masks/diverse-v3--HP09-d21.png) |
| d22 | wine bottle | [PNG](../masks/diverse-v3--HP09-d22.png) |
| d23 | wine bottle | [PNG](../masks/diverse-v3--HP09-d23.png) |
| d24 | wine bottle | [PNG](../masks/diverse-v3--HP09-d24.png) |
| d25 | wine bottle | [PNG](../masks/diverse-v3--HP09-d25.png) |
| d26 | wine bottle | [PNG](../masks/diverse-v3--HP09-d26.png) |
| d27 | wine bottle | [PNG](../masks/diverse-v3--HP09-d27.png) |
| d28 | wine bottle | [PNG](../masks/diverse-v3--HP09-d28.png) |
| d29 | wine bottle | [PNG](../masks/diverse-v3--HP09-d29.png) |
| d30 | wine bottle | [PNG](../masks/diverse-v3--HP09-d30.png) |
| d31 | wine bottle | [PNG](../masks/diverse-v3--HP09-d31.png) |
| d32 | wine bottle | [PNG](../masks/diverse-v3--HP09-d32.png) |
| d33 | wine bottle | [PNG](../masks/diverse-v3--HP09-d33.png) |
| d34 | wine bottle | [PNG](../masks/diverse-v3--HP09-d34.png) |
| d35 | wine bottle | [PNG](../masks/diverse-v3--HP09-d35.png) |
| d36 | wine bottle | [PNG](../masks/diverse-v3--HP09-d36.png) |
| d37 | wine bottle | [PNG](../masks/diverse-v3--HP09-d37.png) |
| d38 | wine bottle | [PNG](../masks/diverse-v3--HP09-d38.png) |
| d39 | wine bottle | [PNG](../masks/diverse-v3--HP09-d39.png) |
| d40 | wine bottle | [PNG](../masks/diverse-v3--HP09-d40.png) |
| d41 | wine bottle | [PNG](../masks/diverse-v3--HP09-d41.png) |
| d42 | wine bottle | [PNG](../masks/diverse-v3--HP09-d42.png) |
| d43 | wine bottle | [PNG](../masks/diverse-v3--HP09-d43.png) |
| d44 | wine bottle | [PNG](../masks/diverse-v3--HP09-d44.png) |
| d45 | wine bottle | [PNG](../masks/diverse-v3--HP09-d45.png) |
| d46 | wine bottle | [PNG](../masks/diverse-v3--HP09-d46.png) |
| d47 | wine bottle | [PNG](../masks/diverse-v3--HP09-d47.png) |
| d48 | wine bottle | [PNG](../masks/diverse-v3--HP09-d48.png) |
| d49 | wine bottle | [PNG](../masks/diverse-v3--HP09-d49.png) |
| d50 | wine bottle | [PNG](../masks/diverse-v3--HP09-d50.png) |
| d51 | wine bottle | [PNG](../masks/diverse-v3--HP09-d51.png) |
| d52 | wine bottle | [PNG](../masks/diverse-v3--HP09-d52.png) |
| d53 | wine bottle | [PNG](../masks/diverse-v3--HP09-d53.png) |
| d54 | wine bottle | [PNG](../masks/diverse-v3--HP09-d54.png) |
| d55 | wine bottle | [PNG](../masks/diverse-v3--HP09-d55.png) |
| d56 | wine bottle | [PNG](../masks/diverse-v3--HP09-d56.png) |
| d57 | wine bottle | [PNG](../masks/diverse-v3--HP09-d57.png) |
| d58 | wine bottle | [PNG](../masks/diverse-v3--HP09-d58.png) |
| d59 | wine bottle | [PNG](../masks/diverse-v3--HP09-d59.png) |
| d60 | wine bottle | [PNG](../masks/diverse-v3--HP09-d60.png) |
| d61 | wine bottle | [PNG](../masks/diverse-v3--HP09-d61.png) |
| d62 | wine bottle | [PNG](../masks/diverse-v3--HP09-d62.png) |
| d63 | wine bottle | [PNG](../masks/diverse-v3--HP09-d63.png) |
| d64 | wine bottle | [PNG](../masks/diverse-v3--HP09-d64.png) |
| d65 | wine bottle | [PNG](../masks/diverse-v3--HP09-d65.png) |
| d66 | wine bottle | [PNG](../masks/diverse-v3--HP09-d66.png) |
| d67 | wine bottle | [PNG](../masks/diverse-v3--HP09-d67.png) |
| d68 | wine bottle | [PNG](../masks/diverse-v3--HP09-d68.png) |
| d69 | wine bottle | [PNG](../masks/diverse-v3--HP09-d69.png) |
| d70 | wine bottle | [PNG](../masks/diverse-v3--HP09-d70.png) |
| d71 | wine bottle | [PNG](../masks/diverse-v3--HP09-d71.png) |
| d72 | wine bottle | [PNG](../masks/diverse-v3--HP09-d72.png) |
| d73 | wine bottle | [PNG](../masks/diverse-v3--HP09-d73.png) |
| d74 | wine bottle | [PNG](../masks/diverse-v3--HP09-d74.png) |
| d75 | wine bottle | [PNG](../masks/diverse-v3--HP09-d75.png) |
| d76 | wine bottle | [PNG](../masks/diverse-v3--HP09-d76.png) |
| d77 | wine bottle | [PNG](../masks/diverse-v3--HP09-d77.png) |
| d78 | wine bottle | [PNG](../masks/diverse-v3--HP09-d78.png) |
| d79 | wine bottle | [PNG](../masks/diverse-v3--HP09-d79.png) |
| d80 | wine bottle | [PNG](../masks/diverse-v3--HP09-d80.png) |
| d81 | wine bottle | [PNG](../masks/diverse-v3--HP09-d81.png) |
| d82 | wine bottle | [PNG](../masks/diverse-v3--HP09-d82.png) |
| d83 | wine label | [PNG](../masks/diverse-v3--HP09-d83.png) |
| d84 | wine label | [PNG](../masks/diverse-v3--HP09-d84.png) |
| d85 | wine label | [PNG](../masks/diverse-v3--HP09-d85.png) |
| d86 | wine label | [PNG](../masks/diverse-v3--HP09-d86.png) |
| d87 | wine label | [PNG](../masks/diverse-v3--HP09-d87.png) |
| d88 | wine label | [PNG](../masks/diverse-v3--HP09-d88.png) |
| d89 | wine label | [PNG](../masks/diverse-v3--HP09-d89.png) |
| d90 | wine label | [PNG](../masks/diverse-v3--HP09-d90.png) |
| d91 | wine label | [PNG](../masks/diverse-v3--HP09-d91.png) |
| d92 | wine label | [PNG](../masks/diverse-v3--HP09-d92.png) |
| d93 | wine label | [PNG](../masks/diverse-v3--HP09-d93.png) |
| d94 | wine label | [PNG](../masks/diverse-v3--HP09-d94.png) |
| d95 | wine label | [PNG](../masks/diverse-v3--HP09-d95.png) |
| d96 | wine label | [PNG](../masks/diverse-v3--HP09-d96.png) |
| d97 | wine label | [PNG](../masks/diverse-v3--HP09-d97.png) |
| d98 | wine label | [PNG](../masks/diverse-v3--HP09-d98.png) |
| d99 | wine label | [PNG](../masks/diverse-v3--HP09-d99.png) |
| d100 | wine label | [PNG](../masks/diverse-v3--HP09-d100.png) |
| d101 | wine label | [PNG](../masks/diverse-v3--HP09-d101.png) |
| d102 | wine label | [PNG](../masks/diverse-v3--HP09-d102.png) |
| d103 | wine label | [PNG](../masks/diverse-v3--HP09-d103.png) |
| d104 | wine label | [PNG](../masks/diverse-v3--HP09-d104.png) |
| d105 | wine label | [PNG](../masks/diverse-v3--HP09-d105.png) |
| d106 | wine label | [PNG](../masks/diverse-v3--HP09-d106.png) |
| d107 | wine label | [PNG](../masks/diverse-v3--HP09-d107.png) |
| d108 | wine label | [PNG](../masks/diverse-v3--HP09-d108.png) |
| d109 | wine label | [PNG](../masks/diverse-v3--HP09-d109.png) |
| d110 | wine label | [PNG](../masks/diverse-v3--HP09-d110.png) |
| d111 | wine label | [PNG](../masks/diverse-v3--HP09-d111.png) |
| d112 | wine label | [PNG](../masks/diverse-v3--HP09-d112.png) |
| d113 | wine label | [PNG](../masks/diverse-v3--HP09-d113.png) |
| d114 | wine label | [PNG](../masks/diverse-v3--HP09-d114.png) |
| d115 | wine label | [PNG](../masks/diverse-v3--HP09-d115.png) |
| d116 | wine label | [PNG](../masks/diverse-v3--HP09-d116.png) |
| d117 | wine label | [PNG](../masks/diverse-v3--HP09-d117.png) |
| d118 | wine label | [PNG](../masks/diverse-v3--HP09-d118.png) |
| d119 | wine label | [PNG](../masks/diverse-v3--HP09-d119.png) |
| d120 | wine label | [PNG](../masks/diverse-v3--HP09-d120.png) |
| d121 | wine label | [PNG](../masks/diverse-v3--HP09-d121.png) |
| d122 | wine label | [PNG](../masks/diverse-v3--HP09-d122.png) |
| d123 | wine label | [PNG](../masks/diverse-v3--HP09-d123.png) |
| d124 | wine label | [PNG](../masks/diverse-v3--HP09-d124.png) |
| d125 | wine label | [PNG](../masks/diverse-v3--HP09-d125.png) |
| d126 | wine label | [PNG](../masks/diverse-v3--HP09-d126.png) |
| d127 | wine label | [PNG](../masks/diverse-v3--HP09-d127.png) |
| d128 | wine label | [PNG](../masks/diverse-v3--HP09-d128.png) |
| d129 | wine label | [PNG](../masks/diverse-v3--HP09-d129.png) |
| d130 | wine label | [PNG](../masks/diverse-v3--HP09-d130.png) |
| d131 | wine label | [PNG](../masks/diverse-v3--HP09-d131.png) |
| d132 | wine label | [PNG](../masks/diverse-v3--HP09-d132.png) |
| d133 | wine label | [PNG](../masks/diverse-v3--HP09-d133.png) |
| d134 | wine label | [PNG](../masks/diverse-v3--HP09-d134.png) |
| d135 | wine label | [PNG](../masks/diverse-v3--HP09-d135.png) |
| d136 | wine label | [PNG](../masks/diverse-v3--HP09-d136.png) |
| d137 | wine label | [PNG](../masks/diverse-v3--HP09-d137.png) |
| d138 | wine label | [PNG](../masks/diverse-v3--HP09-d138.png) |
| d139 | wine label | [PNG](../masks/diverse-v3--HP09-d139.png) |
| d140 | wine label | [PNG](../masks/diverse-v3--HP09-d140.png) |
| d141 | wine label | [PNG](../masks/diverse-v3--HP09-d141.png) |
| d142 | wine label | [PNG](../masks/diverse-v3--HP09-d142.png) |
| d143 | wine label | [PNG](../masks/diverse-v3--HP09-d143.png) |
| d144 | wine label | [PNG](../masks/diverse-v3--HP09-d144.png) |
| d145 | wine label | [PNG](../masks/diverse-v3--HP09-d145.png) |
| d146 | wine label | [PNG](../masks/diverse-v3--HP09-d146.png) |
| d147 | wine label | [PNG](../masks/diverse-v3--HP09-d147.png) |
| d148 | wine label | [PNG](../masks/diverse-v3--HP09-d148.png) |
| d149 | wine label | [PNG](../masks/diverse-v3--HP09-d149.png) |
| d150 | hand | [PNG](../masks/diverse-v3--HP09-d150.png) |
| d151 | hand | [PNG](../masks/diverse-v3--HP09-d151.png) |
| d152 | box | [PNG](../masks/diverse-v3--HP09-d152.png) |
| d153 | price tag | [PNG](../masks/diverse-v3--HP09-d153.png) |
| d154 | price tag | [PNG](../masks/diverse-v3--HP09-d154.png) |
| d155 | price tag | [PNG](../masks/diverse-v3--HP09-d155.png) |
| d156 | price tag | [PNG](../masks/diverse-v3--HP09-d156.png) |
| d157 | price tag | [PNG](../masks/diverse-v3--HP09-d157.png) |
| d158 | price tag | [PNG](../masks/diverse-v3--HP09-d158.png) |
| d159 | price tag | [PNG](../masks/diverse-v3--HP09-d159.png) |
| d160 | price tag | [PNG](../masks/diverse-v3--HP09-d160.png) |
| d161 | price tag | [PNG](../masks/diverse-v3--HP09-d161.png) |
| d162 | price tag | [PNG](../masks/diverse-v3--HP09-d162.png) |
| d163 | price tag | [PNG](../masks/diverse-v3--HP09-d163.png) |
| d164 | price tag | [PNG](../masks/diverse-v3--HP09-d164.png) |
| d165 | price tag | [PNG](../masks/diverse-v3--HP09-d165.png) |
| d166 | price tag | [PNG](../masks/diverse-v3--HP09-d166.png) |
| d167 | price tag | [PNG](../masks/diverse-v3--HP09-d167.png) |
| d168 | price tag | [PNG](../masks/diverse-v3--HP09-d168.png) |
| d169 | price tag | [PNG](../masks/diverse-v3--HP09-d169.png) |
| d170 | price tag | [PNG](../masks/diverse-v3--HP09-d170.png) |
| d171 | price tag | [PNG](../masks/diverse-v3--HP09-d171.png) |
| d172 | price tag | [PNG](../masks/diverse-v3--HP09-d172.png) |
| d173 | price tag | [PNG](../masks/diverse-v3--HP09-d173.png) |
| d174 | price tag | [PNG](../masks/diverse-v3--HP09-d174.png) |
| d175 | price tag | [PNG](../masks/diverse-v3--HP09-d175.png) |
| d176 | price tag | [PNG](../masks/diverse-v3--HP09-d176.png) |
| d177 | price tag | [PNG](../masks/diverse-v3--HP09-d177.png) |
| d178 | price tag | [PNG](../masks/diverse-v3--HP09-d178.png) |
| d179 | price tag | [PNG](../masks/diverse-v3--HP09-d179.png) |
| d180 | price tag | [PNG](../masks/diverse-v3--HP09-d180.png) |
| d181 | price tag | [PNG](../masks/diverse-v3--HP09-d181.png) |
| d182 | price tag | [PNG](../masks/diverse-v3--HP09-d182.png) |
| d183 | price tag | [PNG](../masks/diverse-v3--HP09-d183.png) |
| d184 | price tag | [PNG](../masks/diverse-v3--HP09-d184.png) |
| d185 | price tag | [PNG](../masks/diverse-v3--HP09-d185.png) |
| d186 | price tag | [PNG](../masks/diverse-v3--HP09-d186.png) |
| d187 | price tag | [PNG](../masks/diverse-v3--HP09-d187.png) |
| d188 | price tag | [PNG](../masks/diverse-v3--HP09-d188.png) |
| d189 | price tag | [PNG](../masks/diverse-v3--HP09-d189.png) |
| d190 | price tag | [PNG](../masks/diverse-v3--HP09-d190.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--HP09.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d191 | mirror | [PNG](../context-masks/diverse-v3--HP09-d191.png) |
| d192 | mirror | [PNG](../context-masks/diverse-v3--HP09-d192.png) |
| d193 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP09-d193.png) |
| d194 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP09-d194.png) |
| d195 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP09-d195.png) |
| d196 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP09-d196.png) |
| d197 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP09-d197.png) |
| d198 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP09-d198.png) |
| d199 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP09-d199.png) |
| d200 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP09-d200.png) |
| d201 | bottle held in hand | [PNG](../context-masks/diverse-v3--HP09-d201.png) |

[Raw frozen detector response](../detections/diverse-v3--HP09.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate exactly ONE independent candid smartphone photograph. Show believable glass, paper, natural material imperfections, fictional wine branding, and anatomically plausible hands. No collage, grid, arrows, annotations, bounding boxes, highlights, watermark, UI overlay, or explanatory caption. Text is allowed on physical objects within the scene. Keep the target visible front label entirely inside the frame unless partial occlusion or close-up is explicitly requested. Image format: landscape 3:2, approximately 1536 by 1024 pixels. Setting: inside a real wine store. Use a shop tasting counter, bottle shelves with small price strips, retail aisle details and natural store lighting. Background wine bottles may be present on shelves but should remain clearly in the background. Viewpoint: the customer is examining a wine bottle in their own hand while shopping or browsing the cellar, with the bottle front label turned toward the phone camera. Show the bottle, the holding hand and enough surrounding shelves or cellar details to establish the location. Scene details: On a counter exactly two real bottles. A hand firmly holds the RIGHT pale-pink-label bottle around body. A small mirror behind the LEFT unheld bottle shows a reflection of the same hand, with visible mirror frame. The reflection does not imply a second physical grip.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Винный магазин. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
