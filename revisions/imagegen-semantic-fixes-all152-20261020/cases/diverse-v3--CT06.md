# main-selector-imagegen-diverse-v3-20261020:CT06

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--CT06.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): На яхте без бутылок · бокалы и мельница без бутылок

Reference target description (source): Нет целевой бутылки — полный кадр

Expected intent: `no_target`. Accepted target proposals: `full_frame`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:CT06`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--CT06.png)

![Proposed target overlay](../target-overlays/diverse-v3--CT06.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: None; reason: existing_original_frame_fallback; mode: legacy; crop 1536×1024 px. Target agreement: True. Target retention proxy: n/a; maximum other-bottle retention: n/a; minimum associated label retention: n/a. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--CT06-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--CT06-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--CT06-scene-v1.json)

### semantic-v2: No automatic failure flag; usability pending

Selected: None; reason: fallback_original_frame; mode: fallback; crop 1536×1024 px. Target agreement: True. Target retention proxy: n/a; maximum other-bottle retention: n/a; minimum associated label retention: n/a. Mask ownership, label completeness and legibility still require human review.

![semantic-v2 crop](../crops/diverse-v3--CT06-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--CT06-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--CT06-semantic-v2.json)

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1392×701 px. Target agreement: n/a (no native target ID). Target retention proxy: n/a; maximum other-bottle retention: n/a; minimum associated label retention: n/a. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--CT06-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--CT06-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--CT06-dis-v1.json)

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine glass | [PNG](../masks/diverse-v3--CT06-d0.png) |
| d1 | wine glass | [PNG](../masks/diverse-v3--CT06-d1.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--CT06.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|

[Raw frozen detector response](../detections/diverse-v3--CT06.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, landscape 3:2, approximately 1536 by 1024 pixels. An empty yacht cockpit table with drinking accessories only, sea and sail hardware behind. Absolutely no wine bottles or bottle images anywhere in frame, including the background. A tasting table with two empty wine glasses, a wooden pepper mill, folded napkins and a water carafe of clearly non-bottle shape. NO wine bottles, no bottle pictures or packaging, no hands. Natural tasting-area phone photograph, no obvious wine-bottle-shaped object. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: На яхте без бутылок. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
