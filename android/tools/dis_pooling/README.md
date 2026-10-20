# DIS p512 pooling experiment

## Input-resolution experiment

The separate [resolution experiment](../../docs/plans/12_dis-input-resolution.md)
tests fixed-shape DIS 768 and DIS 512 with the same p512 custom query pipeline.
Build it with `-PdisPooling=true -PdisResolution=true`.
Its package is `com.alolalab.chtozavino.disresbench`, version `0.1.7-dis-resolution`.
The exporter preserves learned weights and operator options. It keeps explicit padding fixed.
The pack builder changes only DIS and its metadata. All encoder and reference bytes stay unchanged.
Use separate packs, frozen sources, and output directories. Do not overwrite the 1024 baseline.
Read the [resolution measurement report](../../docs/reports/2026-10-20_dis-input-resolution.md).

## Original 1024 comparison

Use [plan 10](../../docs/plans/10_dis-p512-pooling.md).
This experiment changes the query segmenter. It does not rebuild catalogue vectors.
Condition 5 repeats the standard full-image control without segmentation.
Condition 7 uses DIS only for full-image patch weights.
Condition 8 uses DIS for a native white-background crop and the same patch weights.
Both custom conditions keep background weight 0.1 and foreground weight 1.0.
Both custom conditions use the previous matched custom index unchanged.
Keep all 668 frozen assignments and accepted alternative slugs.
Keep re-ranking, barcode, OCR, rotation, and label fusion disabled.

Build the shared test project with `-PdisPooling=true`.
The package is `com.alolalab.chtozavino.dispoolbench`.
Its test-only version is `0.1.6-dis-p512-pooling`.
The production app, defaults, and model pack remain unchanged.
DIS and SigLIP2 run on GPU. Explicit numerical probes MAY select the CPU encoder.
DIS uses FP32 arithmetic and automatic GPU storage. The encoder forces FP32/BUFFER execution.
The default DIS precision failed strict mask agreement. The first forced-BUFFER pilot was too slow.
Both attempts remain preserved. All numerical thresholds remain unchanged.
Do not enable CPU fallback or a no-mask fallback during a measurement.
Keep all model creation, inference, and cleanup on the same worker.

Use `prepare_pack.py` with the previous full-image pack and the verified production ZIP.
It verifies the DIS hash and tensor contract. It copies encoder and index bytes unchanged.
Freeze sources, pack, APK, and workflow before device execution.
Use the shared `full_image_pooling/launch.py` with `package` set to this package
and `conditions` set to `[5, 7, 8]` in a new workflow configuration.
Use a new output directory. Preserve every completed attempt.

The workflow requires five-image GPU/CPU/GPU numerical gates and independent 30-image pilots.
It compares captured DIS masks with the same host CPU graph.
It independently verifies source-mask projection and fractional patch weights.
It requires all 668 standard-control Top-1 predictions to match production before full custom tests.
Final cleanup disables HTTP and stops only the isolated test package.
Read [the measurement report](../../docs/reports/2026-10-20_dis-p512-pooling.md).
