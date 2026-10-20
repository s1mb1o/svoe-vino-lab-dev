# main-selector-imagegen-pilot-v1-20261019:AM03

**Scene confirmed; masks pending. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/pilot-v1--AM03.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Ряд из шести бутылок

Reference target description (source): Третья бутылка слева — fallback

Expected intent: `ambiguous`. Accepted target proposals: `d0`.

Scene group: `main-selector-imagegen-pilot-v1-20261019:AM03`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/pilot-v1--AM03.png)

![Proposed target overlay](../target-overlays/pilot-v1--AM03.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/pilot-v1--AM03-d0.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 211×810 px. Target agreement: True. Target retention proxy: 99.9%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/pilot-v1--AM03-scene-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--AM03-scene-v1.png) · [Exact decision JSON](../results/pilot-v1--AM03-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d7: 100.0%, 64291 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d0; reason: fallback_nearest_center; mode: fallback; crop 232×873 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d7 100.0%.

![semantic-v2 crop](../crops/pilot-v1--AM03-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--AM03-semantic-v2.png) · [Exact decision JSON](../results/pilot-v1--AM03-semantic-v2.json)

Returned label views: [label 1](../label-crops/pilot-v1--AM03-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d7: 100.0%, 64291 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1536×899 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 100.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/pilot-v1--AM03-dis-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--AM03-dis-v1.png) · [Exact decision JSON](../results/pilot-v1--AM03-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d7: 100.0%, 64291 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/pilot-v1--AM03-d0.png) |
| d1 | wine bottle | [PNG](../masks/pilot-v1--AM03-d1.png) |
| d2 | wine bottle | [PNG](../masks/pilot-v1--AM03-d2.png) |
| d3 | wine bottle | [PNG](../masks/pilot-v1--AM03-d3.png) |
| d4 | wine bottle | [PNG](../masks/pilot-v1--AM03-d4.png) |
| d5 | wine bottle | [PNG](../masks/pilot-v1--AM03-d5.png) |
| d6 | wine label | [PNG](../masks/pilot-v1--AM03-d6.png) |
| d7 | wine label | [PNG](../masks/pilot-v1--AM03-d7.png) |
| d8 | wine label | [PNG](../masks/pilot-v1--AM03-d8.png) |
| d9 | wine label | [PNG](../masks/pilot-v1--AM03-d9.png) |
| d10 | wine label | [PNG](../masks/pilot-v1--AM03-d10.png) |
| d11 | wine label | [PNG](../masks/pilot-v1--AM03-d11.png) |
| d12 | wine glass | [PNG](../masks/pilot-v1--AM03-d12.png) |
| d13 | wine glass | [PNG](../masks/pilot-v1--AM03-d13.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/pilot-v1--AM03.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d14 | bottle held in hand | [PNG](../context-masks/pilot-v1--AM03-d14.png) |
| d15 | bottle held in hand | [PNG](../context-masks/pilot-v1--AM03-d15.png) |
| d16 | bottle held in hand | [PNG](../context-masks/pilot-v1--AM03-d16.png) |
| d17 | bottle held in hand | [PNG](../context-masks/pilot-v1--AM03-d17.png) |
| d18 | bottle held in hand | [PNG](../context-masks/pilot-v1--AM03-d18.png) |
| d19 | bottle held in hand | [PNG](../context-masks/pilot-v1--AM03-d19.png) |

[Raw frozen detector response](../detections/pilot-v1--AM03.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural.
Asset type: one independent synthetic smartphone photograph for a wine-subject selection test dataset.
Style: a believable candid phone photo with realistic optics, materials, shadows, depth and anatomically plausible hands when requested. Natural photographic imperfections, not a diagram, collage, 3D render, advertisement or contact sheet.
Bottle labels may use fictional wine names and normal small wine-label text. Labels must have complete physical paper boundaries and plausible printing. Do not add target markers, bounding boxes, arrows, captions, segmentation colors, watermarks or any explanation outside the scene.
Generate exactly one landscape photograph, approximately 1536 by 1024 pixels. Any wine identity is fictional; this tests selection and visible-label preservation, not catalogue recognition.
Scene request: Exactly six physical wine bottles along one shelf at equal depth and similar apparent size, with no held or presented subject. A casually framed phone photo crops a little shelf edge; similar focus and lighting for all six. No poster, mirror or extra physical bottles.
```

</details>

Source review notes (quoted reference data):

> Явного несоответствия при первичном просмотре не отмечено; требуется ваше review.
