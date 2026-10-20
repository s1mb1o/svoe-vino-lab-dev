# main-selector-imagegen-pilot-v1-20261019:VI04

**Scene confirmed; masks pending. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/pilot-v1--VI04.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Тёмная сцена со светлой этикеткой сзади

Reference target description (source): Удерживаемая передняя бутылка слева

Expected intent: `clear`. Accepted target proposals: `d7`.

Scene group: `main-selector-imagegen-pilot-v1-20261019:VI04`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/pilot-v1--VI04.png)

![Proposed target overlay](../target-overlays/pilot-v1--VI04.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/pilot-v1--VI04-d7.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d7; reason: existing_scene_v1_rank; mode: legacy; crop 452×1020 px. Target agreement: True. Target retention proxy: 99.9%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/pilot-v1--VI04-scene-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--VI04-scene-v1.png) · [Exact decision JSON](../results/pilot-v1--VI04-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d40: 100.0%, 130186 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d7; reason: unique_visible_hand_contact; mode: confident; crop 488×1024 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d40 100.0%.

![semantic-v2 crop](../crops/pilot-v1--VI04-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--VI04-semantic-v2.png) · [Exact decision JSON](../results/pilot-v1--VI04-semantic-v2.json)

Returned label views: [label 1](../label-crops/pilot-v1--VI04-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d40: 100.0%, 130186 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1515×1024 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.9%; maximum other-bottle retention: 92.5%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/pilot-v1--VI04-dis-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--VI04-dis-v1.png) · [Exact decision JSON](../results/pilot-v1--VI04-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d40: 100.0%, 130186 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/pilot-v1--VI04-d0.png) |
| d1 | wine bottle | [PNG](../masks/pilot-v1--VI04-d1.png) |
| d2 | wine bottle | [PNG](../masks/pilot-v1--VI04-d2.png) |
| d3 | wine bottle | [PNG](../masks/pilot-v1--VI04-d3.png) |
| d4 | wine bottle | [PNG](../masks/pilot-v1--VI04-d4.png) |
| d5 | wine bottle | [PNG](../masks/pilot-v1--VI04-d5.png) |
| d6 | wine bottle | [PNG](../masks/pilot-v1--VI04-d6.png) |
| d7 | wine bottle | [PNG](../masks/pilot-v1--VI04-d7.png) |
| d8 | wine bottle | [PNG](../masks/pilot-v1--VI04-d8.png) |
| d9 | wine bottle | [PNG](../masks/pilot-v1--VI04-d9.png) |
| d10 | wine bottle | [PNG](../masks/pilot-v1--VI04-d10.png) |
| d11 | wine bottle | [PNG](../masks/pilot-v1--VI04-d11.png) |
| d12 | wine bottle | [PNG](../masks/pilot-v1--VI04-d12.png) |
| d13 | wine bottle | [PNG](../masks/pilot-v1--VI04-d13.png) |
| d14 | wine bottle | [PNG](../masks/pilot-v1--VI04-d14.png) |
| d15 | wine bottle | [PNG](../masks/pilot-v1--VI04-d15.png) |
| d16 | wine bottle | [PNG](../masks/pilot-v1--VI04-d16.png) |
| d17 | wine bottle | [PNG](../masks/pilot-v1--VI04-d17.png) |
| d18 | wine bottle | [PNG](../masks/pilot-v1--VI04-d18.png) |
| d19 | wine bottle | [PNG](../masks/pilot-v1--VI04-d19.png) |
| d20 | wine bottle | [PNG](../masks/pilot-v1--VI04-d20.png) |
| d21 | wine bottle | [PNG](../masks/pilot-v1--VI04-d21.png) |
| d22 | wine bottle | [PNG](../masks/pilot-v1--VI04-d22.png) |
| d23 | wine bottle | [PNG](../masks/pilot-v1--VI04-d23.png) |
| d24 | wine bottle | [PNG](../masks/pilot-v1--VI04-d24.png) |
| d25 | wine bottle | [PNG](../masks/pilot-v1--VI04-d25.png) |
| d26 | wine label | [PNG](../masks/pilot-v1--VI04-d26.png) |
| d27 | wine label | [PNG](../masks/pilot-v1--VI04-d27.png) |
| d28 | wine label | [PNG](../masks/pilot-v1--VI04-d28.png) |
| d29 | wine label | [PNG](../masks/pilot-v1--VI04-d29.png) |
| d30 | wine label | [PNG](../masks/pilot-v1--VI04-d30.png) |
| d31 | wine label | [PNG](../masks/pilot-v1--VI04-d31.png) |
| d32 | wine label | [PNG](../masks/pilot-v1--VI04-d32.png) |
| d33 | wine label | [PNG](../masks/pilot-v1--VI04-d33.png) |
| d34 | wine label | [PNG](../masks/pilot-v1--VI04-d34.png) |
| d35 | wine label | [PNG](../masks/pilot-v1--VI04-d35.png) |
| d36 | wine label | [PNG](../masks/pilot-v1--VI04-d36.png) |
| d37 | wine label | [PNG](../masks/pilot-v1--VI04-d37.png) |
| d38 | wine label | [PNG](../masks/pilot-v1--VI04-d38.png) |
| d39 | wine label | [PNG](../masks/pilot-v1--VI04-d39.png) |
| d40 | wine label | [PNG](../masks/pilot-v1--VI04-d40.png) |
| d41 | wine label | [PNG](../masks/pilot-v1--VI04-d41.png) |
| d42 | wine label | [PNG](../masks/pilot-v1--VI04-d42.png) |
| d43 | wine label | [PNG](../masks/pilot-v1--VI04-d43.png) |
| d44 | wine label | [PNG](../masks/pilot-v1--VI04-d44.png) |
| d45 | wine label | [PNG](../masks/pilot-v1--VI04-d45.png) |
| d46 | hand | [PNG](../masks/pilot-v1--VI04-d46.png) |
| d47 | hand | [PNG](../masks/pilot-v1--VI04-d47.png) |
| d48 | wine glass | [PNG](../masks/pilot-v1--VI04-d48.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/pilot-v1--VI04.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d49 | bottle held in hand | [PNG](../context-masks/pilot-v1--VI04-d49.png) |
| d50 | bottle held in hand | [PNG](../context-masks/pilot-v1--VI04-d50.png) |
| d51 | bottle held in hand | [PNG](../context-masks/pilot-v1--VI04-d51.png) |

[Raw frozen detector response](../detections/pilot-v1--VI04.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural.
Asset type: one independent synthetic smartphone photograph for a wine-subject selection test dataset.
Style: a believable candid phone photo with realistic optics, materials, shadows, depth and anatomically plausible hands when requested. Natural photographic imperfections, not a diagram, collage, 3D render, advertisement or contact sheet.
Bottle labels may use fictional wine names and normal small wine-label text. Labels must have complete physical paper boundaries and plausible printing. Do not add target markers, bounding boxes, arrows, captions, segmentation colors, watermarks or any explanation outside the scene.
Generate exactly one landscape photograph, approximately 1536 by 1024 pixels. Any wine identity is fictional; this tests selection and visible-label preservation, not catalogue recognition.
Scene request: Three physical wine bottles in a dim wine bar phone photo with realistic sensor noise. A nearer off-center dark-glass bottle is deliberately presented in a convincing body grip; its complete front label is visible in low light. Two rear bottles near center have brighter labels. Do not make the image unusably dark.
```

</details>

Source review notes (quoted reference data):

> Фон содержит дополнительные бутылки. Основная этикетка довольно читаема: слабый стресс-тест низкой освещённости.
