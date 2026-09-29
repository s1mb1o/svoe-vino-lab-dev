# Offline HTTP recognition comparison

Status: complete.
Profile: `barcode-siglip2-512-as-is`.
Scope: Loopback HTTP through complete response; excludes browser rendering and remote client network.
Selection: `3b1fd11b30778da43042b04158b1cf820f92e53c7ffe5f360c241ce38dac9763`.
Selected rows: 64. Unique images: 61. Labels: {'positive': 54, 'negative': 10}.

## Full selected sample

| Mode / variant | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Late correct | Error / degraded / censored | HTTP p50 / p95 / p99 ms |
|---|---:|---:|---:|---:|---:|---:|
| persistent / whole | 64 / 64 | 64 / 64 | 42 / 54 | 0 | 0 / 0 / 0 | 277.0 / 1556.8 / 2098.7 |
| persistent / photo4 | 64 / 64 | 64 / 64 | 43 / 54 | 0 | 0 / 0 / 0 | 305.4 / 1634.4 / 2158.0 |

## persistent / whole

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 24 / 24 | 24 / 24 | 23 / 24 | 0 / 0 |
| other_selected_rows | 40 / 40 | 40 / 40 | 19 / 30 | 1 / 10 |
| positive | 54 / 54 | 54 / 54 | 42 / 54 | 0 / 0 |
| negative_constraint | 10 / 10 | 10 / 10 | 0 / 0 | 1 / 10 |
| sensitivity | 62 / 62 | 62 / 62 | 41 / 52 | 1 / 10 |
| after_session_first_observed | 63 / 63 | 63 / 63 | 41 / 53 | 1 / 10 |

First requests: `[{"query_id": "q-001089", "http_wall_ms": 693.0730829481035, "startup_ms": 423.759458004497, "build_ms": 135.7129169628024, "service_setup_ms": 72.82612496055663, "censored": false}]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 64 | 0.0 | 0.0 | 423.8 |
| build_ms | 64 | 0.0 | 0.0 | 135.7 |
| ask_wall_ms | 64 | 144.7 | 845.2 | 1035.9 |
| service_setup_ms | 64 | 0.0 | 0.0 | 72.8 |
| source_read_ms | 64 | 2.2 | 11.3 | 20.9 |
| json_parse_ms | 64 | 1.1 | 3.2 | 3.4 |
| upload_ms | 64 | 8.6 | 214.5 | 498.1 |
| steps_answer_ms | 64 | 66.7 | 455.6 | 519.2 |
| process_ms | 64 | 145.3 | 845.9 | 1036.5 |
| worker_request_ms | 64 | 145.3 | 845.9 | 1036.5 |
| cleanup_ms | 64 | 0.0 | 0.0 | 0.0 |

## persistent / photo4

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 24 / 24 | 24 / 24 | 24 / 24 | 0 / 0 |
| other_selected_rows | 40 / 40 | 40 / 40 | 19 / 30 | 1 / 10 |
| positive | 54 / 54 | 54 / 54 | 43 / 54 | 0 / 0 |
| negative_constraint | 10 / 10 | 10 / 10 | 0 / 0 | 1 / 10 |
| sensitivity | 62 / 62 | 62 / 62 | 42 / 52 | 1 / 10 |
| after_session_first_observed | 63 / 63 | 63 / 63 | 42 / 53 | 1 / 10 |

First requests: `[{"query_id": "q-001089", "http_wall_ms": 630.9817499713972, "startup_ms": 395.47316695097834, "build_ms": 125.71899988688529, "service_setup_ms": 3.6115419352427125, "censored": false}]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 64 | 0.0 | 0.0 | 395.5 |
| build_ms | 64 | 0.0 | 0.0 | 125.7 |
| ask_wall_ms | 64 | 175.4 | 906.4 | 1096.8 |
| service_setup_ms | 64 | 0.0 | 0.0 | 3.6 |
| source_read_ms | 64 | 2.3 | 7.4 | 19.9 |
| json_parse_ms | 64 | 1.0 | 3.2 | 3.4 |
| upload_ms | 64 | 5.9 | 209.9 | 490.4 |
| steps_answer_ms | 64 | 71.3 | 494.3 | 526.1 |
| process_ms | 64 | 180.4 | 906.9 | 1097.4 |
| worker_request_ms | 64 | 175.9 | 906.9 | 1097.4 |
| cleanup_ms | 64 | 0.0 | 0.0 | 0.0 |

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
