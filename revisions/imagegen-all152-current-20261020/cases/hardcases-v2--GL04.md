# main-selector-imagegen-hardcases-v2-20261020:GL04

**Scene confirmed; masks pending. All targets/masks are proposals; no approved segmentation ground truth.**

**scene-v1: No automatic failure flag; usability pending.**

Reference title (source): Хват слева — конденсат и блик

Reference target description (source): Удерживаемая холодная бутылка слева

Expected intent: `clear`. Accepted target proposals: `d0`.

Scene group: `main-selector-imagegen-hardcases-v2-20261020:GL04`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/hardcases-v2--GL04.png)

![Proposed target overlay](../target-overlays/hardcases-v2--GL04.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/hardcases-v2--GL04-d0.png)

## Selector results

### scene-v1: No automatic failure flag; usability pending

Selected: d0; reason: existing_scene_v1_rank; mode: legacy; crop 303×885 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 99.9%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/hardcases-v2--GL04-scene-v1.png)

[Full-resolution keep mask](../keep-masks/hardcases-v2--GL04-scene-v1.png) · [Exact decision JSON](../results/hardcases-v2--GL04-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 99.9%, 91207 source pixels

### semantic-v2: FAIL — provisional target/proxy

Selected: d1; reason: fallback_center_contains; mode: fallback; crop 260×963 px. Target agreement: False. Target retention proxy: 0.0%; maximum other-bottle retention: 100.0%; minimum associated label retention: 0.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d3 100.0%.

![semantic-v2 crop](../crops/hardcases-v2--GL04-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/hardcases-v2--GL04-semantic-v2.png) · [Exact decision JSON](../results/hardcases-v2--GL04-semantic-v2.json)

Returned label views: [label 1](../label-crops/hardcases-v2--GL04-semantic-v2-0.png)

Associated label-mask retention proxies (unreviewed ownership): d2: 0.0%, 91207 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 699×943 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 98.2%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/hardcases-v2--GL04-dis-v1.png)

[Full-resolution keep mask](../keep-masks/hardcases-v2--GL04-dis-v1.png) · [Exact decision JSON](../results/hardcases-v2--GL04-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d2: 100.0%, 91207 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/hardcases-v2--GL04-d0.png) |
| d1 | wine bottle | [PNG](../masks/hardcases-v2--GL04-d1.png) |
| d2 | wine label | [PNG](../masks/hardcases-v2--GL04-d2.png) |
| d3 | wine label | [PNG](../masks/hardcases-v2--GL04-d3.png) |
| d4 | hand | [PNG](../masks/hardcases-v2--GL04-d4.png) |

[Raw frozen detector response](../detections/hardcases-v2--GL04.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Generate exactly one independent photorealistic smartphone photograph, landscape 3:2, approximately 1536 by 1024 pixels. This is an ordinary wine selection moment, with natural perspective, believable glass and paper, imperfect ambient lighting, and realistic human anatomy. No collage, inset, split screen, arrows, highlights, bounding boxes, annotations, watermarks, UI, or text outside physical objects. Use fictional wine branding. Keep the target bottle's entire front label within the frame. The scene must communicate the stated gesture or physical relation visually; do not add any explanatory caption. Exactly two wine bottles on a terrace table at sunset. A single hand enters from left and visibly grips the LEFT pale green chilled wine bottle around its middle body, thumb opposing naturally bent fingers in contact with the glass. Fine condensation and a strong sunset highlight obscure some of its mint label. An unheld dry bottle on the right has an exceptionally clear cream label and is closer to center. The held bottle is slightly lifted above the tabletop; all label borders remain in frame. Photorealistic skin, moisture and glass, no additional hands, everyday smartphone exposure.
```

</details>

Source review notes (quoted reference data):

> Часть хвата скрыта бутылкой: хорошо виден большой палец спереди, противоположные пальцы почти не видны. Подтвердите естественность руки и очевидность удержания.
