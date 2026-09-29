# Offline label comparison preparation

Prepared on 2026-09-27 at 04:28 MSK from the completed reference run.
The inspection did not read the active label run.
The reference run is `2026-09-27T011711Z-lab-barcode-rerank-siglip2-512-crop-my`.
Wait for complete validated artifacts from both runs before paired analysis.

## Reference counts

The reference contains 2228 query rows and 1851 image digests.
It has 1644 positive rows and 584 negative rows.
R@1 is 1392 of 1644. R@5 is 1595 of 1644.
The forbidden negative top-1 count is 90 of 584.
Recorded run wall time is 133.8 seconds.
`metrics.latency_ms.comparable` is false.
These timings describe a cache-enabled bulk run with four workers.
They do not establish sequential fresh-photo latency.

## Trace fields

The `barcode`, `sam3-package`, and `sam3-label` steps use `step.cached`.
All 2228 reference barcode steps have `cached: true`.
Only 24 reference barcode steps have `out.mode: answer` and a unique `out.hit`.
The remaining 2204 rows execute retrieval.
The reference has 2144 `sam3-package` steps with `cached: true`.
Its other 60 package steps have `cached: null` and `out.rule: alpha`.
Those 60 steps need no SAM3 request. Do not count them as cache misses.

The `cluster_rules` step uses `step.out.cached`.
All 585 reference rerank steps have `out.cached: true`.
There are 518 `sheet` results and 67 `verdict` results.
This flag describes the VLM response cache.
The inner label SAM3 request has no separate trace step.
Do not infer its SAM3 cache-hit count from the VLM cache flag.

The `view` and `search` steps use `step.view` with `full` or `label`.
A skipped view has `step.skipped`.
`sam3-label.out.found` records label geometry availability.
One `embed` step has `out.views: [full]` or `out.views: [full, label]`.
This step batches tower inputs. It has no cache flag or separate per-tower timing.
Query embeddings are uncached.
Count tower membership and searches. Do not invent embedding cache counts.

Use `trace.steps[].ms` for recorded step costs.
Do not sum `candidate.explain.ms`, which can contain a previous cached inference time.
Summed step times from four workers do not equal elapsed run wall time.

## Paired quality procedure

After both runs pass terminal validation, write a new queue-summary snapshot.
The existing summary reports differences between rounded aggregate recalls.
For exact paired differences, join `results.jsonl` on `query_id`.
Require equal `image_sha256`, `image_path`, `slug`, `label`, and `truth` values.
For positive rows, an R@k success has a non-null `rank_of_truth` no greater than k.
Report gained and lost query IDs separately for k equal to 1 and 5.
For negative rows, a forbidden result has `predicted_slug == slug`.
Report removed and introduced forbidden predictions.
Do not describe every other negative prediction as a correct recognition.
Preserve the full row and digest denominators.

The saved reference coverage has 2051 full-view wines and 2047 label-view wines.
Its index has 4054 current items, 127 missing items, and two failed items.
Compare saved coverage before attributing a quality change to the tower design.
Cache flags alone do not establish equal cache warmth.
