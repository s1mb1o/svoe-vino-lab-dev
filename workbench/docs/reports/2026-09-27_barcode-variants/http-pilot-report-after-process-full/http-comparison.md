# Offline HTTP recognition comparison

Status: partial.
Profile: `barcode-rerank-siglip2-512-crop`.
Scope: Loopback HTTP through complete response; excludes browser rendering and remote client network.
Selection: `3b1fd11b30778da43042b04158b1cf820f92e53c7ffe5f360c241ce38dac9763`.
Selected rows: 64. Unique images: 61. Labels: {'positive': 54, 'negative': 10}.

## Full selected sample

| Mode / variant | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Late correct | Error / degraded / censored | HTTP p50 / p95 / p99 ms |
|---|---:|---:|---:|---:|---:|---:|
| process / full | 64 / 64 | 45 / 64 | 35 / 54 | 9 | 1 / 0 / 0 | 1498.6 / 6700.5 / 300700.7 |
| process / whole | 5 / 64 | 3 / 64 | 3 / 54 | 1 | 0 / 0 / 0 | 2485.0 / 6579.4 / 6579.4 |
| process / photo4 | 0 / 64 | 0 / 64 | 0 / 54 | 0 | 0 / 0 / 0 | — / — / — |
| process / whole-fresh-barcode | 0 / 64 | 0 / 64 | 0 / 54 | 0 | 0 / 0 / 0 | — / — / — |
| persistent / full | 0 / 64 | 0 / 64 | 0 / 54 | 0 | 0 / 0 / 0 | — / — / — |
| persistent / whole | 0 / 64 | 0 / 64 | 0 / 54 | 0 | 0 / 0 / 0 | — / — / — |
| persistent / photo4 | 0 / 64 | 0 / 64 | 0 / 54 | 0 | 0 / 0 / 0 | — / — / — |
| persistent / whole-fresh-barcode | 0 / 64 | 0 / 64 | 0 / 54 | 0 | 0 / 0 / 0 | — / — / — |

## process / full

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 24 / 24 | 24 / 24 | 24 / 24 | 0 / 0 |
| other_selected_rows | 40 / 40 | 21 / 40 | 11 / 30 | 0 / 10 |
| positive | 54 / 54 | 36 / 54 | 35 / 54 | 0 / 0 |
| negative_constraint | 10 / 10 | 9 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 62 / 62 | 45 / 62 | 35 / 52 | 0 / 10 |
| after_session_first_observed | 62 / 62 | 44 / 62 | 34 / 52 | 0 / 10 |

First requests: `[{"query_id": "q-001089", "http_wall_ms": 1531.4480420202017, "startup_ms": 457.0314580341801, "build_ms": 188.30920790787786, "service_setup_ms": 83.57862499542534, "censored": false}, {"query_id": "q-000063", "http_wall_ms": 4932.597709004767, "startup_ms": 507.9615409485996, "build_ms": 193.66341596469283, "service_setup_ms": 80.73083299677819, "censored": false}]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: `q-000078`.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 64 | 390.6 | 457.0 | 621.5 |
| build_ms | 64 | 183.7 | 200.5 | 236.0 |
| ask_wall_ms | 64 | 847.2 | 4304.2 | 6204.7 |
| service_setup_ms | 64 | 0.0 | 0.0 | 83.6 |
| source_read_ms | 64 | 2.5 | 5.4 | 16.4 |
| json_parse_ms | 64 | 1.4 | 4.4 | 5.7 |
| upload_ms | 64 | 9.6 | 267.7 | 583.4 |
| steps_answer_ms | 63 | 133.4 | 1013.2 | 1108.2 |
| process_ms | 63 | 1291.2 | 4732.3 | 6676.7 |
| worker_request_ms | 63 | 852.1 | 4304.8 | 6205.5 |
| cleanup_ms | 63 | 42.1 | 78.4 | 81.7 |

Saved failure: `RuntimeError: HTTP recognition failed or degraded; stop before the next image`.

## process / whole

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 0 / 24 | 0 / 24 | 0 / 24 | 0 / 0 |
| other_selected_rows | 5 / 40 | 3 / 40 | 3 / 30 | 0 / 10 |
| positive | 5 / 54 | 3 / 54 | 3 / 54 | 0 / 0 |
| negative_constraint | 0 / 10 | 0 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 5 / 62 | 3 / 62 | 3 / 52 | 0 / 10 |
| after_session_first_observed | 4 / 4 | 2 / 4 | 2 / 4 | 0 / 0 |

First requests: `[{"query_id": "q-001089", "http_wall_ms": 1151.7333339434117, "startup_ms": 360.1892499718815, "build_ms": 169.40195800270885, "service_setup_ms": 2.7769580483436584, "censored": false}]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 5 | 380.8 | 416.2 | 416.2 |
| build_ms | 5 | 179.3 | 187.2 | 187.2 |
| ask_wall_ms | 5 | 1303.7 | 4786.5 | 4786.5 |
| service_setup_ms | 5 | 0.0 | 2.8 | 2.8 |
| source_read_ms | 5 | 2.6 | 8.3 | 8.3 |
| json_parse_ms | 5 | 2.2 | 2.7 | 2.7 |
| upload_ms | 5 | 13.2 | 184.9 | 184.9 |
| steps_answer_ms | 5 | 287.3 | 1121.2 | 1121.2 |
| process_ms | 5 | 1727.9 | 5231.3 | 5231.3 |
| worker_request_ms | 5 | 1304.3 | 4787.2 | 4787.2 |
| cleanup_ms | 5 | 45.3 | 52.3 | 52.3 |

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
