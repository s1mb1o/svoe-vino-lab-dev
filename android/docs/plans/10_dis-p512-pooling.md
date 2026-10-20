# DIS p512 pooling comparison on Pixel 8

Date: 2026-10-20.
Status: complete. All three numerical gates, pilots, and full quality audits passed.
Full-image DIS failed the full-run latency targets. Cropped DIS passed latency targets after USB continuation.
Read the measurement record for the final five-pipeline comparison and stability caveat.

## Scope and identity

Use an isolated package `com.alolalab.chtozavino.dispoolbench`.
Keep the production application and all completed YOLO experiments unchanged.
Use the same 668 frozen `my-failed-2` assignments and accepted alternative slugs.
Use the same 2,093 wines and one reference per wine.
Keep re-ranking, barcode, OCR, rotation, label fusion, and embedding caches disabled.
Reuse the exact p512 standard and custom graphs, position table, and indexes.
Keep the production standard index for the control.
Keep the previous matched custom index for both custom conditions.
Do not rebuild reference vectors with DIS in this query-only comparison.

| Condition | Query frame | Pooling | Segmentation | Reference index |
| --- | --- | --- | --- | --- |
| 5 | Full original RGB | Standard | None | Production standard |
| 7 | Full original RGB | Fractional background 0.1, foreground 1.0 | DIS GPU | Previous matched custom |
| 8 | Native white-background crop | Same custom pooling | DIS GPU | Same custom index |

Use the corrected production-equivalent full-resolution decoder for all three conditions.
Condition 7 MUST preserve full source RGB and geometry before NaFlex preprocessing.
Condition 8 MUST reuse the prior four-percent crop margin and 1,024-pixel render limit.
Use the existing DIS model from the production pack.
DIS SHA-256 MUST be `0c3c93b6a2a65e7c69137ec82596944e6bfb97d982c75bab03acb0738dbaa087`.
DIS uses a stretched 1,024 by 1,024 NCHW input and RGB normalization `value / 255 - 0.5`.
Normalize each finite DIS output with its minimum and maximum, as production does.
Project the soft mask to source coordinates. DIS identifies foreground, not a bottle class.
Do not substitute a full-image result for a failed mask.
Keep mask failures in the complete-cohort denominator.

## Execution and gates

Run DIS and the complete p512 encoder on GPU for measured custom requests.
Use FP32 arithmetic and automatic GPU storage for DIS.
Use FP32 GPU execution, BUFFER storage, and no GPU program cache for the encoder.
Create, run, and close every model on the same inference thread.
Reuse compiled models across requests. Do not enable silent CPU fallback.
Numerical checks MAY explicitly select the CPU encoder. DIS remains GPU for these checks.
Compare captured DIS tensors and normalized masks with the same graph on host CPU.
Require maximum raw and normalized mask error at most 0.001.
Verify the projected soft mask, patch weights, encoder vector, and reference scores.
Require encoder cosine at least 0.99999 and maximum component error at most 0.001.
Use the four affected ICC/alpha inputs and one opaque control for GPU/CPU/GPU parity.
Require production vector/ranking agreement for all standard parity requests.
Run an independent 30-image stability pilot for each condition.
Require median at most 3 seconds, P95 at most 5 seconds, and maximum at most 10 seconds.
Require all 668 standard Top-1 predictions to match production before any full custom run.
Stop on a process change, critical thermal status, invalid output, or an unexpected error.
Require Android user 0, unlocked setup, sufficient storage, thermal status at most 2,
and battery temperature at most 40 C before each block.

## Artifacts and reporting

Freeze source, APK, pack, queries, and workflow before device execution.
Use a finite detached controller. Do not install an automatic restart policy.
Use default-off HTTP and the isolated foreground service on the existing port 18088.
Preserve all previous predictions and APKs. Do not clear another package's data.
Save predictions, responses, numerical captures, latency, PSS, heat, and device identity.
Audit every completed 668-assignment cohort independently.
Compare DIS full-image, DIS cropped, the repeated control, and the completed YOLO runs.
Do not attribute whole-pipeline latency differences only to mask quality.
YOLO ran on CPU. DIS runs on GPU in this test.
Control and custom use different reference indexes.
Disable HTTP and stop only the isolated package during final cleanup.
Do not change the production default from this workflow.

## Preserved runtime correction

The initial DIS implementation incorrectly reused the encoder's FP32/BUFFER options.
Its numerical gate passed. Its first independent pilot requests had median latency near 3.8 seconds.
Production DIS uses `CompiledModel.Options(Accelerator.GPU)` without those encoder overrides.
Preserve attempt v1 and its numerical evidence. Stop its pilot through the host runner.
Wait for HTTP-off and process-stop cleanup before another attempt.
Match production DIS GPU options in test version 0.1.5.
Keep the same pack and all numerical and smoothness thresholds.
Freeze new sources and APK. Run a new v2 attempt after exact installed-APK and private-pack checks.
Do not weaken the numerical gate if the production DIS options change mask precision.

V2 default DIS GPU options are fast but fail the unchanged mask agreement threshold.
Maximum raw mask error is 0.007584096. Maximum normalized mask error is 0.032568038.
The workflow stopped before full tests and completed HTTP-off/process-stop cleanup.
Preserve v2. Test FP32 arithmetic with `BufferStorageType.DEFAULT` in version 0.1.6.
Keep the encoder's FP32/BUFFER settings and every numerical threshold unchanged.
Use new v3 source, APK, workflow, and result directories.
