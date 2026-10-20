# Android NaFlex implementations

## Latest application measurements

Summary date: 2026-10-20.
The implementation and benchmark versions below are distinct.

The matched full-`my` experiment records 72.29% Top-1 with DIS and the encoder on GPU.
Its full-photo control records 69.09% Top-1 on the same 2,970 positive assignments.
The segmented experiment adds 95 hits and increases client median latency from 924 to 1,319 ms.
It also uses more sampled memory.
Read [the full matched comparison](reports/2026-10-19_pixel8-p512-dis-dual-gpu-my.md).

The later [Android 0.3.0 release record](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/6bd4abed8009296dec8cdde4e418103f610a74ba/android/docs/releases/0.3.0.md)
reports 46.56% Top-1, 84.58% Top-5, and 89.67% Top-10 on 668 `my-failed-2` assignments.
Its `DIS768_CUSTOM` replay has zero errors and a 1,372/1,832 ms request median/P95.
The standard full-photo control on that hard cohort has 41.02% Top-1.
These compare complete pipelines with different preparation and matched reference indexes.
The hard cohort is not a full-`my` score.
That release record has no full-`my` quality measurement for version 0.3.0.
The linked release source is on `origin/main` at `6bd4abed`.
This documentation update does not change the runtime or model pack in this checkout.
Read [the current benchmark index](../../BENCHMARKS.md) for sources and timing limits.

## Earlier implementation comparison

Date: 2026-10-19

## Working copies

The current wine application working copy is
`/Volumes/Storage/svoe-vino-final/code/svoe-vino-lab-android/android`.
Its application ID is `com.alolalab.chtozavino`.
Measurements and archived APKs made before the ID change keep
`chtozavino.alolalab.com`.
Its application version is `0.2.0`.
Its built-in format 6 pack uses the verified complete Base NaFlex p512 graph.

The separate model-port project is
`/Volumes/T7_2TB/Projects-T7_2TB/siglip2-naflex-litert`.
Its Android benchmark application ID is `dev.naflex.benchmark`.
Its release version is `0.2.0`.
The release provides an AAR, a benchmark APK, and a separate Base p512 model ZIP.
The wine application now uses the pinned v0.2.0 AAR and matching p512 model package.
Read [the integration report](reports/2026-10-19_base-p512-default.md).

## Experimental split runtime

This repository exports a backbone and a pooling head as separate LiteRT models.
The runtime accepts model-pack formats 4 and 5.
The pooling head runs on CPU.
The tested GPU backbones failed numerical agreement on Pixel 8.
The pack builders therefore disable GPU by default.
The CPU measurements in the October 19 pilot belong to these split exports.
Read [the pilot report](reports/2026-10-19_pixel8-siglip2-base-pilot/report.md).

## Verified complete-graph library

The separate project uses one complete encoder graph.
Its graph uses separate attention heads and stable normalization.
Its default stores FP16 weights and requests FP32 GPU execution with BUFFER storage.
Its default disables GPU program caching.

The October 5 and 6 tests ran sixteen profiles on Pixel 8 and realme RMX3890.
Each model family has patch budgets of 128, 196, 224, 256, 512, 576, 784, and 1024.
The families are Base and SO400M.
All profiles completed numerical checks and five fresh process loads.
Some SO400M profiles exceeded the speed or sampled-memory target.

The Base p512 sweep encoder P95 was `401.5` ms on Pixel 8.
The same measurement was `2243.2` ms on realme RMX3890.
These timings exclude image preprocessing and catalogue search.

The released Base p512 ran all 100 original Eval images on Pixel 8 without query
segmentation.
It accepted `85/99` known wines at rank 1 and `96/99` at rank 5.
The check accepted the supplied alternative slugs.
All 100 ordered Top-5 results matched the desktop paths.
The one unknown query was also accepted by the nearest-wine policy.
The median encode and search time was `533.7` ms.
The P95 encode and search time was `964.9` ms.
These timings exclude model loading, HTTP, and USB.

The source reports are in the separate repository:

- `docs/reports/gpu-rewrite.md`
- `docs/reports/naflex-sweep.md`
- `docs/reports/naflex-realme-sweep.md`
- `docs/reports/eval-pixel-8-base-p512.md`
- `docs/releases/v0.2.0.md`
- `docs/android-integration.md`

The 0.2.0 integration measured on 2026-10-19 uses this library and its matching frozen reference index.
That measured wine pack retains 2,093 wines and one reference for each wine.
That measured query path does not segment the image.
The integrated wine application passed the thirty-image Pixel 8 runtime pilot.
It passed CPU/GPU parity on one reference and desktop parity on fourteen images.
It also passed UI recognition and history persistence after a cold restart.
The warm server median was 514.8 ms. P95 was 748.8 ms.
Read the integration report for timing scope and retrieval limits.
The subsequent full `my` run completed all 3,409 requests without HTTP errors.
Positive Top-1 was 69.09%, Top-5 was 87.10%, and Top-10 was 90.03%.
Client median latency was 924 ms. P95 was 1,479 ms.
The full run reached `SEVERE` and regressed on negative cases.
Read [the full-run report](reports/2026-10-19_pixel8-base-p512-full-my.md).
Do not use the fixed Base/224 vectors with Base NaFlex p512.
Keep the split pilot and the complete-graph measurements separate.
