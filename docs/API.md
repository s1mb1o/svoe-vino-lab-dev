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

#### `DELETE /api/dataset-alternative?slug=<slug>&file=<file>`

Remove one active alternative photo. The server moves it to
`alternative_dir/.trash/<slug>/`. The Dataset page calls the route only after `Apply`.

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

#### `POST /api/dataset-atlas-binding`

Create or replace one manual Drink Atlas Core product binding. The JSON body is
`{"slug":"<slug>","product_uuid":"<uuid>"}`. The server validates and normalizes the
UUID. It writes the row to `atlas_bindings_file`. The automatic match file does not
change. A manual row replaces the automatic value for the same slug. Several slugs MAY
use the same product UUID. The Dataset page calls the route when the reviewer presses
the checkmark icon. Pressing the cross icon writes nothing.

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
`run.json` records and with the SAM3 answers of `data/cache/sam3/`. It sends no request.
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
has no vector of this view. `/api/run` removes `items` from its rows.

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

#### `GET /api/run-clusters?id=<id>`

The clusters of the embedding of one run of the lab server, for the cluster frames and
the VLM box of `/runs` (plan 43). The embedding is `backend.embedding` of `run.json`,
or `backend.id` for an older run of an embedding configuration. A run of another
backend has no embedding.

The answer is `{exists, embedding, space, file, built_at, stale, clusters, cards}`.
`space` is `combined`: the view of `data/embeddings/<embedding>/clusters.json` that the
route reads. One cluster holds `{id, key, kind, size, slugs, rule}`. `rule` holds
`{mode, questions}` of the `label` rule of the cluster in `cluster-rules.json`, or
`null`. `cards` holds `{name}` of each cluster slug from the lab database. `stale` is
true when the inputs of the embedding changed after the cluster build, and `null` when
the status is not known.

A run with no embedding answers `embedding: null` and no cluster. An embedding with no
`clusters.json` answers `exists: false`. A file that cannot be read adds `error`.
Errors: `404` for an unknown run.

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
