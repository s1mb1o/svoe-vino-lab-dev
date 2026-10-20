# main-selector-imagegen-pilot-v1-20261019:OW03

**Scene confirmed; masks pending. All targets/masks are proposals; no approved segmentation ground truth.**

![Original, proposed target and all three selector crops](../comparisons/pilot-v1--OW03.jpg)

**scene-v1: FAIL — provisional target/proxy.**

Reference title (source): Настоящая бутылка в открытой упаковке

Reference target description (source): Настоящая бутылка в открытом ящике

Expected intent: `clear`. Accepted target proposals: `d3`.

Scene group: `main-selector-imagegen-pilot-v1-20261019:OW03`. Development only; no independent split claim.

## Original and proposed target

![Original image](../images/pilot-v1--OW03.png)

![Proposed target overlay](../target-overlays/pilot-v1--OW03.jpg)

Green marks the unreviewed target proposal. Source image pixels are retained separately.

[Selected-label mask audit](../selected-label-mask-audit.json): incomplete proposal retention is flagged separately from target agreement.

[Full-resolution target proposal mask](../masks/pilot-v1--OW03-d3.png)

## Selector results

### scene-v1: FAIL — provisional target/proxy

Selected: d3; reason: existing_scene_v1_rank; mode: legacy; crop 269×761 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 97.8%. Mask ownership, label completeness and legibility still require human review.

![scene-v1 crop](../crops/pilot-v1--OW03-scene-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--OW03-scene-v1.png) · [Exact decision JSON](../results/pilot-v1--OW03-scene-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d39: 100.0%, 62772 source pixels; d49: 97.8%, 4040 source pixels

### semantic-v2: No automatic failure flag; usability pending

Selected: d3; reason: single_substantial_bottle_in_scene_context; mode: confident; crop 293×819 px. Target agreement: True. Target retention proxy: 100.0%; maximum other-bottle retention: 0.0%; minimum associated label retention: 100.0%. Mask ownership, label completeness and legibility still require human review. Selected-label mask audit: d39 100.0%; d49 100.0%.

![semantic-v2 crop](../crops/pilot-v1--OW03-semantic-v2.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--OW03-semantic-v2.png) · [Exact decision JSON](../results/pilot-v1--OW03-semantic-v2.json)

Returned label views: [label 1](../label-crops/pilot-v1--OW03-semantic-v2-0.png) · [label 2](../label-crops/pilot-v1--OW03-semantic-v2-1.png)

Associated label-mask retention proxies (unreviewed ownership): d39: 100.0%, 62772 source pixels; d49: 100.0%, 4040 source pixels

### dis-v1: PROXY failure; no native target ID

Selected: dis-foreground; reason: dis_foreground_mask; mode: foreground; crop 1259×1024 px. Target agreement: n/a (no native target ID). Target retention proxy: 100.0%; maximum other-bottle retention: 100.0%; minimum associated label retention: 98.9%. Mask ownership, label completeness and legibility still require human review.

![dis-v1 crop](../crops/pilot-v1--OW03-dis-v1.png)

[Full-resolution keep mask](../keep-masks/pilot-v1--OW03-dis-v1.png) · [Exact decision JSON](../results/pilot-v1--OW03-dis-v1.json)

Associated label-mask retention proxies (unreviewed ownership): d39: 100.0%, 62772 source pixels; d49: 98.9%, 4040 source pixels

## All frozen mask proposals

These links expose every detector proposal, including labels and hands. Shapes and owners are unreviewed.

| ID | Detector class | Full-resolution mask |
|---|---|---|
| d0 | wine bottle | [PNG](../masks/pilot-v1--OW03-d0.png) |
| d1 | wine bottle | [PNG](../masks/pilot-v1--OW03-d1.png) |
| d2 | wine bottle | [PNG](../masks/pilot-v1--OW03-d2.png) |
| d3 | wine bottle | [PNG](../masks/pilot-v1--OW03-d3.png) |
| d4 | wine bottle | [PNG](../masks/pilot-v1--OW03-d4.png) |
| d5 | wine bottle | [PNG](../masks/pilot-v1--OW03-d5.png) |
| d6 | wine bottle | [PNG](../masks/pilot-v1--OW03-d6.png) |
| d7 | wine bottle | [PNG](../masks/pilot-v1--OW03-d7.png) |
| d8 | wine bottle | [PNG](../masks/pilot-v1--OW03-d8.png) |
| d9 | wine bottle | [PNG](../masks/pilot-v1--OW03-d9.png) |
| d10 | wine bottle | [PNG](../masks/pilot-v1--OW03-d10.png) |
| d11 | wine bottle | [PNG](../masks/pilot-v1--OW03-d11.png) |
| d12 | wine bottle | [PNG](../masks/pilot-v1--OW03-d12.png) |
| d13 | wine bottle | [PNG](../masks/pilot-v1--OW03-d13.png) |
| d14 | wine bottle | [PNG](../masks/pilot-v1--OW03-d14.png) |
| d15 | wine bottle | [PNG](../masks/pilot-v1--OW03-d15.png) |
| d16 | wine bottle | [PNG](../masks/pilot-v1--OW03-d16.png) |
| d17 | wine bottle | [PNG](../masks/pilot-v1--OW03-d17.png) |
| d18 | wine bottle | [PNG](../masks/pilot-v1--OW03-d18.png) |
| d19 | wine bottle | [PNG](../masks/pilot-v1--OW03-d19.png) |
| d20 | wine bottle | [PNG](../masks/pilot-v1--OW03-d20.png) |
| d21 | wine bottle | [PNG](../masks/pilot-v1--OW03-d21.png) |
| d22 | wine bottle | [PNG](../masks/pilot-v1--OW03-d22.png) |
| d23 | wine bottle | [PNG](../masks/pilot-v1--OW03-d23.png) |
| d24 | wine bottle | [PNG](../masks/pilot-v1--OW03-d24.png) |
| d25 | wine bottle | [PNG](../masks/pilot-v1--OW03-d25.png) |
| d26 | wine bottle | [PNG](../masks/pilot-v1--OW03-d26.png) |
| d27 | wine bottle | [PNG](../masks/pilot-v1--OW03-d27.png) |
| d28 | wine bottle | [PNG](../masks/pilot-v1--OW03-d28.png) |
| d29 | wine bottle | [PNG](../masks/pilot-v1--OW03-d29.png) |
| d30 | wine bottle | [PNG](../masks/pilot-v1--OW03-d30.png) |
| d31 | wine bottle | [PNG](../masks/pilot-v1--OW03-d31.png) |
| d32 | wine bottle | [PNG](../masks/pilot-v1--OW03-d32.png) |
| d33 | wine bottle | [PNG](../masks/pilot-v1--OW03-d33.png) |
| d34 | wine bottle | [PNG](../masks/pilot-v1--OW03-d34.png) |
| d35 | wine bottle | [PNG](../masks/pilot-v1--OW03-d35.png) |
| d36 | wine bottle | [PNG](../masks/pilot-v1--OW03-d36.png) |
| d37 | wine bottle | [PNG](../masks/pilot-v1--OW03-d37.png) |
| d38 | wine label | [PNG](../masks/pilot-v1--OW03-d38.png) |
| d39 | wine label | [PNG](../masks/pilot-v1--OW03-d39.png) |
| d40 | wine label | [PNG](../masks/pilot-v1--OW03-d40.png) |
| d41 | wine label | [PNG](../masks/pilot-v1--OW03-d41.png) |
| d42 | wine label | [PNG](../masks/pilot-v1--OW03-d42.png) |
| d43 | wine label | [PNG](../masks/pilot-v1--OW03-d43.png) |
| d44 | wine label | [PNG](../masks/pilot-v1--OW03-d44.png) |
| d45 | wine label | [PNG](../masks/pilot-v1--OW03-d45.png) |
| d46 | wine label | [PNG](../masks/pilot-v1--OW03-d46.png) |
| d47 | wine label | [PNG](../masks/pilot-v1--OW03-d47.png) |
| d48 | wine label | [PNG](../masks/pilot-v1--OW03-d48.png) |
| d49 | wine label | [PNG](../masks/pilot-v1--OW03-d49.png) |
| d50 | wine label | [PNG](../masks/pilot-v1--OW03-d50.png) |
| d51 | wine label | [PNG](../masks/pilot-v1--OW03-d51.png) |
| d52 | wine label | [PNG](../masks/pilot-v1--OW03-d52.png) |
| d53 | wine label | [PNG](../masks/pilot-v1--OW03-d53.png) |
| d54 | wine label | [PNG](../masks/pilot-v1--OW03-d54.png) |
| d55 | wine label | [PNG](../masks/pilot-v1--OW03-d55.png) |
| d56 | wine label | [PNG](../masks/pilot-v1--OW03-d56.png) |
| d57 | wine label | [PNG](../masks/pilot-v1--OW03-d57.png) |
| d58 | wine label | [PNG](../masks/pilot-v1--OW03-d58.png) |
| d59 | wine label | [PNG](../masks/pilot-v1--OW03-d59.png) |
| d60 | wine label | [PNG](../masks/pilot-v1--OW03-d60.png) |
| d61 | wine label | [PNG](../masks/pilot-v1--OW03-d61.png) |
| d62 | wine label | [PNG](../masks/pilot-v1--OW03-d62.png) |
| d63 | box | [PNG](../masks/pilot-v1--OW03-d63.png) |
| d64 | box | [PNG](../masks/pilot-v1--OW03-d64.png) |
| d65 | box | [PNG](../masks/pilot-v1--OW03-d65.png) |
| d66 | box | [PNG](../masks/pilot-v1--OW03-d66.png) |
| d67 | box | [PNG](../masks/pilot-v1--OW03-d67.png) |
| d68 | price tag | [PNG](../masks/pilot-v1--OW03-d68.png) |
| d69 | price tag | [PNG](../masks/pilot-v1--OW03-d69.png) |
| d70 | price tag | [PNG](../masks/pilot-v1--OW03-d70.png) |
| d71 | price tag | [PNG](../masks/pilot-v1--OW03-d71.png) |
| d72 | price tag | [PNG](../masks/pilot-v1--OW03-d72.png) |
| d73 | price tag | [PNG](../masks/pilot-v1--OW03-d73.png) |
| d74 | price tag | [PNG](../masks/pilot-v1--OW03-d74.png) |
| d75 | price tag | [PNG](../masks/pilot-v1--OW03-d75.png) |
| d76 | price tag | [PNG](../masks/pilot-v1--OW03-d76.png) |
| d77 | price tag | [PNG](../masks/pilot-v1--OW03-d77.png) |
| d78 | price tag | [PNG](../masks/pilot-v1--OW03-d78.png) |
| d79 | price tag | [PNG](../masks/pilot-v1--OW03-d79.png) |
| d80 | price tag | [PNG](../masks/pilot-v1--OW03-d80.png) |

## Additional image-only context masks

Fixed English noun requests used RGB only; no target or annotation was supplied. Primary dN IDs remain unchanged. These masks are detector evidence, not reviewed ground truth.

[Saved validated context response](../context/pilot-v1--OW03.json)

| Appended ID | Context class | Full-resolution mask |
|---|---|---|
| d81 | bottle held in hand | [PNG](../context-masks/pilot-v1--OW03-d81.png) |
| d82 | bottle held in hand | [PNG](../context-masks/pilot-v1--OW03-d82.png) |
| d83 | bottle held in hand | [PNG](../context-masks/pilot-v1--OW03-d83.png) |

[Raw frozen detector response](../detections/pilot-v1--OW03.json)

<details><summary>Generation prompt (quoted source data)</summary>

```text
Use case: photorealistic-natural.
Asset type: one independent synthetic smartphone photograph for a wine-subject selection test dataset.
Style: a believable candid phone photo with realistic optics, materials, shadows, depth and anatomically plausible hands when requested. Natural photographic imperfections, not a diagram, collage, 3D render, advertisement or contact sheet.
Bottle labels may use fictional wine names and normal small wine-label text. Labels must have complete physical paper boundaries and plausible printing. Do not add target markers, bounding boxes, arrows, captions, segmentation colors, watermarks or any explanation outside the scene.
Generate exactly one landscape photograph, approximately 1536 by 1024 pixels. Any wine identity is fictional; this tests selection and visible-label preservation, not catalogue recognition.
Scene request: An open wooden wine gift box contains one real wine bottle, angled slightly forward so the whole visible main label and neck label can be seen. Beside it is a closed cardboard carton carrying a printed wine-bottle illustration. Natural shop counter photograph; the actual bottle in the open box is clearly the subject.
```

</details>

Source review notes (quoted reference data):

> На задних полках много дополнительных бутылок. Это полезная сложная сцена, но не полностью контролируемый инвентарь исходного рецепта.
