# Preliminary HTTP process-mode comparison

Status: preliminary. This report covers four completed process-mode sessions only.
Persistent-mode results are outside this report.
No image, model, server, or new measurement was used for this analysis.

The `photo4` variant preserves the observed quality of `full` on all 63 mutually successful queries.
Its paired median HTTP reduction is 84.6 ms.
The `whole` variant is faster but loses one known barcode hit.
Fresh barcode SAM3 recovers that hit. It gives no additional hit over `full` or `photo4`.
Fresh barcode SAM3 makes seven responses exceed 3 seconds.

## Inputs and scope

Profile: `barcode-rerank-siglip2-512-crop`.
Selection fingerprint: `3b1fd11b30778da43042b04158b1cf820f92e53c7ffe5f360c241ce38dac9763`.
The frozen sample has 64 query rows and 61 unique images.
It has 54 positive annotations and 10 negative constraints.
It contains all 24 baseline barcode hits and 40 other rows.
The 40 other rows contain 30 positive annotations and 10 negative constraints.
The sample oversamples barcode hits relative to the corpus rate of 24/2228.
These pilot fractions are not corpus estimates.

The HTTP timer covers loopback upload through the complete response read.
It includes `store_upload`, child startup, backend construction, recognition, child cleanup, and `steps_answer`.
It excludes service setup, client source-file read, client JSON parse, browser rendering, and remote client LAN.
The worker uses the experimental import path. It does not run unmodified `recognize.py`.
Every request has a fresh upload directory and cache directory.
Child cache reads are disabled. Server cache reads only reconstruct the response views.

Input hashes and per-query outcomes are saved in [the JSON report](http-process-preliminary.json).

## Raw results, with all failures retained

Correct counts use 54 positive annotations. Deadline counts use all 64 rows.
A complete response is not necessarily a correct recognition.
All variants made zero forbidden top-1 predictions on the 10 negative constraints.
This result does not establish correct negative identification.
All observed native decoder error counts are zero.
The incomplete backend for the `full` failure has no decoder trace.
No degraded responses were observed.
Quantiles use complete HTTP responses, including the HTTP 503.


| Variant | Correct ≤3 s /54 | Correct late | Correct any time /54 | Top-5 /54 | HTTP ≤3 s /64 | Errors | HTTP p50 s | HTTP p95 s | HTTP max s |
|---|---|---|---|---|---|---|---|---|---|
| full | 35 | 9 | 44 | 53 | 45 | 1 | 1.499 | 6.700 | 300.701 |
| whole | 34 | 10 | 44 | 53 | 45 | 0 | 1.343 | 6.576 | 8.011 |
| photo4 | 35 | 10 | 45 | 54 | 45 | 0 | 1.404 | 6.497 | 9.479 |
| whole-fresh-barcode | 32 | 13 | 45 | 54 | 38 | 0 | 1.970 | 7.392 | 8.794 |

The `full` request for `q-000078` returned HTTP 503 after 300.701 s.
The fourth query triggered the first fresh rerank.
The saved preflight and failure reconciliation show that Qwen NVFP4 was cold.
The model was still starting before the child watchdog expired.
The complete HTTP error response arrived. Its transport latency is not censored.
The raw child stage timings are unavailable. The stored zero placeholders do not measure zero work.
Do not attribute the 300.701 s wait to ZXing or to an exact isolated model-load duration.
The resumed session kept this failure and did not retry this query in `full`.
The same query was correct but late in the other variants: 6.579 s, 6.743 s, and 7.719 s.

Evidence: [failure reconciliation](http-pilot-failure-reconciliation-0321.json),
[initial preflight](gpu-preflight-before-http-pilot.json), and
[resume preflight](gpu-preflight-before-http-resume-1.json).

## Paired-success sensitivity

This table excludes `q-000078` in all four variants.
The subset has 63 rows, 60 unique images, 53 positive annotations, and 10 negative constraints.
This conditional comparison does not erase the failure or measure reliability.


| Variant | Correct ≤3 s /53 | Correct any time /53 | Top-5 /53 | HTTP p50 s | HTTP p95 s | HTTP max s | Paired median HTTP delta from full ms |
|---|---|---|---|---|---|---|---|
| full | 35 | 44 | 53 | 1.475 | 5.548 | 8.321 | 0.0 |
| whole | 34 | 43 | 52 | 1.304 | 5.217 | 8.011 | -127.3 |
| photo4 | 35 | 44 | 53 | 1.382 | 5.426 | 9.479 | -84.6 |
| whole-fresh-barcode | 32 | 44 | 53 | 1.966 | 6.222 | 8.794 | 409.4 |

Only `q-000955` changes top-1 prediction on this subset.
Full and photo4 have identical correct-within-3-second query sets.
The variants ran once in a fixed order. Service variation can affect paired latency differences.

## Annotation-conflict sensitivity

The byte-identical queries `q-000483` and `q-000484` have disjoint positive truths.
This sensitivity excludes both queries only.
It has 62 rows, 60 unique images, 52 positives, and 10 negative constraints.
The `full` cold failure remains in this table.


| Variant | Correct ≤3 s /52 | Correct late | Correct any time /52 | Top-5 /52 |
|---|---|---|---|---|
| full | 35 | 8 | 43 | 51 |
| whole | 34 | 9 | 43 | 51 |
| photo4 | 35 | 9 | 44 | 52 |
| whole-fresh-barcode | 32 | 12 | 44 | 52 |

The combined paired-success and conflict sensitivity is separate.
It excludes all three queries and has 61 rows, 59 unique images, and 51 positives.
The JSON report stores that table. It MUST NOT be described as the 52-positive sensitivity.

## Selection strata

The known-hit stratum has 24 positives.
The other stratum has 40 rows with 30 positives.


| Variant | Known hits correct ≤3 s /24 | Known hits correct any time /24 | Other correct ≤3 s /30 | Other correct any time /30 | Other HTTP ≤3 s /40 | Negative HTTP ≤3 s /10 |
|---|---|---|---|---|---|---|
| full | 24 | 24 | 11 | 20 | 21 | 9 |
| whole | 23 | 23 | 11 | 21 | 21 | 9 |
| photo4 | 24 | 24 | 11 | 21 | 21 | 9 |
| whole-fresh-barcode | 24 | 24 | 8 | 21 | 14 | 5 |

## The lost whole-photo hit: q-000955

The expected wine is `fanagoriya-brule-frizzante-brut-rozovoe-merlo-igristoe-bryut-rozovoe-115`.
Full, photo4, and the fresh crop read EAN13 `4603040021149`.
The normalized GTIN is `04603040021149`.
Whole reads no code. Its fallback predicts
`vinodelnya-pokrovskaya-pokrovskoe-sladkoe-krasnoe-kaberne-sovinon-13`.
The expected wine is absent from its top 10.


| Variant | HTTP ms | Barcode stage ms | Native calls | Correct top-1 |
|---|---|---|---|---|
| full | 623.9 | 129.7 | 68 | True |
| whole | 1248.4 | 35.5 | 2 | False |
| photo4 | 546.4 | 67.6 | 70 | True |
| whole-fresh-barcode | 1160.2 | 682.9 | 4 | True |

The fresh crop sends one SAM3 request. It takes 590.3 ms.
The original image is 487 × 1199 pixels. The sent image has the same size.
SAM3 yields rectangles `[305, 796, 399, 1016]` and `[174, 824, 261, 913]`.
The first crop recovers the barcode. The scan stops after that region.
The fresh crop is 613.8 ms slower than photo4 for this query.

## Stage cost and HTTP cost

The next table uses the same 63 successful queries in every variant.
Times are medians in milliseconds.
Build time is inside startup time. Ask time is inside process time.
The barcode, package SAM3, embedding, and rerank stages are inside ask time.
Fresh crop SAM3 is inside the barcode stage. Do not add these nested timers.


| Variant | HTTP | Child startup | Build inside startup | Ask | Upload | steps_answer | Cleanup |
|---|---|---|---|---|---|---|---|
| full | 1474.5 | 390.9 | 184.1 | 851.4 | 8.3 | 133.4 | 42.1 |
| whole | 1304.2 | 387.9 | 182.4 | 698.7 | 7.5 | 126.7 | 42.8 |
| photo4 | 1381.6 | 394.5 | 184.0 | 747.3 | 7.7 | 139.6 | 42.4 |
| whole-fresh-barcode | 1965.8 | 395.6 | 184.6 | 1331.2 | 6.0 | 133.8 | 42.9 |

Child startup is charged for every process-mode query.
The first full session starts with `q-001089`; the resumed session starts with `q-000063`.
The other sessions start with `q-001089`. The JSON report retains these markers.
After-first statistics do not prove that remote models were warm.
The cold rerank occurred on the fourth query.

On matched successful queries, the remaining HTTP time after upload, process, and steps_answer is about 39–40 ms at the median.
This residual includes uninstrumented handler, serialization, response transfer, and client HTTP work.
It is not a direct measurement of network latency.
The `steps_answer` p95 is about 1.0 s across variants.
The upload p95 is about 0.25–0.27 s across variants.
These costs explain part of the difference between backend ask time and the complete HTTP response.

The stage table uses all available successful traces.
Each cell gives the observed row count and median milliseconds.
Different stage counts reflect barcode early exits and the missing full failure trace.


| Variant | Barcode n / median | Package SAM3 n / median | Embedding n / median | Rerank n / median |
|---|---|---|---|---|
| full | 63 / 199.7 | 39 / 725.4 | 39 / 59.0 | 17 / 2172.3 |
| whole | 64 / 69.7 | 41 / 718.0 | 41 / 55.7 | 18 / 2184.4 |
| photo4 | 64 / 110.3 | 40 / 730.6 | 40 / 55.0 | 18 / 2118.5 |
| whole-fresh-barcode | 64 / 689.5 | 40 / 706.7 | 40 / 50.8 | 18 / 2152.8 |

Photo4 parallelizes native decode passes for one image.
It does not reduce native call count here: matched totals are full 2844, whole 126, photo4 2846, whole-fresh-barcode 140.
Full records 68 native calls for q-000955. Photo4 records 70.
Concurrent work can finish before the stop condition is observed.
The photo4 embedding outlier is 1749.9 ms on q-000160.
This outlier belongs to embedding, not barcode decoding.

## Fresh barcode SAM3 benefit and loss

Fresh barcode SAM3 skips segmentation on 23 queries with a unique catalogue barcode hit.
It sends 41 SAM3 client requests.
Thirty-seven requests have no barcode detection. Four requests yield regions.
The four region queries are `q-000726`, `q-000955`, `q-002098`, `q-001516`.
Only q-000955 gains a catalogue barcode hit over whole.
No query gains a barcode hit or a correct top-1 over photo4.
The 41 SAM3 requests use 26.169 s in total, with a median of 609.9 ms.
Sent-image preparation adds 5.173 s across those requests.
Forty queries then perform package segmentation again.
The child has cache reads disabled, so this duplicated SAM3 cost remains in the measured request.

The paired median HTTP increase is 577.7 ms versus whole and 539.4 ms versus photo4.
Fresh barcode SAM3 makes these seven previously timely responses late:
`q-001186`, `q-001714`, `q-002221`, `q-002223`, `q-002225`, `q-000442`, and `q-001822`.
Three are correct positives: `q-001186`, `q-001714`, and `q-001822`.
The other four are negative constraints.
Relative to whole, the added correct early hit q-000955 offsets one of the three lost timely correct positives.
Relative to photo4, there is no offsetting quality gain.

## Interpretation limits

The process-only evidence supports photo4 as the quality-preserving decoder candidate in this pilot.
It does not establish that the complete demo meets a 3-second deadline.
Rerank, package segmentation, child startup, and response views remain material costs.
The persistent-mode comparison is required before a backend lifecycle decision.
The 24-hit standalone crop diagnostic is a separate experiment.
No hard 3-second timeout is implemented or demonstrated.
The 300-second watchdog is an experiment cleanup guard. It is not the demo deadline.
No production code or configuration was changed for this analysis.
