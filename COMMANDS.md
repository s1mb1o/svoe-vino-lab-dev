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
```
A second run of each command is safe. It prints `result: no change`.
`seed_images.py` prints one `no match: <slug>: …` line for each wine with no image.

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
