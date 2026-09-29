# Barcode and recognition latency: final recommendations

Date: 2026-09-27. All measurements below are complete.
This report uses saved artifacts only. The report starts no measurement or inference.
The parent task validated the bulk and HTTP completion artifacts.

## Recommended settings

For repeated bulk runs, use the barcode cache and four query workers with remote
embedding profiles. Keep the full barcode scan. The measured warm run processed
2228 query rows in 129.634 seconds. Its predictions were unchanged from the baseline.
Use one query worker for local embedding profiles under the rerun policy.

For sequential demo requests, use a persistent backend and the `photo4` barcode
variant as the implementation candidate. `photo4` preserves all 24 known barcode
hits. It uses at most four tile tasks inside one image. Do not place four decode
threads inside each of four bulk query workers.

The current measured candidate for the three-second demo target is
`barcode-siglip2-512-as-is` with persistent `photo4`. All 64 selected HTTP requests
finished within three seconds. It returned 43 correct top-1 answers among 54 positive
rows. The crop/rerank reference returned 45, but only 38 were correct within three
seconds. The as-is result includes one forbidden top-1 on ten negative constraints.
This is a latency and quality tradeoff on a small selected sample.

The isolated alternative `barcode-siglip2-512-crop` removes rerank but keeps the same
query package crop. It returned 44 correct top-1 answers. It returned 40 correct
answers within three seconds. Six of its 64 requests still exceeded three seconds.
Use this alternative when retaining package cropping matters more than the observed
deadline fraction. None of these measurements establishes a hard deadline guarantee.
Persistent demo execution and `photo4` remain experimental harness behavior here.
This report does not claim that production already implements either behavior.

## Why the original run was slow

The screenshot captured 424 of 2228 rows after 585 seconds. The run used one worker.
The corresponding trace sum was 583.484 seconds. Barcode scanning used 189.538
seconds. Rerank and label preparation used 116.859 seconds. The first embedding
request used 102.063 seconds, including two HTTP 500 failures and retries. Package
processing used 93.971 seconds. Most SAM3 and VLM responses were already cached.
Image encoding, mask processing, and crop preparation still ran before or after
those cache reads. Query embedding requests had no client response cache.
Read the [original trace investigation](../2026-09-27_profile-latency.md).

The original barcode path scans the source photo before package or label processing.
It applies orientation, flattens transparency on white, and resizes the long side to
1600 pixels. It enlarges smaller photos. It tries `LocalAverage` and `FixedThreshold`
on the whole resized photo. A miss continues through nine overlapping tiles and
then 25 overlapping tiles. The maximum is 70 native decoder calls. A unique
catalogue match stops the scan. The formats are EAN13, GTIN-only Code128, and QR.
`try_downscale` is disabled. `try_rotate` remains enabled.

The pinned zxing-cpp 2.3.0 Python binding releases the GIL around native decoding.
The inspected native decode path has no internal thread pool. The Python API has
no `threads` argument. Caller-managed threads can therefore overlap independent
tile calls. Buffer preparation occurs before the GIL release. `photo4` retains
ordered result consumption and waits for already running work before recording
the image time. Read the [pinned source investigation](../2026-09-27_zxing-speed-options.md).

## Full-corpus barcode controls

The five scan variants in the table rescanned 2228 query rows without barcode-cache reuse.
The rows contain 1851 unique image digests, 1644 positive labels, and 584 negative
constraints. Repeated image bytes still received fresh scans in this control.
These times cover the barcode path alone. They do not measure HTTP recognition.

| Variant | Maximum calls | Correct unique barcode hits | Median ms | p95 ms | p99 ms | Full-set wall s |
|---|---:|---:|---:|---:|---:|---:|
| `full` | 70 | 24 | 326.7 | 638.1 | 910.8 | 816.886 |
| `whole1` | 1 | 20 | 60.3 | 160.1 | 276.8 | 169.6 |
| `whole` | 2 | 23 | 67.2 | 181.4 | 280.8 | 183.991 |
| `tiles3` | 20 | 23 | 168.6 | 335.2 | 546.2 | 426.3 |
| `photo4` | 70 | 24 | 124.0 | 257.5 | 421.9 | 325.217 |

All variants had zero wrong unique matches and zero decoder errors. `photo4`
preserved all 2228 baseline match decisions. Its native-call total was 154396,
against 154394 for `full`. Two additional calls came from already running work.
Its maximum image time was 2805.450 ms, against 2201.758 ms for `full`.
Parallel decoding therefore did not improve every observed tail value.

`whole` loses the known hit on `q-000955`. The 3-by-3 scan does not restore that hit.
`whole1` loses four known hits. The second binarizer restores three of those hits.
The observed whole-set speed ratios are 4.44 for `whole` and 2.51 for `photo4`
relative to `full`. The variants ran sequentially under changing host load.
These ratios are descriptive, not controlled estimates of the decoder-only effect.
The Mac has 12 logical CPUs. Its recorded one-minute load average fell from 46.82
at stage-1 launch to 14.82 at 02:13. Read the
[contention observation](comparison.md) and [saved host sample](host-observation-021302.json).
The saved `estimated_total_ms` values reuse cached baseline stage times.
They MUST NOT be presented as measured new-image or demo latency.

Sources: [full](stage1/full.summary.json), [whole1](stage1/whole1.summary.json),
[whole](stage1/whole.summary.json), [tiles3](stage1/tiles3.summary.json),
and [photo4](stage1/photo4.summary.json).

## Repeated bulk recognition

The four complete runs use the reference profile
`barcode-rerank-siglip2-512-crop` and the full barcode scan. Normal SAM3 and VLM
response caches remain enabled. Query embeddings still require remote requests.
Each run contains 2228 rows and 1851 distinct image digests.

| Barcode cache | Query workers | Process wall s | Harness wall s | Barcode cache-hit rows | Native decoder calls |
|---|---:|---:|---:|---:|---:|
| Cold | 1 | 855.785 | 854.498 | 377 | 128004 |
| Warm | 1 | 462.249 | 460.973 | 2228 | 0 |
| Cold | 4 | 232.358 | 231.029 | 332 | 131154 |
| Warm | 4 | 129.634 | 128.303 | 2228 | 0 |

All four runs have zero errors and zero degraded results. Prediction order, candidate
ranks, truth ranks, and outcomes are unchanged against the baseline and each other.
R@1 is 1392/1644, or 84.67%. R@5 is 1595/1644, or 97.02%.
There are 90 forbidden top-1 predictions among 584 negative constraints.
A prediction allowed by a negative constraint is not a confirmed identification.

The cold cache naturally reuses repeated image bytes. Four workers produce 45 more
cache misses than the 1851 unique digests. This is consistent with concurrent scans
of duplicates before the first cache write. The observation does not directly
measure overlap. Warm cache entries remove all native decoder calls.
Four query workers give observed process-wall speed ratios of 3.68 for cold cache
and 3.57 for warm cache against the corresponding one-worker run.

The first cold one-worker embedding call took 42.054 seconds. The total retains
this call. It includes more than model loading, so it is not a model-load timer.
The original baseline took 2507.100 seconds under a different startup and host-load
state. Do not attribute that entire difference to the barcode cache.

The warm one-worker trace still spends 169.457 seconds in package processing,
109.052 seconds in `cluster_rules`, 100.698 seconds in embedding, and 53.647 seconds
in view preparation. Barcode work falls to 3.950 seconds. Cached model responses
do not remove image processing. Use `trace.steps[].ms` for stage costs. Cached
response fields can retain the original inference duration. With four workers,
summed stage times are not process elapsed time.

Sources: [validated bulk comparison](bulk-comparison-final.md),
[stage costs](bulk-all-step-costs.json), and
[duplicate misses](bulk-cold-4-duplicate-misses.json).

## Sequential HTTP recognition

The frozen pilot contains 64 query rows, 61 unique images, 54 positive labels, and
ten negative constraints. It deliberately includes all 24 known barcode-hit rows.
The other 40 rows contain 30 positives and ten negatives. The pilot therefore
oversamples the fast barcode-return path. Its deadline fraction is not a corpus
estimate. `q-000483` and `q-000484` share image bytes but have disjoint positive
truth. Keep the raw denominator of 54 positives. Also report the sensitivity that
excludes both rows and uses 52 positives among 62 rows.

Each HTTP request uses a new upload directory and response-cache directory.
The child disables model-cache reads. Barcode, SAM3, and VLM responses are fresh
when the path needs them. Persistent mode retains the backend and catalogue.
It does not reuse earlier query responses. Step-view reconstruction can read
responses written during the same request through a cache-only client.

HTTP wall time covers loopback upload through the complete response body.
It includes upload handling, recognition, and `steps_answer` reconstruction.
The first persistent request includes child startup and backend construction.
It excludes service setup, source-file reading, client JSON parsing, browser
rendering, and real client LAN latency. Final persistent-worker shutdown is outside
the request timer. Nested startup, build, ask, stage, and HTTP timers MUST NOT be added.
The experimental child import path differs from production `recognize.py`.

The reference profile gives these complete results. “Correct” requires a correct
top-1, a valid response, and the stated time threshold.

| Runtime / barcode variant | HTTP ≤3 s /64 | Correct ≤3 s /54 | Late correct | HTTP p50 / p95 / maximum ms |
|---|---:|---:|---:|---:|
| Process / full | 45 | 35 | 9 | 1498.6 / 6700.5 / 300700.7 |
| Process / whole | 45 | 34 | 10 | 1343.5 / 6575.6 / 8011.1 |
| Process / photo4 | 45 | 35 | 10 | 1404.0 / 6497.0 / 9478.7 |
| Process / whole + fresh barcode crop | 38 | 32 | 13 | 1970.4 / 7391.5 / 8793.9 |
| Persistent / full | 49 | 38 | 7 | 1037.1 / 5936.1 / 7784.3 |
| Persistent / whole | 51 | 38 | 6 | 877.6 / 5812.9 / 7758.6 |
| Persistent / photo4 | 50 | 38 | 7 | 922.5 / 6074.8 / 7656.5 |
| Persistent / whole + fresh barcode crop | 45 | 35 | 10 | 1552.3 / 6841.2 / 8407.3 |

All cells contain 64 observed requests. The process/full cell retains one HTTP 503.
All other requests returned HTTP 200 without degradation. `whole` retains 23 of
24 known barcode hits. `full`, `photo4`, and whole-first fresh barcode cropping
retain all 24. Fresh barcode fallback recovers the whole-photo miss, but adds
SAM3 cost and gives no quality gain over `photo4` in this pilot.

The process/photo4 runtime starts a child for every request. Its median child
startup is 394.6 ms. Backend construction uses 184.0 ms inside that interval.
Persistent/photo4 charges its 473.9 ms startup to the first request only.
Its 24 known barcode-hit requests all finish correctly within three seconds.
Among the other 40 rows, 26 finish within three seconds. Only 14 of their 30
positive rows are correct within three seconds.

Sources: [pilot report](http-pilot-report-final-v2/http-comparison.md),
[validation](http-pilot-validation.json), and [selection](demo-selection-64.json).

## Measured profile tradeoff

All three rows below use persistent `photo4` and the same frozen 64-row selection.
All three have R@5 of 54/54. All three retain 24/24 known barcode hits.
Each row has zero HTTP errors, degradation, decoder errors, and censored waits.

| Profile | R@1 /54 | R@1 sensitivity /52 | Correct ≤3 s /54 | HTTP ≤3 s /64 | Forbidden top-1 /10 | HTTP p50 / p95 / maximum ms |
|---|---:|---:|---:|---:|---:|---:|
| `barcode-rerank-siglip2-512-crop` | 45 | 44 | 38 | 50 | 0 | 922.5 / 6074.8 / 7656.5 |
| `barcode-siglip2-512-crop` | 44 | 43 | 40 | 58 | 0 | 890.7 / 3345.1 / 3608.5 |
| `barcode-siglip2-512-as-is` | 43 | 42 | 43 | 64 | 1 | 305.4 / 1634.4 / 2158.0 |

Correct-within-three-second sensitivity counts are respectively 38/52, 40/52,
and 42/52. R@5 sensitivity is 52/52 for every profile. An allowed negative prediction
is unscored for identification quality.

The crop profile is an isolated rerank control. It retains the same barcode options,
package preprocessing, model, index, and full retrieval view. Its different default
query-worker count has no effect on sequential HTTP execution. Removing rerank
adds eight timely responses and two correct timely answers. It loses one correct
top-1, `q-002098`. The measured quality difference agrees with the independent
[offline pre-rerank reconstruction](http-persistent-photo4-offline-rerank.md).
The offline reconstruction makes no HTTP latency claim.

The as-is profile is a joint ablation. It removes query package cropping and
conditional label-based VLM rerank. It keeps the same full embedding index and
barcode options. It does not change to a label embedding tower. Its whole/photo4
paths send no query SAM3 or VLM requests. Do not attribute its complete latency
gain to rerank removal alone. Read the [source comparison](profile-comparison-observation.md).

The no-rerank crop control still has six late requests. Their package stage costs
1023.0–1348.8 ms. Their `steps_answer` costs 974.7–1147.9 ms. Their barcode stage
costs 393.3–533.7 ms. Image loading, upload handling, view preparation, and embedding
add further work. Removing VLM rerank alone cannot eliminate this measured tail.

Sources: [as-is report](http-as-is-report-final/http-comparison.md),
[as-is validation](http-as-is-pilot-validation.json),
[crop control report](http-crop-no-rerank-report-final/http-comparison.md),
[crop control validation](http-crop-no-rerank-validation.json), and
[crop control per-request traces](http-crop-no-rerank/persistent-photo4.jsonl).

## Crop evidence and its limits

The cached-geometry stage covers 1851 distinct originals. Package rectangles are
available for 1827. Bottle, label, and barcode rectangles are available for 433,
441, and 86 respectively. Detection responses are missing for 1410 originals.
All 24 known barcode hits lack a baseline package box because the barcode return
bypassed segmentation. Thus zero standalone package hits is a selection effect.
It does not show that package cropping inherently loses every barcode.
The whole-first cached-crop variants retain 23 known hits. No available cached
crop restores `q-000955`. Cached geometry preparation has median 58.184 ms and
p95 217.886 ms. These costs exclude fresh SAM3 inference.

The separate fresh-crop diagnostic measures all 24 known barcode-hit images.
Every image has a fresh SAM3 request before crop decoding. It has no ordinary
barcode-miss images or negative constraints. Each crop uses original-image pixels.
Bottle uses the largest valid rectangle. Label uses the production label-selection
rule. Barcode uses ordered rectangles with a 10% margin per side and no region cap.
The first unique catalogue match stops the scan. Crops are not masked label pixels.
Each crop receives the two whole-region binarizer calls. It does not receive the
full 70-call tile scan.

| Fresh region | Geometry available /24 | Barcode hits /24 | Correct ≤3 s /24 | HTTP ≤3 s /24 | HTTP p50 / p95 / maximum s |
|---|---:|---:|---:|---:|---:|
| Bottle | 19 | 18 | 18 | 23 | 1.129 / 2.334 / 5.373 |
| Label | 24 | 18 | 18 | 24 | 1.181 / 2.098 / 2.146 |
| Barcode | 24 | 22 | 22 | 24 | 1.007 / 1.528 / 1.811 |

These are retention rates for known hits, not full-corpus detection recall.
All 72 diagnostic requests return HTTP 200 without degradation. The normal model
fallback gives no correct top-1 for a missed crop barcode. Fresh barcode rectangles
recover `q-000955`, but lose two other known hits. Fresh SAM3 alone has a median
cost of about 665–676 ms. Whole-image `photo4` retains all 24 known hits without
that added segmentation request. The evidence does not support replacing the
whole-image scan with only a bottle, label, or barcode crop.
The limited crop strategies and selected sample do not establish that every crop
strategy fails. Different geometry, scale, pass budgets, or fallback ordering need
their own measurements before a broader conclusion is possible.

Sources: [preparation coverage](stage2/preparation.summary.json),
[cached whole-barcode control](stage2/whole-barcode.summary.json), and
[fresh crop observation](http-crop-hits-observation.md).

## Startup, response work, and remaining limits

The fourth process/full request, `q-000078`, returned HTTP 503 after 300700.691 ms.
The child watchdog expired during the first conditional rerank while Qwen was
unloaded in the saved preflight. The complete response arrived. This is not a
censored transport wait. Child component timings are unavailable for this failed
request. They are unknown, not zero. The record does not isolate model-load time
or attribute the wait to ZXing. Resume preserved this failed row in all denominators.
After-first observations do not prove remote model residency. A later conditional
request can start a different model. Read the [cold-VLM evidence](http-cold-vlm-observation.json).

In successful persistent/photo4 reference requests, median barcode stage time is
95.8 ms across 64 rows. Median package stage time is 686.8 ms across 40 rows.
Median embedding time is 46.6 ms across 40 rows. Median conditional rerank time
is 2203.8 ms across 18 rows. These distributions use actual trace-stage wall time.
They are path-conditioned and MUST NOT be added as if every request uses every path.

Response work remains visible after inference. Reference persistent/photo4 upload
handling has median 7.1 ms and p95 255.3 ms. `steps_answer` has median 136.9 ms and
p95 1081.6 ms. The as-is variant reduces step-view median to 71.3 ms, with p95
494.3 ms. A future demo implementation must include this response work when it
measures the three-second target. A backend-only timer is insufficient.

The measurements ran once per cell in a fixed sequence under changing host and
service state. Their quantiles describe these runs. The 64-row selection is small
and enriched for barcode hits. The GPU services are shared. The task tracker listed
DrinkAtlas enrichment work, but read-only runtime checks do not prove that work
was active during every cell. SAM3 and vLLM queues were empty at known preflights.
Those snapshots do not establish zero contention for the full measurements.
No service was unloaded for these comparisons. Remote model residency therefore
remains separate from the Mac CPU contention and client-cache settings.
No enforced three-second timeout, deadline-aware
fallback, or cancellation behavior was implemented or validated. A larger sample
with ordinary barcode misses is needed before a demo service can claim a deadline
success rate. Broader profile reruns are a separate task with their own launch gates.
