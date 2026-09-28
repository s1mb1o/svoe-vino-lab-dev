# Research log

## 2026-09-28

This entry records the threshold check for the matcher pipeline `siglip2-p512-as-is`.
The source is the lab runs in `svoe-vino-lab/workbench/runs/`. The runs used no bot code.
The run `2026-09-28T011622Z-lab-siglip2-p512-as-is-my` has 1,647 positive and 579
negative photos. The run `2026-09-27T011444Z-lab-rerank-siglip2-512-crop-my` is the old
bot pipeline on the same set.

| Pipeline | Top-1 accuracy | Answered at 0.70 / 0.015 | Precision of the answers |
|---|---|---|---|
| `siglip2-p512-as-is` | 0.743 | 0.591 | 0.909 |
| `rerank-siglip2-512-crop` | 0.832 | 0.723 | 0.922 |

The median Top-1 cosine of `siglip2-p512-as-is` is 0.791 for a correct and 0.762 for a
wrong answer. The median margin is 0.0385 for a correct and 0.0069 for a wrong answer.
The score scale is similar to the old pipeline, so the thresholds 0.70 and 0.015 keep
the precision. The new pipeline answers fewer photos with confidence.
On the set `official-real-photos` (60 positive photos), the new pipeline gives a Top-1
accuracy of 0.817. At 0.70 / 0.015 it answers 0.700 of the photos with a precision of
0.976.

The prod matcher answered `02eef911.webp` on 2026-09-28 with four candidates. Rank 1 had
the score 0.8199. The answer of `/v1/eval/predict` for the same image was the rank 1 slug.

This entry records a resource and network check of `avalon` as a bot host.
The decision is in `docs/decisions/016-keep-bot-on-gx10.md`.
`avalon` had approximately 1.45 GiB of available RAM and 34 GB of free disk.
Uptime Kuma used 119 MiB. Caddy used 14 MiB.
On gx10, the bot service had a peak memory of 203.2 MB and a swap use of 157.3 MB.
The administration service had a peak memory of 36.2 MB.
The bot data used 14 MB. The virtual environment used 95 MB. The catalogue used 3.4 MB.
The direct Selectel route to Telegram times out.
The `cloudzy-ams` tunnel permits only `api.telegram.org:443`.
This destination covers long polling and Telegram file downloads.
`app.py` creates `Bot` without a session, so the code has no proxy option.
The gx10 reverse tunnel to `avalon` forwards only `28000`.
The prod matcher on `28000` used the mock pipeline `official-eval-mock`.

This entry lists the recognition dependencies of the bot.
It prepares a proposal to move recognition to `svoe-vino-lab/matcher/`.
The bot keeps Telegram handling, moderation, and the administration interface.

The bot calls three recognition services after safe moderation.
The first service is SAM3 `/segment_multi` in `quality.py`.
The second service is the matcher `POST /v1/eval/predict?limit=4&pipeline=<name>` in `matcher.py`.
The third dependency is the local catalogue in `catalog.py`.
The catalogue reads `CATALOG_FILE` and `WINE_CODE_MAP_FILE`.

The production matcher on port 8158 is `svoe-vino-matcher/svm/server.py`.
Its response shape depends on `limit`.
A request without `limit` or with `limit=1` returns `{"slug"}`.
A request with `limit>1` returns `{"candidates": [{slug, score, rank}], "pipeline", "latency_ms"}`.
`svoe-vino-lab/matcher/` has only a `mock` backend.
Its `Prediction` schema forbids extra fields and contains only `slug`.

The bot reads these recognition values:

- four candidates with `rank`, `slug`, and `score`;
- the Top-1 score and the Top-1 margin for the abstain decision;
- `name`, `page_url`, `category`, `color`, `sugar`, `grapes`, and `image_url` for the result card;
- `producer` and `qr_urls` for the HTTP API payload;
- quality `acceptable`, `issues`, blur variance, glare ratio, bottle area ratio, and label area ratio;
- SAM3 masks, boxes, prompts, and scores for the pipeline artifacts.

The negative feedback callback reads candidate wine names after the request ends.
The callback uses `catalog.get(slug)` for ranks 2 through 4.
A move of the catalogue out of the bot needs a stored wine snapshot or a wine lookup call.

`artifact_backfill.py` calls SAM3 again to rebuild quality artifacts.
A move of SAM3 out of the bot changes this command too.

## 2026-09-27

The internal HTTP API can share the bot process and the existing `WorkQueue` instance.
This design prevents concurrent Telegram and HTTP GPU work when the queue has one worker.
FastAPI `UploadFile` can use a temporary file for a large multipart part.
The safety policy forbids this write before moderation.
The selected parser reads a bounded multipart body through `Request.stream()` and parses it in memory.

The production cached control request completed in 9.811 seconds.
Moderation used 0.716 seconds.
SAM3 quality inspection used 5.362 seconds.
Matcher recognition used 2.050 seconds.
The correct `Фантом 30/70` candidate was rank 1.
The bot abstained because the score margin was `0.004748`, below the configured `0.015` threshold.

One uncached control request timed out in matcher recognition after 180.008 seconds.
The shared `qwen3.5-9b-nvfp4` endpoint was busy with another workload.
Moderation and SAM3 completed before the matcher timeout.
The API returned a structured HTTP 502 response with all completed step timings.
This result shows that matcher contention is visible separately from API and preprocessing latency.

## 2026-09-26

CSS blur does not protect a source image.
The browser receives the source and can remove the CSS rule.
A server-side derivative preserves the quarantine boundary.
The selected transformation reduces the longest side to 24 pixels.
It then enlarges the image to a maximum longest side of 768 pixels.
It applies a Gaussian blur with radius 18 after enlargement.
This sequence removes fine spatial detail before the blur operation.
The artifact route uses both the current moderation result and the stored exposure class.

The shared SAM3 `/segment_multi` endpoint accepts `return_masks=true`.
Each returned instance can contain `mask_png_b64`.
The value is a full-size one-bit PNG encoded as base64.
Mask serialization does not run a second segmentation inference.
The client must still validate the base64 value, decoded size, image format, and dimensions.
Persisted artifacts preserve the output from the original processing attempt.
On-demand reconstruction could use GPU time and could produce a different result after a model change.
The administration route checks the current `moderation_safe` value before it serves an artifact.
This check removes access immediately when a retry starts or when the request becomes unsafe.

The request detail page reused the overview statistic grid.
Five detail cards fit in one row, but each definition-list value received too little width.
Long and ordinary values then wrapped one character per line.
A separate detail grid with a 480-pixel minimum card width produces two desktop columns.
The same grid uses the full available width on a narrow viewport.

TCP port `8172` was absent from the Mac and `gx10` port registries.
A live `ss` check on `gx10` found no listener on TCP port `8172`.
SQLite WAL mode supports the bot process and the administration process on the same host.
A persistent `retry_requested` status avoids an in-memory cross-process queue dependency.
The bot can claim this status with a compare-and-set update and use its existing FIFO queue.
The administration interface does not need file routes for its first version.
This design keeps quarantine images outside the HTTP surface.

One SAM3 response used box coordinates from `-2` to `724` for a 720-pixel-wide image.
SAM3 returned HTTP 200, but the strict client rejected the complete response.
Small coordinate overflow is a model rounding artifact.
The client can clamp a small overflow to the image boundary.

One quarantined production request took 86.816 seconds.
The `moderation` step took 86.076 seconds, or approximately 99.1% of the request time.
The ShieldGemma process started when the request arrived.
The delay was a cold model start through `llama-swap`.
The previous ShieldGemma instance used the old 1800-second TTL.
The `llama-swap` configuration changed to an 86400-second TTL before this request.
The running old instance did not adopt the new TTL and unloaded before the request.
The new instance reports the 86400-second TTL and is ready.

The matcher returns a ranked response when the request includes `limit=4`.
Each candidate contains `slug`, `score`, and `rank`.
The measured `barcode-siglip2-448` median score margin is approximately `0.040`
for correct Top-1 results and `0.007` for wrong Top-1 results on the inspected run.
The initial minimum margin is `0.015`.
This value needs calibration from production feedback.

The shared SAM3 service supports `POST /segment_multi`.
The request accepts a multipart image and comma-separated text prompts.
The quality check uses `wine bottle`, `label`, and `wine bottle label`.
The bot reads the SAM3 base URL only from `SAM3_ENDPOINT`.

The `gx10` host runs `llama-swap` on `127.0.0.1:18081`.
The model list contains `qwen3.5-9b` with vision support.
The model accepts OpenAI-compatible chat completion requests.

The `shieldgemma-2-4b-it` classifier is available at
`/upstream/shieldgemma-2-4b-it/classify` on the same service.
The classifier accepts a multipart `image` field.
A live safe-image probe returned model `shieldgemma-2-4b-it` and threshold `0.5`.
The response contains `dangerous`, `sexual`, and `violence` scores.
The response also contains a thresholded `flagged` list.

The `gx10` host runs `svoe-vino-matcher` on `127.0.0.1:8158`.
The matcher health response names `barcode-siglip2-448` as the default pipeline.
The matcher catalogue is at
`/mnt/projects/svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl`.
The catalogue contains `slug`, `name`, and `page_url`.
The catalogue also contains `image_url`, `category`, `color`, and `grapes`.
The catalogue image host is `api.vino-svoe.ru`.
The catalogue images use WebP in the inspected records.
The catalogue does not contain a separate sugar field.
Explicit sugar terms occur in many slugs and wine names.
The bot can infer a sugar class from an explicit term only.
The bot must show `нет данных` when the term is absent.
A live result-image probe downloaded one official WebP image.
The result-image normalizer produced a 44,972-byte JPEG with dimensions 260 by 1000.
The inspected catalogue result images use transparent WebP files.
The inspected dimensions include 1200 by 1200, 2000 by 3000, and 1041 by 3539 pixels.
Telegram crops a very tall result image in the chat preview.
An alpha threshold of 16 isolates the bottle in the inspected transparent images.
A fixed 4:5 canvas prevents Telegram preview cropping.

The Telegram Bot API supports long polling through `getUpdates`.
Telegram gives all photos in one album the same `media_group_id`.
The Bot API also supports bot commands, a description, and a short description.
The profile image still requires BotFather interaction.
