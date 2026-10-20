# Change log

## 2026-10-20

### Rebase onto current GitHub main

- Rebased seventeen Android topic commits onto main in an isolated Git worktree.
- Preserved upstream private-log deletions and all current Workbench changelog entries.
- Verified the full Android tree as unchanged from the pre-rebase backup.
- Passed 181 main, exporter, host benchmark, and Workbench remote-run tests.
- Passed release lint and rebuilt the same unsigned APK from the rebased source.
- Added the signed 0.2.0 website contract and historical-screenshot clarification.
- Passed 530 website tests with 26 skipped tests and passed website type checking.
- Preserved the original checkout, installed APK, and active Pixel benchmark.
- Recorded source and artifact checks in `docs/releases/2026-10-20-main.md`.

### Two complete production pipelines

- Replayed all 668 custom assignments with exact Top-1 agreement and zero errors.
- Replayed 30 standard assignments with exact Top-1 agreement and zero errors.
- Completed Eval.zip: 86/100 accepted results, 100 responses, and zero transport errors.
- Built and test-signed release 0.3.0. Recorded identities and validation in `docs/releases/0.3.0.md`.
- Made DIS-768 cropped custom the default and retained full-image standard p512.
- Added a Russian Settings selector and pipeline-specific accelerator rechecks.
- Added format 7 with both matched graph/index pairs and shared catalogue images.
- Preserved measured fractional patch coverage, crop rendering, and FP32 GPU policies.
- Omitted optional YOLO weights from the public pack by owner choice.
- Preserved history and accelerator preferences during automatic pack migration.
- Passed the first debug/release builds, Android unit tests, release lint, and ten pack-export tests.
- Started Pixel validation only after both DIS resolution runs completed and cleaned up.
- Release publication and final device validation remain pending.

### DIS input-resolution experiment

- Completed and independently audited all 668 DIS-768 assignments with zero errors.
- Measured Top-1/5/10 at 46.56/84.58/89.67%, request median/P95 at 1637/2052 ms.
- Recorded 37.22% lower median and 40.15% lower P95 than DIS 1024, with three fewer Top-1 hits.
- Recorded stable Pixel PID 7960, successful cleanup, and no transport error or fallback.
- Preserved the DIS-1024 USB-continuation caveat and differing thermal conditions.
- Left DIS 512 running through its cooling gate. Kept production and all raw evidence unchanged.

- Passed all 115 DIS-768 device numerical checks and its 30-image pilot with zero errors.
- Measured pilot median/P95 at 1358/1468 ms. Started the full 668-assignment DIS-768 run.
- Kept DIS 512 queued behind the first full run. Complete-cohort results remain pending.

- Added fixed-shape 768 and 512 DIS exports with unchanged learned weights and operator options.
- Verified exact 1024 CPU identity, fixed padding, finite masks, and every candidate tensor shape.
- Added a separate resolution-test application and metadata-checked input dimensions.
- Preserved p512 encoders, position data, reference vectors, crop rendering, and FP32 GPU policies.
- Passed 54 host tests, 33 Android tests, lint, signing, and alignment checks.
- Froze the new APK, packs, and 105 source files. Started the gated Pixel workflow at 20:21 MSK.
- Kept re-ranking off and all previous results intact. Device quality and speed remain pending.

### Isolated DIS p512 custom-pooling comparison

- Recorded a speedup assessment from the existing 668 traces. Added an additive timing budget.
- Identified CPU mask/image work as the first optimization candidate. No runtime or model changed.

- Completed cropped DIS on all 668 assignments with zero inference errors at 19:33 MSK.
- Measured Top-1/5/10 at 47.01/84.58/89.82%, median/P95 at 2607/3429 ms.
- Verified a 5.99-point Top-1 gain over default and a 3.29-point gain over full-image DIS.
- Recomputed all five quality/latency results. Verified identical assignments and custom reference bytes.
- Confirmed exact prefix preservation and successful final cleanup. Recorded the USB-interruption caveat.
- Kept the production default unchanged. Saved the final five-pipeline comparison in the measurement record.

- Added strict host-only continuation after the cropped run lost USB at assignment 190.
- Preserved raw v3 data and exact JSONL prefixes. Required the same Pixel process, APK, and pack.
- Passed all 46 host tests and the real-prefix dry audit. Resumed at assignment 191 in a new v4 directory.
- Kept re-ranking disabled. Reported interrupted stability separately from quality and latency.

- Completed and audited full-image DIS on all 668 assignments with zero errors at 18:27 MSK.
- Measured Top-1/5/10 at 43.71/83.23/88.92%, median/P95 at 2283/5351 ms.
- Confirmed the fresh standard control reproduces all production Top-1 predictions.
- Recorded improved quality and a failed full-run latency target. Kept both findings separate.
- Left cropped DIS queued behind the unchanged cooling gate. The full comparison remains pending.

- Validated FP32 DIS with automatic storage in v3. Kept the original strict mask threshold.
- Passed all 440 numerical checks and three independent 30-image pilots without errors.
- Measured pilot median/P95 at 2025/3351 ms for full-image custom and 1949/2204 ms for cropped custom.
- Started the full 668-query standard control. Both full DIS runs follow exact control agreement.
- Passed all 36 host tests, 31 Android tests, lint, signing, and alignment for test version 0.1.6.

- Preserved v2 after production-default DIS GPU options failed the strict mask-agreement gate.
- Recorded maximum raw/normalized mask errors 0.007584095/0.032568038 and successful cleanup.
- Added FP32 DIS with automatic GPU storage for a separate v3 test. Kept every threshold unchanged.

- Preserved the first DIS pilot after 21 successful requests with median latency 4179 ms.
- Corrected test DIS GPU options to the production defaults. Kept encoder options unchanged.
- Added a regression test that prevents applying encoder-only GPU overrides to DIS.
- Stopped only the owned pilot runner. Verified HTTP-off and process-stop cleanup.
- Kept all numerical and smoothness gates unchanged for a separate v2 attempt.

- Added a separate DIS experiment package with a standard control and two custom query frames.
- Reused the pinned production DIS graph and unchanged p512 encoder/index bytes.
- Added GPU DIS inference, production min-max mask normalization, and raw mask captures.
- Added independent DIS mask projection checks for full-image and cropped/white queries.
- Added a strict standard-control dependency before full custom runs.
- Passed 36 host tests. Device validation and full quality measurements remain pending.
- Passed 30 Android tests, debug lint, API 28 signing verification, and 16-KiB alignment.
- Froze the APK, unchanged model/index files, source snapshot, and finite workflow.
- Started the isolated Pixel numerical gates at 17:04 MSK with default-off HTTP verified.
- Kept re-ranking disabled, previous artifacts preserved, and production unchanged.

### Full-image p512 custom-pooling experiment

- Completed both repaired 668-assignment runs at 16:11 MSK. Fresh audits match saved results.
- Reproduced production Top-1 on 668/668 control assignments after the decoder repair.
- Measured full-image custom Top-1/5/10 at 38.92/77.54/84.43%, median/P95 1554/3002 ms.
- Recorded a 1.95-point Top-1 gain over cropped custom and a 2.10-point loss to the default.
- Confirmed both retained no-bottle failures, a stable process, and successful HTTP-off cleanup.
- Kept the current default unchanged. Saved final results in the dedicated report.

- Matched the isolated full-image decoder to production source-colour and alpha handling.
- Added raw-RGB preprocessing captures and all four affected ICC/alpha parity inputs.
- Added exact installed-APK and private-pack checks before an isolated APK update.
- Preserved the stopped v1 attempt. Prepared version 0.1.3 for a separate v2 attempt.
- Passed all 29 host tests. Kept the exact full-control gate and re-ranking disabled.
- Passed all 25 Android tests, debug lint, signing, and alignment for the repaired build.
- Passed 310 numerical checks and both 30-image pilots on Pixel 8.
- Confirmed restored production rankings on all four affected ICC/alpha inputs.
- Resumed the full 668-query standard control into preserved attempt v2 at 15:35 MSK.

- Recorded the stopped first attempt after its 668-request control failed exact agreement.
- Preserved all records and four changed Top-1 cases. Confirmed successful final cleanup.
- Recorded decoder colour/alpha differences. The full custom run remains unstarted.

- Added isolated package `com.alolalab.chtozavino.fullpoolbench`, version 0.1.2.
- Preserved full-image RGB and geometry. Used the bottle mask only for patch weights.
- Kept previous custom references and production control references byte-identical.
- Added full-source pixel, released preprocessing, and production-control parity gates.
- Added a finite detached two-condition workflow with numerical checks and 30-image pilots.
- Passed 27 host tests, 23 Android tests, debug build, lint, signing, and alignment checks.
- Started the gated Pixel workflow. Full-run quality remains pending.
- Kept the production application and all previous measurement artifacts unchanged.

### Pixel Base pooling comparison completed

- Completed all four 668-assignment `my-failed-2` runs on Pixel 8 at 13:08 MSK.
- Passed 240 numerical checks, four smoothness pilots, and all four full-run audits.
- Saved all 2,672 predictions and the paired standard/custom comparison.
- Measured p512 custom Top-1/5/10 at 36.98/68.86/73.95% and median/P95 at 1769/2428 ms.
- Recorded thermal conditions that limit latency interpretation.
- Disabled the isolated HTTP server and stopped the test app after successful cleanup.
- Kept re-ranking disabled and the production pipeline unchanged.
- Recorded the full results in `docs/reports/2026-10-20_base-naflex-p224-custom-pooling.md`.

### Interrupted Pixel benchmark recovery

- Added recovery-copy finalization from saved telemetry without editing the raw run.
- Verified all 536 saved assignments and exact prediction bytes with the frozen audit.
- Passed a dry resume-prefix check and all 23 host tests.
- Resumed the unchanged full benchmark from assignment 537 into a new v4 directory.
- Added a finite detached workflow for the continuation and gated four-condition comparison.
- Kept the installed APK, model pack, GPU policy, recipes, and re-ranking unchanged.

### Isolated Base NaFlex p224 pooling experiment

- Extended the comparison to p224 standard/custom and p512 standard/custom.
- Added a separate p512 custom graph, matching index, and budget-specific validation.
- Preserved the three initial indexes and all v1 artifacts.
- Superseded only the waiting v1 host coordinator before any device use.
- Added paired standard/custom comparisons at both budgets and cross-budget comparisons.
- Passed 19 Python tests, 19 Android tests, debug lint, and the p512 graph-rewrite gate.
- Prepared all 8,372 vectors and queued the frozen four-condition v2 comparison.

- Added a separate `com.alolalab.chtozavino.basepoolbench` debug application.
- Added Base p224 standard and fractional bottle-coverage pooling with a matched p512 control.
- Preserved native aspect ratio, 768 dimensions, and one encoder pass per query.
- Added matching 2,093-wine reference preparation, checksums, and numerical gates.
- Added a finite Pixel comparison with 30-image pilots and gated 668-assignment runs.
- Kept the active full-v3 benchmark and production default unchanged.
- Passed 16 host tests and the same-weight graph rewrite checks.
- Passed 17 Android tests, debug lint, API 28 signing verification, and ZIP alignment.
- Queued the frozen-source comparison after successful full-v3 completion and cleanup.
- Initial device quality and latency were pending. Read the final dated pooling measurement record.

### Release signed with the previous APK key

- Verified that the local signing certificate matches the published 0.1.4 release.
- Signed the fresh 0.2.0 release with that existing test/debug key at the owner's request.
- Saved `chtozavino-0.2.0-release-test-signed.apk` without replacing the unsigned APK.
- Passed signature verification for API 28 and the final 16-KiB alignment check.
- Verified all 211 original ZIP payloads as unchanged after signing.
- Saved certificate identity, signing evidence, and signed-artifact checksums.
- Left production-key configuration, the device benchmark, and the website unchanged.

### New-ID release rebuild for website preparation

- Rebuilt the main release from committed source `492251af` with all 101 selected tasks.
- Passed 65 debug tests, 62 release tests, 16 Python tests, and release lint.
- Verified `com.alolalab.chtozavino`, API 28, arm64, ZIP alignment, and HTTP exclusion.
- Saved the unsigned APK, mapping, manifest, and checksums in a new archive directory.
- Preserved the previous releases, model pack, and active Pixel benchmark.
- Recorded the permanent-key and production-source decisions still needed for publication.
- Left the website and public downloads unchanged.
- Recorded exact scope in `docs/releases/2026-10-20-rebuild.md`.

## 2026-10-19

### Rebuild and GitHub source checkpoint

- Committed the main application ID, dual-GPU measurements, and offline benchmark by topic.
- Rebuilt main debug, unsigned release, and the isolated benchmark APK.
- Passed 183 fresh tests without a failure, error, or skipped test.
- Passed all three lint variants with no errors. Retained existing warnings.
- Assembled again after the implementation commits.
- Archived all three APKs, checksums, test evidence, and mapping in a new subdirectory.
- Preserved the old-ID release and the embedded format 6 pack.
- Verified package IDs, FileProvider authorities, signatures, and release HTTP exclusion.
- Left the active Pixel APK and process unchanged. Re-ranking remains disabled.
- Recorded the source checkpoint and GitHub branch in `docs/releases/2026-10-19-rebuild.md`.

### Isolated offline retrieval benchmark implementation

- Added owner-approved direct USB HTTP transport with strict framing and bounded retries.
- Added attempt logs and same-process, idle-worker, user, and service guards.
- Added audited continuation into a new directory with exact saved prediction prefixes.
- Preserved model errors and recorded separate process segments for continuation.
- Passed 20 host tests, including binary-prefix injection and UI cleanup timeout.
- Kept the installed v5 APK, model pack, all recipes, and disabled re-ranking unchanged.
- Passed the q-000045 Pixel smoke and its ten-recipe independent audit.
- Resumed full v3 from assignment 45. Verified the first 47 records independently.
- Confirmed exact source preservation and identical q-000045 smoke/cohort candidates.
- Recorded the full v2 transport interruption after 44 of 668 responses.
- Preserved all ten partial prediction files and the independently verified partial audit.
- Confirmed successful automatic HTTP, process, forwarding, and power cleanup.
- Left complete-cohort quality pending. The status request did not restart inference.
- Preserved 29 successful full-run responses before cached-process freezing and LOW_MEMORY.
- Added an owner-approved foreground service only to the isolated benchmark APK.
- Added an explicit HTTP notification, stop action, and CPU wake-lock cleanup.
- Kept HTTP off at fresh process start and disabled automatic service restart.
- Added service-state guards and background telemetry to the benchmark runner.
- Added a separate thirty-image background gate without changing inference recipes.
- Passed 20 Android tests, seven host tests, and the 102-check v5 numerical gate.
- Verified visible notification startup, both stop actions, default-off behavior,
  and worker-ordered cleanup after actual GPU/CPU inference on Pixel 8.
- Started the thirty-image background gate before the full v2 cohort.
- Completed all 30 background requests and independently verified 300 recipe predictions.
- Matched all Top-1, Top-20 orders, and candidate scores with the v4 independent pilot.
- Recorded importance 125 in all 68 background samples and maximum heat MODERATE.
- Started a fresh full v2 cohort with automatic audit, report, and isolated-app cleanup.
- Preserved the second pilot's zero-response foreground `LOW_MEMORY` failure.
- Added a separate constant-tensor-sharing candidate without changing FP32 or weights.
- Explicitly disabled GPU source quantization and added two runtime-policy tests.
- Passed 18 local tests, lint, and all 102 repeated numerical checks for this candidate.
- Started the third independent pilot without changing model or reference bytes.
- Completed the 300-request independent pilot in PID 13687 without errors or fallback.
- Independently verified all ten 30-record prediction files and every pilot metric.
- Measured 4.09-13.74 second medians and 2173.36 MiB peak sampled pilot PSS.
- Recorded `SEVERE` sustained heat. This is not a production heat acceptance.
- Started the full 668-assignment `my-failed-2` run after cooldown to `MODERATE`.
- Complete hard-set quality measurements remain pending.
- Added a separate `com.alolalab.chtozavino.offlinebench` application.
- Kept the main application source, installed data, and reference pack unchanged.
- Added mobile bottle/label segmentation, weighted SO400M p512, and bounded FP32 search.
- Preserved the ten frozen desktop recipe IDs, reference ownership, and fusion weights.
- Added independent variant requests and shared-work complete-cohort requests.
- Disabled barcode recognition and re-ranking in the isolated application.
- Added private model-pack transfer with per-file checksums and no broad file modes.
- Added raw tensor captures and desktop/device numerical verification.
- Passed 16 isolated unit tests and debug lint with no errors.
- Repaired legacy BOX endpoint and 22-bit coefficient rounding before quality tests.
- Passed exact-pooling and repaired all-recipe desktop/device numerical checks.
- Froze the validation-selected epoch-8 checkpoint after the ten-epoch training pilot.
- Preserved the zero-request failed external-pack preflight as evidence.
- Fixed the ten-epoch pilot stopping policy before adapted retrieval evaluation.
- Passed all 102 final-pack numerical checks after the owner restored Android user 0.
- Verified that the installed lifecycle candidate retains HTTP across Activity recreation.
- Started the independent thirty-image pilot for each of the ten adapted recipes.
- Preserved 57 successful pilot responses and a missing request after a background
  `LOW_MEMORY` process exit. The camera was foreground. No own native crash was recorded.
- Saved the process-exit audit and cleanup verification. The pilot is incomplete.
- Complete adapted hard-set quality measurements remain pending.
- Preserved the interrupted final-pack run and its Android profile/exit audit.
- Separated partial numerical diagnostics from a complete passed gate.
- Kept the benchmark server across Activity recreation and ordered HTTP model cleanup.
- Preserved failure metadata when USB cleanup cannot reach the device.
- Added an Android-user guard before device UI, pack transfer, and evaluation.
- Left Android user 10 unchanged and requested the owner's profile decision.

### Ten-variant Android evaluation preflight

- Located the frozen SO400M pooling, geometry, and fusion experiment definitions.
- Confirmed the 668-assignment `my-failed-2` cohort and connected Pixel 8.
- Recorded the model and segmentation difference from the Base p512 application.
- Added plan 06 with explicit re-ranking exclusion and a measurement-boundary gate.
- Requested a choice between exact retrieval reproduction and an offline adaptation.
- Started no image inference, model export, or application installation in preflight.

### Offline adaptation preparation and device control

- Recorded the owner's complete-offline selection in plan 06.
- Completed all 668 frozen `my-failed-2` control requests on Pixel 8 without errors.
- Measured Top-1 41.02%, Top-5 77.84%, and Top-10 84.58% with Base p512 on GPU.
- Saved predictions, vectors, raw responses, process checks, thermal samples, and logs.
- Disabled control HTTP and removed forwarding after measurement.
- Recorded 42 catalogue-uncovered assignments without changing the denominator.
- Matched all 660 overlapping assignment predictions with the earlier full control.
- Prepared 2,031 catalogue training images and 228 wine-group validation images.
- Verified zero training overlap with 3,039 frozen evaluation-image hashes.
- Started isolated local-MPS bottle/label segmentation training with bounded memory.
- Preserved failed training setup v1 and rejected graph v1 as evidence.
- Added pooling log weights without changing the 448 external model-weight buffers.
- Passed desktop zero-bias equivalence, native agreement, and padding-exclusion gates.
- Froze all ten exact desktop recipe identities, gallery counts, and fusion weights.
- The later isolated implementation and device gates are recorded above.

### Main application ID

- Changed the main debug and release application ID to `com.alolalab.chtozavino`.
- Kept the existing Kotlin namespace and Russian launcher name.
- Retained the application-derived FileProvider authority for camera capture.
- Updated the Pixel 8 pilot runner to inspect the new package.
- Added a shared unit test for the debug and release application ID.
- Documented the separate installation and the absence of automatic data migration.
- Preserved historical reports, archived APKs, and the isolated dual-GPU application.
- Left installed applications unchanged.
- Passed 65 debug tests and 62 release tests, including both application-ID checks.
- Passed debug and release lint with no errors and 31 and 32 warnings respectively.
- Built both APKs and verified the new package, launcher, and FileProvider authority.
- Verified the unchanged embedded pack and the frozen old-ID release checksum.
- Kept the new release unsigned and outside the frozen release archive.

### Isolated DIS GPU and p512 GPU experiment

- Built `chtozavino.alolalab.com.dualgpu` from a separate Android source snapshot.
- Kept the main application source, installed APK, debug APK, and release APK unchanged.
- Disabled the inherited dual-GPU override only in the experimental copy.
- Disabled explicit-request CPU fallback and reported actual accelerators in responses.
- Passed 64 isolated debug unit tests and debug lint before installation.
- Passed all thirty pilot requests with GPU + GPU and valid 768-dimensional vectors.
- Completed all 3,409 frozen `my` assignments in one process without a native abort,
  process restart, or model-level CPU fallback.
- Recorded five DIS no-object errors on positive assignments without replacing them.
- Improved Top-1 from 69.09% to 72.29%, Top-5 from 87.10% to 88.18%, and Top-10 from
  90.03% to 90.34% against the no-segmentation p512 baseline.
- Recorded 262 paired Top-1 gains and 167 losses.
- Measured 1,319 ms client median, 2,343 ms P95, and 1,434.2 MiB peak sampled full-run PSS.
- Recorded maximum thermal status `MODERATE` and maximum battery temperature 43.0 C.
- Passed three post-run GPU/CPU vector comparisons while DIS remained on GPU.
- Verified consistent Top-1 results across all 271 repeated-image groups.
- Saved predictions, exact source patch, raw responses, telemetry, logs, and comparison
  in `docs/reports/2026-10-19_pixel8-p512-dis-dual-gpu-my.md` and its linked artifacts.
- Disabled experimental HTTP, removed forwarding, restored power settings, and reopened
  the unchanged main application.
- Left the main dual-GPU guard unchanged.

### DIS and p512 GPU guard investigation

- Traced the inherited CPU override to commit `9fe721dc`.
- Distinguished the observed repeated-model-creation abort from the unproven
  simultaneous-GPU-model explanation.
- Recorded that the complete p512 plus DIS dual-GPU combination remains unverified.
- Left the application and the debug HTTP setting unchanged.

### Local 0.2.0 release archive

- Committed the complete Base NaFlex p512 implementation as `eaf8d688`.
- Rebuilt the unsigned release from that source with all Gradle tasks executed again.
- Passed 64 debug unit tests, 61 release unit tests, 16 Python tests, and release lint.
- Saved `chtozavino-0.2.0-release-unsigned.apk` in
  `/Volumes/Storage/svoe-vino-final/releases/android/`.
- Verified the application ID, version, API 28 minimum, arm64 ABI, and embedded pack.
- Verified that the release is not debuggable and has no debug HTTP implementation.
- Added a release sidecar with hashes, source revision, tests, and pack identity.
- Copied eleven distinct historical local APKs from twenty-two source paths.
- Restored both published GitHub 0.1.4 APKs and verified their published checksums.
- Saved signing identities, a complete archive manifest, checksums, and the R8 mapping.
- Preserved the original APK files and recorded each source path in the archive.
- Added Kotlin build-session cache files to the Android ignore list.
- Kept the release unsigned at the owner's explicit request.
- Did not install, publish, or push the new release.

### Complete Base p512 full my benchmark

- Completed all 3,409 Pixel 8 `/v1/match` requests with GPU and no segmentation.
- Disabled barcode recognition and response caching.
- Verified a byte-identical query file against the previous Base/224 plus DIS run.
- Measured positive Top-1 of 69.09%, Top-5 of 87.10%, and Top-10 of 90.03%.
- Measured client median of 924 ms and P95 of 1,479 ms over the full 55-minute run.
- Observed no HTTP error, process restart, native abort, or CPU fallback.
- Recorded 955.2 MiB peak sampled PSS and maximum thermal status `SEVERE`.
- Recorded the negative Top-1 regression from 42 to 73 forbidden matches out of 430.
- Recorded the unchanged 9 of 9 no-match false accepts.
- Saved raw predictions, scored results, telemetry, source hashes, and paired changes.
- Added `docs/reports/2026-10-19_pixel8-base-p512-full-my.md` and its JSON report.
- Disabled HTTP, removed forwarding and the UI dump, and restored the power setting.

### Verified Base NaFlex p512 main pipeline

- Changed the application version to `0.2.0` with version code `6`.
- Integrated the pinned `siglip2-naflex-litert` v0.2.0 AAR and complete p512 graph.
- Made full-image encoding without segmentation the default.
- Kept DIS and YOLO as optional query modes.
- Added the format 6 pack with 2,093 matching p512 vectors and 2,093 wine cards.
- Preserved transparent display images and local barcode relations.
- Added an atomic pack exporter with model, profile, index, and payload verification.
- Added automatic migration from older installed packs without clearing user data.
- Added GPU/CPU vector agreement to the first-start check.
- Kept GPU lifecycle operations on one dedicated inference worker.
- Made UI inference and debug HTTP inference mutually exclusive.
- Deferred saved HTTP startup until pack migration and accelerator detection finish.
- Scoped pilot logs to the application processes without clearing system logs.
- Passed 64 debug unit tests, 61 release unit tests, and 16 Python tests.
- Passed debug and release lint and APK assembly.
- Verified byte-exact reference equality with the source index for all 2,093 wines.
- Verified all 2,093 transparent WebP display images.
- Installed the debug APK on Pixel 8 without clearing application data.
- Confirmed automatic pack migration, no segmentation, and automatic GPU on Pixel 8.
- Passed CPU/GPU vector agreement and fourteen desktop/device vector comparisons.
- Completed all thirty pilot HTTP requests without a restart or thermal warning.
- Measured 514.8 ms median and 748.8 ms P95 server latency with a warm GPU model.
- Measured 925.3 MiB peak sampled process PSS.
- Measured 17 of 24 positive Top-1 hits and 21 of 24 positive Top-5 hits on the
  stratified pilot only.
- Verified both `/v1/eval/predict` and `/v1/match` with a known transparent reference.
- Saved raw responses and app-only logs outside Git and aggregate measurements in the
  project report.
- Verified transparent PNG gallery input and UI recognition on GPU at 100-percent
  similarity to its exact reference.
- Verified that the new history row persists after a deliberate cold restart.
- Confirmed that HTTP remains off after restart.
- Removed the test image, UI dump, and ADB forwarding rule.
- Recorded scope and remaining device checks in
  `docs/reports/2026-10-19_base-p512-default.md`.

### NaFlex measurement scope

- Recorded the separate `siglip2-naflex-litert` v0.2.0 library and benchmark app.
- Linked its successful GPU measurements to distinguish them from the split exports.
- Kept the October 19 split-export measurements as historical results.
- Recorded the working copy paths and the pending library integration.

### Pixel 8 split-export measurements

- Exported p256 standard, p256 5a, and p512 standard LiteRT splits outside Git.
- Completed 30 measured requests for all four encoder variants.
- Recorded no process restart and no severe thermal state in 120 requests.
- Rejected all four variants under the combined exact-vector and latency gates.
- Kept fixed p224 as the production control.
- Verified one SO400M p512 match on a Pixel 8 with the external format version 4 pack.
- Matched `chin-chin-vermentino` at `0.977004` in `256.082` seconds.
- Passed debug unit tests, Android lint, debug APK assembly, eleven Python model tests,
  and sixteen Workbench tests before the topic commits.

### Debug HTTP and repeatable device benchmarks

- Added `/v1/debug/embedding` to the debug HTTP server.
- Added per-request accelerator overrides for debug HTTP tests.
- Added runtime, vector dimension, patch limit, pooling mode, and aggregation to health.
- Added deterministic 30-image selection and Pixel 8 measurement tools.
- Added CPU/GPU vector parity measurement.
- Added the `android-device-match-k20-top2-mean` Workbench configuration.
- Kept Base pilot packs separate from compatible retrieval catalogue packs.

### SigLIP2 NaFlex split runtimes and model packs

- Added model-pack format version 4 for `google/siglip2-so400m-patch16-naflex`.
- Added model-pack format version 5 for `google/siglip2-base-patch16-naflex`.
- Added 768-dimensional Base NaFlex p256 and p512 support.
- Added a LiteRT backbone that returns NaFlex patch tokens.
- Added a separate LiteRT pooling model with the original `post_layernorm`, attention
  pooling, pooling LayerNorm, and MLP residual.
- Added Android NaFlex preprocessing with native aspect ratio, 16 by 16 patches, exact
  patch-limit selection, resized position vectors, and padding masks.
- Added support for 256, 512, and 1,024 patch limits.
- Added 1,152-dimensional catalogue vectors and dynamic catalogue validation.
- Added foreground-aware 5a attention pooling.
- Added `max` and `top2-mean` reference aggregation.
- Added an export tool with PyTorch split parity and LiteRT parity checks.
- Added format version 4 support to the catalogue pack builder.
- Added focused Kotlin and Python tests for preprocessing, pack validation, and the
  model split.
- Added a `gpu_compatible` model-pack gate.
- Made all pack builders disable NaFlex GPU by default.
- Made `Auto` select LiteRT CPU/XNNPACK for an unverified split runtime.
- Made explicit GPU selection report a clear error before it can return a false match.
- Keyed the saved accelerator check to the installed model files and patch limit.

### HEIC and HEIF gallery input

- Added `image/heic` and `image/heif` to the gallery picker allowlist.
- Kept `ImageDecoder` as the Android 9 and later decode path.
- Kept the history preview as a local JPEG after recognition.
- Added a unit test for all supported gallery MIME types.
- Updated the application and format documentation.
- Passed debug and release unit tests, lint, and APK assembly.
- Verified the HEIC picker, preview, recognition, and persistent history on a Pixel 8.
- Verified that the Pixel 8 picker shows files with MIME types `image/heic` and
  `image/heif`.
- Verified the gallery and preview accessibility labels with TalkBack enabled.

### Pixel 8 current-patch validation

- Built the version 0.1.4 debug APK from commit `f8b15c2`.
- Passed `testDebugUnitTest`, `lintDebug`, and `assembleDebug`.
- Installed the APK on a Google Pixel 8 with Android 17.
- Verified the model pack, settings, main screen, and debug HTTP server.
- Verified selection and recognition of three photographs.
- Verified the multi-shot early exit after one of three photographs.
- Ran all 3,409 eligible queries of the Workbench `my` test set.
- Completed the run in one application process without `SIGABRT` or another crash.
- Measured positive R@1 0.3327, R@5 0.5646, R@10 0.6441, and MRR 0.4402.
- Measured 1,699 ms median latency and 2,156 ms P95 latency.
- Recorded five HTTP 502 results for four unique images where DIS found no main object.
- Disabled the debug HTTP server after the run.
- Removed the ADB port forward and the temporary device images after the run.

## 2026-10-18

### Multi-shot recognition

- Added selection of one through three photographs.
- Added camera and gallery accumulation for selected photographs.
- Added removal of one selected photograph or all selected photographs.
- Processed the selected photographs in sequence.
- Merged results with the maximum score for each wine.
- Continued recognition when at least one photograph succeeded.
- Used the Top-1 source photograph for debug images and the history preview.
- Added deterministic unit tests for result fusion.
- Added a multi-shot early exit at Top-1 `0.93` and Top-1 to Top-2 margin `0.08`.
- Added unit tests for the early-exit score, margin, and candidate-count rules.

- Listed downloadable model packs as a possible future feature.
- Kept model-pack download and replacement outside the current project scope.

## 2026-10-17

### Realme USB smoke test

- Verified cold start on a Realme RMX3890 with Android 14.
- Verified the installed 0.1.5 debug application and model pack.
- Ran 10 queries through `/v1/eval/predict` with zero request errors.
- Ran 10 queries through `/v1/match?k=20` with zero request errors.
- Measured recall@1 0.5 for both endpoints.
- Measured recall@5 0.7 for `/v1/match?k=20`.
- Confirmed that Logcat contained no `FATAL EXCEPTION` or `SIGABRT`.
- Disabled the debug HTTP server after the test.
- Removed the ADB port forward after the test.

## 2026-10-03

### Five-degree Android reference rotation

- Added the Workbench entry `android-siglip2-base-224-dis-white-rot5`.
- Added 72 reference angles from 0 degrees through 355 degrees for each catalogue image.
- Rotated the DIS result before `square_on_white` and the 224 by 224 resize.
- Kept the 0-degree frame equal to the existing Android model input.
- Kept one SigLIP2 query vector on the Android device.
- Kept maximum cosine scoring across all reference rows of one wine.
- Changed the catalogue exporter default to the rotated index.
- Added an `angle` value to each generated candidate relation.
- Added strict validation for the 5-degree sequence and 72 rows per wine.
- Passed four Android catalogue exporter tests and 26 Workbench rotation tests.
- Did not generate the full catalogue index or APK in this change.

### DIS and YOLO segmentation modes

- Added the `DIS / YOLO` segmentation setting.
- Added the official `yolo26n-seg` w8a32 LiteRT model at 640 by 640 pixels.
- Kept only COCO class 39, `bottle`.
- Selected the largest central bottle mask.
- Removed letterbox padding before the white-background crop.
- Kept YOLO inference on CPU.
- Added model-pack format version 3 and a verified YOLO payload.
- Kept format versions 1 and 2 readable.
- Reused one LiteRT environment, compiled model, and buffer set across requests.
- Prevented two live GPU models in the DIS pipeline.
- Added unit tests for YOLO bottle selection, normalized boxes, mask generation, and
  settings fallback.
- Ran controlled DIS and YOLO evaluations on 100 images on a Google Pixel 8.
- DIS with SigLIP2 CPU accepted 38 of 100 images.
- YOLO with SigLIP2 CPU accepted 23 of 100 images.
- YOLO did not find a complete bottle in 30 images.
- Both 100-request runs completed without `SIGABRT`.
- Passed six Python pack-builder tests, Android debug unit tests, `lintDebug`, and
  `assembleDebug`.
- Installed the final debug APK on a Google Pixel 8.
- Kept the debug HTTP server off after the test.

## 2026-09-29

### GitHub Android pre-release

- Created the private GitHub pre-release `android-v0.1.4`.
- Attached the optimized test-signed release APK and the debug APK.
- Attached a SHA-256 checksum file for both APK files.
- Marked the release as a pre-release because both APK files use the Android debug
  certificate.
- Verified the uploaded asset states, byte sizes, and GitHub SHA-256 digests.
- Kept the unsigned APK out of the installable release assets.

### Debug device evaluation API

- Added a labelled collage of the 10 Pixel 8 smoke-test photographs.
- Recorded why the unbalanced 10-query sample reached only 30 percent recall@1.
- Kept the debug HTTP server off by default.
- Added the debug-only `HTTP-сервер для тестов` settings switch.
- Started and stopped the server immediately when the switch changed.
- Saved the switch value between application starts.
- Passed 21 debug unit tests, `lintDebug`, `compileReleaseKotlin`, and `assembleDebug`.
- Verified the default, enabled, persisted, and disabled states on a Google Pixel 8.
- Added a debug-only NanoHTTPD server on port 18088.
- Added matcher-compatible `POST /v1/eval/predict` and `POST /v1/match` operations.
- Added `GET /healthz` with the installed pack state.
- Used the installed model pack and the saved DIS and SigLIP2 accelerator settings.
- Limited uploads to 20 MiB and serialized model inference.
- Kept the server and NanoHTTPD dependency out of the release runtime.
- Added unit tests for `k` validation and both response shapes.
- Passed `lintDebug`, `testDebugUnitTest`, `assembleDebug`, and `compileReleaseKotlin`.
- Built and installed `chtozavino-0.1.4-debug.apk` on a Google Pixel 8.
- Ran 10 images from Workbench through each endpoint with zero request errors.
- `/v1/eval/predict` gave recall@1 0.3 with 4,349 ms median latency.
- `/v1/match?k=20` gave recall@1 0.3, recall@5 0.6, and recall@10 0.9 with
  4,597 ms median latency.

### Optimized release build

- Ran release unit tests and `lintRelease`.
- Ran R8 code optimization and resource shrinking.
- Built the unsigned release APK for version 0.1.4.
- Added the versioned output copy
  `chtozavino-0.1.4-release-unsigned.apk`.
- Verified the package ID, version, SDK levels, ZIP alignment, and embedded model pack.
- Recorded that production signing is not configured.

### Transparent Android catalogue export

- Changed the workbench exporter to package transparent package cuts.
- Stopped packaging the large `main` and `main_patched` source images.
- Kept source image selection only for vector and cut provenance.
- Converted display images to transparent WebP at quality 80.
- Limited the display image long side to 1,024 pixels.
- Added image hash, format, dimension, and transparency validation.
- Added parallel image conversion and atomic pack replacement.
- Added tests for transparent export, resize, provenance, and opaque-cut rejection.
- Exported 2,093 vectors, wines, and images.
- Reduced the generated pack from 531,950,661 bytes to 429,200,870 bytes.

### Versioned APK file name

- Added the application version to the distribution APK file name.
- The version 0.1.4 distribution file is `chtozavino-0.1.4-debug.apk`.
- Kept `versionName` as the single value that supplies the APK file name.
- Changed the distribution task to `Sync` so that an obsolete APK does not stay in
  the output directory.
- Passed `lintDebug`, debug and release unit tests, and `assembleDebug`.
- Verified version code 5, version name 0.1.4, `minSdkVersion` 28, and
  `targetSdkVersion` 36 in the versioned APK.

### Verified marketing screenshots

- Added eight primary screenshots from the installed version 0.1.4 application on a
  Google Pixel 8.
- Added full PNG source files and cropped WebP website files.
- Added a high-resolution contact sheet for presentations.
- Added separate detail views for the crop, white-background, and settings-about
  sections.
- Verified the photo example through DIS, SigLIP2, local search, and persistent
  history.
- Verified the photo result as `Пино Нуар` at `Сходство: 91%`.
- Verified a physical EAN-13 camera scan through Google Code Scanner.
- The code `4630037250909` matched `Шато Тамань. Каберне Совиньон` at
  `Сходство: 100%`.
- Restored the Pixel 8 dark system theme after capture.
- Disabled System UI demo mode and removed the temporary image after capture.

### Lowercase application ID

- Changed the application ID to `chtozavino.alolalab.com`.
- Changed the version to `0.1.4` with version code 5.
- Removed the old `Chtozavino.alolalab.com` installation from the Realme test phone.
- Kept the unrelated `com.alolalab.storagetracker*` applications unchanged.
- Installed the full APK on the Google Pixel 8.
- Installed the built-in pack with 2,093 wines, vectors, and images on the Pixel 8.
- Verified that the Pixel 8 automatic check selected GPU for DIS and SigLIP2.
- Completed one full Pixel 8 recognition with the production pack.
- The source wine matched `Пино Нуар` at `Сходство: 91%`.
- Verified the DIS mask debug view and persistent history on the Pixel 8.
- Verified the result link to the exact `vino-svoe.ru/wines/...` page.
- Verified the settings link to `https://vino-svoe.ru`.
- Verified all settings values and controls in the Pixel 8 dark system theme.
- Built the 576,503,269-byte `chtozavino-0.1.4-debug.apk`.
- The APK SHA-256 is
  `e22d166c8922936dd75acb63ec0b860334ef982caf5bbde36c5bb5c079227c26`.

### Result wording and interface polish

- Changed the version to `0.1.3` with version code 4.
- Replaced the raw cosine label with `Сходство` and a whole-percent value.
- Added two similarity-format unit tests for each build variant.
- Replaced the bottom navigation glyphs with clear 30 dp vector icons.
- Changed the main subtitle to `Не требует интернета`.
- Added the `Сайт «Что за вино?»` link below the application version.
- Added a clear history empty-state message.
- Added the friendly build artifact `chtozavino_debug.apk`.
- Verified the system-controlled light and dark themes on the Realme Android 14 phone.
- Verified that a successful recognition creates a persistent history row.
- Built the 576,503,277-byte `chtozavino_debug.apk`.
- The APK SHA-256 is
  `be7a24ca7db3d182a87c931b6c7d154f69892e28735e7f211a45e4650f55a828`.

### Per-model accelerators and product icon

- Changed the version to `0.1.2` with version code 3.
- Added a first-start GPU compatibility check for DIS and SigLIP2.
- Added a saved automatic accelerator selection for each model.
- Added independent `Авто`, `GPU`, and `CPU` controls for DIS and SigLIP2.
- Kept a CPU retry for a failed GPU result in `Авто` mode.
- Added four accelerator-selection unit tests for each build variant.
- Added an extra DIS output-size test for each build variant.
- Converted `assets/product-logo-640x640.png` to adaptive and fallback launcher
  resources.
- Verified that the automatic check selected DIS GPU and SigLIP2 CPU on the Realme
  Android 14 phone.
- Repeated the full recognition on that phone.
- The test image matched `Пино Нуар` at cosine 0.910.
- The run used DIS GPU for 6,454 ms, SigLIP2 CPU for 3,027 ms, and local search for
  201 ms.
- Tested the same DIS and SigLIP2 files on a Google Pixel 8 with Android 17.
- The Pixel 8 automatic check selected GPU for DIS and GPU for SigLIP2.
- The Pixel 8 saved both selections across an application restart.
- The Pixel 8 matched `Пино Нуар` at cosine 0.909.
- The Pixel 8 run used DIS GPU for 2,546 ms and SigLIP2 GPU for 2,287 ms.
- Verified the DIS mask, crop, and white-background debug images on the Pixel 8.
- Built the 576,832,975-byte debug APK.
- The APK SHA-256 is
  `173ee058ad5681242d275a9fb0bb6a28035fd0f261df30323ff44ca269d2f980`.

### Built-in DIS catalogue

- Added model-pack format version 2 with a verified `images.zip` payload.
- Added a catalogue pack builder for
  `android-siglip2-base-224-dis-white`.
- Added one vector, one candidate relation, and one catalogue image for each included
  wine.
- Selected `main_patched` before `main`.
- Added first-start installation of the pack from the APK.
- Kept format version 1 parsing for development tools.
- Added the catalogue image to each recognition result.
- Added sampled preview decoding to limit memory use for large catalogue images.
- Built a pack with 2,093 wines, 2,093 vectors, 2,093 images, and 135 local code
  relations.
- Omitted five active wines that have no `main_patched` or `main` image.
- Verified 23 `main_patched` selections and 2,070 `main` selections.
- Verified that all 768-dimensional vectors are finite and L2-normalized.
- Built the debug APK with the 531,950,661-byte pack stored in
  `assets/default_model_pack.zip`.
- Passed Python tests, Android debug and release unit tests, `lintDebug`, and
  `assembleDebug`.
- Installed the APK on an arm64 Android 14 phone.
- Verified the first-start installation of all 2,093 images and the format version 2
  manifest on the phone.

### Device inference and interface corrections

- Changed the version to `0.1.1` with version code 2.
- Added validation for the SigLIP2 output size, finite values, and vector norm.
- Added an automatic CPU retry when GPU SigLIP2 returns an invalid output.
- Disabled later SigLIP2 GPU attempts in the same process after this failure.
- Added four SigLIP2 vector-normalization tests for each build variant.
- Added a settings page through a gear icon.
- Removed the model-pack replacement action from the user interface.
- Replaced the long camera and gallery labels with compact icon buttons.
- Enabled Google Code Scanner manual input as a fallback for EAN-13.
- Added scanner cancellation, empty-result, and failure feedback.
- Verified the CPU fallback on an arm64 Android 14 phone.
- The test catalogue image matched its own wine at cosine 0.910.
- A repeated run used DIS on GPU for 6,307 ms, SigLIP2 on CPU for 2,920 ms, and local
  search for 236 ms.

## 2026-09-28

### Initial Android application

- Added an Android 9 application project with the ID `Chtozavino.alolalab.com`.
- Added the offline DIS and SigLIP2 recognition contract.
- Added the verified external model-pack contract.
- Added the Russian user-flow specification and smoke tests.
- Added the model-pack builder with strict model, dimension, pipeline, and hash checks.
- Added local cosine-search and barcode normalization tests.
- Added a model-pack builder test that rejects the current 1,152-dimensional GX10 vectors.
- Verified lint, unit tests, and the debug APK build with JDK 17.
- Verified `minSdkVersion` 28, `targetSdkVersion` 36, and the application ID in the APK.
- Kept model files and catalogue vectors outside Git.

### DIS mask normalization

- Added the per-image min-max normalization of the reference DIS inference code.
- Fixed full-frame selection from the raw LiteRT output range of 0.5 to 0.731.
- Added unit tests for the measured range, a flat mask, and a non-finite mask.

### SigLIP2 vector compatibility

- Added the timm `crop_pct=0.9` preprocessing to the Android SigLIP2 encoder.
- Changed the model-pack pipeline ID to `dis-white-square-timm-crop090-v2`.
- Added a reproducible LiteRT-to-GX10 vector comparison tool.
- Pinned the accepted DIS and SigLIP2 model files by SHA-256 in the pack builder and
  the Android pack importer.
- Verified the SigLIP2 model on 32 catalogue images.
- The minimum cosine value was 0.9999985 across both indices after matching the
  preprocessing.
