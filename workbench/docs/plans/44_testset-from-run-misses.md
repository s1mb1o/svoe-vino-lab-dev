# Plan 44: a new test set from the misses of a run

Date: 2026-09-26. Session: drink-atlas-workspace-9e [4644ab].
Status: approved by the owner on 2026-09-26T09:12:00+0300 (the four answers below). Done
on 2026-09-26, not committed.

Source: owner message of 2026-09-26T09:05:00+0300 and the answers of 09:12:00. The text
is in [../owner-messages.md](../owner-messages.md).

## 1. Goal

1. The page `/runs` gets a button `New testset…` for the open run.
2. The button opens a dialog. The dialog selects the R@1 misses or the R@5 misses of the
   run, and the name of the new test set.
3. The name is `<set>-<N>` by default. `<set>` is the test set of the run. `N` is the
   first number that gives a free name.
4. `Create` writes the new test set into the lab database. The set then stands on
   `/testset`, and the dialog `Run>` of `/testset` can run it.

## 2. The facts before the change

- A run of `pipeline/benchmark.py` names its test set in `options.set` of `run.json`.
  On 2026-09-26, `runs/` holds 140 run directories. 57 runs name a set: `my` (29) and
  `official-real-photos` (28). 78 runs come from `scripts/match_run.py` and name no set.
  5 directories hold no `run.json`.
- `results.jsonl` holds one row for each query: `image_path` (`<place>/<file name>` of the
  set), `image_sha256`, `label`, `rank_of_truth`, and `error`. `rank_of_truth` is null
  when the true slug did not come back.
- The metrics count a failed request of a positive photo as a miss: `recall` of
  `scripts/match_scoring.py` counts a row only when `rank_of_truth <= k`.
- The set `vlmrerank-8b-failed` of `svoe-vino-testset` is the model. It holds the positive
  photos of `default` that the run `2026-09-18T195710Z-svm-vlmrerank-8b-siglip2-448-bench`
  missed at rank 1. The label entries and the notes of the wines are copies without a
  change. `excluded-slugs.json` and `variant-groups.json` are copies of the files of
  `default`. A photo whose label in `default` changed after the run stays out.
- The run `2026-09-25T235549Z-lab-local-siglip2-p256-crop-my-bench40` holds 419 R@1
  misses and 144 R@5 misses. On 2026-09-26 at 09:10, each of them was still `positive` in
  `my`, with the same place, file name, and SHA-256.
- The table `test_set` needs `source_dir` (NOT NULL, not empty). A set name matches
  `^[0-9a-z_-]+$` (the CHECK of `016_testset.sql` and `SET_NAME_RE` of
  `import_testset.py`).

## 3. Decisions of the owner

| Question | Options | Answer |
|---|---|---|
| How does the code make the set? | rows in the database; the same with a new table of the origin (a schema change); a set directory and an import, as `vlmrerank-8b-failed` | rows in the database |
| How does the dialog select the misses? | one choice of two (R@1 or R@5); two check boxes of two groups without an overlap (rank 2 to 5; not in the top 5) | one choice of two |
| A photo whose label in the source set changed after the run | leave it out; copy the present entry | leave it out |
| The name when the source set has a number, for example `my-1` | `my-2`; `my-1-1` | `my-2` |

The agent stated these defaults before the questions, and the owner did not change them:

- The button stands next to the heading `Metrics of <run>`. It is off for a run that names
  no test set and for a dry run.
- The misses come from the whole run. The controls `Show` and `Find` do not change them.
- The new set holds positive photos alone, as `vlmrerank-8b-failed` does.

## 4. The selection rule

1. The run names a test set in `options.set`, the run is not a dry run, and the database
   holds that set. Else the dialog shows the reason, and `Create` is off.
2. A row of `results.jsonl` is selected when its `label` is `positive` and:
   - R@1 misses: `rank_of_truth` is not 1;
   - R@5 misses: `rank_of_truth` is null or greater than 5.
   A row with an `error` has a null `rank_of_truth`, so it is selected. The metrics count
   it as a miss too. The dialog states the count of such rows.
3. `image_path` gives the place and the file name. The part before the last `/` is the
   place.
4. A selected row is copied when the source set holds a photo with this place and this
   file name, with the SHA-256 of the run, and with the label of the run. Else it stays
   out, with one of these reasons: `gone` (no photo with this place and name), `other
   bytes` (another SHA-256), `label changed` (another label or no label).

## 5. The name rule

1. The base is the name of the source set with one trailing `-<digits>` removed: `my`
   gives `my`, `my-1` gives `my`, `official-real-photos` gives `official-real-photos`.
2. The proposed name is `<base>-<N>` with the first `N` of 1, 2, 3, … whose name is not
   in `test_set`.
3. The dialog shows the proposed name in an input field. The owner can change it.
4. `Create` refuses a name that does not match `^[0-9a-z_-]+$` (HTTP 400) and a name that
   `test_set` holds (HTTP 409). The check and the writes run in one transaction.

## 6. The rows of the new set

One transaction writes these rows. No photo file is copied: the image store keeps one
file for each SHA-256, and the new rows name the same files.

| Table | Rows |
|---|---|
| `test_set` | `set_name` is the new name. `source_dir` is the directory of the run, `runs/<run id>` as an absolute path. `edited_at` is the time of the build, so an import without `--force` does not replace the rows. `label_note` states the origin: the build time, the run, the source set, the rule, and the counts. The note of the source set follows it. |
| `test_photo` | A copy of each row of section 4, step 4, with each column unchanged. |
| `test_wine_note` | A copy of the note of each place that holds a copied photo. |
| `test_excluded` | A copy of each excluded slug of the source set. |
| `test_variant` | A copy of each variant group of the source set. The metric `near_duplicate_confusion` reads the groups. |

`Create` refuses a selection with no photo to copy (HTTP 409).

## 7. The routes

`pipeline/testset_routes.py` answers both routes. `lab_server.py` needs no change, because
it sends each GET and each POST of a route of `testset_routes.handles` to that module.
The new module `pipeline/testset_from_run.py` holds the logic.

- `GET /api/testset-from-run?id=<run id>` answers the data of the dialog:
  `run`, `set` (the source set), `name` (the proposed name), and `misses`. `misses` holds
  `r1` and `r5`. Each holds `selected`, `copied`, `errors` (the selected rows with an
  error), and `left_out` (reason -> count). A run that the rule of section 4, step 1
  refuses answers HTTP 409 with `error`. An unknown run answers HTTP 404.
- `POST /api/testset-from-run` with the body `{run, misses, name}`. `misses` is `r1` or
  `r5`. The answer holds `ok`, `set` (the new name), `source`, `run`, `misses`, `photos`,
  `selected`, `errors`, `left_out`, `wine_notes`, `excluded`, and `variant_slugs`.

## 8. The page

1. `runs.html` gets the button `New testset…` after the heading `Metrics of <run>`.
2. The button opens the dialog `New test set from the misses of a run`. The dialog uses
   the look of the dialog `Run>` of `/testset`.
3. The dialog reads `GET /api/testset-from-run?id=<run>`. It shows two radio buttons:
   `R@1 misses — the true wine is not at rank 1` and `R@5 misses — the true wine is not in
   the top 5`, each with the count of photos to copy. A choice with no photo to copy is
   off. R@1 is the first choice.
4. A note under the choices states the photos that stay out, by reason, and the selected
   rows with a failed request.
5. The input `Name` holds the proposed name.
6. `Create` sends the POST. The dialog then shows the result and a link
   `/testset?set=<name>`. An error of the server stands in the dialog, and the dialog stays
   open.
7. `Esc` and a click outside the panel close the dialog.

## 9. Tests

`tests/test_testset_from_run.py` runs the routes through `lab_server.make_server`, with a
fixture set and a fixture run:

- the counts of `r1` and `r5`, and each reason of `left_out`;
- the proposed name: `my-1`; the next free name when `my-1` is taken; `my-2` for the
  source set `my-1`;
- the rows of a new set: the copied columns, the notes, the excluded slugs, the variant
  groups, `source_dir`, `edited_at`, and `label_note`;
- the refusals: a run with no set, a dry run, an unknown run, a bad `misses`, a bad name,
  a taken name, and a selection with no photo to copy;
- `benchmark.build_queries` of the new set gives the copied photos.

A browser check opens `/runs`, creates a set from a fixture run, and reads the new set on
`/testset`.

## 10. Steps

1. Write this plan. Done.
2. Write `pipeline/testset_from_run.py`, the routes, and the tests. Done:
   `test_testset_from_run.py` 6 OK. `options.set` is read from `run.json` directly,
   because `run_files.test_set_of` is not committed yet (section of f4 [b39b7b]).
3. Change `runs.html` after the agreement of the sessions that list the file. Done: the
   owner allowed separate hunks at 09:24:00 (the section of f4 is stale), and CLUSTERS
   [fb59ad] agreed at about 09:27. 32 browser checks on a fixture server pass in the light
   and the dark theme.
4. Restart 8168 (rules 22 to 24 of `AGENTS.md`), and check the dialog on the live run of
   section 2. Done without a restart by this session: another session restarted 8168 at
   09:38:53, after the code of step 2 was on disk. The live dialog of that run shows 419
   and 144 photos and the name `my-1`. No set was made in the live database.
5. Update `README.md`, `docs/API.md`, `ChangeLog.md`, and `SMOKE_TESTS.md` (NT1 to NT12).
   Done.

## 11. Risks

- A label fix in the source set does not reach the new set, and a fix in the new set does
  not reach the source set. This is the rule of `vlmrerank-8b-failed` too.
- A run of the new set gives new query ids. Join it with the source run on `image_path`.
- The new set holds no negative photo. So `false match @1` of its runs is empty.
- A new seed of the database (`pipeline/seed_from_testset.py`) builds the three source
  sets alone. A set made from a run stays in the backup of the old database only.
  `export_testset.py` writes its JSON files, but no photo file, so an import cannot build
  it again from the export alone.

## Change note of 2026-09-26 (plan 51)

Plan 51 (owner answers of 2026-09-26T18:08:34+0300) dropped the tables `test_wine_note`
and `test_excluded`. Since then, `build` copies the comments of each copied photo
(`test_photo_comment`) and no notes of wines and no exclusions. The answer holds
`photo_comments` in the place of `wine_notes` and `excluded`. Session
drink-atlas-workspace-9e agreed to the change of its files at 18:12.
