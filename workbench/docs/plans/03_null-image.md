# 03 — The virtual NULL image

Date: 2026-09-21

## Purpose

A candidate photo can show a wine that no card of the catalogue holds. The review
tool has no way to state this today. The reviewer can only label the photo
`negative`, which states "not this wine" and states nothing about the catalogue.

This plan adds a virtual wine, the NULL image. The reviewer assigns a photo to it
with the same gestures that move a photo to another wine. A photo that lies under
the NULL image carries one statement: **no card of the catalogue shows this wine**.

The benchmark then scores the rejection: the backend MUST answer nothing for such
a photo, and any answer is a false match.

## Decisions

| Decision | Value | Reason |
|---|---|---|
| Storage | A reserved slug with a real directory in `photo_dir` | The tool already moves a photo into the directory of the wine it shows. The NULL image reuses that path, so drag, `reassign_to`, the move dialog, and `apply-moves` need no new machinery. |
| Slug | `__null__` | Two leading underscores keep it apart from every catalogue slug. The catalogue slugs hold no underscore at the start. |
| Label needed? | No | The place IS the statement. A photo under `__null__` counts as a rejection case. `unusable` and the delete mark still take a photo out, as everywhere else. |
| Allowed labels there | `positive`, `unusable` | `positive` confirms the statement. `negative` and `variant` say nothing under NULL, so the server refuses them. |
| Copy to NULL | Refused | A copy states that the photo shows a second wine. NULL is not a wine. |
| Benchmark | `match_run.py` scores the rejection | The user asked for it. See "Stage 2". |

## Stage 1 — the review tool

`scripts/review_server.py`.

### The server

1. Add `NULL_SLUG = "__null__"` and `NULL_NAME`.
2. Add `null_row(catalog)`. It returns the row of the virtual wine. The row holds
   `null_row: True`, `in_catalog: False`, `has_bottle: False`, and the photos of
   `photo_dir/__null__/` when that directory is present.
3. `build_rows` skips the directory `__null__` in its loop and appends `null_row()`.
   The row is therefore present even when the directory is not.
4. `_apply_reassign` accepts `__null__` as a target although the catalogue does not
   hold it and the directory may not exist yet.
5. `_apply_copy` refuses `__null__`.
6. `_apply` refuses `negative` and `variant` under `__null__`.
7. `plan_inbox_moves` accepts `__null__` as a target.
8. `move_note` and `inbox_note` write a text that names the NULL image, not the
   raw slug.
9. `suggest_targets` always ends with the NULL entry, so the move dialog offers it.
10. `count_state` counts the photos under `__null__` as `no_match`.
11. `save_state` describes the slug in the note of the file.
12. `_group` and `_set_excluded` keep their present rules. `_group` already refuses
    a slug that the catalogue does not hold.

### The page

13. The NULL row stands first in the table and no filter takes it away, so the drop
    target is always present.
14. The bottle column of the NULL row draws a placeholder, not an image. The row
    has no `Group` button.
15. A card of the NULL row shows the label buttons `positive` and `unusable` alone.
16. The key `0` assigns the photo under the pointer, or the photo of the large view,
    to the NULL image.
17. A move badge that names `__null__` reads `→ NULL`.
18. The counters of the header show `no match: N`. The line "N of M wines shown"
    leaves the NULL row out of both numbers.

### The agent API

19. `GET /api/v1/wines` leaves the NULL wine out: it is no card of the catalogue and
    holds no labelling work. `GET /api/v1/wine/__null__` answers for it.
20. `POST /api/v1/propose` refuses `__null__`. A reviewer moves a photo there.
21. `GET /api/v1/stats` counts its photos apart, as `no_match_photos`.

## Stage 2 — the benchmark

`scripts/match_run.py`.

22. `build_queries` reads the photos of `__null__`. Each one becomes a row with the
    label `no_match`, an empty `truth`, and the slug `__null__`. The photo stays out
    when it carries `unusable`, when it is marked for deletion, or when `__null__`
    stands in `excluded-slugs.json`.
23. `judge` scores a `no_match` row: no answer is correct, and any answered slug is
    `false_match_at_1`.
24. `metrics_of` adds the block `no_match`: `n`, `rejected`, `false_match_at_1`,
    `rejection_rate`, `errors`, and the median score of a false match.
25. `write_summary` adds the section "Photos with no match in the catalogue".
26. The runs page of the review tool gets two filters: every `no_match` photo, and
    the `no_match` photos that got an answer.

## Risks

- A photo under `__null__` is out of every positive metric. The match share of a
  run does not change. The rejection numbers stand in their own block.
- `08_variants.py`, `03_embed.py`, and the other pipeline stages read `photo_dir`.
  They see a new directory. This plan does not change them, because the pipeline
  runs on the dataset `default` and the NULL directory is empty there until a
  reviewer uses it. This is written in the ChangeLog as an open point.
