# main-selector-imagegen-pilot-v1-20261019:LA02

**Scene confirmed; masks pending. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/pilot-v1--LA02.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Бирка за пределами бутылки

Reference target description (source): Бутылка с выступающей биркой

Expected intent: `clear`. Accepted target proposals: `d0`.

Scene group: `main-selector-imagegen-pilot-v1-20261019:LA02`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/pilot-v1--LA02.png)

![Proposed target overlay](../target-overlays/pilot-v1--LA02.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/pilot-v1--LA02-d0.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 247×935 px. Target agreement: True. Target retention proxy: 99.9%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/pilot-v1--LA02-scene-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--LA02-scene-v1.png) · [Exact decision JSON](../results/pilot-v1--LA02-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 89606 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d0; reason: only_credible_subject; mode: confident; crop 277×989 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d2 100.0%.

![semantic-v2 crop](../crops/pilot-v1--LA02-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--LA02-semantic-v2.png) · [Exact decision JSON](../results/pilot-v1--LA02-semantic-v2.json)

Returned label views: [label 1](../label-crops/pilot-v1--LA02-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 89606 source pixels

### dis-v1: Proxy satisfied; usability pending

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 490×991 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/pilot-v1--LA02-dis-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--LA02-dis-v1.png) · [Exact decision JSON](../results/pilot-v1--LA02-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 89606 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/pilot-v1--LA02-d0.png) |
| d1 | wine label | [PNG](../masks/pilot-v1--LA02-d1.png) |
| d2 | wine label | [PNG](../masks/pilot-v1--LA02-d2.png) |
| d3 | price tag | [PNG](../masks/pilot-v1--LA02-d3.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/pilot-v1--LA02.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d4 | bottle held in hand | [PNG](../context-masks/pilot-v1--LA02-d4.png) |

[Raw frozen detector response](../detections/pilot-v1--LA02.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural.
Asset type: one independent synthetic smartphone photograph for a wine-subject selection test dataset.
Style: a believable candid phone photo with realistic optics, materials, shadows, depth and anatomically plausible hands when requested. Natural photographic imperfections, not a diagram, collage, 3D render, advertisement or contact sheet.
Bottle labels may use fictional wine names and normal small wine-label text. Labels must have complete physical paper boundaries and plausible printing. Do not add target markers, bounding boxes, arrows, captions, segmentation colors, watermarks or any explanation outside the scene.
Generate exactly one landscape photograph, approximately 1536 by 1024 pixels. Any wine identity is fictional; this tests selection and visible-label preservation, not catalogue recognition.
Scene request: One physical wine bottle on a wooden counter with a complete front paper label and a small hanging neck tag tied by string. The tag hangs well outside the right edge of the bottle silhouette, with its whole paper outline visible. Realistic shadows and string attachment. No other bottle.
```

</details>

Source review notes (quoted reference data):

> Явного несоответствия при первичном просмотре не отмечено; требуется ваше review.
