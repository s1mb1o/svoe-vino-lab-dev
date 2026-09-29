# Offline HTTP recognition comparison

Status: complete.
Profile: `barcode-rerank-siglip2-512-crop`.
Scope: Loopback HTTP through complete response; excludes browser rendering and remote client network.
Selection: `0686b5bd8b64fa2be1baf2fb6932e96b80ac554b8f9d14ea99f9591f3f6d53a5`.
Selected rows: 24. Unique images: 24. Labels: {'positive': 24}.

## Full selected sample

| Mode / variant | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Late correct | Error / degraded / censored | HTTP p50 / p95 / p99 ms |
|---|---:|---:|---:|---:|---:|---:|
| persistent / fresh-bottle | 24 / 24 | 23 / 24 | 18 / 24 | 0 | 0 / 0 / 0 | 1128.9 / 2333.7 / 5373.0 |
| persistent / fresh-label | 24 / 24 | 24 / 24 | 18 / 24 | 0 | 0 / 0 / 0 | 1181.5 / 2098.3 / 2145.8 |
| persistent / fresh-barcode | 24 / 24 | 24 / 24 | 22 / 24 | 0 | 0 / 0 / 0 | 1006.8 / 1528.3 / 1811.5 |

## persistent / fresh-bottle

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 24 / 24 | 23 / 24 | 18 / 24 | 0 / 0 |
| other_selected_rows | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| positive | 24 / 24 | 23 / 24 | 18 / 24 | 0 / 0 |
| negative_constraint | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| sensitivity | 24 / 24 | 23 / 24 | 18 / 24 | 0 / 0 |
| after_session_first_observed | 23 / 23 | 22 / 23 | 17 / 23 | 0 / 0 |

First requests: `[{"query_id": "q-001668", "http_wall_ms": 1511.268166010268, "startup_ms": 483.21437498088926, "build_ms": 194.89291706122458, "service_setup_ms": 78.96312500815839, "censored": false}]`.
Sensitivity excludes: ``.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 24 | 0.0 | 0.0 | 483.2 |
| build_ms | 24 | 0.0 | 0.0 | 194.9 |
| ask_wall_ms | 24 | 981.2 | 1788.5 | 4811.5 |
| service_setup_ms | 24 | 0.0 | 0.0 | 79.0 |
| source_read_ms | 24 | 1.7 | 5.0 | 10.0 |
| json_parse_ms | 24 | 0.0 | 6.3 | 6.5 |
| upload_ms | 24 | 7.2 | 69.2 | 86.2 |
| steps_answer_ms | 24 | 38.4 | 453.7 | 465.7 |
| process_ms | 24 | 993.6 | 1789.1 | 4812.4 |
| worker_request_ms | 24 | 981.7 | 1789.1 | 4812.4 |
| cleanup_ms | 24 | 0.0 | 0.0 | 0.0 |

## persistent / fresh-label

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 24 / 24 | 24 / 24 | 18 / 24 | 0 / 0 |
| other_selected_rows | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| positive | 24 / 24 | 24 / 24 | 18 / 24 | 0 / 0 |
| negative_constraint | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| sensitivity | 24 / 24 | 24 / 24 | 18 / 24 | 0 / 0 |
| after_session_first_observed | 23 / 23 | 23 / 23 | 17 / 23 | 0 / 0 |

First requests: `[{"query_id": "q-001668", "http_wall_ms": 1702.000041026622, "startup_ms": 574.4026249740273, "build_ms": 173.04070899263024, "service_setup_ms": 2.156791975721717, "censored": false}]`.
Sensitivity excludes: ``.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 24 | 0.0 | 0.0 | 574.4 |
| build_ms | 24 | 0.0 | 0.0 | 173.0 |
| ask_wall_ms | 24 | 1056.4 | 1750.5 | 1782.4 |
| service_setup_ms | 24 | 0.0 | 0.0 | 2.2 |
| source_read_ms | 24 | 1.7 | 8.5 | 28.0 |
| json_parse_ms | 24 | 0.0 | 5.7 | 7.8 |
| upload_ms | 24 | 6.1 | 65.5 | 66.5 |
| steps_answer_ms | 24 | 63.5 | 298.1 | 310.8 |
| process_ms | 24 | 1068.6 | 1751.1 | 1783.1 |
| worker_request_ms | 24 | 1057.0 | 1751.1 | 1783.1 |
| cleanup_ms | 24 | 0.0 | 0.0 | 0.0 |

## persistent / fresh-barcode

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 24 / 24 | 24 / 24 | 22 / 24 | 0 / 0 |
| other_selected_rows | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| positive | 24 / 24 | 24 / 24 | 22 / 24 | 0 / 0 |
| negative_constraint | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| sensitivity | 24 / 24 | 24 / 24 | 22 / 24 | 0 / 0 |
| after_session_first_observed | 23 / 23 | 23 / 23 | 21 / 23 | 0 / 0 |

First requests: `[{"query_id": "q-001668", "http_wall_ms": 1528.2627909909934, "startup_ms": 482.4899169616401, "build_ms": 189.48549998458475, "service_setup_ms": 3.2775410218164325, "censored": false}]`.
Sensitivity excludes: ``.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 24 | 0.0 | 0.0 | 482.5 |
| build_ms | 24 | 0.0 | 0.0 | 189.5 |
| ask_wall_ms | 24 | 884.5 | 1181.3 | 1505.9 |
| service_setup_ms | 24 | 0.0 | 0.0 | 3.3 |
| source_read_ms | 24 | 1.6 | 2.7 | 11.6 |
| json_parse_ms | 24 | 0.0 | 2.0 | 2.5 |
| upload_ms | 24 | 6.3 | 62.8 | 63.6 |
| steps_answer_ms | 24 | 23.5 | 92.6 | 257.2 |
| process_ms | 24 | 885.1 | 1457.0 | 1506.6 |
| worker_request_ms | 24 | 885.1 | 1181.9 | 1506.6 |
| cleanup_ms | 24 | 0.0 | 0.0 | 0.0 |

## Measurement limits

- Failed and censored observations remain in selected-row and positive denominators.
- Pending rows are listed separately. Partial selected-denominator rates are provisional lower bounds.
- After-first statistics exclude each session's first observation, including resumed sessions.
- After-first does not prove warm remote models. A later request can trigger a cold model load; compare per-query stage times with the saved service preflight.
- Process mode still starts a child for every after-first observation. It is not a persistent warm backend.
- Service setup, client source-file reads, and client JSON parsing are outside HTTP wall time.
- Upload and step-view timing are inside HTTP wall time. Startup, build, ask, process, and stage timings overlap.
- Censored waits are lower bounds. Complete-response quantiles exclude them, but success rates retain them.
- Negative labels constrain excluded wines. An allowed prediction does not prove a correct identification.
- Backend top-1 and top-5 prediction counts can include a response that later failed or degraded.
- The pilot oversamples barcode hits. Its deadline fraction is not a corpus estimate.
- The experimental child imports differ from production recognize.py. No enforced 3-second timeout is established.
