


Стереть базу данных:
```
cd svoe-vino-lab
rm data/catalog-2026-09-17/lab.sqlite3
```

Создать базу данных
```
python3 pipeline/labdb.py data/lab.sqlite3
```

Загрузить файлы из базы данных
```
python3 pipeline/import_catalog.py --db data/lab.sqlite3 \
    ../svoe-wino-hackaton/dataset/official-2026-09-17/strapi_output0709.csv

python3 pipeline/seed_images.py --db data/lab.sqlite3 \
    ../svoe-wino-hackaton/dataset/official-2026-09-17/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads
```



# Pапуск сервера и WebUI


```bash
python3 pipeline/lab_server.py
```

It opens http://127.0.0.1:8168/dataset in your browser, and Ctrl+C stops it.

Options:
- `--no-browser`: start without opening a tab.
- `--port 8170`: use a different port.
- `--config other.yaml`: use a different config file.

The start report should show `schema version: 3` and `wines: 2103 (Active 2103, Disabled 0, Removed 0)`. Port 8168 is free right now.

The "failed" notice was only the stuck `lsof` I stopped. Your question is still recorded in `docs/owner-messages.md`.