# 25 — The cache of the model calls

Date: 2026-09-25.
Status: the owner chose the design on 2026-09-25T13:47:30+0300. The owner message of
13:51:48 says: choose the recommended way for each open question, then test. Session
CACHE [31e42f] implemented the plan on 2026-09-25. All 445 unit tests pass, and 12 live
cases against gx10 pass (list in `ChangeLog.md`). Not committed. The lab server on 8168
uses the cache after its next restart. The owner messages are in
[owner-messages.md](../owner-messages.md).

Changed by [plan 39](39_use-caches-checkbox.md) on 2026-09-26: `model_cache.READ` (True
by default) turns the reads off in one process. `run_job.py --no-cache` (the checkbox
`Use caches` of the dialog `Run>`, off) sets it. Each call then asks its service, and the
fresh answer is stored.

Changed by [plan 70](70_remove-legacy-testset-stages.md) on 2026-09-28: the numbered
stage scripts were removed. The reusable wine-identity VLM client moved from
`scripts/04_verify.py` to `pipeline/wine_identity_vlm.py`.

## Goal

1. A call to GDINO, SAM3, or a VLM that repeats an earlier successful call reads the
   answer from `data/cache/`. It sends no request.
2. A failed call is not stored. The next call sends the request again.

## Decisions of the owner

1. Storage: one JSON file for each call, in `data/cache/`. No database table.
2. Images: the cache stores the sha256 of each sent image. It does not store the image.
3. Scope: SAM3 (`Sam3Client` of `pipeline/derive.py`), the VLM of
   `scripts/cluster_rules.py`, the VLM of `scripts/04_verify.py` and
   `scripts/bench_vlm_models.py`, and a new GDINO client `pipeline/gdino.py`.
4. The key holds the full endpoint URL, with the host.

## Measurements of 2026-09-25

- One catalogue photo of 906 × 1280 pixels, sent as a PNG of 766,538 bytes. The SAM3
  answer with masks: 13,437 bytes for `SAM3_TEXTS` (3 instances, 1.1 s), and 34,464
  bytes for `alternatives.DETECT_TEXTS` (12 instances, 1.2 s).
- Estimate: about 2,000 originals and 2 noun lists give about 100 MB of records.
- `GET /upstream/sam3/health` answers `"model":"facebook/sam3"`, `"dtype":"fp16"`. The
  SAM3 answer holds no model field.
- `GET /upstream/grounding-dino-base/health` answers
  `"model":"IDEA-Research/grounding-dino-base"`, `"dtype":"float32"`. The answer of
  `POST /detect` holds the field `model`.
- The gateway serves three GDINO models: `grounding-dino-base`, `mm-gdino-base`, and
  `mm-gdino-base-all`. One process serves one checkpoint. The request of `/detect` is
  multipart: `image`, `texts`, `threshold` (default 0.25), `text_threshold` (default
  0.25).

## The key

The key is the sha256 hex of the canonical JSON of the request fields. The canonical
JSON has sorted keys, the separators `,` and `:`, and no ASCII escape.

| Field | Content |
|---|---|
| `v` | `1`, the version of the cache format |
| `endpoint` | the full URL of the route that gets the request |
| `model` | the served name: `sam3`, the GDINO name, or the `model` of the VLM payload |
| `params` | each request field that is not the prompt and not an image, as it is sent |
| `prompt` | SAM3 and GDINO: the field `texts`. VLM: the `messages`, with each image data URL replaced by its sha256 |
| `images` | the sha256 hex of each sent image, in the order of the request |

- The image hash is the hash of the bytes that are sent: after the flatten on white and
  after the resize. So a change of the resize rule gives a new key.
- A VLM data URL `data:<type>;base64,<data>` becomes `data:<type>;base64,sha256:<hex>`
  in `prompt`. The hex is the hash of the decoded bytes.
- Not in the key: the timeout, the retries, the headers, and the API key.

## The record

- Path: `data/cache/<model>/<key[0:2]>/<key>.json`. In `<model>`, each character that is
  not a letter, a digit, `.`, `_`, or `-` becomes `-`.
- Content: `v`, `key`, `request` (the request fields), `created` (local time, ISO 8601),
  `ms` (the time of the call, with its retries), and `answer` (the JSON body as the service
  sent it).
- A record is a hit only when its `request` equals the request fields.
- A file that cannot be read or parsed is a miss. The next success replaces it.

## The rule of a success

1. A success is HTTP 200 with a JSON body. Only a success is stored.
2. A SAM3 answer or a GDINO answer with no instance is a success.
3. A VLM answer is a success when its body holds at least one entry in `choices`. A
   gateway can send HTTP 200 with an error body. The `finish_reason` does not change the
   rule. The parse of the text is the work of the caller. The calls use temperature 0.
4. HTTP 429, HTTP 5xx, another 4xx, a timeout, and a network error are not stored.
5. A VLM request with an image URL that is not a data URL gets no lookup and is not
   stored. The content behind a URL can change.

## The write

1. The record goes to a temporary file in the target directory, then `os.replace` puts
   it in place. A reader sees the old file, no file, or the whole new file.
   The record gets the mode 0644, the mode of the other data files.
2. Two processes that write the same key write the same content. The last write stays.
   No lock is necessary.
3. A write that fails prints one warning to stderr for each process. The call returns
   its answer.

## The code

1. New `pipeline/model_cache.py`: `ROOT`, `request_fields`, `vlm_fields`, `lookup`,
   and `store`. It imports only the standard library, so `scripts/` can import it too.
2. `pipeline/derive.py`: `_post(data, texts, return_masks)` stays the entry point. It
   does the lookup and the store. The present retry loop moves unchanged into a new
   method `_send`. A constant `SAM3_MODEL = "sam3"`.
3. New `pipeline/gdino.py`: `GdinoClient(model, gateway)` and `detect(image, texts,
   threshold, text_threshold)`. The sent copy and the retries follow the rule of
   `Sam3Client`. A command line prints the answer and states `hit` or `miss`.
4. `scripts/cluster_rules.py` (`Vlm.ask`), `pipeline/wine_identity_vlm.py`
   (`Backend.ask`), and `scripts/bench_vlm_models.py` (`call`): a lookup before the
   request and a store after a success. `Vlm` counts the hits in `hits`.
   `bench_vlm_models.py` marks a cached line with `"cached": true`.
5. Unit tests set `model_cache.ROOT` to a temporary directory. `tests/test_derive.py`
   does this in `setUpModule`.

## Known limits

1. The served name does not name the checkpoint. A new checkpoint behind the same served
   name gives old answers. After such a change, delete `data/cache/<model>/`. Reason: a
   check of `/health` before each lookup makes the gateway start the model, also for a
   run that the cache answers completely.
2. `derive._Once` stops the SAM3 calls of a run after the first failure, also the calls
   that the cache could answer. The next run reads them.
3. There is no switch to refresh the cache. To send a request again, delete its record
   or the directory of its model.
4. A cached VLM answer keeps the latency of the first call.
5. There is no size limit and no eviction.

## Tests

1. Unit tests: `tests/test_model_cache.py`, `tests/test_gdino.py`, and one test at the
   end of `Sam3ClientTest` in `tests/test_derive.py`.
2. Live tests against gx10: SAM3 miss then hit, GDINO miss then hit, VLM miss then hit
   for `cluster_rules.Vlm` and `04_verify.Backend`, a failure that is not stored, a
   parallel write of one key. `bench_vlm_models.call` is tested with a stub, because it
   calls a cloud service with a key.
3. After the full test run, `data/cache/` holds no record of an `.invalid` endpoint.
