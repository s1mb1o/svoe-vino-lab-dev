# Profile latency investigation

Date: 2026-09-27T00:51:26+03:00

## Owner request

```text
why profile so slow?
```

The screenshot shows `barcode-rerank-siglip2-512-crop`, set `my`, 424 of 2228 photos, and 9 min 45 s.

The investigation reads the job log, result traces, and source code.
The investigation does not change the running job.

## Evidence

The run ID is `2026-09-26T213857Z-lab-barcode-rerank-siglip2-512-crop-my`.
The source files are `work/run-jobs/barcode-rerank-siglip2-512-crop/job.log`
and `runs/2026-09-26T213857Z-lab-barcode-rerank-siglip2-512-crop-my/results.jsonl`.
The analysis uses the first 424 complete result records.
The job log records `workers: 1`, `use_cache: true`, and `use_barcode: true`.
The sum of recorded query latency is 583.484 seconds.
This sum agrees with the screenshot elapsed time of 585 seconds.
These records contain no final query error.

| Step | Count | Total seconds |
|---|---:|---:|
| Barcode scan | 424 | 189.538 |
| Cluster rerank, including label preparation | 165 | 116.859 |
| First embedding request, including failures and retries | 1 | 102.063 |
| Package crop processing | 419 | 93.971 |
| Other embedding requests | 418 | 35.361 |
| Image load | 419 | 14.912 |
| Embedding image preparation | 419 | 26.654 |
| Catalogue search | 419 | 2.912 |
| Score calculation | 419 | 1.016 |

The small remaining difference is wrapper work and timer rounding.
Use `trace.steps[].ms` for this calculation.
Do not sum the stored VLM response duration.
A cached VLM response retains the duration of the original inference.

## Causes

1. The run processes one photo at a time.
   `pipeline/embedding_run.py:421` sets the embedding default to one worker.
   `pipeline/benchmark.py:259` uses a thread pool only when `workers > 1`.
2. Barcode scanning has no result cache.
   Only 5 of the 424 photos returned a unique barcode match.
   A scan without a unique match runs two binarizers on the full image and 34 tiles.
   This produces up to 70 decoder calls per photo.
   Read `pipeline/barcode.py:174`, `:206`, `:240`, and `:310`.
3. The first embedding call took 102.063 seconds.
   Two attempts returned HTTP 500 from llama-swap.
   Both responses reported `upstream command exited prematurely`.
   The later 418 embedding calls averaged 84.6 milliseconds.
   The cause of the upstream process exits was not investigated.
4. A model cache hit does not skip image preparation.
   All 411 package steps that called SAM3 used cached responses.
   The other 8 package steps used the alpha path.
   `pipeline/derive.py:199` encodes a PNG before the SAM3 cache lookup.
   The cached path still decodes and resizes masks.
   `pipeline/derive.py:349` and `:358` apply mask smoothing and build the crop.
   The crop profile then uses the resulting box.
5. The rerank step ran for 165 photos.
   Its VLM response cache contained 157 answers.
   The 157 cached rerank steps still took 82.371 seconds in total.
   The 8 uncached rerank steps took 34.489 seconds in total.
   `pipeline/cluster_rerank.py:337` reopens the image and prepares the label crop.
   The VLM cache lookup occurs later in `pipeline/label_rules.py:439`.
6. Query embeddings have no client response cache.
   `pipeline/build_embeddings.py:78` sends an embedding request on each call.
   The setting `Use caches` does not skip this request.

## Possible improvements

- Test `workers = 4` in the existing Run dialog.
  Measure the speed and error rate before selecting a new default.
  This investigation did not measure parallel throughput.
- Cache decoded barcode results by image digest and decoder options.
  Keep the catalogue lookup separate so that code-map changes remain effective.
- Cache prepared package crops and label crops by image digest and processing settings.
  Include the crop rule version in the cache key.
- Investigate the upstream embedding process exits separately.

The investigation did not run inference, restart a service, stop the job, or change code.

## Authorized implementation

Owner request of 2026-09-27T01:01:41+03:00:

```text
add barcode scan cache also. And support a few workers (4).
```

Store barcode scan stages in the existing atomic JSON cache.
The cache key includes the source bytes, decoder options, decoder version, Pillow version,
and scan algorithm revision.
A stage stores decoded codes only.
The current run performs the wine lookup again.
A unique code can stop the scan before all tiles are read.
A later run resumes an incomplete scan when the cached codes no longer give a unique hit.
Cache successful empty results too.
Do not cache decoder failures.
The existing `Use caches` setting controls cache reads.
Concurrent cache writes must leave a complete JSON record.
Set the profile worker default to 4.
Keep an explicit worker override and the defaults of other profiles.
Validate cache reuse, lookup changes, cache bypass, invalidation, failure recovery,
concurrent calls, and worker overrides with local tests.

## Implementation result

The barcode cache and the profile worker default are implemented.
The cache tests cover changed lookups, partial scans, empty scans, bypass, invalidation,
malformed records, decoder failures, concurrent writes, and trace fields.
The worker tests verify actual concurrency of 4 and overrides of 2 and 1.
The barcode tests pass: 55 tests with the installed zxing-cpp decoder.
The worker and runner tests pass: 107 tests.
A review found an invalid cache-kind validation case.
The validation was fixed.
All 12 cache tests passed again after that fix.

A control used 14 real test photos and a temporary cache.
Four photos produced a unique barcode hit.
The first scan took 8.4754 seconds.
The second scan used four workers and took 0.0767 seconds.
All 14 second scans used the cache.
The decoded codes and wine matches were identical.
This control measured barcode processing only.
It did not measure the throughput of the complete inference pipeline.

Port 8168 restarted from PID 2358 to PID 96402.
`GET /api/dataset` returned HTTP 200.
`GET /api/run-configurations?set=my` reports the profile as runnable with 4 workers.
The existing benchmark kept PID 11418 and its original worker count of 1.
It had completed 1512 photos after the restart.
The changes apply to new runs.
