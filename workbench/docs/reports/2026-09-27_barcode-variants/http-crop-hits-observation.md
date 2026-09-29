# Fresh crop HTTP diagnostic

Status: complete diagnostic. The completed run contains 72 observations.
Each of three variants uses one persistent backend for 24 sequential requests.
This report was computed from saved JSON only.
No image, model, server, or network request was used for this analysis.

Fresh barcode rectangles retain 22 of 24 known barcode hits.
Bottle rectangles retain 18 of 24. Label rectangles retain 18 of 24.
The existing model pipeline does not recover a correct top-1 for any missed crop scan.
All correct returns finish within 3 seconds.
The result does not establish a 3-second demo guarantee.

## Sample and measurement scope

Profile: `barcode-rerank-siglip2-512-crop`.
Selection fingerprint: `0686b5bd8b64fa2be1baf2fb6932e96b80ac554b8f9d14ea99f9591f3f6d53a5`.
The frozen selection has 24 positive rows and 24 unique image digests.
These are all baseline catalogue barcode-hit images.
There are no negatives and no ordinary barcode-miss images.
Barcode retention on this selected set is not full-corpus recall.

The variants scan fresh crop rectangles only.
They do not scan the whole image before or after a crop miss.
The existing recognition pipeline processes a crop miss.
Every request has a new upload directory and cache directory.
Child cache reads are disabled. All 72 crop SAM3 client calls are fresh.
The recorded endpoint is `http://192.168.86.14:18081/upstream/sam3`.
Server cache reads reconstruct response views only.

The HTTP timer covers loopback upload through the complete response read.
It includes upload handling, recognition, and `steps_answer`.
The first request also includes child startup and backend construction.
It excludes service setup, source-file read, client JSON parse, browser rendering, and remote client LAN.
Final persistent-worker shutdown is outside the individual request timer.

## Geometry, decoding, and fallback

Each count uses 24 queries. A detected rectangle does not guarantee a readable code.
A unique barcode return is confirmed by the barcode trace field `out.mode == "answer"`.
It is not inferred from a correct final prediction.


| Variant | Geometry available | Missing geometry | Available crop without accepted code | Unique barcode returns | Pipeline fallbacks | Correct fallback top-1 |
|---|---|---|---|---|---|---|
| fresh-bottle | 19 | 5 | 1 | 18 | 6 | 0 |
| fresh-label | 24 | 0 | 6 | 18 | 6 | 0 |
| fresh-barcode | 24 | 0 | 2 | 22 | 2 | 0 |

All accepted-code rows produce a unique catalogue return.
No accepted-code row requires the model fallback.
All native decoder exception counts are zero.
All SAM3 error, HTTP error, transport error, and degradation counts are zero.
The incorrect recognitions below are HTTP 200 responses.

Bottle has no detection for `q-000955`, `q-000243`, `q-000962`, `q-000946`, `q-001826`.
These five queries make zero native decode calls.
Bottle has an available rectangle but no accepted code for `q-002145`.

Label has available geometry for all 24 queries.
Label returns no accepted code for `q-001661`, `q-000955`, `q-000819`, `q-002145`, `q-002089`, `q-001318`.
The label geometry uses the production `label_cut_of` rule.
Twenty-three queries use method `seg`. Query `q-001620` uses method `crop`.

Barcode has available geometry for all 24 queries.
Barcode returns no accepted code for `q-002145` and `q-001318`.
The barcode variant finds 42 candidate rectangles and scans 26 rectangles.
It stops scanning a query after a unique catalogue hit.
Twenty-one hits come from the first region. `q-002159` needs its second region.
The two misses scan all available regions: two for q-002145 and one for q-001318.

An available crop without an accepted code is a decode miss, not a native decoder exception.
The records do not establish whether the cause is rectangle choice, crop scale, image quality, or limited decode passes.
This analysis did not inspect the image pixels.

## HTTP latency and recognition quality

All counts retain all 24 queries in each variant.
The HTTP deadline column includes incorrect responses.
The correct-deadline column requires a correct top-1 and a valid complete response.


| Variant | Barcode retention | Correct ≤3 s /24 | Correct late | Top-5 /24 | HTTP ≤3 s /24 | HTTP p50 s | HTTP p95 s | HTTP max s |
|---|---|---|---|---|---|---|---|---|
| fresh-bottle | 18/24 | 18 | 0 | 18 | 23 | 1.129 | 2.334 | 5.373 |
| fresh-label | 18/24 | 18 | 0 | 19 | 24 | 1.181 | 2.098 | 2.146 |
| fresh-barcode | 22/24 | 22 | 0 | 22 | 24 | 1.007 | 1.528 | 1.811 |

Correct-within-3-second rates are 75.0%, 75.0%, and 91.7%.
The label fallback has one expected wine in its top five on q-002089.
That query still has an incorrect top-1.
The bottle variant has the only response above 3 seconds: q-000243 at 5.373 s.
That response is incorrect. Its fallback rerank takes 3.072 s.
No variant has a late correct response.

For q-000955, bottle has no region and label scans a region without an accepted code.
Both model fallbacks are incorrect.
The barcode region returns the expected Fanagoriya wine in 661.2 ms.
This confirms the local value of barcode geometry for that query.
It does not recover the two other barcode-crop misses.

## Startup and request cost

The first query is q-001668 in every variant.
It is a correct unique barcode return in every variant.
The persistent backend remains in use for the other 23 requests.


| Variant | First HTTP ms | First child startup ms | Build inside startup ms | After-first HTTP p50 ms | After-first correct ≤3 s /23 |
|---|---|---|---|---|---|
| fresh-bottle | 1511.3 | 483.2 | 194.9 | 1120.7 | 17 |
| fresh-label | 1702.0 | 574.4 | 173.0 | 1167.9 | 17 |
| fresh-barcode | 1528.3 | 482.5 | 189.5 | 1002.0 | 21 |

After-first is an observation group. It does not prove that remote models are warm.
The next table gives median component times in milliseconds, rounded to 0.1 ms.
These timers overlap. Fresh SAM3 and crop work are inside the barcode stage.
The barcode stage is inside ask time. Ask time is inside the HTTP response.
Do not add the columns.


| Variant | Fresh SAM3 | Image preparation | Geometry | Crop decode | Barcode stage | Ask | Upload | steps_answer |
|---|---|---|---|---|---|---|---|---|
| fresh-bottle | 672.2 | 102.5 | 0.0 | 41.8 | 847.0 | 981.2 | 7.2 | 38.4 |
| fresh-label | 675.5 | 101.6 | 31.5 | 43.6 | 926.5 | 1056.4 | 6.1 | 63.5 |
| fresh-barcode | 664.6 | 100.9 | 0.0 | 28.8 | 858.6 | 884.5 | 6.3 | 23.5 |

Each variant makes 24 crop SAM3 client calls.
Fresh SAM3 uses fresh-bottle: 16.294 s, fresh-label: 16.264 s, fresh-barcode: 16.139 s in total.
The 24 counts refer to client calls. Any internal retry time stays in the SAM3 duration.
Fallbacks perform package segmentation again: six bottle queries, six label queries, and two barcode queries.
No crop response is reused by that fallback. The repeated cost is charged.
Native decode calls total 38 for bottle, 48 for label, and 52 for barcode.

## Diagnostic limits

This diagnostic measures retention of known readable barcodes.
It does not measure performance on unseen miss images or negative images.
It does not estimate the demo deadline fraction on the full corpus.
Each variant ran once in a fixed order. Quantiles are descriptive.
The persistent worker uses the experimental import path.
These timings are not a measurement of unmodified `recognize.py` or the browser UI.
No hard 3-second timeout is implemented or demonstrated.

The fresh barcode crop is the strongest standalone crop in this diagnostic.
It still loses two known hits and pays for fresh segmentation on every request.
The complete-image variants and whole-first crop variant require their separate pilot results.

## Artifacts

- [Observation JSON](http-crop-hits-observation.json) records every query, crop rectangle, return path, and timing.
- [Offline generic report](http-crop-hits-report-final/http-comparison.md) retains the standard HTTP summaries.
- [Frozen selection](demo-selection-24.json) records image identities and ground truth.
- [Completion marker](http-crop-hits/complete.json) binds the completed run to its manifest.

The observation JSON records SHA-256 digests for every input artifact.
The source digests stayed fixed during analysis.
