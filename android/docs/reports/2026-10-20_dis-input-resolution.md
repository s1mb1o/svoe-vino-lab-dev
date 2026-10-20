# Pixel 8 DIS input-resolution experiment

Date: 2026-10-20.
Status at 21:16 MSK: both full resolution runs are complete. Both independent audits passed.
Final workflow cleanup confirms HTTP off and no remaining isolated process.

## Completed DIS-512 result

DIS 512 completed all 668 assignments with zero errors.
A fresh audit matches its saved audit. All 668 response and prediction records are present.
Top-1/5/10 is 311/550/586 hits: 46.56/82.34/87.72%.
Request median/P95 is 1324/1665 ms. Maximum is 2044 ms.
Latency and uninterrupted-stability targets pass. No continuation was required.
Peak sampled PSS is 1481891 KiB. Maximum thermal status is 1.
DIS 768 retains the same aggregate Top-1 and 15 more Top-5 hits and 13 more Top-10 hits.
These aggregate counts do not mean that the same queries succeed under both resolutions.
The owner selected DIS-768 cropped custom for a separate production promotion.
That promotion does not modify these frozen measurements.
All 105 frozen source files remain unchanged after both audits.
Predictions: [DIS 512](/Volumes/Storage/svoe-vino-final/artifacts/android-dis-resolution-20261020/comparison-v1/dis-512/full/predictions.jsonl).

## Completed DIS-768 result

DIS 768 completed all 668 assignments with zero inference errors.
The saved files contain 668 predictions and 668 responses in the expected order.
A fresh independent audit matches the saved audit.
Direct accepted-alternative counts and inclusive request percentiles also match.

| Measurement | DIS 1024 baseline | DIS 768 |
| --- | ---: | ---: |
| Top-1 hits | 314/668 (47.01%) | 311/668 (46.56%) |
| Top-5 hits | 565/668 (84.58%) | 565/668 (84.58%) |
| Top-10 hits | 600/668 (89.82%) | 599/668 (89.67%) |
| Request median | 2607 ms | 1637 ms |
| Request P95 | 3429 ms | 2052 ms |
| Request maximum | 5323 ms | 2753 ms |
| Peak sampled PSS | 1751076 KiB (1.67 GiB) | 1647703 KiB (1.57 GiB) |
| Maximum thermal status | 2 | 2 |
| Maximum sampled battery temperature | 43.8 C | 42.6 C |
| Inference errors | 0 | 0 |
| Uninterrupted process and transport | USB continuation required | Passed |

DIS 768 reduces request median by 37.22% and P95 by 40.15%.
Its paired Top-1 comparison has 36 gains and 39 losses.
The net change is three fewer hits, or -0.45 percentage points.
Top-5 is unchanged. Top-10 loses one hit.
These results do not establish statistically equivalent quality.
These results describe `my-failed-2`, not the full `my` dataset.

DIS 768 passed the latency and smoothness targets.
Pixel PID 7960 remained unchanged throughout its measured block.
No process restart, transport error, CPU fallback, or no-mask fallback occurred.
Scoped cleanup completed without errors. The controller then continued to DIS 512.
The measured block lasted approximately 22 minutes 53 seconds.
Its final transport record is at 20:47:44 MSK.

The DIS 1024 baseline required host-only USB continuation after assignment 190.
Its Pixel PID 22646 remained unchanged across both measured segments.
The original 190-record prefix remains byte-identical.
The disconnected interval is excluded from request latency.
Do not describe the baseline as an uninterrupted stability pass.
Both columns measure complete USB HTTP requests, not only model inference.
Start temperatures differ: 35.9 C for DIS 768 and 39.9/38.9 C for the DIS 1024 segments.
Thermal and sequential-run differences limit a strictly causal speed comparison.

Query order, accepted answers, source-image hashes, and custom reference bytes match.
All 105 frozen source files remain unchanged. Re-ranking remains disabled.
No production application or default changed.
The requested DIS-768 completion alert is paused after this report.
The DIS-512 workflow remains active. This alert did not change the device or workflow.
DIS-768 prediction SHA-256: `c092d2f2acb81dd40e9a62f2c738399b025bfb1777db32c4dcafa20d25b801ef`.
DIS-1024 prediction SHA-256: `d836c94ac19d2a5a8315c9a2cf1ce15b956a6f8b5f995ae6a732e833dea021ac`.

Predictions: [DIS 768](/Volumes/Storage/svoe-vino-final/artifacts/android-dis-resolution-20261020/comparison-v1/dis-768/full/predictions.jsonl).
Audit: [saved independent audit](/Volumes/Storage/svoe-vino-final/artifacts/android-dis-resolution-20261020/comparison-v1/dis-768/full/independent-audit.json).
Baseline: [DIS 1024](/Volumes/Storage/svoe-vino-final/artifacts/android-dis-p512-pooling-20261020/comparison-v4/condition-8-full/predictions.jsonl).

## Historical device checkpoint at 20:25 MSK

DIS 768 passed all 115 numerical checks. All 15 GPU/CPU/GPU requests succeeded.
Maximum raw mask error is 0.000001550. Maximum normalized mask error is 0.000006735.
Maximum source-projection error is 0.000000060. Maximum encoder component error is 0.000002906.
Every unchanged numerical threshold passed. No process restart or fallback occurred.

The 30-image pilot passed with zero errors.
Pilot median/P95 is 1358/1468 ms. Maximum is 1737 ms.
Pilot maximum thermal status is 0. Peak sampled PSS is 1653585 KiB.
These are pilot timings, not complete-cohort timings or quality.

At 20:25:25 MSK, full DIS 768 has 15/668 saved assignments and zero errors.
Pixel PID remains 7960. The full block started at battery temperature 35.9 C and thermal status 0.
Controller PID 93931 has parent PID 1. The frozen 105-file source inventory is unchanged.
Allow approximately 45-65 more minutes for both full runs, gates, audits, and cooling.
DIS 512 will start after full DIS 768 and its scoped cleanup.
Do not duplicate the controller or edit the frozen source.

The owner requested a DIS-768 report as soon as its results are ready.
Thread follow-up `report-dis-768-results` checks saved evidence every two minutes.
It reports the completed audit without waiting for DIS 512.
It does not change or interrupt either device run.
It stops its completion checks after the report or an actionable terminal failure.

## Fixed comparison

Test DIS 768 and DIS 512 against the completed cropped DIS 1024 baseline.
Use 668 `my-failed-2` assignments, 627 distinct images, and accepted alternative slugs.
Keep all segmentation failures in the quality and timing denominators.
Keep Base NaFlex p512, 768-dimensional vectors, and fractional custom pooling unchanged.
Use background weight 0.1 and foreground weight 1.0.
Keep the previous matched custom reference vectors unchanged.
Keep the original RGB decoder, four-percent crop margin, white compositing, and 1024-pixel render limit.
Keep re-ranking, barcode, OCR, label fusion, rotation, embedding sharing, and fallback disabled.

| DIS input | Top-1 | Top-5 | Top-10 | Median, ms | P95, ms | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1024 baseline | 47.01% | 84.58% | 89.82% | 2607 | 3429 | Complete; USB continuation preserved |
| 768 | 46.56% | 84.58% | 89.67% | 1637 | 2052 | Complete; audit and uninterrupted-stability targets pass |
| 512 | 46.56% | 82.34% | 87.72% | 1324 | 1665 | Complete; audit and uninterrupted-stability targets pass |

Do not infer a speedup or unchanged quality from the host export checks.
The baseline used the same Pixel process across two measured segments after USB disconnected.
Do not describe that baseline as an uninterrupted stability pass.

## Export checks

The pinned source is `litert-community/DIS-ISNet-LiteRT` at revision
`1b966dbe2f33bd5ca1299cf94fbab59265210b6b`.
Source graph SHA-256: `0c3c93b6a2a65e7c69137ec82596944e6bfb97d982c75bab03acb0738dbaa087`.
The source contains one subgraph, 247 operators, and fixed spatial resize constants.
The exporter specializes activation spatial shapes, six resize constants, and the final reshape shape.
It preserves learned weights, channel counts, operator options, and interpolation flags.
The original 1024 specialization reproduces the source CPU output with maximum error zero.
Both smaller candidates produce finite masks at their declared sizes on CPU.
Every declared tensor shape matches the CPU runtime-inferred shape.

The first shape walk identified the source's explicit one-pixel padding.
Padding must stay one pixel. It must not scale with the input resolution.
Preserve the first 512 export as unused preparation evidence in `exports/`.
Use only the padding-preserving candidates in `exports-v2/`.
Regression tests cover this padding distinction and unchanged channel dimensions.

DIS 768 graph SHA-256: `b8ede77d06da09f9220d40d8c0735eebbd474d443915d48e2c5f44855b596c94`.
DIS 512 graph SHA-256: `b032690ff9f7701945be5aaf6785e2be914cd8212e921cb3ca0ad15ffdb8a5dc`.
Pack 768 manifest SHA-256: `ae6205fb4579530470d5213113d1e9b2b5d1d2234a4d3a28d53731dfe0f07338`.
Pack 512 manifest SHA-256: `f7e17174d5500ee7e4a0e18e0cc125ecadfd9309ced7d0fdcd867b942b06d59e`.
All non-DIS pack payloads remain byte-identical to the previous pack.

## Build and device workflow

The separate application ID is `com.alolalab.chtozavino.disresbench`.
Test version is `0.1.7-dis-resolution`.
APK SHA-256: `7f69363432bdf81dabacef91e91f72e62f801c415fb4b8fbe98234e2a1e6e18f`.
All 54 host tests and 33 Android tests pass.
Android debug lint, API 28 signature verification, and 16-KiB alignment pass.
The frozen source snapshot contains 105 files.
The production pack retains SHA-256 `4307a92be20fc53bec18f922ae80b60d92fc219c2a8e22f981f8c8778117a128`.
The old application, private packs, APKs, snapshots, and prediction files remain unchanged.

The detached controller started at 20:21:21 MSK with PID 93931.
It has no automatic restart policy. It verifies source, APK, packs, and the original completed control.
It installs only the new application ID. It preserves each previous private experimental pack.
It verifies default-off HTTP before enabling the test server through the observed UI switch.
It runs 768 first and 512 second.
Each condition requires five-image GPU/CPU/GPU numerical checks and a 30-image pilot.
Raw and normalized DIS masks are compared with the same candidate on host CPU.
The mask threshold remains 0.001. Vector and reference-score thresholds remain unchanged.
Only eligible conditions start the full 668-assignment run.
Every block requires thermal status at most 2 and battery temperature at most 40 C.
The measured path uses DIS FP32 with automatic GPU storage and encoder FP32/BUFFER.
All GPU resources remain on one inference worker. No CPU or no-mask fallback is enabled.
Cleanup disables HTTP, stops only the new isolated app, and removes the owned USB forward.

## Artifact paths

Artifact root: `/Volumes/Storage/svoe-vino-final/artifacts/android-dis-resolution-20261020/`.

- `exports/identity-1024/`: original-resolution identity check.
- `exports-v2/dis-768/` and `exports-v2/dis-512/`: verified fixed-shape graphs and change inventories.
- `device-packs/dis-768/` and `device-packs/dis-512/`: unchanged encoders/references with smaller DIS.
- `apk-v1/`: signed debug test APK.
- `build-record-v1.json`: test counts, artifact hashes, and source inventory.
- `source-snapshot-v1/`: frozen execution tools and Android sources.
- `workflow-v1/`: detached launch record and workflow logs.
- `comparison-v1/status.json`: current device stage and eligibility.
- `comparison-v1/dis-768/full/predictions.jsonl`: full 768 predictions, when eligible.
- `comparison-v1/dis-512/full/predictions.jsonl`: full 512 predictions, when eligible.
- `comparison-v1/comparison.json` and `comparison-v1/report.md`: final comparison, after completion.

Query SHA-256: `1b8fb97a08b08fe8d9c7a422c142e316e5f853cd827219236ca5504840cce93a`.
Custom reference SHA-256: `684be34d3d200b6b130bb8192060799036d57ced096e25f2a955be1cf384286b`.
No production default change, commit, or push is part of this experiment.
Read [plan 12](../plans/12_dis-input-resolution.md).
Source context: [the model card](https://huggingface.co/litert-community/DIS-ISNet-LiteRT).
