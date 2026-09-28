# 61 — Label descriptions of the images

Date: 2026-09-27.
Status: approved by the owner on 2026-09-27T14:46:48+0300, with the answer "No, new answers
only" to Q1. Written by drink-atlas-workspace-6b [e99257].
The owner message of 2026-09-27T13:55:59+0300 and the answers of about 14:15:00 are in
[owner-messages.md](../owner-messages.md).

## Goal

1. A new table keeps the label descriptions of each linked image. A label description
   is the answer of `label_rules.DESCRIBE_PROMPT`, the stage 1 prompt of the cluster
   rules (plan 45), or a copy of such an answer that the owner edited.
2. Stage 3 of the watcher `describe_images.py` makes a label description for each
   linked image that has none. It runs in the background, after stage 1 (the class, plan
   26) and stage 2 (the detail, plan 29). It sends its own request. It does not change
   the class request.
3. Each VLM row records the VLM and the settings of the request: the endpoint, the model,
   `max_tokens`, thinking, and the other settings. Each row records its creation time.
4. The latest label description of an image is the effective one. The dialog "Image
   description" of `/dataset` shows each label description of the image as an expandable
   block.
5. The owner can remove a label description. The owner can edit a label description as
   JSON. The edit is saved as a new row.
6. The watcher sends no request for an image that has a label description.
7. The code repairs obvious key drift in each VLM answer, and then checks the answer
   against a JSON Schema. The cluster rules (`label_rules.describe`) repair the same key
   drift.

## Decisions of the owner

Answers of about 2026-09-27T14:15:00+0300:

- Approach A: stage 3 of the watcher, and a fresh run for each linked image.
  `image_detail` (plan 29) stays as it is. The Drink Atlas matcher reads it.
- The request is the exact request of the cluster stage 1. The code checks the result
  and repairs obvious key drift. The cluster code repairs key drift too.
- A removal of the last label description of an image puts the image back in the queue
  of stage 3.
- The edit is a JSON text area. Save adds a new row with `created_by = 'manual'`. That
  row becomes the latest. The VLM row stays in the history.

## Facts of 2026-09-27

- `label_rules.DESCRIBE_PROMPT` equals `describe_images.detail_prompt("package",
  "bottle")` character for character. Stage 2 sent it to 2,069 bottle images, with other
  settings: a JPEG at a long side of 1,536 pixels, `max_tokens` 4,096 or 8,192, and a
  strict JSON Schema. This plan does not use those answers.
- 2,136 distinct images are linked: `main` 2,070, `main_patched` 16, `full_front` 22,
  `label_back` 24, `full_back` 4.
- `data/embeddings/gx10-siglip2-so400m-patch16-naflex-p256/cluster-rules.json` holds 382
  cluster descriptions of 360 distinct images, all of the kind `package`. The median time
  of a call was 15.6 s. The median answer had 340 tokens, the largest 861. 5 answers
  needed the loop guard.
- Key drift in these 382 answers: 132 have the key `text` instead of `texts`. 2 of
  them also have `number` instead of `numbers`. 1 answer has an extra top-level key
  `where`. 1 answer has no key `bottle`.
- The cluster code does not repair key drift now. `parse_json` accepts each JSON object.
  `cluster_rerank.py` reads `texts` alone, so it finds no text in a drifted description.

## Which images

Each image that `wine_image` links to a wine with a type of
`image_descriptions.IMAGE_TYPES`: `main`, `main_patched`, `full_front`, `label_front`,
`full_back`, and `label_back`. This is the set of stage 1.

An image waits for stage 3 when both are true:

1. It has no row in `image_label_description`.
2. It has fewer than `image_description.max_attempts` (3) counted failures in
   `image_label_description_failure`.

The newest link comes first (`wine_image.rowid` descending), as in stage 1.

## The request

The request is the request of `label_rules.describe` for one picture. A test compares
the two payloads.

- The input file: the `package` cut of the image in `image_derivative`, else the
  original. This is the rule of `label_rules.card_pictures` for stage 1.
- The picture: `label_rules.picture_png(path, describe_side)`: upright by its EXIF tag,
  on white where it is transparent, scaled up or down to a long side of `describe_side`
  (2,048), as PNG.
- One user message: the picture as a data URL (`label_rules.data_url`), then
  `label_rules.DESCRIBE_PROMPT`.
- `temperature: 0`, `max_tokens: describe_max_tokens` (1,500),
  `response_format: {"type": "json_object"}`, and `enable_thinking: thinking` (false) in
  the place of the `thinking_field` of the entry.
- The VLM entry: `label_rules.vlm` (`qwen3.5-9b-nvfp4`). The timeout:
  `label_rules.timeout_s` (300 s).
- The loop guard of `label_rules.ask_guarded`: an answer with `finish_reason: length`
  is sent once more with `repetition_penalty: 1.15` and two times `max_tokens` (3,000).
  A second answer that is cut off is a counted failure.
- The settings come from the block `label_rules` of `config.yaml`, through
  `label_rules.config_values`. So stage 3 and the cluster rules send the same request.
  They share the records of `data/cache/`. About 360 images of the backlog get a cache
  hit.
- The errors of the service are the errors of the watcher: an HTTP 429 or 5xx answer,
  no connection, and a timeout are not counted, and the watcher waits (plan 26). A
  timeout gets the probe of plan 49.

## The key repair

`label_descriptions.repair(value)` returns the repaired object and the list of the
renames. The module holds no import outside the standard library and the lab modules
`comments` and `labdb`, because `label_rules` imports it and the embedding virtual
environment has no `jsonschema`.

- A top-level key that is an alias of a key of the prompt gets the key of the prompt,
  when the object does not hold the key of the prompt already:

  | Key of the prompt | Aliases |
  |---|---|
  | `texts` | `text` |
  | `numbers` | `number` |
  | `colours` | `colour`, `colors`, `color` |
  | `marks` | `mark` |
  | `vintage` | `vintage_year` |

- A key that differs from a key of the prompt or from an alias by the letter case alone
  counts as that key, for example `Texts`.
- The repair changes no value and no key inside a value.
- The list of the renames goes into the row, for example `[["text", "texts"]]`.

## The check

After the repair, `describe_images.LABEL_SCHEMA` (Draft 2020-12, `jsonschema` of the
system Python) checks the answer. The forms come from the 382 cluster answers.

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["texts", "numbers", "vintage", "colours", "design", "marks", "bottle"],
  "properties": {
    "texts": {"type": "array", "items": {"anyOf": [
      {"type": "string"},
      {"type": "object", "required": ["text"], "properties": {
        "text": {"type": "string"}, "where": {"type": ["string", "null"]}}}]}},
    "numbers": {"type": "array", "items": {"anyOf": [
      {"type": ["string", "number"]},
      {"type": "object", "required": ["value"], "properties": {
        "value": {"type": ["string", "number"]}, "where": {"type": ["string", "null"]}}}]}},
    "vintage": {"type": ["string", "integer", "null"]},
    "colours": {"type": ["array", "string"], "items": {"type": "string"}},
    "design": {"type": "string"},
    "marks": {"type": "array", "items": {"type": ["string", "object"]}},
    "bottle": {"type": ["string", "object", "null"]}
  }
}
```

- The answer text MUST parse with `label_rules.parse_json`: one JSON object, or the first
  `{...}` in the text. This is the rule of the cluster stage 1.
- A failure of the parse or of the check is a counted failure: `attempts` goes up by
  one, `error` gets the first schema error and the first 300 characters of the answer,
  and no row is written.
- The `model_cache` record is stored only for an answer that passed the check. A cached
  record whose answer fails the check does not count: the watcher sends the request
  again. A valid new answer replaces the record.
- 2 of the 382 cluster answers fail this check: the answer with the extra key `where`
  and the answer with no key `bottle`.

## The cluster rules

`label_rules.describe` applies `label_descriptions.repair` to each new answer. The record
of the card keeps the renames in the key `repairs`. The cluster code does not get the
check of this plan: a card with an answer outside the schema keeps its description.

The 382 stored cluster descriptions do not change. A changed description changes
`inputs_sha` of the rule of its cluster, and the next rules run sends that cluster to
`qwencloud-qwen3.8-max` again. A forced describe run
(`pipeline/build_label_rules.py --name <embedding> --stage describe --force`) repairs them
from the cache. That run is the decision of the owner (open question Q1).

`scripts/cluster_rules.py` (retired by plan 43) and
`svoe-vino-testset/scripts/cluster_rules.py` do not change.

## Schema file

`pipeline/schema/NNN_image_label_description.sql`. The number is fixed at the entry
(rules 25 to 28 of `AGENTS.md`).

```sql
CREATE TABLE image_label_description (
    id               INTEGER PRIMARY KEY,
    sha256           TEXT NOT NULL REFERENCES image (sha256),  -- the linked image
    description      TEXT NOT NULL CHECK (json_valid(description)
                         AND json_type(description) = 'object'),
    created_by       TEXT NOT NULL CHECK (created_by IN ('vlm', 'manual')),
    created_at       TEXT NOT NULL,  -- UTC, `comments.now_utc`
    -- The VLM call. NULL in a manual row.
    vlm_name         TEXT,     -- the name of the `vlm` entry
    vlm_endpoint     TEXT,     -- the chat URL
    vlm_model        TEXT,     -- the model name of the request
    vlm_served_model TEXT,     -- the model name that the service reported
    max_tokens       INTEGER,  -- of the request that gave the answer
    thinking         INTEGER CHECK (thinking IS NULL OR thinking IN (0, 1)),
    input_sha256     TEXT,     -- the file that the VLM got
    vlm_request      TEXT CHECK (vlm_request IS NULL OR json_valid(vlm_request)),
    vlm_reply        TEXT CHECK (vlm_reply IS NULL OR json_valid(vlm_reply)),
    CHECK ((created_by = 'vlm') = (vlm_name IS NOT NULL))
) STRICT;

CREATE INDEX image_label_description_image ON image_label_description (sha256, created_at);

CREATE TABLE image_label_description_failure (
    sha256     TEXT PRIMARY KEY REFERENCES image (sha256),
    attempts   INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    error      TEXT,
    updated_at TEXT NOT NULL
) STRICT;
```

- One image can have many rows. The latest row is the row with the newest
  `created_at`; for the same second, the higher `id`.
- `input_sha256` has no foreign key. It is a reference, and a new cut can replace the
  file.
- `vlm_request` holds the other settings of the request: `prompt`
  (`label_rules.DESCRIBE_PROMPT`), `prompt_sha256`, `input_kind` (`package` or
  `original`), `describe_side`, `sent_size`, `image_format` (`png`), `temperature`,
  `response_format`, `repetition_penalty` (after the loop guard alone), `timeout_s`,
  `settings_sha` (`describe_sha` of `label_rules`), and `cache_key`.
- `vlm_reply` holds `finish_reason`, `usage`, `ms`, `cached`, `loop_guard`, `repairs`,
  and `raw`: the answer text as the service sent it, at most 8,000 characters.
- The times are UTC, to the second, in ISO 8601 with `Z`.

## The rules of the rows

- The watcher inserts its row only when the image has no row at that moment. So a
  manual row that the owner saves during a call stays the latest, and the VLM answer is
  dropped. The log line says `not taken`.
- A manual row holds a JSON object of at most 64 KiB. It gets no schema check. Its VLM
  columns are NULL.
- A removal deletes one row. When the image has no row after the removal, the removal
  also deletes the failure row of the image, and the image waits for stage 3 again.

## The watcher

Hunks in `pipeline/describe_images.py`. The functions of the tables are in the new
`pipeline/label_descriptions.py`.

- A new key `image_description.labels` turns stage 3 on. The default in the code is
  false. So the tests and a configuration with no key run stage 1 and stage 2 alone.
- `next_items` takes the images that wait for a class first, then the images that wait
  for a detail, then the images that wait for a label description.
- The calls of stage 3 use the same workers, lock, backoff, and state file.
- The log line of stage 3: the time, the short sha256, `label`, the result, the input
  kind, the number of texts, the renames, the time of the call, and the cache hit.
- `--label-sha <sha256>` makes the label description of one linked image and stops. An
  image that has a label description is skipped.
- `--retry-failed` also sets the failure count of stage 3 to 0.
- The state file names the stage `label` of a call that runs.

## The indicator of the watcher

- `image_descriptions.watcher_status` adds `labels_linked`, `labels_done`,
  `labels_failed`, and `labels_pending`.
- `image_descriptions.call_view` shows the input file, the attempts, and the error of a
  call of the stage `label`.
- The pill `#vlm-status`: `VLM labels <done> / <linked> · <speed>` while stage 3 works;
  the idle text adds `· labels <done> / <linked>`.
- The dialog of the pill gets the row `Labels`.

## The lab server

A new module `pipeline/label_description_routes.py` answers three routes. The lab
server sends them to `respond`, as it does for `testset_routes`.

- `GET /api/image-label-descriptions?sha256=<sha256>`: `sha256`, `rows` (newest first),
  `latest_id`, `failure` (`attempts`, `error`, `updated_at`, or null), and
  `max_attempts`. Each row holds its columns, with `description`, `vlm_request`, and
  `vlm_reply` parsed.
- `POST /api/image-label-description`, body `{"sha256": "...", "description": {...}}`:
  adds a manual row. The answer is the answer of the GET.
- `DELETE /api/image-label-description`, body `{"id": <id>}`: removes one row. The answer
  is the answer of the GET for its image.
- The image MUST be linked (`image_descriptions.is_linked`), else HTTP 404. A bad
  `sha256`, `id`, or body gives HTTP 400.
- `GET /api/dataset` does not change. The dialog loads the label descriptions of one
  image when it opens.

## The Dataset page

The dialog "Image description" gets a section `Label description` below `Raw VLM reply`.

- A status line: the number of rows and the source of the latest row; else "No label
  description yet. The watcher describes each image that has none."; and the failures of
  stage 3 in red.
- One `<details>` block for each row, newest first. The latest block is open; the other
  blocks are closed. The summary: `#<id>`, `latest` for the latest row, `VLM` or
  `manual`, the time, and for a VLM row the entry, the served model, `max_tokens`, and
  thinking. The body: the JSON of the description, a line of the other settings, the
  raw answer in a closed block, and the buttons `Edit as new` and `Remove`.
- `Edit as new` opens a text area with the JSON of that row. An image with no row gets
  the button `Add manual`, with an empty object of the seven keys. `Save as new` sends
  the POST. The text MUST parse as a JSON object.
- `Remove` asks for a confirmation, then sends the DELETE.
- The class fields, `Save`, and `Cancel` of the dialog do not change. `Save` saves the
  class fields alone.
- Both themes use the color variables of the page. The text area and the blocks fit
  390 pixels.
- drink-atlas-workspace-1d [e2bf93] changes `openDescribe`, `closeDescribe`, the
  `popstate` listener, and the `init` block (a page path for the dialog). This plan adds
  one line in `openDescribe`, before `$("#describe-modal").hidden = false;` (agreed with
  1d at about 14:30).

## Tests

- `tests/test_label_descriptions.py` (new): the repair; the queue (no row, failures, a
  manual row, the input file, the newest link first); the insert rule of the watcher; the
  failures and their reset; the history order and the latest row; a manual row; a
  removal and the queue after the last removal; the counts; the three routes on a
  temporary database.
- New tests at the end of `tests/test_describe_images.py`: the stage 3 payload equals
  the payload of `label_rules.describe`; stage 3 runs after stages 1 and 2; `labels:
  false` sends no request of stage 3; the loop guard; a repaired answer; an answer that
  fails the check writes nothing and is not cached; a cached record that fails the check
  is sent again; the recorded settings; an image with a row gets no request;
  `--label-sha`.
- `tests/test_label_rules.py`: `describe` repairs a drifted answer.
- `tests/test_labdb.py`: `VERSION` and the table list.
- The tests never call the real VLM.

## Deployment

1. The code and the tests, with the schema file as `NNN_image_label_description.sql` in
   `pipeline/schema_pending/`. The tests run on a scratch copy of the project, where the
   file has its number.
2. A live check before the backlog, on a scratch copy of the database, migrated to the
   new schema, with the real VLM and the shared `data/cache/`: one `main` image with a
   cluster cache hit, one `main` image with no hit, one `label_back` image, and one
   `main_patched` image. The running watcher holds the lock, so the check calls
   `describe_images.label_one` directly.
3. Rule 26: read `pipeline/schema/` and `ACTIVE_WORK.md`, send a message to each session
   with schema work, and take the next free number.
4. A backup of `data/lab.sqlite3`, then the migration with `pipeline/labdb.py`.
5. The restart of 8168 with SIGTERM (rules 22 to 24). Before the restart, this session
   sends a message to each active session with uncommitted code of the server.
6. The lab server starts the new watcher, and the backlog starts. Start
   `caffeinate -ims -w <watcher pid>`. Add a row to `/Users/ashmelev/Admin/GPU_TASKS.md`.
7. Read the log and the first rows. Look at the dialog in headless Chromium, in both
   themes and at 390 pixels.

## Time

About 1,780 calls are not in the cache. The watcher made about 1,000 detail calls per
hour with 8 workers on 2026-09-25. A picture of 2,048 pixels holds more image tokens, so
the backlog MAY take 2 to 3 hours. This is an estimate, not a measurement.

## Risks

- The model can answer the bottle prompt for a label close-up with no key `bottle`. Such
  an answer fails the check three times, and the image stops. The owner can add a manual
  row. The count shows on the pill.
- With `temperature: 0` a repeated request can give the same answer that failed. So a
  failed image MAY use three calls.
- A restart of 8168 deploys the uncommitted code of the other sessions (step 5).

## Answered questions

- Q1. Does a forced describe run repair the 382 stored cluster descriptions now? Then
  the rules of the clusters with a repaired card become stale, and the next rules run
  sends them to `qwencloud-qwen3.8-max`. Answer of 2026-09-27T14:46:48+0300: "No, new
  answers only".

## Result on 2026-09-27

- The code and the tests were made on a scratch copy of the project, because a restart
  of 8168 by another session deploys each file on disk. The full suite on the scratch
  copy: 1,209 tests OK.
- The live check of step 2 on a scratch copy of the database (version 27) with the real
  VLM and the shared `data/cache/`: a `main` image with a cluster cache hit (0.3 s, the
  record of the cluster run), a `main` image with no hit (19.6 s), a `label_back` image
  (the original; the loop guard: 2,021 completion tokens at `max_tokens` 3,000, 182 s),
  and a `main_patched` image (14.7 s). 3 of the 4 answers needed the rename `text` ->
  `texts`. Browser check on a scratch server (port 8175, `watch: false`): 44 of 44 checks
  in light and dark mode, at 1,280 and 390 pixels, with no page error.
- Rule 26: `pipeline/schema/` ended at 026, and no other section named schema work.
  027 was taken at 15:16:26. Backup
  `data/backups/lab-before-027-image-label-description-20260927T121654Z.sqlite3`; entry
  at 15:16:55; `data/lab.sqlite3` at version 27 at 15:16:56.
- 8168 restarted at 15:17:20 with SIGTERM (server pid 55047, watcher pid 55081,
  `caffeinate -ims -w 55081` pid 57284). 1d, 64, and d8 got a notice before the
  restart. No other server file had changed after the restart of d8 at 14:57:17.
- The full suite in the live tree: 1,211 tests OK. A read-only browser check of the live
  page: the dialog and the pill `VLM labels 29 / 2,154 · 8.4 s`, no page error.
- The first 39 rows (15:17 to 15:23): 11 loop guards, 9 renames, 1 counted schema failure
  (no key `marks`), about 6 images per minute. The newest links come first, and many of
  them are dense close-ups, so the rate of the older `main` images can be higher. The
  estimate of the section "Time" was too low: the backlog MAY take 4 to 6 hours (5.7
  images per minute at 15:26).
- The rate rose to about 22 images per minute after 15:26 (the cache hits and the `main`
  bottles). drink-atlas-workspace-2f [0e9cfe] restarted 8168 at 15:47 for schema 028; the
  new watcher (pid 47284) took the backlog over. The keeper `work/plan61-caffeinate.sh`
  held `caffeinate` across the restart and stopped by itself at 16:49.
- The backlog ended at 16:49 (1 h 32 min): 2,162 of 2,166 linked images have a label
  description. 358 answers were cache hits of the cluster run, 39 needed the loop guard,
  800 (37 %) needed the rename `text` -> `texts` and 21 the rename `number` -> `numbers`.
  2,130 calls got the `package` cut, 32 the original.
- 2 images stopped after 3 counted failures: `2f5b5c1083a4` (main,
  `derbent-vino-di-kaspiko-shardone-beloe-suhoe-125`) and `b8f64d68dc72` (main,
  `katharon-semi-sweet`). The model wrote the texts flat at the top level, with repeated
  `text` and `where` keys, so the extra key `where` fails the check. The owner can add a
  manual row in the dialog (`Add manual`). A retry (`--retry-failed`) sends the same
  request, and `temperature: 0` will probably give the same answer.

## Files

- New: `pipeline/schema/NNN_image_label_description.sql`,
  `pipeline/label_descriptions.py`, `pipeline/label_description_routes.py`,
  `tests/test_label_descriptions.py`.
- Hunks: `pipeline/describe_images.py` (the docstring, the imports, the settings,
  `LABEL_SCHEMA`, the stage 3 functions, `next_items`, `run_item`, `main`),
  `pipeline/image_descriptions.py` (`call_view`, `watcher_status`),
  `pipeline/label_rules.py` (one import, `describe`), `pipeline/lab_server.py` (the
  docstring, the import, one branch in `do_GET`, one branch in `_write_route`, a new
  `Handler._label_descriptions`), `pipeline/pages/dataset.html` (the CSS, the section
  markup, the new functions, one line in `openDescribe`, `vlmStatusView`,
  `renderVlmDialog`, `vlmCallHtml`), `config.yaml` (the key `labels` and its comment),
  `tests/test_describe_images.py`, `tests/test_label_rules.py`, `tests/test_labdb.py`.
- Data: `data/lab.sqlite3` (a backup first, then the migration), a restart of 8168,
  `work/describe_images.log`, `/Users/ashmelev/Admin/GPU_TASKS.md` (one row).
- Docs: `README.md`, `COMMANDS.md`, `docs/API.md`, `SMOKE_TESTS.md`, `ChangeLog.md`,
  `ResearchLog.md` (the key drift of the cluster answers), a dated note at the end of
  plan 45.
