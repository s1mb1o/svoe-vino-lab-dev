# Fake variants of the catalogue CSV

The files of this directory test `pipeline/import_catalog.py` on the full catalogue.
Each variant is the official file
`svoe-wino-hackaton/dataset/official-2026-09-17/strapi_output0709.csv` with a few
changes. The variants are test data. They are not a delivery of the organizers.

`make_catalog_variants.py` writes the three CSV files. It reads the official file and
never writes to it. A row that the script does not change keeps its exact bytes, so
`diff` against the official file shows only the changes.

```bash
python3 tests/data/make_catalog_variants.py
```

## The variants

| File | Change against the official file |
|---|---|
| `strapi_output0709.v2-add-remove.csv` | Removes 3 wines: `ivan-ksenia-kruz-argonne-syrah-sira-krasnoe-suhoe-124` (2 rows), `vinodelnya-myshako-quintessence-blaufrankish-rozovoe-bryut-115` (2 rows), `silvaner-pet-nat-2022` (1 row). Adds 2 fake wines: `fake-added-wine-1` (1 row), `fake-added-wine-2` (2 rows). |
| `strapi_output0709.v3-add-remove.csv` | The changes of v2, except that `ivan-ksenia-kruz-argonne-syrah-sira-krasnoe-suhoe-124` is back. Removes 2 more wines: `donskoe-vinodelcheskoe-hozyaystvo-elbuzd-merlo-krasnoe-suhoe-13` and `novyy-svet-…-novyy-svet-shardone-125`. Adds the fake wine `fake-added-wine-3` (2 rows). |
| `strapi_output0709.v4-changed-field.csv` | v3 with one changed field: `Регион` of `shato-pino-shary-kolduna-glyu-glyu-vione-krasnoe-suhoe-10` is `Крым`, not `Кубань`, in both rows of the wine. |

A fake wine copies the fields of
`vinodelnya-vedernikov-gubernatorskiy-rezerv-beloe-risling-suhoe-12`. Its name, its
producer, and its description start with `FAKE`.

## The expected import results

Start with a database that holds the official file and no other import. Import the
files in this order. The results were measured on 2026-09-24.

| # | File | added | restored | removed | states after the import |
|---|---|---|---|---|---|
| 1 | `strapi_output0709.v2-add-remove.csv` | 2 | 0 | 3 | Active 2102, Removed 3 |
| 2 | `strapi_output0709.v3-add-remove.csv` | 1 | 1 | 2 | Active 2102, Removed 4 |
| 3 | `strapi_output0709.v4-changed-field.csv` | error | — | — | no change: `region 'Кубань' -> 'Крым'` |
| 4 | the official file | 0 | 4 | 3 | Active 2103, Removed 3 (the fake wines) |
| 5 | the official file again | 0 | 0 | 0 | no change |
