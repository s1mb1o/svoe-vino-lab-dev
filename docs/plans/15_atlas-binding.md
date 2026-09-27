# 15 — The Atlas Core product of a wine in the database

Date: 2026-09-25.
Status: the approach is chosen by the owner on 2026-09-25T10:30:50+0300. Implemented and
deployed on 2026-09-25 by drink-atlas-workspace-f1 as schema file `009_atlas_binding.sql`.
The seed added 364 automatic rows and 3 manual rows to `data/lab.sqlite3`.
The owner message of 2026-09-25T10:23:51+0300 ("enable support for Atlas Core product")
and the two answers are in [owner-messages.md](../owner-messages.md).

## Goal

1. The lab database holds the Drink Atlas Core product of each wine.
2. The editor `Atlas Core product` of the Dataset page works on the lab server.
3. A person can set a manual binding and can remove it.

## Present state

- The review tool `scripts/review_server.py` reads two JSONL files. The keys are
  `atlas_matches_file` and `atlas_bindings_file`. They are in `config.old.yaml` alone,
  not in `config.yaml`.
- `svoe-wino-hackaton/dataset/derived/official-2026-09-17/atlas-matches.jsonl` holds 364
  rows. `svoe-wino-hackaton/scripts/match_atlas.py` writes it. 37 rows use a product
  UUID that another slug also uses.
- `atlas-bindings.manual.jsonl` in the same folder holds 3 rows.
- Each row is `{"wine_slug": …, "product_uuid": …}`. No slug is in both files. Each of
  the 367 slugs is in `wine_catalog`. The check was made on 2026-09-25.
- The rule of the files: a manual row replaces the automatic row of the same slug.
- The review tool has `POST /api/dataset-atlas-binding` alone. It has no remove.
- The lab server sends empty file keys and count 0. The page disables the editor, and a
  write answers HTTP 503. Plan 07, rule 5, states this.

## Schema file

`pipeline/schema/009_atlas_binding.sql`. The number was taken at the entry on
2026-09-25 (rules 25 to 28 of `AGENTS.md`).

```sql
CREATE TABLE wine_atlas_binding (
    wine_slug    TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    source       TEXT NOT NULL CHECK (source IN ('automatic', 'manual')),
    product_uuid TEXT NOT NULL CHECK (length(product_uuid) = 36
        AND product_uuid NOT GLOB '*[^0-9a-f-]*'
        AND product_uuid GLOB '????????-????-????-????-????????????'),
    PRIMARY KEY (wine_slug, source)
) STRICT;
CREATE INDEX wine_atlas_binding_product ON wine_atlas_binding (product_uuid);
```

1. A wine has at most one row of each source.
2. The effective binding of a wine is its `manual` row. With no `manual` row, it is the
   `automatic` row.
3. One product MAY belong to more than one wine.
4. The stored UUID is the lower-case form with hyphens, as `str(uuid.UUID(text))` gives.

## Code

1. `pipeline/atlas_bindings.py`: the UUID check, the effective bindings of the wines, the
   set of a manual row, and the remove of a manual row.
2. `pipeline/seed_atlas_bindings.py --db data/lab.sqlite3 --matches <file> --manual <file>`
   reads both files. It checks every row before the first write. A bad UUID, or one slug
   with two UUIDs in one file, stops the seed with no write. A slug that is not in
   `wine_catalog` prints `no wine: <slug>`, and the seed skips it. The seed adds the
   missing rows in one transaction. It never changes or removes a row. A row of a file
   that differs from the stored row is counted as `differs` and is not applied. The seed
   refuses a table that already holds rows, unless `--force` is given (owner answer of
   2026-09-25T12:28:04+0300; plan 11, decision O3).
3. `pipeline/lab_server.py`:
   - `GET /api/dataset` gives each record `_atlas_product_uuid` and
     `_atlas_binding_source` (`manual`, `automatic`, or null). The answer gives
     `atlas_bindings` (the wines with an effective binding), `atlas_manual_bindings`, and
     `atlas_binding_editor: true`. The file keys stay empty.
   - `POST /api/dataset-atlas-binding` with `{"slug": …, "product_uuid": …}` sets the
     manual row. The answer is `{ok, slug, product_uuid, source: "manual", total,
     manual}`. The body and the answer keep the form of the review tool.
   - `DELETE /api/dataset-atlas-binding?slug=…` removes the manual row. The answer is
     `{ok, slug, removed, product_uuid, source, total, manual}`. `product_uuid` and
     `source` give the binding after the remove: the automatic row, or null.
   - An unknown slug answers HTTP 404. A bad UUID answers HTTP 400. A DELETE of a wine
     with no manual row answers HTTP 404.
4. `pipeline/pages/dataset.html`: the editor is on when the answer holds
   `atlas_bindings_file` (the review tool) or `atlas_binding_editor` (the lab). A manual
   binding on the lab gets a red `×` that removes it. A save and a remove redraw their
   own card alone.

## Consequences

1. The lab does not write the JSONL files. The review tool and `svoe-wino-hackaton` do
   not see a binding that a person sets on the lab. An export is not part of this plan.
2. A new run of `match_atlas.py` does not change a stored automatic row. The seed counts
   such a row as `differs`. How to apply a new run is an open point.

## Change of 2026-09-26: the remove of an automatic row

Source: the owner message of about 2026-09-26T18:40:00+0300 ("add (x) button to remove
wrong drink-atlas match") and the answers of about 18:45:00. Session
drink-atlas-workspace-f2.

1. `DELETE /api/dataset-atlas-binding?slug=…` removes the effective row: the manual row,
   else the automatic row. `atlas_bindings.remove_effective` replaces `remove_manual`.
2. The answer is `{ok, slug, removed, removed_source, product_uuid, source, total,
   manual}`. `removed_source` is `manual` or `automatic`.
3. A wine with no row answers HTTP 404: `the wine … has no Atlas binding`.
4. The Dataset page shows the red `×` for a binding of each source. The confirm text
   names the source. A wine with both rows needs two removes: the first removes the
   manual row and shows the automatic row.
5. The removed automatic row does not come back: the seed refuses a table with rows. A
   seed with `--force` adds it back. The owner chose the plain delete over a stored
   rejection.

## Change of 2026-09-26: two or more products of a wine

Schema 025 replaces the rules 1 and 2 of the section "Schema file" and the one-row routes.
A wine MAY have 2 or more products. Read [plan 54](54_atlas-binding-list.md).
