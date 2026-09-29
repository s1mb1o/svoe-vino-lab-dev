# PARTIAL / DRAFT — profile comparison

Date: 2026-09-27. This is not the final 53-profile report.
This draft uses reviewed reports and saved queue records only.
It performs no inference, launch, image inspection, or rescoring.

At 06:31:08 MSK, the queue records 41 done, one running, and 11 pending authorized profiles.
The running profile is `siglip2-384-as-is`. All four local profiles remain pending.
These are saved queue states, not a new verification of live processes.
The observed queue SHA-256 is `75a0f640207d52f44ec5748e137a91f3da6029651604ceeec2c1eaa23f7b68ef`.

## Final completion accounting — TO FILL

There are 54 configured profiles. The authorized queue contains 53 internal or local profiles.
The external `vino-svoe-search-by-photo` profile is excluded pending explicit photo-transfer approval.

**[TO FILL: final queue snapshot path, hash, generation time, and review evidence.]**

**[TO FILL: successful / failed / unavailable / pending counts among the 53 authorized profiles.]**

Keep every failed or unavailable profile visible, with its reason and evidence.
An unavailable profile without a launch must retain an empty attempt list.
Do not call a capacity refusal an inference failure.
The reporter can exit zero for a partial snapshot. Read its status and terminal counts.
Use `terminal_with_failures` when all authorized profiles are terminal but some did not succeed.
Do not describe that state as 53 successful measurements.

## Final all-profile table — TO FILL

**[TO FILL: exactly 54 named rows from the final reconciled snapshot.]**

Include status, attempts, run ID, workers, cache setting, and configured barcode stage.
Include observed rows, errors, degraded results, R@1, R@5, and forbidden top-1/top-10 counts.
Include index coverage, runner wall, intent-to-final time, and cached bulk throughput.
Keep unavailable metrics unknown. Do not replace them with zero.
The JSON snapshot contains index coverage and forbidden-top-10 fields that its Markdown table omits.
Mark obsolete queue-time reasons, such as the earlier missing p1024 index, as historical.

Every complete run uses 2228 query rows and 1851 unique image digests.
Quality uses 1644 positive rows and 584 negative constraints.
A negative row forbids its named wine. Another prediction is not a confirmed identification.
The queue requests `use_barcode=true`, but profiles without a configured barcode stage do not scan codes.

## Final ranking — TO FILL

**[TO FILL: quality ranking of verified complete runs, with exact denominators and coverage caveats.]**

**[TO FILL: observed bulk throughput comparison, with workers and cache conditions.]**

Keep incomplete and unavailable profiles outside measured rankings.
Do not use cached bulk latency to rank fresh sequential demo performance.
Do not describe small differences from one run per setting as controlled causal estimates.

## Fast bulk reruns

Use the barcode cache and four query workers for remote embedding profiles.
The separate completed bulk comparison retains the full barcode scan and the reference crop/rerank profile.
All four settings preserve baseline predictions, candidate order, ranks, and outcomes.

| Barcode cache | Query workers | Process wall, s | Harness wall, s |
|---|---:|---:|---:|
| Cold | 1 | 855.785 | 854.498 |
| Warm | 1 | 462.249 | 460.973 |
| Cold | 4 | 232.358 | 231.029 |
| Warm | 4 | 129.634 | 128.303 |

The observed four-worker speed ratios are 3.68 for cold cache and 3.57 for warm cache.
Warm barcode caches remove native decoding in this instrumented comparison.
Cached SAM3 and VLM responses still require image preparation and response processing.
Remote query embeddings still require requests.
The cold one-worker run retains its initial 42.054 s embedding request.
This startup-associated request includes other work. It is not an isolated model-load timer.
Startup, host load, and model residency differ between runs.
Use one query worker for local profiles under the queue policy.

Source: [completed barcode recommendations](../2026-09-27_barcode-variants/final-recommendations.md).

## Fresh sequential demo requests

Persistent execution with per-image `photo4` decoding is the measured implementation candidate.
It retains all 24 known barcode hits. It can overlap up to four tile tasks inside one image.
Do not multiply four internal decode threads by four bulk query workers.

The HTTP pilot has 64 rows, 61 image digests, 54 positive rows, and ten negative constraints.
It includes all 24 known barcode-hit rows. Its deadline rate is not a full-corpus estimate.
Requests are sequential and bypass prior per-image response caches.
The HTTP timer covers upload through the complete response body, including response reconstruction.
This loopback timer excludes browser rendering and phone/network transit latency.

The main eight-cell HTTP pilot retains all 512 observations: 511 successful responses and one failure.
In the process/full cold-Qwen case, `q-000078` returns HTTP 503 after 300.701 s.
The watchdog expires during the first conditional rerank after an unloaded-Qwen preflight.
The retained failure does not isolate model-load time. It remains in all raw denominators.

| Persistent `photo4` profile | Correct top-1 /54 | Correct within 3 s /54 | Complete response within 3 s /64 | Forbidden top-1 /10 |
|---|---:|---:|---:|---:|
| Reference crop/rerank | 45 | 38 | 50 | 0 |
| Crop without rerank | 44 | 40 | 58 | 0 |
| As-is without crop/rerank | 43 | 43 | 64 | 1 |

The as-is profile gives the best measured deadline fraction in this selected comparison.
It trades two correct top-1 answers for more timely answers versus the reference.
Its HTTP p50 / p95 / maximum are 305.4 / 1634.4 / 2158.0 ms.
All three profiles have R@5 of 54/54.
The reviewed source also preserves the separate 52-positive sensitivity analysis.
Persistent execution and `photo4` remain experimental harness behavior.
No enforced three-second timeout, cancellation policy, or hard deadline guarantee was implemented or validated.

Source: [sequential HTTP evidence and limits](../2026-09-27_barcode-variants/final-recommendations.md).

## New label embedding tower

The reference and new label profile use the same frozen queries, catalogue, model, and index.
The new profile searches label vectors as a second tower.
It produces 29 fewer correct top-1 answers and nine fewer correct top-5 answers.

| Metric | Reference | Label profile | Paired changes |
|---|---:|---:|---|
| R@1 /1644 | 1392 | 1363 | 51 gained; 80 lost |
| R@5 /1644 | 1595 | 1586 | 10 gained; 19 lost |
| Forbidden top-1 /584 | 90 | 94 | 18 introduced; 14 removed |
| Forbidden top-10 /584 | 474 | 476 | 21 introduced; 19 removed |

These results do not support replacing the reference with this label profile.
Two missing-label rows correctly use the full tower alone.
Changed retrieval order and rerank selection also affect quality.
Do not attribute every loss to segmentation.

The run walls are 133.8 s and 895.2 s, with unequal cache warmth.
The label run has 1457 retrieval-label SAM3 misses and 50 rerank VLM misses.
The reference has no retrieval-label step and zero rerank VLM misses.
These walls do not measure equal-cache steady performance or demo latency.

Source: [reviewed paired label comparison](label-comparison-final.md).

## Coverage and other reviewed comparisons

The rebuilt NaFlex-1024 index has 4181 current items and no missing items.
The compared NaFlex-256/512 indexes have 4054 current items and 127 missing items.
NaFlex-1024 has 45 more wines in each view. All three retain two failed items.
Thus, cross-budget comparisons do not isolate the patch budget.
Matched crop/as-is and plain/barcode pairs use the same index.

The reviewed G2 and G3–G5 comparisons show crop gains with negative-constraint tradeoffs.
Barcode resolves the same 24 correct rows and preserves the matching pipeline on 2204 fallback rows.
A scan-cache hit is not a resolved wine answer.
Native-call totals are absent from these ordinary profile traces.

Sources: [G2 plain](g2-plain-comparison.md), [G2 barcode](g2-barcode-comparison.md),
and [G3–G5 comparison](g3-g5-comparison.md).

## Annotation constraints

The frozen audit finds 67 identical-digest groups with incompatible exact-slug positive constraints.
They contain 136 positive rows. No same-digest positive truth conflicts with a negative forbidden slug.
If identical bytes always produce the same deterministic answer without row-specific metadata,
the optimistic top-1 ceiling is 1576/1644, or 95.8637%. At least 68 positive rows must miss.
This is a conditional metadata bound, not an achieved result or an annotation correction.
It does not bound top-5. All raw labels, weights, and denominators remain unchanged.

Source: [reviewed annotation audit](annotation-audit.md).

## Local G10 and external status — TO FILL

**[TO FILL: all four local outcomes, current capacity evidence, applicable policy, and any run artifacts.]**

The [preliminary local note](local-readiness-preliminary.md) is not a launch gate or failure result.
Do not preemptively classify the pending local profiles as failed or unavailable.
Any final capacity outcome needs current evidence and the recorded policy reason.

External photo-transfer approval remains pending.
The external recognizer has no authorized measurement in this execution.
Its exclusion must remain visible in the final 54-profile table and the final user report.
