# Base NaFlex p224 custom pooling experiment

Date: 2026-10-20.
Status: ready for implementation. The owner selected both scope decisions.

## Scope

Use `google/siglip2-base-patch16-naflex` at revision
`b53b807d3a2d5e2b3911292f2d69e5341cdc064c`.
Use `max_num_patches=224`, patch size 16, and 768 output dimensions.
Preserve image proportions. Do not interpret p224 as a 224 by 224 image.
Use a separate experiment. Do not change the production p512 default.
Do not interrupt the active SO400M full v3 benchmark on Pixel 8.
Keep re-ranking, barcode, OCR, and VLM inference disabled.

## Candidate

The source report is `http://127.0.0.1:59998/complete-report-20261018/report.html`.
Its pooling legend defines `5a` as fractional whitespace 0.1.
The report measures SO400M and desktop masks. It does not establish Base p224 quality.
Use one bottle mask and one image-encoder pass per query.
Do not add label fusion, label boosting, query rotation, or reference augmentation.

For each valid patch, calculate the bottle coverage `f` in `[0, 1]`.
Use `weight = 0.1 * (1 - f) + f`.
Add `log(weight)` to the original attention-pooling logits before softmax.
Keep the transformer and valid-patch masks unchanged.
Do not infer foreground from RGB whiteness. A white label belongs to the bottle.
Calculate coverage on the actual resized NaFlex grid.
Exclude sequence padding. Padding is not whitespace.
Keep original model weights, LayerNorm, MLP, and final normalization.

This candidate retains some context when a mobile mask is imperfect.
This is an Android-fit hypothesis, not a measured winner.

## Paired conditions

1. Base p224 with standard pooling and the same mobile bottle crop.
2. Base p224 with custom pooling and the same mobile bottle crop.
3. Base p512 with standard pooling and the same mobile bottle crop.
4. Base p512 with custom pooling and the same mobile bottle crop.

The owner added condition 4 on 2026-10-20.
Use the same fractional whitespace 0.1 and bottle 1.0 formula at both patch budgets.
Keep conditions 1 to 3 and their completed reference vectors unchanged.
Preserve the original three-condition pack and source snapshot as v1 evidence.
Replace only the waiting v1 comparison coordinator with a frozen four-condition v2.
Check the p512 graph rewrite before custom reference generation or device inference.

Use the same catalogue wines, original reference cuts, query bytes, masks, and scorer.
Use one unrotated reference per wine in each condition.
Generate a matching reference index for every encoder and pooling profile.
Never reuse p512 or standard-pooling vectors as p224 custom-pooling vectors.
Keep the original built-in catalogue and previous test results unchanged.
Use existing production p512 no-segmentation results only as separately labelled context.
Do not attribute an encoder, catalogue, or segmentation difference to pooling alone.

## Implementation and validation

Reuse the verified complete-graph NaFlex export and runtime.
Do not return to the earlier split export that failed Pixel GPU parity.
Keep the running full-v3 host tools unchanged.
Use a separate Android package and an explicit default-off HTTP switch.
Keep GPU creation, execution, and cleanup on one inference worker.
Preserve model and reference checksums in the experiment manifest.

Check model rewrites and export outputs against native source outputs.
Check that zero log bias reproduces standard pooling.
Check fractional coverage, fully empty patches, white labels, and padding exclusion.
Require cosine at least 0.99999 and maximum component error at most 0.001.
Check GPU/CPU agreement on captured identical inputs before device quality measurements.
Use explicit GPU. Do not silently fall back to CPU during the experiment.

After full v3 ends and its cleanup succeeds, run a 30-image Pixel pilot.
Use frozen evenly spaced distinct query identities, not correctness-selected images.
Measure independent complete-pipeline median, P95, process PSS, heat, and stability.
Freeze these smoothness gates before the first device measurement.
Require client median at most 3 seconds, P95 at most 5 seconds, and maximum at most
10 seconds after one untimed warmup. Include segmentation failures in timing.
Reuse compiled models. Do not reuse query embeddings between independent requests.
Stop on a process change, invalid vector, native abort, or CRITICAL thermal status.
Run all 668 frozen my-failed-2 assignments only for conditions that pass the gates.
Retain every segmentation failure in predictions and in the quality denominator.
Accept every frozen alternative slug. Save per-condition predictions.jsonl files.
Record paired gains and regressions, Top-1/5/10, and declared timing scopes.
Do not claim a new production default before the comparison is complete.
