# Plan 66: the tags of a test image

Date: 2026-09-27

Source: owner message of 2026-09-27T23:50:37+0300 and the owner answers that follow it
(`docs/owner-messages.md`).

## Goal

A person puts free-form text tags on a test photo on `/testset`. A tag belongs to the
image bytes (the SHA-256 of the file). So each copy of the image, in each set and in each
row, shows the same tags.

## Decisions of the owner

1. A tag belongs to the image bytes (`sha256`), not to one photo of one set.
2. The page shows and edits the tags in three places: an editor in the side panel of the
   large view, a badge on each tile, and a filter `Tag`.
3. The JSON export of a set writes the tags into the field `tags` of each label entry.
   The import reads the field back.

## Decisions of the agent

4. A tag has the form of the wine tags of plan 63: `wine_tags.normal` makes it. It has
   1 to 64 characters. Each character is a letter, a digit, `_`, `-`, `:`, or `.`. The
   normal form has no outer white space and is lower case. A later change of these rules
   in `wine_tags.py` changes the rules of the image tags too (condition of
   drink-atlas-workspace-1e [7df1e0], the session of plan 63).
5. The pipeline does not read the tags. A run does not read them.
6. A tag write sets `test_set.edited_at` of the set of the request, as a photo comment
   does. It does not change `ts` of the label entry, because a tag has its own time.
7. The import adds the tags of an entry. The import never removes an image tag, because
   an image tag belongs to no set. A second import adds no row.
8. A `tags` value that is not a list of valid tags stops the import, as an unknown label
   value does. The reason: a value in `extra` would collide with the field `tags` of the
   export.
9. `New testset…` of `/runs` (plan 44) needs no change. The new set holds the same
   images, so it shows the same tags.

## Data

Schema file `pipeline/schema/NNN_image_tag.sql`. The number is fixed at the entry of the
file (rules 25 and 26 of `AGENTS.md`). The next free number on 2026-09-27T23:55 is 030.

```sql
CREATE TABLE image_tag (
    sha256     TEXT NOT NULL REFERENCES image (sha256),
    tag        TEXT NOT NULL CHECK (tag <> '' AND length(tag) <= 64),
    created_at TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    PRIMARY KEY (sha256, tag)
) STRICT;
```

- One row is one tag of one image. The rowid order is the order of the adds.
- `created_at` is the UTC time of the add, as `wine_tag.created_at`.
- No code deletes a row of `image`. A later schema file that builds `image` again MUST
  handle this table too.

## Module `pipeline/image_tags.py`

10. `tags(conn, digests=None)` returns SHA-256 -> the list of its tags, in rowid order.
    With `digests`, the answer holds those images alone. An image with no tag has no key.
11. `names(conn)` returns each tag of the table once, sorted, with the number of its
    images.
12. `add(conn, digest, text, now=None)` adds one tag and returns its normal form. A tag
    that the image has raises `DuplicateError`.
13. `remove(conn, digest, text)` removes one tag. It returns False for a tag that the
    image does not have.

## Module `pipeline/testsets.py`

14. `photo_view` sends `tags`: the list of the tags of the image of the photo.
15. `set_view` sends `tag_names`: the result of `image_tags.names`. The page suggests
    these tags in the input.
16. `add_photo_tag(conn, set_name, place, file_name, tag)` and
    `remove_photo_tag(conn, set_name, place, file_name, tag)` find the photo, write the
    tag of its image, and set `test_set.edited_at`. The answer: `ok`, `set`, `place`,
    `file`, `sha256`, `tags` (the tags of the image after the write), `added` or `removed`
    (the normal form), `tag_names`, `photo`, and `counts`.

## Routes

17. `POST /api/testset-photo-tag` with the body `{set, place, file, tag}` adds one tag.
18. `POST /api/testset-photo-tag-remove` with the body `{set, place, file, tag}` removes
    one tag.
19. HTTP 400: no tag, or a tag that breaks item 4. HTTP 404: no set, no photo, or a
    remove of a tag that the image does not have. HTTP 409: an add of a tag that the image
    has.

## The page `/testset`

20. The side panel of the large view gets the section `Tags of this image` between the
    comments and the box. It lists the tags as chips with a remove button `×`. An input
    adds a tag: Enter adds it, Esc leaves the field. The input suggests the tags of
    `tag_names` (a `datalist`). A short note tells that the tags belong to the image, so
    each copy of the image shows them.
21. A tile of a photo with a tag shows a badge at the lower right corner of the image.
    The badge shows the tags, cut with an ellipsis. Its title lists each tag.
22. The select `Marks` gets the option `a tag`. The row counts get `N tagged`.
23. The row `Additional settings` gets the select `Tag`: `any`, then each tag of the
    photos of the set, with its number of photos. A choice shows the wines that hold a
    photo whose image has the tag. The select is not an axis of `FILTER_AXES`, because a
    free-form tag can be equal to an option value of an axis, for example `done`. The
    address keeps it as `tag=`, and `localStorage` keeps it with the header.
24. After a write, the page draws again each tile of the set that shows the same image.
25. The editor uses the colours of the page (`--accent`, `--line`, `--panel-2`). So the
    light and the dark theme stay correct.

## Export and import

26. `export_testset.py` writes `tags` into the entry of each photo whose image has a tag.
    A photo with a tag and no other field now gets an entry. `LABELS_NOTE` gets one
    sentence about the field `tags`.
27. `import_testset.py` takes the field `tags` out of the entry before
    `testsets.entry_columns`, as it does for `comments`. It adds each tag with
    `INSERT ... ON CONFLICT DO NOTHING`, after the new rows of `image`. The report counts
    the new tags and the tags that were there already.

## Deploy

28. The entry of the schema file, a backup and the migration of `data/lab.sqlite3` with
    `pipeline/labdb.py`, and the restart of 8168 belong together (rule 27).
29. The schema file comes after 027, 028, and 029. These files are not committed. So
    this plan is committed after them. `image_tags.py` imports `wine_tags.py` (plan 63),
    so this plan is committed with or after plan 63.
30. `pipeline/db_export.py` reads `sqlite_schema`. It exports the new table with no
    change.

## Tests

31. `tests/test_image_tags.py` (new): the module functions and the table checks.
32. `tests/test_testsets.py`: `tags` in `photo_view`, `tag_names`, the two writes, the
    errors, and one image in two places.
33. `tests/test_testset_routes.py`: the two routes and their HTTP codes.
34. `tests/test_export_testset.py` and `tests/test_import_testset.py`: a round trip of
    `tags`, a second import adds no row, a bad `tags` value stops the import.
35. `tests/test_labdb.py`: VERSION and the table list.
36. A browser check on 8168 with the tag writes mocked and each other write blocked, in
    the light and the dark theme.
37. Smoke tests IT1 and later in `SMOKE_TESTS.md`.

## Result

Done on 2026-09-28. The code and the tests were made in a scratch copy of the project,
with the schema file under its number. They went into the tree at 00:32 with patches at
zero fuzz. Schema 030 was entered and migrated at 00:32:43, after the backup
`data/backups/lab-before-030-image-tag-20260927T213243Z.sqlite3`. 8168 was restarted at
00:32:47 (PID 4467). No session had pending server code at the restart. The self-test job
of drink-atlas-workspace-49 had ended at 00:21:32.

- `test_image_tags.py` 5, `test_testsets.py` 31, `test_testset_routes.py` 11,
  `test_import_testset.py` 18, `test_export_testset.py` 9, and `test_labdb.py` 17 tests
  OK. The full suite gives 1,290 tests OK (5 skipped).
- A browser check on a scratch server (port 8175) with a migrated copy of the database
  passed 60 of 60 checks, in the light and the dark theme, at 1,440 px and 390 px. It
  used the real routes on the copy: add, duplicate, bad tag, suggestions, badges on both
  places, the filter `Tag` with the address and the header, `Marks: a tag`, the set `my`
  with 4 copies, and the removes.
- A read-only browser check on 8168, with each write blocked, passed 12 of 12.
- No data of the tree held a field `tags` before this plan: no `extra` of `test_photo`,
  and no entry of the six `review-labels.json` files of `svoe-vino-testset/dataset/` and
  `dataset/`.
- One change outside the plan: the row count `N tagged` has the class `tagged-n`
  (`white-space: nowrap`), because the meta column breaks each word (`word-break`) and
  the text broke inside `tagged`. The other row counts stay as they were.
