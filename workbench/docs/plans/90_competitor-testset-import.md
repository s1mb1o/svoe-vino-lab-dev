# Plan 90: competitor test-set import

Date: 2026-09-30

## Goal

Import each usable public competitor query set into the lab.
Keep trustworthy evaluation rows separate from exploratory rows.
Run `siglip2-p512-rot5-seg` on each non-empty imported set.
Report results without combining incompatible evidence tiers.

## Evidence tiers

Each competitor source MUST use the competitor name as the test-set prefix.
Each source MAY produce two test sets:

- `<competitor>-scored` contains exact or independently verified `wine_slug` labels.
- `<competitor>-provisional` contains machine labels, packshots, training overlap,
  same-line labels, ambiguous labels, or labels that do not resolve to the current
  catalogue.

An image MUST NOT enter `scored` only because its parent directory resembles a slug.
An image with an unknown target slug MUST stay in `provisional`.
Identical image bytes MUST keep one stored file and MAY appear in two source sets only
when the report states the overlap.

## Snapshot

The importer MUST read local public repository clones.
It MUST create a local normalized snapshot before the lab import.
The snapshot MUST contain source repository, commit SHA, source path, original label,
normalized slug, tier, tier reason, SHA-256, dimensions, and file status.
The snapshot MUST use hard links where the source and target filesystems permit them.
It MUST fall back to a file copy.
The importer MUST not change a competitor repository.

## Source adapters

The first version MUST use explicit adapters for inspected repository formats.
It MUST not infer ground truth from arbitrary file names across all repositories.
An adapter MUST state its confidence rule and known leakage risk.

## Import and benchmark

The normalized snapshot MUST use the existing `review-labels.json` format.
The existing `pipeline/import_testset.py` MUST perform the database import.
The import MUST not need a schema change.
The benchmark MUST create a separate run per imported test set.
The report MUST show exact Top-1, Top-5, positive coverage, unknown handling, latency,
duplicate overlap, and exclusions when the run artifacts provide them.
`provisional` results MUST be labelled unscored even if the runner calculates metrics.

## Acceptance

- The source inventory lists each inspected competitor repository with a decision.
- Every imported row has provenance and a tier reason.
- Every stored image opens with Pillow and matches its recorded SHA-256.
- Exact slugs in `scored` exist in the current catalogue.
- Duplicate images are reported across competitor sets.
- Tests cover tier assignment, unknown slugs, duplicate files, and snapshot replay.
- Each non-empty imported set has a completed or explicitly failed benchmark run.
- `ChangeLog.md`, `SMOKE_TESTS.md`, `README.md`, and the final report are updated.

## Result

Completed on 2026-09-30.

- The importer inspected 57 repository clones and imported 601 rows from 10 competitors.
- It created 13 test sets.
- Image validation found 0 missing or invalid files.
- The duplicate audit found 100 shared SHA-256 values.
- The label audit moved nine conflicting source photos out of `scored`.
- Ten benchmarkable sets completed.
- Three all-unusable sets returned the expected `gives no query` result.
- The final evidence and recommendations are in
  [`docs/reports/2026-09-30_competitor-testsets.md`](../reports/2026-09-30_competitor-testsets.md).
