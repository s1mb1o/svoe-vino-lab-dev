# The agent API of the review tool

`scripts/review_server.py` answers an HTTP API under `/api/v1/`. An agent uses it to
read the wines, to look at the pictures, and to propose a photo for a wine.

The server MUST be running:

```bash
python3 scripts/review_server.py --no-browser      # http://127.0.0.1:8154
```

`docs/openapi.yaml` holds the same contract in machine-readable form. It covers every
route of the server, not only `/api/v1/`. The running server serves it:

| Route | Answer |
|---|---|
| `GET /openapi.yaml` | the document, as it is written |
| `GET /openapi.json` | the same document, converted to JSON |
| `GET /docs` | the document in a browser, with Swagger UI |

The document is written by hand. It is not generated from the code. A change of a
route MUST change `docs/openapi.yaml` in the same commit.

Every write goes through this one server, so a write of the agent and a click of the
reviewer cannot overwrite one another.

## The rule of the proposals

An agent MUST NOT write a label. A label is the decision of the reviewer.
An agent writes a **proposal**: the photo lands in `my/<slug>/` as `NN_agent.<ext>`,
and its entry holds `proposed`, `by`, `confidence`, and `source_url`.

A proposal is not counted in `labelled`. The card shows a dashed border and a tag with
the confidence. The reviewer opens the filter `holds a photo proposed by an agent` and
answers with the keys `1` to `4`. Only then the photo has a label.

## Read

### `GET /api/v1/stats`

```json
{ "wines": 844, "photos": 2023,
  "excluded_wines": 3, "excluded_photos": 7,
  "counts": { "positive": 534, "negative": 203, "unusable": 61, "variant": 0,
              "labelled": 798, "proposed": 0, "commented": 15, "wine_notes": 2 },
  "variant_groups": 28 }
```

`excluded_wines` and `excluded_photos` count the wines and the photos that are out of
the benchmark. Read `docs/excluded-slugs.md`.

### `GET /api/v1/wines`

| Parameter | Meaning |
|---|---|
| `filter` | `all`, `unlabelled`, `needs_positive`, `has_proposal`, `fully_labelled`, `in_variant_group`, `no_candidate_photos`, `image_unresolved`, `image_assumed`, `image_confirmed`, `image_manual`, `image_shared` |
| `q` | a part of the slug, the name, or the producer |
| `limit` | 1 to 500, default 50 |
| `offset` | default 0 |
| `include_excluded` | `1` also lists the excluded wines. The default value leaves them out. |

`needs_positive` is the work list of an agent: the wines with no confirmed photo.

An excluded wine is out of the benchmark, so the list leaves it out. An agent MUST NOT
hunt photos for such a wine. Read `docs/excluded-slugs.md`.

```json
{ "total": 571, "offset": 0, "limit": 50, "wines": [ { "slug": "...", "name": "...",
  "producer": "...", "photos_total": 1, "labels": {...}, "unlabelled": 0,
  "proposed": 0, "bottle_path": "/Volumes/...", "bottle_url": "/img/bottle?slug=...",
  "variant_group": null, "wine_note": "",
  "excluded": false, "exclude_reason": "" } ] }
```

`excluded` states that the photos of this wine are NOT used for benchmarking.
`exclude_reason` states the error of the card, most often a wrong bottle photo.

### `GET /api/v1/wine/<slug>`

The same record with `photos` added. `description` is already in the record of
`GET /api/v1/wines`. Each photo holds:

```json
{ "file": "01_conf095.jpg",
  "path": "/Volumes/.../my/<slug>/01_conf095.jpg",
  "url": "/img/photo?slug=<slug>&file=01_conf095.jpg",
  "conf": 95, "label": "positive", "proposed": null, "by": null,
  "confidence": null, "source_url": null, "comment": null,
  "reassign_to": null, "moved_from": null,
  "copy_to": null, "copied_from": null }
```

`path` is an absolute path on this machine. An agent reads the picture from the path
with its own file tool; the bytes do not travel through the API.

`variant_group` names the wines that hold the same wine in another bottle, with the
path of each bottle photo. Read it before a decision: the photos of two variants
differ only in a small detail.

### `GET /api/v1/wine/<slug>/photos?label=positive`

Only the photos with that label. Leave `label` out for every photo.

### `GET /img/bottle?slug=<slug>` and `GET /img/photo?slug=<slug>&file=<file>`

The picture itself, for a browser. An agent SHOULD use `path` instead.

## Write

### `POST /api/v1/propose`

```json
{ "slug": "agora-risling",
  "url": "https://otzovik.com/.../photo.jpg",
  "proposed": "positive",
  "confidence": 0.91,
  "source_url": "https://otzovik.com/review_1234.html",
  "comment": "the label and the capsule match the catalogue bottle",
  "by": "claude-code" }
```

The server fetches the address, stores the picture as `NN_agent.<ext>`, and writes the
proposal. `confidence` MUST be between 0 and 1. `proposed` MUST be `positive`,
`negative`, `unusable`, or `variant`.

The address MUST be `http`, `https`, or a `data:` URL. An `http` or `https` address
MUST NOT resolve to a local or a private address. The media type is always read from
the first bytes of the file, not from the address and not from the server header.

A `data:` URL is the way to propose a picture from a host that the server cannot
fetch: a host that blocks this machine, or a host that omits its intermediate
certificate. Fetch the bytes yourself, then send
`"url": "data:image/jpeg;base64,<base64>"`. This also proves that the stored file is
the file the agent judged. Keep the page address in `source_url`, because the `url`
field then holds the data URI and not an address.

Answer: `{ "ok": true, "slug": ..., "file": "07_agent.jpg", "photos": [...],
"counts": {...} }`.

`photos` holds the short form of every photo of the wine: `{"file": ..., "conf": ...}`.
It holds no label state. Read `GET /api/v1/wine/<slug>` for the full form.

## The routes of the page

These routes serve the review page and the runs page. An agent MAY use them. They
follow the page, so they MAY change when the page changes. The routes under `/api/v1/`
do not change in this way.

`GET /dataset` serves the Dataset page. `GET /img/catalog?slug=<slug>` serves the
unmodified `local_path` of one catalogue record. `GET /img/patch?slug=<slug>` serves
the correction from `patch_dir`. A browser navigation to one of these two image routes
gets an HTML preview on a checkerboard. The preview states the natural pixel
dimensions. `raw=1` always gets the image bytes. `view=1` always gets the preview when
`raw=1` is absent. An image request and a client that does not accept HTML get the
image bytes by default. `GET /img/alternative?slug=<slug>&file=<file>` serves one
active alternative. The image routes stay separate because a patch replaces the
catalogue image and an alternative adds a view.

`GET /embedding` serves the Embedding page. `GET /img/embedding` serves one exact
prepared image. It takes `slug`, `kind`, and, for an additional image, `file`. The
allowed kinds are `main`, `main-label`, `additional`, and `additional-label`.

An agent SHOULD use `POST /api/v1/propose` and MUST NOT use `POST /api/label`. A label
is the decision of the reviewer.

Every route in this section answers `application/json`.

### Read

#### `GET /api/embedding`

The answer holds every catalogue record with its prepared main image, main label, and
additional image pairs. Each image states `kind`, `file`, `available`, and `ignored`.
The top level holds the configured source paths and the counts of available, ignored,
and missing-label images.

#### `POST /api/embedding-ignore`

Set one prepared image to ignored or used. The body is
`{"wine_slug":"<slug>","kind":"<kind>","file":"<file>","ignored":true}`.
`file` is required only for an additional image. The server refuses an unknown image.
It writes `embedding_ignore_file` atomically.

#### `GET /api/dataset`

The full configured catalogue in one answer:
`{catalog_file, patch_dir, patches, alternative_dir, alternatives, barcode_file,
barcodes, qr_urls, atlas_matches_file, atlas_bindings_file, atlas_bindings,
atlas_manual_bindings, records}`. The order
of `records` is the order of `catalog.jsonl`. Each record keeps every source field. It
adds `_patched`, `_alternatives`, `_barcodes`, `_qr_urls`, `_atlas_product_uuid`, and
`_atlas_binding_source`. The source is `automatic`, `manual`, or null. A manual UUID
replaces an automatic UUID for the same slug.

#### `GET /api/image-label-descriptions?sha256=<sha256>`

The lab server alone (plan 61). The label descriptions of one linked image:
`{sha256, rows, latest_id, failure, max_attempts}`. `rows` holds each row of
`image_label_description`, the latest first: `id`, `sha256`, `description`,
`created_by` (`vlm` or `manual`), `created_at`, and the VLM columns `vlm_name`,
`vlm_endpoint`, `vlm_model`, `vlm_served_model`, `max_tokens`, `thinking`,
`input_sha256`, `vlm_request`, and `vlm_reply` (null in a manual row). `failure` is
`{attempts, error, updated_at}` of stage 3, or null. A `sha256` that is not 64 lower-case
hex digits answers `400`. An image that no wine links answers `404`.

#### `POST /api/image-label-description` and `DELETE /api/image-label-description`

The lab server alone (plan 61). `POST` with `{"sha256":"<sha256>","description":{...}}`
adds a manual row, which becomes the latest. `description` MUST be a JSON object of at
most 64 KiB; it gets no schema check. `DELETE` with `{"id":<id>}` removes one row. When
the image has no row after the removal, its failures of stage 3 go too, and the watcher
describes it again. Each answer is the answer of the GET for the image. A bad body
answers `400`; an unknown image or id answers `404`.

#### `POST /api/dataset-patch?slug=<slug>`

Write one patch image. The request body is the image bytes. The server accepts JPEG,
PNG, WebP, GIF, and BMP files up to 20 MB. The server detects the file type from the
bytes and writes `<slug>.<extension>` into `patch_dir`. A previous patch moves to
`patch_dir/.trash`. Existing crop and label images for the slug move to `.trash` in
their directories. The Dataset page calls this route only when the reviewer presses
`Apply`.

#### `DELETE /api/dataset-patch?slug=<slug>`

Remove the patch from the active patch set. The file moves to `patch_dir/.trash`, so it
can be recovered. Existing crop and label images for the slug move to `.trash` in their
directories. The Dataset page calls this route only when the reviewer presses `Apply`
after `Remove`.

#### `POST /api/dataset-alternative?slug=<slug>`

Add one alternative catalogue photo. The body and the validation rules equal the patch
upload rules. The server writes `alternative_dir/<slug>/NN_manual.<extension>` and
returns the active file names of the slug. The Dataset page calls the route only after
the reviewer presses `Apply`.

The lab server stores the photo in its image store and scans it with
`POST <qr_scanner.endpoint>/scan`, with the engine of the top-level `qr_scanner` key of
`config.yaml` (plan 76). The endpoint MAY be `"{env:QR_SCANNER_ENDPOINT}"`. Each valid barcode is
normalized as a GTIN-14. Each QR code that contains an HTTP or HTTPS URL is normalized
as a QR URL. Missing values are added to `wine_code` before the response record is
built. Invalid values and existing values are ignored. A scanner failure does not
reject the image. The answer then contains a warning that the photo was stored without
new code fields.

#### `DELETE /api/dataset-alternative?slug=<slug>&file=<file>`

Remove one active alternative photo. The server moves it to
`alternative_dir/.trash/<slug>/`. The Dataset page calls the route only after `Apply`.

#### `POST /api/dataset-alternative-cut` and `DELETE /api/dataset-alternative-cut?slug=<slug>&sha256=<sha256>`

The lab server alone (plan 56). `POST` takes the JSON body
`{"slug": "<slug>", "sha256": "<sha256>", "points": [[x, y], ...]}` of at most 64 KiB. It
stores the manual cut of one alternative photo: the photo cut along the polygon, on a
transparent background. The points are in the pixels of the original after its EXIF
orientation: 3 to 1000 points; the server rounds and clamps each value. The cut replaces
the SAM3 cut of the kind of the current type (`package` for `FF` and `FB`, `label` for
`LF` and `LB`). No automatic run replaces it. `DELETE` removes the manual cut of that
kind, and SAM3 cuts the photo again. The answer holds `ok`, `slug`, `record`,
`alternatives`, `type`, `kind`, `changed`, and a `warning` when SAM3 does not answer.
Each photo of `record._alternatives` holds `manual` and `manual_points`. HTTP 400 is a bad
body or bad points, HTTP 404 no wine or no such photo, and HTTP 409 a type change during
the request.

#### `POST /api/dataset-alternative-recut`

The lab server alone (owner message of 2026-09-27T00:51:44+0300). The JSON body is
`{"slug": "<slug>", "sha256": "<sha256>"}`. The route segments one alternative photo
again, for the kind of its current type (`package` for `FF` and `FB`, `label` for `LF`
and `LB`). First, SAM3 gets each request of that cut with no read of the model cache;
the fresh answers replace the cache records. A full photo with transparent pixels needs
no SAM3 request. Then the server removes the cut of that kind and cuts the photo again
from the fresh records. A label type keeps the close-up rule. The answer holds `ok`,
`slug`, `record`, `alternatives`, `type`, `kind`, `changed` (true), and a `warning` when
the photo gets no processed file. HTTP 400 is a bad body, HTTP 404 no wine or no such
photo, HTTP 409 a manual cut of that kind (remove it first; the manual cut stays), and
HTTP 503 no answer of SAM3 (the old cut stays).

#### `POST /api/dataset-barcode`

Add one product barcode to a catalogue slug. The JSON body is
`{"slug":"<slug>","barcode":"<value>"}`. The server removes whitespace from the
value. It refuses an empty value, a value above 128 characters, and a value that
already belongs to a slug. The server preserves QR codes and other record fields in
the structured code map. The Dataset page calls the route when the reviewer presses
the checkmark icon. Pressing the cross icon writes nothing.

#### `DELETE /api/dataset-barcode?slug=<slug>&barcode=<value>`

Remove one exact product barcode from one catalogue slug. The server refuses a value
that the slug does not own. It preserves the QR code and every other record field. If
the removed value is the last barcode, the structured record stays and its `barcode`
field becomes `null`. The answer is `{ok, slug, removed, barcodes, total}`.

#### `POST /api/dataset-qr-url`

Add one wine page URL decoded from a QR code. The body is
`{"slug":"<slug>","url":"<http-or-https-url>"}`. The server normalizes the scheme,
host, port, path, and fragment in the same way as the matcher. It refuses an invalid
URL and a normalized URL that already belongs to a slug. It writes the value to the
`qr_code` field of the shared code map. The answer is
`{ok, slug, url, qr_urls, total}`.

#### `DELETE /api/dataset-qr-url?slug=<slug>&url=<url>`

Remove one QR URL from one slug. The server preserves every barcode and other record
field. If the removed URL is the last QR URL, `qr_code` becomes `null`. The answer is
`{ok, slug, removed, qr_urls, total}`.

#### The barcode scans after a code change

The lab server alone (owner answers of 2026-09-27T16:49:57+0300). A successful `POST` or
`DELETE` of `/api/dataset-gtin` or `/api/dataset-qr-url` deletes the stored barcode scans
of the test photos of the wine. A stored scan is a record of `data/cache/models/barcode/`. A test
photo of the wine is a row of `test_photo` with `place` equal to the slug. The next run
scans these photos again. A refused request deletes no record. The answer does not
change. When a record cannot be deleted, the answer is HTTP 503, and the code change stays.

#### `POST /api/dataset-atlas-binding`

Create or replace one manual Drink Atlas Core product binding. The JSON body is
`{"slug":"<slug>","product_uuid":"<uuid>"}`. The server validates and normalizes the
UUID. It writes the row to `atlas_bindings_file`. The automatic match file does not
change. A manual row replaces the automatic value for the same slug. Several slugs MAY
use the same product UUID. The Dataset page calls the route when the reviewer presses
the checkmark icon. Pressing the cross icon writes nothing.

#### `POST /api/dataset-atlas-binding-approve`

The lab server alone. A person confirms one automatic Drink Atlas Core product of one
wine. The JSON body is `{"slug":"<slug>","product_uuid":"<uuid>"}`. The server changes
the source of the row from `automatic` to `manual`. The row keeps its place in the list.
The answer is `{ok, slug, approved, source, products, total, manual}`; `products` is the
list of the wine after the change. A wine that does not exist answers `404`. A UUID
that the wine does not have answers `404`. A manual UUID answers `409`. A bad UUID or no
slug answers `400`.

#### `GET /api/dataset-validation`

The current Dataset validation state. The answer holds `running`, `selected`,
`started_at`, `finished_at`, `current_check`, `progress`, `results`, and `error`.
This route starts no work. A completed result stays available until the next job.

#### `POST /api/dataset-validation`

Start one background Dataset validation. The body is
`{"checks":["slugs","images","pages"]}`. At least one known check is required.
The route answers `202` with the initial state. It answers `409` when a job runs.

`slugs` compares `catalog.jsonl` with the public wine sitemap. `images` downloads each
`image_url` and compares its SHA-256 with `local_path`. This is an exact byte check.
`pages` compares the file name of `image_url`, or `upload_file` when the URL is absent,
with the file name of `og:image` on `page_url`. The checks write no file.

#### `GET /api/rows`

The whole state in one answer: `{rows, labels, wines, excluded, groups, slugs}`. The
page reads it once at the start. It is large, about 2500 photos and 850 wines.

`rows` holds first the wines that have a directory in `my/`, then the catalogue cards
that have none. A catalogue card carries `catalog_only: true`.

One row is the virtual NULL wine, the slug `__null__`. It carries `null_row: true`. Its
photos match NO card of the catalogue. The row is answered even when
`<photo_dir>/__null__/` is not present yet. It is not in `GET /api/v1/wines`, and
`POST /api/v1/propose` refuses it: a reviewer moves a photo there, an agent does not.

A row is not the record of `GET /api/v1/wines`. A row holds `has_bottle` and
`min_conf`, and it holds no label count, because the page counts the labels itself
from `labels`.

An agent SHOULD use `GET /api/v1/wines`, which pages and filters.

#### `GET /api/state`

`{labels, wines, excluded, counts}`. The same state without the rows.

`labels` maps a slug to a file name to an entry. An entry holds only the fields that
were written: `label`, `proposed`, `by`, `confidence`, `source_url`, `comment`,
`reassign_to`, `copy_to`, `delete`, `moved_from`, `copied_from`, and `ts`. A field that was never written is
absent, not null. The entry is removed when no field is left.

#### `GET /api/checks`

`{checks: [{id, title, help}]}`. The checks that `POST /api/validate` can run. The
page draws one line per check in its dialog, so a new check needs no change of the
page.

#### `GET /api/reload`

Read the directory `my/` again, read the variant groups again, and build the rows
again. Answer: `{rows, labels, wines, excluded}`. Use it after a script wrote into
`my/` behind the server. The route writes nothing.

#### `GET /api/suggest?slug=<slug>`

`{slug, targets}`. The wines that a photo of this wine most likely belongs to, best
first, at most 5. The photos of one producer look alike, and a search result often
shows the right wine in the wrong bottle.

The order is: a member of the variant group of this wine, then the same producer, then
a wine whose name shares words. Each target holds `{slug, name, producer, category,
has_bottle, in_group, score}`. `score` has no unit. It only orders the list.

#### `GET /api/runs` and `GET /api/run?id=<id>`

The match runs. `GET /api/runs` answers `{runs: [...]}` with the headline metrics of
each run. `GET /api/run` answers `{run, metrics, head, filter, sort, total, offset,
limit, rows}` for one run.

`GET /api/run` takes `id` (required), `filter`, `q`, `sort`, `limit` (1 to 1000,
default 200), and `offset`. `filter` is one of `all`, `error`, `hit`, `miss`, `near`,
`absent`, `rank_2_5`, `after_5`, `after_10`, `false_match`, `negative_in_topk`, `negative`,
`negative_above_positive`, `twin_conflict`, `rule_acted`, `rule_changed`. `rule_acted` keeps
the rows where the cluster rule step of `svoe-vino-matcher` asked the VLM; `rule_changed`
keeps the rows where the answer changed the order. Both read the `explain` record with
`kind: cluster_rules` of a candidate. `sort` is one of `manifest`, `worst`, `rank`, `latency_desc`,
`latency_asc`, `score_desc`, `score_asc`, `path`. `manifest` is the order that the
backend answered in.

The shape of one row follows the match runner, not this server. Read
`docs/match-runner.md`.

One field is added by this server and is not in `results.jsonl`: `twin`. It names the
true wine of a negative photo, which the server reads from a byte-equal `positive` photo
of the same run. It holds `slugs`, `rank`, `forbidden_rank`, `verdict` (`above`, `below`,
`no_forbidden`, `absent`, or `null`), `conflict`, and `conflict_slugs`. The filter
`negative_above_positive` keeps the rows whose `verdict` is `below`. The filter
`twin_conflict` keeps the rows whose `conflict` is true, which is a defect of the photo
set. Read `docs/match-runner.md`.

Errors: `400` for a bad identifier, a bad number, or an unknown order. `404` when no
run holds the identifier.

#### `GET /api/run-inputs?id=<id>&query=<query id>`

The exact derived query images that the local matcher passed to an embedding model or
to a VLM for one result row. The Runs page reads this route only when the user opens
the matched photo.

The route reads the backend URL and the source SHA-256 from the run. It reads the
matching local matcher configuration and the content-addressed label crop cache. It
applies the recorded image preparation and model resize rules. It does not call an
embedding model, a VLM, or SAM3. It refuses the reconstruction when the source bytes
changed after the run.

The answer holds `{run, query, pipeline, config, inputs, notes}`. Each item of `inputs`
holds `{sha256, uses, pipelines, label, model, width, height, mime, src}`. `uses` can
hold `Embedding`, `VLM`, or both. `src` is a data URL of the bytes sent to the model.
`notes` explains a barcode or QR short-circuit and any transient model input that the
run did not store.

A run of a pipeline of the backend `embedding` (`backend.kind` is `embedding`, plan 33)
gets the model input of each view. The route prepares the photo again with the steps that
`run.json` records and with the SAM3 answers of `data/cache/models/sam3/`. It sends no request.
Each item has `uses: ["Embedding"]`; `pipelines` and `label` hold the view (`full` or
`label`). A view with no input gets a note. When the cache holds no SAM3 answer of the
photo, `inputs` is empty, and a note states the reason.

Errors: `404` for an unknown run, query, or source image. `422` when the exact input
cannot be rebuilt. `500` when a local file cannot be read.

#### `GET /api/run-candidate?id=<id>&query=<query id>&slug=<slug>`

The catalogue inputs of one candidate of one result row of a run of the backend
`embedding` (plan 38). The Runs page reads this route only when the user opens the image
of a candidate.

Since plan 38, each candidate of such a run holds the key `items` in `results.jsonl`:
each current item of the wine in the index of the run, in the view order of the entry,
the highest cosine first inside a view. An item holds `{sha256, view, type,
embedding_hash, cosine}`. `sha256` is the `source_sha256` of the catalogue image. `type`
is the image type of the wine column, for example `main` or `main_patched`. `cosine` is
the cosine to the query vector of the same view, with 4 decimals, or null when the query
has no vector of this view. `/api/run` removes `items` from its rows. For an entry with
`rotation_step` (plan 82), the rows of one image give one item, and the item holds `angle`:
the angle of the rotated row with the best cosine. The candidate holds `angle` too: the
angle of its best `full` row.

The answer holds `{run, query, slug, score, views, items, notes}`. `views` maps each view
of the query to the best cosine of the candidate. Each item holds the keys above and
`best`, `state`, `url`, `width`, and `height`. `best` is true for the item whose cosine
equals the best cosine of its view. `state` is `same` when the present index holds the
item with the same `embedding_hash`: then `url` names
`/embeddings/<name>/images/<sha256>_<view>.png`, the PNG that went to the model. `changed`
(another hash) and `gone` (no item or no file) get the `url` null. A run from before plan
38 has no `items`: the answer then lists the items of the wine in the present index with
`cosine` null and `state` `current`, and a note states it. A run of another backend gets
no item and a note. The route sends no request to a model.

Errors: `404` for an unknown run or query, and for a slug that is not a candidate of the
query.

#### `GET /api/run-steps?id=<id>&query=<query id>`

The steps of one result row for the step popup of the Runs page (plan 41). The page reads
this route when the user clicks the query photo of a row. `pipeline/run_steps.py` builds
the answer. The route sends no request to a model, to SAM3, or to the matcher.

Since plan 41, each row of an embedding run holds the key `trace` in `results.jsonl`:
`{v: 1, steps: [...]}`. A step holds `id`, `start_ms` and `ms` (counted from the start of
the photo, one decimal), and `out`, the result of the step. The ids in their order are
`input`, `sam3-package`, `sam3-label`, `view` (with `view`), `embed`, `search` (with
`view`), and `score`. A SAM3 step holds `cached`: true when `model_cache` gave the
answer. A view with no input holds `skipped`, and a step that raised holds `error`; the
trace ends at that step. `view.out` holds `width`, `height`, `bytes`, and `sha256` of the
PNG that went to the model. `search.out` holds `rows`, `wines`, and `top`: the `top_k`
wines of that view alone, each with `slug`, `cosine`, and the `sha256`, `type`, and
`embedding_hash` of its best item (plan 82: and the `angle` of the best row, for an entry
with `rotation_step`; `rows` then counts the rotated rows). A pipeline with the key
`barcode` (plan 42) adds the
step `barcode` first; on a code hit the trace holds that step alone. `/api/run` removes
`trace` from its rows.

The answer holds `{run, query, kind, configuration, photo, row, recorded, rounds, notes}`.
`kind` is `embedding`, `matcher`, `remote`, `request`, or `none`. `recorded` is true when
the row holds a trace. Each round holds `{n, title, note, steps}`. Each step holds `{n, id,
name, service, model, group, start_ms, ms, state, cached, error, artifacts, lists, vlm,
settings, result, notes}`. `state` is `done`, `failed`, or `skipped`. `ms` null means that
the run recorded no time. An artifact holds `{src, caption, width, height, boxes, check}`:
`boxes` are boxes in the pixels of the image, and `check` is `same` or `changed` when the
image made again is compared with the `sha256` of the trace. A list holds `{title, note,
items}`, and an item holds `{slug, name, rank, score, image, truth, forbidden, moved,
detail}`; `moved` is the move against the order before the step, positive is up. `vlm`
holds the VLM rule answer of a matcher run: `{mode, cluster, window, questions, answers,
answer, chosen, scores, ms, cached, error, changed}`.

An embedding run makes its images again from the SAM3 answers of `data/cache/models/sam3/` and
the steps of `run.json`. A matcher run takes its model inputs from the code of
`/api/run-inputs` and its re-rank steps from the `explain` records of the candidates.

Errors: `404` for an unknown run or query. `503` when the lab database cannot be read.

#### `GET /api/run-clusters?id=<id>`

The clusters of the embedding of one run of the lab server, for the cluster frames and
the VLM box of `/runs` (plan 43). The embedding is `backend.embedding` of `run.json`,
or `backend.id` for an older run of an embedding configuration. A run of another
backend has no embedding.

The answer is `{exists, embedding, space, file, built_at, stale, clusters, cards}`.
`space` is `combined`: the view of `data/catalog/embeddings/<embedding>/clusters.json` that the
route reads. One cluster holds `{id, key, kind, size, slugs, rule}`. `rule` holds
`{mode, questions}` of the `label` rule of the cluster in `cluster-rules.json`, or
`null`. `cards` holds `{name}` of each cluster slug from the lab database. `stale` is
true when the inputs of the embedding changed after the cluster build, and `null` when
the status is not known.

A run with no embedding answers `embedding: null` and no cluster. An embedding with no
`clusters.json` answers `exists: false`. A file that cannot be read adds `error`.
Errors: `404` for an unknown run.

#### `POST /api/testset-rename`

Rename one test set without changing its photos, labels, comments, variant groups,
source directory, or order in the selector. The body is `{set, name}` and the answer is
`{ok, set, old_set}`. Both names use `0-9`, `a-z`, `_`, and `-` alone. Errors: `400` for
an invalid or unchanged new name, `404` for an unknown source set, `409` when the new
name exists, and `503` when the lab database cannot be written.

#### `GET /api/testset-from-run?id=<id>` and `POST /api/testset-from-run`

The dialog `New testset…` of `/runs` of the lab server (plan 44). The route makes a new
test set of the lab database from the R@1 misses or the R@5 misses of one run. The run
names its test set in `options.set` of `run.json`.

The GET answer is `{run, set, name, misses}`. `set` is the test set of the run. `name` is
the proposed name `<base>-<N>`: `base` is `set` without a trailing `-<digits>`, and `N` is
the first number that gives a free name. `misses` holds `r1` and `r5`, each
`{title, rule, selected, copied, errors, left_out}`. `selected` counts the positive rows
of `results.jsonl` whose true slug is not at rank 1 (`r1`) or not in the top 5 (`r5`). A
failed request has no rank, so it counts as a miss; `errors` counts such rows. `copied`
counts the selected photos that the set still holds with the same place, file name,
SHA-256, and label. `left_out` maps each reason (`gone`, `other bytes`, `label changed`)
to a count.

The POST body is `{run, misses, name}`. `misses` is `r1` or `r5`. The route writes the
new set in one transaction: a row of `test_set`, a copy of each copied row of
`test_photo`, the comments of the copied photos (`test_photo_comment`), and each variant
group of the source set. No photo file is copied. The answer is `{ok, set, source, run,
misses, photos, selected, errors, left_out, photo_comments, variant_slugs}`. Since plan
51 the wine comments belong to no set, and the exclusion went away, so the answer has no
`wine_notes` and no `excluded`.

Errors: `400` for a bad `misses` and for a name that does not match `^[0-9a-z_-]+$`.
`404` for an unknown run and for a test set that the database does not hold. `409` for a
run with no test set, for a dry run, for a run with no `results.jsonl`, for a name that
the database holds, and for a selection with no photo to copy. `503` when the lab
database cannot be opened.

#### `GET /api/health`

The status part and the endpoints of the Health page of the lab server (plan 46). The
answer is `{time, config_error, endpoints, status}`. `endpoints` lists
`{kind, name, model, endpoint, key_env, error}` for each endpoint of `config.yaml`, in the
order of the page: the `vlm` entries, the `embeddings` entries (with `backend`), `sam3`,
and `remote` (the vino-svoe.ru API, with `used_by`). `error` holds the configuration error
of an entry. `status` holds `server`, `database`, `watcher`, `jobs`, and `gateways`. Each
part holds its own `error`; a part that failed holds `{error}` alone. The route sends no
request to a model: `gateways` sends one `GET /running` to each root with no key.

#### `POST /api/health/check`

The check of one endpoint of the Health page (plan 46). The body is
`{"kind": <kind>, "name": <name>}`. `kind` is `vlm`, `embedding`, `sam3`, or `remote`;
`name` is a name of `endpoints` of `GET /api/health`. The answer is
`{kind, name, status, summary, details, ms}`. `status` is `ok`, `idle`, `warn`, or `error`.
`details` lists each request with its HTTP code and its time, and the notes of the check.
A key value never appears in the answer. A failed check answers HTTP 200 with
`status: error`.

Errors: `400` for a body that is not a JSON object, for an unknown `kind`, and for no
`name`. `404` for a name that `config.yaml` does not hold. `405` for another method.
`503` when `config.yaml` cannot be read.

### Write

Each of these routes answers `{"ok": true, "counts": {...}}` unless the table states
another answer. `counts` is the counter set of the whole review set.

| Route | Body | Answer and rules |
|---|---|---|
| `POST /api/label` | `{slug, file, label}` | The decision of the reviewer. An empty `label`, or `null`, clears it. Clearing the label keeps the other fields of the entry. `400` `unknown photo`. |
| `POST /api/labels` | `{items: [{slug, file, label}]}` | Many labels in one request. Answers `{ok, counts, skipped}`. An item that names no known photo is skipped and counted in `skipped`. The whole list is written under one lock and saved once. `400` when `items` is not a list. |
| `POST /api/comment` | `{slug, file, text}` | A note about one photo, at most 4000 characters. An empty `text` clears it. `400` `unknown photo`. |
| `POST /api/wine-comment` | `{slug, text}` | A note about a whole wine, at most 4000 characters. An empty `text` clears it. `400` for an unknown slug or a longer note. |
| `POST /api/reassign` | `{slug, file, to}` | Record that the photo belongs to `to`. The file is NOT moved. `POST /api/apply-moves` moves it later. An empty `to` clears the record. `400` when the target is unknown or is the slug of the photo. |
| `POST /api/copy` | `{slug, file, to}` | Record that the photo shows the wine `to` as well. The file is NOT copied, and the photo stays in its own wine with its label. `POST /api/apply-moves` copies it later. An empty `to` clears the record. `400` when the target is unknown or is the slug of the photo. |
| `POST /api/mark-delete` | `{slug, file, delete}` | Mark the photo for deletion, or take the mark away. `delete` defaults to true. The file is NOT touched. Answers `{ok, slug, file, delete, counts}`. `400` `unknown photo`. |
| `POST /api/apply-moves` | `{}` | Carry out every recorded copy, every recorded move, and every deletion, in that order. A move takes the source file away, so the copies MUST run first. This route touches the files. A deleted photo is moved into `my/trash/`, not unlinked. A photo that holds both a target and a delete mark is deleted, and is neither moved nor copied. A copy that is done no longer holds `copy_to`, so a second call does not write the file again. Answers `{ok, moved, already_done, failed, copied, copy_failed, renamed, deleted, delete_failed, delete_gone, rows, labels, counts}`. `500` when a file cannot be written. |
| `POST /api/validate` | `{checks: [id]}` | Run the named checks over the whole photo set and answer the defects. The route only reads. An absent `checks` runs every check. Answers `{ok, ran, wines, photos, seconds, findings, slugs}`. `findings` holds one record per defect, with `check`, `why`, and `photos` (a list of `{slug, file}`). `slugs` holds every wine that at least one finding names, sorted. `400` when `checks` is not a list of strings, is empty, or names an unknown check. |
| `POST /api/exclude` | `{slug, excluded, reason}` | Take one wine out of the benchmark, or bring it back. `excluded` defaults to true. A reason is required to exclude, at most 1000 characters. Answers `{ok, slug, excluded, entry, count}`. Read `docs/excluded-slugs.md`. |
| `POST /api/group` | `{slug, target}` | Join two wines into one variant group. The write is one pair. A wine that is in no group takes the group of the other wine. Answers `{ok, changed, group, ...}`; when `changed` is true the answer also holds `rows`, `labels`, `wines`, `excluded`, `groups`, and `slugs`. `409` when both wines are already in two different groups: a merge of two groups cannot be undone by taking one pair away. |
| `POST /api/upload?slug=<slug>&name=<file>` | the picture bytes | The body is the picture itself, not a form. The route writes no label, no score, and no comment. Answers `{ok, slug, file, photos}`. An agent SHOULD use `POST /api/v1/propose` with a `data:` URL instead. |
| `POST /api/inbox-upload?name=<file>` | the picture bytes | Store one external file directly in the unassigned `my/` inbox. The media type comes from the bytes. The route removes path parts and unsafe characters from the source name. It does not replace an existing file. Answers `{ok, file, inbox}`. |
| `POST /api/fetch-image` | `{slug, url}` | Fetch one picture from an address and store it, without a proposal. The rules of the address are the rules of `POST /api/v1/propose`. Answers `{ok, slug, file, photos, url}`. An agent SHOULD use `POST /api/v1/propose` instead. |
| `POST /api/inbox-fetch` | `{url}` | Fetch one picture that was dragged from another browser page. Store it directly in the unassigned `my/` inbox. The address rules equal the rules of `POST /api/v1/propose`. Answers `{ok, file, inbox, url}`. |

### The rules of a picture

`POST /api/v1/propose`, `POST /api/upload`, `POST /api/fetch-image`,
`POST /api/inbox-upload`, and `POST /api/inbox-fetch` store a picture. The five
routes keep the same limits and address rules.

1. The media type is read from the first bytes of the file. The server does not trust
   the address and does not trust the header of the remote server.
2. Only `image/jpeg`, `image/png`, `image/webp`, `image/gif`, and `image/bmp` are
   stored.
3. The picture MUST NOT be larger than 20971520 bytes.
4. An address MUST be `http`, `https`, or a `data:` URL.
5. An `http` or `https` address MUST NOT resolve to a loopback, private, link-local,
   reserved, or multicast address.
6. A picture that belongs to a wine gets the name `NN_<tag>.<ext>`. `NN` is the next
   free rank. The tag is `agent` for `POST /api/v1/propose` and `manual` for the two
   other wine routes.
7. An inbox picture keeps a safe form of its source name. The extension comes from
   the bytes. A name that is already present gets `_inbox2`, `_inbox3`, and so on.

## Errors

Every error of a JSON route answers an object with one field `error`. The field states
why the request was refused.

| Status | Meaning |
|---|---|
| `400` | The request is refused. This is also the status when a picture cannot be fetched or stored. |
| `404` | An unknown wine, an unknown run, or an unknown route. |
| `409` | Both wines of `POST /api/group` are already in two different groups. |
| `500` | A file could not be read, moved, or deleted. |

The server never answers `502` and never answers `503`.

The two routes under `/img/` are the exception. They answer the plain text `not found`
with status `404`, not JSON.

## Known defects

#### The checks

| id | What it reports |
|---|---|
| `shared_positive` | One picture that carries the label `positive` under two or more slugs. One picture cannot show two wines, so one of the labels is wrong, or the two catalogue cards are one wine. Two photos count as one picture when their bytes are equal; a re-encoded or resized copy is not found. A pair of wines that are in one variant group is reported too, and the finding carries `same_group: true` and the group id. |

| `photo_too_small` | One photo whose long side is under 256 pixels. The matcher runs SigLIP2 with an input of 448 by 448 pixels, so such a photo holds less than the half of that input. The check reads the long side, because a photo of a bottle is tall and narrow and its short side is small even when the photo is good. The finding carries `width`, `height`, `long_side`, and `tag`, the text of the pill. |
| `photo_below_model_input` | One photo whose long side is 256 to 447 pixels. The matcher stretches it up to its input. The photo is usable and carries less detail than the model can read. A photo with a long side under 256 pixels is reported by `photo_too_small` only, so the two lists never hold the same photo. |
| `candidate_is_catalog_photo` | One candidate photo that is the catalogue bottle photo of the SAME wine. The set holds real-world photos only, and the bottle photo is a studio render, so such a photo makes the benchmark easier than reality. The check never compares across wines. Two pictures count as duplicates when the bytes are equal, and also when the content is equal and the size differs: each picture is composited on white, converted to grey, cropped to the bounding box of the bottle, and resized to 32 by 32, and the measure is the mean absolute difference of the 1,024 values, on the scale 0 to 255, with the threshold 10.0. A photo marked `unusable` and a photo marked for deletion stay out, and a wine with no catalogue bottle photo is not checked. The finding carries `same_bytes`, `difference`, and `tag`, the text of the pill. |
| `catalog_photo_twin` | Two wines whose CATALOGUE bottle photo is the same picture, or nearly the same. The matcher cannot separate two such wines by the image, and one of the two cards names the wrong bottle. The check reads no candidate photo of `my/`, so a label does not change its result, and it covers the whole catalogue, including a card that has no directory in `my/`. Each picture is composited on white and cropped to the bounding box of the bottle; a grey 32 by 32 signature then names the near pairs of all 2,189,278 pairs, and a COLOUR 128 by 128 signature measures those pairs alone. The second stage is needed: under the grey signature two DIFFERENT wines of one producer line measure as little as 0.09 of 255, which is the band of a true duplicate. A finding reports the whole cluster and carries `slugs`, `bottle`, `same_picture`, `same_bytes`, `distance`, and `tag`. It carries no `photos`. The tag `same pic` means the distance is under 0.05 and the cards carry one picture, which is a defect; the tag `twin` means the distance is 0.05 to 1.0 and the pictures are different photographs of a bottle that looks nearly the same, which is not a defect by itself and is a candidate for a variant group. |

A run of `shared_positive` reads every candidate photo, 2,543 files on the set of
today, and takes about 2.5 seconds. The result is not cached.

`photo_too_small` and `photo_below_model_input` read the header of every photo that is
not marked `unusable` and not marked for deletion, 3,832 files on the set of today, in
about 2.8 seconds. They read the size, not the pixels. On the set of today they report
0 photos and 44 photos.

`candidate_is_catalog_photo` reads the pixels of every candidate photo and of every
catalogue bottle photo, about 6,000 files on the set of today, in about 50 seconds. It
decodes in 8 threads. On the set of 2026-09-18, 304 of the 4,112 pairs are under the
threshold and 0 of them have equal bytes; the check reports 282 photos in 241 wines,
because it leaves out the photos that are already marked `unusable` or marked for
deletion.

`catalog_photo_twin` reads the pixels of every catalogue bottle photo, 2,093 files on
the catalogue of 2026-09-17, in about 43 seconds. It decodes in 8 threads and needs
numpy; without numpy one finding states that and the server does not fail. On that
catalogue it reports 70 findings over 162 wines: 27 clusters with the tag `same pic`
over 55 wines, and 43 clusters with the tag `twin`. Every `same pic` cluster of that
catalogue is byte-identical. The badge of this check sits under the bottle photo of the
row, not on a card, because the finding names no photo of `my/`.

The check has two limits. The measure has no sharp edge between the two classes, so a
copy over the threshold is not reported and the check misses it. The check also
composites a transparent picture on WHITE, so a render that was flattened on another
colour is not found. `ResearchLog.md` holds the measurement and the choice of the
threshold.

1. `GET /api/v1/wines` does not check that `limit` and `offset` are numbers.
   `?limit=abc` raises inside the handler, and the server closes the connection
   without an answer. A client reads this as a connection reset, not as an error.
   `GET /api/run` does check, and answers `400`.
2. `GET /api/v1/wine/<slug>` answers `404` for a catalogue card that holds no
   directory in `my/`, although `GET /api/v1/wines` lists that card under a catalogue
   filter. There is no route that reads one catalogue-only wine.

## The Recognize page

The page `/recognize` recognizes one photo that the user gives (plan 55,
`docs/plans/55_recognize-page.md`). `pipeline/recognize_routes.py` answers each route.

#### `GET /api/recognize`

The pipelines of the backend `embedding` of `config.yaml`, in the order of the file:
`{pipelines: [{name, embedding, barcode, rerank, runnable, reason}]}`. `barcode` and
`rerank` are true when the pipeline has the key. `runnable` is false when the entry has a
configuration error or its embedding has no index; `reason` states why. A pipeline of
another backend is not in the list.

#### `POST /api/recognize?pipeline=<name>&name=<file name>`

The body is the image, 1 byte to 20 MB. `name` is the file name that the page shows; it
MAY be absent. The server writes the image to `work/recognize/<sha256>.<ext>` and keeps
it. Then it starts `pipeline/recognize.py` with `embedding_python`, one process for each
photo, and waits 300 s at most. The script builds the backend of the pipeline and asks it
one time, as a run asks it for a test photo. So the route sends the SAM3 request and the
embedding request of the pipeline; a pipeline with the key `barcode` decodes the photo
first, and a code hit sends no embedding request.

The answer has the keys of `GET /api/run-steps`: `{kind, configuration, photo, row,
recorded, rounds, notes}`, with `kind` `embedding`. The row has no label and no truth. In
addition: `pipeline`; `sha256` of the image; `answer`, the candidates as `[{slug, name,
rank, score, code}]` (`code` is set for a candidate of the code lookup); `build_ms`, the
time of the backend build in the script; and `process_ms`, the wall time of the script
(the start of Python, the build, and the question). The photo of the input step is
`/recognize/photo/<sha256>.<ext>`.

Errors: `400` with the reason for no pipeline, an unknown pipeline, a pipeline of another
backend, a pipeline that cannot run, an empty body, or a body that Pillow cannot read.
`503` when the script gives no answer, fails before the question, or runs over 300 s. A
failure inside the question (SAM3, the embedding endpoint) is not an error of the route:
the answer holds the failed step and `row.error`.

#### `GET /recognize/photo/<sha256>.<ext>`

One uploaded photo, with `Cache-Control: public, max-age=31536000, immutable`. `404` for
an unknown file.

## Hard cases (the relation `similar`) — plan 62

The table `wine_similar` (schema 028) holds the manual pairs of two hard cases: two wines
that are hard to distinguish. The page says `Hard cases`; the routes and the keys keep the
name `similar`. A pair has no direction. Read [plan 62](plans/62_similar-wines.md).

`GET /api/dataset` sends `similar_editor: true` and `similar_pairs` (the number of pairs).
Each record holds `_similar`: the slugs of its partners, in the order of the marks.

### `POST /api/dataset-similar`

The body is `{"slug": "<wine slug>", "other": "<wine slug>"}`. A wine of each state
allows it. The answer:

```json
{"ok": true, "slug": "wine-b", "other": "wine-a", "added": ["wine-a", "wine-b"],
 "similar": ["wine-a"], "other_similar": ["wine-b"], "total": 1}
```

`added` is the stored pair, in sorted order. `similar` and `other_similar` are the
partners of each wine after the write. `total` is the number of pairs.

### `DELETE /api/dataset-similar?slug=<wine slug>&other=<wine slug>`

Removes one pair; the order of the two slugs does not matter. The answer has the keys of
the POST, with `removed` in place of `added`.

Errors of both routes: `400` for a missing slug, a missing `other`, or two equal slugs;
`404` for a wine that does not exist, or a DELETE of a pair that does not exist; `409`
for a POST of a pair that exists; `503` for a database error.

The cluster build (`pipeline/clusters.py`) adds each pair of two Active wines with an
image to the links of each view. Such a link has `"manual"` in its list `by`; a link with
no vector evidence has an empty `spaces`. A cluster with a manual link has `"manual"` in
`signals`; a cluster of manual links alone has the kind `manual`.

## Wine tags — plan 63

The table `wine_tag` (schema 029) holds the free-form text tags of a wine. One wine MAY
have more than one tag. The pipeline does not read the tags. Read
[plan 63](plans/63_wine-tags.md).

The normal form of a tag: no outer white space, lower case. A valid tag has 1 to 64
characters: letters (also Cyrillic), digits, `_`, `-`, `:`, and `.`, with no white space.
Examples: `generic`, `vintage:2017`.

`GET /api/dataset` sends `tag_editor: true` and `wine_tags` (the number of rows: each tag
of each wine counts one time). Each record holds `_tags`: its tags, in the order of the
adds.

### `POST /api/dataset-tag`

The body is `{"slug": "<wine slug>", "tag": "<text>"}`. A wine of each state allows it.
The answer:

```json
{"ok": true, "slug": "wine-a", "added": "vintage:2017", "tags": ["vintage:2017"],
 "total": 1}
```

`added` is the normal form of the tag. `tags` is the list of the tags of the wine after
the write. `total` is the number of rows.

### `DELETE /api/dataset-tag?slug=<wine slug>&tag=<text>`

Removes one tag. The server applies the normal form to `tag` first. The answer has the
keys of the POST, with `removed` in place of `added`.

Errors of both routes: `400` for a missing slug, or a missing or invalid tag; `404` for a
wine that does not exist, or a DELETE of a tag that the wine does not have; `409` for a
POST of a tag that the wine has; `503` for a database error.

## Build all clusters — plan 65

### `POST /api/clusters/build-all`

Starts the queue of `Build all clusters` on `/clusters`: a thread of the lab server builds
`clusters.json` of each embedding entry with no configuration error, one at a time, in the
order of `config.yaml`. The request has no body. The answer is HTTP 202 with
`{"queue": <queue>}`. Errors: `409` while a queue runs; `400` when each entry has a
configuration error. A `GET` of this path is the detail of an entry named `build-all`.

`GET /api/clusters` holds the key `queue`: null before the first queue, else
`{state, names, index, current, waiting, results, started_t, ended_t, message}`. `state`
is `running`, `done`, or `failed`. `waiting` tells why the build of `current` waits (its
embedding build runs), or is null. `results` holds one `{name, state, counts, message}`
for each entry that ended; `state` is `done`, `skipped` (for example no index), or
`failed`. A restart of the server ends the queue and clears it.

## Android device run parameter — plan 86

`GET /api/run-configurations?set=<set>` adds `device_ip: true` to a pipeline that needs
an Android device address.
The other pipelines have `device_ip: false`.

`POST /api/run-jobs` MUST include `device_ip` as an IPv4 string for a pipeline with
`device_ip: true`.
The server rejects a missing or invalid address.
The server also rejects this key for another pipeline or for a self-test.
The runner replaces `{device_ip}` in the configured URL before it creates the HTTP
backend.
The resolved URL is in `run.json` under `backend.url`.

## The self-test of an embedding — plan 67

### `POST /api/run-jobs` with the key `selftest`

Starts the self-test of one entry of `embeddings` (the button `Selftest` of `/embedding`).
The body is `{"selftest": "<embedding>", "limit", "workers", "use_cache"}`. `limit`,
`workers`, and `use_cache` have the rules of a run job. The keys `configuration` and `set`
are not allowed with `selftest`. The server starts `run_job.py --selftest --name
<embedding>`. The answer is HTTP 202 with `{"name": "selftest-<embedding>", "set":
"dataset", "state": "running", "pid"}`. Errors: `400` for a bad body, an entry with a
configuration error, an entry with no index, or a missing `embedding_python`; `404` for an
unknown entry; `409` while the self-test of the entry runs.

`GET /api/run-jobs` lists the job as `selftest-<embedding>`, and `POST
/api/run-jobs/selftest-<embedding>/stop` stops it. The run has `configuration:
selftest-<embedding>`, `options.set: dataset`, and `use_barcode: false`. Each row has the
`wine_slug` of its image as the truth, and `image_path` is
`<wine_slug>/<image_type>-<first 12 hex of sha256>.<extension>`.

## Browser-image drops on the Testset

### `POST /api/testset-fetch`

The body is `{"set", "place", "url"}`. `place` is a wine slug, `__null__`, or
`__drawer__`. The route fetches an image dragged from another browser page and then
applies the rules of `POST /api/testset-upload`: supported image type, 20 MB and pixel
limits, duplicate checks, safe file name, image-store write, and a new unlabelled
`test_photo`. The answer has the upload answer plus `source_url`.

The fetch happens before the database write transaction. The initial HTTP(S) address
and each redirect MUST resolve only to public addresses; loopback, private, link-local,
reserved, multicast, and credential-bearing addresses are refused. The response is read
only through the 20 MB limit. The image signature, not its URL or response media type,
decides whether it is a JPEG, PNG, WebP, GIF, or BMP.

Errors: `400` for an absent, unsafe, unreachable, empty, oversized, or non-image address;
`404` for an unknown set or place; `409` when the place holds the image already; `405`
for another method; `503` for a database error.

## Image tags of the Testset — plan 66

The table `image_tag` (schema 030) holds the free-form text tags of an image. The key is
the SHA-256 of the bytes, so each test photo that holds the bytes shows the same tags, in
each place and in each set. One image MAY have more than one tag. The pipeline does not
read the tags. Read [plan 66](plans/66_testset-image-tags.md).

A tag has the form of a wine tag of plan 63 (`wine_tags.normal`): no outer white space,
lower case, 1 to 64 letters, digits, `_`, `-`, `:`, and `.`.

`GET /api/testset` sends `tags` in each photo: the tags of its image, in the order of the
adds. It sends `tag_names` too: each tag of `image_tag` once, in text order, as
`{"tag", "images"}`. Each write answer of a photo holds `photo.tags`.

### `POST /api/testset-photo-tag`

The body is `{"set", "place", "file", "tag"}`. The server adds the tag to the image of the
photo and sets `test_set.edited_at` of the set. The answer:

```json
{"ok": true, "set": "my", "place": "wine-a", "file": "01.jpg", "added": "blurry",
 "sha256": "<sha256>", "tags": ["blurry"], "tag_names": [{"tag": "blurry", "images": 1}],
 "photo": {"...": "...", "tags": ["blurry"]}, "counts": {"...": "..."}}
```

`added` is the normal form of the tag. `tags` is the list of the tags of the image after
the write.

### `POST /api/testset-photo-tag-remove`

The body is `{"set", "place", "file", "tag"}`. The server applies the normal form to `tag`
and removes it from the image. The answer has the keys of the add, with `removed` in place
of `added`.

Errors of both routes: `400` for a missing place or file, or a missing or invalid tag;
`404` for an unknown set or photo, or a remove of a tag that the image does not have;
`409` for an add of a tag that the image has; `503` for a database error.

The export `pipeline/export_testset.py` writes the field `tags` into the label entry of
each photo whose image has a tag. The import `pipeline/import_testset.py` adds the tags of
the field and never removes an image tag.

## The wait of a run job — plan 88

### `GET /api/run-jobs`

A run job can wait before its event `start`. An example is the wait for a build of the
embedding of its pipeline, with the key `rebuild_embeddings_on_run`. During the wait, the
job has the state `running`, `todo` is null, and `message` is the text of its last event
`log`. An example is `a build of <embedding> runs: PID <pid>; the run waits for its end`.
A job with no event `log` yet has the message `starting`. A SIGTERM during the wait gives
the state `stopping`. The state comes from `job.lock` and `job.log`, so a restart of the
server keeps it.

The wait writes a new event `log` each time the PID of the build changes. An example is a
stop of the build and a new build of the `Build All` queue.

`/testset` shows each running build of `GET /api/embedding-jobs` after its run rows.
`/embedding` shows each running run job of `GET /api/run-jobs` after its build rows, but
not the jobs `selftest-<embedding>`.
