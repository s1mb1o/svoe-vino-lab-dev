# Barcode bulk comparison

Expected coverage: 2228 query rows and 1851 unique image digests.

This report reads recorded metadata only. The parent task MUST verify actual PID commands before any launch or retry.

| Variant | State | Observed rows | Digests | Errors | Degraded | Barcode hits | Native calls | Harness s | Process s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cold-1 | complete | 2228 | 1851 | 0 | 0 | 377 | 128004 | 854.498 | 855.785 |
| warm-1 | missing | 0 | 0 | 0 | 0 | 0 | unavailable | unavailable | unavailable |
| cold-4 | missing | 0 | 0 | 0 | 0 | 0 | unavailable | unavailable | unavailable |
| warm-4 | missing | 0 | 0 | 0 | 0 | 0 | unavailable | unavailable | unavailable |

Rows from an incomplete run are partial observations. They are not complete-run metrics.

| Left | Right | Scope | Matched rows | Prediction changes | Top-5 changes | Truth-rank changes | Outcome changes |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| baseline | cold-1 | complete paired runs | 2228 | 0 | 0 | 0 | 0 |

Process wall includes work outside harness timing. Do not interpret the difference as pure startup time.


- Artifacts can change while a run is active. Partial observations are not complete-run metrics.
- Bulk timings do not establish latency for a new demo image.
- Cold barcode caches permit natural hits for repeated image digests.
- Normal SAM3 and VLM response caches remain enabled. Query embeddings have no client response cache.
- The first request can include remote model startup. Keep its full latency in total wall time. Its latency is not an isolated model-load duration.
- Candidate scores are not compared. Prediction order, candidate ranks, truth ranks, outcomes, and errors are compared by query ID.
