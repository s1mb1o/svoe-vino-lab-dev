# main-selector-imagegen-pilot-v1-20261019:LA05

**Scene confirmed; masks pending. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/pilot-v1--LA05.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Крупный план этикетки без горлышка

Reference target description (source): Полный контекст крупного плана этикетки

Expected intent: `label_context`. Accepted target proposals: `d0, full_context`.

Scene group: `main-selector-imagegen-pilot-v1-20261019:LA05`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/pilot-v1--LA05.png)

![Proposed target overlay](../target-overlays/pilot-v1--LA05.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/pilot-v1--LA05-d0.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 1076×1020 px. Target agreement: True. Target retention proxy: 99.8%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.9%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/pilot-v1--LA05-scene-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--LA05-scene-v1.png) · [Exact decision JSON](../results/pilot-v1--LA05-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d1: 99.9%, 1005992 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d0; reason: only_credible_subject; mode: confident; crop 1536×1024 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d1 100.0%.

![semantic-v2 crop](../crops/pilot-v1--LA05-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--LA05-semantic-v2.png) · [Exact decision JSON](../results/pilot-v1--LA05-semantic-v2.json)

Returned label views: [label 1](../label-crops/pilot-v1--LA05-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d1: 100.0%, 1005992 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 891×896 px. Target agreement: n/a (no native target ID). Target retention proxy: 19.9%; maximum other-bottle retention: 0.0%; minimum associated label retention: 21.4%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/pilot-v1--LA05-dis-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--LA05-dis-v1.png) · [Exact decision JSON](../results/pilot-v1--LA05-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d1: 21.4%, 1005992 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/pilot-v1--LA05-d0.png) |
| d1 | wine label | [PNG](../masks/pilot-v1--LA05-d1.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/pilot-v1--LA05.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d2 | bottle held in hand | [PNG](../context-masks/pilot-v1--LA05-d2.png) |

[Raw frozen detector response](../detections/pilot-v1--LA05.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural.
Asset type: one independent synthetic smartphone photograph for a wine-subject selection test dataset.
Style: a believable candid phone photo with realistic optics, materials, shadows, depth and anatomically plausible hands when requested. Natural photographic imperfections, not a diagram, collage, 3D render, advertisement or contact sheet.
Bottle labels may use fictional wine names and normal small wine-label text. Labels must have complete physical paper boundaries and plausible printing. Do not add target markers, bounding boxes, arrows, captions, segmentation colors, watermarks or any explanation outside the scene.
Generate exactly one landscape photograph, approximately 1536 by 1024 pixels. Any wine identity is fictional; this tests selection and visible-label preservation, not catalogue recognition.
Scene request: A very close smartphone photo of the front label on a physical wine bottle. The label and curved glass fill nearly the entire image; no neck, cap or full bottle outline is visible. Complete cream label boundaries are visible except a tiny clipped margin at the bottom image edge. It contains a large blue illustrated bird and small winery and vintage text around it.
```

</details>

Source review notes (quoted reference data):

> Нижняя граница этикетки обрезана кадром; сохранять можно только видимые пиксели.
