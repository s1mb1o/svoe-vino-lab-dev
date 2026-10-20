# Isolated Base NaFlex p224 and p512 comparison

Use this experiment to compare four matched conditions on Pixel 8.
Do not install this APK over the production application or the active offline benchmark.

| Condition | Patch budget | Pooling |
| --- | --- | --- |
| 1 | 224 | Standard attention |
| 2 | 224 | Fractional bottle coverage; whitespace 0.1; bottle 1.0 |
| 3 | 512 | Standard attention |
| 4 | 512 | Fractional bottle coverage; whitespace 0.1; bottle 1.0 |

All conditions use `google/siglip2-base-patch16-naflex` at revision
`b53b807d3a2d5e2b3911292f2d69e5341cdc064c`.
All conditions preserve image proportions and output 768 dimensions.
The value p224 means at most 224 patches. It does not mean 224 by 224 pixels.

The source report defines the selected profile as `5a`:
[complete report](http://127.0.0.1:59998/complete-report-20261018/report.html).
That report uses SO400M and desktop masks. Its accuracy does not establish Android quality.
The selected candidate uses one image-encoder pass and no label fusion.

## Weight contract

For each valid patch, calculate the fraction `f` covered by the bottle mask.
Resize the float mask to the actual NaFlex image grid with bilinear interpolation.
Average each 16 by 16 patch. Set `weight = 0.1 * (1 - f) + f`.
Add `log(weight)` to the original attention-pooling logits.
Keep the transformer, original attention head, LayerNorm, MLP, and normalization.
Keep valid-patch flags. Padding is not whitespace.
A white label belongs to the bottle. Do not calculate coverage from RGB whiteness.

Conditions 1 and 2 use the same modified complete graph.
Condition 1 supplies zero log bias. Condition 2 supplies mask-derived log bias.
Each condition has its own reference index and effective profile checksum.
Conditions 3 and 4 use separate original and modified p512 graphs.
The p512 zero-bias gate verifies agreement between those graphs.
The indexes contain the same 2,093 wines and one unrotated reference per wine.
References use frozen original alpha cuts. Do not substitute display WebP images.
Queries use original image bytes and the on-device catalogue-trained bottle segmenter.
The segmenter runs on CPU. The encoder runs on the explicitly requested accelerator.
No query mask or accepted answer goes to the device.
No re-ranking, barcode, OCR, VLM, rotation, label fusion, or full-image fallback runs.

## Build and prepare

Use the cached Python 3.11 environment from `siglip2-naflex-litert`.
The environment supplies LiteRT 2.2, the converter schema, NumPy, Pillow, and Torch.
Do not download another model copy. Use the pinned existing complete graphs.

Run these commands from the repository root:

```sh
python -m unittest discover -s android/tools/base_p224_experiment -p 'test_*.py' -v
JAVA_HOME=/path/to/jdk-17 ANDROID_HOME=/path/to/android-sdk \
  bash android/tools/base_p224_experiment/build_device.sh
```

The APK path is
`device/app/build/outputs/apk/debug/app-debug.apk` under this directory.
Its application ID is `com.alolalab.chtozavino.basepoolbench`.
Its launcher name is `Что за вино · Base pooling тест`.
The four-condition APK version is `0.1.1-base-p224-p512-pooling`.
The Kotlin namespace retains `com.alolalab.chtozavino.offlinebench` for shared JNI code.
The HTTP switch is off on first launch. The foreground service exists only while HTTP runs.
The experiment reuses lifecycle and geometry source files through a Gradle copy task.
The build does not modify the original offline benchmark sources.

Use the preparation tools in this order. Each tool exposes its required paths with `--help`.

1. `freeze_inputs.py`: verify source cuts, source hashes, and the frozen 668 query assignments.
2. `../offline_benchmark/patch_weighted_pooling.py`: add the log-bias graph input to each Base budget.
3. `validate_graph.py`: check zero bias, an independent attention oracle, and padding exclusion for each budget.
4. `build_references.py`: build all four matching indexes on one local GPU graph at a time.
5. `assemble_pack.py`: include verified models, reference vectors, and the position table.

Use `--p512-custom` and `--p512-validation` for the new p512 graph and its passed gate.
Use `build_references.py --reuse` to retain the three verified v1 indexes byte-for-byte.
The v2 pack contains both budget-specific graph-validation reports.
Keep the v1 APK, pack, indexes, and source snapshot as historical evidence.
The v1 waiting coordinator was superseded before any device use.

Use new output directories. Preserve failed attempts and previous results.
Do not put model weights, generated packs, or query photographs in Git.
The generated pack contains no query photographs, query masks, or accepted answers.

## Run the finite comparison

Use `run_comparison.py` only after the APK and pack are complete.
The coordinator reads the preceding run's local evidence while it waits.
It does not access the phone until that run finishes and its cleanup passes.
It rejects an already installed Base experiment package to preserve existing data.

```sh
python -u android/tools/base_p224_experiment/run_comparison.py \
  --after /path/to/full-my-failed2-v3 \
  --serial 41231FDJH002WZ \
  --apk /path/to/frozen-base-p224-test.apk \
  --pack /path/to/base-p224-pack \
  --queries /path/to/frozen-queries.json \
  --out /path/to/new-comparison-attempt
```

Keep the phone connected, unlocked, and in user 0 for setup.
The coordinator does not unlock the phone, switch users, or restart Android.
It requires thermal status at most MODERATE and battery temperature at most 40 C before a block.
It requests the notification permission through the observed Android dialog.
It verifies default-off HTTP before explicit enablement.

For each of the four conditions, run three distinct images in GPU, CPU, and GPU blocks.
Validate captured tensors and all reference scores on the host.
Require cosine at least 0.99999 and maximum component error at most 0.001.
These thresholds compare the same deployed FP16 model weights.
They do not measure FP32-source-to-FP16 quantization loss.

Then run 30 frozen, evenly spaced distinct images for that condition.
Do not select images from correctness or segmentation success.
Require client median at most 3 seconds, P95 at most 5 seconds, and maximum at most 10 seconds.
Exclude one warmup request. Include decoding, segmentation, crop, encoder, and matching.
Record PSS, heat, process identity, raw responses, and transport attempts.
Stop on CRITICAL heat, process changes, invalid vectors, or unexpected model errors.
Run all 668 assignments only for conditions that pass the numerical and smoothness gates.

## Results and evidence

Each condition writes `predictions.jsonl`, raw responses, `run.json`, telemetry, and logcat.
Segmentation failures remain in predictions and in the accuracy denominator.
The host audit accepts all frozen alternative slugs.
Incomplete runs do not produce complete-cohort accuracy.
The final `comparison.json` records Top-1/5/10 and paired gains and regressions.
It compares standard with custom pooling at each budget.
It also compares p224 with p512 for each pooling type.
The production default remains unchanged.

Read the dated [measurement record](../../docs/reports/2026-10-20_base-naflex-p224-custom-pooling.md).
Device results remain pending until their artifacts exist and their audits pass.

## Recover an interrupted host run

Require owner authorization before a continuation.
Do not edit the raw interrupted directory or a frozen measurement tool.
Use `recover_interrupted.py` with a new output directory and the observed saved count.
The utility copies all original files and preserves every prediction byte.
It derives missing maxima from saved telemetry. It does not invent samples.
The recovery copy's `finished_at` is the metadata finalization time.
The recovery record states that the actual original worker exit time is unknown.
The utility runs the independent audit and a dry resume-prefix check.

Use `resume_workflow.py` with an explicit frozen workflow configuration.
The workflow resumes the full selector first. It starts the four-condition comparison
only after successful completion, audit, and cleanup.
Use new full-run and comparison directories. Preserve the old attempts.
The workflow transfers the abandoned ADB forward to the resumed runner.
The resumed runner can then remove its own forward during cleanup.

Use `start_detached.py --config /path/to/workflow.json` for a finite standalone process.
The launcher uses a separate session and ignores `SIGHUP`.
It writes a PID record and redirects output to persistent log files.
It has no automatic restart policy. It refuses to reuse an existing attempt directory.
Do not use `launchctl submit` as a one-shot launcher. That command restarts failed jobs.
Keep the Pixel connected and unlocked for the comparison setup.
