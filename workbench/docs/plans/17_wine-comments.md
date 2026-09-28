# 17 — Timestamped comments of a wine

Date: 2026-09-25.
Status: the owner chose the design on 2026-09-25T11:07:00+0300. Implemented and
deployed on 2026-09-25 by drink-atlas-workspace-98 as schema file `011_wine_comment.sql`.
`data/lab.sqlite3` is at version 11. The lab server on 8168 runs the code since about
11:23.
The owner message of 2026-09-25T11:04:34+0300, the three answers, the message of
11:07:59 (the filter), and the message of 11:09:30 (the source) are in
[owner-messages.md](../owner-messages.md).

## Goal

1. A person can add a comment to one wine on the Dataset page of the lab server.
2. One wine MAY have more than one comment. Each comment has a timestamp.
3. A person can remove one comment.
4. The page shows the comments of a wine in time order, the oldest first.
5. The comments are in their own table, not in `wine_code`.
6. Each comment has a source: `user` for a person on the Dataset page, `script` for a
   script.

## Decisions of the owner

- Order: the oldest comment first. The newest comment is next to the input field.
- Input: a multi-line text field. Enter adds a line break. Cmd+Enter or Ctrl+Enter saves.
  The button `✓` saves. Esc cancels.
- The shared files `pipeline/lab_server.py` and `pipeline/pages/dataset.html` get small
  separate hunks on top of the uncommitted work of the other sessions.

## Schema file

`pipeline/schema/NNN_wine_comment.sql`. The number is fixed at the entry (rules 25 to 28
of `AGENTS.md`).

```sql
CREATE TABLE wine_comment (
    id         INTEGER PRIMARY KEY,
    wine_slug  TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    created_at TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    source     TEXT NOT NULL CHECK (source IN ('user', 'script')),
    text       TEXT NOT NULL CHECK (text <> '' AND length(text) <= 4000)
) STRICT;

CREATE INDEX wine_comment_wine ON wine_comment (wine_slug, created_at, id);
```

- `id` identifies one comment. A remove names the `id`, because two comments MAY hold
  the same text.
- `created_at` is the UTC time of the write, to the second, in ISO 8601 with `Z`. The
  string order is the time order. Two comments of the same second keep the `id` order.
- The page shows `created_at` in the local time of the browser.
- `source` is `user` for a person on the Dataset page and `script` for a script.
- A comment has no edit. A person removes it and adds a new one.

## Module `pipeline/comments.py`

- `clean_text(value)`: the value MUST be a string. The function changes `\r\n` and `\r`
  to `\n` and removes the white space at the start and at the end. The result MUST NOT
  be empty and MUST have at most 4,000 characters. A control character other than `\n`
  and `\t` is refused. The function raises `CommentError`.
- `comments(conn, slug=None)`: wine slug -> the list of `{id, created_at, source, text}`,
  in time order.
- `count(conn)`: the number of rows.
- `add(conn, slug, text, source, now=None)`: insert one row, return it. `source` MUST
  be `user` or `script`. A script that writes the database directly uses `script`.
- `remove(conn, slug, comment_id)`: delete one row of the wine, return its row, or None.

A function that writes runs in the transaction of the caller.

## Lab server

- `GET /api/dataset`: each record gets `_comments`. The answer gets `comments`, the
  number of rows.
- `POST /api/dataset-comment` with `{"slug": …, "text": …}` adds one comment. The answer
  is `{"ok": true, "slug": …, "comment": {…}, "comments": […], "total": N}`.
- The body MAY hold `"source": "script"`. A script that uses the HTTP route sends it.
  With no `source`, the source is `user`. The Dataset page sends no `source`.
- `DELETE /api/dataset-comment?slug=…&id=…` removes one comment. The answer is
  `{"ok": true, "slug": …, "removed": id, "comments": […], "total": N}`.
- Errors: HTTP 400 for a bad body, a bad text, or a bad `id`. HTTP 404 for an unknown
  wine or a comment that the wine does not have. A wine of each state allows a write.

## Dataset page

- The editor `Comments` stands after the editor `Atlas Core product`. It has the count,
  the `+` button, the list, and the input field. It redraws its own card alone.
- Each comment shows the local time, the source, the text with its line breaks, and
  the `×` button.
  The `×` button asks for a confirmation.
- The head line gets `N comments`. The text search finds the text of a comment.
- The filter `Show` gets the value `with comments`: the wines with at least one comment.
  The owner asked for it on 2026-09-25T11:07:59+0300.
- The editor and the filter value show only when the answer has the key `comments`. The
  review tool `scripts/review_server.py` does not send it.

## Tests

- `tests/test_comments.py`: `clean_text`, the order, the add, and the remove.
- `tests/test_lab_server.py`: the routes, the answers, and the errors.
- `tests/test_labdb.py`: the version and the list of the tables.

## Deploy

The entry of the schema file, the migration of `data/lab.sqlite3`, and the restart of
the lab server on 8168 belong together (rule 27 of `AGENTS.md`).
