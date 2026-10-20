# Assessment map

| Field | Value |
|---|---|
| Repository | `s1mb1o/svoe-vino-lab-dev` |
| Branch | `main` |
| Checked at commit | `db288cc9` |
| Date of the last check | 2026-10-20 |
| Scope | This file describes `main` of this repository only. |
| Task | Task #10 «Сканер российских вин с описанием на платформе Свое Вино» ([docs/task-10-specification.pdf](docs/task-10-specification.pdf)) |

## About this file

This file is an index of the features in this repository. It is for the hackathon organizers and the jury: people and LLMs. It is not development documentation. For development, read the `README.md`, `AGENTS.md`, and `CLAUDE.md` files of each component.

- Each row states one fact about the repository.
- Each fact has at least one proof. A proof is a file, a test, a command, or an artifact that you can open in this repository.
- This file contains facts only. It does not contain opinions, rankings, or marketing statements.
- The status of each feature is `Deployed`, `Implemented`, or `Research-only`. The section "Known gaps and work outside `main`" lists what is partial or missing.

Read "Highlights" first. Then read the section for the criterion that you check. Use the "Verify" line for a fast check. Live URLs are secondary proofs, because a review can run without network access.

### Status terms

| Status | Meaning |
|---|---|
| `Deployed` | A ChangeLog, ResearchLog, SMOKE_TESTS, or report file in this repository records a live deployment and a live check. |
| `Implemented` | The code and its tests are on `main`. No live deployment is recorded in this repository. |
| `Research-only` | The workbench contains the feature or experiment. The default matcher configuration does not use it. |
| `Partial` | A part of the feature works. The "Limits" line states the missing part. |
| `Demo` | The UI shows the feature with fixed or sample data, and the UI labels it as a demo. |

### Test commands

Each feature refers to the test command of its component. Real inference needs model weights. The weights are not in Git (see F-33).

| Component | Command | Source |
|---|---|---|
| `matcher/` | `python -m unittest discover -s matcher/tests -v` | [SETUP.md](SETUP.md), [matcher/TESTING.md](matcher/TESTING.md) |
| `matcher-inspector/` | `cd matcher-inspector && python -m unittest discover -s tests -v` | [matcher-inspector/README.md](matcher-inspector/README.md) |
| `webui/` | `cd webui && npm test` | [webui/package.json](webui/package.json) |
| `telegram-bot/` | `cd telegram-bot && uv sync --extra dev && uv run pytest -q` | [telegram-bot/README.md](telegram-bot/README.md) |
| `max-bot/` | `cd max-bot && ./scripts/verify.sh` | [max-bot/README.md](max-bot/README.md) |
| `im-core/` | `cd im-core && uv run pytest -q` | [im-core/README.md](im-core/README.md) |
| `mcp/` | `cd mcp && npm ci --ignore-scripts && npm test` | [mcp/README.md](mcp/README.md) |
| `account/` | `cd account && ./scripts/verify.sh` | [account/README.md](account/README.md) |
| `dinner-lens/` | `cd dinner-lens && .venv/bin/python -m unittest discover -s tests -v` | [dinner-lens/README.md](dinner-lens/README.md) |
| `android/` | `cd android && ./gradlew test assembleDebug` | [android/README.md](android/README.md) |
| `ios/` | `cd ios && xcodebuild -project ChtoZaVino.xcodeproj -scheme ChtoZaVino -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath DerivedData CODE_SIGNING_ALLOWED=NO test` | [ios/README.md](ios/README.md) |
| `bootstrap/` | `cd bootstrap && .venv/bin/python -m unittest discover -s tests -v` | [bootstrap/README.md](bootstrap/README.md) |
| `proxies/` | `cd proxies && .venv/bin/python -m unittest discover -s tests -t .` | [proxies/README.md](proxies/README.md) |
| `workbench/` | `cd workbench && python3 -m unittest discover -s tests` | [workbench/README.md](workbench/README.md) |

Some suites need files that are not in Git:

- The `dinner-lens/` tests need the embedding indexes `dinner-lens/data/index/` and `dinner-lens/data/index.v4/` (F-27).
- The `android/` build needs `android/app/src/main/assets/default_model_pack.zip` (F-44).
- The `ios/` build needs the generated Core ML models and the resource pack ([ios/project.yml](ios/project.yml)).
- The `workbench/` suite has 14 known failures in 2,567 tests ([workbench/ChangeLog.md](workbench/ChangeLog.md) 2026-10-20). Three come from the open port of the re-rank prompts (F-07). Eleven need files outside this repository or are lab defects.

## Highlights

1. **Offline recognition on an Android phone.** The phone encodes the full photo with SigLIP2 Base NaFlex p512 and searches 2,093 wines without network. On a Pixel 8, the internal set `my` gave Top-1 69.09% with a median client time of 924 ms. The release manifest has no `INTERNET` permission. See F-80 to F-83 and F-89. A native iPhone app with on-device Core ML recognition is on `main` too (F-94).
2. **A cascade matcher with a fixed answer time.** Barcode and QR scan, SAM3 package crop, and a VLM cluster re-rank run in parallel. The matcher answers at 2.9 s and cancels the remaining model calls. See F-04 and F-61.
3. **Recognition of a full shelf in one request.** One photo gives a mask, a box, and a wine card for each bottle. A production check recorded 93 matched bottles in one response. See F-20.
4. **Image moderation before the first disk write.** ShieldGemma 2 checks each photo. Unsafe photos go to a closed quarantine, and the admin UI shows only a blurred preview. See F-73.
5. **Two messengers on one shared core.** The Telegram bot and the MAX bot share `im-core/`. A drift test guards the copied modules. See F-31, F-70, and F-71.
6. **Confidence-aware answers.** Score and margin thresholds select a confident card, a tentative card, or «Не уверен». A negative feedback shows ranks 2 to 4. See F-09 and F-25.
7. **A taste passport and regional dishes after the result.** Each value shows its source: the wine card or a labeled dataset estimate. See F-21 and F-22.
8. **A verifiable matcher build.** The embedding bundle is in Git and the matcher checks its SHA-256 at load. Dependencies are hash-locked. CI fails when any test is skipped. See F-32 and F-33.
9. **Committed benchmark artifacts.** Run directories with queries and predictions are in Git. A reviewer can recompute R@1 offline. See F-10 and F-11.
10. **Two MCP interfaces for AI agents.** WebMCP tools in the portal let an AI agent in a supported browser drive the same scanner and shelf state that a user sees. A local read-only MCP server gives an AI assistant the wine card, filter search, and comparison of the 2,093 Active catalogue wines. See F-77 and F-48.
11. **Wine for a dish.** The portal mode `/dish` takes a dish photo or a dish name. A separate service recognizes the dish with a local VLM, filters the wines with code rules, and shows editorial choices before embedding results. See F-27 to F-29.

12. **Retrieval algorithm research reference.** A committed document defines 39 pooling profiles and 42 fusion policies. It records 353,188 unique configurations per frozen testset, including p512 leaderboards and exact recipes. The research uses no re-ranking. See F-112.

## Results summary

| Metric | Value | Dataset | Pipeline | Source |
|---|---|---|---|---|
| Top-1 match with the team reference | 95/100 | 100 organizers' photos; reference answers made by the team | `POST /v1/eval/predict` | [README.md](README.md) section «Результаты», [predictions.jsonl](predictions.jsonl) |
| R@1 / R@5 | 90.48% / 100% | Organizers' photos: 63 positive and 21 negative, labels by the team | `cascade-p512-rot5`, `POST /v1/match`, no time limit | [README.md](README.md) section «Предыдущие инженерные бенчмарки», [workbench/ResearchLog.md](workbench/ResearchLog.md) |
| R@1 with the 3 s budget | 90.0%, 81 of 81 photos answered within 3 s | Organizers' photos | `cascade-p512-rot5` with `fast_answer` | [matcher/ResearchLog.md](matcher/ResearchLog.md) |
| R@1 / R@5 | 84.67% / 97.02% | Internal set `my`: 1,644 positive and 584 negative queries | `barcode-rerank-siglip2-512-crop` (workbench) | [BENCHMARKS.md](BENCHMARKS.md), [workbench/docs/reports/2026-09-27_all-profile-rerun/final-profile-comparison.md](workbench/docs/reports/2026-09-27_all-profile-rerun/final-profile-comparison.md) |
| R@1 / R@5 | 74.15% / 92.94% | Internal set `my` | `siglip2-p512-as-is` (default of [matcher/config.yaml](matcher/config.yaml)) | [BENCHMARKS.md](BENCHMARKS.md) |
| R@1 with the 3 s budget | 93.65% (59 of 63 positive photos), 0 errors, p50 1,353 ms, max 2,905 ms | Organizers' photos (lab set `official-real-photos`, 84 photos), labels by the team | `cascade-p512-rot5` with `fast_answer` and a local FP8 VLM on an RTX 4090 host (F-66) | [workbench/ResearchLog.md](workbench/ResearchLog.md) 2026-10-01 |
| Top-1 / Top-5 / Top-10 on the phone | 69.09% / 87.10% / 90.03%, median 924 ms | Internal set `my`: 2,970 positive assignments of 3,409 queries | Android, SigLIP2 Base NaFlex p512, full photo, Pixel 8 GPU (F-89) | [android/docs/reports/2026-10-19_pixel8-base-p512-full-my.md](android/docs/reports/2026-10-19_pixel8-base-p512-full-my.md) |

The 95/100 value is an internal check of the team. It is not an official jury result ([README.md](README.md)).

The phone row and the workbench rows of the set `my` use different query cohorts. Do not compare these percentages directly.

## Criterion 1: search result accuracy (50/100)

### F-01 Official prediction contract

- **Claim:** `POST /v1/eval/predict` accepts a multipart `image` and returns `{"slug": ...}`. This is the contract of the organizers' harness.
- **Status:** Deployed ([matcher/docs/reports/2026-09-29_production-stress-test.md](matcher/docs/reports/2026-09-29_production-stress-test.md)).
- **Entry point:** [matcher/app.py](matcher/app.py)
- **Proof:** `matcher/tests/test_official_harness.py::test_the_official_harness_gets_the_three_configured_slugs`; [eval/participant_test.sh](eval/participant_test.sh) (the organizers' harness).
- **Verify:** Read [matcher/tests/test_official_harness.py](matcher/tests/test_official_harness.py).
- **Limits:** A real answer needs a SigLIP2 model service.

### F-02 Ranked candidates with wine cards

- **Claim:** `POST /v1/match?k=1..20` returns ranked candidates with full wine cards. Rank 1 always equals the answer of `/v1/eval/predict`.
- **Status:** Deployed.
- **Entry point:** [matcher/app.py](matcher/app.py), [matcher/openapi.yaml](matcher/openapi.yaml)
- **Proof:** `matcher/tests/test_match.py::test_the_first_ranked_wine_is_the_top1_wine`, `matcher/tests/test_match.py::test_match_returns_ranked_candidates_with_cards`.
- **Verify:** Read [matcher/openapi.yaml](matcher/openapi.yaml).

### F-03 Default pipeline with an in-Git bundle

- **Claim:** The default pipeline `siglip2-p512-as-is` embeds the whole photo with SigLIP2 so400m NaFlex p512 and ranks wines by the maximum cosine over the `full` view. The bundle in Git has 2,094 wines and 4,642 vectors.
- **Status:** Deployed.
- **Entry point:** [matcher/config.yaml](matcher/config.yaml), [matcher/siglip2.py](matcher/siglip2.py), [matcher/bundle.py](matcher/bundle.py), [matcher/data/gx10-siglip2-so400m-patch16-naflex-p512/manifest.json](matcher/data/gx10-siglip2-so400m-patch16-naflex-p512/manifest.json)
- **Proof:** `matcher/tests/test_siglip2.py::test_the_default_config_selects_the_siglip2_pipeline`, `matcher/tests/test_siglip2.py::test_the_best_full_view_cosine_wins_and_label_vectors_are_ignored`.
- **Verify:** Read the counts in the bundle `manifest.json`.
- **Limits:** R@1 is 74.15% on the internal set `my` (see "Results summary"). The model endpoints in [matcher/config.yaml](matcher/config.yaml) are LAN addresses of the team. Another host needs an edited YAML file. Since `da8c8954`, the matcher reads no endpoint environment variable.

### F-04 Cascade backend

- **Claim:** The `cascade` backend runs a barcode and QR scan, SAM3, and a whole-photo SigLIP2 vector in parallel. Then it embeds the package crop, scans the crop for codes, and re-ranks the candidates in a visual cluster with VLM label rules. A fixed order of answer sources selects the result.
- **Status:** Implemented. [README.md](README.md) states that the production matcher uses the pipeline `cascade-p512-rot5`.
- **Entry point:** [matcher/cascade.py](matcher/cascade.py), [matcher/cascade_run.py](matcher/cascade_run.py), [matcher/docs/cascade.md](matcher/docs/cascade.md)
- **Proof:** `matcher/tests/test_cascade.py::test_a_package_code_beats_the_full_photo_code`, `matcher/tests/test_cascade.py::test_a_verdict_reorders_the_cluster_and_keeps_the_position_scores`; [matcher/tests/test_cascade_api.py](matcher/tests/test_cascade_api.py).
- **Verify:** Read [matcher/docs/cascade.md](matcher/docs/cascade.md).
- **Limits:** The cascade needs the lab catalogue copy and the rotated index. These files are not in Git. It also needs four model services.

### F-05 Rotated reference vectors

- **Claim:** Bundle format v3 stores one vector row for each rotation angle of a reference image. A wine gets the maximum cosine over the angles.
- **Status:** Implemented. The `cascade` backend uses it.
- **Entry point:** [matcher/bundle.py](matcher/bundle.py)
- **Proof:** [matcher/tests/test_rotation.py](matcher/tests/test_rotation.py); [workbench/tests/test_rotated_embeddings.py](workbench/tests/test_rotated_embeddings.py).
- **Verify:** Read [matcher/tests/test_rotation.py](matcher/tests/test_rotation.py).

### F-06 Barcode and QR rules

- **Claim:** A barcode or QR code of exactly one wine answers at once. A GTIN that belongs to several wines limits the candidates to those wines. A QR URL that belongs to several wines never decides the answer.
- **Status:** Implemented.
- **Entry point:** [matcher/codes.py](matcher/codes.py), [workbench/pipeline/barcode.py](workbench/pipeline/barcode.py)
- **Proof:** `matcher/tests/test_cascade.py::test_a_shared_qr_url_never_decides`; `workbench/tests/test_barcode_shared.py::test_a_unique_code_wins_over_a_shared_gtin_that_came_first`.
- **Verify:** Read [workbench/tests/test_barcode_shared.py](workbench/tests/test_barcode_shared.py).
- **Limits:** The catalogue has codes for a small part of the wines.

### F-07 Visual clusters and VLM label rules

- **Claim:** The workbench groups similar wines into clusters by embedding similarity, GTIN, and manual links. A VLM writes label rules for each cluster. Code checks validate the rules. The re-rank applies the rules inside the top-k window.
- **Status:** Implemented in the workbench. The `cascade` backend uses the committed rules.
- **Entry point:** [workbench/pipeline/build_clusters.py](workbench/pipeline/build_clusters.py), [workbench/pipeline/build_label_rules.py](workbench/pipeline/build_label_rules.py), [workbench/pipeline/cluster_rerank.py](workbench/pipeline/cluster_rerank.py), [matcher/rerank.py](matcher/rerank.py)
- **Proof:** `workbench/tests/test_cluster_rerank.py::test_the_rule_moves_the_card_up`; `workbench/tests/test_label_rules.py::test_a_bottle_number_and_a_feature_outside_the_label_are_never_valid`; [workbench/data/catalog/embeddings/gx10-siglip2-so400m-patch16-naflex-p512/cluster-rules.json](workbench/data/catalog/embeddings/gx10-siglip2-so400m-patch16-naflex-p512/cluster-rules.json).
- **Verify:** Read [workbench/ResearchLog.md](workbench/ResearchLog.md) (paired McNemar test of the re-rank).
- **Limits:** The workbench re-rank prompts differ from the prompts of [matcher/rerank.py](matcher/rerank.py). The lab changes of `matcher/rerank.py` are not in this repository. `workbench/tests/test_cluster_rerank.py::test_the_prompts_equal_the_prompts_of_the_matcher` fails, and `workbench/tests/test_matcher_parity.py` has 2 failures ([workbench/ChangeLog.md](workbench/ChangeLog.md) 2026-10-20).

### F-08 Hand-aware main package selection

- **Claim:** An option selects the package that a hand holds and crops it with SAM3 before the embedding.
- **Status:** Implemented. The option is off by default.
- **Entry point:** [matcher/main_scene.py](matcher/main_scene.py), [matcher/docs/hand-selection.md](matcher/docs/hand-selection.md)
- **Proof:** [matcher/tests/test_hand_selection.py](matcher/tests/test_hand_selection.py); `workbench/tests/test_main_scene.py::test_a_held_can_beats_many_shelf_bottles`.
- **Verify:** Read [matcher/docs/hand-selection.md](matcher/docs/hand-selection.md).

### F-09 Confidence-aware bot answers

- **Claim:** The bots compare the matcher score and margin with thresholds (0.70 and 0.015). A low confidence gives a tentative Top-1 card with a request for another photo. An empty matcher answer gives «Не уверен».
- **Status:** Deployed for Telegram ([telegram-bot/ChangeLog.md](telegram-bot/ChangeLog.md), 2026-10-05). Implemented for MAX.
- **Entry point:** [telegram-bot/src/chto_za_vino_bot/config.py](telegram-bot/src/chto_za_vino_bot/config.py) (`match_min_score`, `match_min_margin`), [telegram-bot/src/chto_za_vino_bot/app.py](telegram-bot/src/chto_za_vino_bot/app.py)
- **Proof:** `telegram-bot/tests/test_processor_quality.py::test_confidence_changes_the_wording_and_keeps_the_wine_card`, `telegram-bot/tests/test_processor_quality.py::test_an_empty_matcher_answer_abstains`; [max-bot/ChangeLog.md](max-bot/ChangeLog.md) 2026-10-17 (live run).
- **Verify:** Read [telegram-bot/tests/test_processor_quality.py](telegram-bot/tests/test_processor_quality.py).

### F-10 Benchmark runner and committed run artifacts

- **Claim:** The benchmark runner writes a run directory with `run.json` (git commit, backend, index, counts, cache and barcode switches), queries, predictions, metrics, and a summary. Metrics are R@1, R@5, R@10, MRR, F1@1, F1@5, and "forbidden top-1" on negative queries.
- **Status:** Implemented.
- **Entry point:** [workbench/pipeline/benchmark.py](workbench/pipeline/benchmark.py), [workbench/scripts/match_scoring.py](workbench/scripts/match_scoring.py)
- **Proof:** `workbench/tests/test_benchmark.py::test_the_metrics_are_the_metrics_of_match_scoring`, `workbench/tests/test_benchmark.py::test_the_runner_does_not_write_to_the_database`; run directories [workbench/runs-1/2026-09-27T011711Z-lab-barcode-rerank-siglip2-512-crop-my/](workbench/runs-1/2026-09-27T011711Z-lab-barcode-rerank-siglip2-512-crop-my/) and [workbench/runs-1/2026-09-27T020325Z-lab-siglip2-p512-as-is-my/](workbench/runs-1/2026-09-27T020325Z-lab-siglip2-p512-as-is-my/).
- **Verify:** Join `queries.jsonl` with `predictions.jsonl` in a run directory and count the correct Top-1 answers.
- **Limits:** The committed runs moved from `workbench/runs/` to `workbench/runs-1/` ([workbench/ChangeLog.md](workbench/ChangeLog.md) 2026-10-01).

### F-11 Test sets and annotation audit

- **Claim:** The workbench manages test sets with labels, "No Match" photos, boxes, and tags. It can make a new test set from the misses of a run. An annotation audit computes the Top-1 ceiling of the internal set `my`.
- **Status:** Implemented.
- **Entry point:** [workbench/pipeline/testset_routes.py](workbench/pipeline/testset_routes.py), [workbench/pipeline/testset_from_run.py](workbench/pipeline/testset_from_run.py), [workbench/dataset/test-1/README.md](workbench/dataset/test-1/README.md)
- **Proof:** [workbench/tests/test_testset_from_run.py](workbench/tests/test_testset_from_run.py); [workbench/docs/reports/2026-09-27_all-profile-rerun/annotation-audit.md](workbench/docs/reports/2026-09-27_all-profile-rerun/annotation-audit.md).
- **Verify:** Read the annotation audit report.

### F-12 Fingerprinted rerun of 53 profiles

- **Claim:** One queue reran 53 recognition profiles. Each attempt records fingerprints of the source map, the configuration, the query identity, and the catalogue.
- **Status:** Implemented.
- **Entry point:** [workbench/scripts/run_internal_profile_queue.py](workbench/scripts/run_internal_profile_queue.py)
- **Proof:** `workbench/tests/test_run_internal_profile_queue.py::test_default_inspection_never_writes_or_calls_api`; [workbench/docs/reports/2026-09-27_all-profile-rerun/final-production-source-check.md](workbench/docs/reports/2026-09-27_all-profile-rerun/final-production-source-check.md).
- **Verify:** Read the fingerprint table in `final-production-source-check.md`.

### F-13 Shelf pipeline with label evidence

- **Claim:** `matcher.group_pipeline` selects a separate pipeline for `POST /v1/group/match`. Single-image requests keep `matcher.pipeline`. The pipeline `siglip2-p512-rot5-seg` ranks each masked bottle against the `full` view, uses the best reference rotation at 5-degree steps, and rejects scores below 0.78. With `quality_model` and `quality_endpoint`, a VLM reads each bottle label. Deterministic catalogue identity checks then accept or reject the candidates, and the response has `label_evidence`.
- **Status:** Implemented. [matcher/README.md](matcher/README.md) states that production uses the shelf pipeline `siglip2-p512-rot5-seg-vlm9b` with the VLM `qwen3.5-9b-nvfp4`. [matcher/config.yaml](matcher/config.yaml) defines only `siglip2-p512-rot5-seg` and keeps `group_pipeline` as a comment.
- **Entry point:** [matcher/group_pipeline.py](matcher/group_pipeline.py), [matcher/group_quality.py](matcher/group_quality.py), [matcher/group_quality_runtime.py](matcher/group_quality_runtime.py)
- **Proof:** `matcher/tests/test_group_pipeline.py::test_separate_group_selection_and_full_ranking_ignore_label_disagreement`; `matcher/tests/test_group_quality.py::test_only_printed_attributes_veto_visual_candidates`, `matcher/tests/test_group_quality.py::test_one_shared_brand_word_does_not_identify_another_producer`; [matcher/ChangeLog.md](matcher/ChangeLog.md) 2026-10-18 (port of the production matcher `8b096a16`).
- **Verify:** Read the section «POST /v1/group/match» in [matcher/README.md](matcher/README.md).
- **Limits:** The pipeline needs the rotated index `gx10-siglip2-so400m-patch16-naflex-p512-rot5` and a VLM service. The index is not in Git. The repository has no shelf accuracy benchmark (F-20).

### F-14 Patch-weight re-rank experiments

- **Claim:** An experiment re-ranks the cropped SigLIP2 result with weights for bottle and label patches. The frozen `my` cohort has 2,374 positive and 534 negative assignments and a gallery of 2,166 wines. Fixed patch weights give 2,058 Top-1 hits. Standard cropped SigLIP2 gives 2,048. Named negative false matches change from 82 to 85. Cap, neck, and label region weights give 2,067 Top-1 hits and 87 negative false matches. The default stays the standard ranking. The Runs step popup shows the patch weights of a saved query.
- **Status:** Research-only.
- **Entry point:** [workbench/pipeline/patch_inspection.py](workbench/pipeline/patch_inspection.py), [workbench/docs/lab-openapi.yaml](workbench/docs/lab-openapi.yaml) (`/api/run-patches`)
- **Proof:** [workbench/ChangeLog.md](workbench/ChangeLog.md) entries of 2026-10-15 (full `my` patch benchmark, cap and neck weights, tight crop, partial-label rotation guard); `workbench/tests/test_patch_inspection.py::test_status_read_does_not_start_inference`, `workbench/tests/test_patch_inspection.py::test_missing_cached_masks_make_no_model_request`.
- **Verify:** Read the 2026-10-15 entries of [workbench/ChangeLog.md](workbench/ChangeLog.md).
- **Limits:** The patch code `patch_pipeline`, the report `PATCH_PIPELINE_REPORT.md`, and the evidence are in the sibling repository `svoe-vino-lab-experiments`. This repository cannot reproduce the numbers. For the region weights, the paired interval includes zero.

### F-15 Label crop gate, OCR checks, and local comparison methods

- **Claim:** The workbench has 21 optional `lab-compare-*` pipelines. They compare the bottle ranking with a label-crop quality gate, Tesseract, PaddleOCR, SuperPoint + LightGlue, SuperGlue, LoFTR, DINOv2, DINOv3, LPIPS, DISTS, and SigLIP2 label retrieval. On 2,565 current `my` cases, the label gate gives a positive R@1 of 84.29%. The bottle control gives 82.56%. Both give 93 negative false matches at rank 1. A shared dictionary of 36 grapes and 11 sugar classes normalizes the OCR text.
- **Status:** Research-only.
- **Entry point:** [workbench/pipeline/label_gate.py](workbench/pipeline/label_gate.py), [workbench/pipeline/local_comparison.py](workbench/pipeline/local_comparison.py), [workbench/pipeline/wine_terms.py](workbench/pipeline/wine_terms.py), [workbench/docs/testing/label-gate.md](workbench/docs/testing/label-gate.md), [workbench/docs/testing/local-comparison.md](workbench/docs/testing/local-comparison.md)
- **Proof:** `workbench/tests/test_label_gate.py::test_surrounding_glass_fails_with_the_same_detector_confidence`, `workbench/tests/test_local_comparison.py::test_all_missing_or_failed_values_keep_bottle_order`, `workbench/tests/test_wine_terms.py::test_owner_examples_and_visual_lookalikes`; [workbench/ChangeLog.md](workbench/ChangeLog.md) 2026-10-08.
- **Verify:** Read [workbench/docs/testing/local-comparison.md](workbench/docs/testing/local-comparison.md).
- **Limits:** The cohort contains earlier debugging cases. The gate thresholds are not calibrated. The evidence is in the lab `internal/` directory and is not in Git. The matcher part of selective OCR is not in this repository (see "Known gaps").

### F-16 Alternative VLM re-rank and vintage choice

- **Claim:** Optional presets replace the Qwen re-rank VLM with Laya-V (image) or with PaddleOCR text that Laya reads. The lab test set `official-test-2026-10-01` has 95 scored photos. The Qwen preset gives Top-1 90/95 (94.74%). Laya-V gives 86/95 (90.53%), and PaddleOCR + Laya gives 85/95 (89.47%). All three give Top-5 95/95. A rule after the VLM selects the exact printed vintage in a triggered cluster. Without an exact vintage in the window, it selects the undated variant.
- **Status:** Research-only.
- **Entry point:** [workbench/pipeline/laya_v.py](workbench/pipeline/laya_v.py), [workbench/pipeline/laya_ocr.py](workbench/pipeline/laya_ocr.py), [workbench/pipeline/vintage_matching.py](workbench/pipeline/vintage_matching.py), [workbench/docs/laya-v-rerank.md](workbench/docs/laya-v-rerank.md), [workbench/docs/testing/vintage-matching.md](workbench/docs/testing/vintage-matching.md)
- **Proof:** `workbench/tests/test_laya_v.py::test_invalid_or_partial_responses_are_rejected`, `workbench/tests/test_vintage_matching.py::test_exact_vintage_has_priority_over_the_undated_variant`.
- **Verify:** Read [workbench/docs/laya-v-rerank.md](workbench/docs/laya-v-rerank.md).
- **Limits:** The run directories are not in Git. [matcher/rerank.py](matcher/rerank.py) does not have the vintage rule. Only three live requests checked the vintage rule.

### F-17 Bottle orientation and z-rotation tests

- **Claim:** An optional query step turns the bottle mask upright before the embedding. On 256 positive `my` photos, Top-1 changes from 206 (80.47%) to 203 (79.30%). Two scripts test a bottle that turns about its vertical axis. Turned copies of the catalogue image raise the mean cosine by 0.011 to 0.029. They add 0 to 4 rank-1 photos of 33.
- **Status:** Research-only.
- **Entry point:** [workbench/pipeline/bottle_orientation.py](workbench/pipeline/bottle_orientation.py), [workbench/scripts/zrotation_similarity.py](workbench/scripts/zrotation_similarity.py), [workbench/scripts/zrotation_reconstruction.py](workbench/scripts/zrotation_reconstruction.py)
- **Proof:** `workbench/tests/test_bottle_orientation.py::test_all_72_camera_rotations_become_portrait_with_neck_at_top`; [workbench/docs/reports/zrotation-similarity-2026-10-01.md](workbench/docs/reports/zrotation-similarity-2026-10-01.md), [workbench/docs/reports/zrotation-reconstruction-2026-10-01.md](workbench/docs/reports/zrotation-reconstruction-2026-10-01.md).
- **Verify:** Read the section "Findings" of each report.
- **Limits:** The z-rotation scripts need `tools/bottle_rotation/`, which is not in this repository. The z-rotation tests use one wine and one photo series.

### F-18 DINOv3 + ArcFace projection

- **Claim:** A trainer learns a 512-dimension ArcFace projection on frozen DINOv3 ViT-L/16 vectors. A source-disjoint catalogue validation gives R@1 43.34% against 32.25% for the base DINOv3. R@5 is 80.20% against 59.90%.
- **Status:** Research-only.
- **Entry point:** [workbench/pipeline/train_arcface.py](workbench/pipeline/train_arcface.py), [workbench/pipeline/arcface.py](workbench/pipeline/arcface.py), [workbench/docs/arcface.md](workbench/docs/arcface.md)
- **Proof:** `workbench/tests/test_arcface.py::test_no_source_disjoint_validation_fails`, `workbench/tests/test_arcface.py::test_recall_uses_unique_wines_and_same_view_gallery`.
- **Verify:** Read the validation table in [workbench/docs/arcface.md](workbench/docs/arcface.md).
- **Limits:** These are checkpoint-selection results. No test on real photos was run. The checkpoint is not in Git.

### F-19 Competitor pipeline ablation

- **Claim:** Eleven runs compare competitor-style actions on 77 rows: 50 positive and 27 verified no-match photos. The reject action keeps the positive Top-1 at 86.0%, rejects 8 of 27 no-match photos, and raises the exact decision accuracy from 55.8% to 66.2%.
- **Status:** Research-only.
- **Entry point:** [workbench/pipeline/competitor_steps.py](workbench/pipeline/competitor_steps.py), [workbench/scripts/benchmark_competitor_experiments.py](workbench/scripts/benchmark_competitor_experiments.py)
- **Proof:** [workbench/docs/reports/2026-09-30_competitor-pipeline-ablation.md](workbench/docs/reports/2026-09-30_competitor-pipeline-ablation.md); `workbench/tests/test_competitor_followup.py::test_unusable_acceptance_does_not_inflate_recall`.
- **Verify:** Read the section "Result" of the report.
- **Limits:** The benchmark script has a recorded lab defect: it gives `CascadeMatcher` to `Run` ([workbench/ChangeLog.md](workbench/ChangeLog.md) 2026-10-20).

### F-112 Retrieval-only algorithm research reference

- **Claim:** A committed research reference defines custom attention-pooling weights, query geometry, label retrieval, synthetic bottle-axis views, crop margins, patch budgets, wine-score aggregation, and bottle–label fusion without re-ranking. It records 39 pooling profiles, 42 fusion policies, and 53 exact result recipes. The source campaign covers 353,188 unique retrieval configurations on each frozen testset, `my` and `my-failed-2`. On `my-failed-2`, the standard `siglip2-p512-rot5-seg` baseline has R@1 294/668 (44.01%). The best all-budget R@1 is 450/668 (67.37%), and the best p512 R@1 is 442/668 (66.17%). These are different configurations; their other recall values are listed separately in the reference.
- **Status:** Research-only. The document is committed. The results do not describe the default matcher or the Android Base encoder.
- **Entry point:** [RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md](RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md).
- **Proof:** The reference contains the fixed model revision, frozen testset hashes, formulas, complete parameter grids, raw recall counts, baseline deltas, per-family results, all-budget leaderboards, p512 leaderboards, exact recipe JSON, and source audit hashes. Sections 11–14 keep each configuration's metrics together. Section 15 keeps the incomplete RTX4090 replay separate from GX10.
- **Verify:** Read Sections 4–8 for the algorithms and grids. Read Sections 11–14 for the results and exact recipes. Recompute each recall and percentage-point delta from the printed hit counts and denominators.
- **Limits:** Both testsets were used for development selection and share 619 images. This is not independent validation or an official jury score. The report uses SigLIP2 SO400M NaFlex, not the Android Base model. The imported file contains local paths to the external lab workspace. The raw metric databases, frozen images, model weights, and campaign scripts are not committed with this reference, so this repository alone cannot rerun the campaign or independently verify every prediction.

## Criterion 2: post-search features (20/100)

### F-20 Shelf mode

- **Claim:** The Web UI sends one shelf photo to `/v1/group/match`. It draws a mask and a numbered hotspot for each bottle. A tap on a bottle opens its ready result without a second recognition request. Shelf mode has its own page `/shelf`.
- **Status:** Deployed ([webui/ChangeLog.md](webui/ChangeLog.md) 2026-09-29: 93 matched bottles; [webui/ResearchLog.md](webui/ResearchLog.md): HTTP 200 in 2,598 ms). The repository configuration turns shelf mode off by default ([README.md](README.md) section «Ограничения»).
- **Entry point:** [webui/app/pages/shelf.vue](webui/app/pages/shelf.vue), [webui/app/components/ShelfScanner.vue](webui/app/components/ShelfScanner.vue), [webui/server/routes/v1/group/match.post.ts](webui/server/routes/v1/group/match.post.ts), [matcher/group.py](matcher/group.py), [matcher/docs/group-match.md](matcher/docs/group-match.md)
- **Proof:** `webui/tests/shelf-state.test.ts` ("matches the group once and opens ready bottle results without another request"); `matcher/tests/test_group.py::test_group_endpoint_returns_masks_coordinates_and_wine_cards`; `matcher/tests/test_match.py::test_group_matching_rejects_an_ambiguous_two_view_result`.
- **Verify:** Read [webui/docs/shelf-mode.md](webui/docs/shelf-mode.md).
- **Limits:** Shelf mode needs SAM3. The repository has no shelf accuracy benchmark.

### F-21 Taste passport

- **Claim:** «Паспорт вкуса» shows six taste meters (1 to 5), aroma families, and one international style analogue. Values from the wine card come first. Grape-level aggregates from the public Wine Reviews dataset fill the gaps, and the UI labels them as estimates.
- **Status:** Deployed ([webui/ChangeLog.md](webui/ChangeLog.md) 2026-09-29). The result block has the label «О ВИНЕ И ПРОИЗВОДИТЕЛЕ». The dialogs of the taste passport, the dishes, and the label have the label «ДЕМОНСТРАЦИЯ ВОЗМОЖНОСТИ».
- **Entry point:** [webui/app/components/WineExperiences.vue](webui/app/components/WineExperiences.vue), [webui/shared/taste.ts](webui/shared/taste.ts), [webui/shared/data/wine-style-priors.json](webui/shared/data/wine-style-priors.json), [webui/scripts/build-wine-style-priors.py](webui/scripts/build-wine-style-priors.py)
- **Proof:** `webui/tests/experiences.test.ts` ("uses dataset aggregates only as a labeled fallback"); `webui/tests/taste-priors.test.ts` ("stores bounded aggregates without reviews or critic scores"); [webui/shared/data/WINE_STYLE_PRIORS_LICENSE.md](webui/shared/data/WINE_STYLE_PRIORS_LICENSE.md).
- **Verify:** Read [webui/docs/result-experiences.md](webui/docs/result-experiences.md).
- **Limits:** The profile is an estimate, not a tasting. The dataset covers 18 grapes.

### F-22 Regional dishes

- **Claim:** «Подобрать блюда» selects three dishes from three regional cuisines with deterministic rules on the data of the matched wine. Each dish shows its source: the wine card or the wine style.
- **Status:** Deployed ([webui/ChangeLog.md](webui/ChangeLog.md) 2026-09-29).
- **Entry point:** [webui/app/components/WineExperiences.vue](webui/app/components/WineExperiences.vue), [webui/shared/taste.ts](webui/shared/taste.ts)
- **Proof:** `webui/tests/experiences.test.ts` ("selects three distinct regional cuisines").
- **Verify:** Read [webui/docs/result-experiences.md](webui/docs/result-experiences.md).

### F-23 Exact wine card from the vino-svoe.ru API

- **Claim:** For a slug outside the local records, the server loads the exact card from `api.vino-svoe.ru/v1/wines/<slug>` and validates it. The card image is the static file `/img/wines/1600/<slug>.webp` (F-108), not the image of the source response. If the request fails, the result keeps the catalogue link.
- **Status:** Implemented.
- **Entry point:** [webui/server/api/wines/[slug].get.ts](webui/server/api/wines/[slug].get.ts), [webui/server/utils/wine-metadata.ts](webui/server/utils/wine-metadata.ts)
- **Proof:** `webui/tests/wine-metadata.test.ts` ("loads one exact slug from the official JSON API", "uses the static wine image whatever image the source response names").
- **Verify:** Read [webui/server/utils/wine-metadata.ts](webui/server/utils/wine-metadata.ts).

### F-24 Producer product-line map

- **Claim:** The result card has the action «Путеводитель по линейке». It opens an interactive product-line map of the producer. The maps cover 25 producers and 1,203 products with tiers, groups, and bottle images. The map selects the matched wine and marks it «ВАШЕ ВИНО». It has zoom, a group selector, and a control that returns to the matched wine. A product with a catalogue card links to vino-svoe.ru. A product without a card stays selectable without a link. The page `/lineup/<producer>` shows each map in the page space with `noindex`. The page `/lineup` lists all maps.
- **Status:** Deployed in web UI release `772a396e` on 2026-10-19 at 18:20:46 UTC. The live index lists all 25 producer maps, including the six-map expansion.
- **Entry point:** [webui/shared/product-line-map.ts](webui/shared/product-line-map.ts), [webui/shared/product-line-core.ts](webui/shared/product-line-core.ts), [webui/shared/data/product-line-maps/](webui/shared/data/product-line-maps/), [webui/app/components/ProductLineMap.vue](webui/app/components/ProductLineMap.vue), [webui/app/components/WineExperiences.vue](webui/app/components/WineExperiences.vue), [webui/app/pages/lineup/index.vue](webui/app/pages/lineup/index.vue)
- **Proof:** `webui/tests/product-line-map.test.ts` ("resolves the exact scanner result and verified legacy aliases to one product", "keeps gray products selectable as full records without a portal URL"); `webui/tests/product-line-registry.test.ts` ("registers every producer JSON and rejects cross-producer ambiguity", "has a bottle image and a measured frame for every current map product").
- **Verify:** `cd webui && npx vitest run tests/product-line-map.test.ts tests/product-line-registry.test.ts`
- **Limits:** The maps cover 1,138 of 2,103 saved catalogue cards (54.1132%). One Abrau-Durso card remains excluded until exact identification. Read [the current coverage report](webui/docs/validation/catalog-lineup-coverage.md). Other producers have no map. The browser checks `npm run test:line-map` and `npm run test:producer-maps` need a portal origin and Playwright.

### F-25 Feedback with alternatives in the bots

- **Claim:** A result has «✅ Совпало» and «❌ Не совпало» buttons. A negative answer shows ranks 2 to 4 and «Ничего из этого». The bot stores only the first answer of the user who sent the photo.
- **Status:** Deployed for Telegram. Implemented for MAX.
- **Entry point:** [telegram-bot/src/chto_za_vino_bot/app.py](telegram-bot/src/chto_za_vino_bot/app.py)
- **Proof:** `telegram-bot/tests/test_feedback.py::test_negative_feedback_shows_three_alternatives`, `telegram-bot/tests/test_feedback.py::test_result_feedback_rejects_another_user`.
- **Verify:** Read [telegram-bot/tests/test_feedback.py](telegram-bot/tests/test_feedback.py).
- **Limits:** Album results have no feedback buttons.

### F-26 Recognition history on the phone

- **Claim:** The Android app keeps a local history of recognitions with previews and links to the wine pages on vino-svoe.ru.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/HistoryStore.kt](android/app/src/main/java/com/alolalab/chtozavino/HistoryStore.kt)
- **Proof:** [android/SMOKE_TESTS.md](android/SMOKE_TESTS.md) (a history row survives a restart); [android/docs/screenshots/android-0.1.4/raw/06_history_dark.png](android/docs/screenshots/android-0.1.4/raw/06_history_dark.png).
- **Verify:** Open the screenshot.

### F-27 Dinner Lens food-to-wine API

- **Claim:** `dinner-lens/` is a separate FastAPI service, version 0.7.0, for issue #28. `POST /v1/recommendations` takes a dish name or a `node_id`. `POST /v1/recognize-and-recommend` takes a dish photo. `POST /v1/recommendations/more` takes a signed cursor. The `/v1/` routes need a bearer token. The same admission filters apply to each wine: catalogue status, colour, sweetness, wine kind, alcohol limit, and user constraints. A missing required fact excludes the wine. Editorial choices come first. Then the service ranks the other eligible wines by the cosine similarity of `qwen3.7-text-embedding` vectors. The cursor expires after one hour and rejects a changed context. A local `qwen3.5-9b-nvfp4` on GX10 recognizes the photo. `qwen3.8-flash` in QwenCloud is the fallback after a provider failure or an invalid answer. The model only recognizes the dish. It does not select wines. The service accepts JPEG, PNG, HEIC, HEIF, and WebP photos.
- **Status:** Implemented. [dinner-lens/README.md](dinner-lens/README.md) states that the GX10 deployment uses the local-first configuration. [webui/SMOKE_TESTS.md](webui/SMOKE_TESTS.md) (section «Wine for a dish») records checks of the real GX10 service through a local portal on 2026-10-19. No file records the deployed version.
- **Entry point:** [dinner-lens/src/dinner_lens/api.py](dinner-lens/src/dinner_lens/api.py), [dinner-lens/src/dinner_lens/engine.py](dinner-lens/src/dinner_lens/engine.py), [dinner-lens/src/dinner_lens/provider.py](dinner-lens/src/dinner_lens/provider.py), [dinner-lens/src/dinner_lens/embeddings.py](dinner-lens/src/dinner_lens/embeddings.py), [dinner-lens/config.yaml](dinner-lens/config.yaml)
- **Proof:** `dinner-lens/tests/test_pipeline.py::test_curated_first_then_real_embedding_continuation`, `dinner-lens/tests/test_pipeline.py::test_inactive_and_discovery_conflicts_fail_admission`, `dinner-lens/tests/test_pipeline.py::test_cursor_tampering_is_rejected`, `dinner-lens/tests/test_pipeline.py::test_photo_hypothesis_is_not_a_recipe_confirmation`; `dinner-lens/tests/test_provider_chain.py::test_local_success_does_not_call_cloud_or_send_cloud_key`, `dinner-lens/tests/test_provider_chain.py::test_provider_failures_use_cloud_with_identical_pixels_and_instructions`; `dinner-lens/tests/test_image_formats.py::test_heic_and_webp_decode_to_metadata_free_jpeg`.
- **Verify:** Read the section «API» in [dinner-lens/README.md](dinner-lens/README.md).
- **Limits:** Only the 49 reviewed wines have a confirmed wine kind. The admission filters exclude the other Active wines. The embedding index is not in Git. The tests need `data/index/` and `data/index.v4/`. The index build makes paid QwenCloud calls. [dinner-lens/config.yaml](dinner-lens/config.yaml) has the cloud fallback on. The bots do not call the service. [README.md](README.md) and [dinner-lens/README.md](dinner-lens/README.md) still state that the Web UI is not connected. F-28 connects it.

### F-28 Wine for a dish in the Web UI

- **Claim:** The mode «Вино к блюду» is at `/dish`. The user drops or selects a dish photo (JPEG, HEIC, PNG, or WebP, up to 10 MiB) or types a dish name. The browser decodes HEIC locally and sends an upright JPEG without the source EXIF data. A searchable picker shows the 320 Dinner Lens labels as a tree with at most three levels. Two icon groups set the heat and the sauce. The page requests wines again after recognition, after a dish choice, and after each heat or sauce change. Each card shows the wine image, the source facts, a reason, and a link to vino-svoe.ru. «Показать ещё» loads the next page. Three server routes `/api/dinner/*` call Dinner Lens with a server-only bearer token.
- **Status:** Implemented. The deployed Web UI releases `e2e36bfa` and `772a396e` ([webui/ChangeLog.md](webui/ChangeLog.md) 2026-10-19) contain the `/dish` code. No file records a live check of `/dish`.
- **Entry point:** [webui/app/pages/dish.vue](webui/app/pages/dish.vue), [webui/app/components/DinnerScanner.vue](webui/app/components/DinnerScanner.vue), [webui/app/components/DinnerDishPicker.vue](webui/app/components/DinnerDishPicker.vue), [webui/app/composables/useDinnerAutoRecommendations.ts](webui/app/composables/useDinnerAutoRecommendations.ts), [webui/server/utils/dinner.ts](webui/server/utils/dinner.ts), [webui/docs/dinner-lens.md](webui/docs/dinner-lens.md)
- **Proof:** `webui/tests/dinner.test.ts` ("injects bearer auth on the server and forbids redirects", "projects the result without provider/internal metadata"); `webui/tests/dinner-state.test.ts` ("appends real continuation pages with the original opaque cursor", "does not turn an unavailable service into a mock success"); `webui/tests/dinner-auto.test.ts` ("aborts a superseded request and ignores its late response and notification"); `webui/tests/dinner-picker.test.ts` ("keeps every source ID and label reachable in at most three visual levels"); `webui/tests/dish-image.test.ts` ("accepts the real rotated macOS HEIC fixture with no MIME or extension").
- **Verify:** `cd webui && npx vitest run tests/dinner.test.ts tests/dinner-state.test.ts tests/dinner-auto.test.ts tests/dinner-picker.test.ts tests/dish-image.test.ts`
- **Limits:** The mode needs a running Dinner Lens service. Without the private settings, the routes return HTTP 503. The page sends no colour, sweetness, or wine-kind constraints. The browser suites `npm run test:dinner` and `npm run test:dinner-uploads` need Playwright and a running portal. No check with a physical phone camera is recorded.

### F-29 Dinner Lens reference dataset

- **Claim:** `pairing-dataset.v4.json` has 320 nodes: 200 dishes, 104 intermediate classes, and 16 fallback classes. It has 68 pairing profiles and 1,231 editorial links to 49 reviewed wines from 12 producers. The validation report records that all 320 nodes pass with continuation to the last page (1,696 pages). Versions v1 to v3 stay in Git.
- **Status:** Implemented.
- **Entry point:** [dinner-lens/data/pairing-dataset.v4.json](dinner-lens/data/pairing-dataset.v4.json), [dinner-lens/scripts/build_dataset_v4.py](dinner-lens/scripts/build_dataset_v4.py), [dinner-lens/scripts/validate_dataset_v4.py](dinner-lens/scripts/validate_dataset_v4.py)
- **Proof:** [dinner-lens/data/pairing-dataset.v4.validation.json](dinner-lens/data/pairing-dataset.v4.validation.json); `dinner-lens/tests/test_expansion.py::test_original_nodes_and_embedding_inputs_preserved`; `dinner-lens/tests/test_compositional_guards.py::test_strong_acid_requires_positive_source_evidence_on_every_page`.
- **Verify:** `python3 -c "import json;d=json.load(open('dinner-lens/data/pairing-dataset.v4.validation.json'));r=d['results'];print(d['passed'],len(r),sum(x['passed'] for x in r),d['pages'])"` prints `True 320 320 1696`.
- **Limits:** The links and the style families are editorial judgments. No taste panel checked them. The repository has no photo recognition accuracy result and no blind-audit score. The benchmark ground truth and the audit directory are not in Git.

## Criterion 3: architecture and reproducibility (15/100)

### F-30 Component layout

- **Claim:** Each top-level directory owns one function. Most components have their own README, ChangeLog, SMOKE_TESTS, and tests.
- **Status:** Implemented.
- **Entry point:** [ARCHITECTURE.md](ARCHITECTURE.md), [SETUP.md](SETUP.md), [COMMANDS.md](COMMANDS.md)
- **Proof:** The table below.
- **Verify:** Read [ARCHITECTURE.md](ARCHITECTURE.md).

| Directory | Function |
|---|---|
| [matcher/](matcher/) | FastAPI recognition API and the embedding bundle |
| [matcher-inspector/](matcher-inspector/) | Read-only viewer of archived matcher requests and bundles |
| [webui/](webui/) | Nuxt web portal and PWA |
| [telegram-bot/](telegram-bot/) | Telegram bot |
| [max-bot/](max-bot/) | MAX messenger bot |
| [im-core/](im-core/) | Shared core of the two bots |
| [mcp/](mcp/) | Read-only MCP server of the wine catalogue |
| [account/](account/) | Account service of «Винный дневник»: login, messenger links, application tokens |
| [dinner-lens/](dinner-lens/) | Food-to-wine API (wine for a dish) |
| [android/](android/) | Offline Android application |
| [ios/](ios/) | Offline iPhone application (SwiftUI, Core ML) |
| [bootstrap/](bootstrap/) | Local model services and their gateway |
| [proxies/](proxies/) | Model proxy for several inference hosts (lab tool) |
| [workbench/](workbench/) | Catalogue, test sets, embeddings, experiments, and bundle builds |
| [eval/](eval/) | Organizers' evaluation harness |
| [docs/](docs/) | Task specification, runbooks, plans, and audits |

### F-31 Shared bot core

- **Claim:** `im-core/` holds the shared modules of the two bots: queue, moderation, quality checks, matcher client, result cards, artifacts, and the HTTP API. A script copies three modules into `max-bot/`, and a test fails when the copies drift.
- **Status:** Implemented.
- **Entry point:** [im-core/src/chto_za_vino_core/](im-core/src/chto_za_vino_core/), [max-bot/scripts/sync_shared.py](max-bot/scripts/sync_shared.py)
- **Proof:** `max-bot/tests/test_shared_modules.py::test_shared_file_matches_the_telegram_file`; [im-core/ChangeLog.md](im-core/ChangeLog.md).
- **Verify:** `cd max-bot && python scripts/sync_shared.py --check`
- **Limits:** The platform-specific `app.py` and `storage.py` files are separate in each bot.

### F-32 Hash-verified matcher bundle

- **Claim:** The matcher bundle in Git has a manifest with a SHA-256 and a byte size for each payload. The matcher rejects a changed bundle at load. The workbench builds and validates the bundle atomically.
- **Status:** Implemented.
- **Entry point:** [matcher/bundle.py](matcher/bundle.py), [workbench/pipeline/matcher_bundle.py](workbench/pipeline/matcher_bundle.py), [workbench/scripts/build_matcher_bundle.py](workbench/scripts/build_matcher_bundle.py), [workbench/docs/testing/matcher-bundle.md](workbench/docs/testing/matcher-bundle.md)
- **Proof:** `matcher/tests/test_siglip2.py::test_a_changed_or_unsupported_bundle_is_rejected`; `matcher/tests/test_match.py::test_a_changed_wines_file_is_rejected`; `workbench/tests/test_matcher_bundle.py::test_validator_rejects_a_modified_vector_file`.
- **Verify:** Read [matcher/data/gx10-siglip2-so400m-patch16-naflex-p512/manifest.json](matcher/data/gx10-siglip2-so400m-patch16-naflex-p512/manifest.json).

### F-33 Reproducible matcher build and CI

- **Claim:** The matcher installs hash-locked dependencies on a digest-pinned Docker base. The GitHub workflow runs the matcher tests and fails when any test is skipped.
- **Status:** Implemented.
- **Entry point:** [matcher/Dockerfile](matcher/Dockerfile), [matcher/tests/run_ci.sh](matcher/tests/run_ci.sh), [.github/workflows/matcher-tests.yml](.github/workflows/matcher-tests.yml)
- **Proof:** The same files.
- **Verify:** Read [matcher/tests/run_ci.sh](matcher/tests/run_ci.sh).
- **Limits:** The workflow uses a self-hosted runner. Model weights (about 20 GiB) are not in Git. [bootstrap/artifacts/model-bundles/manifest.json](bootstrap/artifacts/model-bundles/manifest.json) lists them with SHA-256 values. The test `matcher/tests/test_mlflow_integration.py::test_real_store_export_retry_and_artifact_hashes` runs only with `MLFLOW_TEST_INTEGRATION=1`. The workflow does not set this variable, so the test is skipped and `run_ci.sh` fails. The last matcher workflow run on `main` (commit `ddcf2c52`) failed with `discovered=282 run=282 skipped=1`.

### F-34 Local model services

- **Claim:** `bootstrap/` runs one native FastAPI process for each model (QR scanner, SAM3, ShieldGemma 2, SigLIP2) behind one gateway. The gateway `/health` returns 503 when a service is down. One command checks the HTTP contracts of all services.
- **Status:** Implemented.
- **Entry point:** [bootstrap/launcher.py](bootstrap/launcher.py), [bootstrap/gateway.py](bootstrap/gateway.py), [bootstrap/scripts/check_compatibility.py](bootstrap/scripts/check_compatibility.py), [bootstrap/docs/decisions/001-native-model-services.md](bootstrap/docs/decisions/001-native-model-services.md)
- **Proof:** [bootstrap/tests/test_gateway.py](bootstrap/tests/test_gateway.py), [bootstrap/tests/test_compatibility.py](bootstrap/tests/test_compatibility.py); [bootstrap/VERIFICATION.md](bootstrap/VERIFICATION.md).
- **Verify:** Read [bootstrap/VERIFICATION.md](bootstrap/VERIFICATION.md).

### F-35 Checksummed offline model bundles

- **Claim:** The installer checks the SHA-256 of each model archive and rejects symbolic links and parent paths in the archives.
- **Status:** Implemented.
- **Entry point:** [bootstrap/scripts/install_model_bundles.py](bootstrap/scripts/install_model_bundles.py), [bootstrap/artifacts/model-bundles/manifest.json](bootstrap/artifacts/model-bundles/manifest.json)
- **Proof:** `bootstrap/tests/test_bundles.py::test_rejects_parent_path`, `bootstrap/tests/test_bundles.py::test_rejects_symbolic_link`.
- **Verify:** Read the manifest.

### F-36 Lab database in Git

- **Claim:** The lab SQLite database uses numbered schema migrations. A text export in Git restores the same database.
- **Status:** Implemented.
- **Entry point:** [workbench/pipeline/db_export.py](workbench/pipeline/db_export.py), [workbench/pipeline/labdb.py](workbench/pipeline/labdb.py), [workbench/db-export/](workbench/db-export/)
- **Proof:** `workbench/tests/test_db_export.py::test_restore_gives_the_same_database`.
- **Verify:** `git log --stat -- workbench/db-export`
- **Limits:** The export in Git is from 2026-09-29: schema 32, 22 tables, 35,368 rows, 2,123 catalogue wines. The code has schema migrations up to `036`. The lab snapshot of 2026-10-18 (2,358 wines, 936 new images) is not in this repository. Of that commit, only the cluster file `clusters.json` is in Git.

### F-37 Content-addressed embedding index

- **Claim:** Each index item has an `embedding_hash` of its source, view, model, options, steps, and derivative. The index build can resume.
- **Status:** Implemented.
- **Entry point:** [workbench/pipeline/build_embeddings.py](workbench/pipeline/build_embeddings.py), [workbench/pipeline/embeddings.py](workbench/pipeline/embeddings.py)
- **Proof:** `workbench/tests/test_embeddings.py::test_default_options_give_the_same_hash`.
- **Verify:** Read [workbench/tests/test_embeddings.py](workbench/tests/test_embeddings.py).

### F-38 Request archive and Matcher Inspector

- **Claim:** The matcher archives each request image and a `request.json` with a decision trace. Matcher Inspector shows the archive and the installed bundles with read-only mounts.
- **Status:** Implemented.
- **Entry point:** [matcher/audit.py](matcher/audit.py), [matcher-inspector/app.py](matcher-inspector/app.py)
- **Proof:** `matcher/tests/test_official_harness.py::test_request_archive_saves_image_headers_ip_and_duration`; `matcher-inspector/tests/test_app.py::test_lists_and_renders_one_request`.
- **Verify:** Read [matcher-inspector/README.md](matcher-inspector/README.md).

### F-39 Bot packaging and offline demo

- **Claim:** The bot images use a pinned base digest, run as a non-root user, and have a `/readyz` health check. An offline host demo runs the full bot pipeline without private services.
- **Status:** Deployed for Telegram ([telegram-bot/SMOKE_TESTS.md](telegram-bot/SMOKE_TESTS.md)).
- **Entry point:** [telegram-bot/Dockerfile](telegram-bot/Dockerfile), [telegram-bot/compose.host-demo.yaml](telegram-bot/compose.host-demo.yaml), [im-core/src/chto_za_vino_core/host_demo.py](im-core/src/chto_za_vino_core/host_demo.py)
- **Proof:** `im-core/tests/test_host_demo.py::test_host_demo_runs_the_pipeline_without_private_services`.
- **Verify:** `cd telegram-bot && uv run chto-za-vino-host-demo`

### F-40 LAN recognition API in the bot

- **Claim:** `POST /api/v1/recognize` runs inside the bot process and uses the same queue and pipeline as chat users. It needs a bearer token of at least 32 characters and a network allowlist.
- **Status:** Deployed for Telegram.
- **Entry point:** [im-core/src/chto_za_vino_core/http_api.py](im-core/src/chto_za_vino_core/http_api.py)
- **Proof:** `telegram-bot/tests/test_http_api.py::test_http_submission_uses_work_queue_and_returns_full_result`.
- **Verify:** Read [telegram-bot/tests/test_http_api.py](telegram-bot/tests/test_http_api.py).

### F-41 Bot admin UI

- **Claim:** A separate admin UI shows statistics, users, and requests with SAM3 masks and crops. It can reset limits, retry a request, and delete a request with CSRF protection. A quarantined request shows only a server-made blurred preview.
- **Status:** Deployed for Telegram (base UI). Implemented for request deletion.
- **Entry point:** [telegram-bot/src/chto_za_vino_bot/admin_web.py](telegram-bot/src/chto_za_vino_bot/admin_web.py), [im-core/src/chto_za_vino_core/pipeline_artifacts.py](im-core/src/chto_za_vino_core/pipeline_artifacts.py)
- **Proof:** `telegram-bot/tests/test_admin_web.py::test_admin_serves_only_censored_derivative_for_quarantined_request`, `telegram-bot/tests/test_admin_web.py::test_admin_deletes_a_finished_request_with_its_files`.
- **Verify:** Read [telegram-bot/tests/test_admin_web.py](telegram-bot/tests/test_admin_web.py).

### F-42 Bot data storage and retention

- **Claim:** SQLite in WAL mode stores requests, candidates, step timings, artifacts, and feedback. Production deletes data after 30 days. A command deletes the data of one user.
- **Status:** Deployed for Telegram.
- **Entry point:** [telegram-bot/src/chto_za_vino_bot/storage.py](telegram-bot/src/chto_za_vino_bot/storage.py), [telegram-bot/src/chto_za_vino_bot/data_lifecycle.py](telegram-bot/src/chto_za_vino_bot/data_lifecycle.py)
- **Proof:** `telegram-bot/tests/test_data_lifecycle.py::test_retention_deletes_terminal_requests_files_and_inactive_users`.
- **Verify:** Read [telegram-bot/tests/test_data_lifecycle.py](telegram-bot/tests/test_data_lifecycle.py).

### F-43 Durable MAX update inbox

- **Claim:** The MAX bot writes each update to an SQLite inbox before it handles the update. After a crash, it replays the unprocessed updates. The webhook secret check uses a constant-time comparison.
- **Status:** Implemented.
- **Entry point:** [max-bot/src/chto_za_vino_max_bot/delivery.py](max-bot/src/chto_za_vino_max_bot/delivery.py)
- **Proof:** `max-bot/tests/test_delivery.py::test_unprocessed_updates_are_replayed_after_a_restart`.
- **Verify:** Read [max-bot/tests/test_delivery.py](max-bot/tests/test_delivery.py).

### F-44 Android model-pack contract

- **Claim:** The Android model pack has a format version from 1 to 6. The app checks the SHA-256 of each payload, the pipeline ID, and the vector dimension. Format 6 also pins the SHA-256 of the p512 model, its profile, and its position table. The app rejects unsafe ZIP paths before it activates the pack. An update replaces an older pack with the built-in format 6 pack and keeps the history and the settings.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/ModelPack.kt](android/app/src/main/java/com/alolalab/chtozavino/ModelPack.kt), [android/docs/model-pack.md](android/docs/model-pack.md), [android/tools/build_verified_naflex_pack.py](android/tools/build_verified_naflex_pack.py)
- **Proof:** `android/tools/test_build_model_pack.py::test_builds_verified_pack`, `android/tools/test_build_model_pack.py::test_rejects_a_different_siglip_model`, `android/tools/test_build_verified_naflex_pack.py::test_rejects_an_index_from_another_model`, `android/tools/test_build_verified_naflex_pack.py::test_rejects_missing_wine_without_silent_catalogue_loss`; [android/app/src/test/](android/app/src/test/) (`ModelPackContractTest`, `ModelPackUpgradeTest`).
- **Verify:** `cd android && python3 -m unittest tools.test_build_catalog_pack tools.test_build_model_pack tools.test_build_verified_naflex_pack`
- **Limits:** The model pack is not in Git. Gradle stops the build when `app/src/main/assets/default_model_pack.zip` is missing (`verifyBuiltInModelPack` in [android/app/build.gradle.kts](android/app/build.gradle.kts)). The app does not download a model pack after installation ([android/docs/specification.md](android/docs/specification.md)).

### F-45 Matcher-compatible API on the phone

- **Claim:** The debug build of the Android app can run an HTTP server on port 18088 with `/healthz`, `/v1/eval/predict`, `/v1/match`, and `/v1/debug/embedding`. The server is off by default. A debug request can select the accelerator of each model and the `max` or `top2-mean` aggregation. The workbench sends complete test sets to the phone through this server.
- **Status:** Implemented (debug builds only).
- **Entry point:** [android/app/src/debug/java/com/alolalab/chtozavino/DebugHttpServer.kt](android/app/src/debug/java/com/alolalab/chtozavino/DebugHttpServer.kt), [workbench/config.yaml](workbench/config.yaml) (`android-device-*` entries)
- **Proof:** [android/app/src/testDebug/](android/app/src/testDebug/) (`DebugHttpServerTest`: `serverIsDisabledByDefault`, `validatesMatchLimit`, `writesMatcherCompatibleResponses`); `workbench/tests/test_remote_run.py::test_the_project_config_holds_the_android_device_entries`; [android/docs/reports/2026-10-19_pixel8-base-p512-full-my.md](android/docs/reports/2026-10-19_pixel8-base-p512-full-my.md) (3,409 requests, 0 HTTP errors).
- **Verify:** Read [android/README.md](android/README.md), section «Debug device bulk evaluation».
- **Limits:** No unit test covers `/v1/debug/embedding`. The release APK has no HTTP server ([android/docs/releases/2026-10-20-main.md](android/docs/releases/2026-10-20-main.md)).

### F-46 Workbench web UI with an OpenAPI contract

- **Claim:** The workbench has a local web UI for the dataset, embeddings, clusters, test sets, runs, run comparison, recognition, website import, and health. A checked-in OpenAPI 3.1 file describes 136 operations on 118 paths. A test compares the operations of the file with a fixed list of operations in the test.
- **Status:** Implemented.
- **Entry point:** [workbench/pipeline/lab_server.py](workbench/pipeline/lab_server.py), [workbench/docs/lab-openapi.yaml](workbench/docs/lab-openapi.yaml)
- **Proof:** `workbench/tests/test_lab_openapi.py::test_document_has_exact_route_inventory`, `workbench/tests/test_lab_openapi.py::test_operations_have_unique_ids_summaries_and_success_responses`.
- **Verify:** Read [workbench/docs/lab-openapi.yaml](workbench/docs/lab-openapi.yaml).

### F-47 Organizers' harness with checksums

- **Claim:** `eval/` holds the organizers' harness and three sample photos with SHA-256 checksums.
- **Status:** Implemented.
- **Entry point:** [eval/participant_test.sh](eval/participant_test.sh), [eval/README.md](eval/README.md)
- **Proof:** [eval/checksums.sha256](eval/checksums.sha256).
- **Verify:** `cd eval && shasum -a 256 -c checksums.sha256`

### F-48 Read-only catalogue MCP server

- **Claim:** `mcp/` is a local stdio MCP server with five read-only catalogue tools: `get_wine`, `find_wines`, `compare_wines`, `get_producer_line`, and `get_audio`. Each tool has strict input and output schemas. `get_producer_line` reads the 25 producer maps of F-24 through the same module as the Web UI. The server reads the matcher bundle of F-32 and stops when the SHA-256 of `wines.jsonl` differs from the manifest. Discovery uses the 2,093 Active wines of the 2,094 bundle IDs. Each result has the catalogue version and the source hashes. The server has no write, command, SQL, or URL fetch tool. With the optional variable `CHTOZAVINO_ACCOUNT_TOKEN` (an application token of F-103), the server adds two read-only tools: `get_my_profile` and `list_my_wines`. These tools send HTTPS `GET` requests to `/api/app/v1/profile` and `/api/app/v1/wines` with no redirects, a 5 s timeout, and a 256 KiB answer limit. Without the token, the server registers no account tools and makes no network request. A GitHub workflow runs the tests on Node.js 22.19.0 and 26.4.0.
- **Status:** Implemented.
- **Entry point:** [mcp/src/server.mjs](mcp/src/server.mjs), [mcp/src/catalog.mjs](mcp/src/catalog.mjs), [mcp/src/account.mjs](mcp/src/account.mjs), [mcp/README.md](mcp/README.md), [.github/workflows/mcp-tests.yml](.github/workflows/mcp-tests.yml)
- **Proof:** `mcp/tests/protocol.test.mjs` ("real SDK client discovers and calls all tools repeatedly over one stdio connection"); `mcp/tests/catalog.test.mjs` ("uses all matcher IDs and excludes non-Active records from discovery", "every Active ID resolves to its exact map node or to unavailable"); `mcp/tests/account.test.mjs` ("account tools read the diary with the bearer token; notes stay data", "without a token the server has the five catalog tools and the old instructions"); [mcp/ChangeLog.md](mcp/ChangeLog.md).
- **Verify:** `cd mcp && npm ci --ignore-scripts && npm test && npm run demo`
- **Limits:** `get_producer_line` covers only the 25 producers of F-24. Other producers return `unavailable`. `get_audio` returns `unavailable`, because the repository has no approved audio files. The server uses local stdio only. No interactive AI assistant and no Qwen dialogue have been tested with it. `list_my_wines` returns an empty list, and `get_my_profile` returns `null` preferences, until the diary history of issue #48 exists. The account tools were checked on a local stack only ([mcp/ResearchLog.md](mcp/ResearchLog.md)).

### F-49 Experiment tracking and saved-run comparison

- **Claim:** The shared benchmark runner can export each finished run to MLflow. An export failure keeps the local results, and an explicit command repeats the export. The Runs page compares two saved runs case by case with the saved query snapshots and the image SHA-256 values. A changed snapshot blocks the pass/fail comparison until the user selects the unchanged cases. One transaction makes a new test set from the filtered cases. The option "Repeat last failed" of the test-set Run dialog sends only the failed or changed photos to the backend again.
- **Status:** Implemented.
- **Entry point:** [matcher/mlflow_tracking.py](matcher/mlflow_tracking.py), [workbench/pipeline/experiment_tracking.py](workbench/pipeline/experiment_tracking.py), [matcher/docs/mlflow.md](matcher/docs/mlflow.md), [workbench/docs/mlflow.md](workbench/docs/mlflow.md), [workbench/pipeline/run_compare.py](workbench/pipeline/run_compare.py), [workbench/pipeline/testset_from_compare.py](workbench/pipeline/testset_from_compare.py), [workbench/docs/testing/run-comparison.md](workbench/docs/testing/run-comparison.md)
- **Proof:** `workbench/tests/test_mlflow_tracking.py::test_failed_export_keeps_benchmark_results`; `matcher/tests/test_mlflow_tracking.py::test_repeated_export_has_no_duplicate`, `matcher/tests/test_mlflow_tracking.py::test_failed_upload_retries_same_run_without_secret_in_state`; `workbench/tests/test_run_compare.py::test_changed_truth_blocks_comparison_until_explicit_common`; `workbench/tests/test_testset_from_compare.py::test_write_failure_rolls_back_new_set_and_photos`; `workbench/tests/test_benchmark.py::test_a_repeat_asks_the_failed_photos_alone_and_copies_the_others`.
- **Verify:** Read [matcher/docs/mlflow.md](matcher/docs/mlflow.md) and [workbench/docs/testing/run-comparison.md](workbench/docs/testing/run-comparison.md).
- **Limits:** The MLflow client is not in the default dependencies. No MLflow server run is recorded (issue #18). The real-store test is opt-in (F-33). [matcher/docs/mlflow.md](matcher/docs/mlflow.md) names the label-only and label-parts evaluators, which are not in this repository.

## Criterion 4: design (10/100)

### F-50 «Своё Вино» visual style

- **Claim:** The Web UI specification requires Playfair Display headings, burgundy controls, cream surfaces, and the grapevine background of vino-svoe.ru. The CSS defines these colors as tokens.
- **Status:** Deployed.
- **Entry point:** [webui/docs/specification.md](webui/docs/specification.md), [webui/docs/assets.md](webui/docs/assets.md), [webui/app/assets/main.css](webui/app/assets/main.css), [webui/public/reference/playfair-display.woff2](webui/public/reference/playfair-display.woff2)
- **Proof:** Screenshots [webui/public/screenshots/home-wide.jpg](webui/public/screenshots/home-wide.jpg), [webui/public/screenshots/home-narrow.jpg](webui/public/screenshots/home-narrow.jpg), [webui/public/screenshots/hackaton/web-mobile.jpg](webui/public/screenshots/hackaton/web-mobile.jpg).
- **Verify:** Open the screenshots. Live: <https://chtozavino.ru/>.

### F-51 Light and dark theme

- **Claim:** The Web UI follows the system theme. A switch stores only an explicit choice. The theme applies before the first paint and stays the same in all open tabs.
- **Status:** Deployed.
- **Entry point:** [webui/app/components/ThemeSwitcher.vue](webui/app/components/ThemeSwitcher.vue), [webui/shared/theme.ts](webui/shared/theme.ts), [webui/app/assets/main.css](webui/app/assets/main.css)
- **Proof:** [webui/tests/pwa.test.ts](webui/tests/pwa.test.ts) (theme color checks); [android/docs/screenshots/android-0.1.4/raw/06_history_dark.png](android/docs/screenshots/android-0.1.4/raw/06_history_dark.png) (Android dark theme).
- **Verify:** Read the dark tokens in [webui/app/assets/main.css](webui/app/assets/main.css).

### F-52 Accessibility features

- **Claim:** The Web UI has a skip link, a live announcement of the result, focus management for dialogs, an inert background under the age dialog, keyboard bottle buttons, `role="meter"`, `aria-pressed`, and reduced motion support. A wine image that does not load shows a bottle silhouette, and screen readers announce «<название>: нет изображения».
- **Status:** Implemented. Issue #35 (VoiceOver and TalkBack support) is open.
- **Entry point:** [webui/app/components/PhotoScanner.vue](webui/app/components/PhotoScanner.vue), [webui/app/app.vue](webui/app/app.vue), [webui/app/components/WineImage.vue](webui/app/components/WineImage.vue)
- **Proof:** [webui/SMOKE_TESTS.md](webui/SMOKE_TESTS.md) (manual checklist); `webui/tests/seo.test.ts` ("keeps the page server-rendered behind the age overlay"); [webui/scripts/check-dinner-browser.mjs](webui/scripts/check-dinner-browser.mjs) (keyboard activation, `aria-pressed`, 44 px targets, keyboard focus with forced colors); [webui/scripts/check-product-line-map-browser.mjs](webui/scripts/check-product-line-map-browser.mjs) (popup focus, focus return, text contrast).
- **Verify:** `grep -rno 'aria-[a-z]*' webui/app`
- **Limits:** The repository has no automated accessibility audit, for example axe-core. No automated check covers the skip link or the live result announcement on `/`. No VoiceOver or TalkBack run of the Web UI is recorded. The browser checks need Playwright and a portal origin.

### F-53 Bot result card

- **Claim:** The bot result is a photo with a caption (name, producer, color, sugar, grapes) and a vino-svoe.ru link button. The official bottle image is placed on a white 4:5 canvas.
- **Status:** Deployed for Telegram.
- **Entry point:** [im-core/src/chto_za_vino_core/result_card.py](im-core/src/chto_za_vino_core/result_card.py)
- **Proof:** `im-core/tests/test_result_card.py::test_catalog_result_photo_fits_transparent_bottle_on_4_by_5_canvas`.
- **Verify:** Read [im-core/tests/test_result_card.py](im-core/tests/test_result_card.py).

### F-54 Installable PWA

- **Claim:** The portal is an installable PWA with a manifest, regular and maskable icons, and screenshots. The service worker caches pages and never caches `/api` or `/v1` responses.
- **Status:** Deployed ([webui/ResearchLog.md](webui/ResearchLog.md) 2026-09-29).
- **Entry point:** [webui/nuxt.config.ts](webui/nuxt.config.ts)
- **Proof:** [webui/tests/pwa.test.ts](webui/tests/pwa.test.ts); [webui/scripts/check-pwa-browser.mjs](webui/scripts/check-pwa-browser.mjs).
- **Verify:** Read the `pwa` block in [webui/nuxt.config.ts](webui/nuxt.config.ts).

## Criterion 5: service speed (5/100)

### F-60 Latency of the 100 evaluation predictions

- **Claim:** All 100 rows of `predictions.jsonl` have `latency_ms` of 3,000 ms or less. The median is 1,316.5 ms. The maximum is 2,906 ms.
- **Status:** Implemented (artifact of 2026-10-02).
- **Entry point:** [predictions.jsonl](predictions.jsonl)
- **Proof:** The same file.
- **Verify:** `python3 -c "import json,statistics;v=[json.loads(l)['latency_ms'] for l in open('predictions.jsonl')];print(len(v),statistics.median(v),max(v))"`

### F-61 Answer time budget

- **Claim:** With `fast_answer`, the cascade answers at 2.9 s when it has an answer, cancels the remaining model calls, and returns an empty slug at 9.5 s. The clock starts when the request headers arrive.
- **Status:** Implemented. [matcher/config.yaml](matcher/config.yaml) has the settings as a comment, together with `pipeline: cascade-p512-rot5`.
- **Entry point:** [matcher/cascade.py](matcher/cascade.py) (`answer_at_seconds`, `timeout_seconds`), [matcher/cascade_run.py](matcher/cascade_run.py)
- **Proof:** `matcher/tests/test_cascade.py::test_slow_sam3_gives_the_whole_answer_at_answer_at`, `matcher/tests/test_cascade.py::test_a_slow_vlm_is_cut_at_answer_at_and_its_connection_closes`, `matcher/tests/test_cascade.py::test_everything_slow_gives_an_empty_slug_at_the_hard_limit`; `matcher/tests/test_cascade_api.py::test_the_time_budget_counts_from_the_request_headers`; [matcher/ResearchLog.md](matcher/ResearchLog.md) (81 of 81 photos within 3 s).
- **Verify:** Read [matcher/docs/cascade.md](matcher/docs/cascade.md).

### F-62 Default pipeline latency

- **Claim:** The default pipeline answered the three harness photos in 334 to 455 ms.
- **Status:** Implemented.
- **Entry point:** [BENCHMARKS.md](BENCHMARKS.md)
- **Proof:** [BENCHMARKS.md](BENCHMARKS.md), [matcher/ResearchLog.md](matcher/ResearchLog.md).
- **Verify:** Read [BENCHMARKS.md](BENCHMARKS.md).

### F-63 Overload protection

- **Claim:** The matcher limits the upload size, the pixel count, and the upload time. A bounded queue returns 503 with `Retry-After` when it is full, and `/healthz` stays available. The limits are public settings in `matcher.limits` of the YAML configuration. An environment variable cannot change them. A production stress test with 32 concurrent clients recorded no HTTP 500.
- **Status:** Deployed ([matcher/docs/reports/2026-09-29_production-stress-test.md](matcher/docs/reports/2026-09-29_production-stress-test.md)). The YAML form of the limits (`da8c8954`, 2026-10-19) has no recorded deployment.
- **Entry point:** [matcher/protection.py](matcher/protection.py), [matcher/configuration.py](matcher/configuration.py), [matcher/config.yaml](matcher/config.yaml)
- **Proof:** `matcher/tests/test_resilience.py::test_full_queue_returns_503_while_healthz_stays_available`; `matcher/tests/test_configuration.py::test_yaml_controls_http_limits_and_environment_cannot_override_it`, `matcher/tests/test_configuration.py::test_each_limit_rejects_invalid_values`; [matcher/docs/reports/2026-09-29_production-stress-test.md](matcher/docs/reports/2026-09-29_production-stress-test.md).
- **Verify:** Read the stress test report.

### F-64 Hardware benchmark: GX10 and RTX 4090

- **Claim:** A benchmark compares the GX10 (GB10) host and an RTX 4090 host for each model service at concurrency 1, 2, 4, and 8.
- **Status:** Research-only.
- **Entry point:** [bootstrap/scripts/benchmark.py](bootstrap/scripts/benchmark.py), [bootstrap/scripts/run_benchmarks.py](bootstrap/scripts/run_benchmarks.py)
- **Proof:** [bootstrap/docs/benchmarks/2026-09-28-gx10-vs-rtx4090.md](bootstrap/docs/benchmarks/2026-09-28-gx10-vs-rtx4090.md); [bootstrap/tests/test_run_benchmarks.py](bootstrap/tests/test_run_benchmarks.py).
- **Verify:** Read the report tables.

### F-65 Model-call cache in the model proxy

- **Claim:** The model proxy spreads SAM3, Grounding DINO, and SigLIP2 requests over several hosts and caches the answers in SQLite. It merges identical concurrent requests.
- **Status:** Implemented (lab tool).
- **Entry point:** [proxies/model_proxy/app.py](proxies/model_proxy/app.py), [proxies/model_proxy/pool.py](proxies/model_proxy/pool.py)
- **Proof:** [proxies/tests/](proxies/tests/) (`test_concurrent_identical_misses_are_merged`); [proxies/ChangeLog.md](proxies/ChangeLog.md) 2026-09-29.
- **Verify:** Read [proxies/README.md](proxies/README.md).

### F-66 Cascade with a local FP8 VLM on an RTX 4090

- **Claim:** The pipeline `cascade-p512-rot5` with `fast_answer` ran on one RTX 4090 host with a local Qwen3.5-9B VLM. The VLM ran in vLLM 0.30.0 with FP8 quantization at load and MTP-3. On the lab set `official-real-photos` (84 photos, one photo at a time), it gave R@1 93.65% with 0 errors. The latency was p50 1,353 ms, p90 1,929 ms, and max 2,905 ms.
- **Status:** Research-only.
- **Entry point:** [workbench/ResearchLog.md](workbench/ResearchLog.md) (section of 2026-10-01 «Qwen3.5-9B in vLLM 0.30.0 on an RTX 4090»)
- **Proof:** [workbench/ResearchLog.md](workbench/ResearchLog.md); [workbench/ChangeLog.md](workbench/ChangeLog.md) 2026-10-01.
- **Verify:** Read the ResearchLog section.
- **Limits:** The deployment scripts and the input set `eval/official-real-photos/` of this run are not in this repository. The run directory is not in Git. The log does not measure the effect of FP8 on the re-rank answers. The GX10 result of 90.0% used 81 photos, so the two values are not a paired comparison.

## Other features

### F-70 Telegram bot

- **Claim:** `@ChtoZaVinoBot` accepts one photo, an album, or an image file (JPEG, PNG, WebP, HEIC, HEIF). Each photo becomes its own request. HEIC files become JPEG files without EXIF data.
- **Status:** Deployed for photos and albums. Implemented for files and HEIC.
- **Entry point:** [telegram-bot/src/chto_za_vino_bot/app.py](telegram-bot/src/chto_za_vino_bot/app.py), [im-core/src/chto_za_vino_core/image_types.py](im-core/src/chto_za_vino_core/image_types.py)
- **Proof:** `telegram-bot/tests/test_album.py::test_album_photos_create_separate_ordered_jobs`; `telegram-bot/tests/test_image_document.py::test_heic_document_is_recognized_and_stored_as_jpeg`.
- **Verify:** Read [telegram-bot/README.md](telegram-bot/README.md). Live: <https://t.me/ChtoZaVinoBot>.

### F-71 MAX bot

- **Claim:** The MAX messenger bot has the same recognition flow as the Telegram bot and uses `im-core/`.
- **Status:** Implemented.
- **Entry point:** [max-bot/src/chto_za_vino_max_bot/](max-bot/src/chto_za_vino_max_bot/), [max-bot/README.md](max-bot/README.md)
- **Proof:** `max-bot/tests/test_end_to_end.py::test_album_message_gives_one_receipt_and_results_without_feedback`; [max-bot/SMOKE_TESTS.md](max-bot/SMOKE_TESTS.md).
- **Verify:** `cd max-bot && ./scripts/verify.sh`

### F-72 Age confirmation (18+)

- **Claim:** The Web UI and the bots need an 18+ confirmation before they process a photo. A photo sent before the confirmation waits and enters the queue after «Мне есть 18 лет». For a returning visitor, a head script reads the saved confirmation and hides the server-rendered warning before the first paint. The legal pages open without the gate (F-104).
- **Status:** Deployed (Web UI and Telegram gate). Implemented (held photo replay, MAX, hiding the warning before the first paint).
- **Entry point:** [webui/app/components/AgeGate.vue](webui/app/components/AgeGate.vue), [webui/shared/age.ts](webui/shared/age.ts), [telegram-bot/docs/decisions/004-soft-age-gate.md](telegram-bot/docs/decisions/004-soft-age-gate.md)
- **Proof:** `webui/tests/age.test.ts` ("fails closed when storage is unavailable", "marks a saved confirmation before the page paints"); `webui/tests/seo.test.ts` ("hides the age overlay before paint for a saved confirmation"); `telegram-bot/tests/test_age_gate.py::test_photo_before_the_age_confirmation_is_queued_after_the_adult_choice`.
- **Verify:** Read [telegram-bot/tests/test_age_gate.py](telegram-bot/tests/test_age_gate.py).

### F-73 Image moderation before storage

- **Claim:** ShieldGemma 2 checks each image before the bot writes it to disk. An invalid moderation answer blocks the image. An unsafe image goes to an owner-only quarantine and never reaches the matcher. Production does not start with moderation off.
- **Status:** Deployed for Telegram.
- **Entry point:** [im-core/src/chto_za_vino_core/moderation.py](im-core/src/chto_za_vino_core/moderation.py), [im-core/src/chto_za_vino_core/files.py](im-core/src/chto_za_vino_core/files.py)
- **Proof:** `im-core/tests/test_moderation.py::test_invalid_response_fails_closed`; `telegram-bot/tests/test_config.py::test_production_rejects_disabled_moderation`.
- **Verify:** Read [im-core/tests/test_moderation.py](im-core/tests/test_moderation.py).

### F-74 Work queue with restart recovery

- **Claim:** A FIFO work queue sends a receipt with the queue position and the estimated wait. After a restart, the bot restores the received, queued, and processing requests from SQLite.
- **Status:** Deployed for Telegram.
- **Entry point:** [im-core/src/chto_za_vino_core/work_queue.py](im-core/src/chto_za_vino_core/work_queue.py)
- **Proof:** `im-core/tests/test_work_queue.py::test_queue_processes_jobs_in_fifo_order`, `im-core/tests/test_work_queue.py::test_queue_estimates_wait_by_worker_wave`; `telegram-bot/tests/test_storage.py::test_pending_requests_are_restored_in_received_order`.
- **Verify:** Read [im-core/tests/test_work_queue.py](im-core/tests/test_work_queue.py).

### F-75 Rate limits

- **Claim:** Each user can send 50 photos in a rolling hour. The limit is stored in SQLite. The MAX client limits outgoing calls to 30 per second in total and 2 per second for each chat.
- **Status:** Deployed for Telegram. Implemented for MAX.
- **Entry point:** [telegram-bot/src/chto_za_vino_bot/storage.py](telegram-bot/src/chto_za_vino_bot/storage.py), [max-bot/src/chto_za_vino_max_bot/max_api.py](max-bot/src/chto_za_vino_max_bot/max_api.py)
- **Proof:** `telegram-bot/tests/test_storage.py::test_rate_limit_is_rolling_and_persistent`; `max-bot/tests/test_max_api.py::test_send_repeats_only_rate_limited_requests`.
- **Verify:** Read [telegram-bot/tests/test_storage.py](telegram-bot/tests/test_storage.py).

### F-76 Image quality checks

- **Claim:** Blur, glare, and SAM3 bottle and label checks run before recognition. The bot stores the results as metadata for the admin UI.
- **Status:** Deployed for Telegram.
- **Entry point:** [im-core/src/chto_za_vino_core/quality.py](im-core/src/chto_za_vino_core/quality.py)
- **Proof:** `im-core/tests/test_quality.py::test_blur_and_glare_are_reported`; `telegram-bot/tests/test_processor_quality.py::test_quality_service_failure_continues_to_recognition`.
- **Verify:** Read [im-core/tests/test_quality.py](im-core/tests/test_quality.py).
- **Limits:** The checks do not change the answer.

### F-77 WebMCP tools

- **Claim:** The portal registers nine WebMCP tools through `document.modelContext`: scanner tools, a scan mode tool, and five shelf tools.
- **Status:** Implemented.
- **Entry point:** [webui/app/composables/useScannerTools.ts](webui/app/composables/useScannerTools.ts), [webui/app/components/ScannerPage.vue](webui/app/components/ScannerPage.vue) (`set_wine_scan_mode`), [webui/app/composables/useShelfTools.ts](webui/app/composables/useShelfTools.ts)
- **Proof:** [webui/docs/verification-2026-09-15.md](webui/docs/verification-2026-09-15.md) (manual check).
- **Verify:** Read [webui/app/composables/useShelfTools.ts](webui/app/composables/useShelfTools.ts).
- **Limits:** WebMCP is an experimental browser API.

### F-78 Search metadata

- **Claim:** The portal has a canonical URL, Open Graph and Twitter tags, WebSite and WebApplication JSON-LD, `robots.txt`, and `sitemap.xml`.
- **Status:** Deployed.
- **Entry point:** [webui/nuxt.config.ts](webui/nuxt.config.ts), [webui/public/robots.txt](webui/public/robots.txt), [webui/public/sitemap.xml](webui/public/sitemap.xml)
- **Proof:** [webui/tests/seo.test.ts](webui/tests/seo.test.ts).
- **Verify:** Read [webui/public/sitemap.xml](webui/public/sitemap.xml).
- **Limits:** `sitemap.xml` on `main` lists 14 URLs. Five of them have no recorded release: `/terms`, `/privacy`, `/contacts`, `/sitemap`, and `/iphone`.

### F-79 Project pages

- **Claim:** The portal has the pages `/ideas` (feature ideas with their status), `/android` (APK download), `/hackaton`, and `/presentation`. `/ideas` has four implemented scenarios, including «Dinner Lens — вино к блюду» with a link to `/dish` (F-28). It links to `/crocodile` (F-106) and `/game` (F-107). Other portal pages are `/lineup` (F-24), `/iphone` (F-98), the legal pages (F-104), and `/sitemap` (F-105).
- **Status:** Deployed ([webui/ChangeLog.md](webui/ChangeLog.md) 2026-09-29). The `/ideas` changes of 2026-10-19 are in release `e2e36bfa`. Its live check opens `/ideas` and follows the link to `/crocodile` ([webui/docs/validation/crocodile-landing.md](webui/docs/validation/crocodile-landing.md)).
- **Entry point:** [webui/app/pages/ideas.vue](webui/app/pages/ideas.vue), [webui/app/pages/android.vue](webui/app/pages/android.vue), [webui/app/pages/hackaton.vue](webui/app/pages/hackaton.vue), [webui/app/pages/presentation.vue](webui/app/pages/presentation.vue)
- **Proof:** [webui/tests/android-landing.test.ts](webui/tests/android-landing.test.ts); [webui/scripts/check-presentation-browser.mjs](webui/scripts/check-presentation-browser.mjs).
- **Verify:** Read [webui/docs/ideas-landing.md](webui/docs/ideas-landing.md).
- **Limits:** On `main`, `/android` offers APK 0.2.0 (F-85). The deployment of 2026-09-29 offered APK 0.1.4. No file records a deployment of the 0.2.0 page. The demo card «Место в линейке» on `/ideas` and [webui/docs/ideas-landing.md](webui/docs/ideas-landing.md) still describe only the Abrau-Durso map.

### F-86 HEIF (HEIC) photos

- **Claim:** `POST /v1/eval/predict`, `POST /v1/match`, and `POST /v1/group/match` accept HEIF (HEIC) photos. iPhone cameras save HEIC by default. The matcher decodes the primary image of a HEIF file. A damaged HEIF file gives HTTP 422 on the single-image endpoints and HTTP 400 on the group endpoint, not HTTP 500. The Web UI accepts HEIC photos. For an unreadable HEIC photo, it shows «Не удалось прочитать HEIC. Сохраните фото как JPEG.»
- **Status:** Implemented. [README.md](README.md) states that the production matcher decodes HEIF since 2026-10-18.
- **Entry point:** [matcher/photo.py](matcher/photo.py), [matcher/group.py](matcher/group.py), [matcher/protection.py](matcher/protection.py), [webui/app/composables/useWineScanner.ts](webui/app/composables/useWineScanner.ts)
- **Proof:** `matcher/tests/test_match.py::test_a_heif_photo_is_matched_on_both_single_image_endpoints`, `matcher/tests/test_match.py::test_a_damaged_heif_answers_422_on_both_single_image_endpoints`, `matcher/tests/test_group.py::test_a_damaged_heif_photo_is_400_before_the_sam3_request`, `matcher/tests/test_resilience.py::test_the_libheif_crash_file_does_not_stop_the_service`; `webui/tests/prediction.test.ts` ("accepts a HEIC signature and names the file by its detected type"), `webui/tests/scanner.test.ts` ("explains an unreadable %s photo").
- **Verify:** Read [matcher/ResearchLog.md](matcher/ResearchLog.md) (crash test of two HEIF decoders on 2,106 damaged HEIC files).
- **Limits:** The production Telegram bot accepts photos and albums, but not HEIC files (F-70). The Android app accepts HEIC and HEIF files in the gallery (F-90). Dinner Lens accepts HEIC and HEIF (F-27, F-28). A cut tiled HEIF file decodes without an error ([matcher/docs/KNOWN_ISSUES.md](matcher/docs/KNOWN_ISSUES.md), item 4).

### Android application

#### F-80 Optional bottle segmentation on the device

- **Claim:** The setting `Без сегментации / DIS / YOLO` selects how the app prepares the photo. The default is `Без сегментации`. In this mode, the app encodes the full original photo. DIS (LiteRT) and YOLO26n-seg (F-88) are optional modes. In these modes, the app cuts the object out of the photo and places it on a white square.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/AcceleratorSettings.kt](android/app/src/main/java/com/alolalab/chtozavino/AcceleratorSettings.kt) (`SegmenterMode`), [android/app/src/main/java/com/alolalab/chtozavino/ImageRecognition.kt](android/app/src/main/java/com/alolalab/chtozavino/ImageRecognition.kt) (`DisSegmenter`, `YoloBottleSegmenter`, `ForegroundImageProcessor`)
- **Proof:** [android/app/src/test/](android/app/src/test/) (`AcceleratorSettingsTest.unknownSegmenterUsesFullImage`, `AcceleratorSettingsTest.noSegmentationPreferenceIsPreserved`, `DisMaskTest`); [android/docs/reports/2026-10-19_base-p512-default.md](android/docs/reports/2026-10-19_base-p512-default.md) (the Pixel 8 health report gives the segmenter `NONE`); [android/docs/screenshots/android-0.1.4/raw/05_processing_pipeline_dark.png](android/docs/screenshots/android-0.1.4/raw/05_processing_pipeline_dark.png) (DIS mode, version 0.1.4).
- **Verify:** Read [android/README.md](android/README.md), section «Functions».
- **Limits:** The reference vectors are package cuts in all modes. When DIS runs on the GPU, the main app runs SigLIP2 on the CPU. A separate experimental app with DIS and SigLIP2 both on the GPU gave Top-1 72.29% on `my` ([android/docs/reports/2026-10-19_pixel8-p512-dis-dual-gpu-my.md](android/docs/reports/2026-10-19_pixel8-p512-dis-dual-gpu-my.md)).

#### F-81 On-device SigLIP2 NaFlex vectors

- **Claim:** The app makes a 768-dimension SigLIP2 Base NaFlex p512 vector (`google/siglip2-base-patch16-naflex`) on the phone. It keeps the native aspect ratio of the photo. It uses the pinned `siglip2-naflex-litert` library, version 0.2.0. On a Pixel 8, 14 images gave a minimum cosine of 0.9999999999289232 between the device vectors and the desktop vectors of the same graph.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/VerifiedNaFlexEncoder.kt](android/app/src/main/java/com/alolalab/chtozavino/VerifiedNaFlexEncoder.kt), [android/app/build.gradle.kts](android/app/build.gradle.kts), [android/app/libs/README.md](android/app/libs/README.md)
- **Proof:** [android/docs/reports/2026-10-19_base-p512-default.md](android/docs/reports/2026-10-19_base-p512-default.md) (section «Vector agreement»); [android/app/src/test/](android/app/src/test/) (`ModelPackContractTest`, `NaFlexPreprocessorTest`).
- **Verify:** Read the section «Vector agreement» of the report.
- **Limits:** The server default uses SigLIP2 so400m p512 (F-03), not Base. The phone uses its own index of 2,093 Base p512 vectors. The CPU/GPU check used one image. The check of 32 samples with a minimum cosine of 0.99999851 in [android/VERIFICATION_RESULTS.md](android/VERIFICATION_RESULTS.md) applies to the earlier fixed Base/16-224 encoder.

#### F-82 Offline catalogue search

- **Claim:** The app searches the catalogue on the phone by cosine similarity and keeps the best image score for each wine. The built-in pack has 2,093 wines and one p512 vector for each wine. The release manifest has no `INTERNET` permission.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/CatalogueIndex.kt](android/app/src/main/java/com/alolalab/chtozavino/CatalogueIndex.kt), [android/app/src/main/AndroidManifest.xml](android/app/src/main/AndroidManifest.xml)
- **Proof:** [android/app/src/test/](android/app/src/test/) (`CatalogueIndexTest.searchUsesMaximumImageCosinePerWine`).
- **Verify:** `grep -rn INTERNET android/app/src`
- **Limits:** The debug manifest adds `INTERNET` for the debug HTTP server (F-45).

#### F-83 Barcode and QR input

- **Claim:** The app reads EAN-8, EAN-13, and QR codes with Google Code Scanner and finds the wine in the local code table.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/MainActivity.kt](android/app/src/main/java/com/alolalab/chtozavino/MainActivity.kt), [android/app/src/main/java/com/alolalab/chtozavino/CatalogueIndex.kt](android/app/src/main/java/com/alolalab/chtozavino/CatalogueIndex.kt)
- **Proof:** [android/app/src/test/](android/app/src/test/) (`CatalogueIndexTest.ean13MatchesGtin14`); [android/docs/screenshots/android-0.1.4/raw/08_barcode_result_dark.png](android/docs/screenshots/android-0.1.4/raw/08_barcode_result_dark.png).
- **Verify:** Open the screenshot.

#### F-84 Accelerator selection

- **Claim:** For each model (DIS and SigLIP2), the user can select Auto, GPU, or CPU. At first start, the app compares the GPU and CPU vectors of the p512 encoder. It selects the CPU when the cosine is below 0.99999 or the maximum error is above 0.001. In Auto mode, the app falls back to the CPU when the GPU gives an invalid output.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/AcceleratorSettings.kt](android/app/src/main/java/com/alolalab/chtozavino/AcceleratorSettings.kt), [android/app/src/main/java/com/alolalab/chtozavino/NaFlexAcceleratorAgreement.kt](android/app/src/main/java/com/alolalab/chtozavino/NaFlexAcceleratorAgreement.kt)
- **Proof:** [android/app/src/test/](android/app/src/test/) (`AcceleratorSettingsTest.autoUsesDetectedAcceleratorsAndAllowsSafeFallback`, `NaFlexAcceleratorAgreementTest`); [android/docs/reports/2026-10-19_base-p512-default.md](android/docs/reports/2026-10-19_base-p512-default.md) (Pixel 8: automatic GPU, 30 requests, median server time 514.8 ms).
- **Verify:** Read [android/README.md](android/README.md), section «Functions».
- **Limits:** When DIS runs on the GPU, the main app runs SigLIP2 on the CPU. The timings in [android/ChangeLog.md](android/ChangeLog.md) 2026-09-29 apply to the earlier Base/224 pipeline.

#### F-85 Android releases 0.1.4 and 0.2.0

- **Claim:** The Android app 0.1.4 (Android 9 and later, arm64) is a GitHub pre-release with tag `android-v0.1.4`. `main` builds version 0.2.0 (version code 6) with the application ID `com.alolalab.chtozavino`. The 0.2.0 release APK has the same test/debug signing key as 0.1.4. The `/android` page on `main` points to this APK.
- **Status:** 0.1.4: Implemented. 0.2.0: Implemented. No tag, GitHub release, or website deployment of 0.2.0 is recorded.
- **Entry point:** [android/app/build.gradle.kts](android/app/build.gradle.kts), [webui/shared/android.ts](webui/shared/android.ts), [android/docs/releases/2026-10-20-main.md](android/docs/releases/2026-10-20-main.md)
- **Proof:** [android/SMOKE_TESTS.md](android/SMOKE_TESTS.md) 2026-09-29 (APK SHA-256 values); [android/docs/releases/2026-10-20-rebuild.md](android/docs/releases/2026-10-20-rebuild.md) (section «Same-key signing follow-up»); [android/app/src/test/](android/app/src/test/) (`ApplicationIdentityTest.mainApplicationUsesCanonicalId`); `webui/tests/android-landing.test.ts` ("keeps one versioned release contract for the page and download route").
- **Verify:** `git tag --list 'android-*'`
- **Limits:** The 0.2.0 key is a test/debug key, not a production key. The new application ID installs as a separate app, and the history does not migrate. No record shows an installation of the new-ID APK on a phone. The device measurements used the old ID with the same pack. The APK contains YOLO26n-seg weights with AGPL-3.0 metadata. [android/README.md](android/README.md) requires a license approval before publication.

#### F-87 Multi-shot recognition

- **Claim:** The user can select one to three photos for one recognition. The app processes the photos in sequence and keeps the maximum score of each wine. It continues when one photo fails. It stops before the next photo when Top-1 is at least 0.93 and the margin over Top-2 is at least 0.08.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/MultiShotRecognition.kt](android/app/src/main/java/com/alolalab/chtozavino/MultiShotRecognition.kt), [android/app/src/main/java/com/alolalab/chtozavino/AppViewModel.kt](android/app/src/main/java/com/alolalab/chtozavino/AppViewModel.kt) (`MAX_SELECTED_IMAGES`)
- **Proof:** [android/app/src/test/](android/app/src/test/) (`MultiShotRecognitionTest`: `keepsMaximumScoreForEachWine`, `stopsForAHighTopScoreWithALargeMargin`, `continuesWhenTheScoreMarginIsTooSmall`); [android/VERIFICATION_RESULTS.md](android/VERIFICATION_RESULTS.md) (Pixel 8: Top-1 0.9425, margin 0.0919, one of three photos processed).
- **Verify:** Read [android/README.md](android/README.md), the multi-shot paragraph.
- **Limits:** The device check used a 0.1.4 debug build with DIS and Base/224. No file records a multi-shot check with the p512 default. No benchmark measures the accuracy effect.

#### F-88 YOLO bottle segmentation

- **Claim:** The YOLO mode runs the Ultralytics `yolo26n-seg` w8a32 LiteRT model at 640 by 640 pixels on the CPU. It keeps only COCO class 39 (`bottle`) and selects the largest central bottle mask. Model-pack format 3 and later formats contain this model.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/YoloBottleMask.kt](android/app/src/main/java/com/alolalab/chtozavino/YoloBottleMask.kt), [android/app/src/main/java/com/alolalab/chtozavino/ImageRecognition.kt](android/app/src/main/java/com/alolalab/chtozavino/ImageRecognition.kt) (`YoloBottleSegmenter`)
- **Proof:** [android/app/src/test/](android/app/src/test/) (`YoloBottleMaskTest`: `selectsLargestCentralBottleAndReadsCoefficients`, `rejectsCandidateWhenBottleIsNotBestClass`, `buildsMaskAndRemovesLetterboxArea`); [android/README.md](android/README.md), section «Pixel 8 segmentation comparison».
- **Verify:** Read that README section.
- **Limits:** In a test of 100 images on a Pixel 8 with Base/224 on the CPU, YOLO found a bottle in 70 images and accepted 23 results. DIS accepted 38. The YOLO median was 1,234 ms, and the DIS median was 2,024.5 ms. The result files are not in this repository. No YOLO measurement with p512 exists. The model metadata declares AGPL-3.0.

#### F-89 Retrieval benchmark of the default pipeline on a Pixel 8

- **Claim:** The debug app on a Pixel 8 answered all 3,409 queries of the internal set `my` through `/v1/match?k=20`. It used Base NaFlex p512 on the full photo on the GPU. Top-1 was 2,052 of 2,970 positive assignments (69.09%). Top-5 was 87.10%, and Top-10 was 90.03%. The median client time was 924 ms, and the P95 was 1,479 ms. 3,406 requests finished within 3 s. The baseline of Base/224 with DIS gave Top-1 33.27% at a median of 1,699 ms.
- **Status:** Implemented (measurement of 2026-10-19).
- **Entry point:** [android/docs/reports/2026-10-19_pixel8-base-p512-full-my.md](android/docs/reports/2026-10-19_pixel8-base-p512-full-my.md)
- **Proof:** [android/docs/reports/2026-10-19_pixel8-base-p512-full-my.json](android/docs/reports/2026-10-19_pixel8-base-p512-full-my.json) (`metrics.latency_ms`, `paired_top1_changes`, `runtime.maximum_thermal_status`).
- **Verify:** Read the section «Results» of the report.
- **Limits:** The forbidden wine is Top-1 in 73 of 430 negative assignments (baseline: 42). All 9 no-match queries return a wine. The thermal status reached `SEVERE`. 170 positive assignments have no accepted wine in the pack. Barcode decoding was off. The run directory is not in Git. The app ID in this run was `chtozavino.alolalab.com`.

#### F-90 HEIC and HEIF gallery input on Android

- **Claim:** The gallery picker accepts JPEG, PNG, WebP, HEIC, and HEIF files. The history preview is a local JPEG.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/MainActivity.kt](android/app/src/main/java/com/alolalab/chtozavino/MainActivity.kt) (`GALLERY_MIME_TYPES`)
- **Proof:** [android/app/src/test/](android/app/src/test/) (`GalleryMimeTypesTest.galleryAcceptsEverySupportedImageType`); [android/SMOKE_TESTS.md](android/SMOKE_TESTS.md) «Verification on 2026-10-19» (Pixel 8: a HEIC result, the preview after a cold restart, TalkBack labels).
- **Verify:** `grep -n '"image/' android/app/src/main/java/com/alolalab/chtozavino/MainActivity.kt`
- **Limits:** The device check ran before the p512 default. [android/docs/reports/2026-10-19_base-p512-default.md](android/docs/reports/2026-10-19_base-p512-default.md) states that HEIC input was not tested again after that change.

#### F-91 Offline retrieval benchmark on the phone

- **Claim:** [android/tools/offline_benchmark/](android/tools/offline_benchmark/) contains a separate app (`com.alolalab.chtozavino.offlinebench`) and host tools. The app runs ten mobile versions of desktop retrieval recipes on the phone. It uses YOLO11n-seg bottle and label masks on the CPU, SigLIP2 so400m NaFlex p512 (1,152 dimensions) on the GPU, and FP32 search over 2,274 wines. The host client opens a new HTTP socket over ADB for each request. It repeats a failed transfer at most two times. It continues an interrupted run from audited saved predictions.
- **Status:** Partial.
- **Entry point:** [android/tools/offline_benchmark/README.md](android/tools/offline_benchmark/README.md), [android/docs/plans/06_android-retrieval-variants.md](android/docs/plans/06_android-retrieval-variants.md)
- **Proof:** `android/tools/offline_benchmark/test_usb_http.py::test_binary_prefix_is_rejected_and_retried_on_fresh_socket`, `android/tools/offline_benchmark/test_usb_http.py::test_retries_are_bounded`, `android/tools/offline_benchmark/test_resume_run.py::test_copy_is_exact_and_source_is_unchanged`, `android/tools/offline_benchmark/test_audit_device_run.py::test_partial_does_not_publish_full_accuracy`; [android/docs/reports/2026-10-19_pixel8-my-failed2-offline-variants.md](android/docs/reports/2026-10-19_pixel8-my-failed2-offline-variants.md) (pilot: 300 requests with HTTP 200, medians of 4.09 s to 13.74 s).
- **Verify:** `python3 -m unittest discover -s android/tools/offline_benchmark -p 'test_*.py' -v`
- **Limits:** The complete result for the 668 `my-failed-2` assignments is pending. Two full runs stopped after 29 and 44 records. The pilot reached the thermal status `SEVERE` and 2,173.36 MiB peak PSS. The main app does not use these recipes. On the same assignments, the main app gave Top-1 41.02% and Top-5 77.84% ([android/docs/reports/2026-10-19_pixel8-my-failed2-offline-control.md](android/docs/reports/2026-10-19_pixel8-my-failed2-offline-control.md)).

#### F-92 Smoke test on a second phone

- **Claim:** The debug app ran on a Realme RMX3890 with Android 14. Each endpoint received 10 `my` queries with zero request errors. `/v1/match?k=20` gave R@1 0.5 and R@5 0.7. Logcat contained no `FATAL EXCEPTION` or `SIGABRT`.
- **Status:** Implemented (check of 2026-10-17).
- **Entry point:** [android/VERIFICATION_RESULTS.md](android/VERIFICATION_RESULTS.md) (section «Realme RMX3890 debug endpoint verification»)
- **Proof:** The same file; [android/ChangeLog.md](android/ChangeLog.md) 2026-10-17.
- **Verify:** Read that section.
- **Limits:** The test used only 10 queries. The build was a debug build with DIS, Base/224, and a pack of 2,178 wines, not the current default. The median was 4,217 ms, and no request met the 3,000 ms objective.

#### F-93 Experimental NaFlex split runtimes

- **Claim:** Model-pack format 4 (so400m, 1,152 dimensions) and format 5 (Base, 768 dimensions) split the NaFlex encoder into a LiteRT backbone and a LiteRT pooling model. The built-in pack does not use them.
- **Status:** Implemented (experimental).
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/ImageRecognition.kt](android/app/src/main/java/com/alolalab/chtozavino/ImageRecognition.kt) (`NaFlexSplitEncoder`), [android/tools/export_siglip2_naflex_split.py](android/tools/export_siglip2_naflex_split.py)
- **Proof:** [android/app/src/test/](android/app/src/test/) (`ModelPackContractTest`); `android/tools/test_export_siglip2_naflex_split.py::test_split_matches_original_vision_model` (needs torch and transformers).
- **Verify:** Read [android/docs/naflex-implementations.md](android/docs/naflex-implementations.md).
- **Limits:** The app turns off the GPU for the split runtime. One so400m p512 image took about 256 s on the Pixel 8 CPU. The Base pilot rejected all four variants ([android/docs/reports/2026-10-19_pixel8-siglip2-base-pilot/report.md](android/docs/reports/2026-10-19_pixel8-siglip2-base-pilot/report.md)).

### iPhone application

#### F-94 Offline iPhone application

- **Claim:** [ios/](ios/) contains a native SwiftUI app for iOS 17.2 and later with a Russian UI. It has the user functions of the Android app: 18+ confirmation, camera and photo-library input, code scan with manual input, ranked local search, 50 history rows, and settings. Recognition and catalogue search run on the iPhone with Core ML. The app needs a network only to open a result page.
- **Status:** Implemented. Only simulator checks are recorded.
- **Entry point:** [ios/README.md](ios/README.md), [ios/docs/specification.md](ios/docs/specification.md), [ios/ChtoZaVino/RecognitionEngine.swift](ios/ChtoZaVino/RecognitionEngine.swift)
- **Proof:** [ios/ChtoZaVinoTests/CoreTests.swift](ios/ChtoZaVinoTests/CoreTests.swift) (`testGTINNormalizationMatchesAndroid`, `testURLNormalizationRemovesFragmentAndDefaultPort`, `testDebugMatchLimit`); [ios/SMOKE_TESTS.md](ios/SMOKE_TESTS.md) «2026-10-03 result» (production pack with 2,093 wines).
- **Verify:** `grep -rn URLSession ios/ChtoZaVino` gives no output.
- **Limits:** No file records a run on a physical iPhone. No TestFlight or App Store build exists. [ios/project.yml](ios/project.yml) has version 0.1.0 and an empty `DEVELOPMENT_TEAM`. The Core ML models and the resource pack are not in Git. The bundle ID `chtozavino.alolalab.com` differs from the new Android ID.

#### F-95 iPhone segmentation and encoders

- **Claim:** The app offers DIS (the default) or YOLO26n-seg segmentation. It offers three encoders: SigLIP2 Base NaFlex p512 (the default, 768 values), SigLIP2 Base 224 (768 values), and MobileCLIP2-S2 (512 values). Each encoder has its own index of 2,093 wines. The compute modes are `Авто`, `ANE`, and `CPU`.
- **Status:** Implemented.
- **Entry point:** [ios/ChtoZaVino/Models.swift](ios/ChtoZaVino/Models.swift), [ios/ChtoZaVino/Preferences.swift](ios/ChtoZaVino/Preferences.swift), [ios/ChtoZaVino/YOLOSegmenter.swift](ios/ChtoZaVino/YOLOSegmenter.swift), [ios/docs/model-pack.md](ios/docs/model-pack.md)
- **Proof:** [ios/ChtoZaVinoTests/CoreTests.swift](ios/ChtoZaVinoTests/CoreTests.swift) (`testNaFlexPatchOrderIsPixelThenRGB`, `testYOLOSelectsLargestCentralBottleAndReadsCoefficients`, `testYOLOBuildsMaskAndRemovesLetterbox`); [ios/ResearchLog.md](ios/ResearchLog.md) 2026-10-06 (Core ML p512 cosine 0.99970 against PyTorch; self-match at rank 1 with cosine 0.9083).
- **Verify:** Read [ios/ResearchLog.md](ios/ResearchLog.md).
- **Limits:** The iPhone p512 path uses a square of 352 by 352 pixels (22 by 22 patches). Android keeps the native aspect ratio. No Top-k benchmark exists for the iPhone app. The simulator timings use the CPU: DIS + p512 3,216 ms, YOLO + p512 1,884 ms, search 11 ms. The YOLO license (AGPL-3.0) and the MobileCLIP2 license need confirmation before distribution.

#### F-96 iPhone accessibility

- **Claim:** The app has VoiceOver labels, hints, headings, status announcements, and focus moves. It supports Dynamic Type with vertical layouts, 44-point controls, Reduce Motion, Reduce Transparency, Voice Control, and Switch Control. VoiceOver reports a scanned code in the manual input field.
- **Status:** Implemented.
- **Entry point:** [ios/ChtoZaVino/AccessibilitySupport.swift](ios/ChtoZaVino/AccessibilitySupport.swift), [ios/docs/specification.md](ios/docs/specification.md) (section «Accessibility»)
- **Proof:** [ios/ChtoZaVinoUITests/AccessibilityUITests.swift](ios/ChtoZaVinoUITests/AccessibilityUITests.swift) (`testAgeGateAccessibility`, `testRecognitionScreenAccessibilityAtLargestTextSize`, `testSettingsAccessibility`, `testHistoryAccessibilityAtLargestTextSize`, `testCodeScannerAccessibility`, `testUnavailableCameraAccessibility`); [ios/SMOKE_TESTS.md](ios/SMOKE_TESTS.md) «2026-10-18 accessibility» (12 unit tests and 6 UI tests passed on the iPhone 17 Pro simulator).
- **Verify:** `grep -n performAccessibilityAudit ios/ChtoZaVinoUITests/AccessibilityUITests.swift`
- **Limits:** The recognition test skips the XCTest Dynamic Type audit because of false failures ([ios/ResearchLog.md](ios/ResearchLog.md)). No file records a manual VoiceOver run.

#### F-97 iPhone debug HTTP API

- **Claim:** The debug build has an HTTP server on port 18088 with `/healthz`, `/v1/eval/predict`, and `/v1/match`. `/v1/match` returns stage timings. The release build does not compile the server (`#if DEBUG`).
- **Status:** Implemented (debug builds only).
- **Entry point:** [ios/ChtoZaVino/DebugHTTPServer.swift](ios/ChtoZaVino/DebugHTTPServer.swift)
- **Proof:** [ios/ChtoZaVinoTests/CoreTests.swift](ios/ChtoZaVinoTests/CoreTests.swift) (`testDebugMatchLimit`); [ios/SMOKE_TESTS.md](ios/SMOKE_TESTS.md) «2026-10-06 bottleneck check».
- **Verify:** `grep -n "#if DEBUG" ios/ChtoZaVino/DebugHTTPServer.swift`

#### F-98 iPhone landing page

- **Claim:** The portal page `/iphone` describes the iPhone app with two simulator screenshots. It has no download action. The button «Следить за TestFlight» opens GitHub issue #36. The page states that a speed check on a physical iPhone is still necessary.
- **Status:** Implemented. No deployment is recorded ([webui/docs/iphone-landing.md](webui/docs/iphone-landing.md): «Status: Implemented locally»).
- **Entry point:** [webui/app/pages/iphone.vue](webui/app/pages/iphone.vue)
- **Proof:** `webui/tests/iphone-landing.test.ts` ("publishes verified iPhone capabilities and the release-status link", "provides the verified simulator screenshots as WebP", "publishes metadata, navigation, and cache policy for the iPhone route"); [webui/SMOKE_TESTS.md](webui/SMOKE_TESTS.md) «iPhone application landing page».
- **Verify:** Read [webui/docs/iphone-landing.md](webui/docs/iphone-landing.md).

### «Винный дневник» accounts

#### F-99 Login and sign-up

- **Claim:** `account/` is a LAN-only service for the accounts of «Винный дневник». A person logs in with a 6-digit email code (10 minutes, 5 tries) or with Yandex ID (OAuth 2.0 with PKCE `S256` and `state`). A new identity signs up with a username and two separate consents. A session has no expiry. It ends at logout or at account deletion. Account deletion and unlinking ask for a confirmation on the page, not for a new login. An account keeps at least one login method. The service stores only hashes of bearer secrets. The Web UI page `/account` and the header link «Дневник» use same-site `/api/account/*` routes with httpOnly `__Host-` cookies. The browser never gets the address or the token of the service. The service offers no login through Telegram, Google, or Apple ([account/README.md](account/README.md)).
- **Status:** Implemented. The recorded Web UI releases `e2e36bfa` and `772a396e` contain the account pages. No file records a live login check.
- **Entry point:** [account/src/chto_za_vino_account/api.py](account/src/chto_za_vino_account/api.py), [account/src/chto_za_vino_account/service.py](account/src/chto_za_vino_account/service.py), [account/src/chto_za_vino_account/yandex.py](account/src/chto_za_vino_account/yandex.py), [webui/app/pages/account.vue](webui/app/pages/account.vue), [webui/server/utils/account.ts](webui/server/utils/account.ts), [webui/docs/account.md](webui/docs/account.md)
- **Proof:** `account/tests/test_email.py::test_new_email_signs_up_and_gets_a_session`, `account/tests/test_email.py::test_wrong_codes_lock_the_challenge`, `account/tests/test_email.py::test_session_does_not_expire`; `account/tests/test_yandex.py::test_authorize_url_uses_pkce_and_state`; `account/tests/test_account.py::test_an_old_session_can_delete_the_account`, `account/tests/test_account.py::test_unlink_keeps_one_login_method`; `webui/tests/account.test.ts` ("sets the session cookie after a correct code and keeps the token away from the browser", "lists only email and Yandex ID as login methods", "deletes the account without a re-login and clears the session cookie").
- **Verify:** `cd account && ./scripts/verify.sh`
- **Limits:** The diary data does not exist yet: searches, photos, ratings, and preferences ([account/README.md](account/README.md)). MAX login is off by default (`MAX_LOGIN_ENABLED`). [account/MANUAL_TESTS.md](account/MANUAL_TESTS.md) has no recorded run, including test 8.4 (VoiceOver and TalkBack).

#### F-100 Same-email account join

- **Claim:** A login of an unknown identity joins the one account that has the same email. For Yandex ID, the service uses the `default_email` from Yandex ID. The service compares addresses after trim and lower case. No join occurs when two accounts have the email or when the account already has an identity of this provider. The operator command `chto-za-vino-account merge --keep <username> --remove <username>` joins duplicate accounts.
- **Status:** Implemented.
- **Entry point:** [account/src/chto_za_vino_account/service.py](account/src/chto_za_vino_account/service.py), [account/src/chto_za_vino_account/cli.py](account/src/chto_za_vino_account/cli.py)
- **Proof:** `account/tests/test_email_join.py::test_yandex_login_joins_the_account_with_the_same_email`, `account/tests/test_email_join.py::test_email_login_joins_the_account_of_a_yandex_identity`, `account/tests/test_email_join.py::test_no_join_when_two_accounts_have_the_email`, `account/tests/test_email_join.py::test_the_operator_merge_refuses_a_provider_clash`.
- **Verify:** Read [account/tests/test_email_join.py](account/tests/test_email_join.py).
- **Limits:** The join trusts the address that Yandex ID returns ([account/README.md](account/README.md)).

#### F-101 MAX link through the diary mini app

- **Claim:** `/max` is the account page in MAX mode (issue #50). Inside MAX, the person logs in with an email code and confirms the link. The page sends the signed launch data (`initData`) to the server. The service checks the signature, the age (5 minutes by default, at most 60), the single use of `query_id`, and the signed `ip`. The service reads an `auth_date` above 10^11 as milliseconds. It also accepts the URL fragment form of the launch data and a launch string that is URL-encoded one more time. A refused launch logs its reason without the launch data. Outside MAX, `/max` shows a fixed deep link and its QR code. A host guard limits the mini-app host to the mini-app page, its assets, the legal pages, and the account routes. On that host, the account cookies are `SameSite=None; Partitioned`.
- **Status:** Implemented. [account/ChangeLog.md](account/ChangeLog.md) 2026-10-20 records failed real MAX links (`launch_expired`, then «launch data has no hash»). The fixes `8b661b27`, `5b29fb08`, and `49fba100` have no recorded release.
- **Entry point:** [account/src/chto_za_vino_account/max_launch.py](account/src/chto_za_vino_account/max_launch.py), [webui/app/utils/max-bridge.ts](webui/app/utils/max-bridge.ts), [webui/server/middleware/max-host.ts](webui/server/middleware/max-host.ts), [webui/server/api/account/max/link.post.ts](webui/server/api/account/max/link.post.ts), [docs/plans/05_max-authorization.md](docs/plans/05_max-authorization.md)
- **Proof:** `account/tests/test_max.py::test_signature_check`, `account/tests/test_max.py::test_launch_checks`, `account/tests/test_max.py::test_launch_date_in_milliseconds`, `account/tests/test_max.py::test_launch_forms_of_max_clients`, `account/tests/test_max.py::test_max_login_is_off_by_default`; `webui/tests/account.test.ts` ("sends the launch data with the session and the client address", "serves the QR code of the fixed link only when it is set", "sets and clears the email and session cookies with SameSite=None and Partitioned").
- **Verify:** Read the section "MAX link" in [webui/docs/account.md](webui/docs/account.md).
- **Limits:** The MAX bot does not save searches to the diary ([docs/plans/05_max-authorization.md](docs/plans/05_max-authorization.md)). MAX login stays off.

#### F-102 Telegram link

- **Claim:** «Привязать мессенджер» → «Telegram» on `/account` gives a one-time deep link `https://t.me/<bot>?start=link_<code>` (issue #51). The code lives 10 minutes. An account can make at most 10 codes per hour. The bot links the Telegram user ID only after «Привязать», and only in a private chat. The first Telegram user who claims a code owns it. A new code ends the open code. `/unlink` in the bot and «Отвязать» on the site remove the link. The bot menu shows `/unlink` only when the diary link is on. A Telegram identity never opens a session.
- **Status:** Implemented.
- **Entry point:** [account/src/chto_za_vino_account/service.py](account/src/chto_za_vino_account/service.py), [telegram-bot/src/chto_za_vino_bot/account.py](telegram-bot/src/chto_za_vino_bot/account.py), [telegram-bot/src/chto_za_vino_bot/profile.py](telegram-bot/src/chto_za_vino_bot/profile.py), [webui/server/api/account/links/telegram.post.ts](webui/server/api/account/links/telegram.post.ts)
- **Proof:** `account/tests/test_telegram.py::test_link_telegram_with_confirmation`, `account/tests/test_telegram.py::test_a_code_belongs_to_the_first_claimer`, `account/tests/test_telegram.py::test_a_new_code_replaces_the_open_one`, `account/tests/test_telegram.py::test_bot_unlink`; `telegram-bot/tests/test_account_link.py::test_start_link_asks_for_confirmation`, `telegram-bot/tests/test_account_link.py::test_link_only_in_a_private_chat`; `telegram-bot/tests/test_profile.py::test_menu_shows_unlink_only_with_the_account_link`.
- **Verify:** Read [telegram-bot/tests/test_account_link.py](telegram-bot/tests/test_account_link.py).
- **Limits:** The bot does not save searches to the diary yet. [account/MANUAL_TESTS.md](account/MANUAL_TESTS.md) test 8.3 has no recorded run.

#### F-103 Application tokens for MCP clients

- **Claim:** «Токены приложений» on `/account` creates a read-only token: `cvpat_` and 32 random bytes in base64url (issue #65). The service stores only the SHA-256 hash, and the page shows the token once. A token lives 30, 90, or 365 days. An account can have at most 5 active tokens. `GET /api/app/v1/profile` and `GET /api/app/v1/wines` accept `Authorization: Bearer cvpat_...`. Each refused token gets the same HTTP 401. A token can make 60 requests per minute. Above a limit, the answer is HTTP 429 with `Retry-After`. A token never opens a session and cannot manage tokens. The MCP server uses these tokens (F-48).
- **Status:** Implemented.
- **Entry point:** [account/src/chto_za_vino_account/service.py](account/src/chto_za_vino_account/service.py) (`APP_TOKEN_PATTERN`), [webui/server/api/app/v1/profile.get.ts](webui/server/api/app/v1/profile.get.ts), [webui/server/api/app/v1/wines.get.ts](webui/server/api/app/v1/wines.get.ts), [mcp/src/account.mjs](mcp/src/account.mjs)
- **Proof:** `account/tests/test_app_tokens.py::test_create_shows_the_token_once_and_stores_only_its_hash`, `account/tests/test_app_tokens.py::test_refusals_are_the_same_401`, `account/tests/test_app_tokens.py::test_a_token_is_not_a_session_and_cannot_manage_tokens`, `account/tests/test_app_tokens.py::test_a_sixth_active_token_is_refused`, `account/tests/test_app_tokens.py::test_the_61st_request_in_a_minute_is_limited`; `webui/tests/account.test.ts` ("creates a token with the site origin and returns the secret once", "passes the bearer token on as X-App-Token and keeps no cookie or cache").
- **Verify:** Read [account/README.md](account/README.md).
- **Limits:** The preferences are `null` and the wine list is empty until the diary part of issue #48 exists. Public use of `/api/app/*` needs a change of the reverse proxy. The end-to-end check ran on a local stack only.

### Portal pages and shared assets

#### F-104 Shared legal pages

- **Claim:** `/terms`, `/privacy`, and `/contacts` (issue #37) are one set of pages for all services: the website with «Винный дневник» and «Вино к блюду», both bots, the Android app, and the iPhone app. Each service has a stable fragment: `#site`, `#account`, `#telegram`, `#max`, `#android`, `#ios`. The pages open without the 18+ gate. The footer and `/sitemap.xml` link to the pages. [webui/ResearchLog.md](webui/ResearchLog.md) lists the evidence for each data statement.
- **Status:** Implemented. Not deployed. [ChangeLog.md](ChangeLog.md) 2026-10-19 says: "Do not deploy them before the matcher archive has a 30-day cleanup job." It also says: "Do not deploy them before the Dinner Lens cloud fallback is off."
- **Entry point:** [webui/app/pages/terms.vue](webui/app/pages/terms.vue), [webui/app/pages/privacy.vue](webui/app/pages/privacy.vue), [webui/app/pages/contacts.vue](webui/app/pages/contacts.vue), [webui/app/components/LegalPage.vue](webui/app/components/LegalPage.vue), [webui/app/data/legal.ts](webui/app/data/legal.ts), [webui/docs/legal-pages.md](webui/docs/legal-pages.md)
- **Proof:** `webui/tests/legal-pages.test.ts` ("publishes the three shared paths", "opens the legal pages without the age gate", "keeps a stable fragment for every service in the terms and the policy", "covers «Винный дневник» and the dish photos").
- **Verify:** Read the section "Release conditions" in [webui/docs/legal-pages.md](webui/docs/legal-pages.md).
- **Limits:** A lawyer has not reviewed the texts (issue #45). The pages do not claim Metrika consent, because the consent banner of issue #41 does not exist.

#### F-105 Public HTML site map

- **Claim:** `/sitemap` lists 13 pages in six groups. [webui/app/data/sitemap.ts](webui/app/data/sitemap.ts) holds the list. A test keeps the list equal to [webui/public/sitemap.xml](webui/public/sitemap.xml). The list omits `/hackaton`, `/account`, `/max`, and the `noindex` map pages. The footer has the link «Карта сайта».
- **Status:** Implemented. Not deployed: `429d3ecc` is not in release `772a396e`.
- **Entry point:** [webui/app/pages/sitemap.vue](webui/app/pages/sitemap.vue), [webui/app/data/sitemap.ts](webui/app/data/sitemap.ts)
- **Proof:** `webui/tests/sitemap.test.ts` ("lists the same pages as the XML sitemap", "omits the direct-access and noindex pages", "links only to existing pages", "is linked from the shared footer").
- **Verify:** Read [webui/app/data/sitemap.ts](webui/app/data/sitemap.ts).

#### F-106 Wine Crocodile landing

- **Claim:** `/crocodile` presents «Винный крокодил», a printable card game with 30 illustrated cards. The page shows six sample cards with keyboard-operable flips, color filters with `aria-pressed`, the rules, and a FAQ. Two print files are available: `/crocodile/downloads/cards-a4.pdf` and `/crocodile/downloads/box-a4.pdf`. `/ideas` links to the page.
- **Status:** Deployed ([webui/docs/validation/crocodile-landing.md](webui/docs/validation/crocodile-landing.md), section «Production verification»: release `e2e36bfa` active on 2026-10-19 at 17:05:37 UTC; [webui/ChangeLog.md](webui/ChangeLog.md) 2026-10-19: sixteen live layouts and 23 live HTTP checks). The later copy changes `e39cb46d` and `e422999c` are not in a recorded release.
- **Entry point:** [webui/app/pages/crocodile.vue](webui/app/pages/crocodile.vue), [webui/app/data/crocodile-cards.ts](webui/app/data/crocodile-cards.ts), [webui/public/crocodile/](webui/public/crocodile/), [webui/docs/crocodile-landing.md](webui/docs/crocodile-landing.md)
- **Proof:** [webui/scripts/check-crocodile-browser.mjs](webui/scripts/check-crocodile-browser.mjs) (filters, flips, FAQ, PDF hashes, the link from `/ideas`); [webui/docs/crocodile-media/asset-manifest.json](webui/docs/crocodile-media/asset-manifest.json).
- **Verify:** Read [webui/docs/validation/crocodile-landing.md](webui/docs/validation/crocodile-landing.md).
- **Limits:** No Vitest test covers the page. No test ran on a physical phone.

#### F-107 Wine&Dine Merge landing

- **Claim:** `/game` introduces the Wine&Dine Merge game. Its play links open `https://game.chtozavino.ru/`. The page does not load the game runtime. `/ideas` links to the page.
- **Status:** Implemented. Release `e2e36bfa` contains the page. No file records a live check of `/game`.
- **Entry point:** [webui/app/pages/game.vue](webui/app/pages/game.vue), [webui/docs/game-landing.md](webui/docs/game-landing.md)
- **Proof:** [webui/scripts/check-game-landing-browser.mjs](webui/scripts/check-game-landing-browser.mjs); [webui/SMOKE_TESTS.md](webui/SMOKE_TESTS.md) section "Wine&Dine Merge landing" (local check).
- **Verify:** Read [webui/docs/game-landing.md](webui/docs/game-landing.md).
- **Limits:** The game source is not in this repository. The game is a simplified prototype with no expert review.

#### F-108 Static wine images with a hash-checked release

- **Claim:** `workbench/scripts/build_wine_images.py` builds a release of wine images from the lab database: `1600/<slug>.webp` and `400/<slug>.webp` for each Active wine, `manifest.json` (format `svoe-vino-wine-images`, version 2), and `SHA256SUMS`. Each file comes from the package cut of the `main_patched` image, else of the `main` image. The build trims transparent, white, and black borders. It keeps the alpha channel and does not enlarge an image. `check_wine_images.py` compares a release directory or the published files with a catalogue database and returns a non-zero exit code on a difference. The matcher catalogue reader and the bundle builder give `image_url` = `https://chtozavino.ru/img/wines/1600/<slug>.webp`, or `null` for a wine with no image. The bots load catalogue images over HTTPS only from `chtozavino.ru` and `api.vino-svoe.ru`. `WineImage.vue` shows a bottle silhouette when an image does not load.
- **Status:** Implemented. [docs/plans/06_wine-images.md](docs/plans/06_wine-images.md) and [ChangeLog.md](ChangeLog.md) 2026-10-19 state that the release is not deployed.
- **Entry point:** [workbench/pipeline/wine_images.py](workbench/pipeline/wine_images.py), [workbench/scripts/build_wine_images.py](workbench/scripts/build_wine_images.py), [workbench/scripts/check_wine_images.py](workbench/scripts/check_wine_images.py), [matcher/catalog.py](matcher/catalog.py), [im-core/src/chto_za_vino_core/result_card.py](im-core/src/chto_za_vino_core/result_card.py), [webui/app/components/WineImage.vue](webui/app/components/WineImage.vue), [docs/plans/06_wine-images.md](docs/plans/06_wine-images.md)
- **Proof:** `workbench/tests/test_wine_images.py::test_the_release_holds_the_main_patched_or_main_image_of_each_active_wine`, `workbench/tests/test_wine_images.py::test_the_trim_cuts_borders_and_keeps_dark_and_light_bottles_whole`, `workbench/tests/test_wine_images.py::test_the_check_finds_a_changed_an_extra_and_a_missing_file`; `matcher/tests/test_catalog.py::test_only_a_main_or_main_patched_image_gives_an_image_url`; `im-core/tests/test_result_card.py::test_catalog_image_loader_accepts_the_static_wine_images`; `webui/tests/wine-metadata.test.ts` ("uses the static wine image whatever image the source response names").
- **Verify:** `cd workbench && python3 -m unittest discover -s tests -p 'test_wine_images.py'`
- **Limits:** A real build from the lab database (2,198 Active wines) gave 2,193 images and 5 wines with no image ([workbench/ChangeLog.md](workbench/ChangeLog.md) 2026-10-19). Issue #69 tracks the 5 wines. The release files are not in Git. A build needs the lab database and its image files. The matcher bundle in Git (F-03) is older than this change: its 2,094 cards keep `image_url` on `api.vino-svoe.ru`.

### Workbench catalogue tools

#### F-109 Website import automation and startup sync

- **Claim:** The website import adds valid new wines automatically. Conflicts and possible duplicates wait for a manual decision. A new Main image replaces the old one only when the package and label crops pass three checks: a native resolution gain, the image quality, and an independent VLM identity check. The old image stays as an additional photo. `scripts/sync_website.py`, or an optional startup hook, imports the data, builds the selected embeddings and clusters, and validates a frozen matcher catalogue. Then it publishes the catalogue through an atomic local symbolic link.
- **Status:** Implemented. The startup sync is off by default (`website_sync.on_startup: false` in [workbench/config.yaml](workbench/config.yaml)).
- **Entry point:** [workbench/pipeline/website_sync.py](workbench/pipeline/website_sync.py), [workbench/scripts/sync_website.py](workbench/scripts/sync_website.py), [workbench/pipeline/website_image_review.py](workbench/pipeline/website_image_review.py), [workbench/pipeline/import_website.py](workbench/pipeline/import_website.py), [workbench/docs/testing/website-sync.md](workbench/docs/testing/website-sync.md)
- **Proof:** `workbench/tests/test_website_sync.py::test_stage_failure_prevents_publication_and_preserves_diff`, `workbench/tests/test_website_sync.py::test_no_startup_by_default`; `workbench/tests/test_website_image_review.py::test_an_enlargement_cannot_be_an_automatic_improvement`; `workbench/tests/test_import_website.py::test_control_wine_is_not_missing_or_a_rename_candidate`.
- **Verify:** Read [workbench/docs/testing/website-sync.md](workbench/docs/testing/website-sync.md).
- **Limits:** No live website import is recorded for these features. The sync publishes local data only. It does not deploy or restart a remote matcher.

#### F-110 Catalogue review tools

- **Claim:** The Add wine dialog reads a staged Main image with the VLM, fills empty fields, shows similar wines, and warns about duplicates and vintage conflicts before Save and inside the create transaction. The Dataset page compares the catalogue metadata with printed image evidence: grape, sweetness, colour, vintage, reserve, and barrel. The `wine_vintage` relation links the vintages of one wine, and the cluster build joins each vintage family.
- **Status:** Implemented.
- **Entry point:** [workbench/pipeline/wine_draft.py](workbench/pipeline/wine_draft.py), [workbench/pipeline/attribute_compare.py](workbench/pipeline/attribute_compare.py), [workbench/pipeline/wine_vintages.py](workbench/pipeline/wine_vintages.py), [workbench/docs/testing/wine-draft.md](workbench/docs/testing/wine-draft.md), [workbench/docs/testing/attribute-comparison.md](workbench/docs/testing/attribute-comparison.md), [workbench/docs/testing/wine-vintages.md](workbench/docs/testing/wine-vintages.md)
- **Proof:** `workbench/tests/test_wine_draft.py::test_different_vintage_and_one_missing_vintage`; `workbench/tests/test_attribute_compare.py::test_partial_blend_does_not_establish_conflict`; `workbench/tests/test_wine_vintages.py::test_an_undated_entry_can_link_to_multiple_years`, `workbench/tests/test_wine_vintage_clusters.py::test_a_pair_merges_two_clusters_in_each_view`.
- **Verify:** Read [workbench/docs/testing/wine-draft.md](workbench/docs/testing/wine-draft.md).
- **Limits:** The attribute facts need a VLM service. The database export in Git has no attribute facts (F-36).

#### F-111 Workbench read caches and operator tools

- **Claim:** The workbench persists checked run indexes, cluster summaries, and catalogue snapshots. It defers popup images until a step opens, and it mounts cards near the viewport. Each cache checks its sources and falls back to the original read. Local measurements: repeated cluster requests went from 8.212 s to 0.079 s, and repeated large-run pages from 5.123 s to 0.108 s. The Dataset transfer went from 6,648,486 to 1,227,636 bytes. A switch turns off the automatic label cut of one image. `scripts/restart_lab_server.sh` restarts the lab server with a start check.
- **Status:** Implemented.
- **Entry point:** [workbench/pipeline/run_page_cache.py](workbench/pipeline/run_page_cache.py), [workbench/pipeline/summary_cache.py](workbench/pipeline/summary_cache.py), [workbench/pipeline/cluster_view_cache.py](workbench/pipeline/cluster_view_cache.py), [workbench/pipeline/catalogue_snapshot.py](workbench/pipeline/catalogue_snapshot.py), [workbench/scripts/restart_lab_server.sh](workbench/scripts/restart_lab_server.sh)
- **Proof:** `workbench/tests/test_run_index.py::test_append_and_incomplete_tail_invalidate_the_index`, `workbench/tests/test_catalogue_snapshot.py::test_database_and_wal_commits_invalidate`, `workbench/tests/test_generate_label.py::test_a_turned_off_image_gets_no_sam3_request_and_no_row`; [workbench/ChangeLog.md](workbench/ChangeLog.md) entries of 2026-10-06 and 2026-10-07.
- **Verify:** Read the 2026-10-06 entries of [workbench/ChangeLog.md](workbench/ChangeLog.md).
- **Limits:** All timings are local lab measurements under host load. The evidence files are in the lab `internal/` directory and are not in Git.

## Known gaps and work outside `main`

### Work on other branches of this repository

| Branch | Content | Issue |
|---|---|---|
| `issue-34-review-assets-v2` | Review assets of the main bottle selector semantic-v2: 216 cases of the frozen set `main-selector-hardcases-v2` with masks, crops, and expected results. The branch has no shared history with `main`. | #34 |

The branch `android/current` has no Android content that `main` lacks. Its Android commits are on `main` as rebased copies.

### Open parts of the workbench port

[workbench/ChangeLog.md](workbench/ChangeLog.md) 2026-10-20 records these gaps:

- The lab changes of `matcher/rerank.py` are not ported (F-07).
- The matcher part of selective OCR and `matcher/config.selective-ocr.example.yaml` are not in this repository. [workbench/docs/testing/selective-ocr.md](workbench/docs/testing/selective-ocr.md) names files that are not in this repository.
- `tools/bottle_rotation/` is not in this repository (F-17).

### Demo features

- «Рассказать об этикетке» in the Web UI shows a fixed sample explanation. The UI states that the text is not about the matched wine.
- The `/ideas` page shows ideas with the status of each idea. Four ideas are static mockups with the badge «Макет · не подключено».

### Files that are not in Git

- Model weights. [bootstrap/artifacts/model-bundles/manifest.json](bootstrap/artifacts/model-bundles/manifest.json) lists the archives and their SHA-256 values.
- The lab catalogue database and the rotated index that the `cascade` pipeline needs. The text export of the lab database is in Git (F-36).
- The lab snapshot of 2026-10-18 (2,358 wines, 936 new images) (F-36).
- The Android model pack (F-44).
- The iPhone Core ML models and resource pack (F-94).
- The Dinner Lens embedding indexes, the benchmark ground truth, and the audit directory (F-27, F-29).
- The static wine image release (F-108).
- The organizers' 100 evaluation photos. [eval/](eval/) has three sample photos. The lab set `eval/official-real-photos/` (84 photos) is not in Git (F-66).
- The package `patch_pipeline` and its evidence. They are in the sibling repository `svoe-vino-lab-experiments` (F-14).
- The evidence directories `internal/` of the workbench experiments. [workbench/ChangeLog.md](workbench/ChangeLog.md) names each path.

### Planned features

The open issues of this repository list the planned features, for example #26, #27, and #29 to #31 (post-search features), #35 (screen reader support), #48 (diary history, ratings, and preferences), and #36 (iPhone release). Issue #28 (Dinner Lens) is open, and F-27 to F-29 describe its current state.
