# Prepared profile comparison

Date: 2026-09-27. This inspection reads source, configuration, and baseline metadata.
It opens no image. It sends no request. It starts no inference or measurement.

## Scope of the comparison

The prepared comparison is a joint ablation of query package cropping and conditional
label-based VLM reranking. It is not an isolated rerank ablation. A difference in
accuracy or latency cannot identify the separate effect of either removed stage.
Compare matching `persistent-whole` and `persistent-photo4` sessions from both profiles.
The existing `barcode-siglip2-512-crop` profile would retain query preprocessing for a
separate isolated rerank comparison. After this finding, the parent prepared one
measured `persistent-photo4` control on that profile, after the crop and as-is diagnostics.
This report does not launch that control.

Parsed configuration confirms that `barcode-siglip2-512-crop` differs from the reference
only in its name, absent `rerank`, and default query-worker count of one instead of four.
Its embedding, package preprocessing, full view, and barcode options are identical.
The sequential HTTP harness does not use the query-worker default. The existing crop
profile is therefore a valid isolated rerank control for matching persistent sessions.

The saved trace already supports an offline fallback-quality comparison.
`search` with `view: full` keeps the base candidate order in `out.top`.
Both profiles have one query tower, so that order equals the pre-rerank embedding order.
The final reranked candidates also preserve `explain.base_rank` and `explain.base_score`.
For shared GTINs, reconstruction MUST preserve the final unranked-code append behavior
of `CodeFirst.limited`. Unique code answers are unchanged. A failed row with no saved
base ranking MUST remain unavailable in the offline comparison. Do not impute success.

The inspected `http-pilot/persistent-whole.jsonl` contains 64 saved rows and 18 rerank
rows. The rerank rows retain their base order. Offline quality needs no new inference.
Subtracting the `cluster_rules` duration gives only a latency estimate. It does not
measure HTTP initialization, response reconstruction, or response-size changes after
removing rerank. A claim about measured HTTP latency needs the isolated control.
The completed `persistent-photo4` quality reconstruction is saved in
[the separate offline report](http-persistent-photo4-offline-rerank.md).

| Property | `barcode-rerank-siglip2-512-crop` | `barcode-siglip2-512-as-is` |
|---|---|---|
| Embedding index | `gx10-siglip2-so400m-patch16-512` | Same |
| Embedding model | `siglip2-so400m-patch16-512` | Same |
| Query retrieval view | `full` only | `full` only |
| Query preprocessing | Package rectangle, white background, resize | Whole photo, white background, resize |
| Resize | Long side at most 1024; preserve aspect ratio; no upscale | Same |
| Query background mask | No `remove_background` step | No `remove_background` step |
| Conditional rerank | Cluster rule, label detection, Qwen request | Absent |
| Configured query workers | 4 | Default 1 |
| HTTP diagnostic concurrency | One sequential image per worker | Same |

Both profiles search the same current catalogue `full` vectors. The index also holds
label vectors, but neither profile submits a label query vector. The catalogue full
view uses package segmentation, background removal, white background, and resize.
Thus `as-is` changes the query pixels while preserving the catalogue preparation.
The index passes the existing file-presence readiness check at inspection time.
That check does not validate every vector or guarantee service capacity.

The crop profile gets its package rectangle through `derive.derive_image()`.
An alpha channel can supply the rectangle without a SAM3 call. Otherwise the client
requests package segmentation. A missing mask uses the white-background rectangle
fallback. The query uses the rectangle from this operation, not its processed mask.

Reranking runs only when the cluster rule triggers within the first five candidates.
It requests label detection. It sends the selected label image, or the whole photo
when no label is found, to `qwen3.5-9b-nvfp4`. The options are `thinking: false`,
`side: 1536`, `max_tokens: 256`, and `timeout_s: 180`. The rules come from
`gx10-siglip2-so400m-patch16-naflex-p256`; this does not change the embedding model.

Sources: [profile configuration](../../../config.yaml), `cuts_of`, `view_input`,
`Catalogue.rank`, and `build_pipeline_backend` in
[embedding_run.py](../../../pipeline/embedding_run.py), `apply_steps` in
[embeddings.py](../../../pipeline/embeddings.py), and `picture` and `rerank` in
[cluster_rerank.py](../../../pipeline/cluster_rerank.py).

## Barcode and cache behavior

The profiles have identical barcode options: EAN13, GTIN-only Code128, QR enabled,
tiles enabled, long side 1600, and upscale enabled. A unique lookup hit returns before
embedding, package segmentation, and rerank. A shared GTIN restricts the downstream
candidate set. A miss uses the ordinary downstream pipeline.

The HTTP harness overrides the decoder by variant. `whole` runs two whole-photo calls
with `LocalAverage` and `FixedThreshold`. `photo4` starts with the same whole-photo
calls. It then scans the 3-by-3 and 5-by-5 tiles with at most four concurrent tile tasks.
It consumes results in production order. It includes unfinished speculative work in
the timing and native-call count. These are four decoder tasks within one photo.
The profile's configured query-worker count does not create four HTTP requests.

Every HTTP request gets a new upload directory and response-cache directory.
The child sets `model_cache.READ = False`, including in persistent mode. Barcode,
SAM3, embedding, and VLM responses are therefore computed again when the path needs
them. The backend and loaded catalogue remain in the persistent child. Server-side
model residency is uncontrolled and MUST be reported separately from cache bypass.
The HTTP step view can read responses written by this same request. It uses the
cache-only client for reconstruction and does not issue a second inference request.

Sources: [barcode.py](../../../pipeline/barcode.py), `scan_stages` in
[benchmark_barcode_variants.py](../../../scripts/benchmark_barcode_variants.py),
`build_experiment` and `worker_loop` in
[benchmark_recognition_latency.py](../../../scripts/benchmark_recognition_latency.py),
and `RouteAdapter` and `isolated_server` in
[benchmark_recognition_http.py](../../../scripts/benchmark_recognition_http.py).

## Actual destinations

- Both profiles: `POST http://192.168.86.14:18081/v1/embeddings`.
- Crop and rerank segmentation: `POST http://192.168.86.14:18081/upstream/sam3/segment_multi`.
- Rerank: `POST http://192.168.86.14:18081/v1/chat/completions`.
- Barcode decoding: local ZXing. The configured external rule-generation endpoint is
  not part of either recognition path.

The configured SAM3 base URL and `SAM3_ENDPOINT` agree at inspection time.
The prepared `as-is` variants `whole` and `photo4` need no query SAM3 or VLM call.
Backend construction still creates an unused SAM3 client object.

## Prepared commands and frozen selections

Both future commands in [demo-launches.json](demo-launches.json) match the current
HTTP CLI options and supported variant names. Their baseline run, archived log, and
stage-1 paths exist. Their output directories do not exist at inspection time.
The commands use the system Python for the HTTP parent. The configured embedding
interpreter runs the child. Keep the project root as the command working directory.

| Command | Profile | Variants | Mode | Rows per variant | Output directory |
|---|---|---|---|---:|---|
| `fresh_crop_diagnostic` | Crop/rerank default | `fresh-bottle,fresh-label,fresh-barcode` | `persistent` | 24 | `http-crop-hits` |
| `conditional_existing_profile_comparison` | `barcode-siglip2-512-as-is` | `whole,photo4` | `persistent` | 64 | `http-as-is-pilot` |

Selection reconstruction from baseline JSON reproduces both saved fingerprints:

- 24 rows, 24 unique images, 24 positive labels, and 24 unique baseline barcode hits:
  `0686b5bd8b64fa2be1baf2fb6932e96b80ac554b8f9d14ea99f9591f3f6d53a5`.
- 64 rows, 61 unique images, 54 positive labels, 10 negative labels, and 24 baseline
  barcode hits: `3b1fd11b30778da43042b04158b1cf820f92e53c7ffe5f360c241ce38dac9763`.

The harness recomputes these selections; `selection_file` is a planning field, not a
CLI input. Compare the new manifest fingerprint with the saved fingerprint.
The 24-row sample is enriched for known hits. It cannot estimate corpus detection
recall or the corpus three-second success rate. The 64-row sample is also deliberate.
Keep the raw 54-positive denominator and the 52-positive annotation-conflict sensitivity.

Each `fresh-*` variant requests fresh SAM3 geometry before scanning. It does not try
the whole photo first. Bottle uses the largest valid detection rectangle. Label uses
the production label-selection rule. Barcode scans all valid rectangles in descending
area order, then score, then coordinates, with a 10% margin per side. There is no
rectangle cap. Each selected rectangle gets the two whole-region ZXing calls.
The decoder uses original-image crop pixels. It does not use a masked label image.
The first unique lookup hit stops the region sequence.

On a crop miss, the configured crop/rerank pipeline still runs. Its later segmentation
is charged again. The fresh geometry response is not reused by the downstream client.
Thus the diagnostic measures the complete crop-barcode strategy plus any fallback.
The `answer.crop_scan` telemetry separates SAM3, geometry, crop decoding, and call counts.

Outputs remain `manifest.json`, `<mode>-<variant>.jsonl`, corresponding summaries,
full response JSON files, upload/cache directories, failure records when needed, and
`complete.json` after all requested sessions pass. Failed rows remain in the denominator
on resume. The first persistent request includes child initialization. HTTP wall time
ends after the complete response body. JSON parsing is reported separately. Browser
rendering and remote client network time are excluded. No hard three-second timeout
is implemented.

The top-level `prepared_not_started` label in `demo-launches.json` is stale for the
already active pilot. Do not use that label as a launch gate. The parent must verify
pilot completion, fresh capacity, workload registration, and absence of a competing
measurement before the two future commands. This inspection grants no launch approval.

Configuration SHA-256:
`14642fdc568cc2d309ab52d95b3f428dae09d16bf68fb8250f1f358789916d77`.
Inspected launch-plan SHA-256:
`2ba1b1ba1f7af18240fa4152a65e92cae9feca6136060734be03cd03f45427af`.
