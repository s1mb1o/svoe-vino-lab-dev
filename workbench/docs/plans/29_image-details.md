# 29 — Image details: the second VLM pass

Date: 2026-09-25.
Status: approved by the owner on 2026-09-25T20:28:51+0300, with the answer "Later" to Q1.
Written by drink-atlas-workspace-a7 [bbd3b6].
The owner message of 2026-09-25T19:14:31+0300 and the answers of 20:24:17 are in
[owner-messages.md](../owner-messages.md). The probe of 19:20 is in `ResearchLog.md`.

## Goal

1. Plan 26 gives each linked image a class: `package_type`, `subject_scope`,
   `package_view`, and `content_roles`. On 2026-09-25 each of the 2,023 linked images has
   its class.
2. A second VLM pass uses the class to select a detail prompt. The answer describes the
   label, so that a person can tell the wine apart from similar wines of the same
   producer.
3. The VLM gets the cut of the image from `image_derivative`, not the original. So it
   sees only the package or the label.

## Decisions of the owner

- The prompts are the two prompts of the message of 19:14:31. The code sends them
  verbatim, with one change: the word `bottle` is replaced by the name of the
  `package_type`.
- The replacement changes the text and the last key. The text uses a readable name, for
  example `Tetra Pak carton`. The key is the `package_type` value, for example `"can"`.
  The label prompt changes too, for example `one wine can label`. The capsule clause
  stays as the owner wrote it (answer 2).
- The pass is stage 2 of the watcher `describe_images.py`. The watcher classifies first.
  When no image waits for a class, it takes the next image that waits for a detail
  (answer 1).
- An image with `subject_scope` `multiple_packages` or `unknown` gets no detail. It gets
  one when the owner sets `subject_scope` to `full_package` or `label_closeup` (answer 3).
- The VLM is `qwen3.5-9b-nvfp4`. The long side of the image is 1,536 pixels at most.
  `max_tokens` is 4,096. Thinking is off (answer 4).
- The request of stage 2 sends the JSON Schema of the answer in `response_format`
  (`json_schema`, strict). The live check of 20:45 found the key `text` instead of
  `texts` in 3 of 4 answers of the package prompt with `json_object` alone. Stage 1 keeps
  `json_object` (owner answer of 2026-09-25T21:45:41+0300).
- The session MAY add hunks to `pipeline/describe_images.py` and
  `pipeline/image_descriptions.py`. The stale sections drink-atlas-workspace-ca [af6346]
  and drink-atlas-workspace-99 list them. Their work is in commit `f4ebe45` (answer 1).

## Which images

An image gets a detail when all of these are true:

1. `wine_image` links it to a wine, with a type of `image_descriptions.IMAGE_TYPES`.
2. Its row of `image_description` has `subject_scope` `full_package` or `label_closeup`.
   The value can come from the VLM or from the owner.
3. Its `package_type` has a name in the table of the section "The prompts". The values
   `other` and `unknown` have no name, so such an image gets no detail.

On 2026-09-25 this gives 2,015 images: 2,013 `full_package` (1,977 `bottle`, 21
`tetra_pak`, 11 `can`, 4 `box`) and 2 `label_closeup` (`bottle`). The 7 images of
`multiple_packages` get no detail.

## The input file of each image

| `subject_scope` | Prompt | The file that the VLM gets |
|---|---|---|
| `full_package` | the package prompt | the cut of the kind `package`; else the original |
| `label_closeup` | the label prompt | the cut of the kind `label`; else the cut of the kind `package`; else the original |

- On 2026-09-25 each `full_package` image has a cut of the kind `package`. One
  `label_closeup` image (a `label_back` photo) has no cut of the kind `package`, but it has
  a cut of the kind `label`.
- The file is read through the row of `image` of the input file:
  `imagestore.folder_of(db_path, folder)/<sha256>.<extension>`.
- The image is prepared as in plan 26 (`describe_images.image_data_url`): upright by its
  EXIF tag, on white where it is transparent, scaled down to a long side of
  `detail_max_side`, and sent as a JPEG at quality 90.

## The prompts

### The names

| `package_type` | `{name}` | `{names}` | `{key}` |
|---|---|---|---|
| `bottle` | bottle | bottles | bottle |
| `can` | can | cans | can |
| `keg` | keg | kegs | keg |
| `bag` | bag | bags | bag |
| `bag_in_box` | bag-in-box package | bag-in-box packages | bag_in_box |
| `tetra_pak` | Tetra Pak carton | Tetra Pak cartons | tetra_pak |
| `barrel` | barrel | barrels | barrel |
| `decanter` | decanter | decanters | decanter |
| `box` | box | boxes | box |

### The package prompt

For `package_type` `bottle`, the text is the first prompt of the owner, character for
character. A test checks this.

```text
This is a catalogue photo of one wine {name}. Describe its label, so that a person can tell this {name} apart from similar {names} of the same producer.
Report only what you see. Do not guess. If a text or a number is too small to read, write "unreadable" for it.
Write each text exactly as it is printed, in its own alphabet. Do not translate it and do not transliterate it.
Answer with one JSON object with these keys:
"texts": a list of every text that you can read, each as {"text": "...", "where": "..."};
"numbers": a list of every number that you can read, such as a year, a ratio or a percentage, each as {"value": "...", "where": "..."};
"vintage": the vintage year if the label shows one, else null;
"colours": the main colours of the label;
"design": a short description of the design and the layout of the label;
"marks": a list of stickers, medals, seals and other marks, each with its place;
"{key}": the colour and the shape of the {name} and of the capsule.
```

### The label prompt

For `package_type` `bottle`, the text is the second prompt of the owner, character for
character. The last line ends with `;`, as in the message of the owner.

```text
This is a catalogue photo of one wine {name} label. Describe it.
Report only what you see. Do not guess. If a text or a number is too small to read, write "unreadable" for it.
Write each text exactly as it is printed, in its own alphabet. Do not translate it and do not transliterate it.
Answer with one JSON object with these keys:
"texts": a list of every text that you can read, each as {"text": "...", "where": "..."};
"numbers": a list of every number that you can read, such as a year, a ratio or a percentage, each as {"value": "...", "where": "..."};
"vintage": the vintage year if the label shows one, else null;
"colours": the main colours of the label;
"design": a short description of the design and the layout of the label;
"marks": a list of stickers, medals, seals and other marks, each with its place;
```

- `{name}`, `{names}`, and `{key}` are the only placeholders. The code replaces them
  with plain string replacement, not with `str.format`, because the prompts hold `{` and
  `}`.
- No fixed-fact lines are added. The class of plan 26 selects the prompt; it is not
  sent as a fact.

## The request

- One user message: the image as a base64 data URL, then the prompt text. The form is
  `describe_images.payload_of`.
- `temperature: 0`, `max_tokens: detail_max_tokens` (4,096), thinking off by the
  `thinking_field` of the entry.
- `response_format: {"type": "json_schema", "json_schema": {"name": "answer", "strict":
  true, "schema": <the schema of the section below>}}`. The gateway 18081 keeps the
  answer to the keys of the schema. The code checks the answer against the same schema
  too (owner answer of 21:45:41).
- The timeout stays 300 s. The probe needed 80 s for a dense back label.
- The call goes through `pipeline/model_cache.py`. The code stores a record only after
  the answer passed the schema check, as in plan 26.
- An answer with `finish_reason: length` is a counted failure. Its JSON is cut off.

## The JSON Schema of the answer

`describe_images.detail_schema(prompt_kind, key)` builds it. The keys are strict. The
values accept the forms that the probe saw, because the prompt does not fix them.

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["texts", "numbers", "vintage", "colours", "design", "marks", "<key>"],
  "properties": {
    "texts": {"type": "array", "items": {
      "type": "object", "required": ["text", "where"],
      "properties": {"text": {"type": "string"}, "where": {"type": "string"}}}},
    "numbers": {"type": "array", "items": {
      "type": "object", "required": ["value", "where"],
      "properties": {"value": {"type": ["string", "number"]}, "where": {"type": "string"}}}},
    "vintage": {"type": ["string", "integer", "null"]},
    "colours": {"type": ["array", "string"], "items": {"type": "string"}},
    "design": {"type": "string"},
    "marks": {"type": "array", "items": {"type": ["string", "object"]}},
    "<key>": {"type": ["string", "object"]}
  }
}
```

- The label prompt has no `<key>`. Its schema has six keys.
- The probe answer with the key `text` instead of `texts` fails this schema. It is a
  counted failure. At `temperature: 0` the next attempt gives the same answer, so the
  request sends the schema (section "The request").
- A failure writes `vlm_error` (the first schema error and the first 300 characters of
  the answer) and adds one to `vlm_attempts`. After `max_attempts` (3) failures the image
  stops.

## Schema file

`pipeline/schema/NNN_image_detail.sql`. The number is fixed at the entry (rules 25 to 28
of `AGENTS.md`).

```sql
-- The detail of one image: the answer of the detail prompt of plan 29.
CREATE TABLE image_detail (
    sha256        TEXT PRIMARY KEY REFERENCES image (sha256),  -- the original
    -- The inputs of the last call. A change of one of them makes the row stale.
    prompt_kind   TEXT NOT NULL CHECK (prompt_kind IN ('package', 'label')),
    package_type  TEXT NOT NULL,
    input_sha256  TEXT NOT NULL REFERENCES image (sha256),  -- the file that the VLM got
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    -- NULL: no valid answer for these inputs yet.
    vlm_at        TEXT,
    vlm_name      TEXT,
    vlm_model     TEXT,
    answer        TEXT CHECK (answer IS NULL OR json_valid(answer)),
    vlm_error     TEXT,
    vlm_attempts  INTEGER NOT NULL DEFAULT 0 CHECK (vlm_attempts >= 0)
) STRICT;
```

- One row for each original. The detail is the same for each wine that shares the file.
- `answer` keeps the full valid answer.
- The times are UTC, in the form of `comments.now_utc`.

## The stale rule

The code computes the wanted inputs of each image from the section "Which images" and
the section "The input file of each image": `prompt_kind`, `package_type`, and
`input_sha256`.

1. An image with no row waits for a detail.
2. A row whose three inputs differ from the wanted inputs is stale. It waits for a detail,
   also when it holds an answer or 3 failures. Examples: the owner changes
   `package_type`; drink-atlas-workspace-cb [48de03] makes a new label cut.
3. A row with the wanted inputs and no answer waits while `vlm_attempts` <
   `max_attempts`.
4. A row with the wanted inputs and an answer is done.
5. An image that is no longer eligible keeps its row. The watcher does not send it.

A write stores the inputs of the call. When the inputs differ from the stored inputs,
the write sets `vlm_attempts` to 0 first and clears `answer`, `vlm_at`, `vlm_name`, and
`vlm_model`. So the count of failures belongs to the present inputs.

## The watcher

Hunks in `pipeline/describe_images.py`, with the functions of the table in a new
`pipeline/image_details.py`.

- Each step asks first for an image that waits for a class (plan 26). Only when none
  waits, it asks for an image that waits for a detail (`image_details.pending`, the
  newest link first). So a new upload gets its class after the detail call that runs.
- Stage 2 runs only when `image_description.details` is true.
- One call at a time, as in plan 26. Note of 2026-09-26: plan 35 replaced this rule. Up
  to `image_description.workers` calls run at the same time (8 in `config.yaml`).
- A failure of the service (HTTP 429 or 5xx, no connection, a timeout) is not counted,
  and the watcher waits as in plan 26.
- The log line of a detail: the time, `detail`, the short sha256, the prompt kind, the
  `package_type`, the result, the number of texts, the time of the call, and the cache hit.
- `--detail-sha <sha256>` gets the detail of one image and stops. The image MUST be
  eligible.
- `--retry-failed` also sets `vlm_attempts` to 0 for the failed detail rows.
- The state file gets the key `stage` (`class` or `detail`) while the state is
  `working`.

## The configuration

New keys in `image_description` of `config.yaml`:

```yaml
image_description:
  watch: true
  vlm: qwen3.5-9b-nvfp4
  max_side: 1024
  poll_seconds: 30
  max_attempts: 3
  details: true
  detail_max_side: 1536
  detail_max_tokens: 4096
```

The defaults in the code: `details: false`, `detail_max_side: 1536`,
`detail_max_tokens: 4096`. So a configuration with no `details` key runs stage 1 alone.

## The indicator of the watcher

- `image_descriptions.watcher_status` adds the counts of stage 2: `details_eligible`,
  `details_done`, `details_failed`, and `details_pending`. The route
  `GET /api/image-description-status` does not change.
- The pill `#vlm-status` of `/dataset`, in `vlmStatusView` and `renderVlmStatus`:
  - `working` in stage 2: `VLM details <done> / <eligible> · <speed>`.
  - `idle` with no pending class: `VLM all <n> described · details <done> / <eligible>`.
  - The title gets one line: `Details <done> of <eligible> · pending <n> · failed <n>`.
  - The red text gets `<n> details failed` when a detail failed 3 times.

## Not in this plan

- A view of the details on `/dataset`. The answers are in `image_detail.answer`. Open
  question Q1.
- The images of `multiple_packages`, of `subject_scope` `unknown`, and of `package_type`
  `other` or `unknown`.
- The use of the details for a match or a rerank.

## Tests

- `tests/test_image_details.py`: the eligible images; the input file of each scope and
  its fallbacks; the stale rule (a new `package_type`, a new label cut); a stale write
  sets the attempts to 0; the counts; the newest link first.
- New tests at the end of `tests/test_describe_images.py`:
  - The package prompt for `bottle` equals the first prompt of the owner. The label
    prompt for `bottle` equals the second prompt. The prompts for `can` and `tetra_pak`
    hold no word `bottle`.
  - The schema: the probe answer passes after the fix of `text` to `texts`; the key `text`,
    an extra key, a missing key, and a label answer with a `<key>` fail.
  - Stage 2 runs after stage 1, and a new image with no class goes first.
  - `details: false` sends no detail request.
  - A `multiple_packages` image gets no request.
  - A request uses `max_tokens` 4,096, the cut file, and `response_format` `json_schema`
    with the schema of the answer. A class request keeps `json_object`.
  - `finish_reason: length` is a counted failure.
- `tests/test_labdb.py`: `VERSION` and the table list.
- `tests/image_description_fixture.py`: cut rows of `image_derivative` for the fixture
  images.
- The tests never call the real VLM.

## Deployment

1. The code and the tests, with the schema file as `NNN_image_detail.sql` in
   `pipeline/schema_pending/`. The tests run on a scratch copy of the project, where the
   file has its number.
2. Live check before the backlog: one `bottle`, one `can`, one `tetra_pak`, and one
   `label_closeup` image. The running watcher holds the lock, so `--detail-sha` cannot
   run beside it. The check runs `describe_images.detail_one` on a scratch copy of the
   database, migrated to the new schema, with the real VLM and the shared `data/cache/`.
3. Rule 26: read `pipeline/schema/` and `ACTIVE_WORK.md`, send a message to each session
   with schema work, take the next free number.
4. A backup of `data/lab.sqlite3`, then the migration with `pipeline/labdb.py`.
5. The restart of 8168 with SIGTERM (rules 22 to 24), with `/opt/homebrew/bin/python3`
   (it has `jsonschema`). The restart also deploys the uncommitted code of the other
   sessions. Before the restart, this session sends a message to each active session
   with uncommitted hunks in the files of the server, and tells the owner.
6. The lab server starts the new watcher, and the backlog starts. Start
   `caffeinate -ims -w <watcher pid>`. Update the watcher row of
   `/Users/ashmelev/Admin/GPU_TASKS.md`.
7. Read the log and the first rows of `image_detail`.

## Result on 2026-09-25

- Schema file `020_image_detail.sql` entered at 22:00 (rule 26 notices to cb [48de03] and
  5c [cbb143] at 21:55). `data/lab.sqlite3` at version 20; `PRAGMA foreign_key_check`
  answered no row. Backup: `data/backups/lab-before-020-20260925T220038.sqlite3`.
- 8168 was down at 21:56 (the log ends at 20:37; not stopped by this session). Started
  at 22:00:54 with `/opt/homebrew/bin/python3` (server pid 59883). 5c agreed that its
  uncommitted server code goes live with it.
- The watcher (pid 59886, `caffeinate` pid 60168) started the backlog at 22:00:53. After
  3 minutes: 11 of 2,015 done, 0 failed, about 13 s for each new `bottle` cut, 77 s for the
  back label. The 4 answers of the live check came from the cache.
- The full suite: 634 tests `OK`. The pill on the live page read
  `VLM details 11 / 2,015 · 16.7 s` (headless Chrome).

## Time

- The probe: 15.7 s for one bottle cut, 60 to 80 s for one dense back label.
- About 2,015 images at about 16 s give about 9 hours. This is an estimate from one
  request. A larger source image sends more image tokens at 1,536 pixels.

## Risks

- The 9B model misreads small text. The probe misread «ИГРИСТОЕ ВИНО» on a cut of 353 ×
  1,136 pixels. The detail is not a verified transcription.
- The model changes key names with `json_object` alone (3 of 4 package answers). The
  request sends the schema, and the code check catches the rest: 3 failures stop the
  image. The count of failed images shows in red on the pill.
- drink-atlas-workspace-cb [48de03] changes the label cut rule now and runs
  `seed_label_cuts.py` again. Only the `label_closeup` images use a label cut (2 images),
  so the stale rule sends at most 2 images again.
- A restart of 8168 deploys the uncommitted code of other sessions (step 4 of the
  deployment).

## Answered questions

- Q1. Does this plan add a read-only block `Details` to the dialog `Image description` of
  `/dataset` now? Answer: "Later (Recommended)". The answers stay in
  `image_detail.answer`; a view is a later request.
- Q2 (after the live check of 20:45). How does stage 2 handle the key drift of the
  package prompt? Answer: "JSON Schema in request (Recommended)". The other options were
  a normalization in the code and no change.

## Files

- New: `pipeline/schema/NNN_image_detail.sql`, `pipeline/image_details.py`,
  `tests/test_image_details.py`.
- Hunks: `pipeline/describe_images.py` (the prompts, the schema, stage 2 of `run`,
  `--detail-sha`, the settings), `pipeline/image_descriptions.py` (`watcher_status`),
  `pipeline/pages/dataset.html` (`vlmStatusView`, `renderVlmStatus`),
  `tests/test_describe_images.py` (new tests at the end),
  `tests/image_description_fixture.py` (the cut rows), `tests/test_labdb.py` (the
  version and the table list), `config.yaml` (three keys).
- Data: `data/lab.sqlite3` (a backup first, then the migration), a restart of 8168,
  `work/describe_images.log`.
- Docs: `README.md`, `COMMANDS.md`, `SMOKE_TESTS.md`, `ChangeLog.md`, plan 26 (one
  note).
