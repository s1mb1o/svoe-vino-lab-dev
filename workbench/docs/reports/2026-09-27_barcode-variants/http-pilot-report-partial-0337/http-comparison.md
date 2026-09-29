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
| process / whole | 64 / 64 | 45 / 64 | 34 / 54 | 10 | 0 / 0 / 0 | 1343.5 / 6575.6 / 8011.1 |
| process / photo4 | 64 / 64 | 45 / 64 | 35 / 54 | 10 | 0 / 0 / 0 | 1404.0 / 6497.0 / 9478.7 |
| process / whole-fresh-barcode | 64 / 64 | 38 / 64 | 32 / 54 | 13 | 0 / 0 / 0 | 1970.4 / 7391.5 / 8793.9 |
| persistent / full | 64 / 64 | 49 / 64 | 38 / 54 | 7 | 0 / 0 / 0 | 1037.1 / 5936.1 / 7784.3 |
| persistent / whole | 64 / 64 | 51 / 64 | 38 / 54 | 6 | 0 / 0 / 0 | 877.6 / 5812.9 / 7758.6 |
| persistent / photo4 | 32 / 64 | 26 / 64 | 21 / 54 | 4 | 0 / 0 / 0 | 896.1 / 6074.8 / 6274.7 |
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
| baseline_barcode_hit | 24 / 24 | 24 / 24 | 23 / 24 | 0 / 0 |
| other_selected_rows | 40 / 40 | 21 / 40 | 11 / 30 | 0 / 10 |
| positive | 54 / 54 | 36 / 54 | 34 / 54 | 0 / 0 |
| negative_constraint | 10 / 10 | 9 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 62 / 62 | 45 / 62 | 34 / 52 | 0 / 10 |
| after_session_first_observed | 63 / 63 | 44 / 63 | 33 / 53 | 0 / 10 |

First requests: `[{"query_id": "q-001089", "http_wall_ms": 1151.7333339434117, "startup_ms": 360.1892499718815, "build_ms": 169.40195800270885, "service_setup_ms": 2.7769580483436584, "censored": false}]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 64 | 388.8 | 429.6 | 446.5 |
| build_ms | 64 | 182.5 | 199.9 | 222.8 |
| ask_wall_ms | 64 | 708.4 | 4758.4 | 5998.2 |
| service_setup_ms | 64 | 0.0 | 0.0 | 2.8 |
| source_read_ms | 64 | 2.3 | 6.4 | 16.2 |
| json_parse_ms | 64 | 1.4 | 4.8 | 6.3 |
| upload_ms | 64 | 7.5 | 262.1 | 518.5 |
| steps_answer_ms | 64 | 131.2 | 997.9 | 1121.2 |
| process_ms | 64 | 1140.7 | 5219.7 | 6448.1 |
| worker_request_ms | 64 | 709.0 | 4759.3 | 5999.1 |
| cleanup_ms | 64 | 42.9 | 79.8 | 84.7 |

## process / photo4

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 24 / 24 | 24 / 24 | 24 / 24 | 0 / 0 |
| other_selected_rows | 40 / 40 | 21 / 40 | 11 / 30 | 0 / 10 |
| positive | 54 / 54 | 36 / 54 | 35 / 54 | 0 / 0 |
| negative_constraint | 10 / 10 | 9 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 62 / 62 | 45 / 62 | 35 / 52 | 0 / 10 |
| after_session_first_observed | 63 / 63 | 44 / 63 | 34 / 53 | 0 / 10 |

First requests: `[{"query_id": "q-001089", "http_wall_ms": 1182.928082998842, "startup_ms": 377.8554580640048, "build_ms": 176.67429195716977, "service_setup_ms": 2.6169170159846544, "censored": false}]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 64 | 394.6 | 428.5 | 511.5 |
| build_ms | 64 | 184.0 | 202.4 | 246.9 |
| ask_wall_ms | 64 | 748.6 | 4613.6 | 7386.3 |
| service_setup_ms | 64 | 0.0 | 0.0 | 2.6 |
| source_read_ms | 64 | 2.2 | 9.4 | 20.2 |
| json_parse_ms | 64 | 1.5 | 4.5 | 5.1 |
| upload_ms | 64 | 7.8 | 263.9 | 514.8 |
| steps_answer_ms | 64 | 141.6 | 1038.8 | 1154.2 |
| process_ms | 64 | 1192.9 | 5116.0 | 7887.9 |
| worker_request_ms | 64 | 749.1 | 4614.8 | 7387.6 |
| cleanup_ms | 64 | 42.4 | 83.1 | 86.2 |

## process / whole-fresh-barcode

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 24 / 24 | 24 / 24 | 24 / 24 | 0 / 0 |
| other_selected_rows | 40 / 40 | 14 / 40 | 8 / 30 | 0 / 10 |
| positive | 54 / 54 | 33 / 54 | 32 / 54 | 0 / 0 |
| negative_constraint | 10 / 10 | 5 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 62 / 62 | 38 / 62 | 32 / 52 | 0 / 10 |
| after_session_first_observed | 63 / 63 | 37 / 63 | 31 / 53 | 0 / 10 |

First requests: `[{"query_id": "q-001089", "http_wall_ms": 1705.4948749719188, "startup_ms": 371.2772080907598, "build_ms": 170.81412498373538, "service_setup_ms": 2.2792089730501175, "censored": false}]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 64 | 396.3 | 512.1 | 631.5 |
| build_ms | 64 | 184.6 | 223.9 | 367.5 |
| ask_wall_ms | 64 | 1337.0 | 5623.8 | 6779.5 |
| service_setup_ms | 64 | 0.0 | 0.0 | 2.3 |
| source_read_ms | 64 | 2.5 | 7.9 | 16.7 |
| json_parse_ms | 64 | 1.5 | 4.1 | 11.1 |
| upload_ms | 64 | 6.5 | 254.5 | 523.3 |
| steps_answer_ms | 64 | 137.0 | 999.3 | 1126.7 |
| process_ms | 64 | 1791.3 | 6098.6 | 7225.5 |
| worker_request_ms | 64 | 1338.1 | 5624.9 | 6780.3 |
| cleanup_ms | 64 | 42.9 | 81.5 | 88.9 |

## persistent / full

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 24 / 24 | 24 / 24 | 24 / 24 | 0 / 0 |
| other_selected_rows | 40 / 40 | 25 / 40 | 14 / 30 | 0 / 10 |
| positive | 54 / 54 | 40 / 54 | 38 / 54 | 0 / 0 |
| negative_constraint | 10 / 10 | 9 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 62 / 62 | 49 / 62 | 38 / 52 | 0 / 10 |
| after_session_first_observed | 63 / 63 | 48 / 63 | 37 / 53 | 0 / 10 |

First requests: `[{"query_id": "q-001089", "http_wall_ms": 1255.948832957074, "startup_ms": 432.25245794747025, "build_ms": 181.6142089664936, "service_setup_ms": 3.2970000756904483, "censored": false}]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 64 | 0.0 | 0.0 | 432.3 |
| build_ms | 64 | 0.0 | 0.0 | 181.6 |
| ask_wall_ms | 64 | 808.2 | 4566.4 | 6198.4 |
| service_setup_ms | 64 | 0.0 | 0.0 | 3.3 |
| source_read_ms | 64 | 2.2 | 6.0 | 16.0 |
| json_parse_ms | 64 | 1.4 | 4.1 | 6.9 |
| upload_ms | 64 | 6.2 | 240.6 | 580.0 |
| steps_answer_ms | 64 | 131.7 | 1050.7 | 1304.5 |
| process_ms | 64 | 833.0 | 4567.2 | 6199.8 |
| worker_request_ms | 64 | 808.8 | 4567.2 | 6199.7 |
| cleanup_ms | 64 | 0.0 | 0.0 | 0.0 |

## persistent / whole

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 24 / 24 | 24 / 24 | 23 / 24 | 0 / 0 |
| other_selected_rows | 40 / 40 | 27 / 40 | 15 / 30 | 0 / 10 |
| positive | 54 / 54 | 42 / 54 | 38 / 54 | 0 / 0 |
| negative_constraint | 10 / 10 | 9 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 62 / 62 | 50 / 62 | 37 / 52 | 0 / 10 |
| after_session_first_observed | 63 / 63 | 50 / 63 | 37 / 53 | 0 / 10 |

First requests: `[{"query_id": "q-001089", "http_wall_ms": 1236.8975409772247, "startup_ms": 466.2473329808563, "build_ms": 174.87904196605086, "service_setup_ms": 2.413625014014542, "censored": false}]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 64 | 0.0 | 0.0 | 466.2 |
| build_ms | 64 | 0.0 | 0.0 | 174.9 |
| ask_wall_ms | 64 | 666.6 | 4458.2 | 5910.2 |
| service_setup_ms | 64 | 0.0 | 0.0 | 2.4 |
| source_read_ms | 64 | 2.9 | 6.6 | 24.7 |
| json_parse_ms | 64 | 1.4 | 4.2 | 5.3 |
| upload_ms | 64 | 6.9 | 247.4 | 513.5 |
| steps_answer_ms | 64 | 129.6 | 1063.6 | 1285.4 |
| process_ms | 64 | 684.1 | 4459.3 | 5911.1 |
| worker_request_ms | 64 | 667.5 | 4459.2 | 5911.1 |
| cleanup_ms | 64 | 0.0 | 0.0 | 0.0 |

## persistent / photo4

| Group | Observed / selected | Complete HTTP ≤3 s | Correct ≤3 s / positive | Forbidden top-1 / negative constraints |
|---|---:|---:|---:|---:|
| baseline_barcode_hit | 12 / 24 | 12 / 24 | 12 / 24 | 0 / 0 |
| other_selected_rows | 20 / 40 | 14 / 40 | 9 / 30 | 0 / 10 |
| positive | 29 / 54 | 23 / 54 | 21 / 54 | 0 / 0 |
| negative_constraint | 3 / 10 | 3 / 10 | 0 / 0 | 0 / 10 |
| sensitivity | 30 / 62 | 26 / 62 | 21 / 52 | 0 / 10 |
| after_session_first_observed | 31 / 31 | 25 / 31 | 20 / 28 | 0 / 3 |

First requests: `[{"query_id": "q-001089", "http_wall_ms": 1257.2662089951336, "startup_ms": 473.94779208116233, "build_ms": 182.9957909649238, "service_setup_ms": 2.664958010427654, "censored": false}]`.
Sensitivity excludes: `q-000483, q-000484`.
Failed or degraded query IDs: ``.

Component times include available observations. Nested costs MUST NOT be added together.

| Component | Observations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| startup_ms | 32 | 0.0 | 0.0 | 473.9 |
| build_ms | 32 | 0.0 | 0.0 | 183.0 |
| ask_wall_ms | 32 | 682.9 | 4560.3 | 4767.4 |
| service_setup_ms | 32 | 0.0 | 0.0 | 2.7 |
| source_read_ms | 32 | 2.3 | 10.6 | 13.9 |
| json_parse_ms | 32 | 1.3 | 4.2 | 4.5 |
| upload_ms | 32 | 8.3 | 255.3 | 340.3 |
| steps_answer_ms | 32 | 102.9 | 1214.6 | 1287.5 |
| process_ms | 32 | 713.5 | 4561.4 | 4769.5 |
| worker_request_ms | 32 | 683.6 | 4561.4 | 4769.4 |
| cleanup_ms | 32 | 0.0 | 0.0 | 0.0 |

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
