# Final remote source and control audit

Recorded at 2026-09-27T06:58:16.997718+03:00.

The source and frozen-control audit passes. All 49 remote attempts use the same 57-file production source map. The current 57 top-level `pipeline/*.py` files match that map. All archived attempt records equal their queue records. All 49 canonical identity hashes are valid.

The queue retains 48 `done` profiles and one `invalid_completion` profile. `siglip2-p14-384-as-is` retains eight errors. Source equality does not promote that failed run. The [failure evidence](g9-failed-run-evidence.md) remains part of the result.

| Control | Evidence |
|---|---|
| Query rows | 2228 in each frozen identity |
| Image digests | 1851 in each frozen identity |
| Positive / negative rows | 1644 / 584 in each frozen identity |
| Query IDs | 2228 unique IDs; complete ordered identities equal across all 49 attempts |
| Workers | 4 in all requests and identities; 4 in all 48 embedded run records |
| Cache reads | Enabled in all requests and all 48 embedded run records |
| Barcode request | `use_barcode=true` in all 49 requests |
| Configured barcode step | 25 profiles have the step; 24 profiles do not have the step |
| Archived attempts | 49/49 equal the queue attempt objects |
| Current source files | 57/57 match all frozen source maps |

The barcode request permits a configured barcode step. It does not add that step. All 25 configured barcode runs record `use_barcode=true` and `backend.barcode`. The 23 validated plain runs omit both fields. The failed plain attempt has request and identity evidence. Its embedded run metadata is absent. See `pipeline/run_jobs.py:304`, `pipeline/run_job.py:153`, and `pipeline/embedding_run.py:545`.

All recorded model endpoints use the internal GX10 gateway. The embedding and rerank base URL is `http://192.168.86.14:18081/v1`. The SAM3 URL is `http://192.168.86.14:18081/upstream/sam3`. This audit sent no request.

## Common fingerprints

| Field | SHA-256 |
|---|---|
| `source_map_sha256` | `14896220bb22aad868dcadde37b3e6105aed5d69b19043ff0b358a8d071d9562` |
| `config_sha256` | `14642fdc568cc2d309ab52d95b3f428dae09d16bf68fb8250f1f358789916d77` |
| `queries_identity_sha256` | `59a36beb0114325aa7a7fca7177608beac01d5d7d1b432f64abb3daf4fc60912` |
| `baseline_queries_sha256` | `99673ed979606f881fcfa4bf26f0156f9f55d58e061dd3e624b74f2a3bae91dc` |

The structured hash uses UTF-8 JSON with sorted object keys, compact separators, and unescaped Unicode. List order is preserved. The query identity hash was recomputed from each frozen list. The baseline file hash is a recorded value. The 48 successful attempts also record that same `queries.jsonl` artifact hash. This audit did not reread run artifact bytes or live `config.yaml`.

## Deliberate data differences

The seven G1 profiles use catalogue fingerprint `6eaaa1b7e9204cb8e37af7b7aa2b0e6028d7937b01f4aa803ae5f73c12c3e16c`. The 42 later profiles use `aa5574dd516633f84062bb14fc25396712bafed674fac65cdc1723525e78b104`. The later snapshot follows the planned G2 derivative preparation. These are stored catalogue fingerprints. They are not hashes of the fingerprint strings.

The 49 attempts use 11 configured embedding indexes. Each frozen index identity and its profile membership are listed in the JSON report. The NaFlex-p1024 index has 4181 current vectors and 2096 full/2092 label wines in its four saved run records. The other 44 available saved run records have 4054 current vectors and 2051 full/2047 label wines. The missing-entry counts are zero and 127, respectively. Both groups have two failed index entries. Prepared-image name counts are not vector counts. These coverage differences limit comparisons across indexes.

## Scope and limits

The audit read the queue, 49 archived attempts, and 57 current production source files. It read no live database, source image, or current index/vector file. It ran no tests, inference, launch, or network request. It did not change the queue or an attempt. The JSON report records archive file hashes, canonical attempt hashes, source hashes, and all per-attempt checks.

The common configuration hash proves agreement between frozen attempts and the queue-time hash. It does not verify live `config.yaml`. Source equality covers local pipeline Python files. It does not verify dependencies, remote services, model weights, or runtime state.

Cache reads were enabled. Cache contents and model residency can differ between runs. Bulk timings do not establish the three-second fresh-image HTTP target. The failed G9 attempt remains a failure.

Audit issues: 0. The 49 remote queue records stayed equal during this audit.

Independent metadata review: `review_bulk_harness` matched all 49 archive/queue records, identity hashes, source/config/query fingerprints, counts, and worker/cache/barcode controls. The author separately hashed the 57 current source files.
