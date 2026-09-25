# 36 — The row "No Match" and the Drawer of `/testset`

Date: 2026-09-26.
Status: approved by the owner at 00:33:55. Done at 00:44:51, not committed.
Session: drink-atlas-workspace-e2 [9e7fe4].
Source: owner message of 2026-09-26T00:25:00+0300 and the answer of 00:29:00.

## Goal

The Testset page gets two special places instead of one:

1. "No Match": a special row of the table. A photo of this row shows a wine that no card
   of the catalogue shows. A run uses each such photo. The right answer is "no match".
2. "Drawer": the right sidebar. It keeps photos between launches. A run does not use a
   photo of the Drawer.

The owner answer of 2026-09-26T00:29:00:

```text
yes, we need 2 special items:
- "no match" - images that assigned to this item expected not to much, but they are matched
- "drawler" - it is right drawler sidebar. These images are not used for matching.
```

## The present state

1. The place `__null__` is the right sidebar (owner answers of 2026-09-25T18:05:36).
2. `__null__` has two jobs. A photo with no label waits for a wine. A photo with `V`
   (`positive`) is a "no match" query of a run.
3. `benchmark.build_queries` takes a `__null__` photo only with `positive`. This rule
   differs from `scripts/match_run.py`, which takes each `__null__` photo that is not
   `unusable`.
4. On 2026-09-26T00:30 no set holds a photo of `__null__`. `official-real-photos` holds 7
   photos with `reassign_to: __null__` (6 `unusable`, 1 `negative`), from the old tool.

## Decisions

| Point | Decision |
|---|---|
| The place of "No Match" | `__null__`. This is its meaning in `review-labels.json` and in `scripts/match_run.py`. The 7 `reassign_to: __null__` entries keep their meaning. |
| The place of the Drawer | A new reserved place `__drawer__`. No schema change: `test_photo.place` is free text. |
| The queries of "No Match" | Each `__null__` photo is a "no match" query, also with no label. A photo stays out when its label is `unusable`, when it is marked for deletion, or when `__null__` is excluded. This is the rule of `match_run.py`. |
| The labels of "No Match" | `V` and `×`, as today. `V` stays a confirmation of a person. A run does not need it. |
| The queries of the Drawer | None. `build_queries` counts a Drawer photo as "drawer" and leaves it out. |
| The labels of the Drawer | None. The server refuses a label on `__drawer__` with HTTP 400. The comment, the box, and the delete mark stay allowed. |
| The place of the row | The first row of the table. No filter, sort, search, slug filter, or group filter removes it. |

## Changes

1. `pipeline/testsets.py`:
   - New `DRAWER_SLUG = "__drawer__"` and `DRAWER_NAME = "Drawer"`.
   - `NULL_NAME` becomes `No Match`.
   - `set_view` adds the row of `__drawer__` with `drawer_row: true`. The row of
     `__null__` keeps `null_row: true`.
   - `_known_slug` accepts `__drawer__`. So a move and an upload to the Drawer work.
   - `set_label` refuses each label on `__drawer__` (HTTP 400).
   - `counts` gets the key `drawer`. `export_testset.COUNT_KEYS` does not change, so the
     export does not write it.
2. `pipeline/benchmark.py`: the `__null__` rule of `match_run.py`; a `__drawer__` photo is
   left out as "drawer". The docstring changes.
3. `pipeline/manual_wines.py`: `RESERVED_SLUGS` gets `__drawer__`.
4. `pipeline/testset_routes.py`: the docstring names `__drawer__`.
5. `pipeline/pages/testset.html`:
   - The row "No Match" is the first row of the table again.
   - The sidebar shows the photos of `__drawer__`. Its title is "Drawer". Its help text
     says that a run does not use its photos.
   - A drop of a card onto the sidebar moves the photo to `__drawer__`. A drop of Finder
     files onto the sidebar uploads them to `__drawer__`. A drop onto the row "No Match"
     moves or uploads to `__null__`, as for each wine row.
   - The key `0` of the large view moves the photo to the Drawer. The context menu gets
     "Move to the Drawer" and "Move to No Match".
   - A Drawer card has no label buttons.
   - The header counts the photos of "No Match" and of the Drawer.
6. Tests: `tests/test_testsets.py`, `tests/test_testset_routes.py`,
   `tests/test_benchmark.py`, `tests/test_manual_wines.py`.
7. Docs: `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`, one note line in
   `docs/plans/24_testset-page.md`.
8. A restart of 8168 (rules 22 to 24 of `AGENTS.md`).

## Not changed

- The import and the export of `review-labels.json`. The export writes a Drawer entry
  under the key `__drawer__`. `match_run.py` reads only the photos of the directories of
  `svoe-vino-testset`, and no directory `__drawer__` exists there.
- The Runs page. Its filters `no match` read the label `no_match` of a run.

## Risks

- A photo that a person drags onto the sidebar before the restart goes to `__null__`.
  After the restart, it is in the row "No Match" and a run uses it. Just before the
  restart, the session counts the `__null__` photos of each set. When the count is not
  0, the session asks the owner.
- Session drink-atlas-workspace-28 [5ddfae] changes `render` of `testset.html` at the
  same time. The two sessions agree on separate hunks.

## Result

1. The server code went live with the restart of 8168 by drink-atlas-workspace-d3
   [4920ce] at 00:36:23. The page is read from disk on each request, so the page hunks
   went live without a second restart.
2. `python3 -m unittest discover -s tests -p "test_*.py"`: 692 tests `OK`.
3. A browser check on a copy of the database on the temporary port 8175: 23 checks pass,
   in the light theme, in the dark theme, and at a width of 390 px. The check ran again
   after the hunks of session drink-atlas-workspace-28 [5ddfae]: 23 checks pass.
4. `build_queries` on the copy: a `__null__` photo with no label is a `no_match` row, and
   a `__drawer__` photo is counted as `drawer`.
5. A read-only check of the live page on 8168: the first row is `__null__`, and the page
   gives no error.
