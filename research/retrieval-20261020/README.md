# Retrieval research package

[Read the full algorithm reference](../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md).
[Read the compact benchmark results](summaries/README.md).

The package records retrieval without re-ranking.
It contains frozen specifications, algorithm source snapshots, compact metric exports, and provenance.
It does not contain model weights, evaluation photos, masks, accepted answers, or complete result databases.

## Verify from a checkout

Use Python 3.9 or later. No third-party package is required.

```sh
python3 research/retrieval-20261020/verify.py
```

The checker starts no model, service, SSH connection, or GPU job.
It checks all file hashes, 5,432 generated recipes, 39 pooling profiles, exact result recipes, metric arithmetic, leaderboard ordering, and repository links.
It checks summary consistency. It does not independently reproduce predictions or prove global leaderboard optimality without the complete datasets.

## Files

| Path | Content |
| --- | --- |
| [sources/campaign](sources/campaign) | Historical campaign scripts, frozen protocols, enumeration, and audit receipts. |
| [sources/workbench/pipeline](sources/workbench/pipeline) | Matching helper snapshots for geometry, masks, and embedding preparation. |
| [summaries/benchmark-summary.json](summaries/benchmark-summary.json) | Coverage counts, baselines, and all-budget and p512 leaderboard membership. |
| [summaries/configurations.json](summaries/configurations.json) | All 53 exact result recipes. |
| [summaries/metrics.csv](summaries/metrics.csv) | Raw counts for all reported result recipes and controls. |
| [summaries/report-tables.json](summaries/report-tables.json) | All numeric report tables before the source index. |
| [summaries/input-manifest-summary.json](summaries/input-manifest-summary.json) | Input counts and the original 50 MB manifest checksum. |
| [summaries/dataset-inventory.json](summaries/dataset-inventory.json) | Checksums and sizes of unbundled full databases. |
| [provenance/source-manifest.json](provenance/source-manifest.json) | Original source hashes and derived-summary identities. |
| [provenance/report-origin.json](provenance/report-origin.json) | Original report identity and publication-only changes. |
| [package-manifest.json](package-manifest.json) | Committed package file hashes. |
| [tools/export_results.py](tools/export_results.py) | Optional aggregate export from a complete private source campaign. |

## Historical source boundary

Source snapshots preserve their original bytes and hashes.
Some scripts retain historical filesystem and service settings.
These scripts document the exact algorithms and controls.
They need the original runtime configuration and private assets for full inference.
The portable checker does not import the historical runners.
It executes only the pure profile factory and uses a separate standard-library recipe reconstruction.

The published report keeps the benchmark tables and 53 exact recipe JSON blocks unchanged.
Publication changes replace local links and add committed evidence and verification instructions.
The main leaderboards use GX10 only.
The incomplete RTX4090 replay keeps its own baseline.
