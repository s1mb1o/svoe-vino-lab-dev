# Research Log

## 2026-09-29 — Facts for the design of the model proxy

### The gx10 cache on port 18082

- Source: `/Users/ashmelev/Admin/gx10/docs/inference/vlm-response-cache.md` and
  `/Users/ashmelev/Admin/gx10/scripts/inference/vlm_response_cache/server.py` (786 lines,
  19 tests).
- It is a FastAPI proxy in front of llama-swap `127.0.0.1:18081`. It forwards to one
  upstream only.
- It caches `POST /v1/embeddings` for nine image models and three WeMM models, the four SAM3
  routes, `POST /upstream/<gdino>/detect` for three Grounding DINO models, and the chat of
  `qwen3.5-*`.
- The key: the SHA-256 of the namespace, the method, the path, the sorted query, and the
  semantic body. The multipart form ignores the boundary and the file name.
- `Cache-Control: no-cache` or `X-GX10-Cache: bypass` skips it. A skipped request stores
  nothing.
- `GET /_cache/stats` at about 08:30: namespace `gx10-vlm-cache-v1`, 55,066 entries,
  627,601,282 bytes; 20,593 SAM3 entries (446 MB), 392 SigLIP2 NaFlex entries (151 MB),
  34,076 `qwen3.5-9b-nvfp4` entries, 3 Grounding DINO entries.
- The store computes `SUM(body_size)` with a full scan at each write, and has no index on
  the creation time. The proxy keeps the total in memory and adds the index.

### The bootstrap on the RTX 4090 hosts

- Source: `../bootstrap/` (`gateway.py`, `launcher.py`, `services/`), `../bootstrap/README.md`,
  and `<workspace>/deploy/bootstrap/selectel-rtx4090.md`.
- The gateway serves `/upstream/<model>/<path>` and routes `POST /v1/embeddings` by the JSON
  field `model`. The paths and the bodies are the paths and the bodies of gx10.
- The SAM3 service has the four routes `segment`, `segment_multi`, `segment_verify`, and
  `segment_point`. The SigLIP2 service is the gx10 image-embedding service: batch limit 64,
  `max_num_patches` 1 to 4096, default budget 256.
- The bootstrap has no Grounding DINO service.
- The launcher runs one accelerator model by default. `--allow-multiple-accelerators` runs
  more after a memory check. It binds `127.0.0.1:18090`. It stops on SIGHUP.
- Precision on CUDA: SAM3 fp16 (the launcher passes `--batch-size 1`), SigLIP2 bf16. On
  gx10: SAM3 fp16 with batch 4 and one worker, SigLIP2 bf16, Grounding DINO fp32.
- `GET /health` of the gateway returns `active_models` and `failures`, with HTTP 503 when a
  service is not ready.

### Throughput and limits

- Source: `../bootstrap/docs/benchmarks/2026-09-28-gx10-vs-rtx4090.md`.
- SAM3 at client concurrency 1, 2, 4, 8: gx10 2.75, 3.87, 4.07, 4.13 requests per second;
  RTX 4090 7.91, 8.38, 8.55, 8.84. SigLIP2 NaFlex p256 at concurrency 8: gx10 41.31, RTX
  56.19; fixed-512: gx10 35.79, RTX 51.01. The benchmark used a generated image and no masks.
- llama-swap on gx10 admits at most 10 requests in flight for each model. The eleventh gets
  HTTP 429 at once (`/Users/ashmelev/Admin/gx10/docs/inference/image-embeddings.md`).
- The SAM3 and Grounding DINO clients of the workbench retry after HTTP 429 and 5xx and read
  `Retry-After`. The matcher SigLIP2 client does not retry and has a timeout of 60 s.

### Hosts on 2026-09-29

- `kit` (178.130.51.88, RTX 4090 24 GiB) and `zelda` (111.88.124.23, RTX 4090, spot) did not
  answer on TCP port 22 at about 08:30. `princess` and `github.com:443` answered, so the Mac
  had internet access.
- gx10 `/running` at 10:24: `qr-scanner`, `qwen3.5-9b`, `qwen3.5-9b-nvfp4`, `sam3`,
  `shieldgemma-2-4b-it`, `siglip2-so400m-patch16-naflex`. Grounding DINO and SigLIP2
  fixed-512 did not run.

### Clients of the three variables

- `~/.zshrc` exports `SIGLIP2_ENDPOINT`, `GROUNDING_DINO_ENDPOINT`, and `SAM3_ENDPOINT` with
  the gx10 cache `:18082`.
- Readers: `matcher/`, `telegram-bot/`, `workbench/scripts/runner_smoke.py`,
  `bootstrap/scripts/check_compatibility.py`, `drink-atlas-matcher`, and
  `drink-atlas-enrichment`.
- The workbench lab reads its endpoints from `workbench/config.yaml` (gx10 `:18081`), not from
  the variables. The key of `workbench/pipeline/model_cache.py` holds the full endpoint URL.
- `run_internal_profile_queue.py`, `benchmark_bulk_cache.py`, and
  `prepare_rerun_label_inputs.py` refuse a `SAM3_ENDPOINT` that is not the gx10 URL.

### Libraries

- Starlette 1.7.0 (with FastAPI 0.141.1) limits a multipart field without a file name to
  1 MiB (`max_part_size`). A file part goes to a `SpooledTemporaryFile` and has no limit.
- `httpx.Response(json=...)` reads its body in the constructor. After that, `aiter_raw()`
  raises `StreamConsumed`, and `aiter_bytes()` gives the stored body.

### Live measurements of the proxy

- A tunnel host is down at the first probe: the probe came 22 ms after the `ssh` start,
  before the forward was open. The probe 2 s later found the host up.
- A tunnel whose remote port is closed accepts the local connection. `ssh` then reports
  `channel 1: open failed: connect failed: Connection refused` and resets the connection.
  httpx raises `ReadError` (`[Errno 54] Connection reset by peer`), not `ConnectError`. So
  the proxy does not mark the host down after such a request. It sends the request to the
  next host at once, and the next probe marks the host down.
- Through the scratch proxy, a new SAM3 `segment_multi` request took 605 ms (gx10 cache
  `MISS`); the repeat was a proxy hit in 2 ms. SigLIP2 NaFlex p512: 249 ms and 2 ms.
- Upload estimate (not measured): at 8.84 SAM3 requests per second and 2 to 3 MB for each
  PNG, one RTX 4090 needs about 140 to 210 Mbit/s of upload from the Mac.
