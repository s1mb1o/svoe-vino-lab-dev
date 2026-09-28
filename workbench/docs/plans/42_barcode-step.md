# Plan 42: the barcode step of the pipelines

Date: 2026-09-26

Source: owner message of 2026-09-26T07:22:10+0300, and the answers of 07:27:08
(session drink-atlas-workspace-1c [800d92]).

Transport amended on 2026-09-29 by the owner's request: the workbench no longer imports
`zxing-cpp`. Both this step and additional-image uploads use the shared HTTP scanner from
the top-level `qr_scanner` key of `config.yaml`.

## 1. Goal

Add a barcode step to the pipelines of `config.yaml`.

svoe-vino-testset does not decode a barcode itself. Its backend `svm-barcode-siglip2-448`
sends each photo to the pipeline `barcode-siglip2-448` of svoe-vino-matcher. The lab
originally copied that local decoder. Since 2026-09-29 it calls the shared `qr-scanner`
service instead.

## 2. The decisions of the owner

| Question | Answer |
|---|---|
| Where does the step go? | An optional key `barcode:` on a pipeline of the backend `embedding`. |
| Which code list does the lookup read? | The table `wine_code` of `data/lab.sqlite3`. |
| A code that belongs to more than one wine? | Each wine of the code, at score 1.0, in slug order. The embedding does not run. |
| Which new pipelines? | A barcode twin of each pipeline of the backend `embedding`: 22 entries. |

## 3. The key `barcode`

```yaml
- name: barcode-siglip2-p256-as-is
  backend: embedding
  embedding: gx10-siglip2-so400m-patch16-naflex-p256
  barcode:
    formats: [EAN13, Code128]
    code128_gtin_only: true
    qr: true
    tile_scan: false
    max_side: 1600
    upscale: true
  views: *as-is-views
```

| Option | Default | Meaning |
|---|---|---|
| `formats` | `[EAN13, EAN8, UPCA, Code128]` | The scanner-service formats of a product code. |
| `qr` | `true` | Read QR codes too. |
| `tile_scan` | `true` | Legacy experimental mode: send overlapping tiles after a whole-image miss. The project sets `false` to avoid up to 34 additional remote calls. |
| `max_side` | `1600` | Scale a photo with a longer side down to this side. |
| `upscale` | `false` | Scale a smaller photo up to `max_side`, with LANCZOS. |
| `code128_gtin_only` | `false` | Keep a Code 128 only when it holds a valid GTIN-13. |

`barcode: {}` takes each default. `pipeline/barcode.py` (`check_options`) checks the
options. `pipeline/pipelines.py` calls it.

The shared service is configured once:

```yaml
qr_scanner:
  endpoint: "{env:QR_SCANNER_ENDPOINT}"
  engine: zxing-cpp
```

`endpoint` also accepts a literal HTTP(S) URL. An unresolved environment reference is a
runtime scanner failure: the embedding still answers, and an additional-image upload
still stores the photo with a warning.

The 22 twins use the options of `barcode-siglip2-448` of svoe-vino-matcher. The YAML
anchor `barcode-options` holds them one time. Each twin is named `barcode-<pipeline>`. It
has the embedding and the views of its pipeline.

## 4. The run

`embedding_run.build_pipeline_backend` puts `barcode.CodeFirst` around the embedding
backend of a pipeline with the key `barcode`. `run_job.py` and `embedding_run.py` both
use this function. For each photo, `CodeFirst.ask` does these steps:

1. Open the photo with `derive.open_image` (the EXIF orientation is applied).
2. Put a transparent area on white. Scale the photo with `max_side` and `upscale`.
3. Send the whole prepared image to `POST <qr_scanner.endpoint>/scan` with the configured
   engine. The project uses `zxing-cpp` and `tile_scan: false`, so one uncached query
   makes one scanner request. This is the service path closest to the former local
   decoder; the service currently has zxing-cpp 3.0.0 rather than the former 2.3.0.
4. Normalize the returned format names and look up each decoded code.
5. A hit gives each wine of the code at score 1.0, in slug order, up to `top_k`. The
   embedding does not run.
6. A miss asks the embedding backend. Its answer does not change. Its latency gets the
   time of the decode.

The lookup reads `wine_code` of the Active wines one time, at the start of the run. A
decoded product code becomes its GTIN-14 with `codes.clean_gtin`. A QR text becomes its
normal URL with `codes.clean_qr_url`. A text that is not valid for its kind gives no
lookup. The lab has no kind `barcode` (owner decision of 2026-09-25), so a Code 128 that
is not a GTIN never gives a hit.

When `wine_code` holds no code of an Active wine, the step does not decode. This is the
rule of the matcher: a decode cannot change the answer.

A decoder error does not stop the photo. The trace records the error, and the embedding
answers.

## 5. The lookup and service rules

1. The lookup reads `wine_code`, not `code-map.json`.
2. The allowed formats have no `UPCE`: the compressed digits are not stored as a GTIN.
3. Decoder choice and image-level retries belong to `qr-scanner`, not the workbench.
4. A shared code gives each of its wines. The code map of the matcher refuses a shared
   code.
5. The step records no count of decoded photos. `run.json` is written from the spec at
   the start of the run.

## 6. The run files

- `run.json`, the key `backend`: the spec of the embedding backend, and the key `barcode`
  with the options, `engine: qr-scanner`, `scanner` (the resolved endpoint and selected
  service engine), and `codes` (the count of each kind of the lookup). `kind` stays
  `embedding`.
- A candidate of a hit holds `slug`, `score` 1.0, `rank`, `source` (`gtin` or `qr_url`),
  `code` (the stored value), `read` (the text as decoded), and `format`.
- The trace of plan 41: `CodeFirst.ask` returns five values. The first step is
  `barcode`:

```json
{"id": "barcode", "start_ms": 0.0, "ms": 812.4,
 "out": {"codes": [{"kind": "barcode", "format": "EAN13", "text": "4600682000181"}],
         "hit": null}}
```

  `hit` is null, or `{"source", "code", "read", "format", "slugs"}`. The step holds
  `error` when the decoder raised. `out.skipped` tells that no decode ran. On a hit the
  trace holds the step `barcode` alone. On a miss the steps of the embedding follow, and
  their `start_ms` gets the time of the decode. Session f4 [b39b7b] agreed to this form
  and shows the step in `pipeline/run_steps.py`.
- `/api/run-inputs` of a photo that the code lookup answered: no input, and one note.
  `run_routes.py` gives the candidates of the row to `embedding_run.model_inputs`.
- `/api/run-candidate` of a candidate of the code lookup: no item, and one note
  (`embedding_run.candidate_items`).

## 7. The client dependency

The workbench uses `requests`, already in `requirements-local.txt`. It does not install
or import `zxing-cpp`; that decoder and the other engines belong to the scanner service.

## 8. The tests

`tests/test_barcode.py`: the options, the key of `pipelines.py`, the 22 twins of the
project config, the lookup on a test database, `CodeFirst` with a fake decoder and a
fake embedding, the notes of a code answer, and a fake HTTP scanner. The focused tests
make no network request and need no local barcode-decoder package.

## 9. Result

See the section 2026-09-26 of [ChangeLog.md](../../ChangeLog.md).

## 10. Change of 2026-09-27

[Plan 58](58_shared-codes.md) (owner message of 2026-09-26T23:54:53+0300) changes the rule
of a hit. Only a code of one Active wine answers the photo. A GTIN of 2 or more wines limits
the embedding match to its wines. A QR URL of 2 or more wines decides nothing. The step
`barcode` of the trace gets the keys `mode` and `shared_qr`.
