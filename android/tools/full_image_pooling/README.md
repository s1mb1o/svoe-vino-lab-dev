# Full-image p512 pooling experiment

Use the approved [plan](../../docs/plans/09_full-image-p512-custom-pooling.md).
This experiment preserves the full query RGB image.
The bottle mask changes only attention-pooling weights.
It does not crop, whiten, rotate, or remove the background.

Condition 5 reproduces the current standard no-segmentation pipeline.
It uses byte-exact production vectors.
Condition 6 uses the previously measured matched custom reference index unchanged.
It uses the CPU bottle mask and the GPU complete p512 custom graph.
Keep detection failures in the denominator. Keep re-ranking and barcode recognition off.

Build the shared isolated test project with `-PfullImagePooling=true`.
This property selects `com.alolalab.chtozavino.fullpoolbench` and version `0.1.3-full-image-p512-pooling`.
Set `BASE_POOLING_PACKAGE=com.alolalab.chtozavino.fullpoolbench` for its host tools.
The ordinary four-condition package remains the default when the property is absent.
The production application is not changed.

Use `prepare_pack.py` to combine verified p512 weights, the previous custom index,
and the exact production index in a new pack directory.
No query image, query mask, or accepted answer belongs in the device pack.
Freeze source, APK, pack, queries, and configuration before launching a measurement.

Use `launch.py --config /absolute/path/to/workflow.json` for a finite detached run.
The configuration names the frozen shared `run_comparison.py`, old completed full run,
new pack, APK, serial, frozen queries, new output directory, and previous control directory.
The launcher selects conditions 5 and 6. It has no automatic restart policy.
The workflow verifies default-off HTTP, then performs numerical gates and pilots.
The full-image numerical gate checks pixel preservation, released preprocessing,
fractional coverage, CPU/GPU vectors, and all reference scores.
Condition 5 must reproduce all original control Top-1 predictions.
Only conditions that pass the gates proceed to the full 668-assignment run.
Final cleanup disables HTTP and stops only the isolated test package.

The repaired decoder follows production source-colour and alpha handling.
Numerical checks cover the four ICC/alpha inputs from the stopped first attempt.
Raw RGB captures verify the released preprocessing without a PNG colour conversion.
For an explicit update, set `replace_apk_sha256` to the preserved installed APK hash.
The workflow checks that APK and all private pack files before `adb install -r`.
It does not clear application data. Use a new snapshot and output directory for each attempt.
