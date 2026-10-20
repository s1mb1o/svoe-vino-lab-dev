# DIS input-resolution comparison

Date: 2026-10-20.
Status: implemented. All host/build checks pass. The finite Pixel workflow started at 20:21 MSK.
Device gates and full-cohort quality remain pending.

## Scope

Test DIS at 768 and 512 input pixels on Pixel 8.
Compare cropped/white custom pooling with the completed 1024 DIS result.
Use all 668 frozen `my-failed-2` assignments and accepted alternative slugs.
Keep Base NaFlex p512, custom pooling, reference vectors, and FP32 GPU policies unchanged.
Keep re-ranking, barcode, OCR, label fusion, rotation, and fallback disabled.
Keep the original RGB decoder, four-percent margin, and 1024-pixel crop-render limit.
Do not change production or any completed benchmark artifact.

## Graph specialization

Start from pinned DIS SHA-256 `0c3c93b6a2a65e7c69137ec82596944e6bfb97d982c75bab03acb0738dbaa087`.
The graph has one subgraph, 247 operators, and fixed spatial resize constants.
Create separate fixed-shape LiteRT exports for 768 and 512.
Change only activation spatial shapes, six bilinear-resize size constants, and the final reshape shape.
Preserve every learned weight, operator, option, channel count, normalization, and interpolation flag.
Reject an unexpected graph layout or shape constant.
Record every changed tensor and buffer. Record all immutable buffer hashes.
Test identity specialization at 1024 against the original CPU output.
Require finite CPU outputs with the declared square mask size for both candidates.
Do not claim that smaller masks equal the 1024 masks.

## Device contract

Use a separate package `com.alolalab.chtozavino.disresbench`.
Keep HTTP disabled by default. Use the existing isolated foreground-service lifecycle.
Load the DIS input size from checked model metadata.
Accept only 512, 768, and 1024 with matching NCHW input and output shapes.
Report the DIS size and graph hash in each response.
Keep model creation, inference, and cleanup on the same worker.
Keep DIS FP32 with automatic storage and encoder FP32/BUFFER.
Preserve all encoder, position-table, and reference bytes from the previous DIS pack.
Use separate packs and output directories for the two resolutions.
Stop the test process before changing its private pack. Preserve the previous private pack.

## Gates and full runs

Verify the original 1024 run and production-control agreement before device work.
Verify every prepared pack and installed APK hash.
Run five-image GPU/CPU/GPU encoder checks for each cropped candidate.
Compare captured DIS raw and normalized masks with the same candidate on host CPU.
Keep maximum mask error at most 0.001. Keep all previous vector and score thresholds.
Verify mask projection and fractional patch weights at the declared DIS resolution.
Run an independent 30-image pilot for each candidate.
Require median at most 3000 ms, P95 at most 5000 ms, and maximum at most 10000 ms.
Run the full 668 assignments only for eligible candidates.
Require thermal status at most 2 and battery temperature at most 40 C before each block.
Stop on process change, critical thermal status, invalid outputs, or an unexpected error.
Keep expected segmentation failures in predictions and in quality/timing denominators.
Use a finite detached workflow. Do not add an automatic restart policy.

## Evidence and cleanup

Freeze source, graph, pack, APK, and workflow before execution.
Save `predictions.jsonl`, responses, numerical captures, timings, PSS, and thermal samples.
Audit each complete cohort. Compare Top-1/5/10 and paired gains/regressions with DIS 1024.
Compare median/P95, segmentation stage latency, memory, and maximum thermal status.
Use identical accepted answers and custom reference hashes for every comparison.
Report numerical or pilot failures without weakening thresholds.
Disable HTTP and stop only the separate test package during final cleanup.
Remove the owned USB forward. Restore the observed screen-power setting.
Record successful cleanup and the final report. Do not change the production default.
