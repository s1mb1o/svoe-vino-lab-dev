# Pareto audit of `svoe-vino-lab`

Date: 2026-09-25.
Scope: the current shared worktree and `data/lab.sqlite3` at schema version 17.
Method: read the architecture, run the full unit test suite, run Ruff, inspect the live
database, and inspect the current Git state.

This review separates structural risks from temporary worktree risks. Many sessions are
changing the project at the same time. The current worktree is not a release snapshot.

## Result

The project has good local safety mechanisms. It has strict SQLite tables, foreign key
checks, content-addressed image files, atomic file writes, resumable embedding builds,
model-call caches, and many tests.

The main risks are not inside one algorithm. The main risks are data ownership, data
isolation, and experiment provenance. Five improvements can remove most of the present
risk:

1. Finish the declared SQLite migration and remove legacy write paths.
2. Back up SQLite and every referenced content-addressed file.
3. Separate the canonical database from development and smoke-test databases.
4. Give each model artifact and each experiment a stable revision.
5. Add one integration gate for every commit.

## Architecture

The project has two generations of the laboratory.

### Declared target architecture

The owner defined the target on 2026-09-25.

1. SQLite is the only source of truth for mutable domain data and relations.
2. SQLite stores catalogue data, image metadata, labels, test sets, codes, bindings,
   comments, favorites, exclusions, and review decisions.
3. Mutable cluster and rule data also moves to SQLite.
4. Image bytes stay in the content-addressed image store. SQLite stores their hashes,
   metadata, and relations.
5. Embedding artifacts stay in files. These artifacts include `index.json`, vector
   arrays, prepared images, and build logs.
6. Run artifacts stay in immutable directories under `runs/`.
7. A technical cache is disposable. It MUST NOT become a source of truth.
8. Configuration files stay configuration files. They MUST NOT contain mutable domain
   state.

The legacy generation is a migration source. It is not part of the target architecture.

### Legacy generation

1. `scripts/01_search.py` finds candidate images.
2. `scripts/02_download.py` downloads the candidates.
3. `scripts/03_embed.py` calculates similarity.
4. `scripts/04_verify.py` asks a VLM to verify a candidate.
5. `scripts/05_report.py` writes the selected dataset.
6. `work/state.db` stores the resumable pipeline state.
7. `scripts/review_server.py` edits JSON files and filesystem directories.
8. `scripts/match_run.py` sends test photos to matcher backends.
9. Each run is a directory under `runs/`.

### SQLite generation

1. The files in `pipeline/schema/` define `data/lab.sqlite3`.
2. `pipeline/import_catalog.py` and `pipeline/import_website.py` import catalogue data.
3. `pipeline/import_testsets.py` imports test sets.
4. `pipeline/seed_*.py` imports images, codes, bindings, and derived data.
5. `data/images/` is a content-addressed image store.
6. `pipeline/derive.py` makes package and label cuts with local rules and SAM3.
7. `pipeline/lab_server.py` serves the Dataset page and dispatches other route modules.
8. `pipeline/build_embeddings.py` prepares model inputs and writes vectors and an index.
9. `pipeline/benchmark.py` reads a test set from SQLite and writes a run directory.
10. The Runs page reads run files. The database does not store runs.

### External services

1. The project calls the matcher through HTTP backends from `backends.yaml`.
2. It calls embedding models through an OpenAI-compatible endpoint.
3. It calls SAM3 and Grounding DINO through the gx10 gateway.
4. It calls the vino-svoe.ru API for the website import.

## Verified strengths

1. `PRAGMA integrity_check` returned `ok`.
2. `PRAGMA foreign_key_check` returned no row.
3. The full suite ran 445 tests in 71.9 seconds and returned `OK`.
4. The image store had 9,522 files and the `image` table had 9,522 rows.
5. Image writes use a temporary file and `os.replace`.
6. Existing image bytes are checked against the SHA-256 in the file name.
7. Slow SAM3 work runs before the SQLite write transaction in patch and alternative
   writes.
8. Embedding checkpoints write the vector file before the index that names it.
9. Each benchmark query records the SHA-256 of its source photo.
10. Model cache writes are atomic and store successful calls alone.

## Pareto findings

### P0. The canonical data has no complete durability path

Evidence:

1. Git ignores the complete `data/` directory.
2. The database is now the source of truth for patches and several other edits.
3. The database holds manual wines, manual bindings, comments, favorites, and refusals.
4. Some of these values have no export.
5. The plan still keeps the export question open.
6. The database was 7.1 MiB. The complete `data/` directory was 4.3 GiB.

Impact:

1. A disk failure can remove human work.
2. Git cannot show a reviewable history of the human work.
3. A database rebuild cannot restore all state.
4. A database backup alone does not restore the image store.

Recommended improvement:

1. Define `data/lab.sqlite3` as the canonical metadata source.
2. Add a manifest for every content-addressed file that the database references.
3. Make one command create a consistent SQLite backup and image manifest.
4. Make another command verify and restore the backup.
5. Put backup metadata and bulk backup data in approved durable storage.
6. Generate text exports only for interchange, inspection, or audit.
7. Do not use a generated export as a second source of truth.

Benefits:

1. Human work becomes recoverable.
2. A database rebuild becomes deterministic.
3. The project gets a clear source-of-truth rule.

Costs and risks:

1. The backup format needs schema versioning.
2. Restore tests need representative image data.
3. A backup of the full image store needs storage and retention rules.

### P0. Development data contaminates the canonical database

Evidence from the live database:

1. One active manual wine has the slug `__wqeqwe` and test-like text.
2. One user comment contains `Tes`.
3. Three manual alternative images belong to
   `avtohtonnoe-vino-kryma-beloe-suhoe`.
4. The same three image bytes are positive test photos for three different wines.
5. These exact overlaps are eligible for the `my` benchmark.
6. The lab validation API is still disabled.
7. The project research log already records duplicate and label-quality problems.

Impact:

1. An embedding index can contain an image under the wrong wine.
2. A benchmark can read a test image that also exists in the catalogue image set.
3. A metric can improve because of leakage.
4. A metric can become worse because of a wrong catalogue assignment.
5. A smoke test can change the data that a later experiment uses.

Recommended improvement:

1. Create explicit `canonical`, `development`, and `test` profiles.
2. Never run UI smoke tests against the canonical database.
3. Add a promotion command for reviewed changes from development to canonical data.
4. Add a blocking data audit before an embedding build and before a benchmark.
5. Reject an exact test-to-catalogue overlap unless an allowlist explains it.
6. Detect a test image that is assigned to a different catalogue wine.
7. Restore the near-duplicate and label checks before the new Testset page becomes the
   only tool.

Benefits:

1. Metrics become credible.
2. UI development cannot silently change an experiment.
3. Data errors fail early.

Costs and risks:

1. Three profiles add configuration and storage.
2. Promotion needs conflict rules.
3. Near-duplicate checks add compute time and need threshold maintenance.

### P0. The migration to the declared SQLite target is incomplete

Evidence:

1. `scripts/review_server.py` is 10,980 lines and edits legacy JSON files.
2. `pipeline/lab_server.py` serves the SQLite laboratory.
3. The Dataset page contains compatibility code for both servers.
4. The SQLite server still disables Clusters, Testset, validation, and old API routes.
5. Lab codes do not automatically reach `svoe-vino-matcher`.
6. Lab Atlas bindings do not automatically reach the review tool.
7. Test labels can exist in JSON and in SQLite.
8. Cluster and rule data remains in files outside SQLite.
9. Runs remain files by design. They are not migration debt.
10. Embedding indexes and vectors remain files by design. They are not migration debt.

Impact:

1. A legacy write can stay invisible in a SQLite consumer.
2. The same business rule has more than one implementation.
3. A shared HTML page contains conditional behavior for incompatible APIs.
4. Remaining JSON writes can recreate a second source of truth.

Recommended improvement:

1. Inventory every JSON file that contains domain state.
2. Classify only embedding artifacts and run artifacts as supported JSON data.
3. Freeze new features and new writes in the legacy server.
4. Port validation and Testset editing to SQLite first.
5. Define SQLite tables for mutable cluster and rule data before the Clusters port.
6. Import each remaining domain JSON file once and record the import result.
7. Add generated exports for the matcher and other consumers when they cannot read
   SQLite directly.
8. Remove legacy write paths after parity tests pass.
9. Keep a read-only legacy viewer for a short transition period if necessary.

Benefits:

1. The project gets one authoritative data model and one write path.
2. The code loses the largest monolith and many compatibility branches.
3. Runs and embeddings stay portable without duplicating mutable domain state.
4. A change becomes visible to every consumer through SQLite or a generated export.

Costs and risks:

1. The migration is substantial.
2. Feature work must slow during the cutover.
3. A parity suite must cover the old validation and review behavior.
4. Generated exports need clear ownership and invalidation rules.

### P0. Model outputs and experiments do not name a stable model artifact

Evidence:

1. The embedding item hash includes the model name and options.
2. It deliberately excludes `base_url`.
3. It does not include a checkpoint digest or server revision.
4. Pixel-processing code uses a manually incremented `STEPS_VERSION`.
5. The model cache key includes the endpoint and served model name.
6. It does not include a checkpoint digest or deployment revision.
7. A benchmark stores the short Git commit.
8. It does not store the dirty-tree state or a source-tree digest.
9. It stores the database path. It does not store a database snapshot digest.
10. The current tree has 48 changed tracked files and 63 untracked files.

Impact:

1. A model can change behind the same name and reuse old vectors or cached answers.
2. A code change can produce a run that has the commit of older code.
3. Two runs can look comparable while they use different unrecorded state.
4. An old result can be impossible to reproduce.

Recommended improvement:

1. Add a required `model_revision` or `artifact_sha256` to each model configuration.
2. Put that value in embedding hashes and model-cache keys.
3. Record the gateway software version and model artifact revision in each index.
4. Record the Git commit and the dirty-tree patch digest in each run.
5. Record hashes of the effective config, the schema files, the test rows, and the
   relevant database snapshot.
6. Replace the manual `STEPS_VERSION` rule with a code version or an explicit pipeline
   revision that changes in review.

Benefits:

1. Cache reuse becomes safe.
2. A/B comparisons become defensible.
3. A result can be traced to exact inputs and code.

Costs and risks:

1. Correct invalidation causes more rebuilds.
2. The gateway must expose or accept a stable model revision.
3. Dirty-tree recording adds metadata and can expose local paths if redaction is absent.

### P0. The project has no automated integration gate

Evidence:

1. The repository has no CI configuration.
2. The dependency file uses lower bounds and has no lock file.
3. Ruff reports 40 findings.
4. The tests pass, but they emitted resource warnings for unclosed resources.
5. The shared worktree is eight commits ahead of `origin/main`.
6. The shared worktree has 111 changed or untracked paths.

Recommended improvement:

1. Add one command that runs schema migration tests, unit tests, Ruff, and the data
   contract checks.
2. Run the command in CI and before a shared-tree checkpoint commit.
3. Split dependencies into a small server set and a pinned ML set.
4. Generate a lock file for each supported Python version and platform.
5. Make benchmark creation refuse a dirty tree by default.
6. Permit a dirty run only with an explicit option that records the patch digest.

Benefits:

1. Integration errors stop before they enter the shared tree.
2. Environment rebuilds become repeatable.
3. Parallel sessions get a common definition of done.

Costs and risks:

1. ML dependencies make CI large.
2. macOS and local-model tests need a separate optional job.
3. A strict dirty-tree rule can slow exploratory work.

## Second-wave improvements

### P1. Enforce the canonical service configuration

The code hard-codes the SAM3 endpoint. The workspace rule requires `SAM3_ENDPOINT`.
The code also hard-codes the gx10 gateway and an old dataset path.

Improvement:

1. Read SAM3 from `SAM3_ENDPOINT`.
2. Put the other service bases in one checked configuration object.
3. Keep stable defaults only where the workspace rules permit them.
4. Add startup diagnostics that show redacted effective configuration.

Benefit: the same code can run on another host without source edits.

Cost: tests and commands must provide explicit configuration.

### P1. Add checksums to the migration ledger

`PRAGMA user_version` records a number alone. A changed applied SQL file is skipped.

Improvement:

1. Add a migration ledger with the number, file name, SHA-256, and applied time.
2. Compare each applied checksum at every open.
3. Refuse a mismatch.

Benefit: accidental edits of an applied migration become visible.

Cost: the current database needs one trusted baseline entry for each applied file.

### P1. Split the large server and page modules

`pipeline/lab_server.py` is 1,064 lines. `pipeline/pages/dataset.html` is 2,581 lines.
`scripts/review_server.py` is 10,980 lines.

Improvement:

1. Move Dataset read models and each write route into small modules.
2. Split the Dataset JavaScript by feature.
3. Remove shared legacy branches after the legacy server becomes read-only.

Benefit: changes have a smaller collision area for parallel sessions.

Cost: this refactor has limited direct user value until the dual-system migration starts.

### P1. Add a safe remote-access boundary

The server binds to `127.0.0.1` by default. The `--host` option can expose it without
authentication. The API can change the database, start and stop builds, start imports,
and open a Finder directory.

Improvement:

1. Refuse a non-loopback host unless authentication is configured.
2. Add an origin check and a CSRF token for write routes.
3. Separate process-control routes from ordinary data routes.

Benefit: an accidental LAN bind cannot expose destructive controls.

Cost: remote use needs a token or a trusted proxy.

### P2. Add pagination or virtualization to the Dataset page

The current `/api/dataset` response has 2,104 records and is approximately 3.1 MiB.
The browser renders every visible record into one HTML string. A code comment records
about 0.7 seconds for a full render.

Improvement:

1. Keep client-side search if the current size stays stable.
2. Add virtual rendering first.
3. Add server pagination only when the dataset grows or remote use starts.

Benefit: the page stays responsive as the catalogue grows.

Cost: virtual navigation and image-preview order need more state management.

### P2. Add SQLite operational settings and health checks

The server uses one connection per request and a threaded HTTP server. SQLite uses the
default journal mode and timeout. The current workload is small, and model calls run
outside write transactions.

Improvement:

1. Set and document a busy timeout.
2. Measure WAL mode before enabling it.
3. Add a health report for schema, foreign keys, missing files, orphan files, and active
   jobs.

Benefit: concurrent writes fail less often and operational defects become visible.

Cost: WAL adds side files and changes backup procedures.

## Recommended order

1. Stop canonical database mutation by smoke tests.
2. Back up the database and image store.
3. Remove or quarantine the verified test rows after owner review.
4. Add the blocking data audit.
5. Inventory all domain JSON and define its target SQLite tables.
6. Port validation, Testset editing, clusters, and rules to SQLite.
7. Import remaining domain JSON once.
8. Freeze and then remove legacy write paths.
9. Add model and run revision metadata.
10. Add the integration gate.
11. Apply the P1 and P2 improvements after the data contracts are stable.

## Verification evidence

Commands used:

```text
python3 -m unittest discover -s tests
ruff check pipeline scripts tests --statistics
sqlite3 -readonly data/lab.sqlite3 'PRAGMA integrity_check;'
sqlite3 -readonly data/lab.sqlite3 'PRAGMA foreign_key_check;'
git status --short
```

Results:

1. Unit tests: 445 passed.
2. Ruff: 40 findings.
3. SQLite integrity: `ok`.
4. Foreign key problems: 0.
5. Schema version: 17.
6. Catalogue: 2,104 wines.
7. Test photos: 4,323 rows in 3 sets.
8. Image files: 9,522.
9. Git status: 48 changed tracked files and 63 untracked files.
