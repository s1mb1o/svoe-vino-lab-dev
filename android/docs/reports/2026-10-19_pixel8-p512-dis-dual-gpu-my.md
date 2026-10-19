# Pixel 8 isolated DIS and complete p512 dual-GPU test

Date: 2026-10-19

## Status

The thirty-image pilot and full `my` stability checks passed.
All 3,409 assignments completed in one process without a native abort or CPU fallback.
DIS failed to find an object on five positive assignments.
Those failures remain in every positive quality denominator.
The main application code and APKs remain unchanged.
Read [the machine-readable measurements](2026-10-19_pixel8-p512-dis-dual-gpu-my.json).

## Full comparison

Both runs use the same 2,970 positive assignments and accepted alternative slugs.
The frozen query files are byte-identical.

| Measurement | p512 GPU, no segmentation | DIS GPU + p512 GPU |
| --- | ---: | ---: |
| Top-1 | 2,052 / 2,970 (69.09%) | 2,147 / 2,970 (72.29%) |
| Top-5 | 2,587 / 2,970 (87.10%) | 2,619 / 2,970 (88.18%) |
| Top-10 | 2,674 / 2,970 (90.03%) | 2,683 / 2,970 (90.34%) |
| Top-20 | 2,714 / 2,970 (91.38%) | 2,722 / 2,970 (91.65%) |
| MRR | 0.7707 | 0.7923 |
| Client median latency | 924 ms | 1,319 ms |
| Client P95 latency | 1,479 ms | 2,343 ms |
| Client maximum latency | 5,837 ms | 6,140 ms |
| Calls within 3 seconds | 3,406 / 3,409 | 3,344 / 3,409 |
| HTTP errors | 0 | 5 DIS no-object errors |
| Peak sampled full-run PSS | 955.2 MiB | 1,434.2 MiB |
| Maximum thermal status | SEVERE (3) | MODERATE (2) |
| Bulk wall time | 3,300.0 s | 5,822.4 s |

DIS adds 95 Top-1 hits, or 3.20 percentage points.
The paired Top-1 comparison has 262 gains and 167 losses.
Top-5 improves by 1.08 percentage points. Top-10 improves by 0.30 percentage points.
Median HTTP latency increases by 42.75 percent.
P95 HTTP latency increases by 58.42 percent.
These values describe HTTP pipeline latency, not encoder inference alone.
The measured quality gain therefore has a latency and memory cost.
The recorded 90-percent Top-1 target is still not met.

The pack covers an accepted wine for 2,800 positive assignments.
The other 170 positive assignments remain unreachable with this catalogue.
On the covered subset, DIS Top-1 is 76.68 percent, Top-5 is 93.54 percent, and Top-10
is 95.82 percent.
For the 2,808 distinct positive image hashes, DIS Top-1 is 71.72 percent, Top-5 is
87.78 percent, and Top-10 is 89.96 percent.
The primary metric keeps every assignment and does not deduplicate the set.

The forbidden wine appears at Top-1 in 69 of 430 negative assignments.
The no-segmentation baseline count is 73 of 430.
Another returned slug is not proof of correct recognition on a negative assignment.
All 9 no-match queries still return a wine instead of rejection in both runs.

### Segmentation coverage

HTTP 200 responses: 3,404. HTTP 502 responses: 5.
All five errors are positive queries where DIS did not find the main object:
`q-001679`, `q-001712`, `q-001713`, `q-002870`, and `q-003136`.
The application did not restart for these errors.
The experiment did not replace a failed DIS query with no-segmentation output.
All 271 repeated-image groups kept the same Top-1 result across their assignments.
Variant-group near-duplicate statistics were not evaluated with this frozen-query
override. Do not compare the zero placeholder in `metrics.json` with baseline
near-duplicate confusion counts.

## Isolation and pipeline

The experimental application ID is `chtozavino.alolalab.com.dualgpu`.
Its version is `0.2.0-dualgpu`. Its launcher label is `Что за вино · GPU-тест`.
It is installed beside the main application, not over the main application.
The source is a separate snapshot of commit `e14c541e`.
The experiment bypasses the inherited DIS GPU to SigLIP2 CPU override only in that
snapshot.
It keeps model reuse and the dedicated inference worker.
Explicit debug requests cannot fall back to CPU.
Every successful response reports both actual model accelerators.

The device is Pixel 8 `41231FDJH002WZ`, Android 17, SDK 37.
The model pack remains `20261019-base-naflex-p512-complete`, format 6.
The pack has 2,093 wines, 2,093 vectors, and one unrotated reference for each wine.
Its SHA-256 is `4307a92be20fc53bec18f922ae80b60d92fc219c2a8e22f981f8c8778117a128`.
The query pipeline is DIS GPU, native white-background crop, and complete Base p512 GPU.
The p512 graph uses FP32 execution, BUFFER storage, and no GPU program cache.
Reference aggregation is `max`. Barcode decoding and response caching are disabled.

The main source and main APK outputs were unchanged before installation.
The installed main APK SHA-256 was
`a11767bc3a3f2199cb836f155cce376601ae596f001647b3e37260781ba30b0e`.
The experiment temporarily stops the main process to prevent competing GPU sessions.
It does not export or copy private main-application settings or history.

## Thirty-image pilot

The selection is identical to the previous thirty-image pilot.
Every input SHA-256 and accepted-slug list matches the frozen full baseline.
The set contains 24 positive, 5 negative, and 1 no-match assignments.
All 30 requests returned HTTP 200 in process `19651`.
Both actual accelerators were GPU for every request.
All thirty embeddings contained 768 finite values and passed unit-norm checks.
No process restart, native abort, or CPU fallback occurred.

Median client latency was 972.9 ms.
The first request took 6,220 ms and included compilation of the model sessions.
Peak sampled process PSS was 1,602,565 KiB, or 1,565.0 MiB.
The maximum sampled Android thermal status was `NONE` (`0`).
The stability gate passed. This gate does not prove long-run stability.

Positive Top-1 was 16 of 24. Top-5 was 21 of 24. Top-10 was 21 of 24.
This stratified selection is not a full-set accuracy estimate.
Use the complete-run comparison for a pipeline decision.

## Full run protocol

Run ID:
`2026-10-19T102704Z-lab-android-device-match-k20-my-pixel8-p512-dis-dual-gpu-experimental-20261019`.

The run reuses all 3,409 frozen baseline assignments and accepted alternatives.
The frozen query file SHA-256 is
`9c2c4591e02f3e597dbbd75db2e8565d2dd90fc5cc282f7664eb9f6cf6eefd40`.
The runner resolves image locations from read-only catalogue records.
Some query images reside outside `data/testsets/images`.
An initial zero-request preflight assumed that directory alone.
The preserved preflight record documents this host path-resolution error.
The actual full run verified all 3,031 distinct source image hashes before device
requests.

The run uses one uncached worker and `/v1/match?k=20` through USB forwarding.
Both accelerator overrides are `gpu`.
Every successful response must confirm DIS GPU and p512 GPU.
The full run keeps the same warmed process as the pilot.
The earlier no-segmentation baseline included a new model session on its first request.
Do not treat maximum or first-request latency as a controlled cold-start comparison.

Client latency measures the HTTP call, including decoding, preprocessing, inference,
search, and USB transport.
Host multipart construction and per-request ADB process checks are outside that timer.
Whole-run wall time includes host checks and runner overhead.
The new full run takes 97.04 minutes including those checks.
Its summed HTTP call time is 4,963.619 seconds.
The remaining 858.781 seconds are outside the per-call timer.
The baseline summed HTTP call time is 3,286.822 seconds.
Its remaining host overhead is 13.178 seconds.
The new runner checks the application PID before and after each request.
These checks change device duty cycle and bulk wall time.
Bulk wall time is not a controlled inference-throughput comparison.
Do not interpret the lower measured thermal status as proof that DIS consumes less
power or is inherently cooler.
Sampled PSS does not include the complete GPU allocation peak.
The runner stops on a process change, invalid output, or CPU fallback.
At `CRITICAL` or higher, the monitor force-stops only the experimental application.
It does not change Android thermal protection.

The comparison baseline is
[the complete p512 no-segmentation run](2026-10-19_pixel8-base-p512-full-my.md).
The runs use the same catalogue and frozen query assignments.
The runs occur at different times and can have different thermal conditions.

## Runtime and numerical verification

All 3,404 successful full-run responses report DIS GPU and p512 GPU.
The application PID remained `19651` from the pilot through the full run.
No process restart, native abort, fatal application exception, or model-level CPU
fallback was observed.
The monitor saved 347 full-run telemetry samples.
Thermal status reached `LIGHT` after 160.2 seconds and `MODERATE` after 2,003.9 seconds.
These times are relative to the first full-run telemetry sample.
No `SEVERE` or `CRITICAL` status occurred.
Battery temperature started at 34.6 degrees Celsius and ended at 41.9 degrees Celsius.
The maximum sampled battery temperature was 43.0 degrees Celsius.

After the full run, three explicit p512 CPU requests were compared with p512 GPU
requests on the same images while DIS remained on GPU.
These CPU requests are numerical checks, not fallback or measured full-run requests.
All three comparisons passed cosine `0.99999` and maximum-error `0.001` thresholds.
The minimum observed cosine was `0.9999999999044907`.
The maximum component error was `0.000003159046173095703`.
A final GPU request then confirmed GPU + GPU again.
Closing both GPU models through the HTTP switch left the process alive with PID
`19651`.

The inherited guard is therefore not required to complete this measured Pixel 8
workload with this complete p512 graph and dedicated-worker runtime.
This result does not establish compatibility for another phone, another LiteRT
version, a legacy fixed model, or a split graph.
The experiment did not isolate which earlier lifecycle or runtime change prevents
the historical abort.
The main application retains its existing guard.

## Evidence and cleanup

Technical artifacts:
`/Volumes/Storage/svoe-vino-final/artifacts/android-p512-dis-dual-gpu-20261019/`.
The folder contains the source snapshot, exact experimental patch, APK hashes, pilot
responses, full raw responses, telemetry, app-only logs, and coordinator records.
Workbench writes full `predictions.jsonl`, scored results, and metrics in the run
directory above.

Read [the saved predictions](../../../workbench/runs/2026-10-19T102704Z-lab-android-device-match-k20-my-pixel8-p512-dis-dual-gpu-experimental-20261019/predictions.jsonl).
The artifact folder also contains `paired-changes.jsonl`, explicit CPU/GPU response
pairs, a final GPU probe, and `cleanup.json`.

The test disabled the experimental HTTP setting through the UI.
The health endpoint stopped accepting connections.
The test removed its ADB forwarding rule and temporary UI dump.
The original screen-awake value `15` was restored and checked.
The experimental application was force-stopped after its GPU resources closed.
The experimental APK remains installed separately with HTTP disabled.
The main application was reopened.
The installed main APK SHA-256 still matches the value above.
The main application source and tools have no changes from `HEAD`.
The main debug APK SHA-256 remains
`a11767bc3a3f2199cb836f155cce376601ae596f001647b3e37260781ba30b0e`.
The main release APK SHA-256 remains
`f6dbfe72e5d2bff1de98cee3ac8948c3b3f9553d1a477575be6425c1feb4ccb6`.
No private main settings or history were exported or replaced.
The task did not publish, push, or replace the main application.
