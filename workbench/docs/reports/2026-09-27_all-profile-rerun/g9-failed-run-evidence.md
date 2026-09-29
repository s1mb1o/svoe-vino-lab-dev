# G9 failed-run evidence

Date: 2026-09-27. Profile: `siglip2-p14-384-as-is`.
Run: `2026-09-27T033914Z-lab-siglip2-p14-384-as-is-my`. Recorded runner PID: `77510`.

**Status: `invalid_completion`. The run is not a validated success.**
The runner ended with 2228 result rows and eight embedding errors.
The final event is named `done`, but its `errors` value is 8.
The queue helper rejected completion with:

> terminal artifacts do not prove complete, error-free paired coverage

## Preservation and coverage

The five source artifacts are copied byte-for-byte into [g9-failed-run-artifacts](g9-failed-run-artifacts/).
Every source and archive SHA-256 matches. Source hashes remained unchanged after copying.
The original attempt and job log remain in their existing archive.
The [JSON evidence](g9-failed-run-evidence.json) records all source paths, hashes, and file sizes.

| Artifact or stratum | Rows |
|---|---:|
| `queries.jsonl` | 2228 |
| `results.jsonl` | 2228 |
| `predictions.jsonl` | 2228 |
| Positive | 1644 |
| Negative constraints | 584 |
| Stored `http_status=200` | 2220 |
| Stored `http_status=null` with error | 8 |

The artifacts contain 1851 unique image digests. No query ID is missing, extra, or repeated.
Query fields match the frozen launch identity. Predictions match the saved results.
All eight errors remain in the raw denominator. No row was removed, retried, or rescored by this audit.

## Exact failed rows

All failures are positive rows. They contain eight distinct image digests across four place slugs.
All have empty candidates, `predicted_slug=null`, `rank_of_truth=null`, and `outcome=no_answer`.
Every failing trace stops at `embed`. There are no retrieval results for these rows.

| Query ID | Saved label | Filename stratum | Saved latency, ms | Embedding step, ms |
|---|---|---|---:|---:|
| `q-000001` | positive | `manual` | 49806 | 49711.9 |
| `q-000002` | positive | `manual` | 49805 | 49699.8 |
| `q-000003` | positive | `manual` | 49806 | 49713.6 |
| `q-000004` | positive | `manual` | 49805 | 49705.3 |
| `q-000005` | positive | `conf095` | 31123 | 31090.1 |
| `q-000006` | positive | `conf095` | 31124 | 31044.9 |
| `q-000007` | positive | `conf095` | 31123 | 31067.6 |
| `q-000008` | positive | `conf095` | 31123 | 31059.6 |

The filename strata describe saved filename suffixes only. No source image was opened.
All eight rows have the same reported failure type: an embedding upstream HTTP 500.
The error body says `unspecific error: upstream command exited prematurely` from `llama-swap`.
The endpoint is `http://192.168.86.14:18081/v1/embeddings`.
The result field itself stores `http_status=null`; do not replace it with 500.
The local artifacts do not establish the remote root cause or prove an OOM.

The parent's [saved gateway lines](g9-gateway-startup-lines.json), collected at 06:44:05 MSK,
show eight premature upstream exits followed by a health-check pass.
The [saved service observation](g9-startup-observation.json), recorded at 06:43:24 MSK,
reports the target as ready. Its bounded 102400-character model-log body contains no startup traceback.
These observations establish recovery, but the original startup failure cause remains unestablished.
The gateway exit count and the 24 client retry records describe different events.

## Time and retries

All times below use MSK, UTC+03:00.
The saved run interval is **06:39:14–06:42:04**. Runner wall is **169.9 s**.
The first retry is recorded at 06:39:38. The last retry is recorded at 06:40:23.
The progress error count rises from zero to four at 06:40:04.
It rises from four to eight at 06:40:35. No later progress event adds an error.
These are progress-event times. Per-query absolute timestamps are not stored.

The archived job log contains **24 retry events**. It records eight events each for attempts 1, 2, and 3.

| Retry timestamp | Attempt | Scheduled wait, s | Events |
|---|---:|---:|---:|
| 2026-09-27T06:39:38+0300 | 1 | 2 | 4 |
| 2026-09-27T06:39:44+0300 | 2 | 4 | 4 |
| 2026-09-27T06:39:52+0300 | 3 | 8 | 4 |
| 2026-09-27T06:40:08+0300 | 1 | 2 | 4 |
| 2026-09-27T06:40:15+0300 | 2 | 4 | 4 |
| 2026-09-27T06:40:23+0300 | 3 | 8 | 4 |

Retry records do not contain query IDs. Do not assign each event to a failed row.
Do not equate retry-event counts with remote model starts or actual upstream request counts.

## Raw saved metrics

The [archived metrics.json](g9-failed-run-artifacts/metrics.json) is unchanged.
The JSON evidence also contains the complete original metrics object.

| Saved metric | Value |
|---|---:|
| Positive denominator | 1644 |
| Positive answered / errors / no answer | 1636 / 8 / 8 |
| Positive R@1 | 0.7676 |
| Positive R@5 | 0.9319 |
| Negative denominator / errors | 584 / 0 |
| Forbidden negative top-1 / top-10 | 97 / 465 |
| Saved latency median / p95 / max, ms | 138 / 241 / 49806 |
| Saved `within_sla` / `within_sla_share` | 2216 / 0.9946 |

The saved latency summary sets `comparable=false`.
The saved SLA field is not a fresh sequential HTTP measurement or a correct-within-deadline claim.
The run uses four workers and `use_cache=true`. Its configured pipeline has no barcode stage.

## Validation limits

The failed attempt did not save `run`, `metrics`, or `artifact_sha256` completion fields.
This audit preserves the existing artifacts and establishes their hashes separately.
It does not modify the queue or promote the attempt to `done`.
It does not claim completion-time stability of live catalogue or index state.
The eight errors must remain visible in final profile comparisons.

- [Frozen attempt](attempts/siglip2-p14-384-as-is-a2e911af73cb472db6fafe8794cf0cd5/attempt.json).
- [Archived job log](attempts/siglip2-p14-384-as-is-a2e911af73cb472db6fafe8794cf0cd5/job.log).
- [Archived run metadata](g9-failed-run-artifacts/run.json).
- [Failure evidence and all artifact hashes](g9-failed-run-evidence.json).
