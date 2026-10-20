# main-selector-imagegen-diverse-v3-20261020:LT09

**Scene and masks pending — exploratory. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/diverse-v3--LT09.jpg)

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): Оригинальный пират при свечах · тёмная удерживаемая бутылка справа

Reference target description (source): Правая удерживаемая бутылка при свечах

Expected intent: `clear`. Accepted target proposals: `d0`.

Scene group: `main-selector-imagegen-diverse-v3-20261020:LT09`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/diverse-v3--LT09.png)

![Proposed target overlay](../target-overlays/diverse-v3--LT09.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/diverse-v3--LT09-d0.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 265×449 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.5%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/diverse-v3--LT09-scene-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LT09-scene-v1.png) · [Exact decision JSON](../results/diverse-v3--LT09-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 99.5%, 13983 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d0; reason: unique_visible_hand_contact; mode: confident; crop 287×484 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d2 100.0%.

![semantic-v2 crop](../crops/diverse-v3--LT09-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LT09-semantic-v2.png) · [Exact decision JSON](../results/diverse-v3--LT09-semantic-v2.json)

Returned label views: [label 1](../label-crops/diverse-v3--LT09-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 13983 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1037×857 px. Target agreement: n/a (no native target ID). Target retention proxy: 25.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 56.7%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/diverse-v3--LT09-dis-v1.png)

[Full-resolution keep mask](../keep-masks/diverse-v3--LT09-dis-v1.png) · [Exact decision JSON](../results/diverse-v3--LT09-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 56.7%, 13983 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/diverse-v3--LT09-d0.png) |
| d1 | wine bottle | [PNG](../masks/diverse-v3--LT09-d1.png) |
| d2 | wine label | [PNG](../masks/diverse-v3--LT09-d2.png) |
| d3 | wine label | [PNG](../masks/diverse-v3--LT09-d3.png) |
| d4 | hand | [PNG](../masks/diverse-v3--LT09-d4.png) |
| d5 | hand | [PNG](../masks/diverse-v3--LT09-d5.png) |
| d6 | box | [PNG](../masks/diverse-v3--LT09-d6.png) |
| d7 | box | [PNG](../masks/diverse-v3--LT09-d7.png) |
| d8 | box | [PNG](../masks/diverse-v3--LT09-d8.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/diverse-v3--LT09.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d9 | bottle held in hand | [PNG](../context-masks/diverse-v3--LT09-d9.png) |
| d10 | bottle held in hand | [PNG](../context-masks/diverse-v3--LT09-d10.png) |

[Raw frozen detector response](../detections/diverse-v3--LT09.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Generate ONE independent landscape 3:2 photograph, approximately 1536 by 1024 pixels. An original bald red-bearded adult pirate captain in a simple faded green linen shirt examines a dark wine bottle by candlelight inside a timber ship cabin. Show his face, maps, compass and porthole. Two physical wine bottles. His hand from right visibly grips the RIGHT nearly black bottle around its body, with thumb and opposing fingers contacting the glass and a dark paper label still visible. A candle beside the LEFT unattended bottle brightly illuminates its large ivory label. Preserve distinguishable target label outline and actual opposed finger contact despite low light. Photorealistic candid cinematic photograph, fictional wine branding, anatomically plausible hands, visible physical contact where requested. No captions, arrows, bounding boxes, watermarks, collage or UI. Create entirely original pirate characters with no actor or existing film character likeness.
```

</details>

Source review notes (quoted reference data):

> Цель предварительно связана с маской SAM3 по заданию генерации; подтвердите по самому фото. Форма масок и их владельцы ещё не проверены.
> Окружение: Пират в каюте при свечах. Проверьте реалистичность рук, хват и присутствие требуемых деталей.
> Запрос с Джеком Воробьём заблокирован генератором; здесь отдельный оригинальный пират.
