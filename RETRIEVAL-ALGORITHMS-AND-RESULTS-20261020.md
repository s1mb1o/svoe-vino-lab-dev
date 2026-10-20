# Retrieval algorithms and benchmark results

Snapshot: 2026-10-20T19:57:11+03:00.

Scope: retrieval without re-ranking.

Repository package: [research/retrieval-20261020](research/retrieval-20261020/README.md).

This is the GitHub publication edition. The benchmark tables and exact result recipes are unchanged.
The original report checksum is recorded in [report-origin.json](research/retrieval-20261020/provenance/report-origin.json).

This document defines the retrieval algorithms in one place.
It records the exact tested parameter grids.
It includes the original experiments, the axial matrix, and the seven extension families.
It gives benchmark results for `my-failed-2` and `my`.
It gives separate all-budget and p512 leaderboards.
It includes exact recipes for every result referenced by an `Rxxx` code.

All final accuracy tables use the completed GX10 campaign.
The incomplete RTX4090 replay has a separate status section.
No RTX4090 score is inserted into a GX10 leaderboard.
The website matcher and the deployed matcher API are outside this document.
Those systems have opaque internal cascades.
No re-ranking experiment, model, score, or result is included.

The parameter grids define all tested recipes.
The document does not print all 706,376 per-variant metric rows.
The source table links committed scripts, specifications, and compact benchmark summaries.
A dataset inventory records the hashes and sizes of the unbundled complete databases.
Each reported winner has its parameters inside this document.

## Contents

1. [Model, inputs, and testsets](#1-model-inputs-and-testsets)
2. [Baseline and metric definitions](#2-baseline-and-metric-definitions)
3. [Query geometry](#3-query-geometry)
4. [Custom pooling](#4-custom-pooling)
5. [Reference galleries, axial views, and crop margins](#5-reference-galleries-axial-views-and-crop-margins)
6. [Label retrieval](#6-label-retrieval)
7. [Wine scoring and fusion](#7-wine-scoring-and-fusion)
8. [Exact enumeration and coverage](#8-exact-enumeration-and-coverage)
9. [Original named experiment results](#9-original-named-experiment-results)
10. [Controlled pooling and query results](#10-controlled-pooling-and-query-results)
11. [Overall top-five leaderboards](#11-overall-top-five-leaderboards)
12. [Best p512 variants](#12-best-p512-variants)
13. [Extension-family and patch-budget results](#13-extension-family-and-patch-budget-results)
14. [Exact result recipes](#14-exact-result-recipes)
15. [Separate RTX4090 replay](#15-separate-rtx4090-replay)
16. [Verification and interpretation limits](#16-verification-and-interpretation-limits)
17. [Source files](#17-source-files)

## 1. Model, inputs, and testsets

| Parameter | Value |
| --- | --- |
| Encoder | google/siglip2-so400m-patch16-naflex |
| Model revision | `cc24074f717b612951c2dead130904ab9b65a81e` |
| Output vector size | 1,152 dimensions |
| Patch size | 16 × 16 RGB pixels |
| Bottle patch budgets | 256, 512, 1024; reference and query budgets vary independently |
| Label patch budget | 512 for reference and query |
| p768 | Not tested |
| Inference type | BF16; native encoder and learned attention pooling head |
| Vector normalization | L2 normalization after the pooling head |
| Catalogue identity | 2,274 wine_slug columns in the frozen evaluation contexts |
| Candidate identity | wine_slug; source images and views are aggregated within a wine |
| Final candidate count | 10 distinct wine identities |
| Score coverage | All catalogue wine scores are calculated before Top-10 selection |
| Cluster role | The offline accuracy matrices do not use cluster pruning |
| Android scope | No SigLIP2 Base or Android runtime accuracy measurement is established here |

`p512` means at most 512 NaFlex input patches.
It does not mean a 512-dimensional output vector.
NaFlex keeps an aspect-dependent patch grid.
The number of real patches can be below the budget.
The remaining sequence positions are padding.
Padding has no foreground coverage and MUST remain excluded.

The reference bottle build has 3,058 distinct full-view sources.
The frozen label build has 3,440 reference sources.
Wine ownership can map one source to more than one wine row.
These source counts are different from the 2,274 wine identities.

The benchmark uses frozen image and mask inputs.
It does not use accepted answers to choose a crop, rotation, mask, or pooling weight.
SAM3 provides package and label masks in the preparation pipeline.
The package prompt is `wine bottle, can, packet, box`.
The label detection prompt is `barcode, bottle, label, bottle neck, can`.
The helper uses detection threshold 0.35 and mask threshold 0.5.
The benchmark reuses the stored segmentation answers and prepared pixels.
It does not rerun segmentation while comparing retrieval recipes.

Use the stored alpha mask when a cut has non-opaque alpha.
For an opaque source, `prepare.foreground` identifies near-white pixels with all RGB channels at least 245.
It removes only 4-connected near-white components that touch an image border.
It retains enclosed white regions.
An empty derived foreground falls back to a full foreground mask.
Custom pooling therefore uses the frozen foreground mask.
It does not classify each patch as whitespace from RGB color alone.

The label mask is placed in the bottle crop coordinates.
Accepted label masks use the existing mask-union rule.
The final label coverage is clipped to foreground coverage.
RGB, foreground, and label masks use the same geometric transformations.

| Testset | Assignments | All images | Positive assignments | Positive images | Negative assignments | no_match assignments |
| --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 668 | 627 | 668 | 627 | 0 | 0 |
| my | 3409 | 3031 | 2970 | 2808 | 430 | 9 |

The two frozen testsets share 619 image identities.
The hard testset has 8 images outside the current frozen `my` image set.
Do not treat these testsets as independent validation sets.
The hard testset was selected from earlier failures.
Both testsets were used for experiment selection.

| Testset | context.json SHA-256 | queries.json SHA-256 |
| --- | --- | --- |
| my-failed-2 | `ba10329117f578b0068bb643d89724bab0c1cc1e7457f60236a24f6d8ceefb9f` | `1b8fb97a08b08fe8d9c7a422c142e316e5f853cd827219236ca5504840cce93a` |
| my | `b09b74a231db69c207d2c8d439299aee4d8030ba10238def663b82a9bffff9be` | `a41cdc14704046c380df8a41a484529ed0608b573f1ac42543b8332025b7441d` |

## 2. Baseline and metric definitions

The standard bottle baseline is **siglip2-p512-rot5-seg**.

- Reference: frozen segmented bottle images; standard learned attention pooling; p512.
- Reference in-plane angles: 0, 5, 10, ..., 355 degrees.
- Query: original segmented bottle; no geometry rotation; p512.
- Pooling: profile `u` on both sides.
- Synthetic axial views: disabled.
- Crop margins: `null` on both sides. Preserve the frozen prepared canvas and resize rule.
- Wine score: maximum reference cosine.
- Label-space fusion: disabled.
- Re-ranking: absent.

`margin=null` does not mean a new tight crop with zero padding.
It preserves the existing prepared input.
`margin=0.0` applies a new tight foreground crop.
The two inputs can differ.

| Testset | R@1 | R@5 | R@10 | MRR@10 |
| --- | --- | --- | --- | --- |
| my-failed-2 | 44.01% (294/668) | 96.56% (645/668) | 99.70% (666/668) | 0.67125333 |
| my | 86.94% (2582/2970) | 99.19% (2946/2970) | 99.93% (2968/2970) | 0.92325236 |

For a positive assignment, a hit occurs when at least one candidate matches an accepted truth wine for that assignment.

```text
R@k = positive assignments with an accepted wine at rank <= k / positive assignments
delta_pp = 100 * (variant_hits_at_k - baseline_hits_at_k) / positive_assignments
MRR@10 = mean(1 / first_accepted_rank if rank <= 10 else 0)
```

Every percentage-point change uses the unrounded integer counts.
Display rounding can make a subtraction of displayed percentages differ by 0.01 pp.
The database field `mrr` is the reciprocal rank from the saved Top-10 list.
It is reported here as MRR@10.

One photo can have multiple positive assignments.
Assignment recall and image recall therefore use different weights.
The `image_top*` fields use the union of accepted positive truth wines for each photo.
The main leaderboards below use positive assignments.

The `my` context also contains negative and `no_match` assignments.
`negative_false1` counts the annotated rejected wine at rank 1 on a negative assignment.
`negative_false10` counts that rejected wine anywhere in Top-10.
`no_match_false1` counts a returned candidate on a `no_match` assignment.
`no_answer` counts assignments with no first candidate.
These counters are separate from positive recall.
Confidence gates in this report route between retrieval spaces.
They do not create a calibrated rejection classifier.

## 3. Query geometry

| Code | Exact operation |
| --- | --- |
| original | Use the original frozen segmented query. |
| iou | Choose the maximum mask/crop-IoU orientation. Rotate and crop. |
| min5 | Use the iou angle except when abs(angle) < 5 degrees. Then apply 0 degrees. |
| card5 | Use the iou angle except when abs((angle + 45) mod 90 - 45) < 5 degrees. Then apply 0 degrees. |
| crop | Take the tight foreground bounding box without rotation. Preserve the source scale. |
| mean-iou | L2-normalize the sum of the original unit vector and the iou unit vector. |
| mean-card5 | L2-normalize the sum of the original unit vector and the card5 unit vector. |

### Maximum-IoU angle

Use foreground alpha >= 128 to estimate the shape.
Calculate the convex hull of foreground pixel centers.
Include each pixel square when calculating the rotated bounds.
An enclosing crop contains the complete foreground.
Maximizing its IoU is equivalent to minimizing its enclosing rectangle area.

Search angles in [0, 90) at 0.5-degree steps.
Refine within +/-0.5 degrees of the best coarse angle at 0.05-degree steps.
Include 0 degrees in the refined candidates.
Keep 0 degrees when its area is within a relative tolerance of 1e-8 of the minimum.
Put the long axis in portrait orientation.
For an empty mask, fewer than 16 foreground pixels, or fewer than 3 hull points, use 0 degrees.

Resolve the remaining 180-degree ambiguity with the bottle-neck width test.
The probe is at most 512 × 512 pixels.
It requires at least 16 rows and a portrait aspect of at least 1.35.
Compare median widths over height bands 8–32% and 68–92%.
The narrow-to-wide ratio MUST be at most 0.72.
The wider band MUST cover at least 65% of the crop width.
The 80th percentile of the narrow band MUST also be at most 0.72 of the wide median.
If the neck is at the bottom, apply the equivalent 180-degree correction.
No candidate score or accepted answer enters this decision.

Rotate source RGB and masks with expanded canvases.
The query RGBA transform uses bicubic interpolation and transparent white fill.
Crop the transformed soft alpha to its nonzero bounding box.
Preserve the full soft alpha for the transform.
The binary geometry mask is only for angle estimation.

The 5-degree comparisons are strict.
An angle of exactly 5 degrees is not suppressed by `min5`.
An angle of 87 degrees is suppressed by `card5`.
It is not snapped to 90 degrees.

For a query-vector mean, encode each required image with its selected pooling profile.
Add the two unit vectors with equal weights.
Normalize their sum.
A zero sum remains a zero vector and gives no bottle candidates.
The mean does not select the better orientation from accepted answers.

## 4. Custom pooling

### Native SigLIP attention pooling

The encoder produces hidden patch vectors.
The native pooling head uses a learned probe and multi-head attention.
Profile `u` gives each real patch an additional prior weight of 1.
It preserves the native learned attention.
It does not replace attention with an arithmetic mean.

For one attention head, the custom prior changes attention logits as follows.

```text
attention_logit_j = q dot k_j / sqrt(head_dimension) + log(w_j)
attention_j = softmax(attention_logit)_j
pooled = native_attention(probe, hidden, hidden, additive_log_weight_bias)
pooled = pooled + native_MLP(native_layernorm(pooled))
embedding = L2_normalize(pooled)
```

Repeat the additive bias for each native attention head.
A zero weight gives a negative-infinity bias.
Padding weights are always zero.
If all real patch weights are zero, use weight 1 for the real patches.
Do not enable padding in this fallback.

The custom prior acts in the final pooling head.
It does not remove whitespace tokens from the vision encoder.
Whitespace tokens can still affect other patch representations inside the encoder.
All examples of equal weights refer to the additional prior, not to equal learned attention.

### Coverage and formulas

Let `f_j` be foreground coverage of a real patch in [0, 1].
Let `l_j` be label coverage of that patch.
Clip label coverage so that `0 <= l_j <= f_j`.
Let `b` be the whitespace floor.
Let `gamma` be the foreground exponent.
Let `lambda` be the label boost.

For fractional coverage:

```text
w_j = b * (1 - f_j**gamma) + f_j**gamma + (lambda - 1) * l_j
```

A complete foreground patch without a label has weight 1.
A complete label patch has weight `lambda`.
A complete whitespace patch has weight `b`.
The label term is additive.
It is not a multiplication of the fractional base weight.

For whole-empty-patch profiles:

```text
occupied_j = any(processed_binary_foreground_patch_sample > 0)
w_j = (1 if occupied_j else b) + (lambda - 1) * l_legacy_j
```

Only a completely empty real patch gets the reduced base weight.
Any retained foreground sample keeps base weight 1.
The whole-empty rule retains the original legacy label-coverage term.
It changes only the whitespace rule.

`legacy` coverage resizes the mask directly to the real NaFlex `(columns, rows)` grid with Pillow BOX resampling.
It flattens that grid in patch order and divides by 255.
`exact` coverage sends a float mask through the same NaFlex resize and patchify geometry as RGB.
It disables RGB conversion, rescaling, and normalization for the float mask.
It averages the 16 × 16 mask samples in each real patch.
It clips the processed mask values to [0, 1].

Whole-empty occupancy uses a binary source foreground mask converted to float.
The source test is foreground > 0.
The NaFlex output occupancy test is any sample > 0, with no epsilon.
This avoids loss of small foreground regions through an 8-bit mask resize.
Every mask input MUST match the RGB spatial shape and padding mask.

The weight maps are recalculated after each reference-view rotation or crop transformation.
They apply to original, in-plane-rotated, and synthetic axial reference views.
They also apply to the selected query geometry.
They are not limited to original reference images.

| Original code | Stored profile key | Whitespace rule | b | gamma | lambda |
| --- | --- | --- | --- | --- | --- |
| u | u | uniform | n/a | n/a | n/a |
| 5a | g1-bg010-l1-legacy | legacy | 0.1 | 1.0 | 1.0 |
| 5b | g1-bg000-l1-legacy | legacy | 0.0 | 1.0 | 1.0 |
| 6a | g1-bg010-l2-legacy | legacy | 0.1 | 1.0 | 2.0 |
| 6b | g1-bg000-l2-legacy | legacy | 0.0 | 1.0 | 2.0 |
| 6c | 6c | whole | 0.1 | 1.0 | 2.0 |
| 6d | 6d | whole | 0.0 | 1.0 | 2.0 |

### All 39 extension pooling profiles

| Profile key | Coverage | b | gamma | lambda |
| --- | --- | --- | --- | --- |
| `u` | uniform | n/a | n/a | n/a |
| `g0.5-bg010-l1-legacy` | legacy | 0.1 | 0.5 | 1.0 |
| `g0.5-bg010-l1-exact` | exact | 0.1 | 0.5 | 1.0 |
| `g0.5-bg010-l2-legacy` | legacy | 0.1 | 0.5 | 2.0 |
| `g0.5-bg010-l2-exact` | exact | 0.1 | 0.5 | 2.0 |
| `g1-bg010-l1-legacy` | legacy | 0.1 | 1.0 | 1.0 |
| `g1-bg010-l1-exact` | exact | 0.1 | 1.0 | 1.0 |
| `g1-bg010-l1.25-legacy` | legacy | 0.1 | 1.0 | 1.25 |
| `g1-bg010-l1.25-exact` | exact | 0.1 | 1.0 | 1.25 |
| `g1-bg010-l1.5-legacy` | legacy | 0.1 | 1.0 | 1.5 |
| `g1-bg010-l1.5-exact` | exact | 0.1 | 1.0 | 1.5 |
| `g1-bg010-l2-legacy` | legacy | 0.1 | 1.0 | 2.0 |
| `g1-bg010-l2-exact` | exact | 0.1 | 1.0 | 2.0 |
| `g1-bg010-l3-legacy` | legacy | 0.1 | 1.0 | 3.0 |
| `g1-bg010-l3-exact` | exact | 0.1 | 1.0 | 3.0 |
| `g2-bg010-l1-legacy` | legacy | 0.1 | 2.0 | 1.0 |
| `g2-bg010-l1-exact` | exact | 0.1 | 2.0 | 1.0 |
| `g2-bg010-l2-legacy` | legacy | 0.1 | 2.0 | 2.0 |
| `g2-bg010-l2-exact` | exact | 0.1 | 2.0 | 2.0 |
| `g0.5-bg000-l1-legacy` | legacy | 0.0 | 0.5 | 1.0 |
| `g0.5-bg000-l1-exact` | exact | 0.0 | 0.5 | 1.0 |
| `g0.5-bg000-l2-legacy` | legacy | 0.0 | 0.5 | 2.0 |
| `g0.5-bg000-l2-exact` | exact | 0.0 | 0.5 | 2.0 |
| `g1-bg000-l1-legacy` | legacy | 0.0 | 1.0 | 1.0 |
| `g1-bg000-l1-exact` | exact | 0.0 | 1.0 | 1.0 |
| `g1-bg000-l1.25-legacy` | legacy | 0.0 | 1.0 | 1.25 |
| `g1-bg000-l1.25-exact` | exact | 0.0 | 1.0 | 1.25 |
| `g1-bg000-l1.5-legacy` | legacy | 0.0 | 1.0 | 1.5 |
| `g1-bg000-l1.5-exact` | exact | 0.0 | 1.0 | 1.5 |
| `g1-bg000-l2-legacy` | legacy | 0.0 | 1.0 | 2.0 |
| `g1-bg000-l2-exact` | exact | 0.0 | 1.0 | 2.0 |
| `g1-bg000-l3-legacy` | legacy | 0.0 | 1.0 | 3.0 |
| `g1-bg000-l3-exact` | exact | 0.0 | 1.0 | 3.0 |
| `g2-bg000-l1-legacy` | legacy | 0.0 | 2.0 | 1.0 |
| `g2-bg000-l1-exact` | exact | 0.0 | 2.0 | 1.0 |
| `g2-bg000-l2-legacy` | legacy | 0.0 | 2.0 | 2.0 |
| `g2-bg000-l2-exact` | exact | 0.0 | 2.0 | 2.0 |
| `6c` | whole | 0.1 | 1.0 | 2.0 |
| `6d` | whole | 0.0 | 1.0 | 2.0 |

The profile grid uses whitespace floors {0, 0.1}.
It crosses gamma {0.5, 1, 2} with label boosts {1, 2}.
It adds label boosts {1.25, 1.5, 3} only at gamma 1.
It tests both legacy and exact coverage for these fractional profiles.
It also includes `u`, `6c`, and `6d`.
The grid does not cross every label boost with every gamma.

## 5. Reference galleries, axial views, and crop margins

| Gallery | In-plane reference angles |
| --- | --- |
| zero | 0 |
| cardinal | 0, 90, 180, 270 |
| rot5 | 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150, 155, 160, 165, 170, 175, 180, 185, 190, 195, 200, 205, 210, 215, 220, 225, 230, 235, 240, 245, 250, 255, 260, 265, 270, 275, 280, 285, 290, 295, 300, 305, 310, 315, 320, 325, 330, 335, 340, 345, 350, 355 |

### Synthetic bottle-axis views

The axial angle set is {-30, -25, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30} degrees.
These angles simulate a turn around the bottle center axis.
They are different from in-plane image rotations.

The renderer projects label texture on an approximate cylindrical surface.
It preserves the bottle silhouette and original alpha.
The zero-angle output is pixel-identical to the prepared source.
The renderer first reverses the photographed cylinder projection.
It then applies the requested axial turn and projects the texture again.
The cylinder profile comes from the bottle silhouette.
The label region uses the frozen label mask.

The campaign uses one label layer.
Its camera distance is 300 cylinder radii.
Its `camera_y` is the midpoint of the label bounds.
It enables profile smoothing.
It reconstructs hidden glass with the `vertical` fill rule.
If vertical reconstruction fails for the declared glass reason, it uses the `inpaint` fallback.
The default repair margin is 5 source pixels before image-scale adjustment.
The inpaint fallback uses OpenCV TELEA with radius 4.
The renderer uses bilinear remapping.
The renderer applies its default lighting adjustment, clipped to [0.75, 1.25].

The horizontal projection uses this model.

```text
x = center_x + R * sqrt(D**2 - 1) * sin(phi) / (D - cos(phi))
D = 300
```

For destination pixel `(x, y)`, use the row cylinder center `c(y)` and radius `R(y)`.
The exact inverse and turn mapping is:

```text
T = sqrt(D**2 - 1)
q = (x - c(y)) / R(y)
C = (q**2 * D + T**2 * sqrt(max(0, 1 - q**2))) / (T**2 + q**2)
S = q * (D - C) / T
Cs = C * cos(theta) + S * sin(theta)
Ss = S * cos(theta) - C * sin(theta)
denominator = max(D - Cs, 0.000001)
source_y = camera_y + (y - camera_y) * (D - C) / denominator
source_x = c(source_y) + R(source_y) * T * Ss / denominator
```

Interpolate the source row center and radius linearly.
Retain samples only when abs(q) <= 1, Cs > 1/D, and the source coordinates are inside the image.
Remap premultiplied label RGB and label coverage together.
The default lighting ratio is:

```text
shade = clip((0.87 + 0.1*C - 0.055*S) /
             max(0.87 + 0.1*Cs - 0.055*Ss, 0.000001), 0.75, 1.25)
```

Blend the remapped label over the reconstructed glass with its remapped coverage.
Round and clip final RGB values to [0, 255].
Keep the original bottle alpha unchanged.
The final axial RGB image is composited on white.
The final maximum side is 1024 pixels with no upscaling.
Foreground and label masks follow the same view mapping.
The label mask is clipped to the foreground.

The initial renderer considered 2,265 sources.
It rendered 2,262 sources and skipped 3 sources.
It created 27,144 unique nonzero-angle vectors before wine ownership expansion.
The wine-expanded nonzero rows number 27,252.
Unsupported sources retain their original gallery coverage.
Do not remove their baseline vectors.

`axial_union=true` adds the nonzero axial views at in-plane 0 degrees to the selected original gallery.
It does not form an axial × in-plane Cartesian product.
The existing zero-angle vectors are retained once.

### Cartesian extension

The later Cartesian family adds the missing axial views at in-plane {90, 180, 270} degrees.
It adds 12 nonzero axial angles × 3 in-plane angles = 36 views per renderable source.
It reuses existing axial views at in-plane 0 degrees.
It reuses existing zero-axial cardinal views.

- `cartesian`: cardinal gallery plus the full axial/cardinal union.
- `rot5-plus-cartesian`: rot5 gallery plus the full axial/cardinal union.

Do not interpret `axial_union=true` alone as the Cartesian extension.

### Crop margins

Reference and query margins vary independently over {0, 0.02, 0.05, 0.10}.
Start from the tight nonzero foreground bounding box.
Let its width and height be `W` and `H`.

```text
dx = round(W * margin)
dy = round(H * margin)
canvas_width = W + 2 * dx
canvas_height = H + 2 * dy
```

Use Python round semantics.
Place the tight RGB crop at `(dx, dy)` on a white canvas.
Place the foreground and label crops at the same coordinates on zero masks.
The margin is per edge.
A 0.05 margin adds about 10% total width and height before NaFlex processing.
The margin grid uses pooling `u` or `6b` on both sides.
It does not add axial views.
It preserves the selected query geometry before adding the margin.

## 6. Label retrieval

Segment the bottle first.
Segment the label inside the selected bottle crop.
Keep the accepted label-mask union.
Encode the label crop with standard learned attention pooling at p512.
Do not apply the bottle custom-pooling prior to the label encoder.

For a label rotation, minimize the enclosing crop area of its alpha >= 128 hull.
Use the same 0.5-degree coarse search and 0.05-degree refinement.
Choose the smallest absolute rotation modulo 90 degrees.
The label angle is `(angle + 45) mod 90 - 45`.
Do not use the bottle-neck heuristic for a label.
Rotate RGB on white and rotate the soft mask with the same angle.
Crop with the rotated mask.
Do not composite the already-white RGB through soft alpha a second time.

| Variant | Rotate reference label | Rotate query bottle before label segmentation | Rotate extracted query label |
| --- | --- | --- | --- |
| 7a | False | False | False |
| 7b | False | True | False |
| 7c | False | False | True |
| 7d | True | False | True |
| 7e | False | True | True |
| 7f | True | False | False |
| 7g | True | True | False |
| 7h | True | True | True |

The initial eight label experiments use one original or aligned vector per reference label.
They do not add rot5 augmentation in that initial comparison.
The complete matrix later crosses each label geometry with zero, cardinal, and rot5 galleries.
Apply each in-plane reference angle after the chosen label geometry.
This gives 8 × 3 = 24 label configurations.

The matched original and aligned label builds use the same fixed batch schedule.
Reference batches have 36 images.
The initial label query service uses one image per request.
This matched schedule prevents the old mixed-batch gallery from confounding the rotation comparison.

If a standalone label query has no label, it returns no candidates.
It keeps the assignment in the denominator.
For bottle–label fusion, a missing label uses the bottle list.

## 7. Wine scoring and fusion

### Per-wine scoring

Reference and query vectors are L2-normalized.
Their dot product is cosine similarity.
Score every retained reference view.
Group the scores by wine_slug.

```text
max:       score(wine) = maximum retained view cosine
top2-mean: score(wine) = mean of the best min(2, available_views) cosines
top3-mean: score(wine) = mean of the best min(3, available_views) cosines
```

Equal-score views remain distinct views for top-k aggregation.
Do not deduplicate equal floating-point values before the mean.
A wine with no reference vector has score negative infinity.
Cosine ties between wines use ascending wine_slug.
The Top-10 list contains distinct wine identities.

### Fusion formulas

Let `B(w)` and `L(w)` be complete per-wine bottle and label scores.
Let `alpha` be the bottle weight.

```text
mean: score(w) = alpha * B(w) + (1 - alpha) * L(w)
max:  score(w) = max(B(w), L(w))
rrf:  score(w) = 1 / (60 + bottle_rank(w)) + 1 / (60 + label_rank(w))
```

Use mean weights alpha in {0.25, 0.50, 0.75}.
If only one cosine is available, the mean keeps that available cosine.
Do not insert zero for an absent reference.
RRF uses 1-based ranks over each complete wine list.
An absent wine contributes zero to RRF.
All formulas use complete per-wine arrays before Top-10 selection.
Max fusion keeps the larger original cosine for a duplicate wine.

### Confidence routing

For each space, calculate the unrounded top-1 minus top-2 wine cosine gap.
A gap passes when it is at least the threshold for that space.
If only one space passes, use that space.
If both spaces pass, compare gap/threshold.
A tie selects the bottle space.

- `always`: use the selected merge formula for every query.
- `gate`: use the confident space list. Use the merge formula if neither space passes.
- `conflict`: if both confident spaces choose different winners, use the merge formula.
- `pin`: select the confident winner with the same rule as gate. Put that winner first. Fill positions 2–10 from the merged list, with no duplicate of the winner.

A pinned list has explicit ordinal ranks.
Its displayed scores need not decrease across the pinned winner and the tail.
The mode is retrieval-score fusion.
It does not invoke a second model on candidate/query pairs.

### Exact 42-policy grid

The grid contains 5 always policies, 15 equal-threshold gates, 12 unequal-threshold gates, 5 conflict policies, and 5 pin policies.
The equal-threshold levels are {0.005, 0.01, 0.02}.
The unequal-threshold grid uses all ordered unequal pairs from that set for mean50 and max.
Conflict and pin use threshold 0.01 in each space.

| Policy ID | Merge | Bottle alpha | Mode | Bottle threshold | Label threshold |
| --- | --- | --- | --- | --- | --- |
| `always-mean25` | mean | 0.25 | always | None | None |
| `always-mean50` | mean | 0.5 | always | None | None |
| `always-mean75` | mean | 0.75 | always | None | None |
| `always-max` | max | None | always | None | None |
| `always-rrf` | rrf | None | always | None | None |
| `gate-mean25-005` | mean | 0.25 | gate | 0.005 | 0.005 |
| `gate-mean50-005` | mean | 0.5 | gate | 0.005 | 0.005 |
| `gate-mean75-005` | mean | 0.75 | gate | 0.005 | 0.005 |
| `gate-max-005` | max | None | gate | 0.005 | 0.005 |
| `gate-rrf-005` | rrf | None | gate | 0.005 | 0.005 |
| `gate-mean25-010` | mean | 0.25 | gate | 0.01 | 0.01 |
| `gate-mean50-010` | mean | 0.5 | gate | 0.01 | 0.01 |
| `gate-mean75-010` | mean | 0.75 | gate | 0.01 | 0.01 |
| `gate-max-010` | max | None | gate | 0.01 | 0.01 |
| `gate-rrf-010` | rrf | None | gate | 0.01 | 0.01 |
| `gate-mean25-020` | mean | 0.25 | gate | 0.02 | 0.02 |
| `gate-mean50-020` | mean | 0.5 | gate | 0.02 | 0.02 |
| `gate-mean75-020` | mean | 0.75 | gate | 0.02 | 0.02 |
| `gate-max-020` | max | None | gate | 0.02 | 0.02 |
| `gate-rrf-020` | rrf | None | gate | 0.02 | 0.02 |
| `gate-mean50-b0.005-l0.010` | mean | 0.5 | gate | 0.005 | 0.01 |
| `gate-max-b0.005-l0.010` | max | None | gate | 0.005 | 0.01 |
| `gate-mean50-b0.005-l0.020` | mean | 0.5 | gate | 0.005 | 0.02 |
| `gate-max-b0.005-l0.020` | max | None | gate | 0.005 | 0.02 |
| `gate-mean50-b0.010-l0.005` | mean | 0.5 | gate | 0.01 | 0.005 |
| `gate-max-b0.010-l0.005` | max | None | gate | 0.01 | 0.005 |
| `gate-mean50-b0.010-l0.020` | mean | 0.5 | gate | 0.01 | 0.02 |
| `gate-max-b0.010-l0.020` | max | None | gate | 0.01 | 0.02 |
| `gate-mean50-b0.020-l0.005` | mean | 0.5 | gate | 0.02 | 0.005 |
| `gate-max-b0.020-l0.005` | max | None | gate | 0.02 | 0.005 |
| `gate-mean50-b0.020-l0.010` | mean | 0.5 | gate | 0.02 | 0.01 |
| `gate-max-b0.020-l0.010` | max | None | gate | 0.02 | 0.01 |
| `conflict-mean25-010` | mean | 0.25 | conflict | 0.01 | 0.01 |
| `conflict-mean50-010` | mean | 0.5 | conflict | 0.01 | 0.01 |
| `conflict-mean75-010` | mean | 0.75 | conflict | 0.01 | 0.01 |
| `conflict-max-010` | max | None | conflict | 0.01 | 0.01 |
| `conflict-rrf-010` | rrf | None | conflict | 0.01 | 0.01 |
| `pin-mean25-010` | mean | 0.25 | pin | 0.01 | 0.01 |
| `pin-mean50-010` | mean | 0.5 | pin | 0.01 | 0.01 |
| `pin-mean75-010` | mean | 0.75 | pin | 0.01 | 0.01 |
| `pin-max-010` | max | None | pin | 0.01 | 0.01 |
| `pin-rrf-010` | rrf | None | pin | 0.01 | 0.01 |

### Initial experiment-8 conditions

The original pair uses the baseline bottle and label geometry 7a.
The IoU pair uses the unrestricted-IoU bottle and label geometry 7h.
These initial label spaces have their original one-vector-per-label setup.
The table below defines the exact initial named conditions.
`threshold=null` means always merge.

| Condition | Pair | Merge | Threshold | Fallback on confident disagreement |
| --- | --- | --- | --- | --- |
| 8a | original | mean | 0.01 | False |
| 8b | original | max | 0.01 | False |
| 8c | original | rrf | 0.01 | False |
| 8d | original | mean | 0.01 | True |
| 8e | original | mean | None | False |
| 8f | original | max | None | False |
| 8g | original | rrf | None | False |
| 8a-iou | iou | mean | 0.01 | False |
| 8b-iou | iou | max | 0.01 | False |
| 8c-iou | iou | rrf | 0.01 | False |
| 8d-iou | iou | mean | 0.01 | True |
| 8e-iou | iou | mean | None | False |
| 8f-iou | iou | max | None | False |
| 8g-iou | iou | rrf | None | False |
| 8a-gap005 | original | mean | 0.005 | False |
| 8a-gap020 | original | mean | 0.02 | False |
| 8b-gap005 | original | max | 0.005 | False |
| 8b-gap020 | original | max | 0.02 | False |

The later named experiment 9 combines bottle pooling 6a or 6b with label geometry 7a.
It keeps the original bottle query and rot5 bottle references.
For each pool, it tests gate-mean50-010, gate-max-010, always-mean50, and always-max.
The eight combinations are 9a–9d for 6a and 9e–9h for 6b.

## 8. Exact enumeration and coverage

### Original and axial matrices

The original matrix crosses:

```text
7 same-side bottle pools × 7 query geometries × 3 in-plane galleries = 147 bottle conditions
8 label geometries × 3 in-plane label galleries = 24 label conditions
147 × 24 × 42 fusion policies = 148,176 fusion variants
147 bottle-only + 24 label-only controls = 171 single-space controls
original total = 148,347 variants per testset
```

The axial extension adds 147 axial bottle controls and 148,176 axial fusion variants.
It reuses the 24 label-only controls.
It therefore adds 148,323 variants.
The combined original and axial matrix has 296,670 unique variants per testset.

### Seven extension families

Use `E1` to `E7` for the later family IDs.
These family IDs are different from original experiment numbers 1 to 8.
The exact enumeration uses the rules below.
Family memberships can overlap after recipe deduplication.

| Family | Name | Exact grid | Bottle recipe memberships |
| --- | --- | --- | --- |
| E1 | Independent reference and query pooling | 7 reference pools × 7 query pools × 7 query geometries × 3 galleries × axial {false,true}; max aggregation; p512; margins null. | 2058 |
| E2 | Nonlinear foreground weights | Same pool on both sides; legacy coverage; gamma {0.5,2}; b {0,0.1}; lambda {1,2}; 7 geometries × 3 galleries × axial {false,true}; p512. | 336 |
| E3 | Label boost | Remaining legacy profiles at gamma 1 plus uniform and whole-empty controls; 7 geometries × 3 galleries × axial {false,true}; p512. Overlap with E1 is retained as membership. | 546 |
| E4 | Crop margins and exact NaFlex coverage | All 18 exact fractional profiles × 7 geometries × 3 galleries × axial {false,true}; plus pools {u,6b} × 4 reference margins × 4 query margins × 7 geometries × 3 galleries, without axial views. | 1428 |
| E5 | Axial and cardinal Cartesian views | 7 same-side pools × 7 geometries × galleries {cartesian,rot5-plus-cartesian}; axial enabled; p512. | 98 |
| E6 | NaFlex patch budgets | Same-side pools {u,6b} × reference budgets {256,512,1024} × query budgets {256,512,1024} × 7 geometries × 3 galleries × axial {false,true}; margins null. | 756 |
| E7 | Reference score aggregation | 7 same-side pools × 7 geometries × 3 galleries × axial {false,true} × aggregation {top2-mean,top3-mean}; p512; margins null. | 588 |

The exact-coverage profiles are assigned to E4 before the gamma test in the enumerator.
This is why E2 lists 336 legacy memberships and E4 also contains exact nonlinear profiles.
The prose protocol groups these checks by scientific purpose.
The enumeration membership list is the source for the coverage and family result tables.

The extension does not multiply unrelated new axes.
For example, it does not cross every margin, patch budget, asymmetric pooling pair, axial Cartesian gallery, and fusion policy.
It executes the finite family grids above.

Each deduplicated bottle recipe has 11 comparisons:

- One bottle-only comparison.
- Two fixed label spaces: `l-7f-rot5` and `l-7g-cardinal`.
- Five fusion policies for each label space: `always-mean50`, `always-mean75`, `gate-mean50-010`, `pin-max-010`, and `always-rrf`.

The extension therefore has 5,432 × 11 = 59,752 variants per testset.
It contains 294 bottle recipes whose 11 comparisons repeat earlier controls.
Exclude those 3,234 rows when combining campaigns.
The extension contributes 56,518 additional unique variants.
The final combined count is 296,670 + 56,518 = **353,188 variants per testset**.
The two testsets together contain 706,376 final metric rows.

### Recipe fields and IDs

Every extension bottle recipe has these fields.

```json
{
  "reference_pool": "stored profile key",
  "query_pool": "stored profile key",
  "query_geometry": "original|iou|min5|card5|crop|mean-iou|mean-card5",
  "gallery": "zero|cardinal|rot5|cartesian|rot5-plus-cartesian",
  "axial_union": false,
  "aggregation": "max|top2-mean|top3-mean",
  "reference_budget": 512,
  "query_budget": 512,
  "reference_margin": null,
  "query_margin": null
}
```

Resolve original aliases with the pooling alias table before hashing.
Use the exact Python JSON serialization below.
Its default spaces are significant for the ID.

```python
bottle_id = "x-" + sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()[:24]
bottle_only_variant_id = bottle_id
fusion_variant_id = bottle_id + "__" + label_id + "__" + policy_id
```

An original matrix bottle ID has the form `b-{pool}-{query}-{gallery}`.
Its axial version adds `+axial`.
A label ID has the form `l-{7a..7h}-{gallery}`.
A single-space control adds the prefix `single-`.
Fusion IDs join bottle, label, and policy IDs with `__`.

| Scope | my-failed-2 | my |
| --- | --- | --- |
| Original matrix | 148,347; audited | 148,347; audited |
| Axial additions | 148,323; audited | 148,323; audited |
| Combined earlier matrix | 296,670 | 296,670 |
| Extension rows before deduplication | 59,752; audited | 59,752; audited |
| Repeated extension controls | 3,234 | 3,234 |
| Final unique retrieval variants | 353,188 | 353,188 |
| Final p512/p512 variants | 345,796 | 345,796 |

## 9. Original named experiment results

These tables preserve the saved named experiment results.
They include initial 1–8 comparisons, original 9 combinations, query controls, and the first axial checks.
They are historical controls inside the larger campaign.
Do not add these counts to the combined unique-variant count.
Do not merge the `my complement` denominator with either current testset.
The complement was evaluated before this document and is not a fresh validation cohort.

Each result cell contains recall percent, the raw hit count, and the denominator.
Every delta uses the standard baseline on the same current testset.
The complement table has no current-testset delta.

### my-failed-2: Original 1–6

| Named condition | R@1 | R@5 | R@10 |
| --- | --- | --- | --- |
| 1. Baseline | 44.01% (294/668); +0.00 pp | 96.56% (645/668); +0.00 pp | 99.70% (666/668); +0.00 pp |
| 2. Rotate for maximum IoU | 45.96% (307/668); +1.95 pp | 96.71% (646/668); +0.15 pp | 99.70% (666/668); +0.00 pp |
| 3. Skip angles below 5° | 45.36% (303/668); +1.35 pp | 96.56% (645/668); +0.00 pp | 99.70% (666/668); +0.00 pp |
| 4. Skip near all cardinal angles | 45.36% (303/668); +1.35 pp | 96.56% (645/668); +0.00 pp | 99.70% (666/668); +0.00 pp |
| 5a. Whitespace 0.1 | 52.69% (352/668); +8.68 pp | 96.71% (646/668); +0.15 pp | 99.25% (663/668); -0.45 pp |
| 5b. Whitespace 0 | 52.25% (349/668); +8.23 pp | 96.86% (647/668); +0.30 pp | 99.40% (664/668); -0.30 pp |
| 6a. Whitespace 0.1; label 2 | 55.69% (372/668); +11.68 pp | 97.90% (654/668); +1.35 pp | 99.70% (666/668); +0.00 pp |
| 6b. Whitespace 0; label 2 | 55.39% (370/668); +11.38 pp | 97.90% (654/668); +1.35 pp | 99.70% (666/668); +0.00 pp |

### my-failed-2: 6c–6d: whole whitespace patches

| Named condition | R@1 | R@5 | R@10 |
| --- | --- | --- | --- |
| 6c. Whole whitespace patch 0.1; label 2 | 53.59% (358/668); +9.58 pp | 97.01% (648/668); +0.45 pp | 99.85% (667/668); +0.15 pp |
| 6d. Whole whitespace patch 0; label 2 | 52.99% (354/668); +8.98 pp | 97.31% (650/668); +0.75 pp | 100.00% (668/668); +0.30 pp |

### my-failed-2: 1b–2b: reference rotation ablation

| Named condition | R@1 | R@5 | R@10 |
| --- | --- | --- | --- |
| 1. Baseline; full 5-degree catalogue | 44.01% (294/668); +0.00 pp | 96.56% (645/668); +0.00 pp | 99.70% (666/668); +0.00 pp |
| 1b. Baseline; 0-degree reference vectors only | 45.36% (303/668); +1.35 pp | 94.16% (629/668); -2.40 pp | 98.65% (659/668); -1.05 pp |
| 2. Maximum-IoU query; full 5-degree catalogue | 45.96% (307/668); +1.95 pp | 96.71% (646/668); +0.15 pp | 99.70% (666/668); +0.00 pp |
| 2b. Maximum-IoU query rotation; 0-degree reference vectors only | 46.11% (308/668); +2.10 pp | 95.51% (638/668); -1.05 pp | 99.25% (663/668); -0.45 pp |

### my-failed-2: 7a–7h: labels

| Named condition | R@1 | R@5 | R@10 |
| --- | --- | --- | --- |
| 7a: reference rotate=false; bottle rotate=false; label rotate=false | 56.89% (380/668); +12.87 pp | 94.01% (628/668); -2.54 pp | 96.41% (644/668); -3.29 pp |
| 7b: reference rotate=false; bottle rotate=true; label rotate=false | 55.39% (370/668); +11.38 pp | 94.31% (630/668); -2.25 pp | 97.31% (650/668); -2.40 pp |
| 7c: reference rotate=false; bottle rotate=false; label rotate=true | 56.29% (376/668); +12.28 pp | 93.11% (622/668); -3.44 pp | 97.01% (648/668); -2.69 pp |
| 7d: reference rotate=true; bottle rotate=false; label rotate=true | 55.99% (374/668); +11.98 pp | 94.31% (630/668); -2.25 pp | 97.31% (650/668); -2.40 pp |
| 7e: reference rotate=false; bottle rotate=true; label rotate=true | 55.54% (371/668); +11.53 pp | 93.41% (624/668); -3.14 pp | 96.86% (647/668); -2.84 pp |
| 7f: reference rotate=true; bottle rotate=false; label rotate=false | 56.89% (380/668); +12.87 pp | 94.16% (629/668); -2.40 pp | 97.01% (648/668); -2.69 pp |
| 7g: reference rotate=true; bottle rotate=true; label rotate=false | 56.14% (375/668); +12.13 pp | 94.31% (630/668); -2.25 pp | 97.60% (652/668); -2.10 pp |
| 7h: reference rotate=true; bottle rotate=true; label rotate=true | 55.99% (374/668); +11.98 pp | 94.46% (631/668); -2.10 pp | 97.16% (649/668); -2.54 pp |

### my-failed-2: 8: bottle and label fusion

| Named condition | R@1 | R@5 | R@10 |
| --- | --- | --- | --- |
| 8a: Gap gate; average cosine fallback | 56.74% (379/668); +12.72 pp | 96.26% (643/668); -0.30 pp | 98.05% (655/668); -1.65 pp |
| 8b: Gap gate; unchanged cosine merge fallback | 56.14% (375/668); +12.13 pp | 95.81% (640/668); -0.75 pp | 98.20% (656/668); -1.50 pp |
| 8c: Gap gate; reciprocal rank fusion fallback | 57.04% (381/668); +13.02 pp | 96.26% (643/668); -0.30 pp | 98.20% (656/668); -1.50 pp |
| 8d: Gap gate; average on a confident conflict | 56.59% (378/668); +12.57 pp | 96.56% (645/668); +0.00 pp | 98.20% (656/668); -1.50 pp |
| 8e: Always average cosine | 56.74% (379/668); +12.72 pp | 97.46% (651/668); +0.90 pp | 99.25% (663/668); -0.45 pp |
| 8f: Always merge unchanged cosine | 53.14% (355/668); +9.13 pp | 97.46% (651/668); +0.90 pp | 99.55% (665/668); -0.15 pp |
| 8g: Always reciprocal rank fusion | 52.54% (351/668); +8.53 pp | 97.31% (650/668); +0.75 pp | 98.95% (661/668); -0.75 pp |
| 8a-iou: Gap gate; average cosine fallback | 57.04% (381/668); +13.02 pp | 96.56% (645/668); +0.00 pp | 98.35% (657/668); -1.35 pp |
| 8b-iou: Gap gate; unchanged cosine merge fallback | 57.78% (386/668); +13.77 pp | 96.11% (642/668); -0.45 pp | 98.35% (657/668); -1.35 pp |
| 8c-iou: Gap gate; reciprocal rank fusion fallback | 57.04% (381/668); +13.02 pp | 96.26% (643/668); -0.30 pp | 98.20% (656/668); -1.50 pp |
| 8d-iou: Gap gate; average on a confident conflict | 56.89% (380/668); +12.87 pp | 96.41% (644/668); -0.15 pp | 98.35% (657/668); -1.35 pp |
| 8e-iou: Always average cosine | 57.34% (383/668); +13.32 pp | 97.46% (651/668); +0.90 pp | 99.55% (665/668); -0.15 pp |
| 8f-iou: Always merge unchanged cosine | 55.39% (370/668); +11.38 pp | 97.31% (650/668); +0.75 pp | 99.70% (666/668); +0.00 pp |
| 8g-iou: Always reciprocal rank fusion | 52.10% (348/668); +8.08 pp | 96.41% (644/668); -0.15 pp | 99.25% (663/668); -0.45 pp |
| 8a-gap005: Gap 0.005; average cosine fallback | 55.84% (373/668); +11.83 pp | 95.81% (640/668); -0.75 pp | 97.75% (653/668); -1.95 pp |
| 8a-gap020: Gap 0.02; average cosine fallback | 56.74% (379/668); +12.72 pp | 96.71% (646/668); +0.15 pp | 98.50% (658/668); -1.20 pp |
| 8b-gap005: Gap 0.005; unchanged cosine merge fallback | 55.84% (373/668); +11.83 pp | 95.81% (640/668); -0.75 pp | 97.90% (654/668); -1.80 pp |
| 8b-gap020: Gap 0.02; unchanged cosine merge fallback | 54.49% (364/668); +10.48 pp | 96.41% (644/668); -0.15 pp | 98.50% (658/668); -1.20 pp |

### my-failed-2: 9: custom pooling and labels

| Named condition | R@1 | R@5 | R@10 |
| --- | --- | --- | --- |
| 9a: 6a bottle + 7a labels; gap 0.01; average scores | 59.88% (400/668); +15.87 pp | 97.16% (649/668); +0.60 pp | 98.20% (656/668); -1.50 pp |
| 9b: 6a bottle + 7a labels; gap 0.01; merge unchanged scores | 60.18% (402/668); +16.17 pp | 96.56% (645/668); +0.00 pp | 98.35% (657/668); -1.35 pp |
| 9c: 6a bottle + 7a labels; always average scores | 60.03% (401/668); +16.02 pp | 98.20% (656/668); +1.65 pp | 99.10% (662/668); -0.60 pp |
| 9d: 6a bottle + 7a labels; always merge unchanged scores | 58.83% (393/668); +14.82 pp | 97.60% (652/668); +1.05 pp | 99.70% (666/668); +0.00 pp |
| 9e: 6b bottle + 7a labels; gap 0.01; average scores | 60.18% (402/668); +16.17 pp | 97.01% (648/668); +0.45 pp | 98.35% (657/668); -1.35 pp |
| 9f: 6b bottle + 7a labels; gap 0.01; merge unchanged scores | 61.23% (409/668); +17.22 pp | 96.56% (645/668); +0.00 pp | 98.35% (657/668); -1.35 pp |
| 9g: 6b bottle + 7a labels; always average scores | 60.18% (402/668); +16.17 pp | 98.35% (657/668); +1.80 pp | 99.40% (664/668); -0.30 pp |
| 9h: 6b bottle + 7a labels; always merge unchanged scores | 58.83% (393/668); +14.82 pp | 97.60% (652/668); +1.05 pp | 99.70% (666/668); +0.00 pp |

### my-failed-2: Extra query controls and complement

| Named condition | R@1 | R@5 | R@10 |
| --- | --- | --- | --- |
| 1-baseline: Original baseline | 44.01% (294/668); +0.00 pp | 96.56% (645/668); +0.00 pp | 99.70% (666/668); +0.00 pp |
| catalogue-cardinal: Catalogue 0/90/180/270-degree vectors only | 44.31% (296/668); +0.30 pp | 94.31% (630/668); -2.25 pp | 99.10% (662/668); -0.60 pp |
| catalogue-zero: Catalogue 0-degree vectors only | 45.36% (303/668); +1.35 pp | 94.16% (629/668); -2.40 pp | 98.65% (659/668); -1.05 pp |
| crop-only: Tight crop without rotation | 44.16% (295/668); +0.15 pp | 96.56% (645/668); +0.00 pp | 99.70% (666/668); +0.00 pp |
| mean-cardinal5: Mean of original and cardinal-guard query embeddings | 45.06% (301/668); +1.05 pp | 96.56% (645/668); +0.00 pp | 99.85% (667/668); +0.15 pp |
| mean-iou: Mean of original and unrestricted-rotation query embeddings | 45.51% (304/668); +1.50 pp | 97.01% (648/668); +0.45 pp | 100.00% (668/668); +0.30 pp |

### my complement: Extra query controls and complement

| Named condition | R@1 | R@5 | R@10 |
| --- | --- | --- | --- |
| complement-baseline: Baseline on the rest of my | 99.26% (2290/2307) | 99.87% (2304/2307) | 100.00% (2307/2307) |
| complement-iou: Unrestricted rotation on the rest of my | 98.40% (2270/2307) | 99.87% (2304/2307) | 99.96% (2306/2307) |
| complement-mean-iou: Mean of original and unrestricted rotation on the rest of my | 98.87% (2281/2307) | 99.87% (2304/2307) | 100.00% (2307/2307) |

### my-failed-2: Initial six axial comparisons

| Named condition | R@1 | R@5 | R@10 |
| --- | --- | --- | --- |
| original-axial-only · baseline | 45.36% (303/668); +1.35 pp | 94.16% (629/668); -2.40 pp | 98.65% (659/668); -1.05 pp |
| original-axial-only · axial | 52.10% (348/668); +8.08 pp | 95.81% (640/668); -0.75 pp | 98.95% (661/668); -0.75 pp |
| original-rot5-plus-axial · baseline | 44.01% (294/668); +0.00 pp | 96.56% (645/668); +0.00 pp | 99.70% (666/668); +0.00 pp |
| original-rot5-plus-axial · axial | 51.20% (342/668); +7.19 pp | 97.01% (648/668); +0.45 pp | 99.70% (666/668); +0.00 pp |
| iou-axial-only · baseline | 46.11% (308/668); +2.10 pp | 95.51% (638/668); -1.05 pp | 99.25% (663/668); -0.45 pp |
| iou-axial-only · axial | 52.69% (352/668); +8.68 pp | 95.81% (640/668); -0.75 pp | 99.25% (663/668); -0.45 pp |
| iou-rot5-plus-axial · baseline | 45.96% (307/668); +1.95 pp | 96.71% (646/668); +0.15 pp | 99.70% (666/668); +0.00 pp |
| iou-rot5-plus-axial · axial | 51.65% (345/668); +7.63 pp | 96.71% (646/668); +0.15 pp | 99.70% (666/668); +0.00 pp |
| mean-iou-axial-only · baseline | 45.81% (306/668); +1.80 pp | 95.21% (636/668); -1.35 pp | 98.95% (661/668); -0.75 pp |
| mean-iou-axial-only · axial | 52.25% (349/668); +8.23 pp | 96.11% (642/668); -0.45 pp | 99.25% (663/668); -0.45 pp |
| mean-iou-rot5-plus-axial · baseline | 45.51% (304/668); +1.50 pp | 97.01% (648/668); +0.45 pp | 100.00% (668/668); +0.30 pp |
| mean-iou-rot5-plus-axial · axial | 51.80% (346/668); +7.78 pp | 97.16% (649/668); +0.60 pp | 100.00% (668/668); +0.30 pp |

### my: Initial six axial comparisons

| Named condition | R@1 | R@5 | R@10 |
| --- | --- | --- | --- |
| original-axial-only · baseline | 85.39% (2536/2970); -1.55 pp | 98.48% (2925/2970); -0.71 pp | 99.70% (2961/2970); -0.24 pp |
| original-axial-only · axial | 87.14% (2588/2970); +0.20 pp | 98.92% (2938/2970); -0.27 pp | 99.76% (2963/2970); -0.17 pp |
| original-rot5-plus-axial · baseline | 86.94% (2582/2970); +0.00 pp | 99.19% (2946/2970); +0.00 pp | 99.93% (2968/2970); +0.00 pp |
| original-rot5-plus-axial · axial | 87.61% (2602/2970); +0.67 pp | 99.33% (2950/2970); +0.13 pp | 99.93% (2968/2970); +0.00 pp |
| iou-axial-only · baseline | 85.25% (2532/2970); -1.68 pp | 98.89% (2937/2970); -0.30 pp | 99.76% (2963/2970); -0.17 pp |
| iou-axial-only · axial | 87.10% (2587/2970); +0.17 pp | 99.09% (2943/2970); -0.10 pp | 99.87% (2966/2970); -0.07 pp |
| iou-rot5-plus-axial · baseline | 86.70% (2575/2970); -0.24 pp | 99.23% (2947/2970); +0.03 pp | 99.90% (2967/2970); -0.03 pp |
| iou-rot5-plus-axial · axial | 87.41% (2596/2970); +0.47 pp | 99.23% (2947/2970); +0.03 pp | 99.93% (2968/2970); +0.00 pp |
| mean-iou-axial-only · baseline | 85.49% (2539/2970); -1.45 pp | 98.75% (2933/2970); -0.44 pp | 99.70% (2961/2970); -0.24 pp |
| mean-iou-axial-only · axial | 87.10% (2587/2970); +0.17 pp | 99.12% (2944/2970); -0.07 pp | 99.83% (2965/2970); -0.10 pp |
| mean-iou-rot5-plus-axial · baseline | 86.97% (2583/2970); +0.03 pp | 99.29% (2949/2970); +0.10 pp | 100.00% (2970/2970); +0.07 pp |
| mean-iou-rot5-plus-axial · axial | 87.58% (2601/2970); +0.64 pp | 99.36% (2951/2970); +0.17 pp | 100.00% (2970/2970); +0.07 pp |

## 10. Controlled pooling and query results

### Pooling in isolation

Fix p512/p512, original query geometry, rot5 references, no axial views, max wine score, and no label-space fusion.
Change only the same-side pooling profile.
The table uses the completed extension controls.
The three percentages in each cell are R@1 / R@5 / R@10.

| Pooling profile | my-failed-2 R@1 / R@5 / R@10 | my R@1 / R@5 / R@10 |
| --- | --- | --- |
| `u` | 44.01% / 96.56% / 99.70% | 86.94% / 99.19% / 99.93% |
| `g0.5-bg010-l1-legacy` | 52.10% / 96.56% / 99.10% | 87.14% / 99.19% / 99.80% |
| `g0.5-bg010-l1-exact` | 51.95% / 96.56% / 98.95% | 87.14% / 99.19% / 99.76% |
| `g0.5-bg010-l2-legacy` | 54.94% / 97.90% / 99.70% | 87.68% / 99.53% / 99.93% |
| `g0.5-bg010-l2-exact` | 55.39% / 97.90% / 99.70% | 87.81% / 99.53% / 99.93% |
| `g1-bg010-l1-legacy` | 52.69% / 96.71% / 99.25% | 87.27% / 99.29% / 99.83% |
| `g1-bg010-l1-exact` | 52.99% / 96.71% / 99.25% | 87.34% / 99.29% / 99.83% |
| `g1-bg010-l1.25-legacy` | 53.14% / 97.16% / 99.55% | 87.47% / 99.36% / 99.90% |
| `g1-bg010-l1.25-exact` | 53.14% / 97.16% / 99.25% | 87.44% / 99.36% / 99.83% |
| `g1-bg010-l1.5-legacy` | 54.49% / 98.05% / 99.55% | 87.74% / 99.60% / 99.90% |
| `g1-bg010-l1.5-exact` | 54.34% / 98.05% / 99.55% | 87.68% / 99.60% / 99.90% |
| `g1-bg010-l2-legacy` | 55.69% / 97.90% / 99.70% | 87.85% / 99.56% / 99.93% |
| `g1-bg010-l2-exact` | 55.99% / 97.90% / 99.70% | 87.95% / 99.56% / 99.93% |
| `g1-bg010-l3-legacy` | 57.19% / 97.75% / 99.85% | 88.05% / 99.53% / 99.97% |
| `g1-bg010-l3-exact` | 57.19% / 97.75% / 99.85% | 88.11% / 99.53% / 99.97% |
| `g2-bg010-l1-legacy` | 53.74% / 97.16% / 99.55% | 87.37% / 99.43% / 99.90% |
| `g2-bg010-l1-exact` | 53.29% / 97.16% / 99.55% | 87.27% / 99.43% / 99.90% |
| `g2-bg010-l2-legacy` | 55.99% / 98.05% / 99.70% | 87.95% / 99.60% / 99.93% |
| `g2-bg010-l2-exact` | 55.69% / 97.90% / 99.70% | 87.95% / 99.56% / 99.93% |
| `g0.5-bg000-l1-legacy` | 51.65% / 96.11% / 99.40% | 86.87% / 99.09% / 99.87% |
| `g0.5-bg000-l1-exact` | 51.20% / 96.11% / 99.40% | 86.77% / 99.09% / 99.87% |
| `g0.5-bg000-l2-legacy` | 55.69% / 97.60% / 99.85% | 87.85% / 99.43% / 99.97% |
| `g0.5-bg000-l2-exact` | 55.69% / 97.60% / 99.85% | 87.81% / 99.43% / 99.97% |
| `g1-bg000-l1-legacy` | 52.25% / 96.86% / 99.40% | 86.70% / 99.29% / 99.87% |
| `g1-bg000-l1-exact` | 52.10% / 96.71% / 99.40% | 86.73% / 99.26% / 99.87% |
| `g1-bg000-l1.25-legacy` | 53.59% / 97.31% / 99.40% | 87.21% / 99.43% / 99.87% |
| `g1-bg000-l1.25-exact` | 53.59% / 97.31% / 99.40% | 87.14% / 99.43% / 99.87% |
| `g1-bg000-l1.5-legacy` | 53.74% / 97.46% / 99.25% | 87.27% / 99.43% / 99.83% |
| `g1-bg000-l1.5-exact` | 53.74% / 97.31% / 99.25% | 87.21% / 99.39% / 99.83% |
| `g1-bg000-l2-legacy` | 55.39% / 97.90% / 99.70% | 87.64% / 99.53% / 99.93% |
| `g1-bg000-l2-exact` | 55.99% / 97.90% / 99.70% | 87.68% / 99.53% / 99.93% |
| `g1-bg000-l3-legacy` | 56.59% / 97.46% / 99.85% | 87.71% / 99.49% / 99.97% |
| `g1-bg000-l3-exact` | 56.44% / 97.46% / 99.85% | 87.81% / 99.49% / 99.97% |
| `g2-bg000-l1-legacy` | 54.64% / 96.71% / 99.40% | 87.34% / 99.29% / 99.87% |
| `g2-bg000-l1-exact` | 54.64% / 96.71% / 99.40% | 87.27% / 99.29% / 99.87% |
| `g2-bg000-l2-legacy` | 56.89% / 97.60% / 99.70% | 87.81% / 99.49% / 99.93% |
| `g2-bg000-l2-exact` | 57.19% / 97.60% / 99.70% | 87.95% / 99.49% / 99.93% |
| `6c` | 53.59% / 97.01% / 99.85% | 87.61% / 99.23% / 99.93% |
| `6d` | 52.99% / 97.31% / 100.00% | 87.17% / 99.33% / 99.97% |

### Query geometry in isolation

Fix standard pooling, p512, rot5 references, no axial views, and no fusion.

| Query code | my-failed-2 R@1 / R@5 / R@10 | my R@1 / R@5 / R@10 |
| --- | --- | --- |
| original | 44.01% / 96.56% / 99.70% | 86.94% / 99.19% / 99.93% |
| iou | 45.96% / 96.71% / 99.70% | 86.70% / 99.23% / 99.90% |
| min5 | 45.36% / 96.56% / 99.70% | 86.94% / 99.19% / 99.93% |
| card5 | 45.36% / 96.56% / 99.70% | 87.00% / 99.19% / 99.93% |
| crop | 44.16% / 96.56% / 99.70% | 86.97% / 99.19% / 99.93% |
| mean-iou | 45.51% / 97.01% / 100.00% | 86.97% / 99.29% / 100.00% |
| mean-card5 | 45.06% / 96.56% / 99.85% | 87.10% / 99.19% / 99.97% |

## 11. Overall top-five leaderboards

Rank all 353,188 unique completed retrieval variants on each testset.
The table recipe codes link to exact parameters in Section 14.
`reference/query` budgets and margins are in that order.
The score cells include the baseline change in pp.
The same five recipes can appear under more than one objective.
These are ranked configurations, not five disjoint algorithm families.

| Objective | Descending tie order before ascending variant ID |
| --- | --- |
| Top-1 | top1, top5, top10, mrr |
| Top-5 | top5, top10, top1, mrr |
| Top-10 | top10, top5, top1, mrr |

### my-failed-2: Top-1

| Rank | Exact recipe | Approach | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- |
| 1 | [R001](#r001) | 1024/1024; pool 6b → 6b; min5; zero; axial; bottle only | 67.37% (450/668); +23.35 pp | 98.35% (657/668); +1.80 pp | 99.85% (667/668); +0.15 pp |
| 2 | [R002](#r002) | 1024/1024; pool 6b → 6b; min5; cardinal; axial; bottle only | 67.37% (450/668); +23.35 pp | 98.35% (657/668); +1.80 pp | 99.85% (667/668); +0.15 pp |
| 3 | [R003](#r003) | 1024/1024; pool 6b → 6b; card5; zero; axial; bottle only | 67.22% (449/668); +23.20 pp | 98.50% (658/668); +1.95 pp | 100.00% (668/668); +0.30 pp |
| 4 | [R004](#r004) | 1024/1024; pool 6b → 6b; mean-card5; zero; axial; bottle only | 67.07% (448/668); +23.05 pp | 98.50% (658/668); +1.95 pp | 100.00% (668/668); +0.30 pp |
| 5 | [R005](#r005) | 1024/1024; pool 6b → 6b; card5; cardinal; axial; bottle only | 67.07% (448/668); +23.05 pp | 98.35% (657/668); +1.80 pp | 99.85% (667/668); +0.15 pp |

### my-failed-2: Top-5

| Rank | Exact recipe | Approach | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- |
| 1 | [R006](#r006) | 512/512; pool 5a → 6b; iou; rot5; l-7f-rot5; always-mean75 | 60.48% (404/668); +16.47 pp | 100.00% (668/668); +3.44 pp | 100.00% (668/668); +0.30 pp |
| 2 | [R007](#r007) | 512/512; pool 5b → 6b; mean-iou; rot5; axial; l-7f-rot5; pin-max-010 | 63.02% (421/668); +19.01 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |
| 3 | [R008](#r008) | 512/512; pool 5a → 6b; mean-iou; rot5; l-7f-rot5; always-mean75 | 60.78% (406/668); +16.77 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |
| 4 | [R009](#r009) | 512/512; pool 5a → 6a; mean-iou; rot5; l-7f-rot5; always-mean75 | 60.63% (405/668); +16.62 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |
| 5 | [R010](#r010) | 512/512; pool 5b → 6b; mean-iou; rot5; l-7f-rot5; always-mean75 | 60.18% (402/668); +16.17 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |

### my-failed-2: Top-10

| Rank | Exact recipe | Approach | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- |
| 1 | [R006](#r006) | 512/512; pool 5a → 6b; iou; rot5; l-7f-rot5; always-mean75 | 60.48% (404/668); +16.47 pp | 100.00% (668/668); +3.44 pp | 100.00% (668/668); +0.30 pp |
| 2 | [R007](#r007) | 512/512; pool 5b → 6b; mean-iou; rot5; axial; l-7f-rot5; pin-max-010 | 63.02% (421/668); +19.01 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |
| 3 | [R008](#r008) | 512/512; pool 5a → 6b; mean-iou; rot5; l-7f-rot5; always-mean75 | 60.78% (406/668); +16.77 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |
| 4 | [R009](#r009) | 512/512; pool 5a → 6a; mean-iou; rot5; l-7f-rot5; always-mean75 | 60.63% (405/668); +16.62 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |
| 5 | [R010](#r010) | 512/512; pool 5b → 6b; mean-iou; rot5; l-7f-rot5; always-mean75 | 60.18% (402/668); +16.17 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |

### my: Top-1

| Rank | Exact recipe | Approach | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- |
| 1 | [R011](#r011) | 512/512; pool 6a → 6a; mean-card5; rot5; axial; top2-mean; l-7f-rot5; always-mean75 | 90.77% (2696/2970); +3.84 pp | 99.83% (2965/2970); +0.64 pp | 100.00% (2970/2970); +0.07 pp |
| 2 | [R012](#r012) | 512/512; pool 6a → 6a; mean-iou; rot5; axial; top2-mean; l-7f-rot5; always-mean75 | 90.77% (2696/2970); +3.84 pp | 99.80% (2964/2970); +0.61 pp | 100.00% (2970/2970); +0.07 pp |
| 3 | [R013](#r013) | 512/512; pool 6a → 6a; iou; rot5; axial; top2-mean; l-7f-rot5; always-mean75 | 90.74% (2695/2970); +3.80 pp | 99.80% (2964/2970); +0.61 pp | 100.00% (2970/2970); +0.07 pp |
| 4 | [R014](#r014) | 512/512; pool 6a → 6a; crop; zero; axial; top3-mean; l-7f-rot5; always-mean75 | 90.74% (2695/2970); +3.80 pp | 99.73% (2962/2970); +0.54 pp | 99.90% (2967/2970); -0.03 pp |
| 5 | [R015](#r015) | 512/512; pool 6a → 6a; original; zero; axial; top3-mean; l-7f-rot5; always-mean75 | 90.74% (2695/2970); +3.80 pp | 99.73% (2962/2970); +0.54 pp | 99.90% (2967/2970); -0.03 pp |

### my: Top-5

| Rank | Exact recipe | Approach | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- |
| 1 | [R006](#r006) | 512/512; pool 5a → 6b; iou; rot5; l-7f-rot5; always-mean75 | 89.36% (2654/2970); +2.42 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| 2 | [R016](#r016) | 512/512; pool 6b → 6b; card5; rot5; margins 0.02/0.05; l-7f-rot5; always-mean75 | 89.33% (2653/2970); +2.39 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| 3 | [R017](#r017) | 512/512; pool 6b → 6b; min5; rot5; margins 0.02/0.05; l-7f-rot5; always-mean75 | 89.26% (2651/2970); +2.32 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| 4 | [R009](#r009) | 512/512; pool 5a → 6a; mean-iou; rot5; l-7f-rot5; always-mean75 | 89.53% (2659/2970); +2.59 pp | 99.90% (2967/2970); +0.71 pp | 100.00% (2970/2970); +0.07 pp |
| 5 | [R008](#r008) | 512/512; pool 5a → 6b; mean-iou; rot5; l-7f-rot5; always-mean75 | 89.46% (2657/2970); +2.53 pp | 99.90% (2967/2970); +0.71 pp | 100.00% (2970/2970); +0.07 pp |

### my: Top-10

| Rank | Exact recipe | Approach | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- |
| 1 | [R006](#r006) | 512/512; pool 5a → 6b; iou; rot5; l-7f-rot5; always-mean75 | 89.36% (2654/2970); +2.42 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| 2 | [R016](#r016) | 512/512; pool 6b → 6b; card5; rot5; margins 0.02/0.05; l-7f-rot5; always-mean75 | 89.33% (2653/2970); +2.39 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| 3 | [R017](#r017) | 512/512; pool 6b → 6b; min5; rot5; margins 0.02/0.05; l-7f-rot5; always-mean75 | 89.26% (2651/2970); +2.32 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| 4 | [R009](#r009) | 512/512; pool 5a → 6a; mean-iou; rot5; l-7f-rot5; always-mean75 | 89.53% (2659/2970); +2.59 pp | 99.90% (2967/2970); +0.71 pp | 100.00% (2970/2970); +0.07 pp |
| 5 | [R008](#r008) | 512/512; pool 5a → 6b; mean-iou; rot5; l-7f-rot5; always-mean75 | 89.46% (2657/2970); +2.53 pp | 99.90% (2967/2970); +0.71 pp | 100.00% (2970/2970); +0.07 pp |

## 12. Best p512 variants

This section requires both bottle reference_budget=512 and bottle query_budget=512.
The label spaces also use p512.
It includes 296,670 earlier variants and 49,126 additional extension variants.
The total is 345,796 unique p512/p512 configurations per testset.
It excludes all mixed or same-side 256 and 1024 budget configurations.
It does not restrict reference-angle counts, query means, or label-space fusion.
Those operations can change inference work even when the patch budget is fixed.

### my-failed-2: p512 Top-1

| Rank | Exact recipe | Approach | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- |
| 1 | [R018](#r018) | 512/512; pool g1-bg000-l3-exact → g1-bg000-l3-exact; iou; cardinal; axial; l-7f-rot5; always-mean50 | 66.17% (442/668); +22.16 pp | 98.80% (660/668); +2.25 pp | 99.55% (665/668); -0.15 pp |
| 2 | [R019](#r019) | 512/512; pool g1-bg000-l3-legacy → g1-bg000-l3-legacy; iou; cardinal; axial; l-7f-rot5; always-mean50 | 66.17% (442/668); +22.16 pp | 98.80% (660/668); +2.25 pp | 99.55% (665/668); -0.15 pp |
| 3 | [R020](#r020) | 512/512; pool 6b → 6b; mean-card5; rot5; margins 0.02/0.02; l-7f-rot5; always-mean75 | 66.02% (441/668); +22.01 pp | 98.95% (661/668); +2.40 pp | 100.00% (668/668); +0.30 pp |
| 4 | [R021](#r021) | 512/512; pool g1-bg000-l3-legacy → g1-bg000-l3-legacy; mean-iou; zero; axial; l-7f-rot5; always-mean50 | 66.02% (441/668); +22.01 pp | 98.95% (661/668); +2.40 pp | 99.55% (665/668); -0.15 pp |
| 5 | [R022](#r022) | 512/512; pool g1-bg000-l3-legacy → g1-bg000-l3-legacy; iou; rot5; axial; l-7f-rot5; always-mean75 | 65.87% (440/668); +21.86 pp | 99.25% (663/668); +2.69 pp | 100.00% (668/668); +0.30 pp |

### my-failed-2: p512 Top-5

| Rank | Exact recipe | Approach | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- |
| 1 | [R006](#r006) | 512/512; pool 5a → 6b; iou; rot5; l-7f-rot5; always-mean75 | 60.48% (404/668); +16.47 pp | 100.00% (668/668); +3.44 pp | 100.00% (668/668); +0.30 pp |
| 2 | [R007](#r007) | 512/512; pool 5b → 6b; mean-iou; rot5; axial; l-7f-rot5; pin-max-010 | 63.02% (421/668); +19.01 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |
| 3 | [R008](#r008) | 512/512; pool 5a → 6b; mean-iou; rot5; l-7f-rot5; always-mean75 | 60.78% (406/668); +16.77 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |
| 4 | [R009](#r009) | 512/512; pool 5a → 6a; mean-iou; rot5; l-7f-rot5; always-mean75 | 60.63% (405/668); +16.62 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |
| 5 | [R010](#r010) | 512/512; pool 5b → 6b; mean-iou; rot5; l-7f-rot5; always-mean75 | 60.18% (402/668); +16.17 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |

### my-failed-2: p512 Top-10

| Rank | Exact recipe | Approach | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- |
| 1 | [R006](#r006) | 512/512; pool 5a → 6b; iou; rot5; l-7f-rot5; always-mean75 | 60.48% (404/668); +16.47 pp | 100.00% (668/668); +3.44 pp | 100.00% (668/668); +0.30 pp |
| 2 | [R007](#r007) | 512/512; pool 5b → 6b; mean-iou; rot5; axial; l-7f-rot5; pin-max-010 | 63.02% (421/668); +19.01 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |
| 3 | [R008](#r008) | 512/512; pool 5a → 6b; mean-iou; rot5; l-7f-rot5; always-mean75 | 60.78% (406/668); +16.77 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |
| 4 | [R009](#r009) | 512/512; pool 5a → 6a; mean-iou; rot5; l-7f-rot5; always-mean75 | 60.63% (405/668); +16.62 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |
| 5 | [R010](#r010) | 512/512; pool 5b → 6b; mean-iou; rot5; l-7f-rot5; always-mean75 | 60.18% (402/668); +16.17 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp |

### my: p512 Top-1

| Rank | Exact recipe | Approach | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- |
| 1 | [R011](#r011) | 512/512; pool 6a → 6a; mean-card5; rot5; axial; top2-mean; l-7f-rot5; always-mean75 | 90.77% (2696/2970); +3.84 pp | 99.83% (2965/2970); +0.64 pp | 100.00% (2970/2970); +0.07 pp |
| 2 | [R012](#r012) | 512/512; pool 6a → 6a; mean-iou; rot5; axial; top2-mean; l-7f-rot5; always-mean75 | 90.77% (2696/2970); +3.84 pp | 99.80% (2964/2970); +0.61 pp | 100.00% (2970/2970); +0.07 pp |
| 3 | [R013](#r013) | 512/512; pool 6a → 6a; iou; rot5; axial; top2-mean; l-7f-rot5; always-mean75 | 90.74% (2695/2970); +3.80 pp | 99.80% (2964/2970); +0.61 pp | 100.00% (2970/2970); +0.07 pp |
| 4 | [R014](#r014) | 512/512; pool 6a → 6a; crop; zero; axial; top3-mean; l-7f-rot5; always-mean75 | 90.74% (2695/2970); +3.80 pp | 99.73% (2962/2970); +0.54 pp | 99.90% (2967/2970); -0.03 pp |
| 5 | [R015](#r015) | 512/512; pool 6a → 6a; original; zero; axial; top3-mean; l-7f-rot5; always-mean75 | 90.74% (2695/2970); +3.80 pp | 99.73% (2962/2970); +0.54 pp | 99.90% (2967/2970); -0.03 pp |

### my: p512 Top-5

| Rank | Exact recipe | Approach | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- |
| 1 | [R006](#r006) | 512/512; pool 5a → 6b; iou; rot5; l-7f-rot5; always-mean75 | 89.36% (2654/2970); +2.42 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| 2 | [R016](#r016) | 512/512; pool 6b → 6b; card5; rot5; margins 0.02/0.05; l-7f-rot5; always-mean75 | 89.33% (2653/2970); +2.39 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| 3 | [R017](#r017) | 512/512; pool 6b → 6b; min5; rot5; margins 0.02/0.05; l-7f-rot5; always-mean75 | 89.26% (2651/2970); +2.32 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| 4 | [R009](#r009) | 512/512; pool 5a → 6a; mean-iou; rot5; l-7f-rot5; always-mean75 | 89.53% (2659/2970); +2.59 pp | 99.90% (2967/2970); +0.71 pp | 100.00% (2970/2970); +0.07 pp |
| 5 | [R008](#r008) | 512/512; pool 5a → 6b; mean-iou; rot5; l-7f-rot5; always-mean75 | 89.46% (2657/2970); +2.53 pp | 99.90% (2967/2970); +0.71 pp | 100.00% (2970/2970); +0.07 pp |

### my: p512 Top-10

| Rank | Exact recipe | Approach | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- |
| 1 | [R006](#r006) | 512/512; pool 5a → 6b; iou; rot5; l-7f-rot5; always-mean75 | 89.36% (2654/2970); +2.42 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| 2 | [R016](#r016) | 512/512; pool 6b → 6b; card5; rot5; margins 0.02/0.05; l-7f-rot5; always-mean75 | 89.33% (2653/2970); +2.39 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| 3 | [R017](#r017) | 512/512; pool 6b → 6b; min5; rot5; margins 0.02/0.05; l-7f-rot5; always-mean75 | 89.26% (2651/2970); +2.32 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| 4 | [R009](#r009) | 512/512; pool 5a → 6a; mean-iou; rot5; l-7f-rot5; always-mean75 | 89.53% (2659/2970); +2.59 pp | 99.90% (2967/2970); +0.71 pp | 100.00% (2970/2970); +0.07 pp |
| 5 | [R008](#r008) | 512/512; pool 5a → 6b; mean-iou; rot5; l-7f-rot5; always-mean75 | 89.46% (2657/2970); +2.53 pp | 99.90% (2967/2970); +0.71 pp | 100.00% (2970/2970); +0.07 pp |

### Five p512 choices from the hard-set results

This table gives five distinct operating choices.
It is not another Top-1 ranking.
The first two p512 Top-1 rows above differ only in exact versus legacy coverage.
Their reported recall counts and MRR are equal on the hard testset.
Keep their parameter identities separate.

Each operating choice below is evaluated unchanged on both testsets.
The recipe is not selected separately for the second testset.

| Goal | Exact recipe | my-failed-2 R@1 / R@5 / R@10 | my R@1 / R@5 / R@10 |
| --- | --- | --- | --- |
| Highest hard-set R@1 | [R018](#r018) | 66.17% / 98.80% / 99.55% | 90.20% / 99.49% / 99.87% |
| High hard-set R@1 with perfect R@10 | [R020](#r020) | 66.02% / 98.95% / 100.00% | 89.93% / 99.80% / 100.00% |
| Higher hard-set R@5 among the strong R@1 choices | [R022](#r022) | 65.87% / 99.25% / 100.00% | 90.51% / 99.76% / 100.00% |
| Best hard-set bottle-only R@1 | [R023](#r023) | 64.37% / 98.80% / 100.00% | 88.82% / 99.66% / 100.00% |
| Highest hard-set R@5 | [R006](#r006) | 60.48% / 100.00% / 100.00% | 89.36% / 99.93% / 100.00% |

The high-R@1/perfect-R@10 choice uses 6b pooling on both sides.
It uses a 0.02 crop margin on each edge of reference and query crops.
It uses `mean-card5` query vectors, rot5 references, no axial union, and 75/25 bottle/label fusion with `l-7f-rot5`.

The bottle-only choice uses 6b pooling, 0.05 margins on both sides, IoU query rotation, rot5 references, and max wine scoring.
It uses no separate label-space retrieval.
It still needs a label mask for the label-weight term in custom bottle pooling.

No Android end-to-end latency is measured for these choices.
The SO400M results do not establish the same accuracy for SigLIP2 Base.

## 13. Extension-family and patch-budget results

### Best observed configuration in each extension family

These rows use recipe membership in the exact enumeration.
A recipe can belong to more than one family.
Family counts and winners therefore overlap.
Each row names one configuration selected for the stated objective.
Its other recall values belong to that same configuration.
Do not treat the selected maxima as an isolated causal effect of one factor.

### my-failed-2: extension family winners

| Family | Selection objective | Member variants | Exact recipe | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- | --- |
| E1 Independent reference and query pooling | Top-1 | 22638 | [R024](#r024) | 65.42% (437/668); +21.41 pp | 98.35% (657/668); +1.80 pp | 99.40% (664/668); -0.30 pp |
| E1 Independent reference and query pooling | Top-5 | 22638 | [R006](#r006) | 60.48% (404/668); +16.47 pp | 100.00% (668/668); +3.44 pp | 100.00% (668/668); +0.30 pp |
| E1 Independent reference and query pooling | Top-10 | 22638 | [R006](#r006) | 60.48% (404/668); +16.47 pp | 100.00% (668/668); +3.44 pp | 100.00% (668/668); +0.30 pp |
| E2 Nonlinear foreground weights | Top-1 | 3696 | [R025](#r025) | 65.27% (436/668); +21.26 pp | 98.65% (659/668); +2.10 pp | 99.55% (665/668); -0.15 pp |
| E2 Nonlinear foreground weights | Top-5 | 3696 | [R026](#r026) | 63.02% (421/668); +19.01 pp | 99.40% (664/668); +2.84 pp | 100.00% (668/668); +0.30 pp |
| E2 Nonlinear foreground weights | Top-10 | 3696 | [R026](#r026) | 63.02% (421/668); +19.01 pp | 99.40% (664/668); +2.84 pp | 100.00% (668/668); +0.30 pp |
| E3 Label boost | Top-1 | 6006 | [R019](#r019) | 66.17% (442/668); +22.16 pp | 98.80% (660/668); +2.25 pp | 99.55% (665/668); -0.15 pp |
| E3 Label boost | Top-5 | 6006 | [R027](#r027) | 63.62% (425/668); +19.61 pp | 99.40% (664/668); +2.84 pp | 100.00% (668/668); +0.30 pp |
| E3 Label boost | Top-10 | 6006 | [R027](#r027) | 63.62% (425/668); +19.61 pp | 99.40% (664/668); +2.84 pp | 100.00% (668/668); +0.30 pp |
| E4 Crop margins and exact NaFlex coverage | Top-1 | 15708 | [R018](#r018) | 66.17% (442/668); +22.16 pp | 98.80% (660/668); +2.25 pp | 99.55% (665/668); -0.15 pp |
| E4 Crop margins and exact NaFlex coverage | Top-5 | 15708 | [R016](#r016) | 64.52% (431/668); +20.51 pp | 99.70% (666/668); +3.14 pp | 100.00% (668/668); +0.30 pp |
| E4 Crop margins and exact NaFlex coverage | Top-10 | 15708 | [R016](#r016) | 64.52% (431/668); +20.51 pp | 99.70% (666/668); +3.14 pp | 100.00% (668/668); +0.30 pp |
| E5 Axial and cardinal Cartesian views | Top-1 | 1078 | [R028](#r028) | 65.27% (436/668); +21.26 pp | 98.65% (659/668); +2.10 pp | 99.40% (664/668); -0.30 pp |
| E5 Axial and cardinal Cartesian views | Top-5 | 1078 | [R029](#r029) | 64.52% (431/668); +20.51 pp | 99.25% (663/668); +2.69 pp | 100.00% (668/668); +0.30 pp |
| E5 Axial and cardinal Cartesian views | Top-10 | 1078 | [R029](#r029) | 64.52% (431/668); +20.51 pp | 99.25% (663/668); +2.69 pp | 100.00% (668/668); +0.30 pp |
| E6 NaFlex patch budgets | Top-1 | 8316 | [R001](#r001) | 67.37% (450/668); +23.35 pp | 98.35% (657/668); +1.80 pp | 99.85% (667/668); +0.15 pp |
| E6 NaFlex patch budgets | Top-5 | 8316 | [R030](#r030) | 63.47% (424/668); +19.46 pp | 99.40% (664/668); +2.84 pp | 100.00% (668/668); +0.30 pp |
| E6 NaFlex patch budgets | Top-10 | 8316 | [R030](#r030) | 63.47% (424/668); +19.46 pp | 99.40% (664/668); +2.84 pp | 100.00% (668/668); +0.30 pp |
| E7 Reference score aggregation | Top-1 | 6468 | [R031](#r031) | 65.57% (438/668); +21.56 pp | 99.25% (663/668); +2.69 pp | 99.85% (667/668); +0.15 pp |
| E7 Reference score aggregation | Top-5 | 6468 | [R011](#r011) | 65.12% (435/668); +21.11 pp | 99.40% (664/668); +2.84 pp | 100.00% (668/668); +0.30 pp |
| E7 Reference score aggregation | Top-10 | 6468 | [R011](#r011) | 65.12% (435/668); +21.11 pp | 99.40% (664/668); +2.84 pp | 100.00% (668/668); +0.30 pp |

### my: extension family winners

| Family | Selection objective | Member variants | Exact recipe | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- | --- |
| E1 Independent reference and query pooling | Top-1 | 22638 | [R032](#r032) | 90.57% (2690/2970); +3.64 pp | 99.76% (2963/2970); +0.57 pp | 100.00% (2970/2970); +0.07 pp |
| E1 Independent reference and query pooling | Top-5 | 22638 | [R006](#r006) | 89.36% (2654/2970); +2.42 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| E1 Independent reference and query pooling | Top-10 | 22638 | [R006](#r006) | 89.36% (2654/2970); +2.42 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| E2 Nonlinear foreground weights | Top-1 | 3696 | [R033](#r033) | 90.40% (2685/2970); +3.47 pp | 99.80% (2964/2970); +0.61 pp | 100.00% (2970/2970); +0.07 pp |
| E2 Nonlinear foreground weights | Top-5 | 3696 | [R034](#r034) | 89.60% (2661/2970); +2.66 pp | 99.87% (2966/2970); +0.67 pp | 100.00% (2970/2970); +0.07 pp |
| E2 Nonlinear foreground weights | Top-10 | 3696 | [R034](#r034) | 89.60% (2661/2970); +2.66 pp | 99.87% (2966/2970); +0.67 pp | 100.00% (2970/2970); +0.07 pp |
| E3 Label boost | Top-1 | 6006 | [R035](#r035) | 90.57% (2690/2970); +3.64 pp | 99.73% (2962/2970); +0.54 pp | 100.00% (2970/2970); +0.07 pp |
| E3 Label boost | Top-5 | 6006 | [R036](#r036) | 89.63% (2662/2970); +2.69 pp | 99.87% (2966/2970); +0.67 pp | 100.00% (2970/2970); +0.07 pp |
| E3 Label boost | Top-10 | 6006 | [R036](#r036) | 89.63% (2662/2970); +2.69 pp | 99.87% (2966/2970); +0.67 pp | 100.00% (2970/2970); +0.07 pp |
| E4 Crop margins and exact NaFlex coverage | Top-1 | 15708 | [R037](#r037) | 90.67% (2693/2970); +3.74 pp | 99.73% (2962/2970); +0.54 pp | 100.00% (2970/2970); +0.07 pp |
| E4 Crop margins and exact NaFlex coverage | Top-5 | 15708 | [R016](#r016) | 89.33% (2653/2970); +2.39 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| E4 Crop margins and exact NaFlex coverage | Top-10 | 15708 | [R016](#r016) | 89.33% (2653/2970); +2.39 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp |
| E5 Axial and cardinal Cartesian views | Top-1 | 1078 | [R038](#r038) | 90.40% (2685/2970); +3.47 pp | 99.76% (2963/2970); +0.57 pp | 100.00% (2970/2970); +0.07 pp |
| E5 Axial and cardinal Cartesian views | Top-5 | 1078 | [R039](#r039) | 89.53% (2659/2970); +2.59 pp | 99.83% (2965/2970); +0.64 pp | 100.00% (2970/2970); +0.07 pp |
| E5 Axial and cardinal Cartesian views | Top-10 | 1078 | [R039](#r039) | 89.53% (2659/2970); +2.59 pp | 99.83% (2965/2970); +0.64 pp | 100.00% (2970/2970); +0.07 pp |
| E6 NaFlex patch budgets | Top-1 | 8316 | [R040](#r040) | 90.51% (2688/2970); +3.57 pp | 99.73% (2962/2970); +0.54 pp | 99.97% (2969/2970); +0.03 pp |
| E6 NaFlex patch budgets | Top-5 | 8316 | [R036](#r036) | 89.63% (2662/2970); +2.69 pp | 99.87% (2966/2970); +0.67 pp | 100.00% (2970/2970); +0.07 pp |
| E6 NaFlex patch budgets | Top-10 | 8316 | [R036](#r036) | 89.63% (2662/2970); +2.69 pp | 99.87% (2966/2970); +0.67 pp | 100.00% (2970/2970); +0.07 pp |
| E7 Reference score aggregation | Top-1 | 6468 | [R011](#r011) | 90.77% (2696/2970); +3.84 pp | 99.83% (2965/2970); +0.64 pp | 100.00% (2970/2970); +0.07 pp |
| E7 Reference score aggregation | Top-5 | 6468 | [R011](#r011) | 90.77% (2696/2970); +3.84 pp | 99.83% (2965/2970); +0.64 pp | 100.00% (2970/2970); +0.07 pp |
| E7 Reference score aggregation | Top-10 | 6468 | [R011](#r011) | 90.77% (2696/2970); +3.84 pp | 99.83% (2965/2970); +0.64 pp | 100.00% (2970/2970); +0.07 pp |

### Best Top-1 configuration at each reference/query budget pair

The p512/p512 row searches the complete p512 universe.
Every other pair searches the declared budget family.
Those pairs have the narrower pool grid {u,6b}, no new margin sweep, and the ten fixed fusion anchors.
The table is not a fully crossed architecture-resolution experiment.

### my-failed-2: patch budget pairs

| Reference budget | Query budget | Exact recipe | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- |
| 256 | 256 | [R041](#r041) | 64.37% (430/668); +20.36 pp | 97.90% (654/668); +1.35 pp | 99.25% (663/668); -0.45 pp |
| 256 | 512 | [R042](#r042) | 64.22% (429/668); +20.21 pp | 98.35% (657/668); +1.80 pp | 99.40% (664/668); -0.30 pp |
| 256 | 1024 | [R043](#r043) | 64.82% (433/668); +20.81 pp | 97.75% (653/668); +1.20 pp | 98.80% (660/668); -0.90 pp |
| 512 | 256 | [R044](#r044) | 64.37% (430/668); +20.36 pp | 98.05% (655/668); +1.50 pp | 99.25% (663/668); -0.45 pp |
| 512 | 512 | [R018](#r018) | 66.17% (442/668); +22.16 pp | 98.80% (660/668); +2.25 pp | 99.55% (665/668); -0.15 pp |
| 512 | 1024 | [R045](#r045) | 66.62% (445/668); +22.60 pp | 98.35% (657/668); +1.80 pp | 99.55% (665/668); -0.15 pp |
| 1024 | 256 | [R046](#r046) | 64.82% (433/668); +20.81 pp | 97.46% (651/668); +0.90 pp | 99.85% (667/668); +0.15 pp |
| 1024 | 512 | [R047](#r047) | 65.42% (437/668); +21.41 pp | 98.20% (656/668); +1.65 pp | 100.00% (668/668); +0.30 pp |
| 1024 | 1024 | [R001](#r001) | 67.37% (450/668); +23.35 pp | 98.35% (657/668); +1.80 pp | 99.85% (667/668); +0.15 pp |

### my: patch budget pairs

| Reference budget | Query budget | Exact recipe | R@1 | R@5 | R@10 |
| --- | --- | --- | --- | --- | --- |
| 256 | 256 | [R048](#r048) | 89.53% (2659/2970); +2.59 pp | 99.36% (2951/2970); +0.17 pp | 99.70% (2961/2970); -0.24 pp |
| 256 | 512 | [R049](#r049) | 89.49% (2658/2970); +2.56 pp | 99.36% (2951/2970); +0.17 pp | 99.66% (2960/2970); -0.27 pp |
| 256 | 1024 | [R050](#r050) | 89.26% (2651/2970); +2.32 pp | 99.33% (2950/2970); +0.13 pp | 99.60% (2958/2970); -0.34 pp |
| 512 | 256 | [R051](#r051) | 89.93% (2671/2970); +3.00 pp | 99.60% (2958/2970); +0.40 pp | 99.87% (2966/2970); -0.07 pp |
| 512 | 512 | [R011](#r011) | 90.77% (2696/2970); +3.84 pp | 99.83% (2965/2970); +0.64 pp | 100.00% (2970/2970); +0.07 pp |
| 512 | 1024 | [R052](#r052) | 90.51% (2688/2970); +3.57 pp | 99.70% (2961/2970); +0.51 pp | 99.97% (2969/2970); +0.03 pp |
| 1024 | 256 | [R046](#r046) | 89.66% (2663/2970); +2.73 pp | 99.36% (2951/2970); +0.17 pp | 99.97% (2969/2970); +0.03 pp |
| 1024 | 512 | [R053](#r053) | 90.13% (2677/2970); +3.20 pp | 99.70% (2961/2970); +0.51 pp | 100.00% (2970/2970); +0.07 pp |
| 1024 | 1024 | [R040](#r040) | 90.51% (2688/2970); +3.57 pp | 99.73% (2962/2970); +0.54 pp | 99.97% (2969/2970); +0.03 pp |

## 14. Exact result recipes

The recipe records below define every `Rxxx` code used in the result tables.
They include the full bottle recipe, resolved pool parameters, label geometry, and fusion parameters.
The JSON values are machine-readable.
`null` means disabled, absent, or preserved input as defined in the relevant section.

All gallery angle sets, masks, interpolation rules, encoder settings, and scoring rules are defined above.
The model revision and frozen testset hashes remain fixed.
For a matrix recipe, the canonical parameter record is reconstructed from the frozen manifest.
For an extension recipe, the record is read directly from the metric database.

### R001

```json
{
  "variant_id": "x-0adf5caa8872f7bf0e7f849e",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "zero",
    "query_budget": 1024,
    "query_geometry": "min5",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 1024,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": null,
  "fusion": null
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 67.37% (450/668); +23.35 pp | 98.35% (657/668); +1.80 pp | 99.85% (667/668); +0.15 pp | 0.81124180 | 0 | 0 | 0 |
| my | 90.40% (2685/2970); +3.47 pp | 99.60% (2958/2970); +0.40 pp | 99.93% (2968/2970); +0.00 pp | 0.94556197 | 65 | 351 | 9 |

### R002

```json
{
  "variant_id": "x-1bd9491e9a8fe38abfb9b21f",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "cardinal",
    "query_budget": 1024,
    "query_geometry": "min5",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 1024,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": null,
  "fusion": null
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 67.37% (450/668); +23.35 pp | 98.35% (657/668); +1.80 pp | 99.85% (667/668); +0.15 pp | 0.81099230 | 0 | 0 | 0 |
| my | 90.40% (2685/2970); +3.47 pp | 99.66% (2960/2970); +0.47 pp | 99.97% (2969/2970); +0.03 pp | 0.94579766 | 65 | 348 | 9 |

### R003

```json
{
  "variant_id": "x-50c2caea953a3977652b1e92",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "zero",
    "query_budget": 1024,
    "query_geometry": "card5",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 1024,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": null,
  "fusion": null
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 67.22% (449/668); +23.20 pp | 98.50% (658/668); +1.95 pp | 100.00% (668/668); +0.30 pp | 0.81086755 | 0 | 0 | 0 |
| my | 90.40% (2685/2970); +3.47 pp | 99.63% (2959/2970); +0.44 pp | 99.97% (2969/2970); +0.03 pp | 0.94570226 | 64 | 351 | 9 |

### R004

```json
{
  "variant_id": "x-39e3dd40e021db88bf36ef96",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "zero",
    "query_budget": 1024,
    "query_geometry": "mean-card5",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 1024,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": null,
  "fusion": null
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 67.07% (448/668); +23.05 pp | 98.50% (658/668); +1.95 pp | 100.00% (668/668); +0.30 pp | 0.80991945 | 0 | 0 | 0 |
| my | 90.44% (2686/2970); +3.50 pp | 99.63% (2959/2970); +0.44 pp | 99.97% (2969/2970); +0.03 pp | 0.94582572 | 64 | 349 | 9 |

### R005

```json
{
  "variant_id": "x-9766a24b393087baf01336de",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "cardinal",
    "query_budget": 1024,
    "query_geometry": "card5",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 1024,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": null,
  "fusion": null
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 67.07% (448/668); +23.05 pp | 98.35% (657/668); +1.80 pp | 99.85% (667/668); +0.15 pp | 0.80924579 | 0 | 0 | 0 |
| my | 90.34% (2683/2970); +3.40 pp | 99.66% (2960/2970); +0.47 pp | 99.97% (2969/2970); +0.03 pp | 0.94540484 | 65 | 348 | 9 |

### R006

```json
{
  "variant_id": "x-0f8d10c1d088bfdbee097a81__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": false,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg010-l1-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 1.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 60.48% (404/668); +16.47 pp | 100.00% (668/668); +3.44 pp | 100.00% (668/668); +0.30 pp | 0.77357784 | 0 | 0 | 0 |
| my | 89.36% (2654/2970); +2.42 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp | 0.93955240 | 67 | 345 | 9 |

### R007

```json
{
  "variant_id": "x-44f4599f9cd969369b40378b__l-7f-rot5__pin-max-010",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l1-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 1.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "pin-max-010",
    "merge": "max",
    "bottle_weight": null,
    "mode": "pin",
    "bottle_threshold": 0.01,
    "label_threshold": 0.01
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 63.02% (421/668); +19.01 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp | 0.79256487 | 0 | 0 | 0 |
| my | 89.60% (2661/2970); +2.66 pp | 99.90% (2967/2970); +0.71 pp | 99.97% (2969/2970); +0.03 pp | 0.94218855 | 61 | 350 | 9 |

### R008

```json
{
  "variant_id": "x-a786defb0b1f3090a087e748__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": false,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg010-l1-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 1.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 60.78% (406/668); +16.77 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp | 0.77607285 | 0 | 0 | 0 |
| my | 89.46% (2657/2970); +2.53 pp | 99.90% (2967/2970); +0.71 pp | 100.00% (2970/2970); +0.07 pp | 0.94026508 | 66 | 346 | 9 |

### R009

```json
{
  "variant_id": "x-afe0d486fbeebfe1cbde460e__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": false,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g1-bg010-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg010-l1-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 1.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 60.63% (405/668); +16.62 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp | 0.77627246 | 0 | 0 | 0 |
| my | 89.53% (2659/2970); +2.59 pp | 99.90% (2967/2970); +0.71 pp | 100.00% (2970/2970); +0.07 pp | 0.94084309 | 67 | 345 | 9 |

### R010

```json
{
  "variant_id": "x-6dc1f0e19a440ef51a91c024__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": false,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l1-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 1.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 60.18% (402/668); +16.17 pp | 99.85% (667/668); +3.29 pp | 100.00% (668/668); +0.30 pp | 0.77475050 | 0 | 0 | 0 |
| my | 89.09% (2646/2970); +2.15 pp | 99.83% (2965/2970); +0.64 pp | 99.97% (2969/2970); +0.03 pp | 0.93864518 | 66 | 345 | 9 |

### R011

```json
{
  "variant_id": "x-adaace72b66523656e44f3f3__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "top2-mean",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "mean-card5",
    "query_margin": null,
    "query_pool": "g1-bg010-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg010-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 65.12% (435/668); +21.11 pp | 99.40% (664/668); +2.84 pp | 100.00% (668/668); +0.30 pp | 0.80310985 | 0 | 0 | 0 |
| my | 90.77% (2696/2970); +3.84 pp | 99.83% (2965/2970); +0.64 pp | 100.00% (2970/2970); +0.07 pp | 0.94844677 | 66 | 343 | 9 |

### R012

```json
{
  "variant_id": "x-dea1ff540b7528ec273a556b__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "top2-mean",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g1-bg010-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg010-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.97% (434/668); +20.96 pp | 99.25% (663/668); +2.69 pp | 100.00% (668/668); +0.30 pp | 0.80256273 | 0 | 0 | 0 |
| my | 90.77% (2696/2970); +3.84 pp | 99.80% (2964/2970); +0.61 pp | 100.00% (2970/2970); +0.07 pp | 0.94848084 | 65 | 344 | 9 |

### R013

```json
{
  "variant_id": "x-9aad7b1ad6a16ae00fb54a78__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "top2-mean",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "iou",
    "query_margin": null,
    "query_pool": "g1-bg010-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg010-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 65.27% (436/668); +21.26 pp | 99.25% (663/668); +2.69 pp | 100.00% (668/668); +0.30 pp | 0.80387083 | 0 | 0 | 0 |
| my | 90.74% (2695/2970); +3.80 pp | 99.80% (2964/2970); +0.61 pp | 100.00% (2970/2970); +0.07 pp | 0.94815777 | 66 | 346 | 9 |

### R014

```json
{
  "variant_id": "x-5413e26b22a393fd785d1e18__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "top3-mean",
    "axial_union": true,
    "gallery": "zero",
    "query_budget": 512,
    "query_geometry": "crop",
    "query_margin": null,
    "query_pool": "g1-bg010-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg010-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 65.27% (436/668); +21.26 pp | 98.95% (661/668); +2.40 pp | 99.55% (665/668); -0.15 pp | 0.80275877 | 0 | 0 | 0 |
| my | 90.74% (2695/2970); +3.80 pp | 99.73% (2962/2970); +0.54 pp | 99.90% (2967/2970); -0.03 pp | 0.94805916 | 67 | 341 | 9 |

### R015

```json
{
  "variant_id": "x-f32d537c3f490dff4015947a__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "top3-mean",
    "axial_union": true,
    "gallery": "zero",
    "query_budget": 512,
    "query_geometry": "original",
    "query_margin": null,
    "query_pool": "g1-bg010-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg010-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 65.27% (436/668); +21.26 pp | 98.95% (661/668); +2.40 pp | 99.55% (665/668); -0.15 pp | 0.80275877 | 0 | 0 | 0 |
| my | 90.74% (2695/2970); +3.80 pp | 99.73% (2962/2970); +0.54 pp | 99.90% (2967/2970); -0.03 pp | 0.94805916 | 67 | 341 | 9 |

### R016

```json
{
  "variant_id": "x-a612b6cebe85c6373cfe61e7__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": false,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "card5",
    "query_margin": 0.05,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": 0.02,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.52% (431/668); +20.51 pp | 99.70% (666/668); +3.14 pp | 100.00% (668/668); +0.30 pp | 0.79582086 | 0 | 0 | 0 |
| my | 89.33% (2653/2970); +2.39 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp | 0.93986011 | 59 | 340 | 9 |

### R017

```json
{
  "variant_id": "x-2b6421b71e268e8fdc424665__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": false,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "min5",
    "query_margin": 0.05,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": 0.02,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.37% (430/668); +20.36 pp | 99.70% (666/668); +3.14 pp | 100.00% (668/668); +0.30 pp | 0.79514721 | 0 | 0 | 0 |
| my | 89.26% (2651/2970); +2.32 pp | 99.93% (2968/2970); +0.74 pp | 100.00% (2970/2970); +0.07 pp | 0.93954024 | 59 | 340 | 9 |

### R018

```json
{
  "variant_id": "x-1979dff348a23e64b79390ad__l-7f-rot5__always-mean50",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "cardinal",
    "query_budget": 512,
    "query_geometry": "iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l3-exact",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l3-exact"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 3.0,
    "coverage": "exact"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 3.0,
    "coverage": "exact"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean50",
    "merge": "mean",
    "bottle_weight": 0.5,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 66.17% (442/668); +22.16 pp | 98.80% (660/668); +2.25 pp | 99.55% (665/668); -0.15 pp | 0.80677811 | 0 | 0 | 0 |
| my | 90.20% (2679/2970); +3.27 pp | 99.49% (2955/2970); +0.30 pp | 99.87% (2966/2970); -0.07 pp | 0.94436668 | 61 | 346 | 9 |

### R019

```json
{
  "variant_id": "x-6be4dd06372a8247147e56b4__l-7f-rot5__always-mean50",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "cardinal",
    "query_budget": 512,
    "query_geometry": "iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l3-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l3-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 3.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 3.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean50",
    "merge": "mean",
    "bottle_weight": 0.5,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 66.17% (442/668); +22.16 pp | 98.80% (660/668); +2.25 pp | 99.55% (665/668); -0.15 pp | 0.80677811 | 0 | 0 | 0 |
| my | 90.20% (2679/2970); +3.27 pp | 99.49% (2955/2970); +0.30 pp | 99.87% (2966/2970); -0.07 pp | 0.94436668 | 61 | 345 | 9 |

### R020

```json
{
  "variant_id": "x-786f3cd931b448300caaf33f__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": false,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "mean-card5",
    "query_margin": 0.02,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": 0.02,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 66.02% (441/668); +22.01 pp | 98.95% (661/668); +2.40 pp | 100.00% (668/668); +0.30 pp | 0.80217422 | 0 | 0 | 0 |
| my | 89.93% (2671/2970); +3.00 pp | 99.80% (2964/2970); +0.61 pp | 100.00% (2970/2970); +0.07 pp | 0.94282107 | 60 | 344 | 9 |

### R021

```json
{
  "variant_id": "x-709924964c66b2c559cd4b05__l-7f-rot5__always-mean50",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "zero",
    "query_budget": 512,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l3-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l3-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 3.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 3.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean50",
    "merge": "mean",
    "bottle_weight": 0.5,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 66.02% (441/668); +22.01 pp | 98.95% (661/668); +2.40 pp | 99.55% (665/668); -0.15 pp | 0.80538090 | 0 | 0 | 0 |
| my | 90.24% (2680/2970); +3.30 pp | 99.53% (2956/2970); +0.34 pp | 99.87% (2966/2970); -0.07 pp | 0.94450136 | 61 | 346 | 9 |

### R022

```json
{
  "variant_id": "x-7412e7a759975fcfea926904__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l3-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l3-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 3.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 3.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 65.87% (440/668); +21.86 pp | 99.25% (663/668); +2.69 pp | 100.00% (668/668); +0.30 pp | 0.80703949 | 0 | 0 | 0 |
| my | 90.51% (2688/2970); +3.57 pp | 99.76% (2963/2970); +0.57 pp | 100.00% (2970/2970); +0.07 pp | 0.94683341 | 66 | 343 | 9 |

### R023

```json
{
  "variant_id": "x-b5a9fac2bd8baff9a706530c",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": false,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "iou",
    "query_margin": 0.05,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": 0.05,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": null,
  "fusion": null
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.37% (430/668); +20.36 pp | 98.80% (660/668); +2.25 pp | 100.00% (668/668); +0.30 pp | 0.79341852 | 0 | 0 | 0 |
| my | 88.82% (2638/2970); +1.89 pp | 99.66% (2960/2970); +0.47 pp | 100.00% (2970/2970); +0.07 pp | 0.93660895 | 63 | 334 | 9 |

### R024

```json
{
  "variant_id": "x-7835aba54b510839c61a12ad__l-7g-cardinal__always-mean50",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "cardinal",
    "query_budget": 512,
    "query_geometry": "iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7g-cardinal",
    "geometry": "7g",
    "angles": "cardinal",
    "reference_rotation": true,
    "bottle_rotation": true,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean50",
    "merge": "mean",
    "bottle_weight": 0.5,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 65.42% (437/668); +21.41 pp | 98.35% (657/668); +1.80 pp | 99.40% (664/668); -0.30 pp | 0.79964357 | 0 | 0 | 0 |
| my | 89.36% (2654/2970); +2.42 pp | 99.19% (2946/2970); +0.00 pp | 99.73% (2962/2970); -0.20 pp | 0.93797606 | 64 | 350 | 9 |

### R025

```json
{
  "variant_id": "x-9261900d1bbea72ec3436bec__l-7f-rot5__always-mean50",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "iou",
    "query_margin": null,
    "query_pool": "g2-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g2-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 2.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 2.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean50",
    "merge": "mean",
    "bottle_weight": 0.5,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 65.27% (436/668); +21.26 pp | 98.65% (659/668); +2.10 pp | 99.55% (665/668); -0.15 pp | 0.80150948 | 0 | 0 | 0 |
| my | 89.97% (2672/2970); +3.03 pp | 99.46% (2954/2970); +0.27 pp | 99.90% (2967/2970); -0.03 pp | 0.94311247 | 63 | 348 | 9 |

### R026

```json
{
  "variant_id": "x-95604c59b1baac70899c25a7__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "card5",
    "query_margin": null,
    "query_pool": "g2-bg010-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g2-bg010-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.1,
    "gamma": 2.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.1,
    "gamma": 2.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 63.02% (421/668); +19.01 pp | 99.40% (664/668); +2.84 pp | 100.00% (668/668); +0.30 pp | 0.79345595 | 0 | 0 | 0 |
| my | 90.37% (2684/2970); +3.43 pp | 99.83% (2965/2970); +0.64 pp | 100.00% (2970/2970); +0.07 pp | 0.94666827 | 65 | 344 | 9 |

### R027

```json
{
  "variant_id": "x-713a7de71bf11a7562c20a9b__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "mean-card5",
    "query_margin": null,
    "query_pool": "g1-bg010-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg010-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 63.62% (425/668); +19.61 pp | 99.40% (664/668); +2.84 pp | 100.00% (668/668); +0.30 pp | 0.79532542 | 0 | 0 | 0 |
| my | 90.37% (2684/2970); +3.43 pp | 99.83% (2965/2970); +0.64 pp | 100.00% (2970/2970); +0.07 pp | 0.94635923 | 63 | 346 | 9 |

### R028

```json
{
  "variant_id": "x-a6dd4f17c33040eb89552aeb__l-7g-cardinal__always-mean50",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "cartesian",
    "query_budget": 512,
    "query_geometry": "iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7g-cardinal",
    "geometry": "7g",
    "angles": "cardinal",
    "reference_rotation": true,
    "bottle_rotation": true,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean50",
    "merge": "mean",
    "bottle_weight": 0.5,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 65.27% (436/668); +21.26 pp | 98.65% (659/668); +2.10 pp | 99.40% (664/668); -0.30 pp | 0.79946892 | 0 | 0 | 0 |
| my | 89.26% (2651/2970); +2.32 pp | 99.26% (2948/2970); +0.07 pp | 99.73% (2962/2970); -0.20 pp | 0.93762813 | 61 | 346 | 9 |

### R029

```json
{
  "variant_id": "x-5b697262a5045bcb007fb129__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5-plus-cartesian",
    "query_budget": 512,
    "query_geometry": "iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.52% (431/668); +20.51 pp | 99.25% (663/668); +2.69 pp | 100.00% (668/668); +0.30 pp | 0.80110137 | 0 | 0 | 0 |
| my | 90.30% (2682/2970); +3.37 pp | 99.80% (2964/2970); +0.61 pp | 100.00% (2970/2970); +0.07 pp | 0.94616001 | 64 | 349 | 9 |

### R030

```json
{
  "variant_id": "x-2ae84b60e89291159a0ec81b__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "mean-card5",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 63.47% (424/668); +19.46 pp | 99.40% (664/668); +2.84 pp | 100.00% (668/668); +0.30 pp | 0.79435415 | 0 | 0 | 0 |
| my | 90.20% (2679/2970); +3.27 pp | 99.83% (2965/2970); +0.64 pp | 100.00% (2970/2970); +0.07 pp | 0.94554032 | 65 | 342 | 9 |

### R031

```json
{
  "variant_id": "x-90ada0100559c6de5f514f57__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "top3-mean",
    "axial_union": true,
    "gallery": "zero",
    "query_budget": 512,
    "query_geometry": "card5",
    "query_margin": null,
    "query_pool": "g1-bg010-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg010-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 65.57% (438/668); +21.56 pp | 99.25% (663/668); +2.69 pp | 99.85% (667/668); +0.15 pp | 0.80757414 | 0 | 0 | 0 |
| my | 90.71% (2694/2970); +3.77 pp | 99.80% (2964/2970); +0.61 pp | 99.97% (2969/2970); +0.03 pp | 0.94858105 | 67 | 341 | 9 |

### R032

```json
{
  "variant_id": "x-46ade619d89ec90f4122de2e__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g1-bg010-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.52% (431/668); +20.51 pp | 99.10% (662/668); +2.54 pp | 100.00% (668/668); +0.30 pp | 0.80034395 | 0 | 0 | 0 |
| my | 90.57% (2690/2970); +3.64 pp | 99.76% (2963/2970); +0.57 pp | 100.00% (2970/2970); +0.07 pp | 0.94756894 | 66 | 342 | 9 |

### R033

```json
{
  "variant_id": "x-6d58e6a2956a1c61b654eed1__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "iou",
    "query_margin": null,
    "query_pool": "g2-bg010-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g2-bg010-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.1,
    "gamma": 2.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.1,
    "gamma": 2.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 63.77% (426/668); +19.76 pp | 99.25% (663/668); +2.69 pp | 100.00% (668/668); +0.30 pp | 0.79685985 | 0 | 0 | 0 |
| my | 90.40% (2685/2970); +3.47 pp | 99.80% (2964/2970); +0.61 pp | 100.00% (2970/2970); +0.07 pp | 0.94680536 | 66 | 346 | 9 |

### R034

```json
{
  "variant_id": "x-a6ea799145c3da81e39bb683__l-7f-rot5__pin-max-010",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g0.5-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g0.5-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 0.5,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 0.5,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "pin-max-010",
    "merge": "max",
    "bottle_weight": null,
    "mode": "pin",
    "bottle_threshold": 0.01,
    "label_threshold": 0.01
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 62.57% (418/668); +18.56 pp | 99.40% (664/668); +2.84 pp | 100.00% (668/668); +0.30 pp | 0.79054748 | 0 | 0 | 0 |
| my | 89.60% (2661/2970); +2.66 pp | 99.87% (2966/2970); +0.67 pp | 100.00% (2970/2970); +0.07 pp | 0.94248116 | 62 | 348 | 9 |

### R035

```json
{
  "variant_id": "x-3d61e97bacedce8a6590b2bd__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "cardinal",
    "query_budget": 512,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g1-bg010-l3-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg010-l3-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 3.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 3.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.67% (432/668); +20.66 pp | 99.10% (662/668); +2.54 pp | 100.00% (668/668); +0.30 pp | 0.80127780 | 0 | 0 | 0 |
| my | 90.57% (2690/2970); +3.64 pp | 99.73% (2962/2970); +0.54 pp | 100.00% (2970/2970); +0.07 pp | 0.94734127 | 65 | 343 | 9 |

### R036

```json
{
  "variant_id": "x-0329f6f54b2eae37fa519966__l-7f-rot5__pin-max-010",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "pin-max-010",
    "merge": "max",
    "bottle_weight": null,
    "mode": "pin",
    "bottle_threshold": 0.01,
    "label_threshold": 0.01
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 62.72% (419/668); +18.71 pp | 99.40% (664/668); +2.84 pp | 100.00% (668/668); +0.30 pp | 0.79084688 | 0 | 0 | 0 |
| my | 89.63% (2662/2970); +2.69 pp | 99.87% (2966/2970); +0.67 pp | 100.00% (2970/2970); +0.07 pp | 0.94253167 | 62 | 347 | 9 |

### R037

```json
{
  "variant_id": "x-6fb91d5324d81bf3eeca17e6__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "mean-card5",
    "query_margin": null,
    "query_pool": "g1-bg010-l3-exact",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg010-l3-exact"
  },
  "reference_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 3.0,
    "coverage": "exact"
  },
  "query_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 3.0,
    "coverage": "exact"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 65.57% (438/668); +21.56 pp | 99.25% (663/668); +2.69 pp | 100.00% (668/668); +0.30 pp | 0.80455042 | 0 | 0 | 0 |
| my | 90.67% (2693/2970); +3.74 pp | 99.73% (2962/2970); +0.54 pp | 100.00% (2970/2970); +0.07 pp | 0.94753621 | 65 | 341 | 9 |

### R038

```json
{
  "variant_id": "x-e4c73c35c9eebabe82b9e6c2__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5-plus-cartesian",
    "query_budget": 512,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.52% (431/668); +20.51 pp | 99.10% (662/668); +2.54 pp | 100.00% (668/668); +0.30 pp | 0.80000356 | 0 | 0 | 0 |
| my | 90.40% (2685/2970); +3.47 pp | 99.76% (2963/2970); +0.57 pp | 100.00% (2970/2970); +0.07 pp | 0.94667068 | 62 | 347 | 9 |

### R039

```json
{
  "variant_id": "x-c5af9332f9f4a32f5852fc96__l-7f-rot5__pin-max-010",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "cartesian",
    "query_budget": 512,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g1-bg010-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg010-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.1,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "pin-max-010",
    "merge": "max",
    "bottle_weight": null,
    "mode": "pin",
    "bottle_threshold": 0.01,
    "label_threshold": 0.01
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 61.38% (410/668); +17.37 pp | 99.25% (663/668); +2.69 pp | 100.00% (668/668); +0.30 pp | 0.78530796 | 0 | 0 | 0 |
| my | 89.53% (2659/2970); +2.59 pp | 99.83% (2965/2970); +0.64 pp | 100.00% (2970/2970); +0.07 pp | 0.94228475 | 62 | 348 | 9 |

### R040

```json
{
  "variant_id": "x-50c2caea953a3977652b1e92__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "zero",
    "query_budget": 1024,
    "query_geometry": "card5",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 1024,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 65.72% (439/668); +21.71 pp | 98.95% (661/668); +2.40 pp | 100.00% (668/668); +0.30 pp | 0.80426647 | 0 | 0 | 0 |
| my | 90.51% (2688/2970); +3.57 pp | 99.73% (2962/2970); +0.54 pp | 99.97% (2969/2970); +0.03 pp | 0.94656886 | 72 | 346 | 9 |

### R041

```json
{
  "variant_id": "x-7ab7f73391b9202381ce0678__l-7f-rot5__always-mean50",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 256,
    "query_geometry": "card5",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 256,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean50",
    "merge": "mean",
    "bottle_weight": 0.5,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.37% (430/668); +20.36 pp | 97.90% (654/668); +1.35 pp | 99.25% (663/668); -0.45 pp | 0.78995046 | 0 | 0 | 0 |
| my | 89.26% (2651/2970); +2.32 pp | 99.33% (2950/2970); +0.13 pp | 99.83% (2965/2970); -0.10 pp | 0.93739779 | 59 | 334 | 9 |

### R042

```json
{
  "variant_id": "x-3298e608ff684422ab56600b__l-7f-rot5__always-mean50",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "zero",
    "query_budget": 512,
    "query_geometry": "mean-card5",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 256,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean50",
    "merge": "mean",
    "bottle_weight": 0.5,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.22% (429/668); +20.21 pp | 98.35% (657/668); +1.80 pp | 99.40% (664/668); -0.30 pp | 0.79241695 | 0 | 0 | 0 |
| my | 89.12% (2647/2970); +2.19 pp | 99.43% (2953/2970); +0.24 pp | 99.87% (2966/2970); -0.07 pp | 0.93802028 | 60 | 341 | 9 |

### R043

```json
{
  "variant_id": "x-94229589b211b939696ca933__l-7f-rot5__gate-mean50-010",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "zero",
    "query_budget": 1024,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 256,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "gate-mean50-010",
    "merge": "mean",
    "bottle_weight": 0.5,
    "mode": "gate",
    "bottle_threshold": 0.01,
    "label_threshold": 0.01
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.82% (433/668); +20.81 pp | 97.75% (653/668); +1.20 pp | 98.80% (660/668); -0.90 pp | 0.79405118 | 0 | 0 | 0 |
| my | 89.26% (2651/2970); +2.32 pp | 99.29% (2949/2970); +0.10 pp | 99.63% (2959/2970); -0.30 pp | 0.93787491 | 65 | 333 | 9 |

### R044

```json
{
  "variant_id": "x-c2c45dd86322e8b417d3ed7d__l-7g-cardinal__always-mean50",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "zero",
    "query_budget": 256,
    "query_geometry": "iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7g-cardinal",
    "geometry": "7g",
    "angles": "cardinal",
    "reference_rotation": true,
    "bottle_rotation": true,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean50",
    "merge": "mean",
    "bottle_weight": 0.5,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.37% (430/668); +20.36 pp | 98.05% (655/668); +1.50 pp | 99.25% (663/668); -0.45 pp | 0.79346664 | 0 | 0 | 0 |
| my | 88.82% (2638/2970); +1.89 pp | 99.09% (2943/2970); -0.10 pp | 99.73% (2962/2970); -0.20 pp | 0.93466611 | 59 | 345 | 9 |

### R045

```json
{
  "variant_id": "x-2268aee79098a89773f10ad3__l-7g-cardinal__always-mean50",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "zero",
    "query_budget": 1024,
    "query_geometry": "iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7g-cardinal",
    "geometry": "7g",
    "angles": "cardinal",
    "reference_rotation": true,
    "bottle_rotation": true,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean50",
    "merge": "mean",
    "bottle_weight": 0.5,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 66.62% (445/668); +22.60 pp | 98.35% (657/668); +1.80 pp | 99.55% (665/668); -0.15 pp | 0.80537378 | 0 | 0 | 0 |
| my | 89.49% (2658/2970); +2.56 pp | 99.19% (2946/2970); +0.00 pp | 99.80% (2964/2970); -0.13 pp | 0.93856916 | 64 | 346 | 9 |

### R046

```json
{
  "variant_id": "x-3b9a6099d04e4e868ab667db__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 256,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 1024,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.82% (433/668); +20.81 pp | 97.46% (651/668); +0.90 pp | 99.85% (667/668); +0.15 pp | 0.79416227 | 0 | 0 | 0 |
| my | 89.66% (2663/2970); +2.73 pp | 99.36% (2951/2970); +0.17 pp | 99.97% (2969/2970); +0.03 pp | 0.94091804 | 62 | 342 | 9 |

### R047

```json
{
  "variant_id": "x-3d52a14873e6dfc5612b5e22__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 1024,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 65.42% (437/668); +21.41 pp | 98.20% (656/668); +1.65 pp | 100.00% (668/668); +0.30 pp | 0.80119404 | 0 | 0 | 0 |
| my | 90.10% (2676/2970); +3.16 pp | 99.60% (2958/2970); +0.40 pp | 100.00% (2970/2970); +0.07 pp | 0.94415504 | 71 | 344 | 9 |

### R048

```json
{
  "variant_id": "x-7ab7f73391b9202381ce0678__l-7f-rot5__gate-mean50-010",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 256,
    "query_geometry": "card5",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 256,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "gate-mean50-010",
    "merge": "mean",
    "bottle_weight": 0.5,
    "mode": "gate",
    "bottle_threshold": 0.01,
    "label_threshold": 0.01
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 63.92% (427/668); +19.91 pp | 97.75% (653/668); +1.20 pp | 98.80% (660/668); -0.90 pp | 0.78907186 | 0 | 0 | 0 |
| my | 89.53% (2659/2970); +2.59 pp | 99.36% (2951/2970); +0.17 pp | 99.70% (2961/2970); -0.24 pp | 0.93899351 | 59 | 337 | 9 |

### R049

```json
{
  "variant_id": "x-3298e608ff684422ab56600b__l-7f-rot5__gate-mean50-010",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "zero",
    "query_budget": 512,
    "query_geometry": "mean-card5",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 256,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "gate-mean50-010",
    "merge": "mean",
    "bottle_weight": 0.5,
    "mode": "gate",
    "bottle_threshold": 0.01,
    "label_threshold": 0.01
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.07% (428/668); +20.06 pp | 97.60% (652/668); +1.05 pp | 98.65% (659/668); -1.05 pp | 0.78838751 | 0 | 0 | 0 |
| my | 89.49% (2658/2970); +2.56 pp | 99.36% (2951/2970); +0.17 pp | 99.66% (2960/2970); -0.27 pp | 0.93889250 | 60 | 337 | 9 |

### R050

```json
{
  "variant_id": "x-c20697ec6ebb1cacd02d8519__l-7f-rot5__gate-mean50-010",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 1024,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 256,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "gate-mean50-010",
    "merge": "mean",
    "bottle_weight": 0.5,
    "mode": "gate",
    "bottle_threshold": 0.01,
    "label_threshold": 0.01
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.37% (430/668); +20.36 pp | 97.90% (654/668); +1.35 pp | 98.65% (659/668); -1.05 pp | 0.79154192 | 0 | 0 | 0 |
| my | 89.26% (2651/2970); +2.32 pp | 99.33% (2950/2970); +0.13 pp | 99.60% (2958/2970); -0.34 pp | 0.93778753 | 64 | 334 | 9 |

### R051

```json
{
  "variant_id": "x-664d50b24e60b318dbf9529b__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "cardinal",
    "query_budget": 256,
    "query_geometry": "iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 63.17% (422/668); +19.16 pp | 98.05% (655/668); +1.50 pp | 99.40% (664/668); -0.30 pp | 0.79055282 | 0 | 0 | 0 |
| my | 89.93% (2671/2970); +3.00 pp | 99.60% (2958/2970); +0.40 pp | 99.87% (2966/2970); -0.07 pp | 0.94359347 | 62 | 344 | 9 |

### R052

```json
{
  "variant_id": "x-199377417ca05573f7c0fde9__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "cardinal",
    "query_budget": 1024,
    "query_geometry": "mean-card5",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 512,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 65.27% (436/668); +21.26 pp | 98.80% (660/668); +2.25 pp | 100.00% (668/668); +0.30 pp | 0.80190393 | 0 | 0 | 0 |
| my | 90.51% (2688/2970); +3.57 pp | 99.70% (2961/2970); +0.51 pp | 99.97% (2969/2970); +0.03 pp | 0.94648883 | 66 | 345 | 9 |

### R053

```json
{
  "variant_id": "x-e820ad121196e32c3023d0ed__l-7f-rot5__always-mean75",
  "source": "seven-family-extension",
  "bottle": {
    "aggregation": "max",
    "axial_union": true,
    "gallery": "rot5",
    "query_budget": 512,
    "query_geometry": "mean-iou",
    "query_margin": null,
    "query_pool": "g1-bg000-l2-legacy",
    "reference_budget": 1024,
    "reference_margin": null,
    "reference_pool": "g1-bg000-l2-legacy"
  },
  "reference_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "query_pool_parameters": {
    "background": 0.0,
    "gamma": 1.0,
    "boost": 2.0,
    "coverage": "legacy"
  },
  "label": {
    "id": "l-7f-rot5",
    "geometry": "7f",
    "angles": "rot5",
    "reference_rotation": true,
    "bottle_rotation": false,
    "label_rotation": false,
    "reference_budget": 512,
    "query_budget": 512,
    "pooling": "standard learned attention"
  },
  "fusion": {
    "id": "always-mean75",
    "merge": "mean",
    "bottle_weight": 0.75,
    "mode": "always",
    "bottle_threshold": null,
    "label_threshold": null
  }
}
```

| Testset | R@1 | R@5 | R@10 | MRR@10 | negative_false1 | negative_false10 | no_match_false1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| my-failed-2 | 64.82% (433/668); +20.81 pp | 98.65% (659/668); +2.10 pp | 100.00% (668/668); +0.30 pp | 0.79540562 | 0 | 0 | 0 |
| my | 90.13% (2677/2970); +3.20 pp | 99.70% (2961/2970); +0.51 pp | 100.00% (2970/2970); +0.07 pp | 0.94375100 | 71 | 341 | 9 |

## 15. Separate RTX4090 replay

The separate RTX4090 summary was exported at 2026-10-20T19:57:05+03:00.
Its last successful server snapshot is 2026-10-20T11:43:20+03:00.
The collector export time is not proof of new GPU progress.
The separate replay is incomplete.
It has its own rebuilt bottle vectors and bottle baseline.
GX10 and RTX4090 pilot differences did not pass the declared mixed-hardware admission policy.
The owner selected separate hardware campaigns.
The fixed label-score arrays are shared between the campaigns.
The bottle vectors and bottle baselines are hardware-specific.

Do not fill missing RTX4090 rows with GX10 rows.
Do not mark the RTX4090 replay complete because the GX10 recipes are complete.
The main document leaderboards use only GX10 results.

| RTX4090 testset | Observed variants | Target variants | Remaining |
| --- | --- | --- | --- |
| my-failed-2 | 52206 | 59752 | 7546 |
| my | 0 | 59752 | 59752 |

| Separate baseline | R@1 | R@5 | R@10 |
| --- | --- | --- | --- |
| RTX4090 my-failed-2 | 45.21% (302/668) | 96.41% (644/668) | 99.85% (667/668) |

The GX10 completion receipt checked all 7,546 variants that remained unscored on RTX4090 at the handoff snapshot.
Those variants correspond to 686 bottle recipes and their fixed fusion comparisons.
It independently recomputed GX10 R@1, R@5, R@10, and MRR@10 from their saved candidate lists.
All 7,546 rows passed.
No additional GX10 GPU run was required for that receipt.

## 16. Verification and interpretation limits

The final GX10 extension audit passed at 2026-10-20T12:44:34+03:00.
It checked all 119,504 extension metric rows across both testsets.
It checked all saved Top-10 candidate lists.
It independently recomputed case metrics.
It verified 6,468 repeated historical control rows across the two testsets.
It preserved frozen source identities and testset hashes.
It verified all 18 native vector stages.

The original matrix audits passed for 148,347 rows per testset.
The axial addition audits passed for 148,323 rows per testset.

### Native execution parameters

- Model revision: `cc24074f717b612951c2dead130904ab9b65a81e`.
- Native runtime: torch 2.11.0+cu130; transformers 5.3.0.
- Tensor type: BF16.
- p256 and p512 vision batch size: 36.
- p1024 vision batch size: 12.
- Native uniform-head agreement tolerance: 0.00002.
- Batch-equivalence tolerance: 0.00002.
- CUDA allocation cap: 8 GiB.
- Normal operation memory reserve: 20 GiB; workers can require 24 GiB before a batch and 28 GiB before a new model load.

The worker reuses one vision pass for several pooling profiles.
It changes only the pooling prior between those profiles.
It checks the uniform-prior output against the native head output.

The p256 and p1024 stages use the versioned explicit-encoder-mask worker.
The library can omit its mask for a fully occupied input.
That omission caused a batch-equivalence failure in the earlier pilot.
The recovery keeps an explicit encoder mask for these previously unbuilt budgets.
The recovery keeps the original p512 worker and completed p512 vectors unchanged.
The repaired p256 and p1024 controls have zero measured batch-equivalence delta.
The frozen p512 controls also have zero measured delta.
The tolerance was not relaxed.

### Interpretation

- The testsets were used for development and configuration selection.
- The hard-set selection and shared images prevent an independent generalization claim.
- A 100% R@10 value means all accepted assignments in this frozen testset have a hit in Top-10.
- Many recipes tie at 100% R@10. Secondary sort keys determine their order.
- Best-in-family values are selected maxima. They are not paired causal estimates for one factor.
- The p512 winners are SO400M results. No SigLIP2 Base or Android accuracy transfer is measured.
- p768 is absent from the tested budget grid.
- Cached score sweeps do not measure end-to-end segmentation and inference latency.
- Separate hardware scores require separate baselines.
- The finite family grid does not cover the Cartesian product of every proposed factor.
- No new run or model call was required to build this document.

The result tables were generated from read-only database connections.
The document build checks the variant counts, recipe definitions, result denominators, and leaderboard sort order.
The hard-set all-budget leaders match the saved final leaderboard export.
All selected exact recipes resolve to stored definitions.

## 17. Source files

All links in this section are repository-relative.
The committed source snapshots preserve the original file bytes.
The original native input manifest is 50 MB and is not bundled.
Its compact summary records the original checksum, size, and input counts.
The GX10 handoff summary omits the long variant-ID list and records its checksum.
The source SHA-256 column identifies the original source, not a derived summary.
The package manifest records the checksum of every committed package file.

| Source | Committed file | Original source SHA-256 | Form |
| --- | --- | --- | --- |
| Original matrix definitions | [manifest.json](research/retrieval-20261020/sources/campaign/my-matrix-20261017/manifest.json) | `47517d29149b0a689dd13a8e4375cc16be5f17c386367e932cdf993af8c7bc18` | Byte-identical snapshot |
| Original query implementation | [geometry.py](research/retrieval-20261020/sources/campaign/geometry.py) | `cfa5b080a019df94afc06de65df4956e46e54ec580b5af81a163854cdeabf6ee` | Byte-identical snapshot |
| Bottle orientation helper | [bottle_orientation.py](research/retrieval-20261020/sources/workbench/pipeline/bottle_orientation.py) | `8cef3a36a9622ef958163c4b484b618f55600681009865d404385e96beb3006e` | Byte-identical snapshot |
| Frozen image and mask preparation | [prepare.py](research/retrieval-20261020/sources/campaign/prepare.py) | `bb9ff9a57df5193648c0571d01e15b37994c85d0ffd39d1da45dcc6258acccd9` | Byte-identical snapshot |
| Initial label specification | [protocol.json](research/retrieval-20261020/sources/campaign/labels-20261017/protocol.json) | `e990f177c73a162cb2e50c96ef013aafe95c28864a30e6d1cde04f844f4f06ec` | Byte-identical snapshot |
| Label alignment implementation | [support.py](research/retrieval-20261020/sources/campaign/labels-20261017/support.py) | `6a8afff61d49e1141a5e01be19c6572518cf7156e8dd6e9dcce7fead5cc4359d` | Byte-identical snapshot |
| Original fusion specification | [protocol.json](research/retrieval-20261020/sources/campaign/fusion-20261017/protocol.json) | `bf8519f841ff3a0de207119ec69cf067ba8e4bdfa2014fad7e0831df44a1a80a` | Byte-identical snapshot |
| Vectorized fusion and evaluator | [core.py](research/retrieval-20261020/sources/campaign/my-matrix-20261017/core.py) | `8d92493d62561d26f1fd50f92edb5383a05914d72a81381178cafa60edfb91b4` | Byte-identical snapshot |
| Axial matrix specification | [PROTOCOL.md](research/retrieval-20261020/sources/campaign/axial-matrix-20261018/PROTOCOL.md) | `baa02b3b43e6a6bf7829fb15108bc654fc5affcbf9b2f3efbc668c318430a6be` | Byte-identical snapshot |
| Axial renderer calibration | [render.py](research/retrieval-20261020/sources/campaign/axial-20261018/render.py) | `262a5c89bec0b6e33d3bba59651975796e71f48ac7f702a6f4d850e39460c97c` | Byte-identical snapshot |
| Axial cylinder renderer | [rotate_bottle.py](research/retrieval-20261020/sources/campaign/axial-20261018/rotate_bottle.py) | `d29adc5aae5fb1214eba6794db7d6fc8b57a0a8dcbde292be4a59928e11c2170` | Byte-identical snapshot |
| Extension specification | [protocol.json](research/retrieval-20261020/sources/campaign/retrieval-extensions-20261018/protocol.json) | `e822f7a60004ec7c7a3a5276c1fe6e13387945903ef5cf010f31f567afb51427` | Byte-identical snapshot |
| Extension recipe enumeration | [enumeration.json](research/retrieval-20261020/sources/campaign/retrieval-extensions-20261018/enumeration.json) | `35b89907a4da62008b94e4a9a08c6b801bda3d4a7f4c0ce873ccae9c4640521d` | Byte-identical snapshot |
| Frozen native input manifest | [native-inputs.json](research/retrieval-20261020/summaries/input-manifest-summary.json) | `fd7c79ad14e14a5b908795928bfc137dbd7073b1e092ffd0ec48b993df2413a6` | Compact summary; original omitted |
| Extension enumerator | [enumerate.py](research/retrieval-20261020/sources/campaign/retrieval-extensions-20261018/enumerate.py) | `12688af934667866716bbbb815db5eb9a48b7d97ca15c25b6e8f76499c605428` | Byte-identical snapshot |
| Pooling profile definitions | [settings.py](research/retrieval-20261020/sources/campaign/retrieval-extensions-20261018/settings.py) | `d6a0c6ae5c297c8b215efbaa9b6747dfd0aa24d93e6c849043501a366eaf2e19` | Byte-identical snapshot |
| Native pooling, margins, and views | [native_worker.py](research/retrieval-20261020/sources/campaign/retrieval-extensions-20261018/native_worker.py) | `d5d0103ccb2263b7edba3b862612b72edb1201573594db9bdf9d628269b87664` | Byte-identical snapshot |
| Explicit encoder-mask worker | [native_worker_explicit_mask.py](research/retrieval-20261020/sources/campaign/retrieval-extensions-20261018/native_worker_explicit_mask.py) | `4bbc2408db4a13ad42d403dc9a00cef5da71651f054c7f03d5656c3a3fe4c4ec` | Byte-identical snapshot |
| Numerical recovery receipt | [attention-mask-recovery.json](research/retrieval-20261020/sources/campaign/retrieval-extensions-20261018/attention-mask-recovery.json) | `023398083c4cfac0a073a57e16497e2f8169d76b38affd9e7e579e3d09189d51` | Byte-identical snapshot |
| Native scoring implementation | [native_score.py](research/retrieval-20261020/sources/campaign/retrieval-extensions-20261018/native_score.py) | `fdbeeedc190b96140369cdfcffe542393b76fe1fab6e0e186ddd6ed84aa18cf8` | Byte-identical snapshot |
| Wine aggregation implementation | [scoring.py](research/retrieval-20261020/sources/campaign/retrieval-extensions-20261018/scoring.py) | `658f33b9fe901e5c069e4dd736487d54854064b75fd25faba7564d1b0e1f52c7` | Byte-identical snapshot |
| Final extension audit | [complete.json](research/retrieval-20261020/sources/campaign/retrieval-extensions-20261018/complete.json) | `9e53b1e588b9e7ccaa29cb5ad46f8209f772021705058a826ae58f8385ae841c` | Byte-identical snapshot |
| GX10 completion of RTX4090-pending recipes | [coverage.json](research/retrieval-20261020/summaries/gx10-completion-summary.json) | `5309d9c4fd8fe8395c9e42181ad441d52ba6976a8bb12defe03f5409b5bf3474` | Compact summary; original omitted |
| RTX4090 campaign specification | [EXPERIMENT.md](research/retrieval-20261020/sources/campaign/retrieval-extensions-20261018/rtx4090-20261019/EXPERIMENT.md) | `6d2480b4506074daf413a83abc4411325f37724e57313333d5126952d8e21c08` | Byte-identical snapshot |

### Compact benchmark summaries

The compact exports cover every reported result table and every exact result recipe.
They contain 281 metric rows with raw counts, including the named historical controls.
They do not contain the complete 706,376-row result universe.
The full databases, per-image predictions, accepted answers, images, masks, and model weights remain outside this package.
The dataset inventory identifies the full source databases by checksum, size, and row count.

| Evidence | Repository file |
| --- | --- |
| Human-readable leaderboards | [Compact benchmark results](research/retrieval-20261020/summaries/README.md) |
| Counts, baselines, and leaderboard membership | [benchmark-summary.json](research/retrieval-20261020/summaries/benchmark-summary.json) |
| All 53 exact result recipes | [configurations.json](research/retrieval-20261020/summaries/configurations.json) |
| Raw counts for reported configurations and controls | [metrics.csv](research/retrieval-20261020/summaries/metrics.csv) |
| Every report table before this source section | [report-tables.json](research/retrieval-20261020/summaries/report-tables.json) |
| Historical named comparisons | [named-results.json](research/retrieval-20261020/summaries/named-results.json) |
| Unbundled dataset identity and scope | [dataset-inventory.json](research/retrieval-20261020/summaries/dataset-inventory.json) |
| Snapshot and derived-summary provenance | [source-manifest.json](research/retrieval-20261020/provenance/source-manifest.json) |
| Published package checksums | [package-manifest.json](research/retrieval-20261020/package-manifest.json) |

### Offline verification

Run this command from the repository root with Python 3.9 or later.
The checker uses only the Python standard library.
It also works from another working directory when given by absolute script path.
It starts no model, service, SSH connection, or GPU job.

```sh
python3 research/retrieval-20261020/verify.py
```

The checker verifies package hashes and the original source snapshot hashes.
It regenerates all 5,432 bottle recipes and their family memberships.
It checks all 39 pooling profiles against the archived profile factory.
It checks the 53 exact result recipes and their IDs.
It checks compact CSV counts against the report, recall arithmetic, baseline deltas, leaderboard ordering, p512 budgets, and repository links.
This check does not reproduce model predictions or independently establish global optimality without the full source datasets.

### Source export with the private campaign assets

The optional exporter reads existing SQLite databases in read-only mode.
It exports aggregate counts and exact parameter records.
It does not export images, masks, per-image predictions, or accepted answers.
A complete source campaign is required for this command.

```sh
python3 research/retrieval-20261020/tools/export_results.py \
  --campaign-root /path/to/frozen-campaign \
  --report RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md \
  --output /tmp/retrieval-summary-check
```

The archived GPU scripts preserve their historical path and service settings.
They are source evidence for the algorithms.
Full inference needs the original runtime configuration and private benchmark assets.
Use the offline checker to inspect this package without that environment.

End of retrieval-only reference.
