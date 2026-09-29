# Offline HTTP recognition comparison

Status: partial.
Profile: `barcode-rerank-siglip2-512-crop`.
Scope: Loopback HTTP through complete response; excludes browser rendering and remote client network.
Selection: `3b1fd11b30778da43042b04158b1cf820f92e53c7ffe5f360c241ce38dac9763`.
Selected rows: 64. Unique images: 61. Labels: {'positive': 54, 'negative': 10}.

## Full selected sample

| Mode / variant | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Late correct | Error / degraded / censored | HTTP p50 / p95 / p99 ms |
|---|---:|---:|---:|---:|---:|---:|
| process / full | 3 / 64 | 3 / 64 | 3 / 54 | 0 | 0 / 0 / 0 | 1531.4 / 2630.8 / 2630.8 |
| process / whole | 0 / 64 | 0 / 64 | 0 / 54 | 0 | 0 / 0 / 0 | — / — / — |
| process / photo4 | 0 / 64 | 0 / 64 | 0 / 54 | 0 | 0 / 0 / 0 | — / — / — |
| process / whole-fresh-barcode | 0 / 64 | 0 / 64 | 0 / 54 | 0 | 0 / 0 / 0 | — / — / — |
| persistent / full | 0 / 64 | 0 / 64 | 0 / 54 | 0 | 0 / 0 / 0 | — / — / — |
| persistent / whole | 0 / 64 | 0 / 64 | 0 / 54 | 0 | 0 / 0 / 0 | — / — / — |
| persistent / photo4 | 0 / 64 | 0 / 64 | 0 / 54 | 0 | 0 / 0 / 0 | — / — / — |
| persistent / whole-fresh-barcode | 0 / 64 | 0 / 64 | 0 / 54 | 0 | 0 / 0 / 0 | — / — / — |

## process / full

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 0 / 24 | 0 / 24 | 0 / 24 | 0 / 0 |
| other_selected_rows | 3 / 40 | 3 / 40 | 3 / 30 | 0 / 10 |
| positive | 3 / 54 | 3 / 54 | 3 / 54 | 0 / 0 |
| negative_constraint | 0 / 10 | 0 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 3 / 62 | 3 / 62 | 3 / 52 | 0 / 10 |
| after_session_first_observed | 2 / 2 | 2 / 2 | 2 / 2 | 0 / 0 |

First requests: `[{"query_id": "q-001089", "http_wall_ms": 1531.4480420202017, "startup_ms": 457.0314580341801, "build_ms": 188.30920790787786, "service_setup_ms": 83.57862499542534, "censored": false}]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 3 | 379.9 | 457.0 | 457.0 |
| build_ms | 3 | 178.1 | 188.3 | 188.3 |
| ask_wall_ms | 3 | 860.3 | 1460.3 | 1460.3 |
| service_setup_ms | 3 | 0.0 | 83.6 | 83.6 |
| source_read_ms | 3 | 1.7 | 3.2 | 3.2 |
| json_parse_ms | 3 | 1.0 | 2.7 | 2.7 |
| upload_ms | 3 | 41.4 | 48.6 | 48.6 |
| steps_answer_ms | 3 | 88.9 | 661.4 | 661.4 |
| process_ms | 3 | 1360.7 | 1878.8 | 1878.8 |
| worker_request_ms | 3 | 860.8 | 1460.9 | 1460.9 |
| cleanup_ms | 3 | 42.8 | 43.0 | 43.0 |

## process / whole

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 0 / 24 | 0 / 24 | 0 / 24 | 0 / 0 |
| other_selected_rows | 0 / 40 | 0 / 40 | 0 / 30 | 0 / 10 |
| positive | 0 / 54 | 0 / 54 | 0 / 54 | 0 / 0 |
| negative_constraint | 0 / 10 | 0 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 0 / 62 | 0 / 62 | 0 / 52 | 0 / 10 |
| after_session_first_observed | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

First requests: `[]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 0 | — | — | — |
| build_ms | 0 | — | — | — |
| ask_wall_ms | 0 | — | — | — |
| service_setup_ms | 0 | — | — | — |
| source_read_ms | 0 | — | — | — |
| json_parse_ms | 0 | — | — | — |
| upload_ms | 0 | — | — | — |
| steps_answer_ms | 0 | — | — | — |
| process_ms | 0 | — | — | — |
| worker_request_ms | 0 | — | — | — |
| cleanup_ms | 0 | — | — | — |

## process / photo4

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 0 / 24 | 0 / 24 | 0 / 24 | 0 / 0 |
| other_selected_rows | 0 / 40 | 0 / 40 | 0 / 30 | 0 / 10 |
| positive | 0 / 54 | 0 / 54 | 0 / 54 | 0 / 0 |
| negative_constraint | 0 / 10 | 0 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 0 / 62 | 0 / 62 | 0 / 52 | 0 / 10 |
| after_session_first_observed | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

First requests: `[]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 0 | — | — | — |
| build_ms | 0 | — | — | — |
| ask_wall_ms | 0 | — | — | — |
| service_setup_ms | 0 | — | — | — |
| source_read_ms | 0 | — | — | — |
| json_parse_ms | 0 | — | — | — |
| upload_ms | 0 | — | — | — |
| steps_answer_ms | 0 | — | — | — |
| process_ms | 0 | — | — | — |
| worker_request_ms | 0 | — | — | — |
| cleanup_ms | 0 | — | — | — |

## process / whole-fresh-barcode

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 0 / 24 | 0 / 24 | 0 / 24 | 0 / 0 |
| other_selected_rows | 0 / 40 | 0 / 40 | 0 / 30 | 0 / 10 |
| positive | 0 / 54 | 0 / 54 | 0 / 54 | 0 / 0 |
| negative_constraint | 0 / 10 | 0 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 0 / 62 | 0 / 62 | 0 / 52 | 0 / 10 |
| after_session_first_observed | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

First requests: `[]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 0 | — | — | — |
| build_ms | 0 | — | — | — |
| ask_wall_ms | 0 | — | — | — |
| service_setup_ms | 0 | — | — | — |
| source_read_ms | 0 | — | — | — |
| json_parse_ms | 0 | — | — | — |
| upload_ms | 0 | — | — | — |
| steps_answer_ms | 0 | — | — | — |
| process_ms | 0 | — | — | — |
| worker_request_ms | 0 | — | — | — |
| cleanup_ms | 0 | — | — | — |

## persistent / full

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 0 / 24 | 0 / 24 | 0 / 24 | 0 / 0 |
| other_selected_rows | 0 / 40 | 0 / 40 | 0 / 30 | 0 / 10 |
| positive | 0 / 54 | 0 / 54 | 0 / 54 | 0 / 0 |
| negative_constraint | 0 / 10 | 0 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 0 / 62 | 0 / 62 | 0 / 52 | 0 / 10 |
| after_session_first_observed | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

First requests: `[]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 0 | — | — | — |
| build_ms | 0 | — | — | — |
| ask_wall_ms | 0 | — | — | — |
| service_setup_ms | 0 | — | — | — |
| source_read_ms | 0 | — | — | — |
| json_parse_ms | 0 | — | — | — |
| upload_ms | 0 | — | — | — |
| steps_answer_ms | 0 | — | — | — |
| process_ms | 0 | — | — | — |
| worker_request_ms | 0 | — | — | — |
| cleanup_ms | 0 | — | — | — |

## persistent / whole

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 0 / 24 | 0 / 24 | 0 / 24 | 0 / 0 |
| other_selected_rows | 0 / 40 | 0 / 40 | 0 / 30 | 0 / 10 |
| positive | 0 / 54 | 0 / 54 | 0 / 54 | 0 / 0 |
| negative_constraint | 0 / 10 | 0 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 0 / 62 | 0 / 62 | 0 / 52 | 0 / 10 |
| after_session_first_observed | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

First requests: `[]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 0 | — | — | — |
| build_ms | 0 | — | — | — |
| ask_wall_ms | 0 | — | — | — |
| service_setup_ms | 0 | — | — | — |
| source_read_ms | 0 | — | — | — |
| json_parse_ms | 0 | — | — | — |
| upload_ms | 0 | — | — | — |
| steps_answer_ms | 0 | — | — | — |
| process_ms | 0 | — | — | — |
| worker_request_ms | 0 | — | — | — |
| cleanup_ms | 0 | — | — | — |

## persistent / photo4

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 0 / 24 | 0 / 24 | 0 / 24 | 0 / 0 |
| other_selected_rows | 0 / 40 | 0 / 40 | 0 / 30 | 0 / 10 |
| positive | 0 / 54 | 0 / 54 | 0 / 54 | 0 / 0 |
| negative_constraint | 0 / 10 | 0 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 0 / 62 | 0 / 62 | 0 / 52 | 0 / 10 |
| after_session_first_observed | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

First requests: `[]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 0 | — | — | — |
| build_ms | 0 | — | — | — |
| ask_wall_ms | 0 | — | — | — |
| service_setup_ms | 0 | — | — | — |
| source_read_ms | 0 | — | — | — |
| json_parse_ms | 0 | — | — | — |
| upload_ms | 0 | — | — | — |
| steps_answer_ms | 0 | — | — | — |
| process_ms | 0 | — | — | — |
| worker_request_ms | 0 | — | — | — |
| cleanup_ms | 0 | — | — | — |

## persistent / whole-fresh-barcode

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 0 / 24 | 0 / 24 | 0 / 24 | 0 / 0 |
| other_selected_rows | 0 / 40 | 0 / 40 | 0 / 30 | 0 / 10 |
| positive | 0 / 54 | 0 / 54 | 0 / 54 | 0 / 0 |
| negative_constraint | 0 / 10 | 0 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 0 / 62 | 0 / 62 | 0 / 52 | 0 / 10 |
| after_session_first_observed | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

First requests: `[]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 0 | — | — | — |
| build_ms | 0 | — | — | — |
| ask_wall_ms | 0 | — | — | — |
| service_setup_ms | 0 | — | — | — |
| source_read_ms | 0 | — | — | — |
| json_parse_ms | 0 | — | — | — |
| upload_ms | 0 | — | — | — |
| steps_answer_ms | 0 | — | — | — |
| process_ms | 0 | — | — | — |
| worker_request_ms | 0 | — | — | — |
| cleanup_ms | 0 | — | — | — |

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
