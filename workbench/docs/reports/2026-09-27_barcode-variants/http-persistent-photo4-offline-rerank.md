# Offline rerank quality control

Date: 2026-09-27. This report reads the completed `persistent-photo4` session only.
It makes no request. It measures no latency. It makes no three-second deadline claim.

The counterfactual retains barcode decoding and package preprocessing. It removes
the optional rerank. The existing `barcode-siglip2-512-crop` profile implements this
control for a later sequential HTTP measurement.

| Population | Positive denominator | Before rerank R@1 | After rerank R@1 | Before rerank R@5 | After rerank R@5 |
|---|---:|---:|---:|---:|---:|
| All saved rows | 54 | 44/54 (81.48%) | 45/54 (83.33%) | 54/54 (100.00%) | 54/54 (100.00%) |
| Exclude two annotation-conflict rows | 52 | 43/52 (82.69%) | 44/52 (84.62%) | 52/52 (100.00%) | 52/52 (100.00%) |

Rerank improves top-1 correctness for 1 positive rows.
Rerank harms top-1 correctness for 0 positive rows.
Top-1 changes in 2 rows across all labels.
The ten negative rows have 0 contradictions before rerank and 0 after rerank.
A negative label rejects the named wine. It does not identify the correct alternative.

All 64 responses have HTTP 200, no top-level error, and no degraded step.
Twenty-four rows return a unique barcode answer. These answers do not change.
The other 40 rows have one full-view search. Their saved search order agrees with
the order reconstructed from candidate `explain.base_rank`, or the unchanged rank.
Eighteen rows trigger rerank. The sample contains zero shared-GTIN branches.
No missing base ranking was imputed.

The sensitivity result excludes `q-000483` and `q-000484`. These rows have identical
source bytes and conflicting positive labels. The raw result preserves both labels.
The sample is deliberate. Its accuracy is not a corpus estimate.

Inspect the paired rows, changed-query lists, rejected negative slugs, and hashes in
[the JSON evidence](http-persistent-photo4-offline-rerank.json).
The source is [the saved HTTP session](http-pilot/persistent-photo4.jsonl).
Source SHA-256: `4f63cd6bfb05df8e9685a4e93a1949b9dc3c7a1fecdf3e2aac6b96f8ff1a1639`.
