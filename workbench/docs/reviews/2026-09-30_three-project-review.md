# Review of `matcher`, `matcher-inspector`, and `workbench`

- Date: 2026-09-30.
- Session: `drink-atlas-workspace-5e [fc9c7d]`.
- Source: owner message of 2026-09-30T00:16:49+0100.
- Code state: git `HEAD` `b533473`. The review changed no code.

## 1. Scope and method

This review is read-only. It changed no code, it restarted no service, and it sent no
request to a live service. One exception: the review read the pipeline list of the home
GitLab through its API.

Eight reviewers read the code and the documents in parallel. Each reviewer had one
scope: matcher code; matcher documents, CI, and deployment; the lab server; the
embedding and benchmark pipeline; data import; the browser pages; scripts and tests; the
workbench documents. The lab server scope had a second pass, because the first report
was cut off. The lead session checked each high and medium finding before it went into
this report.

| Check | Result |
|---|---|
| Matcher tests: `~/.venvs/svoe-vino-lab/bin/python -W error::ResourceWarning -m unittest discover -s matcher/tests` | 213 tests OK, no skip, 82 s. |
| Matcher Inspector tests: `python3 -m unittest discover -s matcher-inspector/tests` | 7 tests OK. |
| Workbench tests: `python3 -m unittest discover -s tests` in `workbench/` | 1,477 tests OK, 1 skipped, 218 s. About 100 `ResourceWarning: unclosed database` lines come from three test files (W-24). |
| `ruff check` with the default rules | `matcher/` and `matcher-inspector/`: no finding. `workbench/`: 82 findings, most of them style. The 3 `F821` findings in `pipeline/describe_images.py` are false positives: `write()` calls the lambda inside the `except` block. |
| GitLab pipelines of `drink-atlas/svoe-vino-lab` | The last 6 pipelines on `main` failed. See C-1. |
| Probes | Only temporary files in the scratchpad of the session. Each finding names its probe. |

Known problems are not reported as new problems (rules 39 to 42 of
[../../AGENTS.md](../../AGENTS.md)). These are `FIX_LATER.md` item 1 and
[matcher KNOWN_ISSUES](../../../matcher/docs/KNOWN_ISSUES.md) items 1 to 3.
Two earlier documents also report some problems:
[the matcher code review of 2026-09-29](../../../matcher/docs/reports/2026-09-29_code-review.md)
and [the security audit of 2026-09-29](../../../docs/security-audit-2026-09-29.md).
This report names their items where a finding touches them. The security audit did not
cover the lab server.

Terms:

- "Verified": a reviewer traced the code path completely, or a probe reproduced the effect.
- "Plausible": the code path exists, but nobody reproduced the effect.
- "Lead check": what the lead session did to confirm the finding.

## 2. Summary

| Project | State | Main risks |
|---|---|---|
| `matcher` | Good code. Strong tests: 213 hermetic tests, real uvicorn processes, fakes of each service. Detailed documents. | Edge cases that give HTTP 500. A configuration typo that switches off authorization. The request archive on the request path. A SAM3 filter that differs from the lab. CI that does not use the lock file. |
| `matcher-inspector` | Small and safe: confined paths, escaped output, a strict Content Security Policy, a read-only mount, a non-root user. | The main page reads every journal of the archive. No CI. |
| `workbench` | Large and capable: 24,700 lines of Python in `pipeline/`, 600 KB of pages, 1,477 tests. The tests are hermetic almost everywhere. All SQL is parameterized, and no subprocess uses a shell. | No guard between the test sets and the catalogue. Tools that lose curated data. Benchmark runs that crash or degrade with no signal. Upload checks that decode every image format. Errors that close the connection with no HTTP answer. No protection of the local server against other web pages. Very large documents that drift from the code. |

## 3. Priority list

The list gives the order that the review recommends. Section 8 groups the work.

| # | ID | Severity | Finding |
|---|---|---|---|
| 1 | W-1 | high | No guard between test photos and catalogue images. Three links exist now. |
| 2 | W-11 | high | The lab upload checks decode every Pillow format, EPS through Ghostscript, inside a write transaction. |
| 3 | C-1 | high | The only CI is red for 6 pushes. No CI runs the 1,477 workbench tests. |
| 4 | M-1 | medium | A JPEG with a damaged EXIF block gives HTTP 500 on the three prod image routes. |
| 5 | M-2 | medium | A failed archive write gives HTTP 500 for every request, while `/readyz` stays 200. |
| 6 | M-3 | medium | An unknown key in `matcher:` loads with no error. A typo can switch off the token or the time budget. |
| 7 | W-3 | medium | The official set and `test-1` were used for tuning. The documents do not say so. |
| 8 | M-4 | medium | Prod ignores SAM3 packages and hands below 0.4 and sends SAM3 another image than the lab. |
| 9 | W-2 | medium | The catalogue copy for the matcher holds the test tables with the true labels. |
| 10 | W-4 | medium | Four tool paths lose curated test-set or patch data with no backup. |
| 11 | W-7, W-8, W-9 | medium | A benchmark run crashes with no positives, aborts on one bad SAM3 mask, or silently drops the barcode step. |
| 12 | W-13, W-14, W-15 | medium | The lab server: the Pillow bomb guard is off, the URL fetch check is not bound to the connection, and many errors close the connection with no HTTP answer. |
| 13 | M-5, M-6 | medium | Cascade `/v1/match` can return 1 candidate for `k=20`, or an empty list. |
| 14 | M-8 | medium | The documented archive path `work/matcher-requests` is not ignored by git. |
| 15 | W-12 | medium | Any web page in the browser of the owner can send write requests to the lab server. |
| 16 | W-25, W-26, W-28 | high/medium | The workbench README starts with the layout of another project. The configuration reference describes the wrong file. No setup or test guide exists. |

## 4. `matcher`

Prod on gx10 runs the pipeline `cascade-p512-rot5` with `fast_answer` 2.8 s / 9.5 s since
2026-09-29 18:00 (`<workspace>/deploy/gx10/matcher-prod.md`). Each cascade finding
affects prod.

### 4.1 Defects

**M-1. A JPEG with a damaged EXIF block gives HTTP 500.**

- Severity: medium. Status: verified. Lead check: `validate_image` accepted the sample
  file of the reviewer, and `photo.decode` raised `struct.error`.
- Location: `photo.py:53-61`, `group.py:163-171`, `app.py:333-352`.
- Problem: `photo.decode` catches `OSError`, `SyntaxError`, and `ValueError`.
  `ImageOps.exif_transpose` writes the EXIF block again when the orientation is not 1.
  It raises `struct.error` when a tag holds a value of the wrong type. `validate_image`
  does not parse EXIF, so the file passes the admission check.
- Effect: `POST /v1/eval/predict`, `POST /v1/match`, and `POST /v1/group/match` answer
  HTTP 500 with a stack trace in the log. A random EXIF mutation test gave 4 such files
  in 4,000. `docs/cascade.md:135` promises HTTP 422. This is not known issue 2 (that
  issue is HTTP 400).
- Fix: when `exif_transpose` fails, continue with the image as stored. Add the sample
  file (763 bytes, a JPEG with orientation 6 and tag `0x0141` that holds a string) as a
  test fixture.

**M-2. A failed archive write gives HTTP 500 for every request.**

- Severity: medium. Status: verified. Lead check: probe with `matcher/tests/config.yaml`
  and a read-only archive tree. `POST /v1/eval/predict` gave HTTP 500. `GET /readyz`
  gave HTTP 200.
- Location: `app.py:299-305` (`save_image`, then `raise`), `app.py:360` (`save_record`
  with no guard on the success path).
- Problem: the request archive is on the request path. The service cannot answer when
  it cannot write the archive.
- Effect: a full or read-only disk on gx10 stops prod matching. The Docker health check
  calls `/readyz`, so the container stays healthy. The archive has no retention job and
  no size limit. [The security audit](../../../docs/security-audit-2026-09-29.md),
  SV-SEC-01, reports the disk growth. It does not state this failure mode.
- Fix: log an archive error and answer the request. Report the free space in `/readyz`.
  Add the retention job of SV-SEC-01, item 3.

**M-3. Unknown keys outside the cascade entry load with no error.**

- Severity: medium. Status: verified. Lead check: read `service.py:340-358`. A reviewer
  loaded test configurations with `load_matcher`.
- Location: `service.py:346-354` (`matcher`), `:387-409` (mock entry), `:465-478`
  (siglip2 entry). Only `_load_cascade` calls `_keys` (`:553`).
- Problem: the loader reads `matcher:` with `.get` and does not check its keys.
- Effect: when a deployment sets a token, the typo `matcher.tokn:` loads with no token,
  and the three POST routes run with no authorization. `matcher.fast_answr:` loads with
  no time budget. The cascade then waits for the call limits (SAM3 30 s, crop 30 s, VLM
  60 s) and misses the 10 s limit of the harness. `docs/cascade.md:72` states that the
  loader refuses an unknown key at each level.
- Fix: call `_keys` at the top level, in `matcher`, and in each backend entry. Add tests
  for each level.

**M-4. Prod and the lab select different packages.**

- Severity: medium. Status: the filter and the input difference are verified by three
  reviewers. The effect on R@1 is plausible. Lead check: read `main_scene.py:58`,
  `group.py:26`, and `config.yaml:55`.
- Location: `main_scene.py:58` (`if instance["score"] < DETECTION_THRESHOLD: continue`),
  `group.py:26` (`DETECTION_THRESHOLD = 0.4`), `cascade_run.py:210`, `services.py:145`.
  Lab: `workbench/pipeline/main_scene.py:133-150`, `derive.py:82`.
- Problem: the cascade asks SAM3 for instances with a score of 0.35 or more. Then
  `rank_packages` drops each package and hand below 0.4. The lab keeps them. The SAM3
  input also differs: the lab sends a PNG with a long side of 1536 px
  (`derive.py:84, 213-214`). The cascade sends a JPEG, quality 86, long side 1600 px
  (`photo.py:24-25, 76`), and adds the noun `label` (`cascade_run.py:193-196`).
- Effect: a bottle or a hand with a score from 0.35 to 0.40 changes the selection in the
  lab but not in prod. A hand below 0.4 switches prod from `HAND_WEIGHTS` to
  `SCENE_WEIGHTS`. The lab SAM3 cache is keyed by the PNG bytes, so no lab run measured
  the prod input. So R@1 of the lab `*-crop` pipelines can differ from the cascade.
  `docs/cascade.md:60, 75` call the values "the lab values".
- Fix: pass `sam3.threshold` into `rank_packages`. Share one function for the SAM3 copy,
  or add a lab option that sends the prod copy. Add parity tests for scores from 0.35
  to 0.40.

**M-5. Cascade `/v1/match` can stop before any ranking exists.**

- Severity: medium. Status: verified with a probe of the reviewer. Lead check: read
  `cascade_run.py:360-372` and `:440-450`.
- Problem: a unique package or label code gives `Answer(..., final=True)`, and
  `execute` returns at once, also in match mode. At that moment the ranking can be
  `None`.
- Effect: `k=20` can give 1 candidate. The result depends on the stage timing.
  `docs/cascade.md:131-132` promises "the code wines at 1.0, then the ranking without
  them".
- Fix: in match mode, fix rank 1 from the code and wait for the running ranking tasks.

**M-6. A code of a wine with no vectors splits `predict` and `match`.**

- Severity: medium. Status: verified with a probe of the reviewer. The review did not
  check how often the real catalogue has this case.
- Location: `catalog.py:216-219, 288`, `cascade.py:111-112, 128`.
- Problem: `load_codes` loads the codes of each Active wine. `load_catalog` makes cards
  only for slugs with vectors. The catalogue copy allows index gaps
  (`workbench/pipeline/catalog_copy.py:59-60`).
- Effect: `predict` answers the code wine. `/v1/match` drops it and can answer `[]`,
  while the audit record says `decision.source: code_package`. Item 6 of the review of
  2026-09-29 has the same effect with another cause.
- Fix: make a card for each `matcher_wine` row, or limit the code table to the slugs of
  the index.

**M-7. The OpenAPI 422 schema does not match the body.**

- Severity: medium. Status: verified.
- Location: `openapi.yaml:76-81, 137-142, 199-204`; `app.py:296-298, 350-351`.
- Problem: the schema declares `HTTPValidationError` (`detail` is a list). The service
  sends a string `detail` for a damaged image.
- Effect: a client generated from `openapi.yaml` cannot parse this 422 answer.
- Fix: declare the 422 answer as `oneOf` (a string `detail` or the validation list).

**M-8. The documented archive path is not ignored by git.**

- Severity: medium. Status: verified. Lead check: `git check-ignore
  work/matcher-requests/x/y/image.jpg` exits 1.
- Location: `README.md:331, 347` and `eval/README.md:76` set
  `SVOE_VINO_MATCHER_OUTPUT_DIR=work/matcher-requests` in the repository root. Only
  `workbench/work/` is ignored.
- Effect: a `git add -A` in the shared tree commits user photos, client addresses, and
  request headers.
- Fix: add `/work/` to the root `.gitignore`, or use an ignored path in both documents.

**M-9. Low-severity defects.**

- After a SAM3 failure, the VLM re-rank runs only when another stage ends later
  (`cascade_run.py:295-301`). With SAM3 off, the re-rank runs. Fix: call `start_vlm()`
  also in the failure branch.
- A malformed rule file stops the start with a bare `KeyError` or `AttributeError`, or
  loads wrong data (`"slugs": "wine-a"`) with no error (`rerank.py:264-276`,
  `service.py:610-613`). Fix: check the types and raise `RuleError`.
- The environment settings accept `nan` and `inf` (`app.py:602-612`). An `inf` upload
  timeout switches off the HTTP 408 guard. The YAML path refuses these values.

### 4.2 Documentation gaps

| Severity | Gap | Evidence |
|---|---|---|
| medium | The documents call the endpoint variables optional. Each `{env:NAME}` of the selected pipeline is required at start. `matcher.env.example` has every line in a comment, so the container stops at start and restarts in a loop. The `docker run` example sets `SAM3_ENDPOINT` but not `SIGLIP2_ENDPOINT`. | `service.py:423-426`; `README.md:390-397`; `deploy/gx10/matcher-prod.md:108-110`; `matcher.env.example` |
| medium | With no `matcher.fast_answer` block, no time budget applies. The call limits (30/30/10 s, VLM 60 s) are not documented. `docs/cascade.md:48` gives `enabled` the default `true`. | `cascade.py:99-100`; `cascade_run.py:45` |
| medium | One pool of 8 in-flight slots serves all three POST routes. The README says "predict". Slow shelf or cascade requests make predict answer 503. | `protection.py:18, 57`; `README.md:316-319` |
| medium | "The matcher reads the two views alone" is false. For the cascade, `load_codes` reads `wine_code` and `wine_catalog`. Rule 28 forbids a change of `031_matcher_views.sql`, which holds the false text. | `catalog.py:200-229`; `README.md:17-19, 219-220`; `workbench/pipeline/schema/031_matcher_views.sql:2-3` |
| low | `GROUNDING_DINO_ENDPOINT` and `VLM_MODEL` are documented. No code reads them. | `README.md:397-398`; `Dockerfile:13-15` |
| low | The manual prod check uses a missing image `workbench/data/images/main/89b5…webp`. `deploy/test/check.sh` uses the plan 75 path. | `deploy/gx10/matcher-prod.md:349` |
| low | `TESTING.md` describes GitHub Actions. Its GitLab acceptance ("Ran 213 tests", "OK") cannot see skipped tests. | `TESTING.md:313-333` |
| low | The cold start is about 48 s for NaFlex SigLIP2. The README says it "can approach" 10 s. | `README.md:353-355`; `docs/cascade.md:165-166` |
| low | Stale facts: the gx10 README gives revision `9ba496d` (prod runs `f199e4d`); the two "first install" procedures copy different configurations; `eval/README.md` says the bundle is not in git; `KNOWN_ISSUES.md` item 1 asks a question that `ResearchLog.md:125-128` answers. | `deploy/gx10/README.md:74`; `COMMANDS.md:38`; `eval/README.md:66-67` |
| low | Undocumented protocol details: `WWW-Authenticate: Bearer` on 401, `Retry-After: 1` on 503, `Connection: close` on each rejection, HTTP 400 for a bad `Content-Length`. | `protection.py:72-85, 212` |
| low | `matcher/config.yaml:18`, `siglip2.py:3`, and both READMEs name the lab pipeline `siglip2-p512-as-is`. The lab has no such pipeline. The matching pipeline is `siglip2-p512`. | `workbench/config.yaml:514-523` |
| low | The sugar and QR rules point to `telegram-bot/src/chto_za_vino_bot/catalog.py`. That file does not exist. | `bundle.py:34`; `catalog.py:49-50` |

### 4.3 Improvements

1. Strict key checks at every configuration level, with tests (M-3).
2. Separate admission for `/v1/eval/predict`: reserve slots for it, or give the shelf
   route and cascade `/v1/match` their own limit. Add a total deadline for cascade
   `/v1/match`: the chain SAM3, crop, VLM can hold a slot for about 120 s.
3. Log each failed cascade stage at WARNING with the stage name and the exception type.
   Today a scanner, SAM3, or VLM outage shows only in `request.json`.
4. OpenAPI error models for 400, 401, 408, 413, 415, 502, 503, and 504, with the
   headers `Retry-After` and `WWW-Authenticate`. The OpenAPI equality test then guards
   them.
5. A test that the pinned versions equal the lock versions. `test_service.py:126-134`
   compares only the names.
6. Tests for the missing error paths: `Retry-After`, a bad `Content-Length`, the
   environment validation, the redaction of each sensitive header, the group gate
   branches, and HTTP 408 and 413 on `/v1/match` and `/v1/group/match`.
7. Take the archive file suffix from the decoded format, not from the client file name
   (`audit.py:55-58`). See I-2.

### 4.4 State of the items of the review of 2026-09-29

| Item | State |
|---|---|
| 3. `/readyz` has no limit | Still present. With the cascade, each call sends one SigLIP2 embedding and two `/health` requests through the HTTP pool of the matching work. |
| 4. Health check sends a model request | Partly fixed. The deploy document names `/readyz`. The model request every 30 s stays by design. |
| 6. `predict` and `match` rank 1 can differ | Still present for siglip2 bundles. The cascade has the same effect through code slugs (M-6). |
| 8. Efficiency of group crops | Still present. |
| 9. `matcher/1.txt` | Fixed. |

## 5. `matcher-inspector`

The service has confined paths (a pattern for the date and the request identifier, no
symbolic links), escapes each value, and sends a strict Content Security Policy,
`nosniff`, and `no-referrer`. The container mounts the data read-only and runs as a
non-root user.

**I-1. The main page reads every journal of the archive.**

- Severity: medium. Status: verified. Lead check: probe with synthetic journals of
  2.7 KB on the internal SSD, warm cache: 1,000 journals 0.14 s, 10,000 journals 1.72 s.
- Location: `app.py:111-135` (`list_requests` loads, parses, and sorts all records,
  then keeps 200).
- Effect: the time and the memory grow linearly with the archive. The archive has no
  retention.
- Fix: read the date directories from the newest, and stop after 200 records.

**I-2. Low-severity defects.**

- `/healthz` answers `"status": "ok"` also when neither data root exists
  (`app.py:480-488`). A wrong volume mount keeps the container healthy with empty
  pages.
- The matcher archives an image with an unknown client suffix as `image.bin`
  (`matcher/audit.py:55-58`). The inspector shows only `image.<known suffix>`
  (`app.py:79-90`), so the page says "No supported image file was found". The official
  queries (names `*.jpg`, WebP bytes) are stored as `image.jpg`. Fix on the matcher side
  (4.3, item 7).
- `deploy/gx10/matcher-inspector.md` says that neither environment has a bundle. Prod
  has `data/bundles/gx10-siglip2-so400m-patch16-naflex-p512`.
- No CI job runs the 7 tests (C-1).

Not repeated here: the missing authentication for archived user data is
[SV-SEC-02](../../../docs/security-audit-2026-09-29.md) (severity high).

## 6. `workbench`

### 6.1 Test sets and catalogue

**W-1. No guard between test photos and catalogue images.**

- Severity: high. Status: verified. Lead check: compared the SHA-256 values of
  `wine_image` and `test_photo` in `db-export/rows/` (export of 2026-09-29 21:48).
- Location: each catalogue writer reuses the `image` row of any folder, also
  `testset`: `alternatives.py:613-615`, `manual_wines.py:179-181`,
  `patches.py:121-123`, `import_website.py:689-690`, `seed_images.py:249-251`,
  `seed_patched.py:181-183`. In the other direction, `testsets.py:820` and
  `import_testset.py:228` accept catalogue bytes as a test photo with no message.
- Current data: three links.

  | Catalogue wine and image | Test photo | Wine state |
  |---|---|---|
  | `abrau-dyurso-victor-dravigny-koshernoe-bryut-shardone-beloe-125`, `label_back` | `my`, `10_manual.webp`, positive of the same wine | Removed |
  | `__cli-index-smoke-20260929`, `main` | `official-real-photos`, `41.8_22-08-2026_20-56-40.webp` | Disabled |
  | `__web-index-smoke-20260929`, `main` | `official-real-photos`, `96.42_22-08-2026_21-29-43.webp` | Disabled |

- Effect: the index and the benchmark read Active wines only, so the current numbers
  do not change. A `Restore` of the first wine makes a test photo a catalogue vector of
  its own wine. The query then matches itself. Runs made while the smoke wines were
  Active can have used an official photo as a catalogue vector (not checked).
- Fix: refuse a catalogue write whose SHA-256 is in `test_photo`, and the reverse. Make
  `build_queries` fail on such a query. Port the near-duplicate check
  `check_candidate_is_catalog_photo` of `scripts/review_server.py:2870`, because a
  re-encoded picture has other bytes. `HACKATHON_TODO.md:27-28` lists this gate as
  open.

**W-2. The catalogue copy for the matcher holds the test tables.**

- Severity: medium. Status: verified. Lead check: read `catalog_copy.py:150-185`. No
  statement deletes a table.
- Location: `catalog_copy.py:165-167` (`source.backup(target)`).
- Effect: each copy holds `test_photo` with the true slug and label of each official and
  `test-1` photo, the photo comments, and 3,529 test image rows. The matcher reads only
  its two views, `wine_code`, and `wine_catalog`.
- Fix: delete the test tables in the temporary copy, then run `VACUUM`.

**W-3. The benchmark sets were used for tuning. The documents do not say so.**

- Severity: medium. Status: verified. Lead check: read the first entry of
  `ChangeLog.md` for 2026-09-29.
- Evidence: a reviewer note written from the official test photos q-000003 and
  q-000004 rebuilt the re-rank rule of cluster `2d33f12d0b3e`. The check run on the same
  set gave R@1 90.5 % → 92.1 %. The set `test-1` holds 48 positives now; its README and
  its report state 35. Sixteen of the new positives belong to 12 wines that were added
  on 2026-09-29 (reviewer count from `db-export/`).
- Effect: the official set and `test-1` are no longer independent of the system. The
  root `README.md:34-37` states 90.48 % on the official set with no note.
  `BENCHMARKS.md` has no row for the official set or for the cascade.
- Fix: state in `BENCHMARKS.md` which sets were used for tuning, with the run
  identifiers. Keep one set that nobody edits.

**W-4. Four tool paths lose curated data with no backup.**

- Severity: medium. Status: verified with probes of the reviewer.
- `export_testset.py`, then `import_testset.py --force`: the import builds rows from the
  files on disk. A moved photo returns to its old place with no label. An uploaded photo
  is lost. The refusal text of `import_testset.py:170-173` recommends this path. Current
  data: `test-1` has 26 rows with no file at their place and 22 files at places that the
  database does not use. `my` has 31 moved rows, `official-real-photos` has 11.
- `seed_patched.py --force` deletes and inserts again each patch whose file differs
  (`:195-205`). A patch that a person set on the page is replaced.
- `seed_from_testset.py` imports only `my`, `official-real-photos`, and
  `vlmrerank-8b-failed` (`import_testsets.py:31`). It drops `test-1` (58 photos), `my-1`
  (261), and `2026sep26superlenta` (15). The README calls the command "build the whole
  lab database again from its sources".
- `import_testset(s) --force` deletes each row of the set (`import_testset.py:300-301`)
  with no backup.
- Fix: match export entries by SHA-256. Make `--force` add rows only, and add a separate
  `--replace`. Make a backup before each replacement. Import `dataset/test-1` in the
  seed.

**W-5. A truncated VLM answer stops the description watcher.**

- Severity: medium. Status: verified with a probe of the reviewer. Lead check: read
  `describe_images.py:386-404`.
- Problem: `post()` does not catch `http.client.IncompleteRead` or `BadStatusLine`.
  `main()` catches only `WaitError`, `DescribeError`, and `sqlite3.Error`.
- Effect: a model reload of llama-swap during an answer stops the watcher. The lab
  server starts the watcher only once, so descriptions stop until the next restart.
- Fix: catch `http.client.HTTPException` in `post()` as a failure that is not counted.

**W-6. Low-severity defects.**

- `move_photo` can put the same bytes twice in one place (`testsets.py:700-729`). `my`
  has 32 queries that repeat the bytes of another query of the same wine.
- A malformed `review-labels.json` stops `import_testset.py` with a traceback.
- `import_catalog.py` accepts a CSV row with extra fields (`:113-126`). An unquoted
  comma moves text into `csv_photo_name`.
- `wine_identity_vlm.parse` raises for a text confidence and reads the string `"false"`
  as true (`:48-49`).
- A test import does not store the file of a known image again when the file is missing.
- A restore after an import removal makes a wine `Active`, also a wine that a person had
  set to `Disabled` (`import_catalog.py:219-220`, `import_website.py:727-728`).
- The website-compare gate is only in `_compare` (`import_website.py:793-794`). The
  public `compare()` has none. No second start path exists today.
- `label_descriptions.pending` (`:87-99`) looks only for images with no row. A new
  package cut keeps the old label description.

### 6.2 Embedding and benchmark pipeline

**W-7. The summary writer crashes when a run has no positive query.**

- Severity: medium. Status: verified with a probe of the reviewer. Lead check: read
  `scripts/match_scoring.py:95-103, 383-392`.
- Problem: `f1()` returns `{"f1": None}` when there is no positive query. The summary
  then formats `None` with `"%.4f"`.
- Effect: a set of negative or `__null__` photos, or `--limit N` when the first rows are
  `__null__/…` (they sort first), gives `TypeError`. `summary.md` is missing, and the
  job ends `failed`.
- Fix: write "—" when `f1` is `None`.

**W-8. One bad SAM3 answer aborts a whole run.**

- Severity: medium. Status: verified with a probe of the reviewer. Lead check: read
  `embedding_run.py:536-544` and `main_scene.py:244-247`.
- Problem: `ask` catches only `Sam3Unavailable`, `ItemError`, and `BackendError`.
  `main_scene.py:246-247` raises `ValueError` for an invalid mask. `derive.py:237`,
  `alternatives.py:343`, and `DecompressionBombError` can raise other types.
- Effect: `pool.map` raises again, and the run writes no `run.json` and no
  `metrics.json`. The answered rows are lost for `/runs`.
- Fix: catch each exception of one photo in `ask` and record it as the error of the row.

**W-9. Barcode pipelines silently become embedding pipelines.**

- Severity: medium. Status: verified. Lead check: read `barcode.py:384-408`.
- Problem: when the scanner fails, `CodeFirst.ask` writes the error into the trace and
  asks the embedding (`:390-391`, `:405`). `qr_barcode.py:159-160` raises
  `ScanUnavailable` when `QR_SCANNER_ENDPOINT` is not set.
- Effect: a lab server that starts without the variable gives `barcode-*` runs that
  equal their embedding twins. `metrics.json` and `summary.md` show no failure.
- Fix: count the barcode step errors in the metrics. Refuse the run when the endpoint
  is not resolved.

**W-10. Low-severity defects.**

- An index never builds again after a change of the vector dimension
  (`build_embeddings.py:279` keeps the old `dim`). Each build fails each item and still
  ends `done` with exit 0. Probe: builds 2 and 3 failed 9 of 9 items.
- An explicit empty answer `{"slug": ""}` counts as a backend error
  (`match_backends.py:124-152`). In a `matcher-eval-predict` run, each timeout and each
  correct rejection of a `__null__` photo counts in "Errors".
- The two-view score mixes wines with one view and wines with two views
  (`embedding_run.py:412-421`). Wines with no label vector get a better score.
- `segment_dis` shows DIS the hidden colours under transparent pixels (`dis_litert.py:33`).
- A plain build can send one image alone (`build_embeddings.py:351`).
  `ResearchLog.md:480-484` measured a cosine of 0.994 against the batched vector for
  NaFlex p256.
- The self-test counts one wine of a shared image as a miss (`selftest.py:18, 75`).
- The cluster "stale" flag ignores the thresholds (`clusters.py:262-274, 596`).
- A current record with invalid rows leaves the index for one build
  (`build_embeddings.py:258-266`).

**Documentation gaps of the pipeline.**

- `config.yaml:536` calls `siglip2-p512-seg` "the lab twin of the matcher
  `hand_selection: true`". The two differ in the threshold, the mask (soft alpha against
  a binary mask), and the crop source (full resolution against the 1600 px copy).
- `matcher/config.yaml:40`, `docs/cascade.md:33`, and `matcher/README.md:212` use
  `catalog: workbench/data/catalog`, the live lab directory. `docs/cascade.md:51`
  requires a copy of `copy_catalog.py`.
- The `summary.md` of a stopped run does not say that the run is partial.

**Improvements of the pipeline.**

1. Parity tests for the prod single-photo path: `main_scene.rank` against
   `rank_packages`, the crop box against `photo.refined_box`, and the SAM3 request
   fields. Today the parity tests cover codes, labels, `refine_mask`, and the re-rank.
2. A lab backend that reproduces the cascade. Today the lab reads the rot5 rules and
   prod reads the p512 rules (`cluster_rerank.py:86-87`).
3. Count the positives whose true wine has no current vector ("unreachable truths") in
   `metrics.json`.
4. Mark a run as degraded after `Sam3Once` trips (`embedding_run.py:126-134`).
5. Write `run.json` at the start, with `finished: null`.
6. Make `copy_catalog` warn when `clusters.json` is older than `index.json`. For p512,
   `clusters.json` is of 27 September and `index.json` of 29 September.
7. Give query embeddings a short timeout and a breaker. They use the build values
   (`TIMEOUT = 300` s, 3 retries), so one hung call can cost about 20 minutes per photo.

### 6.3 Lab server

The lab server listens on `127.0.0.1:8168` (`lab_server.py:1969`). The outside risk is a
web page in the browser of the owner, not a LAN host. The server keeps file routes
inside their directories, parameterizes all SQL, and starts no subprocess through a
shell. Each schema file applies in one transaction with its version, and a failure
rolls back cleanly.

**W-11. Upload checks decode every image format, EPS through Ghostscript.**

- Severity: high. Status: verified. Lead check: read the three checks and
  `testset_routes.py:170-192`; `gs` 10.05.1 is installed at `/opt/homebrew/bin/gs`.
- Location: `patches.py:79-89`, `testsets.py:772-782`, `recognize_routes.py:128-130`.
- Problem: each check calls `Image.open` for every Pillow format and `image.load()`
  before the format allow-list check. For EPS, Pillow runs Ghostscript with no timeout.
  The Testset upload and fetch routes decode the image and write the file (up to 20 MB)
  inside `BEGIN IMMEDIATE`.
- Effect: a file that is not an allowed photo still runs a decoder. A slow decode or a
  slow write on the T7 drive holds the write lock of the database. Other writers wait
  5 s (the default of `sqlite3.connect`) and then answer 503 "database is locked".
  Photos also come from web pages: `/api/testset-fetch` stores the image of a URL.
- Fix: pass `formats=` to `Image.open` in each check. Decode and store before the
  transaction, and keep only the `INSERT` statements inside. The matcher already checks
  the format first (`matcher/protection.py:237-240`), and its image has no Ghostscript.

**W-12. Write routes accept requests from other web pages.**

- Severity: medium. Status: plausible. Lead check: read `_json_body`
  (`lab_server.py:1526-1549`). No code reads `Origin`, `Sec-Fetch-Site`, or
  `Content-Type`.
- Problem: a `text/plain` POST is a simple request with no preflight. The server parses
  any body as JSON.
- Effect: a page in the browser of the owner can remove a wine, start runs against paid
  cloud models, start builds, or make the server fetch a URL. Newer browsers can block
  or ask about requests from a public page to a local address. The review did not test
  this.
- Fix: refuse a write whose `Origin` or `Sec-Fetch-Site` is not the server origin.
  Accept only `Host` `127.0.0.1` or `localhost`. Require `application/json`. Send
  `X-Content-Type-Options: nosniff` and `frame-ancestors 'none'`.

**W-13. The Pillow bomb guard is off in the server process.**

- Severity: medium. Status: verified. Lead check: `imagestore.py:19` sets
  `Image.MAX_IMAGE_PIXELS = None` at import; `lab_server.py` imports `patches`, which
  imports `imagestore`.
- Problem: the setting applies to the whole process. The Recognize upload
  (`recognize_routes.py:127-131`) calls `load()` with no size check, and its
  `except Image.DecompressionBombError` can never run. Line 190 decodes the file a
  second time. The patch and testset checks have their own limit of 100 megapixels.
- Effect: one upload that declares very large dimensions makes the server allocate
  width × height × channels bytes.
- Fix: check `image.size` against `testsets.UPLOAD_PIXELS` before `load()`. Set a high
  explicit limit in `imagestore.py`, or switch the limit off only in the offline tools.

**W-14. The address check of `/api/testset-fetch` is not bound to the connection.**

- Severity: medium. Status: the mechanism is verified.
- Location: `remote_images.py:51` resolves the host and checks each address with
  `is_global`. `remote_images.py:120` then connects through the default `urllib` opener.
- Problem: the opener resolves the host a second time and also uses the proxy
  environment variables. The timeout of 20 s applies to each socket operation, not to
  the fetch.
- Effect: a host name whose DNS answer changes between the two look-ups passes the
  check. The server then connects to a loopback or LAN host (model gateways, the NAS S3
  store, the registry). A GET can have an effect there: for example,
  `/upstream/<model>/` of llama-swap loads a model. The URLs come from images that the
  owner drags from web pages.
- Fix: connect to the checked address, or check `getpeername()` after the connect. Use
  `ProxyHandler({})`. Limit the total time of a fetch.

**W-15. Many errors close the connection with no HTTP answer.**

- Severity: medium. Status: verified. Lead check: `labdb.SchemaError` derives from
  `Exception`, and no code of `lab_server.py` catches it.
- `lab_server.py:293` calls `labdb.schema_files()`, which raises `SchemaError` for a gap
  or a duplicate schema number (`labdb.py:49-51`). The handlers catch only
  `(ConfigError, sqlite3.Error)`. So every database route closes the connection, and
  the pages show a network error. This is the case that rules 25 to 28 try to prevent.
- `_embedding`, `_clusters`, `_website_import`, `_runs` (`lab_server.py:1274-1319`), and
  `_openapi` (`:1422-1428`) have no `try`. Traced paths: `embeddings.open_database`
  re-raises `sqlite3.Error` past `embedding_routes.respond`; `website_import_routes.stop`
  does not catch `PermissionError`; `?log=` of `/api/image-description-status` accepts
  `"²"` through `str.isdigit()`, and `int()` then raises; `testsets.upload_photo` lets an
  `OSError` through.
- Fix: one wrapper in `do_GET` and `_write_route`: coded errors keep their code,
  database and configuration errors give 503, and each other error gives 500 with a JSON
  body. Map `SchemaError` to 503, and name a duplicate number in its message.

**W-16. Low-severity defects of the lab server.**

- The website-import job check trusts a bare PID (`website_import_routes.py:88-95`).
  After PID reuse, `POST /api/website-import/stop` can send SIGTERM to an unrelated
  process. The embedding and run jobs already check the command with `ps`.
- `POST /api/dataset-alternative-recut` commits the DELETE of the old cut before it
  makes the new cut (`alternatives.py:900-912`). A failure leaves the photo with no cut.
- `labdb.migrate` reads `user_version` outside the transaction (`labdb.py:58, 73`). In a
  probe, two processes applied the same file twice. The seed and import tools migrate.
- A rebuild of a table that a view reads fails (`DROP TABLE t` with view `tv`). The
  views of schema 031 and 032 read `wine_catalog`, `wine_image`, and `wine_code`. No
  rule says "drop the views first".
- Wrong codes: a wrong method or an unknown `/api/` path answers 503 "disabled for now"
  (`lab_server.py:1498-1499, 1896-1897`); an oversize body gets 400, not 413; an unknown
  `/api/run?filter=` returns all rows.
- `del _PROCESSES[directory]` runs in parallel request threads with no lock
  (`run_jobs.py:202`, `website_import_routes.py:102`). `embedding_routes.py:146-150`
  uses `pop(directory, None)`.
- `GET /api/dataset` answers 503 when `new_wine_embedding` is missing or invalid
  (`lab_server.py:517-518`), so the Dataset page does not load.
- No limit applies to parallel Recognize runs. Each POST starts a model process and
  waits up to 300 s (`recognize_routes.py:152-153`).
- The `/docs` page loads Swagger UI from `cdn.jsdelivr.net` with no `integrity`
  attribute (`lab_openapi.py:68-69, 95-97`) and enables "try it out" (`:104`).

**Documentation gaps of the lab server.**

- `docs/API.md` describes the review tool on port 8154. The lab routes are mixed in as
  notes. `README.md:2853` and `docs/excluded-slugs.md:109` send readers to `API.md` "for
  every route and every field". Only the docstring of `lab_server.py:126-128` links
  `docs/lab-openapi.yaml`.
- On shared routes, `API.md` contradicts the lab server: the patch formats and storage,
  the key of the alternative DELETE (`file=` against `sha256=`), and the atlas binding
  (replace against add).
- `API.md` does not name many lab routes: `POST /api/wine`, `/api/wine-index`,
  `/api/wine-state`, `/api/wine-name`, the `/api/image-description*` routes, all
  `/api/embeddings…` and `/api/clusters…` routes, most testset writes, and all
  `/api/website-import…` routes.
- `docs/lab-openapi.yaml` lists all 102 operations, but almost every answer is a free
  `Object`. One body schema, `TestsetPhotoWrite`, serves 8 routes and does not name the
  key that each route needs. `tests/test_lab_openapi.py` compares the document with a
  hand-written list, not with the routes of the code.
- `pipeline/schema_pending/` is empty. No code, test, or rule refers to it.

**Improvements of the lab server.**

1. Set the journal mode to WAL once, and raise the busy timeout above 5 s. No code sets
   `journal_mode`. Replace the six copies of the BEGIN/COMMIT/ROLLBACK block with one
   `write_transaction()` helper with the rule "no decode, file I/O, or network call
   inside".
2. Fix the expected schema version at server start. Today `lab_server.py:293` counts the
   files on disk for each request, so a new file of another session gives 503 at once.
3. A route test that starts from the code: start `make_server` on a temporary database,
   send each documented operation, and fail on a fallback answer.
4. One job-state helper for all job kinds: a lock file with the PID and the start time,
   the `ps` check, and an event log. The new-wine index jobs live only in memory
   (`new_wine_jobs.py:8-9`).
5. Answer a write with one record. `wine_answer`, `_patch_answer`, and
   `_alternative_request` build the whole catalogue to return one wine
   (`lab_server.py:655, 759-760, 795-797`).
6. A lock across the read and the apply of a migration. A warning for a `*.sql` file
   that does not match `SCHEMA_RE`: a probe showed that `002_New-Table.sql` is ignored.
7. A backup before the bulk website apply, as `seed_from_testset.py:141-150` does.

### 6.4 Browser pages

No XSS finding: each page escapes its values with `esc`, and each URL from data goes
through `safeUrl` (http and https only). Each API call of a page matches a route and a
method of the server.

**W-17. Older answers overwrite newer ones.**

- Severity: medium. Status: verified. Lead check: read `runs.html:1040-1058`.
- `runs.html:1040-1058` (`loadRun`) clears the table, waits, and appends. Two
  overlapping calls (the Find field, Show, Sort, a run click) mix their rows. A double
  click on "load more" adds the same 100 rows twice.
- `embedding.html:438` and `clusters.html:577`: a slow answer for configuration A
  arrives after the answer for B and replaces it. On `/clusters`, "Save note" can then
  post a cluster key of A to `/api/clusters/B/note`. The key hashes only the slugs, so
  the key can exist in B.
- Fix: a request counter or an `AbortController`. The pattern exists five times in the
  pages already (for example `SP_REQUEST` in `runs.html`).

**W-18. Theme contrast.**

- Severity: medium. Status: verified.
- Light theme: `runs.html:284` gives the notes of the large-view rail the colour
  `#d7d7df` on white (about 1.2:1). Loading and error texts are not readable.
- Dark theme: white text on light accent colours, for example the label buttons of
  `testset.html:315-318` (1.8:1 to 2.2:1), `dataset.html:291`, `recognize.html:74`,
  `runs.html:118`. The transparency checkerboards stay light (`embedding.html:107-117`,
  `dataset.html:583-608`, `clusters.html:101-110`).
- Fix: tokens `--on-pos`, `--on-neg`, `--on-accent`, `--on-exc`, `--checker-a`, and
  `--checker-b` in `theme.css`.

**W-19. Low-severity defects of the pages.**

- `/health` writes the gateway value `ttl` with no escape (`health.html:224`).
- `runs.html:1048, 1634`: a failed request gives an empty table and no message.
- A malformed `%` escape in the URL fragment breaks `/dataset`, `/clusters`, and `/runs`.
- `clusters.html:243` reads the response body twice.
- The VLM poll of `/dataset` can run as several parallel loops (`dataset.html:2433-2452`).
- The preview arrows do nothing on the review tool (`dataset.html:1237`).
- The `/runs` table scrolls the whole page sideways at phone width.
- `beforeunload` of `/dataset` ignores five draft maps (`DRAFT_GTINS`, `DRAFT_QR_URLS`,
  `DRAFT_TAGS`, `DRAFT_SIMILAR`, `DRAFT_NAMES`).

**Documentation gaps of the pages.** The README does not describe these parts: the
Origin filter and the URL keys `origin`, `group`, `q`, and `sort` of `/testset`; the key
`s` of the drawer; the deep link `#<run>/<image path>` of `/runs`; the keys `name`,
`filter`, and `q` of `/embedding`; the Space and Image selects of `/clusters`; paste with
Ctrl+V on `/recognize`; the stored header keys in `localStorage`. The README describes
old preview keys of `/dataset` (`README.md:1766-1769`) and a threshold input of
`/clusters` that the page does not send (`README.md:829`).

**Improvements of the pages.**

1. One shared `common.js`, injected through the existing mark mechanism of
   `lab_pages.PARTS`: `esc` (9 copies today), a JSON fetch helper (7 variants), a
   "latest request wins" helper, header persistence (5 copies), clipboard copy.
2. One navigation list from `NAV`. Today 9 copies exist, and the README has drifted.
3. A non-blocking error line instead of `alert()` (57 calls).
4. Use `renderCard` instead of a full `render()` of about 2,100 cards (about 0.7 s) for
   small changes.

### 6.5 Scripts, tests, and CI

**W-20. The documented environment cannot start the lab server.**

- Severity: medium. Status: verified. Lead check: `describe_images.py:58` imports
  `jsonschema` at module level; `lab_server.py:163` imports `describe_images`.
- Problem: `requirements-local.txt:8` says that the lab server needs "the first four
  packages alone". No workbench requirement file lists `jsonschema`. `matplotlib`,
  `reportlab`, and `zxing-cpp` are also not listed.
- Effect: a new machine that follows `COMMANDS.md:210-214` gets
  `ModuleNotFoundError: jsonschema`. The interpreter rule (system `python3` for the lab
  server and the tests, the venv for builds) is written in no document.
- Fix: a pinned requirement file for the lab server and the tests. Name the interpreter
  of each command.

**W-21. The configuration pins the absolute path of this Mac.**

- Severity: medium. Status: verified by code reading. Lead check: read
  `config.yaml:11-19`.
- Location: `config.yaml:14` and `config.old.yaml:15`
  (`rootdir: /Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace`).
- Effect: scripts with a `--config` default resolve the database under `/Volumes/T7_2TB`
  on each other host: `copy_catalog.py`, `build_matcher_bundle.py`, `add_wine.py`,
  `segmentation_model_matrix.py`. `config.yaml:19`
  (`database_file: svoe-vino-lab/workbench/...`) also needs a checkout directory with the
  name `svoe-vino-lab`. A clone of `svoe-vino-lab-dev` has another name.
- Fix: delete the `rootdir:` line, and make `database_file` relative to the workbench.
  The code already falls back to the directory of the repository (`lab_server.py:272`,
  `embeddings.py:364`).

**W-22. The legacy review tools exit at start.**

- Severity: medium. Status: verified by two reviewers. Lead check: `config.yaml` has no
  key `dataset`, and `scripts/common.py:102-105` calls `sys.exit`.
- Location: `scripts/common.py:10`. Affected: `match_run.py`, `review_server.py`,
  `cluster_rules.py`, `bench_vlm_models.py`.
- Effect: each documented start fails: `README.md:1624-1626, 1678-1679, 1750-1751,
  2748-2758`, `docs/API.md:9`, `docs/match-runner.md:9-13`, and the smoke cases C1 to
  C13. Only `README.md:981-982` names `SVOE_VINO_REVIEW_CONFIG=config.old.yaml`. With the
  variable, these tools read and write the sibling repository `svoe-vino-testset`.
- Fix: print a message that names the variable, or make `config.old.yaml` the default of
  these tools. Mark the tools as legacy (W-29).

**W-23. Some tests need repositories outside git.**

- Severity: medium. Status: verified by code reading.
- `test_run_model_inputs.py` imports `svm` from `../svoe-vino-matcher`
  (`scripts/run_model_inputs.py:29-36`) and changes `sys.path[0]` for the rest of the
  run. In a clean clone, two tests fail.
- `test_seed_images.py:21` and `test_cluster_rerank.py:22` skip without
  `svoe-wino-hackaton` or `svoe-vino-matcher`. `test_runner_smoke.py` skips without
  `zxingcpp`, which the system `python3` does not have.
- Fix: temporary fake packages, fixtures for the constants, and `zxing-cpp` in the test
  requirements.

**W-24. Low-severity test and script defects.**

- A direct run of `tests/test_import_website.py` skips 16 of 37 tests: the `__main__`
  block (line 463) comes before three classes. `COMMANDS.md:107` shows the direct-run
  style.
- About 100 SQLite connections stay open: `with self.connect() as conn:` does not close
  the connection (31 uses in `test_describe_images.py`, `test_image_details.py`,
  `test_image_descriptions.py`; `tests/image_description_fixture.py:69-72`). The pipeline
  code closes its connections with `closing()`, so the lab server does not leak. The
  warnings add about 100 lines of noise to each run of the suite. Fix:
  `contextlib.closing` in the fixture.
- Two tests depend on timing (`test_describe_images.py:720-729`,
  `test_embedding_routes.py:412-419`).
- `rescore_runs.py` rewrites `metrics.json` and `summary.md` in about 379 run
  directories, has no test, and stops at the first run with no `summary.md`.
- `build_matcher_bundle.py` shows a configuration error as a traceback and leaves the
  new directory.
- `run_internal_profile_queue.py:218` posts to the fixed address `127.0.0.1:8168`.
- `bench_vlm_models.py` reads `review-labels.json`, `work/state.db`, and `my/`, which
  the workbench does not have.

**Improvements of scripts and tests.**

1. A GitLab job `workbench-tests`, also on changes of `matcher/**`, and a `Makefile`
   target (rule 35). Add `ruff check --select F`.
2. One isolation module for the suite: it points `model_cache.ROOT` to a temporary
   directory and refuses non-loopback connections. Today `model_cache.py:33-34`
   defaults to the real cache and `derive.py:78` to gx10. Each test file redirects them
   itself.
3. Share the test fakes: six `FakeSam3` classes, eight `sha()` helpers, four separate
   loads of `review_server.py`.
4. Delete dead code: `scripts/common.py:399-539, 566-584`, `scripts/04_verify.py.bak`,
   `bench_vlm_score.py`, `compare_runs.py` (copies of the `svoe-vino-testset` files).
5. Move the one-off experiment scripts (about 6,200 lines) to `scripts/experiments/`
   with an index. They compute p95 in two different ways.

Pipeline modules with no test file of the same name: `dis_litert.py` (partly tested
through `test_embeddings.py`; `Segmenter` has no test), `imagestore.py` (only through its
13 importers), `label_description_routes.py`, `run_job.py`, `wine_identity_vlm.py` (all
tested indirectly), and the CLI of `build_label_rules.py` (no test).

### 6.6 Documentation

**W-25. The README starts with the layout of another project.**

- Severity: high. Status: verified. Lead check: read `README.md:1-16`.
- Problem: lines 3-16 describe the tree of `svoe-vino-testset`: `eval/` with 3 photos,
  `my/`, "the five pipeline stages", `excluded-slugs.json`, `manual-groups.json`. None
  of these exists in `workbench/`. Lines 62-67 say that `config.yaml` holds two keys,
  that the lab server opens the database read-only, and that 5 pages exist. The file has
  13 keys, the server writes, and 7 pages exist.
- Fix: rewrite lines 1-31 from the real tree.

**W-26. The configuration reference describes the wrong file.**

- Severity: high. Status: verified.
- Problem: `README.md:1547-1716` and the header of `config.yaml:1-10` describe
  `config.old.yaml` ("The file MUST hold the key `dataset`"). No reference exists for
  the 13 keys of the lab (`database_file`, `embedding_python`, `new_wine_embedding`,
  `sam3`, `qr_scanner`, `embeddings`, and others).
- Fix: correct the header. Move the old section to the legacy document. Write a table
  of the lab keys.

**W-27. Other document defects.**

| Severity | Defect | Evidence |
|---|---|---|
| medium | `docs/database-structure.html` and `.pdf` describe schema version 17 with 13 tables. The database has version 32, 22 tables, and 2 views. | `database-structure.html:8-10, 248`; `db-export/schema.sql` |
| medium | The root `ARCHITECTURE.md` shows the matcher before the cascade: SigLIP2 and a bundle only, and "does not read `lab.sqlite3`". | `ARCHITECTURE.md:14-15, 38-40, 51, 57` |
| medium | `COMMANDS.md:504-514` ("Импорт старой базы данных") has no code fence, starts in the repository root, and records a past result. The heading `# Android device API` (`:338`) also holds the embedding runs, the bundle, and the cascade. The first command is `rm data/catalog/catalog.sqlite3` with no backup step. `COMMANDS.md:57` says the export writes `excluded-slugs.json`; it does not. | `COMMANDS.md` |
| medium | Deployment documents: a dead image path, two revisions for prod, and decision D3 ("There is no WAN route") next to the public edge `https://chtozavino.ru`. `docs/deployment/01_gx10-public-failover-options.md` is a deployment document in a project directory (workspace rule 28), and says "The current matcher backend is a mock backend". | `deploy/gx10/matcher-prod.md:349`; `deploy/gx10/README.md:74`; `deploy/README.md:14, 31, 147-148` |
| low | Paths broken by the move of plan 73: `../.attick/svoe-vino-lab/` (the real path is `../../.attick/svoe-vino-lab/`), `.claude/skills/...`, and `pipeline/mock_run.py`. | `README.md:2126, 2875`; `SMOKE_TESTS.md:740, 1362, 1743` |
| low | The header of `backends.yaml` names `scripts/match_run.py` as the reader. `pipeline/benchmark.py:55` reads it. | `backends.yaml:1-4` |
| low | Plans 24, 36, 44, 55, 56, 57, 59, and 75 say "done, not committed". Their code is committed. | `docs/plans/75_data-layout.md:4` |
| low | The docstring of `lab_server.py:8-9` says that `/images/...` reads `images/` next to the database. Since plan 75, `cropped` is `catalog/cuts/` and `testset` is `<data root>/testsets/images/`. | `labdb.py:122-132` |

**W-28. Missing documents.**

| Severity | Gap |
|---|---|
| high | No setup path from a fresh clone: the absolute `rootdir`, the name of the checkout directory, `data/` ignored by git, the restore of the database from `db-export/`, and the sibling repositories. `workbench/_submission/config.example.yaml` exists, but no document links it. |
| high | No test guide: `docs/testing.md`, `scripts/test_*.sh`, and a `Makefile` (rules 34 to 36) do not exist. The full-suite command is only in `SMOKE_TESTS.md:2276`. |
| medium | No reference of the environment variables: `QR_SCANNER_ENDPOINT`, `QWENCLOUD_TOKEN_PLAN_API_KEY`, `QWENCLOUD_PAYGO_API_KEY`, `SVOE_VINO_REVIEW_CONFIG`, `SAM3_ENDPOINT` (only 6 scripts read it), `HF_HUB_CACHE`, `DASHSCOPE_API_KEY`. The restart recipe of rule 23 names none of them, so a restarted 8168 can lose the scanner and the cloud keys (plausible; see W-9). |
| medium | No document says that the lab server starts its job scripts from disk (`run_jobs.py:374, 436`, `embedding_routes.py:300`, `cluster_routes.py:69`, `recognize_routes.py:152`). An uncommitted edit in the shared tree is live for the next job with no restart. |
| medium | The detached start of 8168 (`start_new_session=True`) is written only in private agent memory. |
| medium | No module map: `dis_litert.py` and `remote_images.py` (the URL guard of dropped images) appear in no document. All 74 modules have a docstring, so a script can generate the map. |
| medium | The lab run files (`metrics.json`, `summary.md`, `results.jsonl`) are described only in the legacy `docs/match-runner.md`. |
| medium | Two rules select the benchmark photos: the legacy `excluded-slugs.json`, and the lab rule "Active wines only" of plan 87. No document compares them, and `BENCHMARKS.md` does not say which rule its numbers use. |
| medium | The matcher contract (the two views, the base columns of `wine_code` and `wine_catalog`, the catalogue copy, the bundle versions 1 to 3) is in no single document. See 4.2. |
| medium | No glossary. "matcher" has four meanings (the old project, `matcher/`, a backend of `backends.yaml`, the `svm-*` backends). "dataset" has four. |
| low | No index of `docs/plans/` (88 files, numbers 01 to 89). Plan 13 does not exist, but plans 14, 18, and 20 cite it. 28 plans have no status. |

**W-29. The legacy review tool has no boundary.**

- Severity: medium. Status: verified.
- About 47 % of the README (lines 1547-2909), `docs/API.md`, `docs/openapi.yaml`,
  `docs/match-runner.md`, `docs/excluded-slugs.md`, `docs/catalogue-defects.md`, and
  `SMOKE_TESTS.md:5-502` describe `review_server.py` and `match_run.py` on port 8154.
  These tools write the JSON files of `svoe-vino-testset` through `config.old.yaml`.
  No document says that the tools are legacy or that their writes do not reach the lab
  database.
- Fix: move these documents to `docs/legacy/` with a banner. Rename
  `docs/openapi.yaml` to `review-tool-openapi.yaml`.

**W-30. The large files have no archive rule.**

| File | Size | Problem |
|---|---|---|
| `README.md` | 187 KB, 2,909 lines | Reference, history, and legacy tool in one file. |
| `SMOKE_TESTS.md` | 316 KB, 99 sections | No index and no state for each case. 36 matcher cases belong to `matcher/SMOKE_TESTS.md`. Fixed test counts drift ("60 tests", "1,331 tests"). |
| `ChangeLog.md` | 396 KB | 529 lines for 2026-09-29 alone. |
| `ResearchLog.md` | 237 KB | 106 entries; the date order breaks at lines 3482-3500. |
| `docs/owner-messages.md` | 379 KB | One file for all messages. |
| `ACTIVE_WORK.md` | 270 KB, 73 sections | See C-3. |

**Improvements of the documents.** A proposed structure, sized for the owner and the
agent sessions:

1. `README.md` becomes an entry page of at most 150 lines: the real tree, "start here"
   links, and a map of the 7 pages. The lab topics go to `docs/lab/<topic>.md`. Lines
   1547-2909 go to `docs/legacy/review-tool.md`. Command blocks go to `COMMANDS.md`
   (rule 29).
2. Five short system documents: `docs/setup.md`, `docs/testing.md`,
   `docs/configuration.md` (keys, variables, and which tool reads which file),
   `docs/glossary.md`, `docs/matcher-contract.md`.
3. Generated reference documents with a test that fails when they are stale:
   `docs/modules.md` from the docstrings, `docs/database.md` from `db-export/schema.sql`,
   `docs/plans/README.md` with one status vocabulary.
4. `COMMANDS.md`: a table of contents, one heading per component, a mark on each block
   (read-only, changes data, calls a service), a backup step before each destructive
   command.
5. `SMOKE_TESTS.md`: one file per component with an index of case identifiers. Write
   "all tests OK" instead of fixed counts.
6. `ChangeLog.md` and `ResearchLog.md`: keep the current week; move older entries to
   archive files. The owner decides the same for `docs/owner-messages.md` (rules 1 to 8).

## 7. Cross-cutting findings

**C-1. CI.**

- Severity: high. Status: verified. Lead check: GitLab API.
- The owner decided on 2026-09-30 to use only the home GitLab. The last 6 pipelines on
  `main` failed (#326 to #331, from 2026-09-29T07:17Z). The last success is #325
  (2026-09-28). The failing job is `webui-tests`: the runner `docker-srv-runner` cannot
  pull `node:24` from Docker Hub (`runner_system_failure`). The job `matcher-tests`
  passes. A red pipeline is now normal, so a real failure is not visible.
- The GitLab matcher job installs `matcher/requirements.txt` with no hashes and does not
  fail on skipped tests. `matcher/tests/run_ci.sh` does both, but only the unused GitHub
  workflow calls it. The image tag `python:3.11-slim` is not pinned by digest.
- No CI job runs the 1,477 workbench tests, the 7 inspector tests, or the lab-to-matcher
  contract tests (`test_matcher_parity.py`, `test_catalog_copy.py`,
  `test_matcher_views.py`).
- Fix: put `node:24` into `registry.my.3simbio.ru`, or set the pull policy
  `if-not-present`. Make the matcher job run `bash matcher/tests/run_ci.sh`. Add jobs for
  the workbench and the inspector. Remove `.github/workflows/` and the GitHub runner
  section of `COMMANDS.md:536-567`.

**C-2. Repository size.**

- The pack is 2.17 GiB. Git tracks 5,965 files of `workbench/data` with no LFS; some
  images have 20 MB. `.git/objects/pack/` holds 4 left-over `tmp_pack_*` files.
- Improvement: keep the catalogue images in Git LFS or in the SeaweedFS S3 store of the
  workspace. The owner can remove the `tmp_pack_*` files when no git process runs.

**C-3. `ACTIVE_WORK.md` no longer works as intended.**

- 73 sections. 63 say "done, not committed", although the checkpoint commits `587ac00`
  and `b533473` hold that work. `drink-atlas-workspace-ad [139787]` has 3 sections
  (rule 14). The sections `/root` (470 lines) and `root` (643 lines) have no valid
  session name. Rule 13 makes each session read about 67,000 tokens at the start and
  before each change. Rule 21 blocks a cleanup.
- Improvement (owner decision): after a checkpoint commit, move the done sections to an
  archive file. Keep each section short and each name unique.

**C-4. A rule in the root `AGENTS.md` cannot be followed.**

- `svoe-vino-lab/AGENTS.md:4` asks agents to set file times to a time before
  2026-09-29 23:59:00 before they send files to a server. This misstates the time of a
  delivery. Agent sessions do not follow it. A session declined a related request
  (owner message of 2026-09-30T00:32:00+0300).
- Improvement: remove the rule, so that sessions do not stop at it. The file is also not
  tracked by git, and the root has no `CLAUDE.md` link to it.

## 8. Suggested order of work

Stage 1. Prod safety and CI. Small changes.

1. C-1: repair the `webui-tests` image pull; run `run_ci.sh` in GitLab; add the workbench
   and inspector jobs.
2. M-3: strict configuration keys.
3. M-1: continue after an EXIF error. M-2: answer the request after an archive error;
   decide the retention period (SV-SEC-01).
4. W-11 and W-13: `formats=` and a pixel check in the upload checks; decode before the
   transaction.
5. M-8: add `/work/` to the root `.gitignore`.

Stage 2. Trust in the benchmark numbers.

6. W-1 and W-2: the guard between test sets and catalogue; no test tables in the copy.
7. W-3: state the tuning in `BENCHMARKS.md`; keep one frozen set.
8. M-4: the same SAM3 filter and input in prod and in the lab; parity tests.
9. W-7, W-8, W-9: runs that fail per photo, not per run, and that show a degraded step.
10. M-5, M-6: complete candidate lists in cascade `/v1/match`.

Stage 3. Data safety and server errors.

11. W-4: backups and SHA-256 matching in the import and seed tools. W-5: the watcher.
12. W-15: one error wrapper in the lab server. W-14: bind the fetch check to the
    connection.

Stage 4. Lab server and pages.

13. W-12: the `Origin` check. W-17: "latest request wins". W-18: theme tokens.

Stage 5. Documents (the owner decides the structure).

14. W-25 and W-26: the README head and the configuration reference.
15. W-28: `docs/setup.md`, `docs/testing.md`, an environment table, a module map.
16. W-29 and W-30: the legacy boundary, archive rules, and indexes.
