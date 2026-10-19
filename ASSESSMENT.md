# Assessment map

| Field | Value |
|---|---|
| Repository | `s1mb1o/svoe-vino-lab-dev` |
| Branch | `main` |
| Checked at commit | `0621952` |
| Date of the last check | 2026-10-19 |
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
| `android/` | `cd android && ./gradlew test assembleDebug` | [android/README.md](android/README.md) |
| `bootstrap/` | `cd bootstrap && .venv/bin/python -m unittest discover -s tests -v` | [bootstrap/README.md](bootstrap/README.md) |
| `proxies/` | `cd proxies && .venv/bin/python -m unittest discover -s tests -t .` | [proxies/README.md](proxies/README.md) |
| `workbench/` | `cd workbench && python3 -m unittest discover -s tests` | [workbench/README.md](workbench/README.md) |

## Highlights

1. **Offline recognition on an Android phone.** The phone segments the bottle, makes a SigLIP2 vector, and searches the catalogue without network. The release manifest has no `INTERNET` permission. See F-80 to F-83.
2. **A cascade matcher with a fixed answer time.** Barcode and QR scan, SAM3 package crop, and a VLM cluster re-rank run in parallel. The matcher answers at 2.9 s and cancels the remaining model calls. See F-04 and F-61.
3. **Recognition of a full shelf in one request.** One photo gives a mask, a box, and a wine card for each bottle. A production check recorded 93 matched bottles in one response. See F-20.
4. **Image moderation before the first disk write.** ShieldGemma 2 checks each photo. Unsafe photos go to a closed quarantine, and the admin UI shows only a blurred preview. See F-73.
5. **Two messengers on one shared core.** The Telegram bot and the MAX bot share `im-core/`. A drift test guards the copied modules. See F-31, F-70, and F-71.
6. **Confidence-aware answers.** Score and margin thresholds select a confident card, a tentative card, or «Не уверен». A negative feedback shows ranks 2 to 4. See F-09 and F-25.
7. **A taste passport and regional dishes after the result.** Each value shows its source: the wine card or a labeled dataset estimate. See F-21 and F-22.
8. **A verifiable matcher build.** The embedding bundle is in Git and the matcher checks its SHA-256 at load. Dependencies are hash-locked. CI fails when any test is skipped. See F-32 and F-33.
9. **Committed benchmark artifacts.** Run directories with queries and predictions are in Git. A reviewer can recompute R@1 offline. See F-10 and F-11.
10. **Two MCP interfaces for AI agents.** WebMCP tools in the portal let an AI agent in a supported browser drive the same scanner and shelf state that a user sees. A local read-only MCP server gives an AI assistant the wine card, filter search, and comparison of the 2,093 Active catalogue wines. See F-77 and F-48.

## Results summary

| Metric | Value | Dataset | Pipeline | Source |
|---|---|---|---|---|
| Top-1 match with the team reference | 95/100 | 100 organizers' photos; reference answers made by the team | `POST /v1/eval/predict` | [README.md](README.md) section «Результаты», [predictions.jsonl](predictions.jsonl) |
| R@1 / R@5 | 90.48% / 100% | Organizers' photos: 63 positive and 21 negative, labels by the team | `cascade-p512-rot5`, `POST /v1/match`, no time limit | [README.md](README.md) section «Предыдущие инженерные бенчмарки», [workbench/ResearchLog.md](workbench/ResearchLog.md) |
| R@1 with the 3 s budget | 90.0%, 81 of 81 photos answered within 3 s | Organizers' photos | `cascade-p512-rot5` with `fast_answer` | [matcher/ResearchLog.md](matcher/ResearchLog.md) |
| R@1 / R@5 | 84.67% / 97.02% | Internal set `my`: 1,644 positive and 584 negative queries | `barcode-rerank-siglip2-512-crop` (workbench) | [BENCHMARKS.md](BENCHMARKS.md), [workbench/docs/reports/2026-09-27_all-profile-rerun/final-profile-comparison.md](workbench/docs/reports/2026-09-27_all-profile-rerun/final-profile-comparison.md) |
| R@1 / R@5 | 74.15% / 92.94% | Internal set `my` | `siglip2-p512-as-is` (default of [matcher/config.yaml](matcher/config.yaml)) | [BENCHMARKS.md](BENCHMARKS.md) |

The 95/100 value is an internal check of the team. It is not an official jury result ([README.md](README.md)).

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
- **Limits:** R@1 is 74.15% on the internal set `my` (see "Results summary").

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
- **Proof:** [workbench/tests/test_cluster_rerank.py](workbench/tests/test_cluster_rerank.py); `workbench/tests/test_label_rules.py::test_a_bottle_number_and_a_feature_outside_the_label_are_never_valid`; [workbench/data/catalog/embeddings/gx10-siglip2-so400m-patch16-naflex-p512/cluster-rules.json](workbench/data/catalog/embeddings/gx10-siglip2-so400m-patch16-naflex-p512/cluster-rules.json).
- **Verify:** Read [workbench/ResearchLog.md](workbench/ResearchLog.md) (paired McNemar test of the re-rank).

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
- **Proof:** `workbench/tests/test_benchmark.py::test_the_metrics_are_the_metrics_of_match_scoring`, `workbench/tests/test_benchmark.py::test_the_runner_does_not_write_to_the_database`; run directories [workbench/runs/2026-09-27T011711Z-lab-barcode-rerank-siglip2-512-crop-my/](workbench/runs/2026-09-27T011711Z-lab-barcode-rerank-siglip2-512-crop-my/) and [workbench/runs/2026-09-27T020325Z-lab-siglip2-p512-as-is-my/](workbench/runs/2026-09-27T020325Z-lab-siglip2-p512-as-is-my/).
- **Verify:** Join `queries.jsonl` with `predictions.jsonl` in a run directory and count the correct Top-1 answers.

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
- **Status:** Deployed ([webui/ChangeLog.md](webui/ChangeLog.md) 2026-09-29). The UI marks the result actions as «ДЕМО-ФУНКЦИИ».
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

- **Claim:** For a slug outside the local records, the server loads the exact card from `api.vino-svoe.ru/v1/wines/<slug>` and validates it. If the request fails, the result keeps the catalogue link.
- **Status:** Implemented.
- **Entry point:** [webui/server/api/wines/[slug].get.ts](webui/server/api/wines/[slug].get.ts), [webui/server/utils/wine-metadata.ts](webui/server/utils/wine-metadata.ts)
- **Proof:** `webui/tests/wine-metadata.test.ts` ("loads one exact slug from the official JSON API").
- **Verify:** Read [webui/server/utils/wine-metadata.ts](webui/server/utils/wine-metadata.ts).

### F-24 Producer product-line map

- **Claim:** The result card has the action «Путеводитель по линейке». It opens an interactive product-line map of the producer. The maps cover 25 producers and 1,203 products with tiers, groups, and bottle images. The map selects the matched wine and marks it «ВАШЕ ВИНО». It has zoom, a group selector, and a control that returns to the matched wine. A product with a catalogue card links to vino-svoe.ru. A product without a card stays selectable without a link. The page `/lineup/<producer>` shows each map in the page space with `noindex`. The page `/lineup` lists all maps.
- **Status:** The core map experience was deployed in web UI release `7d8e80ea` on 2026-10-19. The index `/lineup` and the page layout are implemented. The six-map expansion is implemented in source and awaits deployment.
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
| [android/](android/) | Offline Android application |
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
- **Limits:** The workflow uses a self-hosted runner. Model weights (about 20 GiB) are not in Git. [bootstrap/artifacts/model-bundles/manifest.json](bootstrap/artifacts/model-bundles/manifest.json) lists them with SHA-256 values.

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

- **Claim:** The Android model pack has a format version. The app checks the SHA-256 of each payload, the pipeline ID, and the vector dimension. It rejects unsafe ZIP paths before it activates the pack.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/ModelPack.kt](android/app/src/main/java/com/alolalab/chtozavino/ModelPack.kt), [android/docs/model-pack.md](android/docs/model-pack.md)
- **Proof:** `android/tools/test_build_model_pack.py::test_builds_verified_pack`, `android/tools/test_build_model_pack.py::test_rejects_a_different_siglip_model`.
- **Verify:** `cd android && python3 -m unittest tools.test_build_catalog_pack tools.test_build_model_pack`
- **Limits:** The model pack is not in Git.

### F-45 Matcher-compatible API on the phone

- **Claim:** The debug build of the Android app can run an HTTP server with `/healthz`, `/v1/eval/predict`, and `/v1/match`. The server is off by default.
- **Status:** Implemented (debug builds only).
- **Entry point:** [android/app/src/debug/java/com/alolalab/chtozavino/DebugHttpServer.kt](android/app/src/debug/java/com/alolalab/chtozavino/DebugHttpServer.kt)
- **Proof:** [android/app/src/testDebug/](android/app/src/testDebug/) (`DebugHttpServerTest`: `serverIsDisabledByDefault`, `writesMatcherCompatibleResponses`).
- **Verify:** Read [android/README.md](android/README.md).

### F-46 Workbench web UI with an OpenAPI contract

- **Claim:** The workbench has a local web UI for the dataset, embeddings, clusters, test sets, runs, recognition, and health. A checked-in OpenAPI 3.1 file describes its routes, and a test compares the file with the server routes.
- **Status:** Implemented.
- **Entry point:** [workbench/pipeline/lab_server.py](workbench/pipeline/lab_server.py), [workbench/docs/lab-openapi.yaml](workbench/docs/lab-openapi.yaml)
- **Proof:** `workbench/tests/test_lab_openapi.py::test_document_has_exact_route_inventory`.
- **Verify:** Read [workbench/docs/lab-openapi.yaml](workbench/docs/lab-openapi.yaml).

### F-47 Organizers' harness with checksums

- **Claim:** `eval/` holds the organizers' harness and three sample photos with SHA-256 checksums.
- **Status:** Implemented.
- **Entry point:** [eval/participant_test.sh](eval/participant_test.sh), [eval/README.md](eval/README.md)
- **Proof:** [eval/checksums.sha256](eval/checksums.sha256).
- **Verify:** `cd eval && shasum -a 256 -c checksums.sha256`

### F-48 Read-only catalogue MCP server

- **Claim:** `mcp/` is a local stdio MCP server with five read-only tools: `get_wine`, `find_wines`, `compare_wines`, `get_producer_line`, and `get_audio`. Each tool has strict input and output schemas. `get_producer_line` reads the 25 producer maps of F-24 through the same module as the Web UI. The server reads the matcher bundle of F-32 and stops when the SHA-256 of `wines.jsonl` differs from the manifest. Discovery uses the 2,093 Active wines of the 2,094 bundle IDs. Each result has the catalogue version and the source hashes. The server has no write, command, SQL, or URL fetch tool. A GitHub workflow runs the tests on Node.js 22.19.0 and 26.4.0.
- **Status:** Implemented.
- **Entry point:** [mcp/src/server.mjs](mcp/src/server.mjs), [mcp/src/catalog.mjs](mcp/src/catalog.mjs), [mcp/README.md](mcp/README.md), [.github/workflows/mcp-tests.yml](.github/workflows/mcp-tests.yml)
- **Proof:** `mcp/tests/protocol.test.mjs` ("real SDK client discovers and calls all tools repeatedly over one stdio connection"); `mcp/tests/catalog.test.mjs` ("uses all matcher IDs and excludes non-Active records from discovery", "every Active ID resolves to its exact map node or to unavailable"); [mcp/ChangeLog.md](mcp/ChangeLog.md).
- **Verify:** `cd mcp && npm ci --ignore-scripts && npm test && npm run demo`
- **Limits:** `get_producer_line` covers only the 25 producers of F-24. Other producers return `unavailable`. `get_audio` returns `unavailable`, because the repository has no approved audio files. The server uses local stdio only. No interactive AI assistant and no Qwen dialogue have been tested with it.

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

- **Claim:** The Web UI has a skip link, a live announcement of the result, focus management for dialogs, an inert background under the age dialog, keyboard bottle buttons, `role="meter"`, `aria-pressed`, and reduced motion support.
- **Status:** Implemented.
- **Entry point:** [webui/app/components/PhotoScanner.vue](webui/app/components/PhotoScanner.vue), [webui/app/app.vue](webui/app/app.vue)
- **Proof:** [webui/SMOKE_TESTS.md](webui/SMOKE_TESTS.md) (manual checklist).
- **Verify:** `grep -rno 'aria-[a-z]*' webui/app`

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

- **Claim:** The matcher limits the upload size, the pixel count, and the upload time. A bounded queue returns 503 with `Retry-After` when it is full, and `/healthz` stays available. A production stress test with 32 concurrent clients recorded no HTTP 500.
- **Status:** Deployed.
- **Entry point:** [matcher/protection.py](matcher/protection.py)
- **Proof:** `matcher/tests/test_resilience.py::test_full_queue_returns_503_while_healthz_stays_available`; [matcher/docs/reports/2026-09-29_production-stress-test.md](matcher/docs/reports/2026-09-29_production-stress-test.md).
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

- **Claim:** The Web UI and the bots need an 18+ confirmation before they process a photo. A photo sent before the confirmation waits and enters the queue after «Мне есть 18 лет».
- **Status:** Deployed (Web UI and Telegram gate). Implemented (held photo replay, MAX).
- **Entry point:** [webui/app/components/AgeGate.vue](webui/app/components/AgeGate.vue), [telegram-bot/docs/decisions/004-soft-age-gate.md](telegram-bot/docs/decisions/004-soft-age-gate.md)
- **Proof:** `webui/tests/age.test.ts` ("fails closed when storage is unavailable"); `telegram-bot/tests/test_age_gate.py::test_photo_before_the_age_confirmation_is_queued_after_the_adult_choice`.
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

### F-79 Project pages

- **Claim:** The portal has the pages `/ideas` (feature ideas with their status), `/android` (APK download), `/hackaton`, and `/presentation`.
- **Status:** Deployed ([webui/ChangeLog.md](webui/ChangeLog.md) 2026-09-29).
- **Entry point:** [webui/app/pages/ideas.vue](webui/app/pages/ideas.vue), [webui/app/pages/android.vue](webui/app/pages/android.vue), [webui/app/pages/hackaton.vue](webui/app/pages/hackaton.vue), [webui/app/pages/presentation.vue](webui/app/pages/presentation.vue)
- **Proof:** [webui/tests/android-landing.test.ts](webui/tests/android-landing.test.ts); [webui/scripts/check-presentation-browser.mjs](webui/scripts/check-presentation-browser.mjs).
- **Verify:** Read [webui/docs/ideas-landing.md](webui/docs/ideas-landing.md).

### Android application

#### F-80 On-device bottle segmentation

- **Claim:** The app cuts the bottle out of the photo with DIS (LiteRT) and places it on a white square.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/ImageRecognition.kt](android/app/src/main/java/com/alolalab/chtozavino/ImageRecognition.kt) (`DisImageProcessor`)
- **Proof:** [android/app/src/test/](android/app/src/test/) (`DisMaskTest`); [android/docs/screenshots/android-0.1.4/raw/05_processing_pipeline_dark.png](android/docs/screenshots/android-0.1.4/raw/05_processing_pipeline_dark.png).
- **Verify:** Open the screenshot.

#### F-81 On-device SigLIP2 vectors that match the server

- **Claim:** The app makes a SigLIP2 Base/16-224 vector on the phone. The preprocessing matches the workbench. A check of 32 samples gave a minimum cosine of 0.99999851 against the server vectors.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/ImageRecognition.kt](android/app/src/main/java/com/alolalab/chtozavino/ImageRecognition.kt) (`SigLip2Encoder`)
- **Proof:** [android/VERIFICATION_RESULTS.md](android/VERIFICATION_RESULTS.md); [android/tools/verify_model_vectors.py](android/tools/verify_model_vectors.py); [android/app/src/test/](android/app/src/test/) (`SigLipVectorTest`).
- **Verify:** Read [android/VERIFICATION_RESULTS.md](android/VERIFICATION_RESULTS.md).

#### F-82 Offline catalogue search

- **Claim:** The app searches the catalogue on the phone by cosine similarity and keeps the best image score for each wine. The release manifest has no `INTERNET` permission.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/CatalogueIndex.kt](android/app/src/main/java/com/alolalab/chtozavino/CatalogueIndex.kt), [android/app/src/main/AndroidManifest.xml](android/app/src/main/AndroidManifest.xml)
- **Proof:** [android/app/src/test/](android/app/src/test/) (`CatalogueIndexTest.searchUsesMaximumImageCosinePerWine`).
- **Verify:** `grep -rn INTERNET android/app/src`

#### F-83 Barcode and QR input

- **Claim:** The app reads EAN-8, EAN-13, and QR codes with Google Code Scanner and finds the wine in the local code table.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/MainActivity.kt](android/app/src/main/java/com/alolalab/chtozavino/MainActivity.kt), [android/app/src/main/java/com/alolalab/chtozavino/CatalogueIndex.kt](android/app/src/main/java/com/alolalab/chtozavino/CatalogueIndex.kt)
- **Proof:** [android/app/src/test/](android/app/src/test/) (`CatalogueIndexTest.ean13MatchesGtin14`); [android/docs/screenshots/android-0.1.4/raw/08_barcode_result_dark.png](android/docs/screenshots/android-0.1.4/raw/08_barcode_result_dark.png).
- **Verify:** Open the screenshot.

#### F-84 Accelerator selection

- **Claim:** For each model (DIS and SigLIP2), the user can select Auto, GPU, or CPU. In Auto mode, the app falls back to the CPU when the GPU gives an invalid output.
- **Status:** Implemented.
- **Entry point:** [android/app/src/main/java/com/alolalab/chtozavino/AcceleratorSettings.kt](android/app/src/main/java/com/alolalab/chtozavino/AcceleratorSettings.kt)
- **Proof:** [android/app/src/test/](android/app/src/test/) (`AcceleratorSettingsTest`); [android/ChangeLog.md](android/ChangeLog.md) 2026-09-29 (Pixel 8 timings).
- **Verify:** Read [android/ChangeLog.md](android/ChangeLog.md).

#### F-85 Android release 0.1.4

- **Claim:** The Android app 0.1.4 (Android 9 and later, arm64) is a GitHub pre-release with tag `android-v0.1.4`.
- **Status:** Implemented.
- **Entry point:** [android/app/build.gradle.kts](android/app/build.gradle.kts)
- **Proof:** [android/SMOKE_TESTS.md](android/SMOKE_TESTS.md) 2026-09-29 (APK SHA-256 values); [android/ChangeLog.md](android/ChangeLog.md).
- **Verify:** `git tag --list 'android-*'`

### F-86 HEIF (HEIC) photos

- **Claim:** `POST /v1/eval/predict`, `POST /v1/match`, and `POST /v1/group/match` accept HEIF (HEIC) photos. iPhone cameras save HEIC by default. The matcher decodes the primary image of a HEIF file. A damaged HEIF file gives HTTP 422 on the single-image endpoints and HTTP 400 on the group endpoint, not HTTP 500. The Web UI accepts HEIC photos. For an unreadable HEIC photo, it shows «Не удалось прочитать HEIC. Сохраните фото как JPEG.»
- **Status:** Implemented. [README.md](README.md) states that the production matcher decodes HEIF since 2026-10-18.
- **Entry point:** [matcher/photo.py](matcher/photo.py), [matcher/group.py](matcher/group.py), [matcher/protection.py](matcher/protection.py), [webui/app/composables/useWineScanner.ts](webui/app/composables/useWineScanner.ts)
- **Proof:** `matcher/tests/test_match.py::test_a_heif_photo_is_matched_on_both_single_image_endpoints`, `matcher/tests/test_match.py::test_a_damaged_heif_answers_422_on_both_single_image_endpoints`, `matcher/tests/test_group.py::test_a_damaged_heif_photo_is_400_before_the_sam3_request`, `matcher/tests/test_resilience.py::test_the_libheif_crash_file_does_not_stop_the_service`; `webui/tests/prediction.test.ts` ("accepts a HEIC signature and names the file by its detected type"), `webui/tests/scanner.test.ts` ("explains an unreadable %s photo").
- **Verify:** Read [matcher/ResearchLog.md](matcher/ResearchLog.md) (crash test of two HEIF decoders on 2,106 damaged HEIC files).
- **Limits:** The production Telegram bot accepts photos and albums, but not HEIC files (F-70). The Android app selects only JPEG, PNG, and WebP files in the gallery. A cut tiled HEIF file decodes without an error ([matcher/docs/KNOWN_ISSUES.md](matcher/docs/KNOWN_ISSUES.md), item 4).

## Known gaps and work outside `main`

### Work on other branches of this repository

| Branch | Content | Issue |
|---|---|---|
| `android/current` | YOLO bottle segmentation as a second option, model-pack format 3, a rotated reference index, and a smoke test on a second phone. | #21 |

### Demo features

- «Рассказать об этикетке» in the Web UI shows a fixed sample explanation. The UI states that the text is not about the matched wine.
- The `/ideas` page shows ideas with the status of each idea. Some ideas are mockups.

### Files that are not in Git

- Model weights. [bootstrap/artifacts/model-bundles/manifest.json](bootstrap/artifacts/model-bundles/manifest.json) lists the archives and their SHA-256 values.
- The lab catalogue database and the rotated index that the `cascade` pipeline needs. The text export of the lab database is in Git (F-36).
- The Android model pack.
- The organizers' 100 evaluation photos. [eval/](eval/) has three sample photos.

### Planned features

The open issues of this repository list the planned features, for example #26 to #31 (post-search features) and #35 (screen reader support).
