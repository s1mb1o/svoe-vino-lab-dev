# main-selector-imagegen-diverse-v3-20261020:WP01

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--WP01.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Прозрачный пакет и хват справа

Reference target description (source): Удерживаемая бутылка справа в прозрачном пакете

Expected intent: `clear`. Accepted target proposals: `d0`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:WP01`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--WP01.png)

![Proposed target overlay](../target-overlays/diverse-v3--WP01.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--WP01-d0.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 277×903 px. Target agreement: True. Target retention proxy: 99.9%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--WP01-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--WP01-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--WP01-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 72191 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d0; reason: unique_visible_hand_contact; mode: confident; crop 308×976 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d2 100.0%.

![semantic-v2 crop](../crops/diverse-v3--WP01-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--WP01-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--WP01-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--WP01-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 72191 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1133×1012 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 100.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--WP01-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--WP01-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--WP01-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 72191 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--WP01-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--WP01-d1.png) |
| d2 | wine label | [PNG](../masks/diverse-v3--WP01-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--WP01-d3.png) |
| d4 | wine label | [PNG](../masks/diverse-v3--WP01-d4.png) |
| d5 | hand | [PNG](../masks/diverse-v3--WP01-d5.png) |
| d6 | hand | [PNG](../masks/diverse-v3--WP01-d6.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--WP01.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d7 | bottle held in hand | [PNG](../context-masks/diverse-v3--WP01-d7.png) |
| d8 | bottle held in hand | [PNG](../context-masks/diverse-v3--WP01-d8.png) |
| d9 | transparent wrapping | [PNG](../context-masks/diverse-v3--WP01-d9.png) |

[Raw frozen detector response](../detections/diverse-v3--WP01.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate exactly ONE independent candid smartphone photograph. Show believable glass, paper, natural material imperfections, fictional wine branding, and anatomically plausible hands. No collage, grid, arrows, annotations, bounding boxes, highlights, watermark, UI overlay, or explanatory caption. Text is allowed on physical objects within the scene. Keep the target visible front label entirely inside the frame unless partial occlusion or close-up is explicitly requested. Image format: landscape 3:2, approximately 1536 by 1024 pixels. Setting: inside a real wine store. Use a shop tasting counter, bottle shelves with small price strips, retail aisle details and natural store lighting. Background wine bottles may be present on shelves but should remain clearly in the background. Viewpoint: the customer is examining a wine bottle in their own hand while shopping or browsing the cellar, with the bottle front label turned toward the phone camera. Show the bottle, the holding hand and enough surrounding shelves or cellar details to establish the location. Scene details: Two bottles. A hand from right firmly grips the RIGHT pink-label bottle mid-body THROUGH clear crinkled cellophane, thumb and fingers compressing film around glass. A left unwrapped blue-label bottle is unheld. Plain background without shelves. Wrapper fully transparent, no graphics.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Винный магазин. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
> Вместо заявленного магазина получился светлый почти студийный фон; магазин по фото не подтверждается.
