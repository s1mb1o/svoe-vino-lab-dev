# Full-image p512 custom pooling on Pixel 8

Date: 2026-10-20.
Status: implementation complete. The owner authorized test-only decoder repair and a new attempt.

## Scope

Test original full-image RGB with Base NaFlex p512 custom attention pooling.
Use the on-device bottle mask only to calculate fractional patch weights.
Do not crop, rotate, whiten, remove the background, or resize to a fixed long edge.
Keep the released NaFlex aspect-preserving 512-patch preprocessing.
Use whitespace weight 0.1 and bottle weight 1.0.
Keep the previous custom reference index byte-identical, as the owner selected.
Keep missing-mask errors in the denominator. Do not add a fallback in this experiment.
Keep re-ranking, barcode, OCR, label fusion, and embedding caches disabled.

The control uses full-image standard pooling and byte-exact production reference vectors.
Run control and custom in the same isolated application and HTTP implementation.
Keep the production application and its saved settings unchanged.

## Identity and data

- Encoder: `google/siglip2-base-patch16-naflex`.
- Revision: `b53b807d3a2d5e2b3911292f2d69e5341cdc064c`.
- Patch budget: 512. Patch size: 16. Vector dimension: 768.
- Custom graph: the previously validated complete p512 log-bias graph.
- Custom index: condition 4 from the completed four-condition experiment.
- Control graph and index: the existing verified format 6 production pack.
- Catalogue: the same 2,093 wines, one unrotated reference per wine.
- Query set: all 668 frozen `my-failed-2` assignments, including accepted alternatives.
- Query SHA-256: `1b8fb97a08b08fe8d9c7a422c142e316e5f853cd827219236ca5504840cce93a`.
- Isolated application ID: `com.alolalab.chtozavino.fullpoolbench`.
- Existing debug HTTP port: 18088. Do not start another owner on this port.

## Device contract

Condition 5 is the full-image standard control. It does not invoke segmentation.
Condition 6 is the full-image custom query. It invokes only the CPU bottle segmenter.
Both conditions use the explicitly selected GPU encoder for quality measurements.
Keep model creation, execution, and cleanup on one inference worker.
Keep the HTTP switch off on first launch. Use the existing foreground service during tests.
Do not silently fall back to CPU or to the cropped query path.
The full-image frame MUST retain decoded image dimensions and pixel values exactly.
The mask MUST remain aligned with the complete decoded source coordinate system.
Each successful response MUST identify query preparation and reference-index policy.

## Verification gates

1. Pass host contracts and Android unit tests. Build and lint the isolated APK.
2. Verify graph, index, pack, APK, source, and query hashes.
3. Require Pixel user 0, unlocked setup, and sufficient storage.
4. Require thermal status at most 2 and battery temperature at most 40 C before a block.
5. Run GPU/CPU/GPU on the four affected ICC/alpha images and one opaque control for both conditions.
6. Compare captured tensors and vectors with the same deployed FP16 graph on the host.
7. Require cosine at least 0.99999 and maximum vector component error at most 0.001.
8. Verify patch pixels against the original full image and the released preprocessing.
9. Verify that control results reproduce the existing production-control candidates.
10. Run the same 30-image smoothness pilot for each condition.
11. Require median at most 3 seconds, P95 at most 5 seconds, and maximum at most 10 seconds.
12. Run all 668 assignments only after numerical and smoothness gates pass.

Stop on critical heat, a process change, invalid vectors, or an unexpected inference error.
Use a finite detached controller with persistent logs and no restart policy.
Disable HTTP and stop only the isolated test app during final cleanup.

## Results

Save separate `predictions.jsonl`, raw responses, timing, memory, heat, and device identity.
Audit complete cohorts independently. Retain every assignment and detection failure.
Report Top-1/5/10, paired gains/regressions, client median/P95, and thermal differences.
Compare the custom full-image result with the new control and the prior cropped custom run.
Treat the comparison with standard references as a whole-pipeline comparison.
Do not describe that comparison as a query-pooling-only experiment.
Record results in the dated report. Do not change the application default automatically.

## Preserved second attempt

The first attempt stopped after four control Top-1 mismatches.
Its decoder forced sRGB. Production preserves source colour values and discards alpha without compositing.
Copy the production full-resolution decoder contract into the isolated test application.
Keep the legacy cropped decoder unchanged.
Capture raw RGB for preprocessing checks. Do not use PNG conversion as the pixel oracle.
Check q-000029, q-000171, q-000380, and q-000567 in every numerical gate.
Add the first independent-pilot image as the opaque control.
Keep all GPU/CPU/GPU recreations and exact production candidate comparisons.
Require identical Top-1 predictions for all 668 control assignments before full custom execution.

Keep all v1 files unchanged. Freeze repaired sources and APK in v2 directories.
Reuse the exact v1 pack and query files. Do not change model or index bytes.
Before an APK update, require the known installed v1 APK hash and the exact private pack hashes.
Use an APK update. Do not uninstall the package or clear application data.
Verify that HTTP is off before explicit enablement. Always disable HTTP during cleanup.
