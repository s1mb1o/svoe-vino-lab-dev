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
Disabled since 2026-09-29: `COMPARE_ENABLED = False` in `pipeline/import_website.py`. The
command exits 1 with `error: the website compare is disabled in the code: …`, and the
Dataset page shows no button.

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

Build the two entries in this order. The endpoint in `config.yaml` MUST serve
`timm/vit_base_patch16_siglip_224.v2_webli` as
`vit_base_patch16_siglip_224.v2_webli` and MUST use float32.

```bash
~/.venvs/svoe-vino-lab/bin/python pipeline/build_embeddings.py \
    --name android-siglip2-base-224-sam3-white
~/.venvs/svoe-vino-lab/bin/python pipeline/build_embeddings.py \
    --name android-siglip2-base-224-dis-white
```

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
