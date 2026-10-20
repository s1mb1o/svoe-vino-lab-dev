## Lab server dependencies

Run these commands from the Workbench root in an activated Python virtual environment.
Installation changes that environment. The lightweight server does not require model packages.

```sh
python -m pip install -r requirements-server.txt
```

This read-only check imports the server without starting a listener or opening the catalogue:

```sh
python -c "import sys; sys.path.insert(0, 'pipeline'); import lab_server"
```

`requirements-local.txt` includes these dependencies and adds local model packages.

Стереть базу данных:
```
cd svoe-vino-lab/workbench
rm data/catalog/catalog.sqlite3
```
The image files in `data/catalog/images/`, `data/catalog/cuts/`, and
`data/testsets/images/` stay. A new load uses them again.

Создать базу данных (или обновить её схему):
```
python3 pipeline/labdb.py data/catalog/catalog.sqlite3
```

Загрузить данные в базу данных:
```
python3 pipeline/import_catalog.py --db data/catalog/catalog.sqlite3 \
    ../../svoe-wino-hackaton/dataset/official-2026-09-17/strapi_output0709.csv

python3 pipeline/seed_images.py --db data/catalog/catalog.sqlite3 \
    ../../svoe-wino-hackaton/dataset/official-2026-09-17/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads

python3 pipeline/seed_patched.py --db data/catalog/catalog.sqlite3 \
    ../../svoe-wino-hackaton/dataset/patched-official-2026-09-17

python3 pipeline/seed_codes.py --db data/catalog/catalog.sqlite3 \
    ../../svoe-vino-matcher/dataset/code-map.json

python3 pipeline/seed_atlas_bindings.py --db data/catalog/catalog.sqlite3 \
    --matches ../../svoe-wino-hackaton/dataset/derived/official-2026-09-17/atlas-matches.jsonl \
    --manual ../../svoe-wino-hackaton/dataset/derived/official-2026-09-17/atlas-bindings.manual.jsonl
```
A second run of `import_catalog.py` and of `seed_images.py` is safe. It prints
`result: no change`. `seed_patched.py`, `seed_codes.py`, and `seed_atlas_bindings.py`
refuse a table that already holds rows, because a second run adds back what a person
removed on the page. Add `--force` to add the missing rows anyway.

Загрузить тестовые наборы `my`, `official-real-photos` и `vlmrerank-8b-failed` из
`svoe-vino-testset/dataset/`:
```
python3 pipeline/import_testsets.py --db data/catalog/catalog.sqlite3
```

Prepare and import the public competitor sets with separate scored and provisional
tiers:

```bash
~/.venvs/svoe-vino-lab/bin/python scripts/import_competitor_testsets.py \
  --repos-root /Volumes/T7_2TB/2026_LCT_Hackatons_10 \
  --research-root /Volumes/T7_2TB/Projects-T7_2TB/2026_LCT_Hackatons/10-Сканер_российских_вин \
  --db data/catalog/catalog.sqlite3 --out data/competitor-testsets
```

Run the requested pipeline on one imported set:

```bash
SAM3_ENDPOINT=http://192.168.86.14:18081/upstream/sam3 \
  ~/.venvs/svoe-vino-lab/bin/python pipeline/embedding_run.py \
  --name siglip2-p512-rot5-seg --set danya213411-scored --workers 4
```

Run the plan 91 comparison on the deduplicated common set.
Use the first command as the base.
Replace the name in the second command with any of the ten `competitor-*` names in
`config.yaml`.

```bash
SAM3_ENDPOINT=http://192.168.86.14:18081/upstream/sam3 \
  ~/.venvs/svoe-vino-lab/bin/python pipeline/embedding_run.py \
  --name siglip2-p512-rot5-seg --set competitors-scored-common --workers 4

SAM3_ENDPOINT=http://192.168.86.14:18081/upstream/sam3 \
  ~/.venvs/svoe-vino-lab/bin/python pipeline/embedding_run.py \
  --name competitor-qacen-reject --set competitors-scored-common --workers 4
```

Merge the imported competitor sets into the one flat set `competitors`, and remove them
from the database. The command changes `data/catalog/catalog.sqlite3` and first copies it
to `data/backups/`. It refuses when the set `competitors` exists. Use `--dry-run` to see
the counts with no write:

```bash
python3 scripts/merge_competitor_testsets.py --dry-run
python3 scripts/merge_competitor_testsets.py
```

After the merge, the database holds no `danya213411-scored` and no
`competitors-scored-common`. Run the importer again before the run commands above.

Install the optional OCR and SIFT runtimes before a competitor run:

```bash
uv pip install --python ~/.venvs/svoe-vino-lab/bin/python -r requirements-local.txt
```

Read `docs/testing/competitor-testsets.md` before a rebuild.
Each run makes the rows of each set equal to its JSON files again. A second run writes
no new image file. Since plan 24 the Testset page `/testset` writes the labels to the
database, and the database is the source. So the import refuses a set with a page edit.
Add `--force` to replace the page edits with the files.

Собрать базу данных заново из `svoe-vino-testset` и исходных файлов (заполнить пустую
лабораторию или вернуть её в состояние этих файлов после теста):
```
python3 pipeline/seed_from_testset.py --db data/catalog/catalog.sqlite3
```
The old database goes to `data/backups/`. The data of the lab alone (states, comments,
favorites, manual wines, alternative photos, Testset page edits, image descriptions) are
in that backup only. The label cuts need SAM3 on gx10 for each image that
`data/cache/models/sam3/` does not hold. Read `docs/plans/28_seed-from-testset.md`.

Выгрузить тестовый набор из базы в JSON-файлы (`review-labels.json`, `excluded-slugs.json`):
```
python3 pipeline/export_testset.py --db data/catalog/catalog.sqlite3 --set my --out <directory>
```
A file of the same name in `--out` is replaced. The export writes no photo file.

Сделать вырезку этикетки для каждого полного фото (вид `label` страницы Embeddings):
```
python3 pipeline/seed_label_cuts.py --db data/catalog/catalog.sqlite3
```
The tool asks SAM3 on gx10 for each full original with no label cut, about 0.6 s for
each photo. A second run continues the first one. `--limit N` makes a short test run.
After the run, press `Build` on `/embedding` for each entry.
`seed_images.py` prints one `no match: <slug>: …` line for each wine with no image.

Сгенерировать PNG с нейтральным тёмно-зелёным стеклом из `main`-картинок
активных вин:

```bash
python3 scripts/normalize_glass.py --db data/catalog/catalog.sqlite3 \
  --output work/glass-normalized
```

Команда только читает базу, не запускает SAM3 и не меняет хранилище. Она берёт
маску бутылки из производной `package`, защищает этикетку маской `label` и пишет
PNG по SHA-256 и `manifest.json` в каталог `--output`. Пример для одного вина с
листом «до / после»:

```bash
python3 scripts/normalize_glass.py --db data/catalog/catalog.sqlite3 \
  --output work/glass-normalized-demo \
  --slug denisov_rubin_klaret_krasnaya_strelka \
  --comparison work/glass-normalized-demo/comparison.png --overwrite
```

`--category Красное`, repeatable `--slug`, `--limit`, `--target-colour`,
`--strength` and `--label-margin` narrow or tune a run. Existing outputs stay unless the
command has `--overwrite`.

Обновить каталог с сайта vino-svoe.ru:
```
python3 pipeline/import_website.py --db data/catalog/catalog.sqlite3
```
The tool reads the API of the website. It adds the new wines, removes the missing wines,
restores the wines that came back, and stores a missing main image. Each change gets a
short comment. A changed text or a changed main image stops the import, and nothing
changes. Fix each named wine by hand, then run the tool again. A run takes some minutes,
because it downloads the image of each wine. Read `docs/plans/18_import-website.md`.
The button `Import from website` of the Dataset page runs the same compare, and a dialog
lets you merge each conflict. Read `docs/plans/21_website-import-ui.md`.
`COMPARE_ENABLED` in `pipeline/import_website.py` switches the compare. It is `True` since
2026-10-02. With `False`, the command exits 1 with
`error: the website compare is disabled in the code: …`, and the Dataset page shows no button.

# Запуск сервера и WebUI

```bash
python3 pipeline/lab_server.py
```

It opens http://127.0.0.1:8168/dataset in the browser. Ctrl+C stops it.

Options:
- `--no-browser`: start without a browser tab.
- `--port 8170`: use another port.
- `--config other.yaml`: use another config file.

Open the lab-server API documentation, or read the same checked-in OpenAPI 3.1
document as YAML or JSON:

```bash
open http://127.0.0.1:8168/docs
curl -sS http://127.0.0.1:8168/openapi.yaml | head
curl -sS http://127.0.0.1:8168/openapi.json | python3 -m json.tool | head
python3 tests/test_lab_openapi.py
```

The start report states the schema version and the wine count of each state.
After a change of the code in `pipeline/`, stop the server and start it again.
After a new file in `pipeline/schema/`, run `labdb.py` first.

Restart the server on port 8168 in the background (rules 22 to 24 of `CLAUDE.md`). The
restart loads the uncommitted server code of every session. `--dry-run` is read-only: it
shows the running server and runs the start check, and it stops nothing.

```bash
scripts/restart_lab_server.sh --dry-run
scripts/restart_lab_server.sh
```

The script stops the listener of port 8168 with SIGTERM and starts
`python3 pipeline/lab_server.py --no-browser` in its own session. The log goes to
`work/lab_server.log`. The script ends when `GET /api/dataset` answers HTTP 200. When no
server runs, the script only starts it. The script stops before it stops the server when
port 8168 belongs to another process, or when the server cannot start: a pending file in
`pipeline/schema/` (run `labdb.py` first) or a bad `config.yaml`.

Add one manual wine and activate it in the configured index:

```bash
python3 scripts/add_wine.py \
    --slug my-wine \
    --name "My Wine" \
    --producer "My Winery" \
    --beverage-type 4 \
    --category "Красное" \
    --color "Рубиновый" \
    --region "Кубань" \
    --grapes "Каберне Совиньон" \
    --description "Dry red wine." \
    --image /absolute/path/to/my-wine.webp
```

`new_wine_embedding` in `config.yaml` selects the index. The index MUST already have an
active `index.json` and vector file. `--embedding <name>` replaces the selected name for
one command. The command creates the wine only after the preflight succeeds. It reuses
current vectors, builds the new items, verifies them in the active index, and prints one
JSON result. Exit status 0 means that the index is active. Exit status 1 means that the
wine exists but the index activation failed. Retry that index on `/embedding`. Exit
status 2 means that the preflight or the wine input failed and no wine was created. Read
`docs/plans/78_incremental-new-wine-index.md`.

The `Add wine` dialog of the Dataset page does not wait for the index: a background job of
the lab server updates it (plan 84). Read the job of one new wine and run the tests. These
commands change nothing:

```bash
curl -sS "http://127.0.0.1:8168/api/wine-index?slug=__my-wine" | python3 -m json.tool
python3 -m unittest discover -s tests -p 'test_new_wine_jobs.py'
python3 -m unittest discover -s tests -p 'test_new_wine_workflow.py'
```

Start the index job of one Active wine again, as the button `Retry` of its card does. The
command starts an incremental build of `new_wine_embedding`:

```bash
curl -sS -X POST http://127.0.0.1:8168/api/wine-index \
    -H 'Content-Type: application/json' -d '{"slug": "__my-wine"}'
```

Read `docs/plans/84_background-new-wine-index.md`.

## New from Atlas and photo moves (plan 95)

Run the tests and read the photo selection of one Atlas product. The Atlas web UI must
answer on port 8157. These commands change nothing:

```bash
python3 -m unittest discover -s tests -p 'test_atlas_import.py'
python3 -m unittest discover -s tests -p 'test_photo_moves.py'
curl -sS "http://127.0.0.1:8168/api/atlas-import/photos?url=$(python3 -c 'import urllib.parse; print(urllib.parse.quote("http://127.0.0.1:8157/products/a3b3d69b-71e5-4f38-9a76-411c6203c873", safe=""))')" | python3 -m json.tool
```

Send the missing Atlas requests of one product, as `Prepare` of the dialog does. This
command calls an external service: it queues Atlas enrichment tasks of the product. The
card button `load photos` sends no such request.

```bash
curl -sS -X POST http://127.0.0.1:8168/api/atlas-import/advance \
    -H 'Content-Type: application/json' \
    -d '{"url": "http://127.0.0.1:8157/products/a3b3d69b-71e5-4f38-9a76-411c6203c873"}' | python3 -m json.tool
```

Read `docs/plans/95_new-from-atlas.md`.

# Описания изображений (plan 26)

With `image_description.watch: true` in `config.yaml`, the lab server starts the watcher
`pipeline/describe_images.py --watch` and stops it at its exit (SIGTERM or Ctrl+C). The
start report names the pid of the watcher. The log is `work/describe_images.log`.

```bash
tail -f work/describe_images.log                          # the watcher at work
python3 pipeline/describe_images.py --sha <sha256>         # one image, now
python3 pipeline/describe_images.py --once                 # one pass, then stop
python3 pipeline/describe_images.py --once --retry-failed  # the failed images again
sqlite3 data/catalog/catalog.sqlite3 "SELECT created_by, vlm_at IS NOT NULL, count(*) \
    FROM image_description GROUP BY 1, 2"                  # the progress
python3 pipeline/describe_images.py --detail-sha <sha256>  # the detail of one image (plan 29)
sqlite3 data/catalog/catalog.sqlite3 "SELECT prompt_kind, package_type, vlm_at IS NOT NULL, \
    count(*) FROM image_detail GROUP BY 1, 2, 3"           # the progress of the details
sqlite3 data/catalog/catalog.sqlite3 "SELECT json(answer) FROM image_detail \
    WHERE sha256 = '<sha256>'"                             # one detail
python3 pipeline/describe_images.py --label-sha <sha256>   # the label description (plan 61)
sqlite3 data/catalog/catalog.sqlite3 "SELECT created_by, count(DISTINCT sha256), count(*) \
    FROM image_label_description GROUP BY 1"               # the progress of stage 3
sqlite3 data/catalog/catalog.sqlite3 "SELECT id, created_at, json(description) FROM \
    image_label_description WHERE sha256 = '<sha256>' \
    ORDER BY created_at DESC, id DESC"                     # the label descriptions of one image
```

Stage 3 (the label descriptions, plan 61) runs with `image_description.labels: true`, when
no image waits for a class or a detail. It sends the request of stage 1 of the cluster
rules; the keys `vlm`, `thinking`, `describe_side`, `describe_max_tokens`, and `timeout_s`
of the block `label_rules` set it. `--label-sha` skips an image that has a label
description. `--retry-failed` also gives the failed label descriptions new attempts.

Stage 2 (the details, plan 29) runs with `image_description.details: true`, when no image
waits for a class. `--retry-failed` also gives the failed details new attempts.

`image_description.workers` (8; plan 35) is the number of requests at the same time, also
for `--once`. The start line of the log names it: `start: watch, vlm …, workers 8, …`. A
change of the value needs a restart of 8168: the watcher reads `config.yaml` only at its
start, and the lab server starts the watcher. Ctrl+C in a `--once` run waits for the
requests that run.

The state of the watcher is in `work/describe_images.status.json`, and
`curl -s http://127.0.0.1:8168/api/image-description-status` answers the state with
the counts. The pill left of `Add wine` on `/dataset` shows the same.

One watcher runs at a time (`work/describe_images.lock`). `--sha`, `--detail-sha`, `--label-sha`, and `--once` stop with
an error while the watcher of the server runs. A run of many images from this Mac needs
`caffeinate -ims -w <pid of the watcher>`.

# Эмбеддинги

Create the venv of the build once:
```bash
python3 -m venv ~/.venvs/svoe-vino-lab
~/.venvs/svoe-vino-lab/bin/pip install -r requirements-local.txt
```

Build one entry of the key `embeddings` of `config.yaml`:
```bash
~/.venvs/svoe-vino-lab/bin/python pipeline/build_embeddings.py \
    --name gx10-siglip2-so400m-patch16-naflex-p256
```
Ctrl+C stops the build after the present batch. A second run continues it.
The files are in `data/catalog/embeddings/<name>/`. The Embeddings page of the lab server
starts and stops a build too.

Build an entry with `rotation_step` (plan 82). The option `--workers` builds 6 rotated
items at a time. Each item sends about `batch_size` images in one request. The command
calls the gx10 gateway:
```bash
~/.venvs/svoe-vino-lab/bin/python pipeline/build_embeddings.py \
    --name gx10-siglip2-so400m-patch16-naflex-p512-rot5 --workers 6
```

Read-only tests of the rotated embeddings, the bundle version 3, and the catalogue copy:
```bash
python3 -m unittest discover -s tests -p 'test_rotated_embeddings.py'
```

Fixed-512 5-degree reference experiment. Prerequisites: the embedding venv above,
catalogue cuts, and the configured GX10 model services. These commands write the
new index and its cluster rules. The embedding and rule builds call model services.
The rule builder also needs the credentials of the configured `label_rules` models.

```bash
caffeinate -i ~/.venvs/svoe-vino-lab/bin/python pipeline/build_embeddings.py \
    --name gx10-siglip2-so400m-patch16-512-rot5 --workers 6
python3 pipeline/build_clusters.py --name gx10-siglip2-so400m-patch16-512-rot5
python3 pipeline/build_label_rules.py --name gx10-siglip2-so400m-patch16-512-rot5
```

After those builds, run the new preset on `my`. Prerequisites: the model services,
the QR scanner at `QR_SCANNER_ENDPOINT`, and the `my` test set. This command writes
a run and calls the configured services. It uses the normal caches.

```bash
caffeinate -i ~/.venvs/svoe-vino-lab/bin/python pipeline/embedding_run.py \
    --name barcode-rerank-siglip2-512-rot5-seg --set my --workers 4
```

NaFlex p512 5-degree rerank. The entry `gx10-siglip2-so400m-patch16-naflex-p512-rot5`
has the rotated view `full` and the unrotated view `label`. A build after the rotated
build embeds only the label items. Prerequisites and effects are those of the fixed-512
commands above. The copy of `cluster-rules.json` from the p512 index is a cache seed:
the rule builder checks its input hashes and rebuilds only changed descriptions or
rules.

```bash
caffeinate -i ~/.venvs/svoe-vino-lab/bin/python pipeline/build_embeddings.py \
    --name gx10-siglip2-so400m-patch16-naflex-p512-rot5 --workers 3
python3 pipeline/build_clusters.py --name gx10-siglip2-so400m-patch16-naflex-p512-rot5
cp -n data/catalog/embeddings/gx10-siglip2-so400m-patch16-naflex-p512/cluster-rules.json \
    data/catalog/embeddings/gx10-siglip2-so400m-patch16-naflex-p512-rot5/
python3 pipeline/build_label_rules.py --name gx10-siglip2-so400m-patch16-naflex-p512-rot5
caffeinate -i ~/.venvs/svoe-vino-lab/bin/python pipeline/embedding_run.py \
    --name barcode-rerank-siglip2-p512-rot5-seg --set my --workers 4
```

Build the clusters of one completed embedding entry:
```bash
~/.venvs/svoe-vino-lab/bin/python pipeline/build_clusters.py \
    --name gx10-siglip2-so400m-patch16-naflex-p256
```
The command writes `clusters.json` in `data/catalog/embeddings/<name>/`. The Clusters page can
run the same build. The thresholds and the limits come from the block `clusters` of
`config.yaml`. The options `--full-threshold 0.9 --label-threshold 0.9` replace the
thresholds for one build. A build over a limit stops and keeps the old file.

Build the label rules of the clusters of the view `combined` (plan 45). First look at
the work, then make a GPU task row, then run:
```bash
python3 pipeline/build_label_rules.py --name gx10-siglip2-so400m-patch16-naflex-p256 --dry-run
caffeinate -ims python3 pipeline/build_label_rules.py \
    --name gx10-siglip2-so400m-patch16-naflex-p256 > work/label-rules-run.json 2> work/label-rules-run.log
```
The command writes `cluster-rules.json` in `data/catalog/embeddings/<name>/`. Stage 1 describes
each card, stage 2 writes the rule of each cluster. `--stage describe`, `--cluster
<slug>`, and `--force` limit or repeat the work. The settings come from the block
`label_rules` of `config.yaml`. A second run makes calls only for the work that changed.
Exit status 0: all records are valid; 1: a record holds an error; 2: the run did not
start or stopped, for example because the service refused the number of images.

Run a pipeline with the cluster re-rank (plan 48) on a test set. The key `rerank` names
the embedding directory of the rules. Use `embedding_python` for the embedding runtime.
For a `barcode-…` twin, `qr_scanner.endpoint` in `config.yaml` MUST resolve; the project
configuration reads `QR_SCANNER_ENDPOINT`:
```bash
~/.venvs/svoe-vino-lab/bin/python pipeline/embedding_run.py \
    --name rerank-siglip2-512-crop --set my --workers 4 --label bench48
```

Make a run of the official recognizer of vino-svoe.ru (the pipeline
`vino-svoe-search-by-photo`, backend `svoe-vino-ru`). Each photo of the test set goes to
the API as it is. First a probe of 3 photos, then the full set:
```bash
python3 pipeline/remote_run.py --name vino-svoe-search-by-photo --set my --limit 3 --label smoke
python3 pipeline/remote_run.py --name vino-svoe-search-by-photo --set my --workers 4
```
The run is in `runs/<stamp>-lab-vino-svoe-search-by-photo-my[-<label>]/`. The Runs page
shows it under the filter `Pipeline` = `vino-svoe-search-by-photo`. `--workers 4`
costs no latency; the default 8 of the entry is faster and raises the median latency by
about 35 percent (`ResearchLog.md`, 2026-09-17). Read
`docs/plans/31_remote-configuration.md`.

Make a run of the prod matcher API (plan 83). The three pipelines `matcher-eval-predict`
(`/v1/eval/predict`, Top-1 alone), `matcher-match-k20` (`/v1/match?k=20`), and
`matcher-group-match` (`/v1/group/match?k=5`) call `http://192.168.86.14:28000`. They use
no local embedding. Prerequisite: the prod matcher answers `GET /healthz`. Each photo
lands in the prod request archive. First a probe of 3 photos, then the full set:
```bash
curl -fsS http://192.168.86.14:28000/healthz
python3 pipeline/remote_run.py --name matcher-match-k20 --set my --limit 3 --label smoke
python3 pipeline/remote_run.py --name matcher-group-match --set my --limit 3 --label smoke
python3 pipeline/remote_run.py --name matcher-eval-predict --set my
```
A row of `matcher-group-match` holds the key `group`. The Runs page shows the photo with
the numbered bottles and the candidates of each bottle. Read
`docs/plans/83_matcher-api-pipelines.md`.

# Android device API

Install and start the Android debug APK first.
The debug server MUST answer on port 18088.
Use the phone Wi-Fi IPv4 address when the host can reach it:

```bash
curl -fsS http://<device-ip>:18088/healthz
python3 pipeline/remote_run.py --name android-device-eval-predict \
    --set my --device-ip <device-ip> --limit 10 --label device-smoke
python3 pipeline/remote_run.py --name android-device-match-k20 \
    --set my --device-ip <device-ip> --limit 10 --label device-smoke
```

Use ADB forwarding when the Wi-Fi network blocks incoming connections.
Set `ANDROID_SERIAL` when more than one device is connected:

```bash
adb -s "$ANDROID_SERIAL" forward tcp:18088 tcp:18088
curl -fsS http://127.0.0.1:18088/healthz
python3 pipeline/remote_run.py --name android-device-eval-predict \
    --set my --device-ip 127.0.0.1 --limit 10 --label device-smoke
python3 pipeline/remote_run.py --name android-device-match-k20 \
    --set my --device-ip 127.0.0.1 --limit 10 --label device-smoke
```

The New Run dialog shows the same `device IPv4` parameter for these two pipelines.
Read `docs/plans/86_android-device-http-evaluation.md`.

Make a run of a pipeline of the backend `embedding` on a test set. Its key `embedding`
names an entry of `embeddings:`, and that entry needs its index. Each photo gets the steps
of the key `views` of the pipeline, or else the steps of the entry, and its vectors rank
the catalogue vectors of the entry. First a probe of 3 photos, then the full set:
```bash
python3 pipeline/embedding_run.py --name siglip2-p256-crop \
    --set official-real-photos --limit 3 --label smoke
python3 pipeline/embedding_run.py --name siglip2-p256-crop --set official-real-photos
```
The run is in `runs/<stamp>-lab-<pipeline>-<set>[-<label>]/`. A view whose first step is
`segment` waits for SAM3 on gx10 in the first run of a set: one call for each target and
photo. The answers stay in `data/cache/models/sam3/`, so a later run of the set, with any
pipeline, sends no SAM3 request. `siglip2-p256` sends no SAM3 request at all. An entry of the backend
`local` runs with `~/.venvs/svoe-vino-lab/bin/python`. A run of the set `my` from this Mac
needs `caffeinate -ims -w <pid>`. Read `docs/plans/33_embedding-run.md`.

Run the three barcode and rerank presets with package background removal on `my`.
These commands call external model services and write run files and caches. The three
embedding indexes and their cluster rules MUST be present. The shell environment
MUST supply `QR_SCANNER_ENDPOINT`. The configured SAM3, SigLIP2, and VLM endpoints MUST
be available. Each command uses four workers and updates its embedding index first.
Run the commands one at a time:

```bash
caffeinate -ims python3 pipeline/run_job.py --name barcode-rerank-siglip2-512-seg --set my
caffeinate -ims python3 pipeline/run_job.py --name barcode-rerank-siglip2-p512-seg --set my
caffeinate -ims python3 pipeline/run_job.py --name barcode-rerank-siglip2-p1024-seg --set my
```

Make the self-test of one embedding: each dataset image is a query in the view `full` of
the index, and its truth is its own wine. The button `Selftest` of `/embedding` starts the
same work as a job. First a probe of 20 images, then all images:
```bash
python3 pipeline/selftest.py --embedding gx10-siglip2-so400m-patch16-512 --limit 20 \
    --label smoke
python3 pipeline/selftest.py --embedding gx10-siglip2-so400m-patch16-512
```
The run is in `runs/<stamp>-lab-selftest-<embedding>-dataset[-<label>]/`. The Runs page
shows it under the filter `Testset` = `dataset`. The default is 4 workers. Read
`docs/plans/67_embedding-selftest.md`.

## Matcher bundle

The builder reads `config.yaml`, `data/catalog/catalog.sqlite3`, and the selected embedding index.
The output path MUST not exist. This command writes a new bundle. It calls no external
service:
```bash
python3 scripts/build_matcher_bundle.py \
    --embedding gx10-dinov3-vitb16 \
    --out work/matcher-bundles/gx10-dinov3-vitb16
```

Copy the prepared images into the bundle when the matcher needs them:
```bash
python3 scripts/build_matcher_bundle.py \
    --embedding gx10-dinov3-vitb16 \
    --out work/matcher-bundles/gx10-dinov3-vitb16-with-images \
    --include-images
```

Validate an existing bundle. This command is read-only and does not need the lab
database or source embedding index:
```bash
python3 scripts/validate_matcher_bundle.py \
    work/matcher-bundles/gx10-dinov3-vitb16
```

Run the local unit tests. They use temporary data and do not call an external service:
```bash
python3 -m unittest discover -s tests -p 'test_matcher_bundle.py'
```

Read `docs/testing/matcher-bundle.md` for the bundle contents and failure checks.

## Matcher catalogue copy (plan 75)

The copy replaces the bundle: the matcher reads `catalog.sqlite3` (the views
`matcher_wine` and `matcher_wine_image`), `embeddings/<name>/index.json`, and its vector
file. The script reads `config.yaml` and `data/catalog/`. It refuses a running build and
an index with an item that is not current. The output path MUST not exist. This command
writes a new directory. It calls no external service:
```bash
python3 scripts/copy_catalog.py --out work/catalog-copy \
    --embedding gx10-siglip2-so400m-patch16-naflex-p512 --no-images
```

Without `--embedding`, the copy holds each embedding that has an index. Without
`--no-images`, it also holds `images/` and `cuts/` (hard links on the same volume). Send
a copy to a host; rsync sends the changed files alone:
```bash
rsync -a --delete work/catalog-copy/ <host>:<path>/
```

Run the local unit tests. They use temporary data and do not call an external service:
```bash
python3 -m unittest discover -s tests -p 'test_catalog_copy.py'
python3 -m unittest discover -s tests -p 'test_matcher_views.py'
```

## Static wine images (plan 06 of the repository)

Build one release from the lab database. The output path MUST not exist. This command writes
a new directory. It reads the database and the image store, and calls no external service:
```bash
python3 scripts/build_wine_images.py --db data/catalog/catalog.sqlite3 \
    --out work/wine-images/$(date -u +%Y%m%dT%H%M%SZ)
```

Check a release directory against a database. Read-only. Exit code 1 means a difference:
```bash
python3 scripts/check_wine_images.py --db data/catalog/catalog.sqlite3 \
    --release work/wine-images/<release>
```

Check the published release. It calls `https://chtozavino.ru`. `--catalog-update` accepts a
manifest wine that is not Active in the database; use it with the new matcher catalogue copy
before a catalogue update:
```bash
python3 scripts/check_wine_images.py --db data/catalog/catalog.sqlite3 \
    --url https://chtozavino.ru/img/wines/ --sample 50
python3 scripts/check_wine_images.py --db work/catalog-copy/catalog.sqlite3 \
    --url https://chtozavino.ru/img/wines/ --catalog-update
```

Run the local unit tests. They use temporary data and do not call an external service:
```bash
python3 -m unittest discover -s tests -p 'test_wine_images.py'
```

## Matcher backend cascade (plan 85)

The matcher pipeline `cascade-p512-rot5` needs a copy with both embeddings: the rotated
index for the photo search and the p512 index for the group route and the cluster rules.
This command writes a new directory. It calls no external service:
```bash
python3 scripts/copy_catalog.py --out work/catalog-copy-cascade --no-images \
    --embedding gx10-siglip2-so400m-patch16-naflex-p512-rot5 \
    --embedding gx10-siglip2-so400m-patch16-naflex-p512
```

Check that the ports of the matcher (codes, labels, cluster re-rank) give the results of
the lab code. The test uses no external service:
```bash
python3 -m unittest discover -s tests -p 'test_matcher_parity.py'
```

# Кэш вызовов моделей

The SAM3, Grounding DINO, and VLM calls keep their answers in `data/cache/models/<model>/`.
Read `docs/plans/25_model-call-cache.md`.

One Grounding DINO call (the output states `"cache": "miss"` or `"hit"`):
```bash
python3 pipeline/gdino.py <image> --texts "wine bottle, label" [--model mm-gdino-base]
```

The records and the size of each model:
```bash
du -sh data/cache/models/*/ && find data/cache/models -name '*.json' | cut -d/ -f4 | sort | uniq -c
```

Send the requests of one model again (for example after a new checkpoint on gx10):
```bash
rm -r data/cache/models/sam3/
```


Импорт старой базы данных:

cd /Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace/svoe-vino-lab

# Rebuild the database and swap it in. Took about 8 min this time.
python3 pipeline/seed_from_testset.py --db data/catalog/catalog.sqlite3 \
    2>&1 | tee work/seed/seed-$(date +%Y%m%dT%H%M%S).log

# Only if 8168 is not running: start it in its own terminal tab, then check it
python3 pipeline/lab_server.py --no-browser
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8168/api/dataset   # expect 200

# Back up the lab database to git as text (plan 50)

The skill `backup-lab-db` runs these steps, checks a round trip, and commits `db-export/`
alone through a private git index. Export `data/catalog/catalog.sqlite3` into `db-export/`:
```bash
python3 pipeline/db_export.py export
```

Restore the export into a new file. The restore never replaces a file:
```bash
python3 pipeline/db_export.py restore --from db-export \
    --db data/backups/lab-restored-$(date -u +%Y%m%dT%H%M%SZ).sqlite3
```

The history of the backups, and of the rows of one table:
```bash
git log --stat --format='%h %ad %s' --date=iso -- db-export
git log -p -- db-export/rows/wine_catalog.jsonl
```

# Smoke check of the GitHub runner (CT 111)

`scripts/runner_smoke.py` checks the gx10 endpoint variables of the self-hosted runner
`ct111-svoe-vino-lab-1`: the variables, the reachability, and one real call of each
service. The test cases are in `SMOKE_TESTS.md`, section "Runner smoke".

Unit tests. Read-only, no network:
```bash
python3 -m unittest discover -s tests -p 'test_runner_smoke.py'
```

The next commands call the gx10 services. They need `SIGLIP2_ENDPOINT`,
`GROUNDING_DINO_ENDPOINT`, `SAM3_ENDPOINT`, `VLM_ENDPOINT`, `VLM_MODEL`,
`SHIELDGEMMA_ENDPOINT`, and `QR_SCANNER_ENDPOINT`. `SIGLIP2_MODEL` is optional; the
default is `siglip2-so400m-patch16-naflex`. The default run calls only the models that
run now, and loads no model:
```bash
python3 scripts/runner_smoke.py
```

Load each model that does not run on gx10. `qwen3.5-9b-nvfp4` alone needs about 27 GB:
```bash
python3 scripts/runner_smoke.py --load-models
```

The same on the runner, through GitHub. Needs `gh` with access to
`s1mb1o/svoe-vino-lab-dev`:
```bash
gh workflow run runner-smoke.yml -R s1mb1o/svoe-vino-lab-dev
gh workflow run runner-smoke.yml -R s1mb1o/svoe-vino-lab-dev -f load_models=true
gh run list -R s1mb1o/svoe-vino-lab-dev -w runner-smoke.yml -L 3
```

# Android embedding indexes

Install the local DIS runtime once:

```bash
~/.venvs/svoe-vino-lab/bin/pip install -r requirements-local.txt
```

Build the three entries in this order. The endpoint in `config.yaml` MUST serve
`timm/vit_base_patch16_siglip_224.v2_webli` as
`vit_base_patch16_siglip_224.v2_webli` and MUST use float32.

```bash
~/.venvs/svoe-vino-lab/bin/python pipeline/build_embeddings.py \
    --name android-siglip2-base-224-sam3-white
~/.venvs/svoe-vino-lab/bin/python pipeline/build_embeddings.py \
    --name android-siglip2-base-224-dis-white
~/.venvs/svoe-vino-lab/bin/python pipeline/build_embeddings.py \
    --name android-siglip2-base-224-dis-white-rot5 --workers 6
```

The rot5 entry creates 72 reference vectors for each full image.
The build calls the remote embedding endpoint.
Check `/Users/ashmelev/Admin/GPU_TASKS.md` before this build.

# No-segmentation, DIS, and SAM3 model matrix

The complete command prepares the full-image path and calls the existing SAM3 cache and
the GX10 embedding gateway.
It does not change a catalogue index or the database.
It writes resumable artifacts under
`runs/segmentation-model-matrix-2026-09-29/`.
Check `/Users/ashmelev/Admin/GPU_TASKS.md` and the GX10 memory before a real run.

`SAM3_ENDPOINT` MUST use the canonical shared endpoint.
The six SigLIP2 entries of plan 79 MUST be present in `config.yaml`.

```bash
SAM3_ENDPOINT=http://192.168.86.14:18081/upstream/sam3 \
~/.venvs/svoe-vino-lab/bin/python scripts/segmentation_model_matrix.py \
    --phase all --batch-size 8
```

Run the offline scoring and verification again without a model call:

```bash
~/.venvs/svoe-vino-lab/bin/python scripts/segmentation_model_matrix.py --phase score
~/.venvs/svoe-vino-lab/bin/python scripts/segmentation_model_matrix.py --phase verify
```

Run the local unit tests.
They do not call a model service:

```bash
~/.venvs/svoe-vino-lab/bin/python -m unittest tests.test_segmentation_model_matrix
```

# Benchmark dataset rule (plan 87)

A run leaves out the photos of a wine outside the dataset: a `Removed` or a `Disabled`
wine, or a place that `wine_catalog` does not hold. An `Active` manual wine stays.

Read-only. Print the change for the saved lab runs:

```bash
python3 scripts/rescore_runs.py --dry-run
```

Changes data. Write `metrics.json` and `summary.md` of the saved lab runs again. The
first write keeps the old files as `*.before-dataset-rule.*`. Run it again after a wine
changes its state:

```bash
python3 scripts/rescore_runs.py
```

Run the tests of the rule:

```bash
python3 -m unittest discover -s tests -p 'test_benchmark.py'
```


## DINOv3 + ArcFace

Run each command from the Workbench root. The training command needs the packages
in `requirements-local.txt` and a built source DINOv3 index. Use new output names
for each run. Read `docs/arcface.md` for data selection and validation limits.

Read-only tests use temporary catalogue files and loopback fake servers. They need
no gateway or model weights:

```bash
~/.venvs/svoe-vino-lab/bin/python -m unittest discover -s tests -p test_arcface.py
```

Train a 512-dimensional projection on frozen ViT-L features. This command writes
a new local checkpoint, report, configuration, and catalogue index. It sends no
images to an external service. The source index stays available:

```bash
~/.venvs/svoe-vino-lab/bin/python pipeline/train_arcface.py \
  --name gx10-dinov3-vitl16 \
  --output-name gx10-dinov3-vitl16-arcface-new \
  --output-dir data/models/dinov3-vitl16-arcface-new \
  --dim 512 --epochs 30 --export-index
```

The completed 2026-10-06 artifact uses the configuration below. A recognition run
needs the existing DINOv3 and SAM3 endpoints. It sends query images to those services
and writes a new run. Before sending files, apply the timestamp rule in
`../internal/AGENTS.md`. This is an evaluation command, not part of local training:

```bash
SAM3_ENDPOINT=http://192.168.86.14:18081/upstream/sam3 \
  ~/.venvs/svoe-vino-lab/bin/python pipeline/embedding_run.py \
  --config data/models/dinov3-vitl16-arcface-20261006-v2/config.yaml \
  --name gx10-dinov3-vitl16-arcface-v2-crop --set official-test-2026-10-01
```

Update this ArcFace catalogue after new source images arrive. This command sends
new model inputs to the configured embedding endpoint. It writes new index rows:

```bash
~/.venvs/svoe-vino-lab/bin/python pipeline/build_embeddings.py \
  --config data/models/dinov3-vitl16-arcface-20261006-v2/config.yaml \
  --name gx10-dinov3-vitl16-arcface-v2
```

## Local visual and OCR comparisons

Read-only regression checks; run from the workbench root. Requires the lab Python
packages. The embedding tests bind temporary loopback HTTP fixtures. These checks
send no request to a configured model endpoint and change no catalogue or test set.

```sh
scripts/test_local_comparison.sh
```

For local weights, cache contracts, the 21 runnable presets and normal lab job usage,
read [local-comparison.md](docs/testing/local-comparison.md).

## Shared OCR wine term normalization

Run from `workbench` with the lab Python environment. These checks use local
fixtures and raw OCR caches; no real model or remote embedding calls are made.
The matching-detail tests bind temporary loopback fake services.

```sh
python3 -m unittest discover -s tests -p test_wine_terms.py -q
python3 -m unittest discover -s tests -p test_variant_attributes.py -q
python3 -m unittest discover -s tests -p test_main_label_match.py -q
python3 -m unittest discover -s tests -p test_competitor_steps.py -q
python3 -m unittest discover -s tests -p test_run_steps.py -q
```

Read-only normalization of a string, without OCR inference or cache changes:

```sh
PYTHONPATH=pipeline python3 -c 'import wine_terms; print(wine_terms.normalize("MYCKАТ Са8иньо бланк ПОЛYСЛАДК0Е"))'
```

Dictionary structure, provenance, confidence and historical behavior:
[docs/testing/wine-terms.md](docs/testing/wine-terms.md).


## YOLO26 label and field training research

Read [the isolated experiment protocol](../internal/victor-dravigny-rank6-20261007/yolo26-label-research/README.md) before downloading or training. The protocol separates field boxes, label masks, landmarks and the SAM3 comparison. Dataset downloads require a local Roboflow key; training writes only `work/label-yolo26/`.

Read-only preparation checks from the workbench root:

```sh
work/label-yolo26/venv/bin/python -m unittest discover -s ../internal/victor-dravigny-rank6-20261007/yolo26-label-research -p 'test_*.py' -v
```

## Cylindrical label rectification prototype

Run from the workbench root. The experiment uses copied inputs and cached masks.
It writes only its own experiment directory. It changes no pipeline or index.

```sh
work/label-yolo26/venv/bin/python ../internal/victor-dravigny-rank6-20261007/rectification-prototype-20261009/run_experiment.py
work/label-yolo26/venv/bin/python ../internal/victor-dravigny-rank6-20261007/rectification-prototype-20261009/validate.py
```

To repeat the local PaddleOCR comparison and rebuild the report:

```sh
work/label-yolo26/venv/bin/python ../internal/victor-dravigny-rank6-20261007/rectification-prototype-20261009/run_ocr.py
work/label-yolo26/venv/bin/python ../internal/victor-dravigny-rank6-20261007/rectification-prototype-20261009/write_report.py
```

Read [the comparison report](../internal/victor-dravigny-rank6-20261007/rectification-prototype-20261009/report.html) for the assumed camera geometry, radius alternatives, source provenance and OCR limits. The reusable `rectify.py` accepts a same-size label mask plus an optional full-photo bottle mask and crop box. A radius inferred from a bottle silhouette differs from a radius assumed from an angular prior.

## Wine term recovery experiment

These commands run from the workbench root. They require Python 3. They use the
standard library. No environment variable is required.

Read-only contract tests:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_wine_term*.py'
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_variant_attributes.py
```

Offline replay writes only a new result directory. The default input campaign and
raw OCR cache MUST exist. No model or service is required. Select a new output
directory for each code or input identity.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/replay_wine_term_recovery.py --output ../internal/ocr-recovery-20261009/reproduce
```

See [the recovery policy](docs/testing/wine-term-recovery.md) for input identities,
confidence and geometry requirements, metrics, and limitations.


## YOLO26 and SAM3 field benchmark

Run from the workbench root. Prerequisites: the isolated label-yolo26 environment,
the pinned public RF100 author export and protocol, and local SAM3 weights.
The current coordinator already owns this run. Do not start a second coordinator.
No Roboflow key is needed for this public author mirror.

Read-only progress and metric tests:

```sh
work/label-yolo26/venv/bin/python -m json.tool ../internal/victor-dravigny-rank6-20261007/yolo26-label-benchmark-20261009/progress.json
PYTHONDONTWRITEBYTECODE=1 work/label-yolo26/venv/bin/python -m unittest discover -s ../internal/victor-dravigny-rank6-20261007/yolo26-label-benchmark-20261009 -p 'test_*.py'
```

After training has completed, the evaluator writes only its benchmark outputs.
It refuses a YOLO test run without the training completion record. The SAM3 test
run requires the frozen SAM3 validation run first. No remote request is made.

```sh
work/label-yolo26/venv/bin/python ../internal/victor-dravigny-rank6-20261007/yolo26-label-benchmark-20261009/evaluate.py --model yolo26n --checkpoint work/label-yolo26/runs/rf100-fields-n-20261009/weights/best.pt --split test
work/label-yolo26/venv/bin/python ../internal/victor-dravigny-rank6-20261007/yolo26-label-benchmark-20261009/evaluate.py --model yolo26s --checkpoint work/label-yolo26/runs/rf100-fields-s-20261009/weights/best.pt --split test
work/label-yolo26/venv/bin/python ../internal/victor-dravigny-rank6-20261007/yolo26-label-benchmark-20261009/evaluate.py --model sam3 --checkpoint work/label-yolo26/sam3-hf-local-20261009/facebook--sam3 --split val
work/label-yolo26/venv/bin/python ../internal/victor-dravigny-rank6-20261007/yolo26-label-benchmark-20261009/evaluate.py --model sam3 --checkpoint work/label-yolo26/sam3-hf-local-20261009/facebook--sam3 --split test
```

See the live local report in
`../internal/victor-dravigny-rank6-20261007/yolo26-label-benchmark-20261009/report.html`.
Whole-label masks, role classes, ordered landmarks, text transcripts and wine
identities require their own annotations. Field-box AP does not measure them.


## Laya-V cluster rerank

Read-only component checks require `~/.venvs/svoe-vino-lab`. Run from the Workbench root:

```sh
~/.venvs/svoe-vino-lab/bin/python -m unittest discover -s tests -p test_vlm_config.py -q
~/.venvs/svoe-vino-lab/bin/python -m unittest discover -s tests -p test_laya_v.py -q
```

The run command calls external model services and writes run and cache files.
The configured index rebuild can update catalogue vectors.
The gateway MUST have Laya-V, SAM3, SigLIP2 NaFlex, and the QR scanner ready.
Submitted input files MUST have timestamps earlier than 2026-09-29 at 23:59:00.
Set `QR_SCANNER_ENDPOINT` before the run:

```sh
QR_SCANNER_ENDPOINT=http://192.168.86.14:18081/upstream/qr-scanner \
  ~/.venvs/svoe-vino-lab/bin/python pipeline/run_job.py \
  --name barcode-rerank_laya_v-siglip2-p512-rot5-seg \
  --set official-test-2026-10-01 --workers 4
```

Read `docs/laya-v-rerank.md` for the typed answer contract and staged benchmark method.

## PaddleOCR + multilingual Laya reranking

Read-only adapter checks use fake services and temporary caches:

```sh
python3 -m unittest discover -s tests -p 'test_laya*.py'
```

The named preset requires the installed `work/main-label-paddle` CPU environment and
both local OCR model directories. Set `QR_SCANNER_ENDPOINT` to the configured scanner
URL. The Laya text, SAM3, SigLIP2 and barcode services must be available. This command
calls those services, writes caches and a new run, and follows the normal configured
embedding rebuild policy:

```sh
python3 pipeline/run_job.py --name barcode-rerank_paddle_laya-siglip2-p512-rot5-seg \
  --set official-test-2026-10-01 --workers 4 --config config.yaml
```

The frozen comparison driver and staged inputs are documented in
`docs/laya-v-rerank.md`; its evidence is under
`../internal/laya-v-rerank-20261009/paddle-laya/`.

## Label colour prompt comparison

Run the isolated test from the repository root:

```bash
python3 internal/colour-prompts-20261011/probe.py descriptions
python3 internal/colour-prompts-20261011/probe.py rules
python3 internal/colour-prompts-20261011/probe.py queries
python3 internal/colour-prompts-20261011/probe.py retries
python3 internal/colour-prompts-20261011/probe.py generated
SAM3_ENDPOINT=http://192.168.86.14:18081/upstream/sam3 \
  python3 internal/colour-prompts-20261011/probe.py cropped
python3 internal/colour-prompts-20261011/probe.py summary
```

The test reads the catalogue database. The test writes isolated artifacts.
The test sends images to the configured description and rule services.
The saved rule test uses the seven-image payload approved on 2026-10-11.
A completed phase skips existing records.
Read [the protocol and results](docs/testing/label-colour-prompts.md).

Run the focused unit suites from `workbench/`:

```bash
python3 -m unittest discover -s tests -p test_label_rules.py
python3 -m unittest discover -s tests -p test_build_label_rules.py
python3 -m unittest discover -s tests -p test_cluster_rerank.py
python3 -m unittest discover -s tests -p test_matcher_parity.py
```

Run the native suite from the repository root:

```bash
python3 -m unittest discover -s matcher/tests -p test_option_score_rerank.py
```

A production rule rebuild writes `cluster-rules.json`.
Use `pipeline/build_label_rules.py --cluster <slug> --dry-run` to inspect a targeted rebuild.
This command needs `--name <embedding-name>`.
The dry run does not generate or replace a rule.

## Rule self-calibration prototype

Run the isolated phases from `workbench/`:

```bash
SAM3_ENDPOINT=http://192.168.86.14:18081/upstream/sam3 \
  python3 ../internal/rule-self-calibration-20261011/prototype.py prepare
python3 ../internal/rule-self-calibration-20261011/prototype.py calibrate
python3 ../internal/rule-self-calibration-20261011/prototype.py final
python3 ../internal/rule-self-calibration-20261011/prototype.py report
```

Run each phase only after the previous phase succeeds.
`prepare` writes isolated image derivatives and calls the shared SAM3 service.
`calibrate` calls the configured LAN recognizer and QwenCloud generator.
`final` calls the recognizer with five independent front photographs.
`report` reads saved results and verifies frozen inputs.
Do not generate a new revision after final recognition.
These commands preserve production catalogue rules and source photographs.
Completed recognition cases resume from their saved records.
Use a new artifact directory for a changed protocol or configuration.
The manifest rejects changed source files, code, configuration, or prepared inputs.

Run the offline safeguards from `workbench/`:

```bash
python3 -m unittest discover -s ../internal/rule-self-calibration-20261011 \
  -p test_prototype.py -v
```

Read [the protocol and results](docs/testing/rule-self-calibration.md).

Audit the saved completed experiment from `workbench/`:

```bash
python3 ../internal/rule-self-calibration-20261011/audit.py
```

The audit is read-only except for its `audit.json` report.
The audit checks both saved freeze records and the recorded preparation correction.
The audit makes no service request.

## Label-only benchmark

Read [the protocol](docs/testing/label-only-benchmark.md).
Use the project Python environment with Pillow and the Workbench dependencies.
Run from `workbench/`.

These checks make no service request:

```bash
python3 -m unittest discover -s ../internal/label-only-benchmark-20261011 -p 'test_*.py'
python3 ../internal/label-only-benchmark-20261011/audit.py
```

The following command calls only the configured resident LAN description model:

```bash
python3 ../internal/label-only-benchmark-20261011/benchmark.py describe
```

The next command sends the reviewed catalogue payload to QwenCloud.
The command requires explicit approval of that payload.
The command waits for the paired LAN descriptions.
It uses at most two Cloud requests at a time.
The command MAY run while the LAN description client runs.

```bash
python3 ../internal/label-only-benchmark-20261011/rules_job.py
```

After descriptions and rules are complete, the next command runs paired recognition.
Wait for the LAN description client to exit before this command.
The command can resume incomplete generation.
It requires the same approval if a Cloud rule is absent.

```bash
python3 ../internal/label-only-benchmark-20261011/benchmark.py run
python3 ../internal/label-only-benchmark-20261011/audit.py --complete
```


## Synthetic rule benchmark

Use the `svoe-vino-lab` Python environment.
Run each command from the Workbench root.
The evidence directory is frozen after preparation.
Do not edit its benchmark code or `SPEC.md` during an inference run.

Local safeguards do not call a model:

```sh
python ../internal/synthetic-rule-benchmark-20261011/test_benchmark.py
```

Prepare synthetic images or verify an existing manifest.
Preparation writes only the isolated evidence directory.
These commands do not call a model:

```sh
python ../internal/synthetic-rule-benchmark-20261011/benchmark.py prepare
python ../internal/synthetic-rule-benchmark-20261011/benchmark.py verify
```

The next command sends the seven approved real label references, metadata, and descriptions to configured QwenCloud `qwen3.8-max`.
It requires `QWENCLOUD_TOKEN_PLAN_API_KEY`.
Do not use this command for a broader unapproved payload.

```sh
python ../internal/synthetic-rule-benchmark-20261011/benchmark.py generate --suite real
```

The next command uses resident LAN Qwen3.5-9B for fictional descriptions and rules.
Read the GPU tracker and check the 20 GiB reserve first.
Do not load another model or restart a service.
Use one LAN request at a time:

```sh
python ../internal/synthetic-rule-benchmark-20261011/benchmark.py generate --suite controlled
```

The matching job waits until every rule record exists.
Then it evaluates both suites through the same resident LAN model.
It resumes saved cases without repeating completed requests:

```sh
python ../internal/synthetic-rule-benchmark-20261011/match_job.py
```

After all 435 cases finish, audit results and create the numbered failure report.
This command makes no model request:

```sh
python ../internal/synthetic-rule-benchmark-20261011/report.py
```

Read [synthetic-rule-benchmark.md](docs/testing/synthetic-rule-benchmark.md) for scope and interpretation.

Verify every numbered failure in the completed local report.
Use the bundled Node.js runtime with Playwright available.
Pass the absolute report path:

```sh
node ../internal/synthetic-rule-benchmark-20261011/qa-report.js /Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace/svoe-vino-lab/internal/synthetic-rule-benchmark-20261011/report.html
```


## Vintage matching tests

Prerequisites: the Workbench Python environment at `~/.venvs/svoe-vino-lab` with
Pillow and PyYAML. Run from the Workbench root.
These local tests use temporary databases and fake VLM responses.
They make no model or network request and do not change catalogue data.

```sh
~/.venvs/svoe-vino-lab/bin/python -m unittest discover -s tests -p test_vintage_matching.py
~/.venvs/svoe-vino-lab/bin/python -m unittest discover -s tests -p test_cluster_rerank.py
```

See [the test concept](docs/testing/vintage-matching.md).


## Original patch inspection tests

Run from the Workbench root.
Use the existing Workbench Python environment with Pillow, NumPy, PyYAML, and jsonschema.
The tests use temporary directories, mock workers, and isolated loopback servers.
The tests make no model-service request.

```sh
PYTHONPATH=pipeline:tests python3 -m unittest test_patch_inspection test_lab_openapi -q
```

Use `Inspect patches` in the Runs step popup for the local diagnostic.
Read [the experiment report](../../svoe-vino-lab-experiments/PATCH_PIPELINE_REPORT.md).


## Bottle crop UI verification

Run from this Workbench root.
Use the existing server Python environment with jsonschema.
These checks use local fixtures and make no model-service request.

```sh
PYTHONPATH=pipeline:tests /opt/homebrew/bin/python3 -m unittest test_patch_inspection test_lab_pages test_run_steps -q
```

The `Inspect patches` worker uses the cropped 138-wine experiment gallery.
Candidate ranking uses cropped standard SigLIP2.
The overlays display the rejected experimental weights.
The panel displays source and crop dimensions for both bottles.
Read [the current report](../../svoe-vino-lab-experiments/PATCH_PIPELINE_REPORT.md).


## Exact pixel-padding crop viewer

Run from this Workbench root with the existing server Python environment.
These checks use local fixtures and make no model-service request.

```sh
PYTHONPATH=pipeline:tests /opt/homebrew/bin/python3 -m unittest test_patch_inspection test_lab_pages test_run_steps -q
```

The viewer uses `cropped/padding-tight/index-tuned` in the experiment evidence.
Pixel-padding crops have zero margin.
Bottle-mask crops retain the detector margin.

## Full-gallery patch comparison

These commands use the installed SigLIP2 checkpoint and local mask files.
The commands write local experiment evidence.
The commands do not send model-service requests.
Calibration writes a selection lock and rejects a second selection.
Validation MUST use the selection lock.

```sh
cd ../../svoe-vino-lab-experiments
~/.venvs/svoe-vino-lab/bin/python -m patch_pipeline.full_comparison --gallery internal/patch-retrieval-20261014/full-gallery --phase calibration
~/.venvs/svoe-vino-lab/bin/python -m patch_pipeline.full_comparison --gallery internal/patch-retrieval-20261014/full-gallery --phase validation
```

## Optional query bottle orientation experiment

Run from the workbench root. Use `~/.venvs/svoe-vino-lab/bin/python` with the Workbench dependencies. The optional integration is active as `siglip2-p512-rot5-seg-upright`. The default pipeline keeps selector v4. The helper CLI uses its isolated saved implementation.

Read-only validation. No model service is needed.

```bash
~/.venvs/svoe-vino-lab/bin/python ../internal/bottle-orientation-20261014/test_integration.py
```

Local preparation. This command writes only its output directory. It reads cached SAM3 masks and sends no model request. The query MUST have an alpha mask or a cached segmentation answer.

```bash
~/.venvs/svoe-vino-lab/bin/python ../internal/bottle-orientation-20261014/query.py \
  --image /absolute/query.png \
  --output ../internal/bottle-orientation-20261014/query-output \
  --prepare-only
```

Query embedding and retrieval. Omit `--prepare-only` from the preceding command. This sends one image to the configured p512 embedding service and reads the existing gallery. Add `--allow-segmentation` only to allow a missing SAM3 mask to be requested. The gallery is not rebuilt.

Paired retrieval benchmark. This command reads the frozen 256-photo manifest, reuses saved query vectors when present, and writes two new Runs entries. It can call the p512 service for absent vectors. It uses cached masks only and does not rebuild the gallery. Complete request latency is not measured.

```bash
~/.venvs/svoe-vino-lab/bin/python ../internal/bottle-orientation-20261014/benchmark_real.py
```

To run the optional pipeline on the current full test set through the standard runner:

```bash
~/.venvs/svoe-vino-lab/bin/python pipeline/embedding_run.py \
  --name siglip2-p512-rot5-seg-upright --set my
```

This standard run can request absent SAM3 masks and query embeddings. It writes a normal Runs result.


## Manual accepted answers: local tests

Prerequisites: Python with the Workbench dependencies.
The job tests need localhost sockets and process inspection.
The tests use temporary databases and a temporary HTTP server.
The tests do not modify the catalogue or call a model service.
Run these commands from the Workbench root.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=pipeline:scripts:tests python3 -m unittest test_manual_accepted_answers test_benchmark test_run_jobs -q
ruff check pipeline/benchmark.py tests/test_manual_accepted_answers.py
```

Read [the test concept](docs/testing/manual-accepted-answers.md).


## Testset Duplicate: local integration tests

Prerequisites: Python with the Workbench dependencies.
The tests need localhost sockets.
The tests use temporary databases and localhost HTTP servers.
The tests do not modify the live catalogue or call a model service.
Run these commands from the Workbench root.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=pipeline:scripts:tests python3 -m unittest test_testset_duplicate test_testset_routes test_lab_openapi test_lab_pages -q
ruff check pipeline/testset_duplicate.py pipeline/testset_routes.py tests/test_testset_duplicate.py
```

Read [the test concept](docs/testing/testset-duplicate.md).


## Testset transfer: local integration tests

Prerequisites: Python with the Workbench dependencies and Node.js for UI behavior tests.
The HTTP tests need localhost sockets.
The tests use temporary databases and localhost HTTP servers.
The tests do not modify the live catalogue or call a model service.
Run these commands from the Workbench root.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=pipeline:scripts:tests python3 -m unittest test_testset_transfer test_testset_transfer_ui test_testset_routes test_lab_openapi test_lab_pages -q
ruff check pipeline/testset_transfer.py pipeline/testset_routes.py tests/test_testset_transfer.py tests/test_testset_transfer_ui.py
```

Read [the test concept](docs/testing/testset-transfer.md).


## Dataset additional-image removal: local tests

Prerequisites: Python with the Workbench dependencies, Node.js, and `webui/node_modules/acorn`.
The UI tests run locally. The route tests need localhost sockets and use temporary databases.
The tests do not change the live catalogue or call a model service.
Run these commands from the Workbench root.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=pipeline:tests python3 -m unittest test_dataset_alternative_removal test_dataset_dom_rendering test_dataset_filter_cache test_alternatives.AlternativeRouteTest.test_remove_deletes_the_row_and_keeps_the_file test_alternatives.AlternativeRouteTest.test_bad_requests_are_refused -q
ruff check tests/test_dataset_alternative_removal.py
```

Read [the test concept](docs/testing/dataset-additional-removal.md).


## Wine vintages: local relation and cluster tests

Prerequisites: Python with the Workbench dependencies, Node.js, and `webui/node_modules/acorn`.
The HTTP tests need localhost sockets. Each test uses a temporary database.
The tests do not change the live catalogue or call a model service.
Run these commands from the Workbench root.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=pipeline:tests python3 -m unittest test_wine_vintages test_wine_vintage_routes test_wine_vintage_clusters test_wine_vintage_merge test_wine_vintage_ui test_similar_wines test_clusters test_wine_merge test_labdb test_dataset_dom_rendering test_dataset_filter_cache test_lab_openapi -q
ruff check pipeline/wine_vintages.py pipeline/lab_server.py pipeline/clusters.py pipeline/wine_merge.py tests/test_wine_vintages.py tests/test_wine_vintage_routes.py tests/test_wine_vintage_clusters.py tests/test_wine_vintage_merge.py tests/test_wine_vintage_ui.py
```

Read [the test concept](docs/testing/wine-vintages.md).


## Dataset metadata and image facts

Run from the Workbench root. Python needs the existing project dependencies.
Node.js is required for the UI behavior checks. Tests use temporary databases and
local test servers. They do not call a model or change the catalogue.

```bash
PYTHONPATH=pipeline:tests python3 -m unittest test_attribute_facts test_attribute_compare test_attribute_extract test_attribute_routes test_attribute_ui
```

The Dataset Actions menu can queue missing image facts, pause/resume the fact queue,
and cancel queued fact jobs. These actions change derived data and can call the
configured VLM. Re-extract on one card requests the current image input only.

Reuse existing image descriptions after the additive migration. This command writes
derived facts. It makes no inference request and preserves source metadata.

```bash
python3 pipeline/attribute_extract.py --db data/catalog/catalog.sqlite3
```


## Run case comparison

Read-only tests. Use Python with the Workbench dependencies and Node.js.
The HTTP tests create temporary databases and localhost servers.
The tests make no inference request and change no saved run.

```sh
PYTHONPATH=pipeline:scripts:tests python3 -m unittest test_run_compare test_run_compare_ui test_testset_from_compare test_testset_from_run test_testset_routes test_run_routes test_run_charts test_lab_openapi test_lab_pages
```

Read [the comparison test notes](docs/testing/run-comparison.md).

## Website import automation

Run from the Workbench root. Use the existing Python dependencies and Node.js.
These checks use temporary databases and fake services. They make no model request.

```sh
PYTHONPATH=pipeline:tests python3 -m unittest test_import_website test_website_import_routes test_website_image_review test_website_import_ui
```

Read [the automation policy](docs/testing/website-import-automation.md) before a real update.
The following command changes the catalogue and can call the configured SAM3/VLM services.
The run directory MUST contain a current prepared report for this database.

```sh
python3 pipeline/import_website.py --db data/catalog/catalog.sqlite3 --automate work/website-import/SELECTED_RUN
```


## Safe website synchronization and matcher data

Set `website_sync.on_startup: true` in `config.yaml` to start a background synchronization
when Workbench starts. The default is false. Configure `matcher_embeddings` and
`matcher_output` in that mapping. Read `docs/testing/website-sync.md`.

This read-only command validates the configuration and prints the planned stages:
```bash
python3 scripts/sync_website.py --dry-run
```

The following command calls vino-svoe.ru, SAM3, VLM, and the selected embedding services.
It writes safe catalogue updates and builds the selected indexes and clusters.
It publishes a checked local matcher catalogue. It keeps manual choices for the UI.
The selected services MUST be available. The command uses `embedding_python`.
```bash
python3 scripts/sync_website.py
```

Use another configuration with `--config /absolute/path/config.yaml`.
Progress and decisions appear at `/dataset/website-import`. The run directory holds
`run.log` and `sync-result.json`. A running remote matcher needs a separate deployment.

The tests use temporary data and a local fake server. They call no external service:
```bash
python3 -m unittest discover -s tests -p 'test_website_sync.py'
```

## MLflow experiment tracking

Read [the integration contract](docs/mlflow.md).
Run every command below from the Workbench root.

### Install the optional client

Use the Python environment that starts Workbench jobs.
This command installs packages.

```sh
python -m pip install -r ../matcher/requirements-mlflow.txt
```

### Export or retry a saved experiment

Set `MLFLOW_TRACKING_URI` to the existing tracking server URI.
Set `MLFLOW_EXPERIMENT_NAME` when the default `svoe-vino-lab` is not suitable.
Read credentials from the standard MLflow environment variables.
These commands write to MLflow and create `.mlflow/` state in the source directory.
Replace each placeholder path.

```sh
python ../matcher/mlflow_tracking.py runs/RUN_ID
python ../matcher/mlflow_tracking.py PATH_TO_MATCHER_EVALUATION --kind matcher
python ../matcher/mlflow_tracking.py PATH_TO_ARCFACE_OUTPUT --kind arcface
```

Set `MLFLOW_TRACKING_ENABLED=true` before starting the server to enable automatic benchmark export.
The explicit commands do not require that flag.

### Local tests

These tests use synthetic results. They do not call MLflow or run inference.
They write temporary test files.

```sh
python -m unittest discover -s tests -p 'test_mlflow_tracking.py' -v
python -m unittest discover -s tests -p 'test_benchmark.py' -v
```

Read `../matcher/docs/mlflow.md` for the opt-in real SQLite store test.
