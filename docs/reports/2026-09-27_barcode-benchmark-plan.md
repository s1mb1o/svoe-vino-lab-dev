# Barcode speed benchmark plan

Date: 2026-09-27.
Status: all required comparisons are complete. The authorized internal/local profile queue started at 03:57 MSK.

## Owner requirements

The owner set two separate objectives:

1. Repeat the bulk benchmark quickly.
2. Return a recognition result within 3 seconds for the hackathon demo.

Demo images arrive sequentially.
The demo needs low latency for one image.
The demo deadline is interpreted as total recognition time, including barcode decoding.
Do not report four-image throughput as single-image latency.
Do not use a repeated-photo cache hit as evidence for the latency of a new demo photo.

## Completion gate

The baseline run is `2026-09-26T213857Z-lab-barcode-rerank-siglip2-512-crop-my`.
The job log is `work/run-jobs/barcode-rerank-siglip2-512-crop/job.log`.
The baseline process was PID 11418.
Do not stop or restart that process.
Do not start benchmark measurements while that run is active.
Require the final event `done`, a matching run ID, and complete run artifacts.
If the run fails or stops, report the failure and preserve the partial evidence.
Do not treat a failed run as a complete baseline.
The benchmark harness must enforce this gate.

## Results and isolation

Store results under `docs/reports/2026-09-27_barcode-variants/`.
Use separate output directories for each stage.
Use task-specific barcode cache directories under the output directory.
Do not clear the production cache.
Do not change production profiles while measuring variants.
Preserve the catalogue, test-set labels, and production result files.
Record configuration values, library versions, the source run, selection, and host load.
Do not run measurement variants at the same time.
Start long measurements in a detached process with a log and PID.
Keep checkpoints so a later task wakeup can continue the work.
Do not launch a second copy of an active measurement.

## Stage 1: barcode scan variants

Use the completed baseline photo set.
First validate the harness on a small subset.
Then measure the full set for the variants that can affect recognition recall.
Use `scripts/benchmark_barcode_variants.py` with the lab Python environment.

Compare:

- The current scan: two whole-photo calls, then 3 by 3 and 5 by 5 tiles.
- One whole-photo call with LocalAverage.
- Two whole-photo calls.
- Two whole-photo calls and 3 by 3 tiles.
- The full scan with four decode workers for one photo.
- Barcode cache writes and reads with one image worker.
- Barcode cache writes and reads with four image workers.

The per-photo parallel variant must retain pass order for matching and cache records.
Use at most four concurrent decoder calls.
Do not nest four decode workers inside each of four image workers.

Record per-photo wall time, decoder calls, decoded codes, and selected wine matches.
Compare unique matches, shared-code behavior, missed matches, and incorrect matches.
Use the saved ground truth and baseline predictions.
Report the number of photos in each denominator.
Report elapsed time, photos per second, median, p95, p99, maximum, and the fraction
that exceeds 3 seconds.
Barcode time alone does not prove that recognition meets the demo deadline.

## Stage 2: crop variants

Compare original-pixel rectangles for the bottle, label, and detected barcode.
Include a margin around a detected barcode.
Use cached segmentation for the initial offline comparison.
Record a missing region or missing cached segmentation as unavailable.
Do not invent a crop or exclude unavailable cases from the report without a count.
Measure the crop preparation cost separately.
Compare standalone crop scans and whole-photo-first crop fallbacks.
A label crop can exclude a barcode or QR sticker.
The crop comparison must measure recall as well as time.
For a new photo, include fresh segmentation cost in the later end-to-end measurement.

## Stage 3: bulk rerun

Use one worker and four workers for the selected barcode strategy with model caches on.
Measure the complete existing recognition pipeline on the same photo set.
Report cold barcode cache and warm barcode cache separately.
Compare top-1 and top-5 recall and errors with the completed baseline.
Do not present a change caused by a catalogue or rule edit as a decoder improvement.
If configuration drift prevents a direct comparison, record the drift and compare
paired variants against the same frozen experiment configuration.
Do not replace the owner's run or discard its output.

## Stage 4: sequential demo recognition

Send one image at a time.
Use a deterministic representative sample with all known barcode-hit cases and a
spread of difficult cases, image sizes, and rerank triggers.
Report the selection and the sample size.
Disable reads of per-image barcode, SAM3, and VLM response caches for the new-photo
measurement. Keep the catalogue index and loaded models warm, as a demo service would.
Report first-request startup time separately.
Record CPU preprocessing, barcode, segmentation, embedding, rerank, and total latency.
Include process startup and backend construction for the current `/recognize` path.
That path currently starts a new process for each image.
Compare a persistent backend separately if startup is material.

Measure the current scan and the best stage-1 and stage-2 candidates.
Report median, p95, p99, maximum, success by 3 seconds, errors, and recognition quality.
Treat results after 3 seconds as missed demo deadlines.
An uncancelled background request is not proof of a hard timeout implementation.
Select a barcode time budget from the measured time needed by the remaining stages.
If optional reranking cannot fit, measure a deadline fallback to the embedding answer.
Report the accuracy tradeoff. Do not silently remove reranking from production.

## Service constraints

Use existing endpoints and models.
Read `/Users/ashmelev/Admin/GPU_SERVERS.md` and `/Users/ashmelev/Admin/GPU_TASKS.md`
before an inference benchmark.
Check current GX10 memory and active processes before sending new inference work.
Register GPU benchmark activity in the tracker when required.
The enrichment classification run can share GX10 and affect latency.
Do not stop an unrelated job or restart a GPU service.
Record contention and report whether the 3-second target holds under that contention.
Use `SAM3_ENDPOINT` for the shared SAM3 client.

## Follow-up behavior

A task heartbeat continues these stages after the baseline finishes.
Stay quiet while the baseline or a measurement advances normally.
Notify on completion, failure, or a condition that requires user action.
On completion, recommend separate settings for bulk reruns and sequential demo images.
After both objectives have benchmark results, execute the owner's additional complete
profile rerun from `2026-09-27_all-profile-rerun.md` and its queue.
Keep the heartbeat active until the authorized queue work and reports are complete.
The external recognizer has a separate pending approval in that queue.

## Baseline completion and continuation

The baseline completed at 2026-09-27T01:20:44+0300.
It answered 2228 photos with zero errors.
The elapsed time was 2507.100 seconds.
Recall at 1 was 0.8467. Recall at 5 was 0.9702.
`2026-09-27_barcode-variants/baseline.json` records artifact hashes and row counts.
The task heartbeat is `benchmark-barcode-speed-after-current-run`.
It runs every five minutes while active.
It continues the benchmark work and reports only completion, failures, or required action.

## Baseline latency caveat

The completed run used model response caches.
Its recorded query median was 869 ms.
Its recorded query p95 was 2370 ms.
It recorded 2178 of 2228 queries within 3000 ms.
These values exclude a fresh process start for every photo.
They do not prove the new-photo demo requirement.
The current Recognize route uses a subprocess for every image and a 300-second timeout.
The demo requirement is 3 seconds.
Keep the required deadline separate from the observed latency distribution.

## Demo measurement review

- Set `model_cache.READ = False` and an isolated `model_cache.ROOT` inside each
  recognition child process. The parent setting does not affect a new interpreter.
- Use client request-to-response wall time for the deadline verdict. `latency_ms`
  excludes build and import work. `process_ms` excludes upload handling and step-view
  construction. Measure these components separately too.
- A persistent `Sam3Once` keeps its first failure. Do not count later immediate
  failures as fast recognition. Record the failure and outstanding work.
- The current HTTP timeout is 300 seconds. A latency measurement below 3 seconds does
  not establish an enforced 3-second timeout.
- Cancelling a future does not stop a native decode that is already running. Report
  the response time and worker completion time separately in deadline experiments.
- Report correct responses within 3 seconds, late correct responses, and fast errors
  separately. Treat the pilot p99 as preliminary.

Start with a deterministic pilot of all baseline barcode-hit photos and a spread of
misses that covers rerank triggers, large images, and difficult crops.
Compare the existing process-per-image path with a persistent backend as separate
experiments. Keep new-photo cache bypass in both experiments.

## Stage 1 launch

The harness passed 11 tests with fake decoders.
A two-photo control passed all nine variants with real ZXing calls.
The control had no decoder errors and no changed matches.
Each warm-cache variant made zero native decoder calls.
The control output is `/private/tmp/barcode-variants-smoke-20260927/`.

The full 2228-photo measurement started at 2026-09-27T01:29:19+0300.
Its PID is 78862.
Read `2026-09-27_barcode-variants/stage1-process.json` for the exact command,
source hashes, host details, and launch time.
Read `2026-09-27_barcode-variants/stage1.log` for progress.
Results, isolated caches, and checkpoints are in
`2026-09-27_barcode-variants/stage1/`.
The command uses `baseline-job.log`, a preserved copy of the completed baseline log.
A later production run can replace its live log without changing this copy.

The 2228 query rows contain 1851 unique image digests.
The other 377 rows repeat a digest.
Keep both denominators in the report.
The stage-1 cold-cache variants disable cache reads for every row.
They force a fresh scan even for a repeated digest.
The warm-cache variants read the completed cold-cache records.
For the full bulk pipeline, report natural cache reuse for repeated digests separately.

Before a continuation, check the saved PID and command.
Do not start another measurement while this process runs.
After an interruption, use the same command with `--resume`.
The manifest rejects changed inputs, lookup values, and decoder settings.
An interrupted timing segment makes total throughput unavailable.
Do not infer missing elapsed time from completed photo rows.

The host was busy at launch.
Its 1-minute, 5-minute, and 15-minute load averages were 46.82, 37.10, and 50.53.
The host has 12 logical CPUs.
Other applications and Python processes were active.
Treat absolute latency as a measurement under this contention.
Recheck leading variants under similar load before drawing a final timing conclusion.
Do not stop unrelated processes.

## Crop preparation from saved metadata

This inspection sent no model requests and decoded no images.

| Source | Query rows | Unique image digests |
|---|---:|---:|
| Baseline | 2228 | 1851 |
| Recorded package rectangle | 2204 | 1827 |
| SAM3 package rectangle | 2134 | 1760 |
| Alpha rectangle | 60 | 58 |
| White-background fallback rectangle | 10 | 9 |
| No recorded package rectangle | 24 | 24 |
| Successful rerank with a label crop | 585 | 436 |

The 24 rows without a package rectangle received a barcode answer.
Those rows did not run embedding preparation.
All 2144 non-alpha package steps record `cached: true`.
Repeated images have consistent package rectangles.
The baseline has no `sam3-label` trace.
Rerank records `picture: "label"` without label coordinates.
Cache replay is required to recover those coordinates.
The database has no package derivatives for these baseline images.
Its single matching label derivative uses a different close-up rule.
Do not use that derivative as the pipeline label crop.

The global SAM3 cache contains 4626 valid records.
Of 2042 package-prompt records, 1985 contain a `wine bottle` instance.
Of 2584 detection-prompt records, 2577 contain a `label`, 2562 contain a `bottle`,
and 191 contain a `barcode`.
These are global counts. They are not baseline coverage counts.
Request settings match the current endpoint, threshold 0.35, mask threshold 0.5,
and `return_masks: true`.
The baseline package and label settings match the current settings.
Cache records do not identify the served model revision.

Use this extraction sequence after stage 1 finishes:

1. Open the original with `derive.open_image()`. Coordinates refer to the image after
   EXIF orientation.
2. For the package variant, use the saved `sam3-package.out.box`. Read original pixels
   inside that rectangle. Do not use masked derivative pixels.
3. Construct `embedding_run.CachedSam3` for cache replay. Its `_send()` raises on a
   cache miss. It cannot make an inference request.
4. Read `instances(image, alternatives.DETECT_TEXTS)`. Select actual `barcode`,
   `bottle`, or label instances. `package_instance()` can select a can, packet, or box.
   Keep the names `package` and `bottle` distinct in the results.
5. For the existing label selection, use `alternatives.label_cut_of()` to obtain its
   box. Crop original pixels inside the returned box.
6. For raw instance boxes, multiply horizontal coordinates by
   `original_width / answer["width"]`. Multiply vertical coordinates by
   `original_height / answer["height"]`. Floor left and top. Ceil right and bottom.
   Clamp all coordinates to the original image bounds.
7. Add a fixed, recorded margin to barcode rectangles before clamping. Keep all
   qualifying barcode rectangles in a deterministic order.
8. Record missing cache, missing detection, and invalid boxes separately.

The scalar resize factor from `instances()` is nominal.
Separate horizontal and vertical ratios account for rounded sent-image dimensions.
Existing `label_box_cut()` uses the mask-width ratio for both axes.
Use that implementation when reproducing the existing crop exactly.
Cache keys use prepared PNG bytes, not original photo bytes.
Exact baseline label and barcode coverage needs image preparation and cache replay.
Run that CPU work after stage 1 to avoid interference with timing.


## Prepared experiment harnesses

The crop, bulk, and CLI demo harnesses are separate from production code.
The stage-1 gate checks all nine variants and the exact baseline hashes.
The shared `measurement.lock` prevents overlap between later measurements.
No later measurement starts while the saved stage-1 PID is active or unknown.

- `scripts/benchmark_barcode_crops.py` scans original-pixel package, bottle, label,
  and barcode rectangles. Each rectangle strategy also has a whole-photo-first form.
  It reads saved SAM3 answers only. It stores geometry checkpoints per unique digest.
  Missing regions stay visible. Its row-weighted latency is a projection.
- `scripts/benchmark_bulk_cache.py` runs the full pipeline for cold and warm barcode
  caches with one and four workers. It preserves normal model-cache behavior.
  It writes complete runs under `runs/`. It requires unchanged query labels,
  semantic catalogue inputs, vectors, and cluster rules between paired variants.
  A new cold run permits natural cache hits for repeated image digests.
- `scripts/benchmark_recognition_latency.py` measures sequential CLI recognition.
  It compares one child per image with one persistent child. Every child disables
  response-cache reads and writes only to the experiment cache. This pilot includes
  imports, backend construction, and normal child cleanup. It excludes HTTP, upload
  storage, step reconstruction, browser rendering, and client-network latency.
  Its watchdog is not a 3-second deadline implementation.

The combined mock suite passed 48 tests before the independent crop review.
The crop review added three tests, for 17 crop tests in total.
Lookup drift, edited frozen checkpoints, and malformed cached instances are guarded.
Unrelated SAM3 cache updates do not invalidate saved crop geometry.
No crop preparation, bulk run, or demo inference has started.

## Full HTTP demo experiment

Implement `scripts/benchmark_recognition_http.py` as an isolated experiment.
Use the existing lab request handler and Recognize route on a loopback port.
Use an OS-assigned port. Do not restart port 8168.
Do not start the lab description watcher or change the production database.
Inspect `make_server` initialization before use. Avoid any initialization mutation.

The experiment MUST include request body handling, upload validation and storage,
backend work, child startup when applicable, step reconstruction, JSON serialization,
and the complete HTTP response transfer in its client wall time.
Use a new upload directory for each request. This preserves upload-write cost when
source bytes repeat. Send only one request at a time.

Use the CLI experiment worker through a process-local `run_script` replacement.
Do not edit the production route. Preserve the full route answer shape.
Each backend child MUST keep response-cache reads disabled.
The HTTP server MAY read this request's isolated response cache to reconstruct the
step view. Reconstruction MUST use `CachedSam3` and MUST NOT send model requests.
This cache replay reproduces presentation work. It does not cache recognition answers.

Compare process-per-image and persistent modes. Record the initial HTTP service setup
separately. The first persistent recognition request includes backend initialization.
Record the experimental child-import overhead explicitly. Do not describe that wrapper
as byte-identical to the production `recognize.py` entry point.
A loopback request excludes the user's browser rendering and a remote client network.
Keep those limits visible in the final demo report.
Stop after a watchdog, backend failure, or latched SAM3 failure. Reconcile possible
remote outstanding work before resuming. Do not claim an enforced 3-second timeout.
Use the same source selection, completion gate, lock, and input fingerprints as the CLI
pilot. Validate cache isolation and timing boundaries with fake backends first.


## Stage 1 completion and stage 2 launch

At 02:13, the stage-1 process had exited and all nine variant summaries passed the
completion gate. Every variant covers all 2228 rows and has zero errors.
`comparison.md` records the scan and cache results.
A control on the first 64 baseline rows confirms the timing direction:
`full` 13.600 s, `whole` 3.057 s, and `photo4` 6.230 s.
All three controls preserve all 64 match decisions, including two barcode hits.
This control checks timing consistency. It is not a new corpus recall estimate.

The crop harness passed a real two-photo control of all eight variants.
Both photos had saved package rectangles but no cached detection answer.
All variants completed with zero errors. Missing crop evidence stayed explicit.
Control files are in `2026-09-27_barcode-variants/stage2-smoke/`.

The complete crop pass started at 02:15:32 in detached PID 52604.
Its exact command, source hashes, and host load are in `stage2-process.json`.
Read `stage2.log` for progress and `stage2/` for checkpoints.
The process prepares 1851 unique images and projects the results onto 2228 query rows.
It sends no SAM3 request and changes no production cache.
Do not launch bulk or demo measurements until it exits and its artifacts are checked.

The HTTP experiment parent must use the system Python because `lab_server` imports
`jsonschema`. The lab venv lacks that package. The route-selected worker interpreter
is the lab venv, which has ZXing. No dependency installation is needed.
The HTTP and CLI samples deliberately include every known barcode hit.
Report barcode-hit and non-hit strata separately. Do not treat the 64-row pilot's
aggregate deadline fraction as a full-corpus estimate.


## Crop availability bias

Cached preparation found 1827 package rectangles, 433 bottle rectangles, 441 label
regions, and 86 barcode regions among 1851 unique images. There were 1410 images
without a cached detection response. All 24 known barcode-hit query rows lack a
saved package rectangle. Among those rows, the bottle region has 23 missing cache
records and one missing detection. The baseline code step bypassed segmentation.
Do not infer crop recall from those unavailable cases. Include every known code-hit
row in fresh segmentation comparisons for the sequential demo. Charge segmentation
to that request. Keep the cached availability counts visible in the report.


## HTTP harness review checkpoint

All five experiment modules pass 68 mock tests: scan variants, crops, bulk cache,
CLI recognition, and HTTP recognition. The HTTP adapter uses the production handler,
upload storage, and step reconstruction. Each request has separate upload and cache
directories. The child never reads a response cache. The server reads only the current
request's newly written cache for presentation reconstruction.
Failed HTTP transport observations remain in the denominator after resume.
Worker cleanup is serialized. A final cleanup after handler join closes any child
created during exceptional shutdown. No real HTTP listener or model request has run.

Before real HTTP measurements, run a small socket control with fake inference.
Read `/Users/ashmelev/Admin/mbp2023/PORTS_USED.md` before allocating a port and record
the transient loopback experiment there. The harness uses port 0 and saves the actual
address in each session's service metadata. Keep port 8168 unchanged.
The current HTTP variants cover the stage-1 scan strategies. Fresh crop variants still
need integration after the crop result review. They MUST charge fresh segmentation.
This review does not establish an enforced 3-second deadline or cancellation.


Read `2026-09-27_barcode-variants/continuation.json` for the current handoff checkpoint.
Use the HTTP harness as the authoritative deadline/error comparison.
The auxiliary CLI harness saves watchdog and launch exceptions in `*.failure.json`,
but it can retry that query on resume. Do not report a resumed CLI aggregate after such
an exception as a failure-inclusive denominator. Inspect the failure artifacts or use
a new trial. The HTTP harness keeps failed observations in its JSONL denominator.


## Stage 2 completion and fresh crop preparation

At 02:32, PID 52604 had exited. All eight crop summaries and all 2228 query identities
passed validation. Each output has 1851 unique-image records. Missing standalone
regions have no fabricated decode time. The completion record matches the frozen
preparation index hash. Source hashes still match the launch record. The measurement
lock is free. Read `comparison.md` for results and availability limits.

Six opt-in fresh crop variants are implemented in the CLI worker and HTTP adapter:
`fresh-bottle`, `fresh-label`, `fresh-barcode`, and `whole-fresh-` forms of each region.
They use `SAM3_ENDPOINT`, force fresh SAM3 responses, and scan original-pixel rectangles.
Each response records segmentation, preparation, geometry, decode cost, and region
availability. A segmentation failure stops further model work for that request.
Production profiles and the experiment defaults are unchanged.
All five experiment modules now pass 77 mock tests (11 scan, 17 crop, 9 bulk, 40 demo).

The first HTTP comparison should use `full`, `whole`, `photo4`, and
`whole-fresh-barcode` on the fixed pilot. Compare process and persistent modes.
Use all 24 known barcode-hit rows for the three standalone fresh crop diagnostics.
Keep that diagnostic sample separate from the 64-row end-to-end pilot.

The ephemeral HTTP port is registered in `/Users/ashmelev/Admin/mbp2023/PORTS_USED.md`.
The benchmark workload is registered in `/Users/ashmelev/Admin/GPU_TASKS.md`.
Read `gpu-preflight-before-bulk.json`: at 02:35, GX10 had 46.66 GiB available.
SAM3 and the configured reranker were ready. SigLIP2-512 was unloaded.
The additional model estimate is 7 GB, with the required 20 GB safety margin.
SAM3 had no queued or running request at the snapshot. Other workloads stay active.
Record the first cold embedding load if it occurs during the full bulk comparison.


## Complete bulk launch

The real HTTP socket control passed four requests at 02:37. It used fake inference,
production upload storage, and production step reconstruction. Every input artifact
reported `check: same`. Each request had a different upload and cache directory.
Both process and persistent worker lifecycles passed. Both temporary listeners closed.
Evidence is in `2026-09-27_barcode-variants/http-socket-control/20260926T233700.124736Z/`.

The first complete bulk comparison started at 02:37:42. It uses one query worker,
a cold isolated barcode cache, normal model caches, and all 2228 queries.
The child PID is 31731. The supervisor PID is 31729.
Read `bulk-cold-1-process.json`, `bulk-cold-1.log`, and `bulk/cold-1.intent.json`.
The supervisor records complete process wall time and the exit status.
The harness wall time starts after Python imports and includes backend construction.
Keep both measurements. Wait for this process before the next variant.
Continue with warm-1, cold-4, and warm-4 in the same `bulk/` directory.

The first image took 42.309 seconds. Its embedding request took 42.054 seconds.
SigLIP2-512 was unloaded at preflight. The next embedding request took 160.3 ms.
The first request includes model startup, network work, and inference. Do not label
all 42.054 seconds as model load time alone. Keep that request in full process totals
and report it separately from steady-state image latency.

The image embedding services use a shared group with `swap:false`. A model switch
does not unload the previous model. Model memory can accumulate across the 53-profile
queue. Read the queue preflight report and check live available memory before each
unloaded model. Wait for existing TTLs or other workload completion when memory is
insufficient. Do not change the service configuration or stop unrelated models.


## Frozen demo selections

The selections were prepared from baseline metadata while bulk cold-1 was running.
No image was opened. No decoder or model was called.
`demo-selection-64.json` records 64 query rows and 61 unique image digests.
The labels contain 54 positive rows and 10 negative rows.
The selection reasons contain 24 known barcode hits and ten rows each for rerank,
large-image, slow-barcode, and deterministic-spread selection. Eighteen rows triggered
rerank in the baseline. Repeated source bytes still need separate fresh-cache requests.

The 64-row selection fingerprint is
`3b1fd11b30778da43042b04158b1cf820f92e53c7ffe5f360c241ce38dac9763`.
`demo-selection-24.json` holds exactly 24 distinct known barcode-hit images.
All 24 rows have positive labels. Its selection fingerprint is
`0686b5bd8b64fa2be1baf2fb6932e96b80ac554b8f9d14ea99f9591f3f6d53a5`.
Compare these fingerprints with the HTTP manifest before interpreting results.

Use 54 as the positive-correctness denominator of the 64-row pilot.
Use 64 as its complete HTTP-response deadline denominator.
Report the 24 hit rows and the other 40 selected rows separately.
This deliberate sample cannot estimate the corpus deadline rate.
A three-second observation is not a hard timeout implementation.


The pilot also contains one annotation conflict. Rows `q-000483` and `q-000484`
have identical source bytes but disjoint positive truth sets for two Aratti Riesling
wines. Preserve both rows and the raw 54-positive denominator. Also report sensitivity
results after excluding these two rows, with 52 positive rows. Do not change labels.
Rows `q-000152` and `q-000160` are a different case. The negative row excludes the brut
wine, and the positive row identifies the semisweet wine. Those constraints agree.
Rows `q-002221` and `q-002223` repeat the same negative constraint.
Keep all three duplicate groups in sequential timing with fresh response caches.

Read `demo-launches.json` for prepared commands. Neither command has started.
The 64-row pilot compares both process modes. The 24-hit crop diagnostic uses one
persistent worker per variant. Its first request still charges backend initialization.
The diagnostic measures each fresh segmentation cost without repeating child startup.


If the required HTTP pilot shows that fresh segmentation or rerank prevents the
3-second target, compare the existing `barcode-siglip2-512-as-is` profile on the same
64 rows. Use persistent mode with `whole` and `photo4`. This profile has no configured
query segmentation or rerank. The comparison measures the quality cost of that choice.
It does not change the production profile. A conditional command is saved in
`demo-launches.json`. Do not infer a latency gain or an acceptable quality cost before
that experiment. Keep any resulting pilot claim separate from a corpus estimate.


## First bulk completion and warm-1 launch

Cold-1 completed all 2228 rows at 02:51:57. The supervisor recorded exit 0 and
855.785 s process wall. Its child and supervisor PIDs are absent from the process list.
The harness reports zero errors, zero degraded rows, and no input drift.
All candidate orders, truth ranks, and outcomes equal the baseline.
There were 1851 fresh barcode scans and 377 natural duplicate-cache hits.
Read `bulk-cold-1-validation.json` for artifact hashes and
`bulk-comparison-after-cold-1.md` for the offline comparison.

Warm-1 started at 02:53:19 in child PID 88095 and supervisor PID 88093.
Read `bulk-warm-1-process.json`, `bulk-warm-1.log`, and `bulk/warm-1.intent.json`.
The same source hashes and paired manifest apply. All required model services were
ready at the 02:50:57 preflight, with 38.05 GiB available.
Do not launch cold-4 until warm-1 finishes and its artifacts and PIDs are validated.

`scripts/summarize_barcode_bulk.py` reads saved artifacts without model or image work.
Eight fixture tests pass. It keeps incomplete variants explicit and writes only to
new, explicitly supplied output paths. Process-state verification remains the parent
task's responsibility. The reporter checks persisted queries, answers, predictions,
metrics, summary, intent, and supervisor termination before declaring completion.


## One-worker pair complete; cold-4 running

Warm-1 completed at 03:01:01 with exit 0. Its child and supervisor PIDs exited.
All 2228 predictions, candidate orders, ranks, and outcomes match both the baseline
and cold-1. All 2228 barcode requests read cache records. Native decoder calls are zero.
The process wall is 462.249 s; the harness wall is 460.973 s.
Read `bulk-warm-1-validation.json` and `bulk-comparison-after-warm-1.md`.

The warm barcode trace sum is only 3.950 s. Package preparation takes 169.457 s,
cluster reranking with label preparation takes 109.052 s, and embedding requests take
100.698 s. The 2144 SAM3 package calls use cache records; 60 other package steps use
alpha handling. Cached model responses still need image and mask preparation.
Read `bulk-one-worker-step-costs.json`. Do not sum original VLM response durations.

Cold-4 started at 03:02:33 in child PID 19976 and supervisor PID 19974.
Read `bulk-cold-4-process.json`, `bulk-cold-4.log`, and `bulk/cold-4.intent.json`.
The 03:00:03 preflight found 38.14 GiB available and all required services ready.
No additional resident model is required. Warm-4 is the remaining bulk comparison.


## Bulk completion and HTTP launch

All four bulk variants completed. See `2026-09-27_barcode-variants/comparison.md`.
The warm four-worker run took 129.634 s process wall time for 2228 query rows.
All 2228 barcode lookups used the scan cache. The run made zero native decode calls.
All variants have zero errors, degradation, and input drift.

The HTTP pilot started at 03:15:13 MSK in child PID 62006 and supervisor PID 62005.
Read `http-pilot-process.json`, `http-pilot.log`, and `http-pilot/manifest.json`.
The selection fingerprint matches `demo-selection-64.json`.
The first three complete responses succeeded.
The fourth request is the first selected baseline rerank trigger.
The preflight found Qwen NVFP4 unloaded and 69.7 GiB of available memory.
The budget covers a 30 GiB model load, 7 GiB transient allowance, and 20 GiB margin.
Keep the cold model request in the report, even when it occurs after the first request.
Do not label every later request as warm only because it follows the first request.
After this pilot, run the 24-hit fresh-crop diagnostic.
Run the existing as-is profile comparison if fresh segmentation or reranking prevents
completion within 3 seconds. Keep the quality tradeoff visible.
All internal profile reruns still wait for the benchmark comparisons.


## Cold VLM failure and retained resume

The first HTTP attempt stopped at 03:20:22 MSK with exit code 2.
The first three responses took 1531.448 ms, 1275.510 ms, and 2630.753 ms.
The fourth query, `q-000078`, triggered the first fresh rerank.
Qwen NVFP4 was unloaded before the pilot and was still starting at 03:18:47.
The child watchdog expired. The route returned HTTP 503 after 300700.691 ms.
This is a failed recognition response, not a successful response after 3 seconds.
The full HTTP error response arrived. Its transport time is not censored.
The raw backend-stage timings are unavailable for that failed child.
Do not assign its full elapsed time to ZXing.
The recorded model startup supports cold VLM initialization as the cause of the wait.
It does not provide an exact isolated model-load duration.

Both local processes exited. The temporary HTTP server closed.
At 03:21:13, the gateway reported Qwen ready.
Direct vLLM metrics showed zero running requests and zero waiting requests.
A fresh preflight found 45.83 GiB available and all required models ready.
SAM3 and vLLM queues were empty.
The pilot resumed at 03:22:09 in child PID 84866 and supervisor PID 84865.
Read `http-pilot-resume-1-process.json` and `http-pilot-resume-1.log`.
The command uses `--resume` and the unchanged manifest.
It skips all four saved rows, including the failed row.
Keep that failure in every raw pilot denominator.
New rows have new upload and cache directories.
New requests are succeeding.
Do not present the after-first subset as warm only because it follows the first row.

Model preparation is required before a 3-second demo.
The comparison still needs all four decoder variants and both backend lifetimes.
The benchmark does not implement a hard 3-second timeout.
No service was stopped or restarted.


## Isolated embedding fallback control

The as-is diagnostic removes both package cropping and optional reranking.
It cannot isolate the effect of reranking alone.
The existing `barcode-siglip2-512-crop` profile matches the reference package crop,
embedding index, full-image tower, and barcode options. It omits optional reranking.
The sequential harness does not use the differing configured bulk-worker default.

After the prepared crop and as-is diagnostics, measure one additional cell:
`barcode-siglip2-512-crop`, persistent mode, `photo4`, the same frozen 64-row selection.
This is the measured embedding fallback required by stage 4.
Use the prepared command in `demo-launches.json` under `isolated_rerank_control`.
Keep response-cache reads disabled and send one request at a time.
The harness measures complete HTTP latency. It still does not enforce a hard timeout.
No production profile changes.
Saved search traces can reconstruct pre-rerank quality without more requests.
Subtracting a rerank step time cannot establish measured fallback HTTP latency.
Complete this control before the 53-profile queue starts.


## HTTP pilot completion and crop diagnostic

The eight-cell pilot completed at 03:40:07 MSK.
All 512 request records are preserved, including one cold-model HTTP 503.
The source manifest and frozen selection passed validation. Both local PIDs exited.
Read `http-pilot-validation.json` and `http-pilot-report-final/http-comparison.md`.
The fresh-crop diagnostic started at 03:42:03 in child PID 55767 and supervisor 55766.
Read `http-crop-hits-process.json` and its log before any next launch.
Next run the prepared as-is diagnostic and the isolated no-rerank control.
Keep all queue preparation and profile execution after those comparisons.


## Final comparison gate

All measurement processes exited by 03:54 MSK.
Read `2026-09-27_barcode-variants/comparisons-complete.json`.
The final HTTP report uses `http-pilot-report-final-v2`.
It excludes unavailable child component timings for the retained HTTP 503.
It preserves all selected rows in quality and deadline denominators.
The same-crop no-rerank control has 58 of 64 responses within 3 seconds.
It has 44 of 54 correct positive answers overall and 40 within 3 seconds.
The as-is photo4 control has 64 of 64 responses within 3 seconds.
It has 43 of 54 correct positive answers.
No comparison implements a hard 3-second timeout.

The first authorized profile rerun started at 03:57:01 MSK.
The selected profile is `siglip2-512-as-is`.
Its runner PID is 7235.
The queue and attempt archive record its run ID and launch intent.
Read the queue before the next launch.
