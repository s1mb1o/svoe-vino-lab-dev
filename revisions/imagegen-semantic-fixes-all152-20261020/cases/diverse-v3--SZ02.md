# main-selector-imagegen-diverse-v3-20261020:SZ02

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--SZ02.jpg)

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): В фойе кинотеатра · бутылка слева и огромная картинка

Reference target description (source): Маленькая настоящая бутылка в руке слева от большого постера

Expected intent: `clear`. Accepted target proposals: `d1`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:SZ02`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--SZ02.png)

![Proposed target overlay](../target-overlays/diverse-v3--SZ02.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--SZ02-d1.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 212×805 px. Target agreement: False. Target retention proxy: 0.0%; maximum other-bottle retention: 99.9%; minimum associated label retention: 0.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--SZ02-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--SZ02-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--SZ02-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 0.0%, 5888 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d1; reason: unique_visible_hand_contact; mode: confident; crop 201×265 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%.

![semantic-v2 crop](../crops/diverse-v3--SZ02-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--SZ02-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--SZ02-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--SZ02-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d3: 100.0%, 5888 source pixels

### dis-v1: Proxy satisfied; usability pending

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 873×951 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.5%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--SZ02-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--SZ02-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--SZ02-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d3: 99.5%, 5888 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--SZ02-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--SZ02-d1.png) |
| d2 | wine label | [PNG](../masks/diverse-v3--SZ02-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--SZ02-d3.png) |
| d4 | hand | [PNG](../masks/diverse-v3--SZ02-d4.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--SZ02.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d5 | poster | [PNG](../context-masks/diverse-v3--SZ02-d5.png) |
| d6 | bottle held in hand | [PNG](../context-masks/diverse-v3--SZ02-d6.png) |
| d7 | bottle held in hand | [PNG](../context-masks/diverse-v3--SZ02-d7.png) |

[Raw frozen detector response](../detections/diverse-v3--SZ02.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, landscape 3:2, approximately 1536 by 1024 pixels. An adult cinema visitor examines a small wine bottle in the foyer of an old cinema. A large framed wine advertisement hangs nearby. Show face and held real bottle, distinct from the poster. One real small cream-label bottle is held mid-body by a hand at LEFT foreground. A huge framed poster at RIGHT shows a much larger printed wine bottle. Show poster border and physical glass base of the held bottle. No other real bottles. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: В фойе кинотеатра. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
> Цель исправлена по фактическому фото: большая бутылка справа изображена на постере, настоящую маленькую бутылку держит женщина.
