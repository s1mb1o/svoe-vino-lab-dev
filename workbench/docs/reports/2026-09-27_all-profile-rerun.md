# Complete profile rerun

Date: 2026-09-27.
Status: running. All benchmark comparisons are complete. The first internal profile started at 03:57:01 MSK.

## Request and scope

The owner requested a new run of every profile.
Use the same test set, `my`.
The queue is `2026-09-27_all-profile-rerun/queue.json`.
The queue records the profile names and availability at the time of the request.
Read [preflight.md](2026-09-27_all-profile-rerun/preflight.md) for the actual model groups,
internal endpoints, memory rules, and index coverage before dispatch.
The current configuration has 54 profiles. The test set has 2228 queries.
The new `barcode-rerank-siglip2-512-crop-label` profile is included.
Preserve all previous runs.

The existing heartbeat `benchmark-barcode-speed-after-current-run` executes the queue.
Finish the barcode, crop, bulk, and sequential demo comparisons first.
Do not run competing measurements at the same time.

## External recognizer approval

Automatic approval review rejected a scheduler update that included
`vino-svoe-search-by-photo`.
The rejection requires explicit approval to send all 2228 photos to
`https://api.vino-svoe.ru/v1/wines/search-by-photo`.
An approval question is pending in the task.
The queue marks this profile `awaiting_user_approval` and `authorized_to_start: false`.
Do not launch that profile unless the owner explicitly approves that transfer.
Do not treat the absence of an answer as approval.
Continue the other 53 profiles independently.

## Preparation

49 internal or local profiles have index files at queue time.
Four more profiles need the same index:
`gx10-siglip2-so400m-patch16-naflex-p1024`.
The dependent profiles are `siglip2-p1024-as-is`, `siglip2-p1024-crop`,
`barcode-siglip2-p1024-as-is`, and `barcode-siglip2-p1024-crop`.
Build that index once through the existing embedding build workflow.
Then recheck those four profiles.
File existence alone does not establish that vectors are current or that a service is available.

Before any model call, read `/Users/ashmelev/Admin/GPU_SERVERS.md` and
`/Users/ashmelev/Admin/GPU_TASKS.md`.
Check live memory and active jobs. Record this workload in the task tracker.
Use the configured internal endpoints and existing models.
Use `SAM3_ENDPOINT` for SAM3.
Do not stop unrelated jobs or restart GPU services.
Check configuration changes against the queue's saved hash.
Record changes that affect comparison.
Record the selected photo hashes and labels at batch start.
Compare each completed run's query artifact with that selection.

## Execution

Run one profile at a time.
Group profiles by embedding model to reduce model switches.
Use caches and the configured barcode step.
Use four query workers for internal remote embedding profiles.
Use one worker for the four `local-siglip2-p256` profiles and their barcode variants.
If the external recognizer is approved, use four workers for that profile too.
Do not apply a query limit.

Use `POST /api/run-jobs` on the existing lab server at port 8168.
The body contains `configuration`, `set: "my"`, `workers`, `use_cache: true`,
and `use_barcode: true`.
The existing runner writes the new artifacts to `runs/`.
The lab shows those artifacts on the Runs page.
The CLI `pipeline/run_job.py` is an equivalent fallback when the API is unavailable.

Check all active runner processes, live job locks, and benchmark processes before dispatch.
Backend construction occurs before the first `start` log event.
A live job lock can therefore coexist with an empty or old API job state.
Verify each PID's command. A verified live runner blocks another launch.
Profile locks do not provide global serialization.

Save launch intent in the queue before each POST.
The API has no idempotency key.
After an uncertain response, reconcile locks, processes, and log timestamps.
Do not retry the POST without reconciliation.
Save the PID, attempt number, start time, and run ID.
Archive each attempt's log under the queue output directory.
A new start replaces the live per-profile `job.log`.
The runner has no per-query resume. A retry is a new complete attempt.
Preserve failed and stopped attempts.

## Completion and report

A successful profile needs a final `done` event, zero errors, complete persisted artifacts,
the expected query coverage, and an exited runner.
Exit code 0 alone is insufficient. Stopped runs and runs with query errors can exit 0.
Record failures explicitly. Continue independent profiles when an endpoint fails.
Do not silently omit a profile with an unavailable index or model.

For each attempt, record run ID, query count, wall time, throughput, latency distribution,
recall at 1, recall at 5, negative false matches, and errors.
Compare the new label profile with its full-only counterpart.
Report cache use. Cached bulk timings do not establish the new-photo demo deadline.
Deliver the final comparison in Russian.
Keep the heartbeat active until the preceding comparisons and all authorized queue work
have terminal outcomes and reports. Keep unresolved approval visible.


## NaFlex-1024 build preparation

Read-only inspection at 2026-09-27T02:10+0300 found 4183 planned items for the new index.
The active inputs include 59 missing label derivatives, two not-applicable labels,
and zero missing package derivatives or source files. Recompute these counts before work.
The unfiltered `seed_label_cuts.py` would process 66 originals. Seven are outside this
index's active input set. Do not use that unfiltered pass for this task.

The embedding build does not derive missing SAM3 crops. Use the existing derivative
functions for only the missing active label digests after all barcode comparisons end.
Freeze that selection from `embeddings.read_inputs()` and `embeddings.plan_items()`.
For each selected digest, recheck active membership and derivative availability.
Preserve current cuts, all manual cuts, and current absence markers.

Call `alternatives.process_image(conn, db_path, digest, path, "label", segmenter,
warnings)` outside a write transaction. Construct the client from `SAM3_ENDPOINT`.
When the result has `links` or `not_applicable`, start `BEGIN IMMEDIATE` and recompute
eligibility. Check `alternatives.has_current_cut()` and `alternatives.current_absence()`
again. Write with `alternatives.write_processed_rows()` only when the same active
source still needs that derivative. Commit the write. Roll back a failed transaction.
Skip a source that another writer completed. Stop on `result.unavailable` and preserve
unresolved `no_label` results in the report.

Then use the existing build endpoint:

```text
POST http://127.0.0.1:8168/api/embeddings/gx10-siglip2-so400m-patch16-naflex-p1024/build
```

No request body is required. HTTP 202 returns the PID.
The equivalent CLI is:

```sh
/Users/ashmelev/.venvs/svoe-vino-lab/bin/python pipeline/build_embeddings.py \
  --config config.yaml --name gx10-siglip2-so400m-patch16-naflex-p1024
```

The incremental build preserves current vectors, retries missing or failed items,
and replaces stale items. It checkpoints every 30 seconds. It does not change
`clusters.json` or `cluster-rules.json`.

The configured model is `siglip2-so400m-patch16-naflex` at the internal GX10 embedding
endpoint. The request uses `max_num_patches: 1024`, batch size 16, and dimension 1152.
`/Users/ashmelev/Admin/gx10/MODELS.md` gives an approximate resident size of 7 GB.
The batch peak is not established by that resident estimate. Apply the required
20 GB safety margin and recheck memory when model residency changes.
Do not stop existing model services to make room.

Save build intent before dispatch. Reconcile the returned PID command, `build.lock`,
and `build.log` before a retry. Require process termination and the final `done` event.
Exit 0 alone does not prove that every item was built. Inspect current, stale, missing,
and failed counts. Validate the index and vector file before running dependent profiles.
Only this new index is scheduled for a build. Report its coverage alongside the existing
indexes. Different catalogue coverage can affect cross-model comparisons.


## Restricted label-input helper

`scripts/prepare_rerun_label_inputs.py` implements the missing-label prerequisite.
The default dry run is read-only. It opens no SAM3 client and writes no database row.
The saved dry run in `2026-09-27_all-profile-rerun/label-input-dry-run.json` selects
exactly 59 active full-photo label sources. It excludes closeups, replaced main photos,
all existing derivatives, manual cuts, and current absence markers.

The helper passed 13 fixture tests. An independent review verified the execution
guards after three fixes. Source bytes are checked again inside the write transaction.
A segmenter proxy validates the parent gate before every detection call.
Acquired sessions and database connections close even when setup fails.
No production execution has occurred. The reviewed helper is ready for the later step.

After all benchmark comparisons finish, run the dry run again and review the selection.
Then record a fresh parent gate. Its schema is in the helper docstring and `--help`.
The gate binds the configuration hash, absolute database path, exact embedding name,
and canonical internal SAM3 endpoint. It references existing evidence for completed
comparisons, reconciled processes, GPU memory checks, and task registration.
The gate expires after 600 seconds. Do not manufacture a completion flag for unfinished
comparisons. The helper also holds the shared measurement lock during execution.

Execute with `--execute --gate <gate.json> --output <new-report-directory>` and the
canonical `SAM3_ENDPOINT`. The helper rechecks active membership and missing cuts
before processing and inside `BEGIN IMMEDIATE`. It checks source bytes before commit.
It preserves a source that another session changed or completed. It stops on service
unavailability. It records unresolved `no_label` and unprocessed sources explicitly.
A stale gate cannot authorize later requests or a commit. For unfinished work, use
a fresh gate and a new output directory. Existing cuts are excluded on continuation.

The helper does not build the embedding index. After inspecting its terminal report,
continue through the existing build endpoint documented above. Keep the index build
and profile launches out of every active barcode timing interval.


## Prepared one-profile queue dispatcher

`scripts/run_internal_profile_queue.py` is a separate execution helper.
Default inspection is read-only.
The helper passed 23 fixture tests.
The final independent review passed.
The helper is ready and unexecuted.
A real read-only inspection selected `siglip2-512-as-is` and found 2228 query rows.
Its embedding endpoint is `http://192.168.86.14:18081/v1`.
The queue SHA-256 stayed unchanged.
See `2026-09-27_all-profile-rerun/queue-helper-inspect.json`.

Use `--profile NAME` to obtain the current input fingerprint.
Use `--execute --profile NAME --gate FILE` only after the benchmark comparisons finish.
The fresh parent gate schema is in the helper docstring and `--help`.
The helper dispatches at most one POST through the existing local run-job API.
It preserves launch intent before POST.
An existing attempt permanently suppresses another POST from this helper.
A lost launch response needs reconciliation, not an automatic retry.
Use `--reconcile --profile NAME` to record observed progress or terminal artifacts.
Reconciliation never launches a job.
The parent owns retry decisions and model-group order.

The helper rejects the external profile even if an authorization flag changes.
It requires a fresh gate, private literal model endpoints, ready index evidence,
query source verification, and a memory budget with a 20 GiB margin.
Local profiles also require evidence that local weights are ready.
The helper rechecks live input identity after durable intent and before POST.
It rejects live or uncertain recorded attempts and native/API jobs.
A completed run requires matching options, full query/result/prediction coverage,
no query errors or trace-step failures, and matching final metrics.
The helper archives the job log and artifact hashes.
It does not build indexes, load models for probes, stop services, or loop over profiles.
No production queue write or launch was made during preparation.


## Queue execution checkpoint

The first launch is `siglip2-512-as-is`, PID 7235.
The run ID is `2026-09-27T005701Z-lab-siglip2-512-as-is-my`.
The API accepted the durable launch intent with HTTP 202.
The helper verified its command and saved its running state.
The source-byte check covers all 2228 rows and 1851 unique paths and digests.
Every SHA-256 matches the frozen query metadata.
GX10 had 44.44 GiB available before dispatch.
The SigLIP2-512 model was ready.
The budget retains a 7 GiB transient allowance and a 20 GiB margin.
Read `query-source-validation.json`, `g1-preflight-1.json`, and the attempt archive.
All next launches need reconciliation and a fresh gate.


## Unreaped runner process

The first runner completed at 03:58:21 MSK with 2228 answers and zero errors.
The lab server retained PID 7235 as an unreaped macOS child.
`ps` reported status `Z` and command `<defunct>`.
The queue helper now treats confirmed `Z` as terminated execution.
It records that termination evidence explicitly.
It still requires the expected final event and complete validated artifacts.
Unknown or malformed process output does not prove termination.
The helper has 25 passing fixture tests after this correction.
No profile launch was retried.
No server process was changed.


## Second profile and offline summary

The first profile is validated as `done`.
It has 2228 results, zero errors, R@1 0.7993, and R@5 0.9544.
Its archived attempt records the confirmed zombie termination evidence.
The second profile, `siglip2-512-crop`, started at 04:04:30 MSK.
Its runner PID is 32985.
Its run ID is `2026-09-27T010430Z-lab-siglip2-512-crop-my`.
The queue remains serial.

`scripts/summarize_internal_profile_queue.py` reports saved queue and archive evidence.
It starts no job and changes no queue.
Use a new output directory for every snapshot.
The helper passed ten fixtures and independent review.
The first real snapshot is `snapshot-0406/queue-summary.md`.
It reports one complete authorized profile and preserves all 54 queue entries.
Its status is partial.


## Third profile checkpoint

The first two profiles are validated as `done`.
Both have 2228 answers and zero query or trace errors.
`siglip2-512-as-is` has R@1 0.7993 and R@5 0.9544.
Its recorded run wall is 80.0 seconds.
`siglip2-512-crop` has R@1 0.8072 and R@5 0.9574.
Its recorded run wall is 98.8 seconds.
These cached bulk values do not establish new-photo latency.

`barcode-siglip2-512-as-is` started at 04:07:44 MSK in PID 43726.
Its run ID is `2026-09-27T010744Z-lab-barcode-siglip2-512-as-is-my`.
The helper verified the exact runner command.
Preflight found 40.50 GiB available and the required model ready.
All 1851 query source file hashes were checked again before launch.
Read the queue for newer progress before another launch.
The partial report is `snapshot-0408/queue-summary.md`.


## NaFlex-1024 execution checks

Offline review at 04:14 MSK still selects 59 missing active label sources.
Do not execute the preparation during a profile run.
The label helper can exit zero with unresolved `no_label` records.
Inspect its selection, results, and summary before the build.
The build API has an index-specific lock, but no global queue or measurement lock.
The parent must serialize the build with all profile jobs.
Preserve each build log before an explicitly reviewed retry.

The service documentation records a successful batch of 16 images at 1024 patches.
It records 650 ms for that batch.
It does not establish a peak-memory measurement.
Before an unloaded NaFlex build, budget 7 GiB for model residency and 7 GiB for
transient work, in addition to the required 20 GiB margin.
The transient value is a conservative allowance, not a measured peak.
Check current residency and available memory again before dispatch.
Do not load a model through a health probe.

Before dependent profiles, validate float32 vectors with shape N by 1152.
N must equal the stored index item count.
Require unique item keys and contiguous row numbers.
Check finite, nonzero, unit-normalized vectors.
Validate vector-file hashes, prepared-image files, and current embedding hashes.
Recompute coverage and absence markers after label preparation.
Do not reuse an earlier catalogue fingerprint after derivative writes.


## Production source control

At 04:17 MSK, all 57 production `pipeline/*.py` files still matched the final HTTP
manifest. No file was added or removed in that scope.
Read `g1-production-source-check.json`.
Independent read-only review confirmed the first four completed queue runs.
Their query identities, artifact hashes, saved predictions, metrics, and archives agree.
No source image was decoded or sent during the review.


## New label profile launch

Six G1 profiles have validated complete artifacts.
Each has 2228 rows, 1851 image digests, and zero query or trace errors.
The reference barcode/rerank profile reproduces R@1 0.8467 and R@5 0.9702.
The partial report is `snapshot-0420/queue-summary.md`.

The new `barcode-rerank-siglip2-512-crop-label` profile started at 04:19:51 MSK.
Its PID is 84780.
Its run ID is `2026-09-27T011951Z-lab-barcode-rerank-siglip2-512-crop-label-my`.
The dispatcher verified the runner command.
Its preflight found 41.17 GiB available and all required models ready.
Keep the same 7 GiB transient allowance and 20 GiB margin.
Do not start preparation, a build, or another profile until this run terminates.
The label profile can populate response caches that earlier profiles did not use.
Record actual cache-hit counts by stage before comparing elapsed times.
A cache-enabled flag alone does not prove equal cache warmth.


## Preliminary local capacity

Read `2026-09-27_all-profile-rerun/local-readiness-preliminary.md` before G10.
The runtime and cached model files appear available.
The Mac currently has high memory pressure and nearly full swap.
This snapshot is not a launch gate and does not mark the local profiles failed.
Check current capacity again before a local model load.
The full float32 model has 4.231 GiB of weights.
The proposed additional loading allowance is unmeasured.
Cached files do not prove that `from_pretrained` will avoid metadata requests.


## Prepared G2 validator

`2026-09-27_all-profile-rerun/validate_naflex_index.py` is ready.
The utility passed compilation and parent source review.
It has not run against an index.
Use the configured embedding interpreter after the build terminates.
It checks the expected internal configuration, vector-file hash, float32 dimensions,
finite normalized vectors, unique item keys, and contiguous row numbers.
It reports current, missing, failed, stale, and not-applicable counts per view.
It also reports unique Active wines with at least one current vector per view.
Source and prepared-image bytes are not decoded or hashed by this utility.
Its coverage check uses current metadata and prepared-file presence.
The parent must separately verify that the matching build PID exited.
Exit zero permits explicit incomplete coverage; inspect the saved JSON before launch.


## G1 completion and G2 execution

All seven G1 profiles have validated complete artifacts with zero errors.
The new label profile completed at 04:34:46 MSK.
It has R@1 0.8291 and R@5 0.9647 on the same 2228 queries.
The full-only reference has R@1 0.8467 and R@5 0.9702.
The saved partial queue report is `snapshot-0435/queue-summary.md`.
The separate paired analysis uses frozen G1 evidence.

Restricted label preparation started at 04:35:41 and finished at 04:36:25 MSK.
It processed all 59 selected sources in 44.58 seconds of process wall time.
It wrote 57 derivatives. Two sources returned `no_label`.
No source remains unprocessed. The process exited zero.
The two unresolved sources remain in the preparation summary.
No existing or manual cut was selected for replacement.
Child PID 38326 and supervisor PID 38324 have exited.
Read `g2-label-process.json` and `g2-label-preparation-1/summary.json`.

The NaFlex-1024 build started at 04:38:05 MSK in PID 46597.
The API accepted one saved launch intent. Its exact command was verified.
The build plans 4183 items. The model was initially unloaded.
GX10 had 41.83 GiB available. The budget allows 14 GiB additional work and a
20 GiB margin. The 14 GiB allowance includes residency and transient work.
Read `g2-build-process.json`, the live build log, and `g2-build-preflight.json`.
Reconcile the existing attempt before any later action. Do not repeat the POST.
Validate terminal artifacts and coverage before dependent profile runs.


## Initial NaFlex service failure

The first 16-item batch exhausted the existing request retries.
The gateway returned HTTP 500 with `upstream command exited prematurely`.
The first failure was recorded at 04:39:39 MSK.
Later batches successfully returned embeddings.
Read `g2-build-startup-observation.json`.
The HTTP status alone does not establish OOM or a specific startup cause.
A separate read-only log inspection is pending.
Keep the first attempt and its 16 failure observations.
After completion, reconcile the build before considering an incremental retry.
Preserve its log, index, vector artifact, and hashes before a new POST.
The two unresolved `no_label` sources are a separate input-coverage condition.


## NaFlex build completion and stronger memory gate

Read `g2-build-cuda-startup-evidence.json`.
The model logs confirm CUDA allocation failure during model transfer to the device.
Four startup processes failed. The fifth startup succeeded.
The initial parent snapshot had 8.085 GiB free and 41.830 GiB available.
The successful wrapper snapshot rounded these values to 14 GiB and 47 GiB.
The existing wrapper also dropped page caches once during a failed startup.
The agent did not issue that command or change the wrapper.
The underlying allocator or page-cache cause is not established.
The observations do not prove a universal successful allocation threshold.

Before a future unloaded model, apply both memory checks.
`MemAvailable` MUST cover the additional residency and transient allowance plus 20 GiB.
`MemFree` MUST cover the additional residency and transient allowance.
Wait for capacity when either check fails. Do not stop services or drop page caches.
This is a conservative parent execution gate. It is not a production service change.

The first build completed 4183 planned items at 04:45:36 MSK.
It stored 4165 vectors. It recorded 16 startup failures and two missing label cuts.
Its log, index, vector file, hashes, and terminal process record are archived in
`g2-build-attempt-1`. The first validation passed with explicit incomplete coverage.

The parent reviewed one incremental retry after the first PID exited.
NaFlex was ready. Fresh memory was 41.82 GiB available and 9.14 GiB free.
The gate retained 7 GiB transient allowance and 20 GiB available margin.
PID 80032 completed the 18 pending items at 04:47:57 MSK in 4.0 seconds.
It added 16 vectors and retained only the two known missing label inputs.
The second attempt is archived in `g2-build-attempt-2`. No further retry is needed.

The final validator passes with 4181 float32 vectors of dimension 1152.
All vector norms are within 1e-5 of one. The vector content hash matches its filename.
The final coverage is 2086 current full items and 2095 current label items.
There are zero missing or stale items, two failed label items, and two not-applicable labels.
Current wine coverage is 2096 full and 2092 label, versus 2051 and 2047 in older indexes.
Keep this catalogue-coverage difference visible in cross-model comparisons.
Read `g2-build-validation-2.json` for exact hashes and remaining source digests.

`siglip2-p256-as-is` started at 04:49:51 MSK in PID 85884.
Its run ID is `2026-09-27T014951Z-lab-siglip2-p256-as-is-my`.
The exact runner command and fresh source hashes were verified.
Its preflight had 41.88 GiB available with NaFlex ready and the free-memory check passed.
The queue remains serial with four workers and the configured caches.

The final paired label report passed independent review.
Read `label-comparison-final.md` and its JSON evidence.
The label profile loses 29 net top-1 successes and 9 net top-5 successes.
It adds 4 net forbidden negative top-1 predictions.
Its first-run label and VLM cache misses prevent equal-cache timing claims.


## Second G2 profile checkpoint

Eight authorized profiles are validated complete.
`siglip2-p256-as-is` has R@1 0.6533 and R@5 0.8692 in 81.1 seconds.
It has 2228 rows, zero query or trace errors, and unchanged input identity.
Its PID 85884 has exited.
`siglip2-p256-crop` started at 04:52:29 MSK in PID 95602.
Its run ID is `2026-09-27T015229Z-lab-siglip2-p256-crop-my`.
The launch gate had 39.91 GiB available and 7.23 GiB free, with both needed models ready.
Use the queue and live log for newer progress.
The partial summary is `snapshot-0454/queue-summary.md`.
The parent G2 launch template is saved in `g2-profile-launch-template.txt`.
It requires a ready model and launches at most one listed profile.
Review every fresh gate. Do not use the template to repeat an existing attempt.


## Capacity wait before NaFlex-512

The first NaFlex-512 preflight at 05:00:53 MSK had 6.79 GiB free and 39.48 GiB available.
The ready-model gate requires 7 GiB free and 27 GiB available.
The parent withheld the launch. No inference attempt was created.
A later preflight passed after memory changed naturally.
Both observations remain in `preflight_checks` on the queue row.

Keep a temporarily capacity-limited profile in the supported `pending` state.
Record waiting evidence in `preflight_checks`.
The launcher accepts only `pending` or `waiting_for_index` before a first attempt.
A parent change to `waiting_for_capacity` caused a pre-launch refusal.
The parent verified empty attempts and no active jobs, then restored `pending`.
The refusal occurred before durable launch intent and before POST.
The first actual dispatch started PID 34046. No POST was duplicated.

For a terminal unavailable profile that never launches, use `status: unavailable`
and a capacity reason with evidence path and hash. Keep the attempt list empty.
The offline reporter counts that outcome as terminal but unsuccessful.
The current memory wait is not an unavailable outcome or an inference failure.


## Later remote group launch template

The parent and an independent reviewer checked `remote-group-launch-template.txt`.
Read `remote-group-template-review.json` for the exact reviewed hash.
The template allows one listed G3 through G9 profile per invocation.
The parent MUST reconcile the previous attempt before using the template.
The template binds the actual inference destinations to the checked GX10 services.
It reads `/running` and `/v1/models`. It does not probe an unloaded upstream service.
It includes the target residency allowance when the target is not ready.
It requires both memory thresholds and ready shared services.
It checks configured build locks, native processes, queue attempts, and query hashes.
It records each refused preflight separately and keeps the queue row pending.
It creates one durable dispatcher attempt after a successful gate.
An uncertain response MUST be reconciled. The template never retries a POST.
Static preparation performed no inference or network request.


## G2 completion and first G3 runs

All 14 G2 profiles completed with 2228 rows, 1851 image digests, and zero errors.
The seven G1 profiles also remain complete. The first G3 profile is now complete.
The partial queue snapshot is `snapshot-0541/queue-summary.md`: 22 of 53 authorized profiles.
The external recognizer remains excluded pending explicit photo-transfer authorization.

Read `g2-plain-comparison.md` and `g2-plain-comparison-review.json`.
The review verifies exact paired query lists and the broader p1024 index coverage.
The barcode paired report is `g2-barcode-comparison.md`.
Its review status is recorded separately when final verification completes.
`g2-production-source-check.json` confirms identical source hashes across all 21 G1/G2 runs.
All 57 current production pipeline files also match those hashes.

The first DINOv3-B preflights refused the launch at 8.01 and 8.38 GiB free.
The target was unloaded. The required additional allowance was 9 GiB.
No attempt or POST was created by either refusal.
The third preflight passed at 45.71 GiB free and 78.70 GiB available.
The task made no service change. The cause of the capacity increase is not established.
PID 64861 completed `dinov3-vitb16-as-is` with full validation.
The next profile, `dinov3-vitb16-crop`, started at 05:40:04 MSK in PID 70653.
Its run ID is `2026-09-27T024004Z-lab-dinov3-vitb16-crop-my`.
Read the live queue and reconcile this attempt before another launch.

The final G2 barcode comparison passed independent review.
Read `g2-barcode-comparison-review.json` for the final artifact hashes.
At 2026-09-27T05:44:47.142760+03:00, 23 profiles are validated complete.
`barcode-dinov3-vitb16-as-is` is running in PID 84785.
Its run ID is `2026-09-27T024350Z-lab-barcode-dinov3-vitb16-as-is-my`.
The current partial snapshot is `snapshot-0544/queue-summary.md`.


## DINOv3 completion and annotation audit

All eight G3 and G4 profiles are validated complete.
Each profile has 2228 rows and 1851 image digests.
Each profile has zero query or trace errors and no per-run input drift.

| Profile | R@1 | R@5 | Forbidden top-1 / 584 | Runner wall, s |
|---|---:|---:|---:|---:|
| `dinov3-vitb16-as-is` | 34.61% | 62.96% | 65 | 73.6 |
| `dinov3-vitb16-crop` | 42.82% | 73.24% | 80 | 87.8 |
| `barcode-dinov3-vitb16-as-is` | 35.95% | 64.23% | 65 | 67.0 |
| `barcode-dinov3-vitb16-crop` | 44.16% | 74.51% | 80 | 84.8 |
| `dinov3-vitl16-as-is` | 29.81% | 57.36% | 46 | 91.1 |
| `dinov3-vitl16-crop` | 43.37% | 73.48% | 65 | 96.6 |
| `barcode-dinov3-vitl16-as-is` | 31.20% | 58.64% | 46 | 78.4 |
| `barcode-dinov3-vitl16-crop` | 44.77% | 74.76% | 65 | 91.4 |

These are configured-profile results on the fixed test set.
All runs use four workers and caches. These wall times do not measure demo latency.

The frozen annotation audit passed parent and independent review.
Read `annotation-audit.md` and `annotation-audit-review.json`.
It finds 67 digest groups with incompatible exact-slug positive constraints.
The groups contain 136 positive rows and 70 disjoint positive-row pairs.
No positive accepted slug is forbidden by a same-digest negative constraint.
Under identical-bytes, identical-answer, and no-row-metadata assumptions, the optimistic
positive top-1 ceiling is 1576/1644 (95.8637%). The minimum is 68 missed positive rows.
This is a conditional metadata bound. It is not an achieved model result.
The audit does not establish which label is correct. It changes no label or score.
The raw 1644-positive and 584-negative denominators stay unchanged.


## Final queue outcome

All 53 authorized profiles have terminal outcomes.
The final snapshot is `2026-09-27_all-profile-rerun/final-snapshot/queue-summary.md`.
Its status is `terminal_with_failures`: 48 validated successes, one invalid completion,
and four unavailable local profiles. The 54th configured external profile remains excluded.

Read `2026-09-27_all-profile-rerun/final-profile-comparison.md` and its metrics JSON.
The report keeps all configured profiles visible and separates bulk throughput from demo latency.
The reference has the highest successful R@1: 1392/1644 (84.67%).
NaFlex-1024 crop with barcode has the highest R@5: 1611/1644 (97.99%), with broader coverage.
The new label profile has R@1 1363/1644 (82.91%) and remains below the reference.

The first SigLIP2-p14-384 as-is run retains eight positive embedding errors.
Its process ended after all 2228 rows. Its state remains `invalid_completion`.
The reviewed archive preserves all five run artifacts, all raw metrics, and the 24 client retry events.
Gateway logs show premature upstream exits and later recovery. The startup root cause is unknown.
The three subsequent profiles of that model completed without query errors.
No failed profile was retried.

The final local capacity observation is at 06:51:39 MSK.
The 16 GiB additional allowance plus the unchanged 20 GiB reserve exceeds the 32 GiB Mac.
All four local rows have `unavailable`, empty attempts, and null PID/run ID.
This is an outcome under the current policy, not a claim that the model can never run locally.
No application was stopped and no memory reserve was reduced.

The external recognizer retains `authorized_to_start:false` and pending explicit transfer approval.
No photo was sent to `api.vino-svoe.ru` by this execution.
