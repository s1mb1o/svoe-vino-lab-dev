# Barcode speed comparisons

Date: 2026-09-27.
Status: scan and cached crop comparisons are complete. Full bulk and fresh-photo HTTP comparisons are pending.

## Scope and denominators

The baseline contains 2228 query rows and 1851 unique image digests.
There are 1644 positive rows and 584 negative rows.
All five completed scan variants cover all 2228 rows.
Each row forces a new scan, including repeated source bytes.
All five variants have zero decoder errors and zero incorrect unique wine matches.

## Completed scan comparisons

| Variant | Correct unique wine hits | Median ms | p95 ms | p99 ms | Full-set wall s | Rows/s |
|---|---:|---:|---:|---:|---:|---:|
| `full` | 24 | 326.7 | 638.1 | 910.8 | 816.9 | 2.73 |
| `whole1` | 20 | 60.3 | 160.1 | 276.8 | 169.6 | 13.14 |
| `whole` | 23 | 67.2 | 181.4 | 280.8 | 184.0 | 12.11 |
| `tiles3` | 23 | 168.6 | 335.2 | 546.2 | 426.3 | 5.23 |
| `photo4` | 24 | 124.0 | 257.5 | 421.9 | 325.2 | 6.85 |

`full` uses two whole-photo passes, then 3 by 3 and 5 by 5 tiles.
`whole1` uses one whole-photo pass.
`whole` uses two whole-photo passes.
`tiles3` adds only 3 by 3 tiles to the two whole-photo passes.
`photo4` keeps the full scan and schedules tile decoding on four threads for one photo.
It does not process four photos at the same time.

The two-pass whole-photo variant is 4.44 times faster by full-set wall time than `full`.
It retains 23 of the 24 barcode wine matches.
Adding 3 by 3 tiles does not restore the remaining match in this set.
The missing case is `q-000955`,
`fanagoriya-brule-frizzante-brut-rozovoe-merlo-igristoe-bryut-rozovoe-115/07_manual.jpg`.
Its full-scan code is EAN13 `4603040021149`.
The full pipeline can still recognize that photo through embeddings after a barcode miss.
That fallback has not yet been measured in this comparison.

The four-thread per-photo variant preserves all 2228 match decisions.
Its full-set wall time is 2.51 times faster than `full`.
It executes two extra native calls because already-running tile work must finish.
Its maximum photo time is 2805.45 ms, compared with 2201.76 ms for `full`.
Parallelism improves the measured median and p95 but does not guarantee a short maximum.

One whole-photo pass loses four known hits: `q-000819`, `q-000955`, `q-001661`, and
`q-002159`. The second pass restores three of those hits for little additional total
wall time. Keep `whole` and `photo4` as the leading candidates for the next comparisons.
This is a candidate selection, not a production configuration change.


## Barcode cache comparisons

All four cache variants preserve the 2228 baseline match decisions with zero errors.
Cold variants force a fresh scan for every row, including the 377 repeated digests.
Warm variants read 2228 cached results and make zero native decoder calls.

| Cache state | Query workers | Full-set wall s | Rows/s | Median row ms | p95 row ms |
|---|---:|---:|---:|---:|---:|
| cold | 1 | 507.776 | 4.39 | 225.50 | 328.61 |
| warm | 1 | 7.483 | 297.76 | 3.04 | 6.01 |
| cold | 4 | 148.194 | 15.03 | 265.66 | 378.26 |
| warm | 4 | 2.945 | 756.45 | 4.15 | 11.53 |

Four query workers improve measured cold-scan throughput by 3.43 times.
They improve warm-cache throughput by 2.54 times.
The warm four-worker run is 2.945 seconds for the whole set's barcode step.
It is not 2.945 seconds for complete recognition of the full set.
It also does not predict recognition latency for a new demo image.

The cold one-worker cache run is faster than the earlier uncached `full` run,
even though the native call count and answers match. The experiment cannot attribute
this difference to caching because cold reads are disabled. Host contention changed:
load averages were 46.82/37.10/50.53 at launch and 14.82/18.57/24.88 at 02:13.
A short repeated scan comparison follows to check the timing direction under closer
conditions. Do not interpret stage-1 ratios as controlled causal estimates.

## Limits

These measurements concern barcode decoding only.
They do not establish a 3-second total recognition response for a new photo.
The host has 12 logical CPUs and had high load when the experiment started.
Variants ran sequentially. Different background load can affect their timing ratios.
Repeat leading variants under comparable load before a final timing recommendation.

The harness also writes `estimated_total_ms` from baseline non-barcode times.
Those values reuse model-cache results and omit per-request startup and HTTP work.
Do not use those estimates as demo measurements.

The full bulk and fresh-photo sequential HTTP comparisons remain pending.
No final bulk or demo setting is selected yet.


## Repeated timing control

The first 64 rows were measured again after stage 1, with one variant at a time.
Full scanning took 13.600 s; two whole-photo passes took 3.057 s; per-photo four-thread
scanning took 6.230 s. The directions match the full-set result.
The control preserves all 64 match decisions and has zero errors.
It contains two barcode hits. It is not a representative corpus-quality sample.
The control and host observations are saved in `stage1-repeat64/` and
`stage1-repeat64-process.json`.


## Cached crop coverage

Stage 2 prepared all 1851 unique source images without model requests.
The saved regions have this coverage:

| Region | Available unique images | Missing cache | No detection or baseline box |
|---|---:|---:|---:|
| package | 1827 | 0 | 24 |
| bottle | 433 | 1410 | 8 |
| label | 441 | 1410 | 0 |
| barcode | 86 | 1410 | 355 |

The detection cache covers only 441 of 1851 unique images.
A missing cache is not evidence that SAM3 would miss a region.
Standalone crop recall therefore needs its availability denominator.
Whole-photo-first fallbacks still test every source image.
The median cached preparation time was 58.18 ms; p95 was 217.89 ms.
Preparation recovered all four region types together. It includes no fresh segmentation.
All eight crop variants are complete. Each result contains 2228 query rows and 1851 unique-image records. Missing crop regions stay in the denominator. Only available standalone regions have measured decode time.


The completed package and bottle crop scans expose selection bias in this offline
comparison. All 24 baseline barcode-hit rows lack a saved package rectangle because
barcode recognition bypassed segmentation. For those same rows, bottle detection has
23 missing cache records and one missing detection. A zero standalone package or
bottle hit count therefore cannot establish that cropping loses readable barcodes.
Before selecting a demo crop strategy, obtain fresh segmentation on the selected demo
sample, including all 24 known barcode-hit rows. Measure that cost inside the request.


## Completed cached crop comparisons

| Variant | Measured unique images | Correct code hits | Incorrect hits | Median wall ms | p95 wall ms |
|---|---:|---:|---:|---:|---:|
| `package` | 1827 | 0 | 0 | 28.21 | 95.92 |
| `bottle` | 433 | 0 | 0 | 27.93 | 81.99 |
| `label` | 441 | 1 | 0 | 42.37 | 77.98 |
| `barcode` | 86 | 1 | 0 | 23.98 | 106.55 |
| `whole-package` | 1851 | 23 | 0 | 66.55 | 147.84 |
| `whole-bottle` | 1851 | 23 | 0 | 47.36 | 117.27 |
| `whole-label` | 1851 | 23 | 0 | 48.20 | 118.38 |
| `whole-barcode` | 1851 | 23 | 0 | 46.73 | 117.74 |

All eight variants have zero decoder errors. Every whole-photo-first variant keeps the
same 23 known barcode answers. No available crop restores the remaining full-scan hit.
The standalone label and barcode regions each find one known hit. Their incomplete
availability prevents a comparison of recall on all new images.

The wall distributions above measure image loading and decoding. They exclude the
separate cached geometry preparation and fresh SAM3 inference. Each unique image is
scanned once. These measurements are not full bulk throughput or complete demo latency.

The next fresh-photo comparison includes opt-in `fresh-bottle`, `fresh-label`,
`fresh-barcode`, and whole-photo-first forms. Every needed segmentation uses a fresh
SAM3 request. Whole-photo-first forms skip that request only after a unique code match.
The request wall time includes segmentation, geometry selection, decoding, and any
later embedding or rerank work. Later pipeline segmentation is not reused by this
experiment. Its repeated cost stays in the measurement.


## Full bulk comparison in progress

The first full-pipeline comparison started at 02:37:42 with one worker and an empty
barcode cache. The set has 2228 rows and 1851 unique digests. Normal SAM3 and VLM
caches stay enabled. Query embeddings have no client response cache.
The first embedding request took 42.054 s while SigLIP2-512 was initially unloaded.
The next request took 160.3 ms. Keep remote cold startup separate from steady-state
results. Both remain part of full process time. Read `bulk-startup-observation.json`.

The full bulk sequence is cold-1, warm-1, cold-4, then warm-4. Results are pending.
The later fresh-photo HTTP experiment uses disabled recognition-cache reads and a
new upload for every sequential request. Its real socket control passed four requests
with fake inference. The 3-second target is not established yet.


## First complete bulk result

Cold barcode cache with one query worker completed at 02:51:57.
The process wall time was 855.785 s (14 min 16 s).
The harness wall time was 854.498 s. Backend construction is included in harness time.
The other 1.288 s includes process launch, imports, validation, hashing, and reporting.
It is not a pure import-duration estimate. The first cold embedding request stays
in both complete totals.

All 2228 query rows and 1851 unique image digests are present. There are zero errors,
zero degraded rows, zero native decoder errors, and no input drift.
The 377 repeated digests used barcode cache records. The other 1851 rows missed that
cache. The decoder made 128004 native calls.
All predictions, candidate orders, truth ranks, and outcomes match the baseline.
Positive top-1 is 1392/1644 (84.67%). Positive top-5 is 1595/1644 (97.02%).
The 584 negative constraints include 90 false matches to the excluded wine at rank 1.

The first run is faster than the older baseline, but the host load and model cache
state differ. Do not attribute that complete difference to the barcode cache alone.
The paired warm-1 comparison started at 02:53:19 and is still running.
Four-worker comparisons and fresh-photo HTTP results remain pending.
Read `bulk-comparison-after-cold-1.md` and `bulk-cold-1-validation.json`.


## Paired one-worker cache comparison

Warm-1 completed at 03:01:01 with exit 0. Both one-worker runs have complete coverage,
zero errors, and identical predictions, candidate orders, truth ranks, and outcomes.
The warm run used all 2228 barcode records and made zero native decoder calls.

| Barcode cache | Query workers | Process wall s | Harness wall s | Barcode cache hits | Native calls |
|---|---:|---:|---:|---:|---:|
| cold, natural duplicate reuse | 1 | 855.785 | 854.498 | 377 | 128004 |
| warm | 1 | 462.249 | 460.973 | 2228 | 0 |

The measured complete warm run took 7 min 42 s. Its barcode trace cost was only
3.950 s across the full set. The remaining work is substantial:

| Step | Cold-1 total s | Warm-1 total s |
|---|---:|---:|
| `barcode` | 360.213 | 3.950 |
| `sam3-package` | 167.376 | 169.457 |
| `embed` | 143.335 | 100.698 |
| `cluster_rules` | 107.960 | 109.052 |
| `view` | 53.048 | 53.647 |
| `input` | 15.907 | 17.544 |
| `search` | 3.368 | 3.314 |
| `score` | 2.270 | 2.313 |

These are sums of `trace.steps[].ms`. The package step includes cached mask loading
and crop processing. Cached model responses do not remove image preparation.
The cold-1 embedding total includes the first 42.054 s request.
Cached VLM response durations inside output fields are excluded from the sums.
The same sums from a four-worker run will not equal its elapsed wall time.

Cold-4 started at 03:02:33 in child PID 19976 and supervisor PID 19974.
Warm-4 and fresh-photo HTTP comparisons remain pending.


## Complete bulk comparison

All four variants completed with exit code 0.
Every variant contains 2228 query rows and 1851 unique image digests.
Every variant has zero errors, degraded queries, and input drift.
Normal SAM3 and VLM response-cache reads stayed enabled.
Query embedding requests still ran.

| Barcode cache | Query workers | Process wall s | Harness wall s | Barcode cache-hit rows | Native decode calls |
|---|---:|---:|---:|---:|---:|
| Cold | 1 | 855.785 | 854.498 | 377 | 128004 |
| Warm | 1 | 462.249 | 460.973 | 2228 | 0 |
| Cold | 4 | 232.358 | 231.029 | 332 | 131154 |
| Warm | 4 | 129.634 | 128.303 | 2228 | 0 |

The cold four-worker run has 45 additional cache-miss rows across 44 repeated digests.
Those rows account for 3150 additional native calls.
Concurrent scans before the first cache write are the inferred cause.
The traces do not record the overlap directly.
The warm four-worker run has no missing cache entries and makes no native calls.

Use four query workers and enabled response caches for repeated bulk runs.
Keep the full barcode pass strategy to preserve all 24 known barcode answers.
Do not nest four decoder workers inside each of four query workers.
The earlier baseline took 2507.100 s.
Host load, model residency, and response-cache state changed between measurements.
Do not attribute the full difference from that baseline to barcode caching.
The first cold-one-worker query includes a 42.054 s embedding request.
That request includes startup, transfer, and inference costs.
It is not an isolated model-load measurement.

These bulk times do not establish latency for a new demo image.
The sequential HTTP pilot started at 03:15:13 MSK.
Its child PID is 62006. Its supervisor PID is 62005.
Its frozen selection contains 64 rows and 61 unique image digests.
The selection contains 54 positive and 10 negative rows.
All 24 known barcode-hit photos are oversampled.
Each request has a new upload directory and disabled response-cache reads.
The measurement includes upload storage and step-view construction.
The first fresh rerank can include a cold Qwen NVFP4 load.
The Qwen model was unloaded at preflight; SAM3 and SigLIP2-512 were ready.
The harness measures deadline outcomes. It does not enforce a hard 3-second timeout.


## Cold VLM failure and retained resume

The first HTTP attempt stopped at 03:20:22 MSK with exit code 2.
The first three responses took 1531.448 ms, 1275.510 ms, and 2630.753 ms.
The fourth query, `q-000078`, triggered the first fresh rerank.
Qwen NVFP4 was unloaded before the pilot and was still starting at 03:18:47.
The child watchdog expired. The route returned HTTP 503 after 300700.691 ms.
This is a failed recognition response, not a successful response after 3 seconds.
The full HTTP error response arrived. Its transport time is not censored.
The raw backend-stage timings are unavailable for that failed child.
Do not assign its full elapsed time to ZXing.
The recorded model startup supports cold VLM initialization as the cause of the wait.
It does not provide an exact isolated model-load duration.

Both local processes exited. The temporary HTTP server closed.
At 03:21:13, the gateway reported Qwen ready.
Direct vLLM metrics showed zero running requests and zero waiting requests.
A fresh preflight found 45.83 GiB available and all required models ready.
SAM3 and vLLM queues were empty.
The pilot resumed at 03:22:09 in child PID 84866 and supervisor PID 84865.
Read `http-pilot-resume-1-process.json` and `http-pilot-resume-1.log`.
The command uses `--resume` and the unchanged manifest.
It skips all four saved rows, including the failed row.
Keep that failure in every raw pilot denominator.
New rows have new upload and cache directories.
New requests are succeeding.
Do not present the after-first subset as warm only because it follows the first row.

Model preparation is required before a 3-second demo.
The comparison still needs all four decoder variants and both backend lifetimes.
The benchmark does not implement a hard 3-second timeout.
No service was stopped or restarted.


## First complete HTTP session

The `process-full` session contains all 64 selected rows and 61 unique digests.
It includes the retained cold-model HTTP 503 observation.
There are 63 successful responses and one failed response.
The HTTP median is 1498.637 ms. The p95 is 6700.459 ms.
45 of 64 complete responses arrive within 3 seconds.
35 of 54 positive rows receive a correct top-1 answer within 3 seconds.
Excluding the two conflicting positive labels gives 35 of 52.
All 24 selected barcode-hit rows receive correct answers within 3 seconds.
Among the other 40 rows, 21 responses arrive within 3 seconds.
Among their 30 positive rows, 11 receive correct answers within 3 seconds.
These fractions describe the oversampled pilot only.
They are not corpus estimates.

18 successful responses exceed 3 seconds in addition to the cold-model failure.
16 of those 18 responses execute `cluster_rules`.
For the 17 successful rerank observations, the median step time is 2172.3 ms.
For 63 successful barcode observations, the median is 199.7 ms and p95 is 592.9 ms.
For 39 fresh package-segmentation observations, the median is 725.4 ms.
The failed child has no usable stage timings and is excluded from stage distributions.
It remains in all raw response and quality denominators.

The remaining seven sessions still need completion.
The condition for the planned existing as-is profile diagnostic is satisfied.
Run that diagnostic after the required pilot and fresh-crop diagnostic.
Do not change the production profile.
See `http-process-full-observation.json` and
`http-pilot-report-after-process-full/http-comparison.md`.


## Complete eight-cell HTTP pilot

The pilot completed at 03:40:07 MSK. Both resumed process IDs exited.
All eight sessions contain 64 rows and 61 unique image digests.
All 512 request cache directories are distinct.
There are 511 successful responses and one retained cold-model HTTP 503.
The failed q-000078 observation remains in process-full.
Every source fingerprint matches the launch manifest.
See `http-pilot-validation.json` and `http-pilot-report-final/http-comparison.md`.

| Backend lifetime | Decoder | Median HTTP ms | p95 HTTP ms | Responses within 3 s /64 | Correct within 3 s /54 positive | Top-1 correct /54 |
|---|---|---:|---:|---:|---:|---:|
| process | full | 1498.6 | 6700.5 | 45 | 35 | 44 |
| process | whole | 1343.5 | 6575.6 | 45 | 34 | 44 |
| process | photo4 | 1404.0 | 6497.0 | 45 | 35 | 45 |
| process | whole-fresh-barcode | 1970.4 | 7391.5 | 38 | 32 | 45 |
| persistent | full | 1037.1 | 5936.1 | 49 | 38 | 45 |
| persistent | whole | 877.6 | 5812.9 | 51 | 38 | 44 |
| persistent | photo4 | 922.5 | 6074.8 | 50 | 38 | 45 |
| persistent | whole-fresh-barcode | 1552.3 | 6841.2 | 45 | 35 | 45 |

These are oversampled pilot results. Do not use the fractions as corpus estimates.
The linked report gives hit/non-hit strata and the 52-positive annotation sensitivity.
Persistent mode reduces process startup cost but still misses many deadlines.
Fresh barcode segmentation recovers the one whole-photo miss. It adds no quality over photo4.
Its extra segmentation cost reduces the number of timely responses.
Offline persistent-photo4 reconstruction gives 44/54 top-1 before rerank and 45/54 after.
A measured control with the same crop and no rerank remains queued.

The 24-hit fresh-crop diagnostic started at 03:42:03 in child PID 55767 and supervisor PID 55766.
Its fresh-bottle, fresh-label, and fresh-barcode sessions run sequentially.
The selection fingerprint matches demo-selection-24.json.
Wait for its terminal artifacts and exited processes before the next comparison.
