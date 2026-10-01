# Workbench review and priority fixes

Date: 2026-10-01, Europe/Moscow.

The first priority is to preserve curated data and make benchmark results reliable.
The next priority is to prevent stale page state and unsafe local writes.
These changes give more immediate value than another model experiment or a large UI rewrite.
This is a Pareto ranking by expected impact and effort. The review does not measure an 80 percent benefit.

The review covers the current workbench working tree, including uncommitted code.
The recorded git revision is `603e22ec8e5e987e7728482536174abdba3af62e`.
Other sessions were active during the review.
The [source hashes](2026-10-01_workbench-pareto-evidence/source-sha256.json) identify the key files checked.
No product code, live database, or service configuration was changed.

## Do these fixes first

Effort is relative. Small means a local change with focused tests.
Medium means coordinated changes across several modules.
The estimate does not include a broad refactor.

| Order | Required fix | Main benefit | Effort | Earlier review |
|---|---|---|---|---|
| 1 | Preserve edits across test-set export and import. Add a backup before replacement. | Prevent loss of labels, moved photos, and uploaded photos. | Medium | W-4, confirmed again |
| 2 | Contain each benchmark query failure. Complete reports for sets with no positives. Show failed optional stages. | Preserve expensive run results and expose degraded pipelines. | Medium | W-7, W-8, W-9, confirmed again |
| 3 | Bind asynchronous page results and edits to the selected resource. | Prevent incorrect cluster edits and stale displays. | Small | W-17, confirmed again |
| 4 | Reject foreign-origin writes. Validate image formats and limits before decoding. | Protect local data and keep uploads from blocking the lab. | Medium | W-11, W-12, W-13; Atlas path also checked |
| 5 | Add a reproducible lab/test environment and a workbench CI job. Resolve service configuration consistently. | Detect regressions before shared code becomes active. | Medium | W-20, W-21, C-1; SAM3 behavior checked again |

### Preserve curated data

The export writes labels but no photo files.
The import reconstructs the photo list from the original directory.
It deletes the current test-set rows before inserting that list.
Therefore, export followed by `--force` is not a safe restoration of the edited set.

A temporary fixture reproduced this sequence:

1. Move a photo from `wine-a` to `wine-b` and label it positive.
2. Upload another photo through the test-set function.
3. Export the set into its source directory.
4. Import the same directory with `force=True`.

The photo count fell from 6 to 5.
The moved photo returned to `wine-a` with no label.
The uploaded photo lost its membership in the set.
The probe did not change the live database.

Evidence: `pipeline/export_testset.py:125`, `pipeline/import_testset.py:165`,
`pipeline/import_testset.py:293`, and [core probes](2026-10-01_workbench-pareto-evidence/core-probes.json).

Required fix: distinguish a labels-only export from a restorable set export.
A restorable export MUST contain the current photo membership and immutable image identities.
It MUST include or resolve every required image body.
A replacement MUST create a recoverable backup first.
Use the existing database export/restore tools where possible.
Do not build a second general backup system.

Acceptance: a round trip preserves uploaded photos, moved photos, labels, comments, and tags.
A failed replacement leaves the original set usable.

### Complete benchmark results when a query fails

`benchmark.one()` calls the backend without an exception boundary.
An unexpected `ValueError` stops the run before the final metadata is written.
The probe saved one result row but produced no `run.json`, `metrics.json`, or `summary.md`.
Partial result bytes remain on disk. The normal run metadata is absent.

A run limited to its first `__null__` photo also failed.
The summary formats an undefined F1 value as a number.
This case produced `run.json` and `metrics.json`, but no `summary.md`.

A barcode scanner failure is recorded in the step trace.
The embedding result can still return success with no top-level error.
The aggregate therefore does not identify a run whose barcode stage failed.

Evidence: `pipeline/benchmark.py:364`, `pipeline/benchmark.py:407`,
`pipeline/embedding_run.py:542`, `scripts/match_scoring.py:387`,
`pipeline/barcode.py:390`, and [core probes](2026-10-01_workbench-pareto-evidence/core-probes.json).

Required fix: record unexpected query exceptions as failed rows.
Write run metadata before processing starts.
Finalize the run with a completed, failed, or interrupted state.
Render an undefined F1 as unavailable.
Count scanner and reranker stage failures separately from final answer failures.
Reject a missing required endpoint before starting a run.

Acceptance: one malformed model answer does not erase the remaining evaluation.
A set with no positive queries produces a complete report.
A degraded pipeline is visible in the run list and summary.

### Keep page state consistent

`clusters.loadDetail()` writes its response into shared `DATA` without checking the request identity.
Changing index A to B starts another request.
If A finishes last, the page displays A while `NAME` is B.
The note handler builds its write URL from `NAME` and its cluster key from the displayed row.
This can send a note to B using a cluster displayed from A.

A controlled execution of the actual page function reproduced
`selected: B, displayed: A`.
The embedding page has the same unguarded pattern.
The test-set loader also accepts stale responses.

Evidence: `pipeline/pages/clusters.html:503`, `pipeline/pages/clusters.html:573`,
`pipeline/pages/embedding.html:425`, `pipeline/pages/testset.html:2697`,
and [UI probe](2026-10-01_workbench-pareto-evidence/ui-probe.json).

Required fix: capture the resource identity and a request generation before each load.
Apply a result only if both still match.
Bind writes to the resource that produced the displayed data.
Disable relevant writes while a different resource loads.

Also include every editable draft map in the Dataset unload guard.
The current guard omits names, GTINs, QR URLs, tags, and similar-wine edits
(`pipeline/pages/dataset.html:4751`).

Acceptance: delayed responses cannot replace a newer selection.
A note always reaches the displayed index and cluster.
Each unsaved draft type activates the unload guard.

### Protect local writes and image decoding

A temporary lab server accepted a JSON body with `Content-Type: text/plain`, a foreign
`Origin`, and `Sec-Fetch-Site: cross-site`.
It returned HTTP 200 and changed `wine_catalog.name_patched` in the temporary database.
This confirms the missing server-side boundary.
The review did not test browser-specific private-network restrictions.

Both upload validators decode the image before checking the format allowlist.
A small TIFF probe reached `Image.load()` before the validators rejected TIFF.
The test-set route performs this work inside `BEGIN IMMEDIATE`.
`imagestore` also disables the Pillow pixel guard for the entire process.

The new Atlas client reads each response without a byte limit.
Atlas orientation and format conversion can decode the image before `check_size()`.
The upload byte limit therefore does not bound download or conversion work on this path.
This path was traced in code. No large-image stress test was run.

Evidence: `pipeline/lab_server.py:1704`, `pipeline/lab_server.py:2017`,
`pipeline/patches.py:79`, `pipeline/testsets.py:776`,
`pipeline/testset_routes.py:183`, `pipeline/imagestore.py:19`,
`pipeline/atlas_import.py:141`, `pipeline/atlas_import.py:496`,
`pipeline/lab_server.py:679`, and the [HTTP probes](2026-10-01_workbench-pareto-evidence/http-probes.json).

Required fix: reject foreign origins and cross-site write requests at one handler boundary.
Require the expected media type for JSON routes.
Keep the loopback default.
Use an explicit image-format allowlist at open time.
Check dimensions before decoding.
Apply limits before Atlas conversion and while reading response bodies.
Decode images before taking a database write lock.

Acceptance: the foreign-origin probe is rejected without a database change.
Unsupported formats never reach a decoder.
Oversized images fail before allocation of the full pixel buffer.

### Make the regression suite reproducible

The repository CI file defines matcher and web UI jobs, but no workbench job.
The workbench imports `jsonschema` at module load, but its requirement file omits that package.
The requirement file also combines the light lab dependencies with the local GPU stack.
The configuration fixes the workspace path to this Mac.

The SAM3 client ignores the canonical `SAM3_ENDPOINT` environment variable.
A fresh Python process with a loopback test value still selected the configured GX10 address.
The default endpoint is resolved from the repository configuration at import time.
An alternative `--config` does not select that default.

Evidence: `../.gitlab-ci.yml`, `requirements-local.txt:16`,
`pipeline/describe_images.py:58`, `config.yaml:15`,
`config.yaml:45`, `pipeline/derive.py:60`, and `pipeline/derive.py:102`.

Required fix: declare the lab and test dependencies separately from local inference dependencies.
Provide one executable test command and run it in GitLab.
Include tests for the failures above.
Use portable database paths.
Read `SAM3_ENDPOINT` as the canonical environment variable.
Resolve the effective configuration once and pass it to clients and child jobs.

Acceptance: a fresh environment can import the lab and run the offline suite without
unlisted packages, undeclared sibling repositories, or a GPU.
The documented SAM3 override changes the actual client endpoint.

## Improvements to do next

### Label results that reuse earlier answers

This is a new reporting gap in `Repeat last failed`.
The merged-run behavior follows the owner's approved plan 96.
Do not remove that behavior.

The probe created a run with 3 copied answers and 1 new answer.
`run.json` recorded `repeat_of` correctly.
The run-list record omitted that field, and the summary did not mention the reuse.
The current repeat badge reads the older `subset` mechanism instead.
The result appears to be a fresh measurement of the current pipeline.

Fix: show an explicit reused-results badge and the copied/asked counts in the list and summary.
Show the source run and the mixed latency provenance.
Require a fresh full run for a published comparison after pipeline changes.

Evidence: `pipeline/benchmark.py:210`, `pipeline/benchmark.py:353`,
`pipeline/run_files.py:118`, `pipeline/pages/runs.html:625`,
`scripts/match_scoring.py:348`, and [repeat probe](2026-10-01_workbench-pareto-evidence/repeat-probe.json).
Effort: small.

### Add an evaluation integrity check

The read-only database check found 7 exact-byte test/catalogue join rows.
Six refer to Disabled wines. One refers to a Removed wine.
None refers to an Active wine.
These are join rows, not necessarily distinct photos.
The review found no current exact-byte overlap with the Active catalogue.
It did not check perceptual duplicates or prove independence from tuning.

Add an exact-byte overlap check before a benchmark.
Check both directions when adding catalogue images and test photos.
Keep a frozen evaluation set separate from sets used for tuning.
Record dataset and effective pipeline identities with published results.
The catalogue copy also retains the complete test tables because it copies the database
without removing them (`pipeline/catalog_copy.py:165`).
Exclude test labels from a deployment copy when the consumer does not require them.
The presence of these tables alone does not prove that the matcher uses the labels.

Earlier findings: W-1, W-2, W-3. Effort: medium.

### Correct the documentation entry point

The README still starts with paths such as `eval/`, `my/`, and `excluded-slugs.json`
that do not describe the current workbench tree.
The configuration header still describes the old test-set builder.

Correct the README opening and the configuration header first.
Add a short setup path that names the interpreter, required environment variables,
database restoration, and test command.
Link the existing detailed material instead of rewriting every document.
Move legacy-tool guidance behind an explicit legacy link in a later pass.

Earlier findings: W-25, W-26, W-28, W-29. Effort: small for the entry-point correction.

## Defer broad changes

- Keep the shared prepared-image cache as known deferred work: `FIX_LATER.md`, item 1.
- Do not present matcher `KNOWN_ISSUES.md` items 1 to 3 as new workbench findings.
- Defer a framework migration, a full page rewrite, and general module splitting.
- Defer large documentation archives and repository-storage migration until the core fixes are complete.
- Do not add more model experiments as a substitute for reliable run evidence.
- A smaller new validation defect can wait: a list in the photo-move `from` field
  returns HTTP 500. Validate `from` and `to` as strings before constructing the set
  (`pipeline/photo_moves.py:78`). Return HTTP 400 for this input.

## Validation

Command: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests`.
Interpreter: `/opt/homebrew/bin/python3`, Python 3.14.7.
Result: 1,585 tests ran in 230.611 seconds. The suite passed with 1 skipped test.
The skipped test requires `zxingcpp`.
Resource warnings from test fixtures remain. This run did not treat them as errors.

The initial sandbox run blocked local socket binding and process inspection.
That run is not evidence of a product regression.
The complete rerun used local socket access and passed.
Current remote GitLab pipeline status was not checked.
The CI finding concerns the checked-in job definitions.

The probes used temporary databases, fake backends, and temporary HTTP servers.
The image probe used a 2 by 2 TIFF.
The UI probe executed the actual cluster load function with controlled response order.
It was a function-level check, not a visual browser test.
The live database was opened read-only for counts and overlap checks.
No live model benchmark or service restart was required.

The earlier review is
[the three-project review from September 30](2026-09-30_three-project-review.md).
This report confirms selected findings against current code.
It does not repeat every lower-impact item from that report.
