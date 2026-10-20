# main-selector-imagegen-pilot-v1-20261019:OW04

**Scene confirmed; masks pending. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/pilot-v1--OW04.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Бутылка и отражение

Reference target description (source): Настоящая бутылка слева от отражения

Expected intent: `clear`. Accepted target proposals: `d1`.

Scene group: `main-selector-imagegen-pilot-v1-20261019:OW04`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/pilot-v1--OW04.png)

![Proposed target overlay](../target-overlays/pilot-v1--OW04.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/pilot-v1--OW04-d1.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d1; reason: existing_scene_v1_rank; mode: legacy; crop 257×929 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/pilot-v1--OW04-scene-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--OW04-scene-v1.png) · [Exact decision JSON](../results/pilot-v1--OW04-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 58675 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d1; reason: only_credible_subject; mode: confident; crop 278×985 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%.

![semantic-v2 crop](../crops/pilot-v1--OW04-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--OW04-semantic-v2.png) · [Exact decision JSON](../results/pilot-v1--OW04-semantic-v2.json)

Returned label views: [label 1](../label-crops/pilot-v1--OW04-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 58675 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 637×987 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.9%; maximum other-bottle retention: 99.7%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/pilot-v1--OW04-dis-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--OW04-dis-v1.png) · [Exact decision JSON](../results/pilot-v1--OW04-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 58675 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/pilot-v1--OW04-d0.png) |
| d1 | wine bottle | [PNG](../masks/pilot-v1--OW04-d1.png) |
| d2 | wine label | [PNG](../masks/pilot-v1--OW04-d2.png) |
| d3 | wine label | [PNG](../masks/pilot-v1--OW04-d3.png) |
| d4 | wine glass | [PNG](../masks/pilot-v1--OW04-d4.png) |
| d5 | wine glass | [PNG](../masks/pilot-v1--OW04-d5.png) |
| d6 | wine glass | [PNG](../masks/pilot-v1--OW04-d6.png) |
| d7 | wine glass | [PNG](../masks/pilot-v1--OW04-d7.png) |
| d8 | wine glass | [PNG](../masks/pilot-v1--OW04-d8.png) |
| d9 | wine glass | [PNG](../masks/pilot-v1--OW04-d9.png) |
| d10 | wine glass | [PNG](../masks/pilot-v1--OW04-d10.png) |
| d11 | wine glass | [PNG](../masks/pilot-v1--OW04-d11.png) |
| d12 | wine glass | [PNG](../masks/pilot-v1--OW04-d12.png) |
| d13 | wine glass | [PNG](../masks/pilot-v1--OW04-d13.png) |
| d14 | wine glass | [PNG](../masks/pilot-v1--OW04-d14.png) |
| d15 | wine glass | [PNG](../masks/pilot-v1--OW04-d15.png) |
| d16 | wine glass | [PNG](../masks/pilot-v1--OW04-d16.png) |
| d17 | wine glass | [PNG](../masks/pilot-v1--OW04-d17.png) |
| d18 | wine glass | [PNG](../masks/pilot-v1--OW04-d18.png) |
| d19 | wine glass | [PNG](../masks/pilot-v1--OW04-d19.png) |
| d20 | wine glass | [PNG](../masks/pilot-v1--OW04-d20.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/pilot-v1--OW04.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d21 | mirror | [PNG](../context-masks/pilot-v1--OW04-d21.png) |
| d22 | mirror | [PNG](../context-masks/pilot-v1--OW04-d22.png) |
| d23 | mirror | [PNG](../context-masks/pilot-v1--OW04-d23.png) |
| d24 | bottle held in hand | [PNG](../context-masks/pilot-v1--OW04-d24.png) |
| d25 | bottle held in hand | [PNG](../context-masks/pilot-v1--OW04-d25.png) |

[Raw frozen detector response](../detections/pilot-v1--OW04.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural.
Asset type: one independent synthetic smartphone photograph for a wine-subject selection test dataset.
Style: a believable candid phone photo with realistic optics, materials, shadows, depth and anatomically plausible hands when requested. Natural photographic imperfections, not a diagram, collage, 3D render, advertisement or contact sheet.
Bottle labels may use fictional wine names and normal small wine-label text. Labels must have complete physical paper boundaries and plausible printing. Do not add target markers, bounding boxes, arrows, captions, segmentation colors, watermarks or any explanation outside the scene.
Generate exactly one landscape photograph, approximately 1536 by 1024 pixels. Any wine identity is fictional; this tests selection and visible-label preservation, not catalogue recognition.
Scene request: One physical wine bottle stands near a vertical mirror in a restaurant. Its mirror reflection appears next to it at a similar apparent scale. Make the mirror boundary, reflected room and contact with the counter physically plausible, but do not privilege either image with sharpness or lighting. No hand and no other bottle.
```

</details>

Source review notes (quoted reference data):

> Рамка зеркала и отражённый текст дают признаки физического владельца. Предлагаю пересмотреть исходное ambiguous до запуска селекторов.
