# Competitor pipeline ablation

Date: 2026-09-30

Status: completed

## Objective

Implement comparable adaptations of five public competitor architectures.
Measure each new action alone.
Measure each complete adapted pipeline on the same benchmark rows.

The implementation MUST NOT claim byte-for-byte or model-for-model equivalence with a
competitor system.
The report MUST call each configuration an adaptation.

## Evidence sources

The source repositories are local public clones under
`/Volumes/T7_2TB/2026_LCT_Hackatons_10`.

| Competitor | Source design | Adapted stages |
|---|---|---|
| Stan | `docs/superpowers/specs/2026-09-21-ocr-rerank-design.md` and `ml/wine_ml/text_match.py` | visual Top-10, token-IDF OCR rerank, colour/sugar/year contradiction penalty |
| Kofeinix | `src/api/services/visual_search.py` and `src/ml/ocr_matching.py` | weighted multi-view retrieval and structured OCR bonus |
| Danya | `ARCHITECTURE.md` and `src/stage5/` | visual Top-30 plus global OCR Top-10 union, structured rerank, local geometry, unknown decision |
| Anna | `app/pipelines/search/cascade/` | candidate retrieval, two-view fusion, and `found / probable / not_in_catalog` zones |
| Qacen | `ml/app/matcher_siglip.py` | package crop, SigLIP2 retrieval, and the published cosine reject threshold 0.76 |

## Benchmark contract

The importer MUST create `competitors-scored-common` from the three scored source sets.
The common set MUST group rows by the original source-photo stem.
It MUST contain one row per stem.
It MUST prefer the image with the largest pixel area when several copies have the same
label.
It MUST refuse a group that has two different labels.

The expected 2026-09-30 snapshot contains 77 rows.
It contains 50 positive rows and 27 verified no-match rows.
No configuration MAY select a weight or threshold from these 77 rows.

Every run MUST use this set, the same catalogue database, Top-5 output, and the same
metric implementation.
The report MUST include positive Top-1, positive Top-5, no-match rejection, exact
decision accuracy, and paired wins and losses against the base pipeline.

## Base and atomic configurations

`siglip2-p512-rot5-seg` is the base configuration.

An atomic configuration MUST add exactly one action to this base.

| Configuration | One action |
|---|---|
| `competitor-stan-ocr` | Stan token-IDF OCR rerank of the visual Top-10 |
| `competitor-kofeinix-ocr` | Kofeinix structured OCR bonus over the visual pool |
| `competitor-danya-ocr-union` | Danya global OCR Top-10 union with visual Top-30 |
| `competitor-anna-two-view` | Anna-style weighted `full` plus `label` view fusion |
| `competitor-qacen-reject` | Qacen absolute cosine rejection at 0.76 |

The atomic configurations MUST keep the base embedding entry.

## Complete adapted configurations

| Configuration | Stages |
|---|---|
| `competitor-stan-full` | closest local Stan SigLIP2 384 index, two views, Stan OCR rerank |
| `competitor-kofeinix-full` | closest local Kofeinix SigLIP2 384 index, weighted views, structured OCR bonus |
| `competitor-danya-full` | DINO candidate source, SigLIP visual pool, OCR union, structured OCR rerank, SIFT rerank, unknown gate |
| `competitor-anna-full` | DINO candidate source, SigLIP two-view fusion, Anna decision zones with reject below 0.55 |
| `competitor-qacen-full` | NaFlex p1024 package and label views, fusion, Qacen reject below 0.76 |

The complete Danya pipeline MAY use DINOv3 as the available proxy for public DINOv2.
The report MUST state this substitution.

## Pipeline configuration

An embedding pipeline MAY contain a checked `competitor` mapping.

```yaml
competitor:
  source: stan
  pool: 30
  secondary:
    embedding: gx10-dinov3-vitb16
    views: {full: {steps: [...]}}
    top_k: 30
  actions:
    - action: secondary_union
    - action: ocr_rerank
      profile: stan
      top_k: 10
      alpha: 0.18
      conflict_penalty: 0.08
    - action: reject
      min_score: 0.55
      score_field: visual_score
```

The `secondary` mapping is optional.
Only `secondary_union` MAY read it.
The base and secondary retrieval pools MUST be computed before the wrapper truncates the
answer to the requested Top-K.

## Actions

### `view_fusion`

Read the per-view cosine fields that the embedding backend already returns.
Compute a weighted mean over available views.
Keep the original score in `visual_score`.
Write the new value to `score` and `fusion_score`.

### `ocr_rerank`

Use local Tesseract with `rus+eng`.
Cache OCR text by input SHA-256 outside git.
The Stan profile MUST implement candidate-local IDF, fuzzy token evidence, and
colour/sugar/year contradiction penalties.
The structured profile MUST score name, producer, grape, colour, category, and vintage
evidence separately.
The action MUST preserve the visual score.

### `ocr_union`

Score every active catalogue record against the OCR text.
Union the best OCR records with the visual pool.
Do not invent an image similarity for an OCR-only candidate.

### `secondary_union`

Run the checked secondary embedding pipeline on the same image.
Union its candidates with the primary candidates by slug.
Preserve both scores in diagnostic fields.

### `sift_rerank`

Use SIFT ratio matching and RANSAC inliers for the first five candidates.
Use the prepared catalogue image of each candidate.
Add a bounded bonus.
Raise a clear configuration error when OpenCV is not installed.

### `reject`

Reject when the configured score is below the fixed threshold.
An optional margin threshold MAY mark the answer as probable in the trace.
Rejection MUST return an empty candidate list, because the benchmark represents a
no-match answer with no candidate.
The trace MUST retain the rejected Top-5 for audit.

## Files

| File | Change |
|---|---|
| `scripts/import_competitor_testsets.py` | build the common scored set |
| `tests/test_import_competitor_testsets.py` | test deduplication and conflict refusal |
| `pipeline/competitor_steps.py` | checked actions and the backend wrapper |
| `pipeline/pipelines.py` | accept and validate `competitor` |
| `pipeline/embedding_run.py` | build the primary, secondary, and wrapper backends |
| `tests/test_competitor_steps.py` | unit tests for each action |
| `config.yaml` | atomic and complete adapted configurations |
| `requirements-local.txt` | add OpenCV for SIFT and RapidFuzz for bounded OCR latency |
| `COMMANDS.md` | reproducible benchmark commands |
| `README.md` | explain the adaptation boundary |
| `SMOKE_TESTS.md` | manual checks |
| `ChangeLog.md` | dated result |
| `docs/reports/2026-09-30_competitor-pipeline-ablation.md` | comparison and conclusions |

## Acceptance criteria

1. The common set has 77 rows, with 50 positive and 27 no-match rows.
2. Every positive common-set slug exists in `wine_catalog`.
3. The parser rejects unknown actions, keys, profiles, and invalid thresholds.
4. Each atomic configuration has one action.
5. Each complete configuration records every action in `run.json`.
6. Unit tests cover reranking, union, fusion, SIFT, and rejection.
7. Eleven runs complete on `competitors-scored-common`: the base, five atomic, and five
   complete configurations.
8. The report separates atomic gain from complete-pipeline performance.
9. The report states every model substitution and every unavailable original artifact.
10. The lab server restarts and `GET /api/dataset` returns HTTP 200.

## Risks

- OCR and SIFT add latency.
- The public competitor thresholds use different embedding score distributions.
- The common set is small.
- Many public competitor photos came from one organizer corpus.
- A complete adaptation measures the public architecture with local substitutes. It
  does not reproduce the private trained weights.

## Completion

Completed on 2026-09-30.

The importer made the 77-row common set.
The implementation added five atomic configurations and five complete adaptations.
All 11 benchmark runs completed with zero query errors.
The full test suite passed 1,494 tests and skipped one test.
The lab server restarted on port 8168.
`GET /api/dataset`, the common test set, and the run configuration API returned HTTP
200.
The run configuration API listed all ten adaptations.
The result is in
[`docs/reports/2026-09-30_competitor-pipeline-ablation.md`](../reports/2026-09-30_competitor-pipeline-ablation.md).

The main decision is to keep the reject-gate idea and conditional structured OCR.
The complete adaptations do not replace the base pipeline.
