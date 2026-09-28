# 52 — Wine type

Date: 2026-09-26.
Status: the owner chose the design on 2026-09-26T18:21:29+0300. Implemented and deployed
on 2026-09-26 by drink-atlas-workspace-d3 as schema file `023_wine_beverage_type.sql`,
after schema 022 of drink-atlas-workspace-ab (owner answer of 18:46:25).
`data/lab.sqlite3` is at version 23 since 18:54:25. The lab server on 8168 runs the code
since 18:54:37. The owner messages of 2026-09-26T17:53:16+0300 and 18:10:45 and the
answers are in [owner-messages.md](../owner-messages.md). The research is in the entry "2026-09-26: Wine
style or bottle type" of [../../../ResearchLog.md](../../../ResearchLog.md).

## Goal

1. Each wine has a wine type: `beverage_type_code`, as in Drink Atlas Core. The default
   is unset.
2. A select on each card of the Dataset page sets the type.
3. The filter `Type` in the row of the advanced filters shows `All`, `Wines`,
   `Sparkling Wines`, or `Not set`.

## Values

| Code | Meaning | Card label | Filter label |
|---|---|---|---|
| no row | no type yet | `not set` | `Not set` |
| `4` | a wine that is not sparkling | `Wine` | `Wines` |
| `44` | a sparkling wine | `Sparkling wine` | `Sparkling Wines` |

- In Drink Atlas Core, `beverage_type_code` is an EGAIS product type code, for example
  `401` or `4402`. `4` and `44` are prefixes of these codes, not dictionary codes.
  `drink-atlas-core/src/drink_atlas_core/data/egais-product-types.json` marks both
  prefixes with `is_dictionary_code: false`. The owner chose the two prefixes on
  2026-09-26, so that the first version stays simple.
- Pearl wine (`4402`) is in the prefix `44`. A frizzante and a pet-nat get `44`.
- This plan copies no code from Drink Atlas. A later copy of exact codes, for example
  from the 367 wines with a Drink Atlas binding, needs one more rule: a sparkling wine
  can also have a code with the prefix `45`, for example `4501`.

## Decisions of the owner

- Storage: a separate table `wine_beverage_type`, not a column of `wine_catalog`. The
  imports of the catalogue do not change. The change-time triggers of schema 015 do not
  change. A change of the type does not change `wine_catalog.modified_at`.
- The card control: one select on the category line of the card.
- The filter: in the row of the advanced filters, after `Package` and `Identifier`.
- The filter values: `All`, `Wines`, `Sparkling Wines`, and `Not set`.

## Schema file

`pipeline/schema/NNN_wine_beverage_type.sql`. Until the deploy, the file is
`pipeline/schema_pending/NNN_wine_beverage_type.sql`. The number is fixed at the entry
(rules 25 to 28 of `AGENTS.md`).

```sql
CREATE TABLE wine_beverage_type (
    wine_slug          TEXT PRIMARY KEY REFERENCES wine_catalog (wine_slug),
    beverage_type_code TEXT NOT NULL CHECK (beverage_type_code IN ('4', '44')),
    updated_at         TEXT NOT NULL CHECK (updated_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z')
) STRICT;
```

- A wine has a type while it has a row. A change to `not set` deletes the row.
- `updated_at` is the UTC time of the last change of the code, in the form of
  `wine_comment.created_at`. The page does not show it.
- A new code value needs a new schema file, because SQLite cannot change a CHECK in
  place.

## Module `pipeline/beverage_types.py`

- `CODES = ("4", "44")`.
- `types(conn)`: wine slug -> `beverage_type_code` of each wine with a type.
- `counts(conn)`: `{"4": N, "44": M}`. A code with no wine has the count 0.
- `set_type(conn, slug, code, now=None)`: `code` None deletes the row. Another code adds
  the row or changes it. The same code again keeps `updated_at`. Return `code`.

A function that writes runs in the transaction of the caller.

## Lab server

- `GET /api/dataset`: each record gets `_beverage_type_code`: `"4"`, `"44"`, or null.
  The answer gets `beverage_types`: `{"4": N, "44": M}`.
- `POST /api/dataset-beverage-type` with
  `{"slug": …, "beverage_type_code": "4" | "44" | null}` sets the type. The body names
  the new value, not a toggle, so a repeated request gives the same result. The answer
  is `{"ok": true, "slug": …, "beverage_type_code": …, "beverage_types": {…}}`.
- Errors: HTTP 400 for a bad body, for a body with no slug, for a body with no key
  `beverage_type_code`, or for a value that is not `"4"`, `"44"`, or null. HTTP 404 for
  an unknown wine. A wine of each state allows the change.

## Dataset page

- The category line of each card (`.kind`: the category and the region) gets the select
  `Type` with `not set`, `Wine`, and `Sparkling wine`. A card with no category and no
  region gets the line with the select alone.
- A change of the select saves at once. The select is disabled while the request runs.
  The save redraws its own card alone. A failed save shows an alert, and the card shows
  the stored value again.
- The row of the advanced filters gets `Type` after `Identifier`. `Wines` shows the
  wines with `4`. `Sparkling Wines` shows the wines with `44`. `Not set` shows the wines
  with no type. The filter combines with the other filters (AND).
- A card that leaves the view of the filter `Type` after a save leaves the list, as a
  card that leaves the view of the filter `State`.
- The button `Advanced Filters:` has the accent while `Type` is not `All`, as for
  `Package` and `Identifier`. The page stores the value of `Type` with the other header
  controls in `localStorage`.
- The select and the filter show only when the answer has the key `beverage_types`. The
  review tool `scripts/review_server.py` does not send it.
- The head line and the text search do not change.

## Tests

- `tests/test_beverage_types.py`: set, change, the same code again, unset, the counts,
  and the checks of the table.
- `tests/test_lab_server.py`: the route, the answers, the errors, and the keys of
  `GET /api/dataset`.
- `tests/test_labdb.py`: `VERSION` and the list of the tables.
- A browser check of the Dataset page on a scratch copy: the select, the save, the
  filter, and the stored header value.

## Documents

- `README.md`: the paragraph of the Dataset page, and one paragraph of the new table.
- `docs/database-structure.html`: not changed. The box of the new table does not fit the
  one-page layout (diagram overflow 91 px with the box), and the page stops at schema
  017. drink-atlas-workspace-ab reports to the owner that the page needs a new layout.
- The docstring of `pipeline/lab_server.py`.
- `ChangeLog.md` and `SMOKE_TESTS.md`.

## Deploy

1. The code and the tests, with the schema file in `pipeline/schema_pending/`. The tests
   run on a scratch copy of the project, where the file has its number.
2. Rule 26: read `pipeline/schema/` and `ACTIVE_WORK.md`. Send a message to each session
   with schema work. Take the next free number.
3. A backup of `data/lab.sqlite3`, then the migration with `pipeline/labdb.py`.
4. The restart of 8168 with SIGTERM (rules 22 to 24). The restart also deploys the
   uncommitted code of the other sessions. Before the restart, send a message to each
   active session with uncommitted hunks in the files of the server, and tell the owner.
5. Check that `GET /api/dataset` answers HTTP 200 with the key `beverage_types`.
