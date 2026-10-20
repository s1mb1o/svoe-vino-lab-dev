# main-selector-imagegen-diverse-v3-20261020:PN10

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--PN10.jpg)

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): Указание в ракурсе сверху

Reference target description (source): Левая бутылка с круглой красной эмблемой

Expected intent: `clear`. Accepted target proposals: `d33`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:PN10`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--PN10.png)

![Proposed target overlay](../target-overlays/diverse-v3--PN10.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--PN10-d33.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d3; reason: existing_scene_v1_rank; mode: legacy; crop 211×721 px. Target agreement: False. Target retention proxy: 0.0%; maximum other-bottle retention: 100.0%; minimum associated label retention: 0.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--PN10-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PN10-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--PN10-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d43: 0.0%, 35269 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d33; reason: explicit_pointing_gesture; mode: confident; crop 187×669 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d43 100.0%.

![semantic-v2 crop](../crops/diverse-v3--PN10-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PN10-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--PN10-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--PN10-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d43: 100.0%, 35269 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1171×1239 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.8%; maximum other-bottle retention: 98.4%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--PN10-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--PN10-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--PN10-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d43: 100.0%, 35269 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--PN10-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--PN10-d1.png) |
| d2 | wine bottle | [PNG](../masks/diverse-v3--PN10-d2.png) |
| d3 | wine bottle | [PNG](../masks/diverse-v3--PN10-d3.png) |
| d4 | wine bottle | [PNG](../masks/diverse-v3--PN10-d4.png) |
| d5 | wine bottle | [PNG](../masks/diverse-v3--PN10-d5.png) |
| d6 | wine bottle | [PNG](../masks/diverse-v3--PN10-d6.png) |
| d7 | wine bottle | [PNG](../masks/diverse-v3--PN10-d7.png) |
| d8 | wine bottle | [PNG](../masks/diverse-v3--PN10-d8.png) |
| d9 | wine bottle | [PNG](../masks/diverse-v3--PN10-d9.png) |
| d10 | wine bottle | [PNG](../masks/diverse-v3--PN10-d10.png) |
| d11 | wine bottle | [PNG](../masks/diverse-v3--PN10-d11.png) |
| d12 | wine bottle | [PNG](../masks/diverse-v3--PN10-d12.png) |
| d13 | wine bottle | [PNG](../masks/diverse-v3--PN10-d13.png) |
| d14 | wine bottle | [PNG](../masks/diverse-v3--PN10-d14.png) |
| d15 | wine bottle | [PNG](../masks/diverse-v3--PN10-d15.png) |
| d16 | wine bottle | [PNG](../masks/diverse-v3--PN10-d16.png) |
| d17 | wine bottle | [PNG](../masks/diverse-v3--PN10-d17.png) |
| d18 | wine bottle | [PNG](../masks/diverse-v3--PN10-d18.png) |
| d19 | wine bottle | [PNG](../masks/diverse-v3--PN10-d19.png) |
| d20 | wine bottle | [PNG](../masks/diverse-v3--PN10-d20.png) |
| d21 | wine bottle | [PNG](../masks/diverse-v3--PN10-d21.png) |
| d22 | wine bottle | [PNG](../masks/diverse-v3--PN10-d22.png) |
| d23 | wine bottle | [PNG](../masks/diverse-v3--PN10-d23.png) |
| d24 | wine bottle | [PNG](../masks/diverse-v3--PN10-d24.png) |
| d25 | wine bottle | [PNG](../masks/diverse-v3--PN10-d25.png) |
| d26 | wine bottle | [PNG](../masks/diverse-v3--PN10-d26.png) |
| d27 | wine bottle | [PNG](../masks/diverse-v3--PN10-d27.png) |
| d28 | wine bottle | [PNG](../masks/diverse-v3--PN10-d28.png) |
| d29 | wine bottle | [PNG](../masks/diverse-v3--PN10-d29.png) |
| d30 | wine bottle | [PNG](../masks/diverse-v3--PN10-d30.png) |
| d31 | wine bottle | [PNG](../masks/diverse-v3--PN10-d31.png) |
| d32 | wine bottle | [PNG](../masks/diverse-v3--PN10-d32.png) |
| d33 | wine bottle | [PNG](../masks/diverse-v3--PN10-d33.png) |
| d34 | wine bottle | [PNG](../masks/diverse-v3--PN10-d34.png) |
| d35 | wine bottle | [PNG](../masks/diverse-v3--PN10-d35.png) |
| d36 | wine bottle | [PNG](../masks/diverse-v3--PN10-d36.png) |
| d37 | wine bottle | [PNG](../masks/diverse-v3--PN10-d37.png) |
| d38 | wine bottle | [PNG](../masks/diverse-v3--PN10-d38.png) |
| d39 | wine bottle | [PNG](../masks/diverse-v3--PN10-d39.png) |
| d40 | wine label | [PNG](../masks/diverse-v3--PN10-d40.png) |
| d41 | wine label | [PNG](../masks/diverse-v3--PN10-d41.png) |
| d42 | wine label | [PNG](../masks/diverse-v3--PN10-d42.png) |
| d43 | wine label | [PNG](../masks/diverse-v3--PN10-d43.png) |
| d44 | wine label | [PNG](../masks/diverse-v3--PN10-d44.png) |
| d45 | wine label | [PNG](../masks/diverse-v3--PN10-d45.png) |
| d46 | wine label | [PNG](../masks/diverse-v3--PN10-d46.png) |
| d47 | wine label | [PNG](../masks/diverse-v3--PN10-d47.png) |
| d48 | wine label | [PNG](../masks/diverse-v3--PN10-d48.png) |
| d49 | wine label | [PNG](../masks/diverse-v3--PN10-d49.png) |
| d50 | wine label | [PNG](../masks/diverse-v3--PN10-d50.png) |
| d51 | wine label | [PNG](../masks/diverse-v3--PN10-d51.png) |
| d52 | wine label | [PNG](../masks/diverse-v3--PN10-d52.png) |
| d53 | wine label | [PNG](../masks/diverse-v3--PN10-d53.png) |
| d54 | wine label | [PNG](../masks/diverse-v3--PN10-d54.png) |
| d55 | wine label | [PNG](../masks/diverse-v3--PN10-d55.png) |
| d56 | wine label | [PNG](../masks/diverse-v3--PN10-d56.png) |
| d57 | wine label | [PNG](../masks/diverse-v3--PN10-d57.png) |
| d58 | wine label | [PNG](../masks/diverse-v3--PN10-d58.png) |
| d59 | wine label | [PNG](../masks/diverse-v3--PN10-d59.png) |
| d60 | wine label | [PNG](../masks/diverse-v3--PN10-d60.png) |
| d61 | hand | [PNG](../masks/diverse-v3--PN10-d61.png) |
| d62 | box | [PNG](../masks/diverse-v3--PN10-d62.png) |
| d63 | box | [PNG](../masks/diverse-v3--PN10-d63.png) |
| d64 | box | [PNG](../masks/diverse-v3--PN10-d64.png) |
| d65 | box | [PNG](../masks/diverse-v3--PN10-d65.png) |
| d66 | box | [PNG](../masks/diverse-v3--PN10-d66.png) |
| d67 | box | [PNG](../masks/diverse-v3--PN10-d67.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--PN10.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d68 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d68.png) |
| d69 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d69.png) |
| d70 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d70.png) |
| d71 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d71.png) |
| d72 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d72.png) |
| d73 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d73.png) |
| d74 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d74.png) |
| d75 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d75.png) |
| d76 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d76.png) |
| d77 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d77.png) |
| d78 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d78.png) |
| d79 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d79.png) |
| d80 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d80.png) |
| d81 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d81.png) |
| d82 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d82.png) |
| d83 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d83.png) |
| d84 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d84.png) |
| d85 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d85.png) |
| d86 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d86.png) |
| d87 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d87.png) |
| d88 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d88.png) |
| d89 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d89.png) |
| d90 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d90.png) |
| d91 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d91.png) |
| d92 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d92.png) |
| d93 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d93.png) |
| d94 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d94.png) |
| d95 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d95.png) |
| d96 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d96.png) |
| d97 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d97.png) |
| d98 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d98.png) |
| d99 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d99.png) |
| d100 | bottle held in hand | [PNG](../context-masks/diverse-v3--PN10-d100.png) |

[Raw frozen detector response](../detections/diverse-v3--PN10.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate exactly ONE independent candid smartphone photograph. Show believable glass, paper, natural material imperfections, fictional wine branding, and anatomically plausible hands. No collage, grid, arrows, annotations, bounding boxes, highlights, watermark, UI overlay, or explanatory caption. Text is allowed on physical objects within the scene. Keep the target visible front label entirely inside the frame unless partial occlusion or close-up is explicitly requested. Image format: square, approximately 1024 by 1024 pixels. Setting: inside a real wine cellar. Use stone or brick walls, wooden wine racks, storage cubbies, a cellar tasting table and practical dim lights. Keep the described foreground inventory; background racks may be empty or softly blurred. Scene details: Top-down oblique phone photo of three separated bottles standing on a round table. A hand from bottom left points diagonally toward the LEFT bottle with a circular red emblem, with a short visible fingertip-to-bottle gap. The other bottles are center-right. No grip.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Винный погреб. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
