# 19 — Favorite wines

Date: 2026-09-25.
Status: the owner chose the design on 2026-09-25T11:39:42+0300. Implemented and
deployed on 2026-09-25 by drink-atlas-workspace-98 as schema file `013_wine_favorite.sql`.
`data/lab.sqlite3` is at version 13. The lab server on 8168 runs the code since 11:55.
The owner message of 2026-09-25T11:37:46+0300 and the two answers are in
[owner-messages.md](../owner-messages.md).

## Goal

1. A star on each card of the Dataset page marks a wine as a favorite. A click toggles
   the mark and saves it at once.
2. The `State` filter gets the value `Favorites`. It shows each favorite wine in each
   state, also a `Removed` wine.

## Decisions of the owner

- Storage: a separate table `wine_favorite`, not a column of `wine_catalog`. The imports
  of the catalogue do not change.
- The star stood first before the name, on the name line (answer of 11:39:42). The owner
  moved it at 11:58:25 (message to drink-atlas-workspace-0b): it stands at the top right
  of the text column (`.info`), next to the alternative photos. `☆` is not a favorite.
  `★` in the amber color of the theme (`--var`) is a favorite.

## Schema file

`pipeline/schema/NNN_wine_favorite.sql`. The number is fixed at the entry (rules 25 to 28
of `AGENTS.md`).

```sql
CREATE TABLE wine_favorite (
    wine_slug  TEXT PRIMARY KEY REFERENCES wine_catalog (wine_slug),
    created_at TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z')
) STRICT;
```

- A wine is a favorite while it has a row. A remove of the mark deletes the row.
- `created_at` is the UTC time of the mark, in the form of `wine_comment.created_at`.
  The page does not show it.

## Module `pipeline/favorites.py`

- `favorites(conn)`: wine slug -> `created_at` of each favorite.
- `count(conn)`: the number of favorites.
- `set_favorite(conn, slug, on, now=None)`: add or delete the row. A second add or a
  delete of a missing row changes nothing. Return `on`.

A function that writes runs in the transaction of the caller.

## Lab server

- `GET /api/dataset`: each record gets `_favorite` (true or false). The answer gets
  `favorites`, the number of favorites.
- `POST /api/dataset-favorite` with `{"slug": …, "favorite": true|false}` sets the mark.
  The body names the new value, not a toggle, so a repeated request gives the same
  result. The answer is `{"ok": true, "slug": …, "favorite": …, "total": N}`.
- Errors: HTTP 400 for a bad body or a `favorite` that is not a JSON boolean. HTTP 404
  for an unknown wine. A wine of each state allows the change.

## Dataset page

- The star button stands at the top right of the text column. The slug line and the
  name line keep room for it, so no text runs under it. At a width of at most 860 px the
  alternative photos stand below the text, and the star stays at the top right of the
  text column. One click sends the other value. The button
  is disabled while the request runs. The save redraws its own card alone.
- The `State` filter gets the value `Favorites` after `Removed`. It shows the wines with
  `_favorite`, in each state. A wine whose mark goes away in this view leaves the list,
  as a wine that leaves the view of another `State` value.
- The head line gets `N favorites`.
- The star and the filter value show only when the answer has the key `favorites`. The
  review tool `scripts/review_server.py` does not send it.

## Tests

- `tests/test_favorites.py`: the add, the second add, the delete, the count.
- `tests/test_lab_server.py`: the route, the answers, and the errors.
- `tests/test_labdb.py`: the version and the list of the tables.

## Deploy

The entry of the schema file, the migration of `data/lab.sqlite3`, and the restart of
the lab server on 8168 belong together (rule 27 of `AGENTS.md`).
