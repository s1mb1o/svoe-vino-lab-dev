# main-selector-imagegen-hardcases-v2-20261020:PT02

**Scene confirmed; masks pending. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/hardcases-v2--PT02.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Указание сверху на левую бутылку

Reference target description (source): Левая бутылка с голубой этикеткой

Expected intent: `clear`. Accepted target proposals: `d1`.

Scene group: `main-selector-imagegen-hardcases-v2-20261020:PT02`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/hardcases-v2--PT02.png)

![Proposed target overlay](../target-overlays/hardcases-v2--PT02.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/hardcases-v2--PT02-d1.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d1; reason: existing_scene_v1_rank; mode: legacy; crop 213×781 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/hardcases-v2--PT02-scene-v1.png)

[Full-resolution keep mask](../keep-masks/hardcases-v2--PT02-scene-v1.png) · [Exact decision JSON](../results/hardcases-v2--PT02-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 51527 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d1; reason: explicit_pointing_gesture; mode: confident; crop 239×841 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%.

![semantic-v2 crop](../crops/hardcases-v2--PT02-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/hardcases-v2--PT02-semantic-v2.png) · [Exact decision JSON](../results/hardcases-v2--PT02-semantic-v2.json)

Returned label views: [label 1](../label-crops/hardcases-v2--PT02-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 51527 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1046×857 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.9%; maximum other-bottle retention: 99.9%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/hardcases-v2--PT02-dis-v1.png)

[Full-resolution keep mask](../keep-masks/hardcases-v2--PT02-dis-v1.png) · [Exact decision JSON](../results/hardcases-v2--PT02-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 51527 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/hardcases-v2--PT02-d0.png) |
| d1 | wine bottle | [PNG](../masks/hardcases-v2--PT02-d1.png) |
| d2 | wine label | [PNG](../masks/hardcases-v2--PT02-d2.png) |
| d3 | wine label | [PNG](../masks/hardcases-v2--PT02-d3.png) |
| d4 | hand | [PNG](../masks/hardcases-v2--PT02-d4.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/hardcases-v2--PT02.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d5 | bottle held in hand | [PNG](../context-masks/hardcases-v2--PT02-d5.png) |
| d6 | bottle held in hand | [PNG](../context-masks/hardcases-v2--PT02-d6.png) |

[Raw frozen detector response](../detections/hardcases-v2--PT02.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Generate exactly one independent photorealistic smartphone photograph, landscape 3:2, approximately 1536 by 1024 pixels. This is an ordinary wine selection moment, with natural perspective, believable glass and paper, imperfect ambient lighting, and realistic human anatomy. No collage, inset, split screen, arrows, highlights, bounding boxes, annotations, watermarks, UI, or text outside physical objects. Use fictional wine branding. Keep the target bottle's entire front label within the frame. The scene must communicate the stated gesture or physical relation visually; do not add any explanatory caption. Exactly two physical upright wine bottles on a wooden tasting table. The LEFT bottle has a pale blue label; the RIGHT bottle has a large orange label and stands far to the right, separated by a gap as wide as a bottle. A single human hand enters from the TOP LEFT, hovering directly above the LEFT bottle. Its broad palm and curled fingers are visible above the left target, and its index points almost vertically DOWNWARD, stopping just short of the LEFT bottle blue label shoulder. The finger and palm stay entirely within the left third of the image, far from the right bottle. It does not grasp either bottle. The gesture unequivocally indicates the LEFT blue-label bottle. Warm indoor daylight, slightly elevated camera viewpoint, no background bottles.
```

</details>

Source review notes (quoted reference data):

> Первая попытка отклонена: палец указывал на соседа. Вторая попытка создана заново; палец теперь слева сверху.
