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
```

The state of the watcher is in `work/describe_images.status.json`, and
`curl -s http://127.0.0.1:8168/api/image-description-status` answers the state with
the counts. The pill left of `Add wine` on `/dataset` shows the same.

One watcher runs at a time (`work/describe_images.lock`). `--sha` and `--once` stop with
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

Сделать прогон конфигурации `mock` (случайные top-k кандидаты для каждого фото
тестового набора; для проверки страницы `/runs`):
```bash
python3 pipeline/mock_run.py --set my --top-k 10 --seed 20260925
```
The run is in `runs/<stamp>-lab-mock-my/`. The Runs page of the lab server shows it
under the filter `Configuration` = `mock`. Without `--seed`, the script takes a random
seed and prints it.

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
