# Barcode bulk comparison

Expected coverage: 2228 query rows and 1851 unique image digests.

This report reads recorded metadata only. The parent task MUST verify actual PID commands before any launch or retry.

| Variant | State | Observed rows | Digests | Errors | Degraded | Barcode hits | Native calls | Harness s | Process s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cold-1 | complete | 2228 | 1851 | 0 | 0 | 377 | 128004 | 854.498 | 855.785 |
| warm-1 | complete | 2228 | 1851 | 0 | 0 | 2228 | 0 | 460.973 | 462.249 |
| cold-4 | complete | 2228 | 1851 | 0 | 0 | 332 | 131154 | 231.029 | 232.358 |
| warm-4 | complete | 2228 | 1851 | 0 | 0 | 2228 | 0 | 128.303 | 129.634 |

Rows from an incomplete run are partial observations. They are not complete-run metrics.

| Left | Right | Scope | Matched rows | Prediction changes | Top-5 changes | Truth-rank changes | Outcome changes |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| baseline | cold-1 | complete paired runs | 2228 | 0 | 0 | 0 | 0 |
| baseline | warm-1 | complete paired runs | 2228 | 0 | 0 | 0 | 0 |
| baseline | cold-4 | complete paired runs | 2228 | 0 | 0 | 0 | 0 |
| baseline | warm-4 | complete paired runs | 2228 | 0 | 0 | 0 | 0 |
| cold-1 | warm-1 | complete paired runs | 2228 | 0 | 0 | 0 | 0 |
| cold-1 | cold-4 | complete paired runs | 2228 | 0 | 0 | 0 | 0 |
| cold-1 | warm-4 | complete paired runs | 2228 | 0 | 0 | 0 | 0 |
| warm-1 | cold-4 | complete paired runs | 2228 | 0 | 0 | 0 | 0 |
| warm-1 | warm-4 | complete paired runs | 2228 | 0 | 0 | 0 | 0 |
| cold-4 | warm-4 | complete paired runs | 2228 | 0 | 0 | 0 | 0 |

Process wall includes work outside harness timing. Do not interpret the difference as pure startup time.


- Artifacts can change while a run is active. Partial observations are not complete-run metrics.
- Bulk timings do not establish latency for a new demo image.
- Cold barcode caches permit natural hits for repeated image digests.
- Normal SAM3 and VLM response caches remain enabled. Query embeddings have no client response cache.
- The first request can include remote model startup. Keep its full latency in total wall time. Its latency is not an isolated model-load duration.
- Candidate scores are not compared. Prediction order, candidate ranks, truth ranks, outcomes, and errors are compared by query ID.
