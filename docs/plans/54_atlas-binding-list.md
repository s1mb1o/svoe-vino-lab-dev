# 54 — Two or more Atlas Core products of a wine

Date: 2026-09-26.
Status: the approach is chosen by the owner at about 2026-09-26T21:58:00+0300. Session
drink-atlas-workspace-bc [2d545a]. Implemented and deployed on 2026-09-26: schema file
`025_atlas_binding_list.sql` entered at 22:25:01. The migration kept 363 automatic rows
and 5 manual rows of `data/lab.sqlite3`. 8168 restarted at 22:25:16.
The owner message ("there can be 2 and more drink-atlas uuids, add support") and the
three answers are in [owner-messages.md](../owner-messages.md).
This plan changes [plan 15](15_atlas-binding.md).

## Goal

1. A wine MAY have 2 or more Drink Atlas Core product UUIDs.
2. The Dataset page of the lab server shows each UUID of a wine. Each UUID has its own
   red `×`, `copy`, and `open`.
3. The `+` button adds one manual UUID. It does not replace a UUID.
4. The read-only match of plan 47 in `drink-atlas-matcher` reads all UUIDs of a wine.

## Present state

- Schema 009: the primary key of `wine_atlas_binding` is `(wine_slug, source)`. A wine
  has at most one `automatic` row and one `manual` row. The manual row replaces the
  automatic row.
- `data/lab.sqlite3` at version 24 holds 364 automatic rows and 5 manual rows. One wine,
  `vysokij-bereg-risling-zelenaya-seriya-1`, has a manual row and an automatic row with a
  different UUID. The check was made on 2026-09-26.
- `seed_atlas_bindings.py` refuses a file that gives one slug two UUIDs.
- `svoe_vino_match.py` keeps one UUID of each source. With more rows, the last row wins.

## Decisions of the owner

1. One list per wine. Each row keeps its source as a label. The rule "manual replaces
   automatic" goes away.
2. The migration keeps the present effective row of each wine: the manual row, else the
   automatic row. The one automatic row that a manual row hides now is dropped.
3. Scope: the lab code and the table read in `drink-atlas-matcher`. The old review tool
   `scripts/review_server.py` and its JSONL files do not change.
4. `GET /api/dataset` sends a list `_atlas_products` and drops `_atlas_product_uuid` and
   `_atlas_binding_source`. The page reads the list. With no list, the page reads the
   old single fields, so the review tool keeps working.

## Schema file

`pipeline/schema/025_atlas_binding_list.sql`. The number was taken at the entry on
2026-09-26 (rules 25 to 28 of `AGENTS.md`).

```sql
CREATE TABLE wine_atlas_binding_new (
    wine_slug    TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    source       TEXT NOT NULL CHECK (source IN ('automatic', 'manual')),
    product_uuid TEXT NOT NULL CHECK (<the check of schema 009>),
    PRIMARY KEY (wine_slug, product_uuid)
) STRICT;
-- Copy the effective row of each wine, in rowid order.
-- DROP the old table, RENAME the new table, CREATE the index on product_uuid again.
```

1. One wine has at most one row for one product UUID.
2. The column order stays `wine_slug, source, product_uuid`.
3. The rowid order is the order of the list on the page.

## Code

1. `pipeline/atlas_bindings.py`:
   - `bindings(conn, slug=None)` returns wine slug → a list of `(product UUID, source)`
     in rowid order.
   - `counts(conn)` returns (the rows, the manual rows).
   - `add_manual(conn, slug, product_uuid)` adds one manual row. A UUID that the wine
     already has raises `DuplicateError`.
   - `remove(conn, slug, product_uuid)` removes one row of either source. It returns the
     source of the removed row, or None.
   - `set_manual` and `remove_effective` go away.
2. `pipeline/seed_atlas_bindings.py`: a file MAY give one slug 2 or more UUIDs. A pair
   `(slug, UUID)` that the table holds with either source is not added. A pair in both
   files gets the source `manual`. The `differs` count goes away. The refusal of a table
   with rows stays.
3. `pipeline/lab_server.py`:
   - `GET /api/dataset`: each record gets `_atlas_products`, a list of
     `{"product_uuid", "source"}`. `atlas_bindings` is the count of rows.
     `atlas_manual_bindings` is the count of manual rows.
   - `POST /api/dataset-atlas-binding` with `{"slug", "product_uuid"}` adds one manual
     row. The answer is `{ok, slug, product_uuid, source: "manual", products, total,
     manual}`. A UUID that the wine already has answers HTTP 409.
   - `DELETE /api/dataset-atlas-binding?slug=…&product_uuid=…` removes that row. The
     answer is `{ok, slug, removed, removed_source, products, total, manual}`. A missing
     `product_uuid` answers HTTP 400. A row that does not exist answers HTTP 404.
4. `pipeline/pages/dataset.html`: the editor `Atlas Core product` lists each UUID with
   its source, `×`, `copy`, and `open`. The head shows the count. `+` opens the input.
   The filter `has Drink Atlas` and the search read all UUIDs.
5. `../drink-atlas-matcher`: `LabWine.bindings` maps product UUID → source. A report row
   gets `prior_bindings`, a list of `{"product_uuid", "source"}`, in place of
   `prior_binding_source` and `prior_product_uuid`. The relation is `agree` when the top
   candidate is one of the UUIDs. The report schema becomes
   `svoe-vino-lab-drink-atlas-report-v2`.

## Consequences

1. A wine with a wrong automatic UUID and a correct manual UUID shows both after a new
   add. A person removes the wrong UUID with its `×`.
2. The old review tool keeps one UUID per slug. It does not see the lab rows.
3. The report of 2026-09-26 in `docs/reports/2026-09-26_drink-atlas-match/` stays in the
   v1 form.
