# Competitor audit additions

The workbench queue is at `/production-errors`. The Dataset page has a link.
The queue stores request evidence and review history in schema 034.
The queue does not turn feedback into an identity label.

## Reviewed request import

Run these commands from the workbench root. The bot database and image root MUST be
local snapshots. The adapter opens the bot database read-only. The adapter imports
safe requests with negative feedback. The adapter removes user identity fields.
The command writes the workbench queue and its local quarantine image directory.

```sh
python3 pipeline/production_errors.py --db data/catalog/catalog.sqlite3 \
  --bot-db /absolute/path/to/bot.sqlite3 --image-root /absolute/path/to/bot-images
```

The page also imports one JSON snapshot. The snapshot holds `source`, `request_id`,
`image_sha256`, `candidates`, `feedback`, and `image_base64`.
Each candidate holds its original `slug`, `rank`, and `score`.
`feedback.selected_slug` is observed feedback. It is not a reviewed identity.
The snapshot image MUST be at most 10 MiB. The JSON MUST be at most 14 MiB.

An operator assigns an active catalog slug, a purpose, a reviewer, and a review note.
An explicit null identity can become a benchmark No Match photo only.
A reference needs a resolved catalog identity and an explicit image type.
Publication uses the existing test-set or reference tables. A reference requires the
existing embedding build before retrieval uses it. Publication does not rebuild an index.
The queue rejects a reference/benchmark overlap for the source and its linked exact
processed images. Published provenance is immutable. Publication is idempotent.
This check cannot detect an unlinked near duplicate. An operator MUST check that case.

## Read-only checks

```sh
python3 -m unittest discover -s tests -p 'test_production_error*.py' -q
python3 -m unittest discover -s tests -p 'test_audit_benchmark.py' -q
```

The tests use temporary databases. They verify review requirements, explicit No Match,
publication, identity conflicts, exact derivative separation, routes, and rollback.

## Recognition experiment

This command calls DINOv3, SigLIP2, SAM3, the QR scanner, and Qwen on the configured LAN
gateway. It sends frozen benchmark image copies. The current session requires the
owner's explicit transfer approval before this command runs outside the sandbox.
Use a new output directory after a benchmark script, reference, or input change.

```sh
OPENBLAS_NUM_THREADS=1 python3 scripts/benchmark_audit.py \
  --output ../internal/competitor-implementation-2026-10-06-benchmark-approved
```

The command does not train a model or rebuild an index. It compares the existing
ArcFace projection with base DINOv3 using the same query features and reference rows.
It runs the existing `cascade-p512-rot5` matcher code with a 9.5-second hard deadline.
The matcher mode is candidate matching. This experiment does not measure the public
prediction endpoint's earlier answer deadline.
The copies have timestamps before the submission cutoff. Original files keep their
bytes and timestamps. SHA-256 binds the query labels, model artifact, reference vectors,
identity mapping, script, and selected cascade configuration to the results.
Exact source families in training or catalog references are excluded. Unknown near
duplicates can remain. Identity groups stay in one calibration or test split.

The fixed baseline uses score 0.70 and margin 0.015. The conservative comparison keeps
that gate and rejects contradictory, unsure, or failed verification evidence.
The comparison never assigns `not_in_catalog` from uncertainty. It fits no learned gate.
The report measures accepted precision, coverage, false acceptance, correct predictions
rejected by the gate, known photos rejected, retrieval recall, and latency.
Recognition errors, absent wines, unreadable photos, and candidate-window misses stay
separate in the evidence. A benchmark failure is not a recognition improvement.

## Web checks and performance

These commands use the web project. The tests can create loopback HTTP servers.
The ranking benchmark writes a report under `internal`.

```sh
(cd ../webui && npm test && npm run typecheck)
(cd ../webui && ./node_modules/.bin/esbuild scripts/benchmark-recommendations.ts \
  --bundle --platform=node --format=esm --alias:#shared=./shared \
  --outfile=/private/tmp/wine-recommendation-benchmark.mjs)
node /private/tmp/wine-recommendation-benchmark.mjs \
  ../internal/competitor-implementation-2026-10-06-ranking.json
```

Build the web project before the browser check. Set `PLAYWRIGHT_MODULE` to the local
Playwright `index.mjs`. The check starts an isolated loopback preview and health stub.
Recognition and metadata responses in this check are fixtures. The image is generated.
The check blocks external HTTPS requests. It sends no benchmark photos to model services.

```sh
(cd ../webui && npm run build)
(cd ../webui && PLAYWRIGHT_MODULE=/absolute/path/to/playwright/index.mjs \
  node scripts/check-collection-browser.mjs)
```

The browser check verifies actual IndexedDB storage, favorites, personal ratings,
offline saved-card reload, clearing, shelf preference reuse, and duplicate positions.
The ranking timings exclude network metadata hydration and recognition.

The local projection microbenchmark sends no service requests. It measures the existing
1024D-to-512D projection on cached index rows. The cache can include stale rows.
This performance check does not measure real-photo accuracy.

```sh
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python3 scripts/benchmark_audit.py \
  --offline-projection --output ../internal/competitor-implementation-2026-10-06-benchmark
```

Use `--prepare-only` with the approved-output path to freeze the current inputs without
service calls. The later approved run uses that same manifest and script hash.

After this frozen run completes, validate the query hashes and calculate paired,
per-set, and acceptance summaries with this local script. It sends no service requests.

```sh
OPENBLAS_NUM_THREADS=1 python3 \
  ../internal/competitor-implementation-2026-10-06-benchmark-approved/analyze_results.py
```

The current frozen cohort has 156 known-identity photos and 6 unusable photos. It has
no confirmed absent-wine photos. It cannot measure absent-wine false acceptance.

## Further competitor comparisons (2026-10-06)

These are local architecture adaptations, not competitor-trained model reproductions.
The matrix uses the same 162 frozen photos and existing indexes. It never invokes
the index rebuild path. The owner requested this benchmark on 2026-10-06.
Run commands from the workbench root with the local virtual environment that has
NumPy, Pillow, PyYAML, requests and rapidfuzz. Tesseract must be installed at
`/opt/homebrew/bin/tesseract` with `rus` and `eng` languages for the crop experiment.

Read-only scoring checks:

```sh
OPENBLAS_NUM_THREADS=1 /Users/ashmelev/.venvs/svoe-vino-lab/bin/python \
  -m unittest discover -s tests -p 'test_competitor_*.py'
```

Prepare the visual/OCR matrix without network calls:

```sh
OPENBLAS_NUM_THREADS=1 /Users/ashmelev/.venvs/svoe-vino-lab/bin/python \
  scripts/benchmark_competitor_followup.py --prepare-only \
  --output ../internal/competitor-followup-2026-10-06/matrix
```

Run the matrix through the LAN gateway. It sends dated copies of the previously
approved query photos. Run live phases sequentially so model contention does not
alter their comparison unnecessarily. Service caches remain enabled.

```sh
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
  /Users/ashmelev/.venvs/svoe-vino-lab/bin/python \
  scripts/benchmark_competitor_followup.py \
  --output ../internal/competitor-followup-2026-10-06/matrix
```

The local cached phase performs fixed equal-weight reciprocal-rank fusion, selective
cropped-label OCR and global text proposals. It sends no service requests. Its
correctness logistic probe trains only on the original 40-photo calibration split.
The threshold uses leave-one-wine-group-out calibration predictions; the 122-photo
test split does not choose weights or thresholds. OCR is bounded by the measured
remaining cascade budget. Cached composition is not integrated end-to-end timing.

```sh
OPENBLAS_NUM_THREADS=1 /Users/ashmelev/.venvs/svoe-vino-lab/bin/python \
  scripts/benchmark_competitor_experiments.py cached
```

The archived public cohort is a local review overlay: 50 positive photos and 18
locally reviewed absent photos. Six historical negatives now have current/potential
matches, and three are ambiguous. Those nine are excluded. Database and archived
labels remain unchanged. Repeated photos of one absent product stay in one split.
This is a public development cohort, not unseen gold evidence. Only four absent
photos enter calibration, so the membership logistic probe is exploratory.

The following two phases call the LAN gateway. Prepare their inputs without requests
with `scripts/benchmark_competitor_experiments.py archive --prepare-only` and
`scripts/benchmark_competitor_experiments.py verify --prepare-only`; the archive
adapter below is for the live run. The archive phase compares visual retrieval, structured OCR, fixed Qacen
rejection and the cascade. The verifier phase compares a 4B model with seven front
reference images against the cached cascade, preserving the original answer on
errors, late answers, `other` or `unsure`. Strong existing supported/unique-code
evidence suppresses the additional verifier. The implementation uses JSON choices;
it does not reproduce Egorov's original log-probability fusion.

```sh
OPENBLAS_NUM_THREADS=1 /Users/ashmelev/.venvs/svoe-vino-lab/bin/python \
  ../internal/competitor-followup-2026-10-06/run_archive.py
OPENBLAS_NUM_THREADS=1 /Users/ashmelev/.venvs/svoe-vino-lab/bin/python \
  scripts/benchmark_competitor_experiments.py verify
```

After all phases finish, this read-only analysis validates all result counts, query
hashes, frozen scripts, and identity split separation. It scores selective full-photo
OCR by composing the already completed matrix and cascade results. That variant has
no live integrated latency measurement.

```sh
OPENBLAS_NUM_THREADS=1 /Users/ashmelev/.venvs/svoe-vino-lab/bin/python \
  ../internal/competitor-followup-2026-10-06/analyze.py
```

The dated follow-up runner writes its outputs only to the directory shown above.
Existing results resume only with unchanged frozen inputs and code. Preserve these
artifacts and use a separate runner/output location for a changed experiment.

All four follow-up phases finished: 1,782 matrix answers, 162 cached experiment rows,
68 archived-cohort rows and 162 verifier rows (59 live reference requests).
The matrix and archive recorded zero service errors; three reference-verifier read
timeouts retained the cascade answer. The owner explicitly approved the
68-query and up-to-279-reference payloads for the same LAN gateway at
2026-10-06T10:06:06+03:00; the earlier automatic-review rejection is resolved.
The archived phase uses `run_archive.py` because the prepared runner passed the outer
matcher object instead of its `.cascade` executor. The first attempt stopped before
any complete query result. The repair is separately hash-bound in
`archive-runner-repair.json`; the original frozen experiment script stays unchanged.
The aborted log is preserved in `aborted-archive-attempt.log`. If resuming after local
temporary logs were cleared, restore that exact log to
`/private/tmp/competitor-archive.log` before running the adapter.

The final results and limitations are in
`internal/competitor-followup-2026-10-06.md` at the repository root. Generate it from
the validated evidence with this local command:

```sh
/Users/ashmelev/.venvs/svoe-vino-lab/bin/python \
  ../internal/competitor-followup-2026-10-06/write_report.py
```

This optional local audit preserves TSV word confidence and crop coordinates; it
does not change ranking or send requests. It finished for all 59 triggered labels.

```sh
OPENBLAS_NUM_THREADS=1 /Users/ashmelev/.venvs/svoe-vino-lab/bin/python \
  ../internal/competitor-followup-2026-10-06/ocr_word_evidence.py
```
