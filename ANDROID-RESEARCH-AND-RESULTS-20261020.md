# Android retrieval research and results

Date: 2026-10-20.
Scope: saved Pixel 8 experiments and the verified Android 0.3.0 integration.
This document consolidates completed work. Its preparation starts no device or GPU job.

## Research contributions

1. Integrated complete SigLIP2 Base NaFlex graphs with native-aspect-ratio preprocessing on Android.
   The source checkpoint is `google/siglip2-base-patch16-naflex`.
   The Android export and runtime are our integration work, not a newly trained SigLIP2 checkpoint.
   The verified complete graph is different from the earlier experimental split exports.
2. Implemented custom attention pooling from fractional object coverage on the actual patch grid.
   Tested standard and custom pooling at maximum patch counts 224 and 512.
3. Compared full-image and cropped queries with CPU mobile segmentation and GPU DIS.
   Preserved matched reference indexes and checked the standard control before accepting comparisons.
4. Specialized DIS graphs to 768 and 512 pixels without changing learned weights.
   Preserved explicit one-pixel padding, interpolation flags, and internal resize constants.
   Verified identity output for the 1024 specialization before testing smaller graphs.
5. Adapted ten SO400M desktop retrieval recipes to a fully offline Android experiment.
   Replaced desktop SAM3 query masks with mobile bottle and label masks.
   Kept those results separate from the Base model and the desktop reference table.
6. Added numerical gates, full-cohort audits, exact-prefix continuation, and production parity checks.
   Preserved stopped candidates and negative results instead of weakening acceptance thresholds.
7. Promoted a measured complete pipeline into release 0.3.0.
   Kept the previous complete standard pipeline selectable in Settings.

## Measurement contract

`p224` and `p512` mean maximum NaFlex patch counts, not square image resolutions.
The patch size is 16 by 16 pixels. The preprocessor preserves aspect ratio.
DIS 1024, 768, and 512 are segmentation input dimensions in pixels.

The hard-case cohort `my-failed-2` has 668 assignments and 627 distinct image hashes.
Quality includes accepted alternative slugs. Segmentation failures stay in the denominator.
Duplicate assignments remain present. Re-ranking and barcode decoding are disabled.
These development-selected results are not an independent holdout or official jury score.
Do not compare them directly with full `my`, Eval.zip, or desktop SAM3 percentages.

The Base experiments use 768-dimensional vectors and 2,093 catalogue wines.
The SO400M experiment uses 1,152-dimensional vectors and 2,274 catalogue wines.
The encoder, reference index, decoder, segmenter, and query frame define a complete pipeline.
Changing several of these components does not isolate a pooling or segmentation effect.

## 1. Earlier full `my` measurements

These results use 3,409 requests, including 2,970 positive assignments.
They describe standard pooling with the earlier pack. They do not measure the new custom default.

| Historical pipeline | Positive Top-1 / Top-5 / Top-10 | Request median / P95 | Errors |
| --- | --- | --- | ---: |
| Fixed Base/224 with DIS | 33.27 / 56.46 / 64.41% | 1699 / 2156 ms | 5 |
| Complete Base NaFlex p512, full image | 69.09 / 87.10 / 90.03% | 924 / 1479 ms | 0 |
| DIS GPU crop with complete p512 GPU, standard pooling | 72.29 / 88.18 / 90.34% | 1319 / 2343 ms | 5 no-object errors |

The dual-GPU pipeline adds 95 Top-1 hits over full-image p512: +3.20 percentage points.
Its paired gains/losses are 262/167. Its latency and sampled memory are higher.
Both pipelines falsely accept all nine no-match queries.
The catalogue lacks an accepted wine for 170 positive assignments.
The full-image run reaches thermal status `SEVERE`. It is not an all-gates pass.

Sources: [full `my`](android/docs/reports/2026-10-19_pixel8-base-p512-full-my.md),
[full `my` machine results](android/docs/reports/2026-10-19_pixel8-base-p512-full-my.json),
[dual GPU](android/docs/reports/2026-10-19_pixel8-p512-dis-dual-gpu-my.md),
[dual-GPU machine results](android/docs/reports/2026-10-19_pixel8-p512-dis-dual-gpu-my.json).

## 2. Four pooling conditions on `my-failed-2`

All four conditions use the on-device CPU bottle segmenter and a cropped query.
Each condition passes numerical checks and a separate 30-image pilot before the complete run.

| Condition | Top-1 / Top-5 / Top-10 | Median / P95 | Errors |
| --- | --- | --- | ---: |
| p224 standard | 27.84 / 57.78 / 63.92% | 1383 / 1748 ms | 2 |
| p224 custom | 28.44 / 57.78 / 66.17% | 1366 / 2073 ms | 2 |
| p512 standard | 33.83 / 66.32 / 70.51% | 2283 / 3215 ms | 2 |
| p512 custom | 36.98 / 68.86 / 73.95% | 1769 / 2428 ms | 2 |

Custom pooling uses weight `0.1 * (1 - foreground) + foreground` for each valid patch.
It adds the logarithm of this weight to the attention logit. Padding remains masked.
The mask identifies foreground. RGB whiteness does not identify foreground.
White label pixels can therefore retain foreground weight.

Custom pooling adds four p224 Top-1 hits, with paired gains/losses 30/26.
It adds 21 p512 Top-1 hits, with paired gains/losses 37/16.
The p512 standard run reaches thermal status 3. The custom run reaches status 1.
The lower observed custom latency is not evidence that custom pooling itself accelerates the encoder.
The independent no-segmentation control has 41.02% Top-1 and zero segmentation errors.
Thus, the best of these four segmented conditions does not beat that control.

Source: [four-condition report](android/docs/reports/2026-10-20_base-naflex-p224-custom-pooling.md).

## 3. Query frame and segmentation on `my-failed-2`

The four custom conditions below retain identical custom reference-vector bytes.
The standard control keeps its original standard index.

| Complete pipeline | Top-1 / Top-5 / Top-10 | Median / P95 | Errors |
| --- | --- | --- | ---: |
| Fresh full-image standard control | 41.02 / 77.84 / 84.58% | 966 / 1700 ms | 0 |
| YOLO full-image custom | 38.92 / 77.54 / 84.43% | 1554 / 3002 ms | 2 |
| YOLO cropped custom | 36.98 / 68.86 / 73.95% | 1769 / 2428 ms | 2 |
| DIS 1024 full-image custom | 43.71 / 83.23 / 88.92% | 2283 / 5351 ms | 0 |
| DIS 1024 cropped custom | 47.01 / 84.58 / 89.82% | 2607 / 3429 ms | 0 |

Cropped DIS adds 40 Top-1 hits over the standard control: +5.99 percentage points.
The paired gains/losses are 115/75. Against full-image DIS, they are 73/51.
Full-image DIS fails the full-run latency targets.
Cropped DIS requires host-only USB continuation after 190 assignments.
Its Pixel process remains unchanged. The saved prefix remains byte-identical.
This is not an uninterrupted transport-stability pass.

YOLO segmentation runs on CPU. DIS segmentation runs on GPU.
The earlier YOLO crop also uses the earlier colour/alpha decoder.
Compare complete pipelines. Do not attribute every difference only to the mask or crop.
The repeated standard-control medians are 662, 878, and 966 ms in separate campaigns.
All three retain the same Top-1 predictions. Thermal and timing conditions differ.

Sources: [full-image comparison](android/docs/reports/2026-10-20_full-image-p512-custom-pooling.md),
[DIS comparison and stage budget](android/docs/reports/2026-10-20_dis-p512-pooling.md).

## 4. DIS resolution on `my-failed-2`

This comparison preserves p512 encoding, custom pooling, crop rendering, and custom reference bytes.
Only the DIS graph specialization changes.

| DIS input | Top-1 / Top-5 / Top-10 | Median / P95 | Peak sampled PSS | Maximum thermal status |
| --- | --- | --- | ---: | ---: |
| 1024 | 47.01 / 84.58 / 89.82% | 2607 / 3429 ms | 1751076 KiB | 2 |
| 768 | 46.56 / 84.58 / 89.67% | 1637 / 2052 ms | 1647703 KiB | 2 |
| 512 | 46.56 / 82.34 / 87.72% | 1324 / 1665 ms | 1481891 KiB | 1 |

Both smaller-input runs complete 668 assignments with zero errors and no continuation.
DIS 768 has 36 Top-1 gains and 39 losses against 1024: net -3 hits.
Its observed median decreases 37.22%. P95 decreases 40.15%.
Different start temperatures limit causal speed attribution.
These results do not establish statistically equivalent quality.
DIS 768 and 512 have equal aggregate Top-1, not identical successful queries.
DIS 768 retains 15 more Top-5 hits and 13 more Top-10 hits than 512.

Source: [resolution report and graph hashes](android/docs/reports/2026-10-20_dis-input-resolution.md).

## 5. Ten SO400M mobile adaptations

All ten recipes complete the same 668 assignments. Two no-bottle failures remain counted.
The experiment uses mobile masks instead of desktop SAM3 masks.
It does not reproduce the desktop table's model preparation and segmentation exactly.

| Recipe | Top-1 / Top-5 / Top-10 | Independent 30-image pilot median / P95 |
| --- | --- | --- |
| 1. Compact bottle and label fusion | 50.15 / 79.79 / 81.74% | 8.95 / 9.89 s |
| 2. Full rotated bottle and label fusion | 49.70 / 78.74 / 81.14% | 10.38 / 11.38 s |
| 3. Original and guarded-rotation mean, label fusion | 50.15 / 80.99 / 83.38% | 13.65 / 15.08 s |
| 4. Original and unrestricted-rotation mean, label fusion | 49.70 / 80.69 / 82.93% | 13.74 / 14.92 s |
| 5. Compact weighted bottle search | 46.86 / 78.89 / 81.74% | 4.26 / 5.09 s |
| 6. Original and guarded-rotation mean, bottle only | 46.86 / 81.14 / 83.53% | 9.09 / 10.83 s |
| 7. Asymmetric weights and label fusion | 48.05 / 79.19 / 82.34% | 10.10 / 11.51 s |
| 8. Standard pooling bottle search | 44.46 / 77.10 / 80.84% | 4.09 / 4.76 s |
| 9. Cardinal-gallery fusion | 49.40 / 79.34 / 81.59% | 8.83 / 10.09 s |
| 10. Exact coverage and stronger label weighting | 48.80 / 76.50 / 78.89% | 8.72 / 9.68 s |

The full campaign shares query work across all ten recipes.
Its 37.05 / 46.77 s request median/P95 covers all ten recipes together.
It is not independent latency for each recipe.
The resumed campaign retains process segments and exact saved prefixes.
It is not an uninterrupted process-stability pass.
The results do not support replacing the main app with these slower recipes.

Sources: [recipe definitions and independent pilot](android/docs/reports/2026-10-19_pixel8-my-failed2-offline-variants.md),
[completed continuation](android/docs/reports/2026-10-20_pixel-benchmark-recovery.md),
[committed compact results](research/android-20261020/results.json).

## 6. Failed candidates and engineering findings

- The earlier split-export pilot rejects all four encoder variants.
  Finite GPU vectors still fail numerical agreement. NaFlex p512 CPU/GPU cosine is 0.92733709.
  CPU fallback is numerically usable but too slow for the pilot latency gates.
  These results do not apply to the later verified complete graph.
- Colour-space and alpha decoding change four standard-control Top-1 results.
  Matching the production decoder restores all 668 control predictions.
- Default-precision DIS GPU execution fails the unchanged mask-parity gate.
  FP32 DIS with automatic storage passes. The encoder uses its separately verified BUFFER policy.
- A smaller source bitmap alone does not specialize a fixed-shape DIS graph.
  The exporter must preserve padding while changing activation shapes and fixed resize constants.
- Model reuse and one inference worker avoid repeated GPU creation in the benchmark path.
  Foreground HTTP lifetime and bounded fresh-socket transport improve test execution.
  Saved-prefix continuation preserves evidence after interruption. It does not erase the interruption.
- A no-object error is counted as a failure. The experiments do not silently substitute full-image output.
  Automatic CPU recovery after a GPU error is a different mechanism.

Sources: [split pilot](android/docs/reports/2026-10-19_pixel8-siglip2-base-pilot/report.md),
[decoder investigation](android/docs/reports/2026-10-20_full-image-p512-custom-pooling.md),
[DIS precision gates](android/docs/reports/2026-10-20_dis-p512-pooling.md),
[transport implementation](android/tools/offline_benchmark/README.md).

## 7. Verified production promotion

Release 0.3.0 defaults to DIS-768 cropped custom with complete Base NaFlex p512.
Format 7 keeps both matched model/index pairs. Settings can select full-image standard.
Each index has 2,093 wines. The pack shares images and position data.
The measured Pixel 8 path can use both models on GPU. Unmeasured devices retain the safety guard.

The main application's custom replay reproduces all 668 experimental Top-1 predictions.
Its Top-1/5/10 is 46.56/84.58/89.67%. Request median/P95 is 1372/1832 ms.
The maximum common score difference is 0.000003400. There are zero request errors.
The standard path reproduces all 30 sampled Top-1 predictions.
That sample is a parity check, not a complete standard quality benchmark.

The separate original 100-image Eval.zip run accepts 86 results: 81 exact and five alternatives.
All requests complete. Fourteen results are incorrect.
Request median/P95 is 1660/2039 ms. The comparison status is `FAIL`, not a perfect quality pass.
The release passes real gallery recognition, Settings switching, and same-key update persistence.
The release keeps no debug HTTP implementation. Optional YOLO weights are omitted by owner choice.

The new custom default has not completed a full `my` benchmark.
Do not attach the earlier 69.09% or 72.29% full-`my` scores to this release pipeline.
The APK uses the existing test signing certificate, not a production signing key.
Publication and complete public download hash verification are in the [release record](android/docs/releases/0.3.0.md).

## Portable evidence and verification

The [research package](research/android-20261020/README.md) retains 23 result series.
It includes 15,364 compact hard-cohort observations and 100 Eval.zip observations.
Thirteen series use Base. Ten SO400M recipe series share one 668-request campaign.
These counts are not 23 independent device campaigns.

```sh
python3 research/android-20261020/verify.py
python3 -m unittest discover -s research/android-20261020 -p 'test_*.py' -v
```

The standard-library checker verifies file hashes, cohort membership, counts, paired gains/losses,
inclusive latency percentiles, and standard/custom production Top-1 parity hashes.
The package retains derived acceptance flags and original source-file hashes.
It omits reference answers, catalogue weights, images, masks, raw vectors, APKs, and credentials.
The checker does not rerun model inference or independently relabel predictions.
Raw response archives remain preserved at the paths listed in the original component reports.
This document changes no application, benchmark, model, or deployment.
