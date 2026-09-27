Стереть базу данных:
```
cd svoe-vino-lab
rm data/lab.sqlite3
```
The image files in `data/images/` stay. A new load uses them again.

Создать базу данных (или обновить её схему):
```
python3 pipeline/labdb.py data/lab.sqlite3
```

Загрузить данные в базу данных:
```
python3 pipeline/import_catalog.py --db data/lab.sqlite3 \
    ../svoe-wino-hackaton/dataset/official-2026-09-17/strapi_output0709.csv

python3 pipeline/seed_images.py --db data/lab.sqlite3 \
    ../svoe-wino-hackaton/dataset/official-2026-09-17/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads

python3 pipeline/seed_patched.py --db data/lab.sqlite3 \
    ../svoe-wino-hackaton/dataset/patched-official-2026-09-17

python3 pipeline/seed_codes.py --db data/lab.sqlite3 \
    ../svoe-vino-matcher/dataset/code-map.json

python3 pipeline/seed_atlas_bindings.py --db data/lab.sqlite3 \
    --matches ../svoe-wino-hackaton/dataset/derived/official-2026-09-17/atlas-matches.jsonl \
    --manual ../svoe-wino-hackaton/dataset/derived/official-2026-09-17/atlas-bindings.manual.jsonl
```
A second run of `import_catalog.py` and of `seed_images.py` is safe. It prints
`result: no change`. `seed_patched.py`, `seed_codes.py`, and `seed_atlas_bindings.py`
refuse a table that already holds rows, because a second run adds back what a person
removed on the page. Add `--force` to add the missing rows anyway.

Загрузить тестовые наборы `my`, `official-real-photos` и `vlmrerank-8b-failed` из
`svoe-vino-testset/dataset/`:
```
python3 pipeline/import_testsets.py --db data/lab.sqlite3
```
Each run makes the rows of each set equal to its JSON files again. A second run writes
no new image file. Since plan 24 the Testset page `/testset` writes the labels to the
database, and the database is the source. So the import refuses a set with a page edit.
Add `--force` to replace the page edits with the files.

Собрать базу данных заново из `svoe-vino-testset` и исходных файлов (заполнить пустую
лабораторию или вернуть её в состояние этих файлов после теста):
```
python3 pipeline/seed_from_testset.py --db data/lab.sqlite3
```
The old database goes to `data/backups/`. The data of the lab alone (states, comments,
favorites, manual wines, alternative photos, Testset page edits, image descriptions) are
in that backup only. The label cuts need SAM3 on gx10 for each image that
`data/cache/sam3/` does not hold. Read `docs/plans/28_seed-from-testset.md`.

Выгрузить тестовый набор из базы в JSON-файлы (`review-labels.json`, `excluded-slugs.json`):
```
python3 pipeline/export_testset.py --db data/lab.sqlite3 --set my --out <directory>
```
A file of the same name in `--out` is replaced. The export writes no photo file.

Сделать вырезку этикетки для каждого полного фото (вид `label` страницы Embeddings):
```
python3 pipeline/seed_label_cuts.py --db data/lab.sqlite3
```
The tool asks SAM3 on gx10 for each full original with no label cut, about 0.6 s for
each photo. A second run continues the first one. `--limit N` makes a short test run.
After the run, press `Build` on `/embedding` for each entry.
`seed_images.py` prints one `no match: <slug>: …` line for each wine with no image.

Обновить каталог с сайта vino-svoe.ru:
```
python3 pipeline/import_website.py --db data/lab.sqlite3
```
The tool reads the API of the website. It adds the new wines, removes the missing wines,
restores the wines that came back, and stores a missing main image. Each change gets a
short comment. A changed text or a changed main image stops the import, and nothing
changes. Fix each named wine by hand, then run the tool again. A run takes some minutes,
because it downloads the image of each wine. Read `docs/plans/18_import-website.md`.
The button `Import from website` of the Dataset page runs the same compare, and a dialog
lets you merge each conflict. Read `docs/plans/21_website-import-ui.md`.

# Запуск сервера и WebUI

```bash
python3 pipeline/lab_server.py
```

It opens http://127.0.0.1:8168/dataset in the browser. Ctrl+C stops it.

Options:
- `--no-browser`: start without a browser tab.
- `--port 8170`: use another port.
- `--config other.yaml`: use another config file.

The start report states the schema version and the wine count of each state.
After a change of the code in `pipeline/`, stop the server and start it again.
After a new file in `pipeline/schema/`, run `labdb.py` first.

# Описания изображений (plan 26)

With `image_description.watch: true` in `config.yaml`, the lab server starts the watcher
`pipeline/describe_images.py --watch` and stops it at its exit (SIGTERM or Ctrl+C). The
start report names the pid of the watcher. The log is `work/describe_images.log`.

```bash
tail -f work/describe_images.log                          # the watcher at work
python3 pipeline/describe_images.py --sha <sha256>         # one image, now
python3 pipeline/describe_images.py --once                 # one pass, then stop
python3 pipeline/describe_images.py --once --retry-failed  # the failed images again
sqlite3 data/lab.sqlite3 "SELECT created_by, vlm_at IS NOT NULL, count(*) \
    FROM image_description GROUP BY 1, 2"                  # the progress
python3 pipeline/describe_images.py --detail-sha <sha256>  # the detail of one image (plan 29)
sqlite3 data/lab.sqlite3 "SELECT prompt_kind, package_type, vlm_at IS NOT NULL, \
    count(*) FROM image_detail GROUP BY 1, 2, 3"           # the progress of the details
sqlite3 data/lab.sqlite3 "SELECT json(answer) FROM image_detail \
    WHERE sha256 = '<sha256>'"                             # one detail
python3 pipeline/describe_images.py --label-sha <sha256>   # the label description (plan 61)
sqlite3 data/lab.sqlite3 "SELECT created_by, count(DISTINCT sha256), count(*) \
    FROM image_label_description GROUP BY 1"               # the progress of stage 3
sqlite3 data/lab.sqlite3 "SELECT id, created_at, json(description) FROM \
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
The files are in `data/embeddings/<name>/`. The Embeddings page of the lab server
starts and stops a build too.

Build the clusters of one completed embedding entry:
```bash
~/.venvs/svoe-vino-lab/bin/python pipeline/build_clusters.py \
    --name gx10-siglip2-so400m-patch16-naflex-p256
```
The command writes `clusters.json` in `data/embeddings/<name>/`. The Clusters page can
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
The command writes `cluster-rules.json` in `data/embeddings/<name>/`. Stage 1 describes
each card, stage 2 writes the rule of each cluster. `--stage describe`, `--cluster
<slug>`, and `--force` limit or repeat the work. The settings come from the block
`label_rules` of `config.yaml`. A second run makes calls only for the work that changed.
Exit status 0: all records are valid; 1: a record holds an error; 2: the run did not
start or stopped, for example because the service refused the number of images.

Run a pipeline with the cluster re-rank (plan 48) on a test set. The key `rerank` names
the embedding directory of the rules. Use `embedding_python`, because the barcode twin
needs zxing-cpp:
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
photo. The answers stay in `data/cache/sam3/`, so a later run of the set, with any
pipeline, sends no SAM3 request. `siglip2-p256-as-is` sends no SAM3 request at all. An entry of the backend
`local` runs with `~/.venvs/svoe-vino-lab/bin/python`. A run of the set `my` from this Mac
needs `caffeinate -ims -w <pid>`. Read `docs/plans/33_embedding-run.md`.

# Кэш вызовов моделей

The SAM3, Grounding DINO, and VLM calls keep their answers in `data/cache/<model>/`.
Read `docs/plans/25_model-call-cache.md`.

One Grounding DINO call (the output states `"cache": "miss"` or `"hit"`):
```bash
python3 pipeline/gdino.py <image> --texts "wine bottle, label" [--model mm-gdino-base]
```

The records and the size of each model:
```bash
du -sh data/cache/*/ && find data/cache -name '*.json' | cut -d/ -f3 | sort | uniq -c
```

Send the requests of one model again (for example after a new checkpoint on gx10):
```bash
rm -r data/cache/sam3/
```


Импорт старой базы данных:

cd /Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace/svoe-vino-lab

# Rebuild the database and swap it in. Took about 8 min this time.
python3 pipeline/seed_from_testset.py --db data/lab.sqlite3 \
    2>&1 | tee work/seed/seed-$(date +%Y%m%dT%H%M%S).log

# Only if 8168 is not running: start it in its own terminal tab, then check it
python3 pipeline/lab_server.py --no-browser
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8168/api/dataset   # expect 200

# Back up the lab database to git as text (plan 50)

The skill `backup-lab-db` runs these steps, checks a round trip, and commits `db-export/`
alone through a private git index. Export `data/lab.sqlite3` into `db-export/`:
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
