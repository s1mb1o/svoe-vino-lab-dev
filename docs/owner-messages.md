# Messages of the project owner

The agents of this project record each message of the project owner in this file.
The rules are in [CLAUDE.md](../CLAUDE.md), section "Messages of the project owner".
The oldest message is first. The log starts on 2026-09-24.

## 2026-09-24T21:42:47+0300

```text
I removed from config.yaml all references to json files. Now sqlite is single oracle. 

temporary disable Clusters, Embeddings, Testset and Runs pages. Let's have only "Dataset" page working. Ensure that server capable to start and display contents of database. Do not remove anything in UI, we will add data later
```

## 2026-09-24T21:48:09+0300

```text
Question: How should the server read the database?
Answer: New lab server

Question: Port 8154 is registered to svoe-vino-testset, which runs a copy of the same server. Both cannot run at once. Which port should the lab server use?
Answer: Keep 8154 for now (Recommended)
```

## 2026-09-24T21:55:37+0300

```text
run lab_server on other port
```

## 2026-09-24T22:01:04+0300

```text
try to launch lab_server.py
```

## 2026-09-24T22:02:43+0300

```text
Question: config.yaml says `database_file: data/lab.sqlite3`. What should a relative path in config.yaml be relative to?
Answer: rootdir, as now

Question: You moved the database from data/catalog-2026-09-17/lab.sqlite3 to data/lab.sqlite3. Plan 07 rule 2 says one directory per delivery. Which layout is the rule now?
Answer: data/lab.sqlite3 (flat)
```

## 2026-09-24T22:03:07+0300

```text
git commit
```

## 2026-09-24T22:04:20+0300

```text
Question: Which of your own pending files should go into the commit? My changes go in anyway.
Answer: config.yaml
```

## 2026-09-24T22:09:52+0300

```text
create fake variants of ../svoe-wino-hackaton/dataset/official-2026-09-17/strapi_output0709.csv that adds and removes a few wine slugs. Put them to svoe-vino-lab/tests/data

then create python3 pipeline/import_catalog.py --db data/lab.sqlite3 \
    <TEST>.csv

add to wine_catalog new column: state = Active | Disabled | Removed

if wine_slug missing in new test csv, then change state to Removed
if wine_slug missing in database, add it.

If other field changed, then abort with error. I do not want implement handling change of wine properties, so if we got new csv where changed properties - just stop with error. 

We handle only add and remove of items.
```

## 2026-09-24T22:14:04+0300

```text
Question: A wine is `Removed` in the database, and a later CSV holds its wine_slug again with the same fields. What should the import do?
Answer: Set it Active again (Recommended)

Question: The import never sets `Disabled`. What happens to a Disabled wine?
Answer: Missing → Removed; present → stays Disabled (Recommended)

Question: import_catalog on an empty database adds every wine, which is what seed_catalog does. What should happen to seed_catalog.py?
Answer: import_catalog replaces it (Recommended)

Question: The table catalog_source holds one row: the file of the seed. After imports, how should the database record its CSV files?
Answer: remove this table completely
```

## 2026-09-24T22:27:45+0300

```text
how run lab_server?
```

## 2026-09-24T22:34:17+0300

````text
remove 
```
catalog.jsonl /Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace/svoe-vino-lab/data/lab.sqlite3, table wine_catalog
patch directory not configured
alternative directory not configured
barcode file not configured
automatic Atlas matches not configured
manual Atlas bindings not configured
```
````

## 2026-09-24T22:38:08+0300

```text
add buttons to "Ignore" and "Remove" to each item (below main image). Removed item get button "Restore". 
add filter that shows All (except Removed), Removed

Idea of Ignored button, that this slug is not used for embeddings and matches]
```

## 2026-09-24T22:41:27+0300

```text
Question: "Ignore" means: the wine is not used for embeddings and matches. The state for that is `Disabled` now. Which name should the database use?
Answer: Keep Disabled

Question: Which buttons does an ignored wine show?
Answer: Enable and Remove

Question: A person removes a wine that the CSV still holds. The next import holds it again. What should the import do?
Answer: Keep it Removed (Recommended)
```

## 2026-09-24T22:52:40+0300

```text
implement 

python3 pipeline/seed_images.py --db data/lab.sqlite3 \
    ../svoe-wino-hackaton/dataset/official-2026-09-17/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads

it shall match images and put them to svoe-vino-lab/data/images/main, store as <sha256>.<extension>

Look to svoe-wino-hackaton/scripts/build_catalog.py how matching wine_slug, name to ./svoe-wino-hackaton/dataset/official-2026-09-17/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads is done.
Do not download from net, if you fail to match image, just message to console and progress.


create new table to store images info

we need also store image type (main, main_patched, ...)
main - is main image at website vino-svoe.ru and provided to us in ../svoe-wino-hackaton/dataset/official-2026-09-17/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads
main_parched - fix of non-good main image. It always overrides main image.

there are also additional images used for training, they can be front, back, label_front, label_back
and images for testdataset

store main in @svoe-vino-lab/data/images/main , patches in @svoe-vino-lab/data/images/patched
add  @svoe-vino-lab/data/images/additional @svoe-vino-lab/data/images/testset

please, review above first.
```

## 2026-09-24T22:54:38+0300

```text
why switching "Ignore" / "Enable" takes so long time? 

also rename "Ignore" to "Disable"
```

## 2026-09-24T22:58:56+0300

```text
Questions of the agent:
1. Matching: A or B?
2. Table: one table or two tables?
3. `testset`: leave it for its own table later, or add it to this table now?
4. Add `data/images/` to `.gitignore`?

Answer:
1. A
Later I add loading from website

2. match_method - explain

what pros and cons of each?

3. main_patched - corect

4. yes, add
add whole data/ to gitinore
```

## 2026-09-24T23:01:54+0300

```text
Questions of the agent:
1. Table: one table (recommended) or two?
2. `match_method`: keep it or drop it?
3. `testset`: its own table in the later test-photo step (recommended), or into the image type list now?

Answer:
ok, one table
```

## 2026-09-24T23:02:03+0300

```text
match_method - keep
```

## 2026-09-24T23:02:03+0300

```text
yes, testset has own table
```

## 2026-09-24T23:02:03+0300

```text
and we can have a few testsets
```

## 2026-09-24T23:02:03+0300

```text
and we can have a few testsets with different set of images
```

## 2026-09-24T23:03:27+0300

```text
and we can have a few testsets with different set of images that linked to different wine_slugs (check type of matches from @svoe-vino-testset )
```

## 2026-09-24T23:05:39+0300

```text
no need to show "Colour: ..."
```

## 2026-09-24T23:07:02+0300

```text
put avtohtonnoe-vino-kryma-beloe-suhoe before title
```

## 2026-09-24T23:18:25+0300

```text
how import images?
```

## 2026-09-24T23:19:40+0300

```text
how import images
```

## 2026-09-24T23:20:44+0300

```text
http://127.0.0.1:8168/dataset why no catalog images shown ?
```

## 2026-09-24T23:22:32+0300

```text
pros and cons of each?
```

## 2026-09-24T23:22:56+0300

```text
git commit all
```
