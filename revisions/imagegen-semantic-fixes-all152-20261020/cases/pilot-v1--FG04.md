# main-selector-imagegen-pilot-v1-20261019:FG04

**Scene confirmed; masks pending. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/pilot-v1--FG04.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Разные уровни полок

Reference target description (source): Верхняя бутылка слева — fallback

Expected intent: `ambiguous`. Accepted target proposals: `d2`.

Scene group: `main-selector-imagegen-pilot-v1-20261019:FG04`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/pilot-v1--FG04.png)

![Proposed target overlay](../target-overlays/pilot-v1--FG04.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/pilot-v1--FG04-d2.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d2; reason: existing_scene_v1_rank; mode: legacy; crop 183×640 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/pilot-v1--FG04-scene-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--FG04-scene-v1.png) · [Exact decision JSON](../results/pilot-v1--FG04-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d5: 100.0%, 44784 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d2; reason: fallback_center_contains; mode: fallback; crop 199×666 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d5 100.0%.

![semantic-v2 crop](../crops/pilot-v1--FG04-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--FG04-semantic-v2.png) · [Exact decision JSON](../results/pilot-v1--FG04-semantic-v2.json)

Returned label views: [label 1](../label-crops/pilot-v1--FG04-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d5: 100.0%, 44784 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1057×1017 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.9%; maximum other-bottle retention: 99.9%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/pilot-v1--FG04-dis-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--FG04-dis-v1.png) · [Exact decision JSON](../results/pilot-v1--FG04-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d5: 100.0%, 44784 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/pilot-v1--FG04-d0.png) |
| d1 | wine bottle | [PNG](../masks/pilot-v1--FG04-d1.png) |
| d2 | wine bottle | [PNG](../masks/pilot-v1--FG04-d2.png) |
| d3 | wine label | [PNG](../masks/pilot-v1--FG04-d3.png) |
| d4 | wine label | [PNG](../masks/pilot-v1--FG04-d4.png) |
| d5 | wine label | [PNG](../masks/pilot-v1--FG04-d5.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/pilot-v1--FG04.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d6 | bottle held in hand | [PNG](../context-masks/pilot-v1--FG04-d6.png) |
| d7 | bottle held in hand | [PNG](../context-masks/pilot-v1--FG04-d7.png) |
| d8 | bottle held in hand | [PNG](../context-masks/pilot-v1--FG04-d8.png) |

[Raw frozen detector response](../detections/pilot-v1--FG04.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural.
Asset type: one independent synthetic smartphone photograph for a wine-subject selection test dataset.
Style: a believable candid phone photo with realistic optics, materials, shadows, depth and anatomically plausible hands when requested. Natural photographic imperfections, not a diagram, collage, 3D render, advertisement or contact sheet.
Bottle labels may use fictional wine names and normal small wine-label text. Labels must have complete physical paper boundaries and plausible printing. Do not add target markers, bounding boxes, arrows, captions, segmentation colors, watermarks or any explanation outside the scene.
Generate exactly one landscape photograph, approximately 1536 by 1024 pixels. Any wine identity is fictional; this tests selection and visible-label preservation, not catalogue recognition.
Scene request: Exactly three physical wine bottles on two clearly separate wooden shelf levels. A large horizontal wine bottle lies on the lower shelf in the lower-left foreground; two upright wine bottles stand on a higher shelf near the image center. Make the separate support planes unmistakable. All three are similarly sharp with no hands and no singled-out bottle.
```

</details>

Source review notes (quoted reference data):

> Разные опорные плоскости хорошо видны. Это не точный контроль измеренной глубины.
