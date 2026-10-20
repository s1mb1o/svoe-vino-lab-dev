# main-selector-imagegen-pilot-v1-20261019:HA01

**Scene confirmed; masks pending. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Хват корпуса вне центра

Reference target description (source): Удерживаемая бутылка слева

Expected intent: `clear`. Accepted target proposals: `d0`.

Scene group: `main-selector-imagegen-pilot-v1-20261019:HA01`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/pilot-v1--HA01.png)

![Proposed target overlay](../target-overlays/pilot-v1--HA01.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/pilot-v1--HA01-d0.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 276×907 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/pilot-v1--HA01-scene-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--HA01-scene-v1.png) · [Exact decision JSON](../results/pilot-v1--HA01-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 65224 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d0; reason: unique_visible_hand_contact; mode: confident; crop 298×942 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d2 100.0%.

![semantic-v2 crop](../crops/pilot-v1--HA01-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--HA01-semantic-v2.png) · [Exact decision JSON](../results/pilot-v1--HA01-semantic-v2.json)

Returned label views: [label 1](../label-crops/pilot-v1--HA01-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 65224 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 657×941 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.8%; maximum other-bottle retention: 99.9%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/pilot-v1--HA01-dis-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--HA01-dis-v1.png) · [Exact decision JSON](../results/pilot-v1--HA01-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 65224 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/pilot-v1--HA01-d0.png) |
| d1 | wine bottle | [PNG](../masks/pilot-v1--HA01-d1.png) |
| d2 | wine label | [PNG](../masks/pilot-v1--HA01-d2.png) |
| d3 | wine label | [PNG](../masks/pilot-v1--HA01-d3.png) |
| d4 | hand | [PNG](../masks/pilot-v1--HA01-d4.png) |

[Raw frozen detector response](../detections/pilot-v1--HA01.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural.
Asset type: one independent synthetic smartphone photograph for a wine-subject selection test dataset.
Style: a believable candid phone photo with realistic optics, materials, shadows, depth and anatomically plausible hands when requested. Natural photographic imperfections, not a diagram, collage, 3D render, advertisement or contact sheet.
Bottle labels may use fictional wine names and normal small wine-label text. Labels must have complete physical paper boundaries and plausible printing. Do not add target markers, bounding boxes, arrows, captions, segmentation colors, watermarks or any explanation outside the scene.
Generate exactly one landscape photograph, approximately 1536 by 1024 pixels. Any wine identity is fictional; this tests selection and visible-label preservation, not catalogue recognition.
Scene request: Two physical wine bottles on a counter. A hand genuinely wraps around the middle of the left off-center bottle, with fingers visibly in front and the thumb on the opposite side; the lower front label remains readable. A second unheld bottle occupies the photo center. Show convincing anatomical grip and contact.
```

</details>

Source review notes (quoted reference data):

> Явного несоответствия при первичном просмотре не отмечено; требуется ваше review.
