# Plan 58: shared codes

Date: 2026-09-27.
Source: owner message of 2026-09-26T23:54:53+0300, answers of 23:59:00.
Session: drink-atlas-workspace-df [46e479].

## Problem

Two wines can have the same GTIN or the same QR URL in `wine_code`. Example:
`belmas-winery-viogner-katya-vione-beloe-suhoe-135` and
`belmas-winery-viognier-belmas-vione-beloe-suhoe-122` share the GTIN `04630171632036` and
the QR URL `https://belmaswinery.com/`.

The barcode step of plan 42 answers a hit with each wine of the code at score 1.0. For a
shared code, the order of the wines is the slug order. The order is not a result of the
photo.

## Terms

- A shared code is a GTIN or a QR URL of 2 or more Active wines.
- A unique code is a GTIN or a QR URL of 1 Active wine.
- The code wines are the Active wines of one code.

## Requirements

1. The Dataset page shows a badge at the right of a shared GTIN.
2. The Dataset page shows a badge at the right of a shared QR URL.
3. The badge shows the count of the code wines, for example `2 wines`. The tooltip of the
   badge lists the other code wines. A click on the badge does nothing.
4. The badge counts the Active wines of `DATA.records`, as the barcode lookup does.
5. The page computes the count. The server does not change. The count changes after each
   add or remove of a GTIN or a QR URL.
6. A unique code of a photo answers the photo with its wine at score 1.0. The embedding
   does not run. This is the fast exit of plan 42.
7. A shared GTIN of a photo, with no unique code, limits the embedding match to the code
   wines. `Catalogue.rank` scores the code wines alone. The answer holds the top-k code
   wines in embedding order.
8. A code wine that the limited match does not rank (no current vector) goes at the end of
   the answer. It keeps the keys of a code candidate and gets the score `None`.
9. A shared QR URL never decides the answer. With no other hit, the normal match runs.
   Reason (owner): the annotation can miss other wines with the same QR URL.
10. Priority in one photo: a unique code, then the first shared GTIN, then the normal match.
11. The scan stops at a unique code. A shared GTIN and a shared QR URL do not stop the
    tile scan, so a unique code in a tile is still found.
12. A limited candidate keeps the keys of the embedding. It has no key `code`. So the
    `/runs` popup and `/api/run-inputs` show the model inputs and the items.

## Trace

The step `barcode` keeps the keys `codes` and `hit`. `hit` is the code that decides the
answer, or None. New keys:

- `mode`: `answer` (a unique code; fast exit) or `limit` (a shared GTIN; limited match).
  No key when `hit` is None.
- `shared_qr`: the hits of the shared QR URLs that the step did not use. No key when there
  is none.

The popup of plan 41 (`run_steps.py`) shows `hit.slugs` as the list `the wines of the code`
when no candidate has the key `code`. The popup needs no change for requirement 7.

## Files

- `pipeline/barcode.py`: `CodeLookup.hits`, `CodeLookup.find` (the priority),
  `Decoder.scan` (the stop rule), `CodeFirst.ask` (the limit).
- `pipeline/embedding_run.py`: `Catalogue.rank` and `EmbeddingBackend.ask` take `only`.
- `pipeline/cluster_rerank.py`: `ClusterRerank.ask` passes `only` to the inner backend.
- `pipeline/pages/dataset.html`: `gtinEditor`, `qrUrlEditor`, one helper, one CSS rule.
- `tests/test_barcode.py`: the old tests of a hit with 2 wines change.
- `tests/test_barcode_shared.py` (new).

## Risks

- A photo with a shared GTIN runs the full tile scan, as a miss does. The decode takes
  longer for these photos.
- The fast exit gives score 1.0. A limited answer gives cosine scores. The runs of a
  pipeline before and after this change are not equal for the photos of shared codes.

## Result

Done on 2026-09-27 by drink-atlas-workspace-df [46e479].

- `CodeLookup.hits` gives each hit; `CodeLookup.find` applies the priority; `is_unique` and
  `shared_qr` are new helpers; `CodeFirst.limited` adds the code wines with no ranked
  vector at the end.
- `Catalogue.rank(..., only=None)` sets the best cosine of each other wine to `-inf` in
  each view, so the `search` steps and the `score` step see the code wines alone.
- `ClusterRerank.ask` calls `inner.ask(path)` when `only` is None, so an inner backend
  with no `only` keeps working.
- An error of the limited match stays an error. The step does not fall back to the fast
  exit.
- The Dataset page: `codeUsers`, `sharedCodeBadge`, `codePeers`; `renderCodeCard` renders
  the cards that show a badge and the cards of the peers; the state action calls
  `renderCodeCard`.
- Tests: `tests/test_barcode_shared.py` 15 OK, `tests/test_barcode.py` 28 OK (5 decoder
  tests need `embedding_python`), the full suite 968 OK. 22 Playwright checks on the live
  page (light, dark, 390 px, in-memory peer edits, no write request).
- One real photo (the Belmas 122 test photo with a drawn EAN-13 `4630171632036`):
  `barcode-siglip2-p256-crop` gives 122 (0.6993), then 135 (0.6928); trace `mode` is
  `limit`, and the step `score` counts 2 wines. The plain `siglip2-p256-crop` has
  neither Viognier in its top 5. So a filter of the normal top-k would lose both wines.
- No server restart: the pages and `run_job.py`/`recognize.py` are read from disk. A run
  that starts now uses the new barcode step.
