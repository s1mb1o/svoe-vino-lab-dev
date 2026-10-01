# Competitor pipeline ablation

Date: 2026-09-30

## Result

The comparison used one frozen set and one catalogue snapshot.
The set `competitors-scored-common` contains 77 rows.
It contains 50 positive rows and 27 verified no-match rows.
All 11 runs completed with zero query errors.

The best low-risk change is the Qacen-style reject action on our base retrieval.
It keeps positive Top-1 at 86.0%.
It rejects 8 of 27 no-match photos.
Exact decision accuracy rises from 55.8% to 66.2%.

The best ranking-only change is the Kofeinix-style structured OCR action.
It keeps positive Top-1 at 86.0%.
It raises positive Top-5 from 98.0% to 100.0%.
Its median latency rises from 690 ms to 1,130 ms.
Its p95 latency rises to 12,625 ms because Tesseract is expensive on text-heavy retail images.

The highest exact decision accuracy is 72.7% for `competitor-qacen-full`.
This result has a recall cost.
Positive Top-1 falls to 82.0%.
The gate rejects 15 of 27 no-match photos and three positive photos.
Do not ship this fixed threshold without calibration on a separate validation set.

## Metric definition

Positive Top-1 and Top-5 use the 50 positive rows.
No-match rejection uses the 27 verified no-match rows.
Exact decision accuracy is `(correct positive Top-1 + rejected no-match) / 77`.
Paired wins and losses compare positive Top-1 with `siglip2-p512-rot5-seg` on the same
query IDs.

The metric does not hide abstentions.
A rejected positive is not a correct result.
A candidate for a no-match row is not a correct result.

## Atomic actions

Each atomic configuration keeps the base embedding entry.
Each atomic configuration adds one action.

| Configuration | Action | Top-1 | Top-5 | No-match rejected | Exact decision | Wins / losses | Median / p95 |
|---|---|---:|---:|---:|---:|---:|---:|
| `siglip2-p512-rot5-seg` | base | 86.0% | 98.0% | 0/27 | 55.8% | 0 / 0 | 690 / 932 ms |
| `competitor-stan-ocr` | candidate-local IDF OCR rerank | 84.0% | 100.0% | 0/27 | 54.5% | 1 / 2 | 1,966 / 5,284 ms |
| `competitor-kofeinix-ocr` | structured OCR bonus | 86.0% | 100.0% | 0/27 | 55.8% | 0 / 0 | 1,130 / 12,625 ms |
| `competitor-danya-ocr-union` | global OCR Top-10 union | 70.0% | 98.0% | 0/27 | 45.5% | 0 / 8 | 3,523 / 67,320 ms |
| `competitor-anna-two-view` | `full` plus `label` fusion | 84.0% | 98.0% | 0/27 | 54.5% | 2 / 3 | 1,326 / 2,465 ms |
| `competitor-qacen-reject` | fixed cosine reject at 0.76 | 86.0% | 98.0% | 8/27 | 66.2% | 0 / 0 | 691 / 912 ms |

### Atomic conclusions

1. Keep the Qacen reject idea.
   Calibrate the threshold on a separate set before production use.
2. Keep the Kofeinix OCR idea as a conditional fallback.
   Run it only for a small visual margin or a weak Top-1 score.
3. Do not use the Danya global OCR union with the current score formula.
   It loses eight base Top-1 hits and adds a large CPU tail.
4. Do not use the Anna two-view weights as an unconditional replacement.
   The action fixes two rows and breaks three rows.
5. Do not use the Stan OCR weights as an unconditional replacement.
   The action improves Top-5 but loses one net Top-1 hit.

## Complete adaptations

| Configuration | Main local substitutions | Top-1 | Top-5 | No-match rejected | Positive no-answer | Exact decision | Wins / losses | Median / p95 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `competitor-stan-full` | local SigLIP2 patch14-384; two views; Tesseract | 84.0% | 98.0% | 0/27 | 0 | 54.5% | 4 / 5 | 1,259 / 25,849 ms |
| `competitor-kofeinix-full` | local SigLIP2 patch16-384; two views; Tesseract | 82.0% | 98.0% | 0/27 | 0 | 53.2% | 3 / 5 | 1,283 / 27,824 ms |
| `competitor-danya-full` | DINOv3 for public DINOv2; local Tesseract and SIFT | 62.0% | 88.0% | 0/27 | 0 | 40.3% | 2 / 14 | 5,299 / 63,803 ms |
| `competitor-anna-full` | local DINOv3 candidate source; local SigLIP2 rerank | 74.0% | 94.0% | 0/27 | 0 | 48.1% | 4 / 10 | 2,408 / 8,033 ms |
| `competitor-qacen-full` | local NaFlex p1024; two views; fixed reject | 82.0% | 94.0% | 15/27 | 3 | 72.7% | 5 / 7 | 1,208 / 1,411 ms |

The complete adaptations are not reproductions of competitor scores.
The original trained weights are not available in the common harness.
The original catalogues are not used.
The original OCR engines and confidence calibrators are not always available.
The Danya configuration uses DINOv3 as a proxy for public DINOv2.
The Danya published review threshold belongs to its learned confidence model.
The local configuration applies it to an adapted score.
This threshold is a diagnostic proxy.

## Pareto decision

Use two ideas from the competitor work.

- Add an abstention gate after the base retrieval.
  The fixed Qacen threshold gives the largest immediate gain and almost no extra latency.
  Replace the fixed value with a calibrated score-and-margin rule.
- Add structured OCR only to uncertain visual answers.
  The Kofeinix action reaches 100% Top-5 without a Top-1 loss on this set.
  A conditional trigger avoids the 12.6-second p95 tail on easy photos.

Do not replace the base retrieval with any complete adaptation from this experiment.
The base has the best positive Top-1 result among configurations that answer every
positive photo.

## Reproduction

Run the base:

```bash
SAM3_ENDPOINT=http://192.168.86.14:18081/upstream/sam3 \
  ~/.venvs/svoe-vino-lab/bin/python pipeline/embedding_run.py \
  --name siglip2-p512-rot5-seg --set competitors-scored-common --workers 4
```

Replace `--name` with one of the ten `competitor-*` names in `config.yaml`.
The saved runs have the labels `plan91-base`, `plan91-atomic`, and `plan91-full`.

## Verification

- `python3 tests/test_competitor_steps.py -q`: 10 tests passed.
- `python3 tests/test_pipelines.py -q`: 34 tests passed.
- `python3 tests/test_barcode.py -q`: 27 tests passed.
- `python3 tests/test_import_competitor_testsets.py -q`: 5 tests passed.
- Full suite: 1,494 tests passed and one test was skipped.
- Eleven benchmark runs completed with zero query errors.

## Limits

The common set is small.
It is not a hidden competition test set.
Some source photos can share acquisition conditions.
The 27 no-match rows have a large effect on exact decision accuracy.
No threshold was selected from these 77 rows.
Future threshold calibration MUST use another set.
