# Website synchronization

`scripts/sync_website.py` runs the same operation as optional Workbench startup.
The operation has four stages:

1. Fetch vino-svoe.ru. Apply safe updates with `import_website.py --automatic`.
2. Build each configured matcher embedding incrementally.
3. Build the clusters of each selected embedding. Keep saved cluster rules and notes.
4. Copy and validate a frozen catalogue. Publish the copy through a local symlink.

## Configuration

The `website_sync` mapping in `config.yaml` has these keys:

| Key | Meaning |
|---|---|
| `on_startup` | Start one background synchronization after Workbench starts. The default is `false`. The server can accept requests during the operation. |
| `matcher_embeddings` | The distinct embedding names to build and publish. Each name MUST exist in `embeddings`. Include both retrieval and group embeddings when the matcher uses a cascade. |
| `matcher_output` | The stable local publication symlink. A relative path starts at `rootdir`. The path MUST be outside the source catalogue. An existing directory is rejected. |

The shell command works when `on_startup` is `false`.
The command uses `embedding_python` for embedding and cluster builds.
The command passes the selected `--config` to the importer, image reviewer, and builds.
The importer uses the selected SAM3 endpoint and VLM settings for image checks.

The shipped configuration selects the p512 and p512-rot5 embeddings.
These embeddings serve the existing cascade catalogue format.
Change the list when another matcher needs other embeddings.

## Safe updates and manual choices

The importer protects `shmelev_shmeleva_risling` from missing-source removal.
The importer adds valid new wines.
An existing Main image needs the native crop, image quality, and independent identity checks.
The importer retains each replaced Main image as an additional photo.
Metadata conflicts, missing wines, uncertain images, and possible duplicate wines need a decision.
Synchronization does not choose an answer for these cases.

The run directory is `work/website-import/<run>/`.
It contains `diff.json`, image evidence, `run.log`, and `sync-result.json`.
The Website import page shows the run and the pending choices.
UI imports, shell synchronization, and startup synchronization share one process lock.
A second operation exits without starting another importer.
The shell exit code is `3` for a busy operation and `1` for another failure.
Exit code `0` permits pending manual choices. It confirms safe import and local publication.

## Publication

Each release is `work/website-import/<run>/matcher-catalog/`.
The release contains the database, selected vector files, indexes, and cluster files.
It contains no catalogue image copies.
The existing matcher reader validates each selected embedding.
Each applicable source view MUST have a current vector.
A missing, stale, failed, or duplicate vector prevents publication.
The frozen database and its vector coverage are checked together after the copy.

Only a valid release replaces `matcher_output`.
The replacement is atomic. The previous release stays on disk.
An import or build failure keeps the previous publication.
Safe catalogue changes that finished before a later build failure remain in Workbench.
The failure and its stage stay in `sync-result.json` and on the Website import page.
Stop sends SIGTERM to the active child process group and waits for the child to exit.
The operation releases its lock after the child exits.

This operation publishes local data. It does not deploy or restart a remote matcher.
A running matcher loads catalogue data at its start.
Use the deployment procedure for its target when a remote installation is required.

## Tests

The fixture tests use a temporary SQLite database and a local fake embedding server.
They do not call vino-svoe.ru or a model service.
They check startup configuration, custom configuration paths, process locks, cancellation,
stage order, manual choices, complete vector coverage, frozen snapshot validation,
cluster builds, and atomic publication.
Read `COMMANDS.md` for the test and synchronization commands.
