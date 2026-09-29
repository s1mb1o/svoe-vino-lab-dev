# Offline HTTP recognition comparison

Status: complete.
Profile: `barcode-siglip2-512-crop`.
Scope: Loopback HTTP through complete response; excludes browser rendering and remote client network.
Selection: `3b1fd11b30778da43042b04158b1cf820f92e53c7ffe5f360c241ce38dac9763`.
Selected rows: 64. Unique images: 61. Labels: {'positive': 54, 'negative': 10}.

## Full selected sample

| Mode / variant | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Late correct | Error / degraded / censored | HTTP p50 / p95 / p99 ms |
|---|---:|---:|---:|---:|---:|---:|
| persistent / photo4 | 64 / 64 | 58 / 64 | 40 / 54 | 4 | 0 / 0 / 0 | 890.7 / 3345.1 / 3608.5 |

## persistent / photo4

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 24 / 24 | 24 / 24 | 24 / 24 | 0 / 0 |
| other_selected_rows | 40 / 40 | 34 / 40 | 16 / 30 | 0 / 10 |
| positive | 54 / 54 | 49 / 54 | 40 / 54 | 0 / 0 |
| negative_constraint | 10 / 10 | 9 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 62 / 62 | 58 / 62 | 40 / 52 | 0 / 10 |
| after_session_first_observed | 63 / 63 | 57 / 63 | 39 / 53 | 0 / 10 |

First requests: `[{"query_id": "q-001089", "http_wall_ms": 1220.551292062737, "startup_ms": 413.99158304557204, "build_ms": 137.14599993545562, "service_setup_ms": 73.77279200591147, "censored": false}]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | Missing | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|---:|
| startup_ms | 64 | 0 | 0.0 | 0.0 | 414.0 |
| build_ms | 64 | 0 | 0.0 | 0.0 | 137.1 |
| ask_wall_ms | 64 | 0 | 711.1 | 1986.6 | 2115.4 |
| service_setup_ms | 64 | 0 | 0.0 | 0.0 | 73.8 |
| source_read_ms | 64 | 0 | 2.2 | 6.5 | 17.8 |
| json_parse_ms | 64 | 0 | 1.4 | 5.0 | 5.8 |
| upload_ms | 64 | 0 | 6.6 | 245.6 | 519.3 |
| steps_answer_ms | 64 | 0 | 139.4 | 1000.3 | 1147.9 |
| process_ms | 64 | 0 | 714.4 | 1987.3 | 2116.4 |
| worker_request_ms | 64 | 0 | 712.5 | 1987.3 | 2116.4 |
| cleanup_ms | 64 | 0 | 0.0 | 0.0 | 0.0 |

## Measurement limits

- Failed and censored observations remain in selected-row and positive denominators.
- Pending rows are listed separately. Partial selected-denominator rates are provisional lower bounds.
- After-first statistics exclude each session's first observation, including resumed sessions.
- After-first does not prove warm remote models. A later request can trigger a cold model load; compare per-query stage times with the saved service preflight.
- Process mode still starts a child for every after-first observation. It is not a persistent warm backend.
- Service setup, client source-file reads, and client JSON parsing are outside HTTP wall time.
- Upload and step-view timing are inside HTTP wall time. Startup, build, ask, process, and stage timings overlap.
- Missing child startup, build, and ask timings are excluded from component statistics. Route placeholder zeros do not measure zero work. HTTP failures stay in all applicable latency and success denominators.
- Censored waits are lower bounds. Complete-response quantiles exclude them, but success rates retain them.
- Negative labels constrain excluded wines. An allowed prediction does not prove a correct identification.
- Backend top-1 and top-5 prediction counts can include a response that later failed or degraded.
- The pilot oversamples barcode hits. Its deadline fraction is not a corpus estimate.
- The experimental child imports differ from production recognize.py. No enforced 3-second timeout is established.
