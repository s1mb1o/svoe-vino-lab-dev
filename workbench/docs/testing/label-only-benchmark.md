# Label-only benchmark

Date: 2026-10-11.
State: LAN descriptions run. Cloud rules wait for approval.

The owner requested both the targeted comparison and the official-test evaluation.
The protocol is in [SPEC.md](../../../internal/label-only-benchmark-20261011/SPEC.md).
The prepared payload review is in [cloud-payload-review.md](../../../internal/label-only-benchmark-20261011/cloud-payload-review.md).

## Comparison

The `current` arm describes the package crop.
The `label_only` arm describes the label crop.
The label-only description prompt excludes bottle and capsule features.
Both arms generate fresh rules with the same rule prompt.
Both arms use the same recognition prompt.
Both arms keep the initial retrieval scores.
The benchmark changes the description image and description prompt together.
Do not attribute the result to the image alone.

All 57 selected catalogue wines have label crops.
All 93 selected recognition cases have label crops.
Rule generation and recognition already use these label crops in the current path.
The live cohort does not exercise the whole-image fallback difference.
Local safeguards test the strict missing-label policy.

## Cohorts

| Cohort | Cases per arm | Coverage |
|---|---:|---|
| Augmented catalogue labels | 56 | Three Фантом wines and four Виктор Дравиньи wines |
| Blank controls | 7 | One per selected wine |
| Additional front photographs | 10 | Five source photographs with two conditions |
| Official rule-triggered photos | 20 | Eighteen saved clusters |

The target cases reuse the earlier frozen self-calibration images.
The additional photographs were checked as front photographs.
These photographs have appeared in earlier experiments.
These photographs are excluded from the generation references in this benchmark.
The current combined Виктор Дравиньи cluster has six wines.
The targeted comparison covers four of these wines.

The official evaluation replays the 20 previously triggered cases.
The evaluation restores their exact initial candidate order and scores.
The evaluation keeps the other 75 results unchanged.
Report all-95 accuracy separately from the 20-case subset.
Do not call this replay a complete pipeline run.
The saved historical result is 90/95 overall and 17/20 in the subset.
Fresh paired results are pending.

## Preparation evidence

The snapshot has 57 main label references and 38 additional label references.
The generation cohort has 19 clusters.
Five evaluation photographs were removed from the additional references before any rule request.
The description inputs and description prompts stayed unchanged during this correction.
The first description-phase contract is preserved.
The manifest records the correction.

Ten local safeguard tests pass.
Ruff passes.
The request audit checks the actual transmitted image hashes.
The request audit also checks model identity and frozen source files.
The final accuracy report MUST include generation errors and unresolved cases.

Inspect the actual composited request PNG for visual input checks.
A raw RGBA preview can display RGB values under zero opacity.
Those values do not reach the VLM.
The extra-brut crop has zero-opacity glass between its printed labels.
The actual transmitted PNG makes that region white.
The recorded request hash matches the checked PNG.
The proof is in [crop-preview-check.json](../../../internal/label-only-benchmark-20261011/crop-preview-check.json).
One LAN SAM3 diagnostic confirmed the existing label mask.
No crop or benchmark input changed during this diagnostic.

## Execution limits

Descriptions and recognition use the resident LAN `qwen3.5-9b-nvfp4`.
Rules use the configured QwenCloud `qwen3.8-max`.
Use one LAN request at a time.
Use at most two Cloud requests at a time.
The Cloud payload contains catalogue references, metadata, descriptions, and reviewer notes.
The Cloud payload contains no test photograph, source code, or credential.
Production rules, source images, catalogue vectors, annotations, and services stay unchanged.

Automatic approval review rejected the expanded Cloud payload.
The earlier explicit approval covered seven wines.
A specific approval question covers this expanded benchmark.
Do not run Cloud rule generation before that approval arrives.
