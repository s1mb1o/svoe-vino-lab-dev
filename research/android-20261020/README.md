# Android research evidence package

Read the [consolidated research report](../../ANDROID-RESEARCH-AND-RESULTS-20261020.md).
Read the [Android 0.3.0 release record](../../android/docs/releases/0.3.0.md) for the shipped pipeline.

## Contents

- `results.json`: exact counts, request statistics, model conditions, and source identities.
- `observations/`: 23 hard-cohort series and the separate 100-image Eval.zip run.
- `cohorts/my-failed-2.jsonl`: ordered query IDs, image hashes, and accepted-answer-set hashes.
- `source-manifest.json`: original raw source file sizes and SHA-256 values.
- `provenance/release-contract.json`: public APK identity, pack identity, build checks, and observed merged permissions.
- `package-manifest.json`: hashes and sizes of this package's committed files.
- `export_results.py`: read-only source export. It starts no model or device request.
- `verify.py` and `test_verify.py`: portable summary verification and focused negative tests.

The hard cohort has 668 assignments and 627 distinct image hashes.
The package has 15,364 hard-cohort observations across 23 result series.
Thirteen Base series have separate measured requests.
Ten SO400M series reuse one shared-query campaign. Their full-run request times are shared.
Do not report the shared time as independent latency for each recipe.

Each observation keeps the query ID, image hash, Top-1/5/10 acceptance flags,
request time, error flag, and a hash of the predicted Top-1 slug.
The Eval.zip observations keep only the corresponding accepted flag and request time.
The original source archive retains the full ranked predictions and reference answers.
The export recomputed acceptance from those answers and checked the saved audit.
The committed flags are derived evidence. They are not independently verifiable ground truth.

No image path, reference answer, raw vector, model weight, APK, credential, or private owner message is included.
The original cohort is development-selected. It is not an independent validation set.
Errors stay in every denominator. The DIS-1024 USB continuation stays in the metadata.
The earlier full `my` reports remain separate committed component evidence.

## Verify without a device

Use Python 3.9 or later. No third-party dependency is required.

```sh
python3 research/android-20261020/verify.py
python3 -m unittest discover -s research/android-20261020 -p 'test_*.py' -v
```

The checker verifies package hashes and ordered cohort membership.
It recalculates all 23 series' Top-k counts, errors, medians, inclusive P95, and maxima.
It checks six paired Top-1 comparisons and the complete standard/custom parity hashes.
It keeps Eval.zip's 86/100 quality result and `FAIL` comparison status explicit.
It does not access ADB, SSH, a network service, a model, or a GPU.
It does not prove model accuracy without the omitted reference answers and images.

## Re-export saved evidence

The original source files MUST be present. The destination MUST NOT exist.
Use a new destination. Do not overwrite the committed package or a previous export.

```sh
python3 research/android-20261020/export_results.py \
  --artifacts /Volumes/Storage/svoe-vino-final/artifacts \
  --eval-run /Volumes/Storage/svoe-vino-final/code/chtozavino-tests/runs/android-0.3.0-dis768-custom-20261020 \
  --out /path/to/new/android-research-export
```

The command only reads saved records. It preserves every raw source byte.
The source manifest uses artifact-relative paths. `eval-run/` refers to the supplied Eval.zip run directory.
The source hashes support provenance checks when the original archive is available.
They do not authenticate a source archive that is not available.
