# 78 — Incremental new-wine creation and index activation

Date: 2026-09-29.
Status: implemented and verified.

The owner selected the operator CLI workflow on 2026-09-29.
The owner also requested one CLI trial and one `lab_server.py` web-interface trial.
The messages are in [owner-messages.md](../owner-messages.md).

## Goal

1. One operation MUST create a manual wine and update one configured embedding index.
2. The operation MUST reuse current vectors.
3. The operation MUST build only missing, stale, or failed items.
4. The operation MUST verify that the active index contains the new wine image.
5. The CLI and `POST /api/wine` MUST use the same workflow.

## Configuration

1. The top-level key `new_wine_embedding` names one entry of `embeddings`.
2. The live configuration uses `gx10-siglip2-so400m-patch16-512`.
3. The CLI option `--embedding` MAY replace the configured name for one operation.
4. The operation MUST reject an unknown embedding before it creates the wine.
5. The operation MUST reject an embedding that has no active `index.json` and vector
   file before it creates the wine.
6. The operation MUST validate the active index before it creates the wine.

## Workflow

1. The preflight reads the configuration and the active index.
2. `manual_wines.add_wine` creates the catalogue row, the main image, and the available
   derivatives.
3. `rebuild_on_run.build` updates the selected embedding.
4. The existing embedding builder keeps current vectors.
5. The builder writes the new vector file before it replaces `index.json`.
6. The replacement of `index.json` is atomic.
7. The workflow reads the new active index and its vector file.
8. The workflow finds every applicable item of the new wine image.
9. Each applicable item MUST have the current `embedding_hash` and a valid vector row.
10. At least one applicable item MUST exist.
11. A successful answer includes the embedding name, state `active`, build counts,
    active-index SHA-256, vector file, and the item count for the wine.

## Failure behavior

1. A preflight failure MUST create no wine.
2. Product creation and model inference cannot use one transaction.
3. A build failure after product creation MUST keep the new wine.
4. A build failure after product creation MUST return state `failed` and a clear warning.
5. The CLI MUST use exit code 1 for this partial result.
6. The HTTP route MUST use HTTP 200 for this partial result because the wine exists.
7. The response MUST let the operator retry the index build from `/embedding`.

## CLI

The command is `python3 scripts/add_wine.py`.

The command accepts these required options:

- `--slug`
- `--name`
- `--producer`
- `--category`
- `--color`
- `--region`
- `--image`

The command accepts `--beverage-type` (`4` for wine or `44` for sparkling wine),
`--grapes`, `--description`, `--config`, and `--embedding`.
The command prints one JSON object.
The JSON object uses the same result contract as `POST /api/wine`.

## Web interface

[Plan 84](84_background-new-wine-index.md) replaces items 4 to 7 of this section. `Save`
answers when the wine is in the catalogue, and a background job updates the index.

1. The existing `Add wine` form stays the creation interface.
2. `GET /api/dataset` sends `new_wine_embedding`.
3. The dialog shows the embedding name.
4. The `Save` button creates the wine and waits for the incremental build.
5. The button text is `Creating and indexing…` while the request runs.
6. A successful card appears only after index verification.
7. A partial result also adds the card and shows the index warning.

## Tests

1. A preflight with an unknown embedding creates no wine.
2. A preflight with no active index creates no wine.
3. The workflow passes the selected name to the incremental builder.
4. A successful build verifies the new item and returns state `active`.
5. The test confirms that an old vector stays byte-identical in the activated index.
6. A failed build keeps the wine and returns state `failed`.
7. A completed build that omits the new item returns state `failed`.
8. The CLI reads the image and prints the result contract.
9. The HTTP route uses the workflow when `config_path` is present.
10. The legacy test server with no `config_path` keeps the create-only behavior.
11. The Dataset page shows the selected embedding and its busy text.
12. A live CLI trial creates a wine and verifies its active item.
13. A live browser trial creates a second wine and verifies its active item.

## Files

- `pipeline/new_wine_workflow.py`
- `scripts/add_wine.py`
- `pipeline/lab_server.py`
- `pipeline/pages/dataset.html`
- `tests/test_new_wine_workflow.py`
- `tests/test_manual_wines.py`
- `config.yaml`
- `COMMANDS.md`
- `README.md`
- `SMOKE_TESTS.md`
- `ChangeLog.md`

## Result

1. `pipeline/new_wine_workflow.py` implements one shared workflow for the CLI and the
   web route.
2. `scripts/add_wine.py` is the operator CLI.
3. The configured embedding is `gx10-siglip2-so400m-patch16-512`.
4. The focused suites passed 152 tests.
5. The live CLI trial created `__cli-index-smoke-20260929` and activated two items.
6. The live web trial created `__web-index-smoke-20260929` and activated two items.
7. All four active items were verified in `vectors-db0c3a7f.npy` at
   `2026-09-29T01:19:45+0300`.
8. The two smoke wines were then set to `Disabled`.
9. The cleanup build pruned four items and activated `vectors-02636f81.npy` with 4,641
   items at `2026-09-29T01:21:20+0300`.
10. Port 8168 runs the new code in managed session 79039. The server process is PID
    80244, and the image-description watcher is PID 80266.
