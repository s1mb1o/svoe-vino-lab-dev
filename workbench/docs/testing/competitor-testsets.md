# Competitor test-set import

Date: 2026-09-30

## Purpose

Use this procedure to rebuild the normalized public competitor test sets.
The procedure keeps verified labels separate from development and uncertain labels.

## Inputs

- Public repository clones: `/Volumes/T7_2TB/2026_LCT_Hackatons_10`.
- Research archive: `/Volumes/T7_2TB/Projects-T7_2TB/2026_LCT_Hackatons/10-Сканер_российских_вин`.
- Lab database: `data/catalog/catalog.sqlite3`.

The importer reads the repositories.
It does not change them.
It writes the generated snapshot below `data/competitor-testsets/`.

## Import

Run this command from `workbench/`:

```bash
~/.venvs/svoe-vino-lab/bin/python scripts/import_competitor_testsets.py \
  --repos-root /Volumes/T7_2TB/2026_LCT_Hackatons_10 \
  --research-root /Volumes/T7_2TB/Projects-T7_2TB/2026_LCT_Hackatons/10-Сканер_российских_вин \
  --db data/catalog/catalog.sqlite3 \
  --out data/competitor-testsets
```

Use `--prepare-only` to make the snapshot without a database write.
Use `--force` only when the Testset page has edited an imported set and the snapshot
MUST replace that edit.

The script rebuilds only the generated `photo/` directories of its managed sets.
It preserves all competitor repositories.
It writes `manifest.jsonl`, `summary.json`, `review-labels.json`, `overlap.json`,
`failures.json`, `source-inventory.json`, and `import-report.json`.

## Evidence rules

- A `scored` row MUST have an exact or verified label.
- A positive `scored` slug MUST exist in the current catalogue.
- A public label conflict for the same source photo moves every conflicting row to
  `provisional`.
- A machine label, development overlap, packshot, same-line label, probable label, or
  unresolved slug MUST be `provisional`.
- An unresolved photo uses `__drawer__` and the label `unusable`.
- The runner MUST NOT treat an unresolved photo as a verified no-match.

## Benchmark

Check `/Users/ashmelev/Admin/GPU_SERVERS.md` and `GPU_TASKS.md` first.
Run one set at a time:

```bash
SAM3_ENDPOINT=http://192.168.86.14:18081/upstream/sam3 \
  ~/.venvs/svoe-vino-lab/bin/python pipeline/embedding_run.py \
  --name siglip2-p512-rot5-seg --set <set-name> --workers 4
```

The command returns `gives no query` for a set that contains only `unusable` rows.
Record this result as an explicit unscored result.
Do not convert these rows to `__null__` to make the command run.

## Verification

Run the importer tests:

```bash
python3 tests/test_import_competitor_testsets.py -v
```

Verify the database rows:

```bash
sqlite3 -header -column data/catalog/catalog.sqlite3 \
  "SELECT set_name, count(*) AS photos FROM test_photo
   WHERE set_name LIKE '%-scored' OR set_name LIKE '%-provisional'
   GROUP BY set_name ORDER BY set_name;"
```

Review the current result in
[`docs/reports/2026-09-30_competitor-testsets.md`](../reports/2026-09-30_competitor-testsets.md).

## Common pipeline benchmark

The importer also creates `competitors-scored-common`.
It deduplicates the scored source rows by original source-photo stem.
It keeps the largest copy when the label is the same.
It refuses conflicting labels.

The 2026-09-30 snapshot contains 77 rows.
It contains 50 positive rows and 27 verified no-match rows.

Run the base and one adaptation with the same command shape:

```bash
SAM3_ENDPOINT=http://192.168.86.14:18081/upstream/sam3 \
  ~/.venvs/svoe-vino-lab/bin/python pipeline/embedding_run.py \
  --name siglip2-p512-rot5-seg --set competitors-scored-common --workers 4

SAM3_ENDPOINT=http://192.168.86.14:18081/upstream/sam3 \
  ~/.venvs/svoe-vino-lab/bin/python pipeline/embedding_run.py \
  --name competitor-kofeinix-ocr --set competitors-scored-common --workers 4
```

Read the complete result in
[`docs/reports/2026-09-30_competitor-pipeline-ablation.md`](../reports/2026-09-30_competitor-pipeline-ablation.md).
The `competitor-*` configurations are local adaptations.
They are not reproductions of private weights or reported competitor metrics.

## Flat set `competitors`

The owner asked for one flat competitor set on 2026-09-30.
The owner selected the rules at 18:58 (`docs/owner-messages.md`).
`scripts/merge_competitor_testsets.py` merges every imported set below
`data/competitor-testsets/` into the set `competitors`.
Then it removes the source sets from the database.
It keeps their directories on disk.

Merge rules:

- Rows with the same SHA-256 or the same source file stem are one photo.
- The largest copy of a photo stays.
- A photo goes to every place that a source set gave it.
  The places include each wine slug, `__null__`, and `__drawer__`.
- `extra.merged_from` of each row holds the source rows of that place.
- Two different labels at one place stop the merge.

The 2026-09-30 merge read 14 sets with 678 rows.
It wrote 236 photos in 323 rows.
The rows are 164 positive, 43 negative (`__null__`), and 116 unusable (`__drawer__`).
65 photos are in more than one place.
The set mixes the scored and the provisional evidence tiers.
A run on `competitors` scores a photo with two places as two queries.
At most one of the two queries can be correct.
Runs skip the `__drawer__` rows.

Run the tests:

```bash
python3 -m unittest discover -s tests -p 'test_merge_competitor_testsets.py' -v
```

A re-run of the importer creates the 14 source sets again.
The merge script refuses to run while the set `competitors` exists.
