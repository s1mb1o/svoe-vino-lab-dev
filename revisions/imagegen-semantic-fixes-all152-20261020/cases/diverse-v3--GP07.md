# main-selector-imagegen-diverse-v3-20261020:GP07

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--GP07.jpg)

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): В ресторане у моря · широкая бутылка справа

Reference target description (source): Широкая удерживаемая бутылка справа

Expected intent: `clear`. Accepted target proposals: `d0`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:GP07`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--GP07.png)

![Proposed target overlay](../target-overlays/diverse-v3--GP07.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--GP07-d0.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 296×554 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--GP07-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--GP07-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--GP07-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 15992 source pixels; d4: 100.0%, 2666 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d0; reason: unique_visible_hand_contact; mode: confident; crop 318×597 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d2 100.0%; d4 100.0%.

![semantic-v2 crop](../crops/diverse-v3--GP07-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--GP07-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--GP07-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--GP07-semantic-v2-0.png) · [label 2](../label-crops/diverse-v3--GP07-semantic-v2-1.png)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 15992 source pixels; d4: 100.0%, 2666 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1306×1024 px. Target agreement: n/a (no native target ID). Target retention proxy: 99.9%; maximum other-bottle retention: 79.7%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--GP07-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--GP07-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--GP07-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 15992 source pixels; d4: 100.0%, 2666 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--GP07-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--GP07-d1.png) |
| d2 | wine label | [PNG](../masks/diverse-v3--GP07-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--GP07-d3.png) |
| d4 | wine label | [PNG](../masks/diverse-v3--GP07-d4.png) |
| d5 | hand | [PNG](../masks/diverse-v3--GP07-d5.png) |
| d6 | hand | [PNG](../masks/diverse-v3--GP07-d6.png) |
| d7 | wine glass | [PNG](../masks/diverse-v3--GP07-d7.png) |
| d8 | wine glass | [PNG](../masks/diverse-v3--GP07-d8.png) |
| d9 | wine glass | [PNG](../masks/diverse-v3--GP07-d9.png) |
| d10 | wine glass | [PNG](../masks/diverse-v3--GP07-d10.png) |
| d11 | wine glass | [PNG](../masks/diverse-v3--GP07-d11.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--GP07.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d12 | bottle held in hand | [PNG](../context-masks/diverse-v3--GP07-d12.png) |
| d13 | bottle held in hand | [PNG](../context-masks/diverse-v3--GP07-d13.png) |

[Raw frozen detector response](../detections/diverse-v3--GP07.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural. Generate ONE independent photograph, landscape 3:2, approximately 1536 by 1024 pixels. An adult seaside-restaurant waiter examines a sparkling-wine bottle beside an outdoor table. Show their upper body, linen shirt, parasols, beach and sea. Bright humid daylight and natural bottle reflections. A hand from right firmly wraps around the lower middle of a broad rounded sparkling-wine bottle on RIGHT with a gold front label. The thumb and curled fingers are visible on both side edges. An unheld thin bottle stands LEFT. Natural realistic skin and glass. Make the scene composition, person, clothing and location specific to this scenario, rather than repeating a generic bottle on a tasting counter. Show genuine physical contact when a grip is requested. Fictional wine branding; no arrows, bounding boxes, captions, collages, watermark or UI. Maintain anatomically plausible hands. Keep the target visible label inside the frame except the explicit close-up and occlusion cases.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: В ресторане у моря. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
