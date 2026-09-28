# 70 — Remove the legacy test-set stages

Date: 2026-09-28.
Status: implemented. The owner selected focused removal on
2026-09-28T07:38:08+0300.

## Goal

Remove `scripts/01_search.py` through `scripts/09_apply_moves.py` from
`svoe-vino-lab`. Keep the current lab server and the old JSON review tool functional.

## Requirements

1. Delete the nine numbered stage scripts.
2. Delete `scripts/run_pipeline.py` and `scripts/finalize.sh`. They only drive the
   deleted stages.
3. Preserve the wine-identity VLM prompt, answer parser, cached backend, and backend
   configuration logic that tests and `scripts/bench_vlm_models.py` use.
4. Put the preserved logic in `pipeline/wine_identity_vlm.py`.
5. Do not import code from the sibling `svoe-vino-testset` repository.
6. Remove commands and smoke tests that execute a deleted script.
7. Replace current code and configuration comments that name a deleted script.
8. Keep historical ChangeLog, ResearchLog, review, and plan statements unchanged when
   they describe work that occurred before this cleanup.
9. Do not change a database schema or restart the lab server.

## Implementation

1. Copy the reusable VLM logic from `scripts/04_verify.py` to
   `pipeline/wine_identity_vlm.py`.
2. Remove the dependency on `scripts/common.py` from the reusable logic.
3. Update the benchmark and unit tests to import `wine_identity_vlm`.
4. Delete the numbered scripts and their two drivers.
5. Update the old review tool text to use its `Apply` action for moves and copies.
6. Describe `variant_groups_file` as an input file. Do not name a removed generator.
7. Remove obsolete README commands and smoke tests.
8. Record the change in `ChangeLog.md`.

## Verification

1. `tests/test_model_cache.py` passes.
2. `tests/test_vlm_config.py` passes.
3. The complete unit-test suite passes.
4. No current source file, configuration file, README command, or smoke test names a
   deleted script.
5. `git diff --check` passes.

## Result

The implementation deletes the nine stages and their two drivers. The benchmark and
tests use `pipeline/wine_identity_vlm.py`. The old review tool keeps its Apply action.
The 69 focused tests pass. `git diff --check` passes.

The complete suite ran 1,298 tests. It passed 1,292 tests, skipped 5 tests, and reported
one environment error. The shell sets `SAM3_ENDPOINT` to port 18082, but the production
client uses the required port 18081. The affected nine-test module passes when it uses
port 18081. This error is not in a file changed by this plan.
