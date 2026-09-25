# 10 — The Embeddings page and the embedding build

Date: 2026-09-25.
Status: approved for implementation on 2026-09-25 (owner message 2026-09-25T00:51:21+0300,
"Implement embedding page in portal"). The open questions are answered.
The owner messages of 2026-09-25 in [owner-messages.md](../owner-messages.md) hold the
request and the answers. The gateway facts are in [ResearchLog.md](../../ResearchLog.md),
section "2026-09-25 — the SigLIP 2 models of the gx10 gateway".

## Goal

1. `config.yaml` holds a list of embeddings. Each embedding has a name, an endpoint,
   options, and steps.
2. A build prepares each input image, gets its vector, and writes files in
   `data/embeddings/<name>/`. The files are the only record of an embedding. The build
   does not write to the database.
3. A build does not make an image or a vector again when the embedding configuration
   and the source image are the same, and each prepared image exists.
4. A stopped or interrupted build continues on the next start. The finished items stay.
5. The Embeddings page of the lab server shows the prepared images of one embedding. A
   combobox selects the embedding.
6. A button starts a build as a separate process. A second button stops it. The process
   writes its progress to stdout. The page shows the progress. Builds of different
   embeddings can run at the same time.

## Decisions of the owner

| Question | Decision |
|---|---|
| The record of an embedding | Files alone: `data/embeddings/<name>/index.json`, the vectors, and `images/`. No database table. |
| The local model | `google/siglip2-so400m-patch16-naflex`. When NaFlex does not work on this Mac, a model that is not NaFlex. The local backend exists so that other people can run a build without gx10. |
| The Python of the local backend | A virtual environment `~/.venvs/svoe-vino-lab` from `requirements-local.txt`. |
| The inputs | Active wines alone. `main_patched` replaces `main`. |
| The processing of a full image | The variants A to F below. |
| The views of one entry | `full` uses C. `label` uses F. |
| B and E as a model input | An error, so that the owner sees what needs work. |
| Close-up images | `label_front` and `label_back` go to the view `label` as they are. |
| The label cut | At import, next to the package cut of plan 09. Outside this plan. |
| The type buttons of additional images | On the Dataset page. Outside this plan. |
| Upscale of small images | No, as the default. The step `resize` has an option for it. |
| Stop | A `Stop` button. |
| `GPU_TASKS.md` | No row for a build. A build starts at once. |
| The entries of `config.yaml` | Each image embedding model of gx10 on the screenshot of 2026-09-25. |

## Image roles and variants

A source image has one of two roles:

- `full`: the whole package with its label: a bottle, a can, a packet, a box. The image
  types `main`, `main_patched`, and the additional full images `full_front` and
  `full_back` (schema 012).
- `label`: a close-up of a label: `label_front` and `label_back`.

A full image has these variants:

| Variant | Steps | Result |
|---|---|---|
| A | `segment` (target `package`) | The original, cropped to the box of the smoothed and grown package mask. The background stays. |
| B | A + `remove_background` | A with the mask as its alpha channel: the processed file of plan 09. |
| C | B + `white_background` | B on white. RGB. |
| D | `segment` (target `label`) | The original, cropped to the box of the label mask. |
| E | D + `remove_background` | D with the label mask as its alpha channel. |
| F | E + `white_background` | E on white. RGB. |

A label close-up has no steps. It goes to the model as it is.

## Configuration

`config.yaml` gets two keys:

```yaml
embedding_python: ~/.venvs/svoe-vino-lab/bin/python

embeddings:
  - name: gx10-siglip2-so400m-patch16-naflex-p256
    backend: openai
    base_url: http://192.168.86.14:18081/v1
    model: siglip2-so400m-patch16-naflex
    extra_body:
      max_num_patches: 256
    views: &views_c_f
      full:
        steps:
          - step: segment
            target: package
          - step: remove_background
          - step: white_background
          - step: resize
            max_size: 1024
            aspect: keep
      label:
        steps:
          - step: segment
            target: label
          - step: remove_background
          - step: white_background
          - step: resize
            max_size: 1024
            aspect: keep
  - name: gx10-siglip2-so400m-patch16-naflex-p512
    backend: openai
    base_url: http://192.168.86.14:18081/v1
    model: siglip2-so400m-patch16-naflex
    extra_body:
      max_num_patches: 512
    views: *views_c_f
  # ... one entry for each model of the list below
```

The entries:

| Name | Backend | Model | `extra_body` |
|---|---|---|---|
| `gx10-siglip2-so400m-patch16-naflex-p256` | openai | `siglip2-so400m-patch16-naflex` | `max_num_patches: 256` |
| `gx10-siglip2-so400m-patch16-naflex-p512` | openai | `siglip2-so400m-patch16-naflex` | `max_num_patches: 512` |
| `gx10-siglip2-so400m-patch14-384` | openai | `siglip2-so400m-patch14-384` | none |
| `gx10-siglip2-so400m-patch16-256` | openai | `siglip2-so400m-patch16-256` | none |
| `gx10-siglip2-so400m-patch16-384` | openai | `siglip2-so400m-patch16-384` | none |
| `gx10-siglip2-so400m-patch16-512` | openai | `siglip2-so400m-patch16-512` | none |
| `gx10-naflexvit-so400m-patch16-siglip2-p256` | openai | `naflexvit_so400m_patch16_siglip.v2_webli` | `max_num_patches: 256` |
| `gx10-pe-core-l14-336` | openai | `PE-Core-L14-336` | none |
| `gx10-dinov3-vitb16` | openai | `dinov3-vitb16-pretrain-lvd1689m` | none |
| `gx10-dinov3-vitl16` | openai | `dinov3-vitl16-pretrain-lvd1689m` | none |
| `local-siglip2-so400m-patch16-naflex-p256` | local | `google/siglip2-so400m-patch16-naflex` | `max_num_patches: 256` |

The llama-swap folder "Image embeddings" also holds `wemm-embed-2b`, `wemm-embed-4b`,
and `wemm-embed-9b`. They are not on the screenshot, so they get no entry.

### Keys

| Key | Required | Meaning |
|---|---|---|
| `embedding_python` | no | The Python interpreter that the lab server uses to start a build. Default: the interpreter of the server. `~` is expanded. |
| `name` | yes | Unique. It MUST match `^[a-z0-9][a-z0-9._-]{0,99}$`. It names the directory and the URL. |
| `backend` | yes | `openai` or `local`. |
| `base_url` | for `openai` | The API base. The build sends `POST <base_url>/embeddings`. The llama-swap UI address `.../ui/#/models/<id>` is not an API base. |
| `model` | yes | For `openai`: the model ID of the gateway. For `local`: the Hugging Face repository. |
| `extra_body` | no | For `openai`: the build adds these keys to the JSON body of each request, as `extra_body` of the OpenAI client does. For `local`: the build gives these keys to the image processor. `local` accepts `max_num_patches` alone. |
| `batch_size` | no | Images in one request. Default 16. |
| `views` | yes | View name -> `steps`. The views are `full` and `label`. |

The build reads `config.yaml` at its start. The lab server reads `config.yaml` at each
request of the Embeddings API. So a new entry appears on the page with no restart of
the server.

### Steps

The steps of a view run in the listed order on one full image.

| Step | Options | Effect |
|---|---|---|
| `segment` | `target`: `package` or `label` (required) | `package`: the original, cropped to the box of `image_derivative` (plan 09). `label`: the original, cropped to the box of the label cut (a later plan). The step keeps the processed file for `remove_background`. |
| `remove_background` | none | The processed file of the target: the crop with the mask as its alpha channel. |
| `white_background` | none | An image with an alpha channel goes on white. The result is RGB. An RGB image does not change. |
| `resize` | `max_size` (required, 16 to 4096), `aspect` (`keep` or `ignore`, default `keep`), `upscale` (default `false`) | `keep`: the long side becomes `max_size`, and the aspect ratio stays. `ignore`: the image becomes `max_size` x `max_size`. With `upscale: false`, a smaller image does not change. The filter is Lanczos. |

The configuration check stops the build, and the page shows the error, for:

1. An unknown key, step, or option.
2. A view other than `full` and `label`.
3. A view with no step `segment` in the first position.
4. `remove_background` in a position other than directly after `segment`.
5. A step that is in one view more than one time.
6. `remove_background` with no `white_background` after it. The message:
   `the gateway drops the alpha channel; the model would see the hidden colours under
   the transparent pixels (variant B or E); add white_background`.
7. A `local` embedding with a key in `extra_body` other than `max_num_patches`.

### The transparency check of an item

The gateway drops the alpha channel. So the build checks each model input before it
sends it. An input with a transparent pixel is a failed item with the error
`the model input has transparent pixels; the gateway drops the alpha channel`.
Examples: variant A of an original with a transparent background, and a close-up with
an alpha channel. The page shows the error on the image.

### Open an image

The build opens a source with `derive.open_image`: EXIF orientation, then RGBA or RGB.
The box of `image_derivative` is in the pixels after the EXIF orientation.

## Inputs

1. Each wine with `state` = `Active`.
2. The full images of the wine: the card image (`main_patched` when the wine has one,
   otherwise `main`) and each additional full image.
3. The close-ups of the wine: each `label_front` and `label_back` image.
4. The items of the view `full`: one for each distinct full image.
5. The items of the view `label`: one for each distinct full image, and one for each
   distinct close-up.
6. A file that several wines share is one item. The page finds the wines through
   `wine_image.sha256`.

## The hash

```text
view_config_hash = sha256(canonical JSON of {backend, model, extra_body, view, steps, steps_version})
embedding_hash   = sha256(canonical JSON of {source_sha256, view, role, view_config_hash,
                                             derivative_sha256})
```

- Canonical JSON: sorted keys, no spaces, UTF-8. Each step holds its default options, so
  `aspect: keep` and no `aspect` give the same hash.
- `role` is `full` or `label`. A close-up in the view `label` has no steps, so its hash
  holds the role `label` and an empty list of steps.
- `steps_version` is a constant in the code. Raise it when the code of a step changes
  the pixels. Then each item is stale.
- `derivative_sha256` is the sha256 of the processed file that `segment` uses, or null.
  A new processed file makes the item stale.
- Not in the hash: `name`, `base_url`, `batch_size`. A move of the gateway to another
  host does not make an item stale.
- Not in the hash: the versions of `torch` and `transformers` of the local backend.
  `index.json` records them.

## Files

The directory is next to the database file, as `images/` is:

```text
data/embeddings/<name>/
  index.json                          the settings, the items, and the failures
  vectors-<8 hex>.npy                 float32, one row for each item, N x dim
  images/<source_sha256>_full.png     the prepared image of the view full
  images/<source_sha256>_label.png    the prepared image of the view label
  build.log                           stdout and stderr of the last build
  build.lock                          the PID of the running build
```

- The build sends the bytes of the prepared PNG as a PNG data URI. It does not send a
  JPEG. So the page shows the pixels that the model got.
- A close-up has no steps. The build writes it as it is, after its EXIF orientation, as
  `images/<source_sha256>_label.png`. So `images/` holds each model input, and the page
  has no special case.
- A file that is a full image of one wine and a close-up of another wine is a full image.
- `index.json`:

```json
{
  "name": "gx10-siglip2-so400m-patch16-naflex-p256",
  "config": {"backend": "openai", "base_url": "...", "model": "...", "extra_body": {}, "views": {}},
  "steps_version": 1,
  "view_config_hash": {"full": "<64 hex>", "label": "<64 hex>"},
  "dim": 1152,
  "vectors_file": "vectors-1a2b3c4d.npy",
  "updated_at": "2026-09-25T01:00:00+0300",
  "host": "Alexanders-MacBook-Pro-2023.local",
  "software": {"python": "3.14.0", "numpy": "2.4.4"},
  "items": [
    {"source_sha256": "<64 hex>", "view": "full", "role": "full",
     "embedding_hash": "<64 hex>", "derivative_sha256": "<64 hex or null>",
     "image": "images/<source_sha256>_full.png", "width": 412, "height": 1024, "row": 0}
  ],
  "failures": [
    {"source_sha256": "<64 hex>", "view": "label", "role": "full",
     "embedding_hash": "<64 hex>", "error": "no label cut yet"}
  ]
}
```

- A write of the vectors is atomic. The build writes a new `vectors-<8 hex>.npy`, then
  writes `index.json` through a temporary file and `os.replace`, then deletes the old
  vector file. A reader never sees an index that names a missing or a partial file.
- A prepared PNG is written through a temporary file and `os.replace` too.

## The build

```text
python pipeline/build_embeddings.py --name <name> [--config config.yaml]
```

1. The build reads and checks the configuration. It takes `build.lock` with an
   exclusive create. A lock with a live PID stops the build with exit code 3. A lock
   with a dead PID is removed.
2. The build computes `embedding_hash` for each item. It sorts each item:
   - `current`: `index.json` holds the item with the same hash, and its prepared image
     exists. The build does nothing for it.
   - `stale`: `index.json` holds the item with another hash, or its prepared image is
     missing.
   - `missing`: `index.json` does not hold the item.
   - An item in `failures` is `missing` again. So each build tries a failed item again.
3. For each `stale` and `missing` item: run the steps, write the PNG, get the vector.
4. An item that is not an input any more is removed from `index.json` and from the
   vectors. Its prepared image is deleted. Example: a wine became `Disabled`.
5. A checkpoint writes the vectors and `index.json`. The build makes a checkpoint every
   30 s, at the end, and at a stop. So a stopped build keeps its finished items, and
   the next start continues with the rest.
6. `openai`: one request holds `batch_size` images. The timeout is 300 s, because a cold
   start of a gateway model takes up to about 48 s. HTTP 429, HTTP 5xx, and a
   connection error make the build wait 2, 4, and 8 s and try again. After the third
   failure the items of the batch go to `failures`, and the build goes on.
7. `local`: the build loads the model from the Hugging Face cache with `transformers`.
   The device is `mps` when it is available, otherwise `cpu`. The dtype is float32.
8. Each vector is scaled to length 1. The dimension of all vectors MUST be the same.
9. A stale item keeps its old vector until the build replaces it.
10. SIGTERM and SIGINT stop the build after the present batch. The build makes a
    checkpoint, writes the line `stopped`, and exits with code 0.

### Progress on stdout

One JSON object per line. The build flushes each line.

```json
{"event": "start", "name": "...", "pid": 123, "items": 4036, "current": 0, "todo": 4036, "time": "..."}
{"event": "progress", "done": 160, "todo": 4036, "failed": 2, "time": "..."}
{"event": "item_failed", "source_sha256": "...", "view": "full", "error": "..."}
{"event": "request", "images": 16, "time": "..."}
{"event": "retry", "attempt": 1, "wait": 2, "error": "HTTP 503 from ...", "time": "..."}
{"event": "done", "built": 4034, "current": 0, "failed": 2, "pruned": 0, "seconds": 71.4}
{"event": "stopped", "built": 800, "failed": 0, "seconds": 20.1}
{"event": "error", "message": "..."}
```

| Exit code | Meaning |
|---|---|
| 0 | The build ended or stopped. Some items can be in `failures`. |
| 1 | A fatal error. The last line is `error`. |
| 2 | A configuration error. |
| 3 | Another build of the same embedding runs. |

## The lab server

The routes are in a new module `pipeline/embedding_routes.py`. `lab_server.py` passes
the routes below to it, and takes `/embedding` out of `DISABLED_PAGES`. The old routes
`/api/embedding` and `/img/embedding` stay HTTP 503.

1. `GET /embedding`: the page `pipeline/pages/embedding.html`.
2. `GET /api/embeddings`: each entry with its backend, model, `extra_body`, views,
   steps, the counts of each status, the job, and the configuration error, if any.
3. `GET /api/embeddings/<name>`: one record for each Active wine that has an input. The
   record holds the wine (slug, name, producer, category, region) and its columns: the
   card image, each additional full image, and each close-up. Each column holds the
   image type and the cells of the views `full` and `label`. A cell holds the status,
   the image URL, the width, the height, and the error.
4. `POST /api/embeddings/<name>/build`: starts the build. HTTP 202 with the job.
   HTTP 409 when a build of this embedding runs. HTTP 404 for an unknown name.
   HTTP 400 for a configuration error.
5. `POST /api/embeddings/<name>/stop`: sends SIGTERM to the PID of `build.lock`.
   HTTP 202. HTTP 409 when no build runs.
6. `GET /api/embedding-jobs`: the job of each entry: `running`, `stopping`, `done`,
   `stopped`, or `failed`, the PID, the start time, and the values of the last
   `progress` line.
7. `GET /embeddings/<name>/images/<sha256>_<view>.png`: one prepared image. A regular
   expression checks the path, as `/images/` does. The page adds `?v=<embedding_hash>`
   to the URL. So the server sends a long cache time, and a new image gets a new URL.
8. `GET /api/embeddings/<name>/log`: the text of `build.log` of the entry, as JSON
   `{"name", "file", "text"}`. HTTP 404 when no build wrote the file yet. Added on
   2026-09-25 (owner message of 11:42:50).

### Jobs

- The server starts the build with `embedding_python`:
  `<embedding_python> pipeline/build_embeddings.py --config <path> --name <name>`.
- stdout and stderr go to `build.log`. The process starts in a new session. So Ctrl+C
  of the server does not stop a build.
- The server reads the job state from `build.lock` and `build.log`. It keeps no job
  state in memory, except the process objects that it reaps. After a restart the page
  shows a running build again.
- A process that ends with no `done`, `stopped`, or `error` line is `failed`. The page
  shows the last line of `build.log` that is not JSON, for example the last line of a
  traceback.

## The page

The page follows the Embedding page of `svoe-vino-testset` (its `README.md`, section
"The Embedding page").

1. The navigation of `dataset.html`. The theme of `theme.css`: light and dark, after the
   system setting.
2. A combobox with each entry: `<name> — <current> / <items>`. The URL key `?name=`
   holds the selection. Its label is `Configuration`, because an entry holds more than
   the embedding model (owner messages of 2026-09-25T12:38:00+0300 and 12:41:00; plan
   23). The last entry `mock` has the backend `mock`: it builds as any entry, with random
   unit vectors of 256 values and no request (owner answer of 13:41:00).
3. A summary: backend, model, `extra_body`, the steps of each view, and the counts.
4. The buttons `Build` and `Stop`. `Build` is disabled while a build of this entry runs.
   `Stop` is enabled while it runs.
5. A job panel: one row for each running build of each entry, with a progress bar,
   `done / todo`, `failed`, and the time since the start. The page asks
   `/api/embedding-jobs` every 2 s while a build runs. At the end of a build of the
   selected entry, the page reads the wines again.
6. One row for each wine. The left column identifies the wine. The right side is a
   matrix. The first column is the card image: the prepared `full` image above, and the
   prepared `label` image below. Each next column is one additional image. A close-up
   column shows its image in the `label` row alone.
7. Each image cell has a checkerboard background. A cell shows the status badge
   `current`, `stale`, `missing`, or `failed`. A `failed` cell shows its error. A
   missing prepared image is shown as missing. It is not replaced with another image.
   A click opens the image in a new tab. Since 2026-09-25 (owner message of 11:59:27),
   a click opens the preview of item 10; a click with a modifier key opens the new tab.
8. A filter: all wines, wines with a failed cell, with a missing cell, with a stale
   cell. A search field: name, producer, slug.
9. The button `Log` after `Stop` opens a dialog with `build.log` (route 8). Each JSON
   line shows as `time · event · fields`. A line that is not JSON shows as it is, in
   red. A checkbox hides the `item_failed` and `progress` lines; it is on at the start.
   Added on 2026-09-25 (owner message of 11:42:50, answer of 11:45:00).
10. A click on a prepared image opens the image preview of `/dataset`: the image, a
    title, the size, `open raw image` (the original), arrows, and thumbnails. The arrows
    step through the images of the same view of the filtered list. The thumbnails show
    each column of the wine: the original and each view, with its status. The URL key
    `preview=<sha256>_<view>` names the open preview. Added on 2026-09-25 (owner message
    of 11:59:27, answers of 12:02:31).
11. The job row shows the phase of a running build: `waiting for the model · <time>`
    when a model request takes 3 s or more, and `retry <n> in <s> s: <error>`. The build
    writes `request` before each model request and `retry` before each wait (see
    "Progress on stdout"). Added on 2026-09-25 (owner message of 13:37:14, answer
    "Phase text").

## The local backend

1. The first implementation step is a probe: 4 images with
   `google/siglip2-so400m-patch16-naflex` on `mps`. The probe compares the vectors with
   the vectors of the gateway for the same PNG files.
2. When the probe fails, the local entry uses `google/siglip2-so400m-patch14-384` with an
   empty `extra_body`. `svoe-vino-matcher` already runs this model on this Mac. The
   agent tells the owner the result.
   Result of 2026-09-25: the probe passed. The cos of the local and the gateway vectors
   is 0.990 to 0.999. The local entry stays NaFlex. `transformers` 5 needs
   `torchvision` for the image processor.
3. The imports of `torch` and `transformers` happen in the local backend alone. The
   `openai` backend and the lab server need no `torch`.
4. `requirements-local.txt` lists the packages of the build: `pyyaml`, `numpy`,
   `pillow`, `requests`, `torch`, `transformers`. The venv is
   `~/.venvs/svoe-vino-lab`.

## Work outside this plan

| Work | Owner decision | State on 2026-09-25 |
|---|---|---|
| The SAM3 label cut at import (D, E, F) | At import, next to the package cut of plan 09. | On 2026-09-25 by plan 22 (`22_label-cut.md`): the row of the kind `label` of `image_derivative` (schema 017), made by `pipeline/seed_label_cuts.py` with the label rule of plan 16. `read_inputs` reads it. The imports do not call the seed yet. |
| Additional images on the Dataset page, with the type buttons `front_full`, `front_label`, `back_full`, `back_label` | On the Dataset page. Default `front_full`. The buttons act as the Testset candidate buttons do. | Done on 2026-09-25 by plan 16 (`16_alternative-images.md`): schema file 010 renames the types; the server detects the kind and, by a barcode, the side (one of the four types); the buttons read `FF`, `LF`, `FB`, `LB`; schema file 012 puts the kind first in the names (`full_front`, `label_front`, `full_back`, `label_back`). |

## Files of the implementation

| File | Change |
|---|---|
| `pipeline/embeddings.py` | New: the configuration check, the inputs, the steps, the hash, the read of `index.json`, the item status. |
| `pipeline/build_embeddings.py` | New: the build CLI and the two backends. |
| `pipeline/embedding_routes.py` | New: the routes of the lab server. |
| `pipeline/pages/embedding.html` | New: the page. |
| `pipeline/lab_server.py` | A small hook: the routes go to `embedding_routes.py`. Agreed with drink-atlas-workspace-8b first. |
| `config.yaml` | The keys `embedding_python` and `embeddings`. |
| `requirements-local.txt` | New. |
| `tests/test_embeddings.py`, `tests/test_build_embeddings.py`, `tests/test_embedding_routes.py` | New. |
| `README.md`, `COMMANDS.md`, `ChangeLog.md`, `SMOKE_TESTS.md` | The new page and the new command. |

## Tests

1. `tests/test_embeddings.py`: each rule of the configuration check, the defaults of the
   steps in the hash, each step on small images (A, B, C; alpha on white; `keep`,
   `ignore`, `upscale`), the transparency check, the inputs, and the item status.
2. `tests/test_build_embeddings.py`: a fake gateway on a local port. A first build, a
   second build that does nothing, a stale item after a change of `extra_body`, a
   stopped build that continues, a failed batch and its retry, the removal of an item
   that is not an input, the lock, the atomic write, and the progress lines.
3. `tests/test_embedding_routes.py`: the page, the API routes, the image route and its
   path check, a build start and a stop with a fake build command, HTTP 409.
4. The tests never call gx10 and never load a real model.

## Risks

1. Disk: each entry holds up to two PNGs for each source file. Measured on 2026-09-25:
   397 MB for the 2,018 full images of one entry, about 200 KB for each PNG. With the
   label images, the estimate is about 0.8 GB for each entry and 9 GB for 11 entries.
   Many entries hold the same images: the steps are the same.
2. `max_size` 1024 and the model resize the image two times. The vectors differ a
   little from the vectors of one resize.
3. Two builds on two different gx10 models at the same time can make llama-swap unload
   one model to load the other. The agent does not know the llama-swap group settings.
4. The SigLIP 2 models were not measured for the alpha channel. Only
   `dinov3-vitb16-pretrain-lvd1689m` was measured. The transparency check applies to
   each backend.
