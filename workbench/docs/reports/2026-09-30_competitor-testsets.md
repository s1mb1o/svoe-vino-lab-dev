# Public competitor test sets

Date: 2026-09-30

Pipeline: `siglip2-p512-rot5-seg`

## Outcome

The import inspected 57 local public repository clones.
It imported data from 10 competitors.
It created 13 test sets with 601 rows and 336 distinct image SHA-256 values.
The import found no missing or invalid image.

The `scored` tier contains 147 rows from three competitors.
These rows represent 77 distinct source-photo names.
The row count is not an independent sample count because competitors reuse the same
organizer photos.

The `provisional` tier contains 454 rows.
These rows include development overlap, machine labels, ambiguous labels, and unknown
targets.

## Scored results

Do not combine the rows across sets.
The same source photo can occur in more than one set.

| Test set | Rows | Positive | No-match | Top-1 | Top-5 | MRR | No-match rejected | p95, ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `danya213411-scored` | 29 | 29 | 0 | 24/29, 82.76% | 29/29, 100% | 0.8994 | — | 1,001 |
| `mishanya-scored` | 73 | 46 | 27 | 40/46, 86.96% | 46/46, 100% | 0.9275 | 0/27, 0% | 126 |
| `qacen-scored` | 45 | 45 | 0 | 40/45, 88.89% | 44/45, 97.78% | 0.9315 | — | 872 |

The latency values are not comparable.
The runner marks them as non-comparable.
The runs reused different SAM3 cache states and different image resolutions.

The strongest verified Top-1 result is 88.89% on `qacen-scored`.
All three scored results are below 90% or have a small denominator.
Top-5 is 97.78% to 100%.
This gap shows that candidate generation is strong and final candidate selection is the
main recognition opportunity.

The no-match result is the main failure.
`siglip2-p512-rot5-seg` always returns a catalogue candidate.
It rejected 0 of 27 verified no-match photos in `mishanya-scored`.

## Provisional results

These values are diagnostic.
They are not leaderboard scores.

| Test set | Positive | No-match | Top-1 | Top-5 | No-match rejected | Result |
|---|---:|---:|---:|---:|---:|---|
| `annamistery-provisional` | 52 | 0 | 90.38% | 100% | — | completed |
| `danya213411-provisional` | 8 | 0 | 62.50% | 100% | — | completed; conflicting labels only |
| `enoscan-provisional` | 8 | 2 | 62.50% | 87.50% | 0/2 | completed |
| `kofeinix-provisional` | 67 | 33 | 83.58% | 98.51% | 0/33 | completed |
| `mishanya-provisional` | 14 | 6 | 50.00% | 85.71% | 0/6 | completed; 7 rows excluded by the runner |
| `qacen-provisional` | 37 | 0 | 43.24% | 83.78% | — | completed; 5 rows excluded by the runner |
| `stan-provisional` | 64 | 33 | 79.69% | 98.44% | 0/33 | completed; 3 ambiguous rows excluded |
| `abobamakers-provisional` | 0 | 0 | — | — | — | no query; 54 unresolved rows retained for review |
| `kairov-provisional` | 0 | 0 | — | — | — | no query; 28 unresolved rows retained for review |
| `willmorton-provisional` | 0 | 0 | — | — | — | no query; 3 unresolved rows retained for review |

## Duplicate and label audit

Exactly 100 image SHA-256 values occur in more than one competitor set.
Kofeinix and Stan contain the same 100 organizer images.
Danya, Qacen, Enoscan, and Willmorton contain subsets of this corpus.
These copies MUST NOT count as independent evidence.

The import found nine source-photo names with conflicting labels in the candidate
`scored` data.
It moved every side of each conflict to `provisional`.
The conflicts include:

- `96.31_09-09-2026_19-29-01`: two Aratti sibling slugs.
- `96.61_28-08-2026_09-16-27`: two Balaklava slugs and one no-match label.
- `94.55_02-09-2026_16-53-08`: Denisov sparkling wine versus Denisov Riesling.
- Four Divnomorskoe photos: an exact `Южный Лес` slug versus no-match.
- `95.49_05-09-2026_15-34-51`: two Zhemchuzhnaya 9 sibling slugs.
- One Golubitskoe Chardonnay photo: an exact slug versus no-match.

This audit changes the clean set sizes from 37 to 29 for Danya, from 82 to 73 for
Mishanya, and from 50 to 45 for Qacen.

## Comparison with competitor claims

The comparisons below use each competitor's own public evidence.
They do not establish an independent ranking.

- Danya labels 21 of the final 29 clean photos as Top-1 correct for its system.
  This is 72.41%.
  Our run is 82.76% on these 29 rows.
  Both systems place all 29 targets in Top-5.
- Stan reports 90.6% Top-1 and 100% Top-5 on its 64 positive rows after OCR and tuned
  rules.
  Our result on the same provisional labels is 79.69% and 98.44%.
  Stan has the largest relevant Top-1 advantage, but the labels and rules were developed
  on this corpus.
- Kofeinix reports 98.5% Top-1 and 100% Top-5 on its 67 positive rows.
  Our result is 83.58% and 98.51%.
  This set is development-overlapping and is not an independent estimate.
- Qacen reports 79.3% Top-1 and 98.4% Top-5 on all 87 rows with a different scoring
  policy.
  Our clean exact subset is 88.89% and 97.78%.
  The denominators and policies differ, so the numbers are not directly comparable.
- Anna reports 95.3% Top-1 on 128 labelled photos after selecting a two-crop fusion on
  the same evaluation pool.
  Our public 52-row subset is 90.38%.
  It stays provisional because the evaluation pool selected the fusion and thresholds.

## Dataset value score

This score rates the imported evidence, not the competitor product.
Ten means an independent, fully verified, diverse field set with exact current slugs.

| Competitor | Score / 10 | Reason |
|---|---:|---|
| Danya213411 | 8.5 | Fixed field set, human exact labels, and useful Top-1/Top-5 groups. Conflicts reduce 37 exact rows to 29. |
| Mishanya | 8.5 | Exact labels plus the only substantial public no-match group. Images are thumbnails and nine rows conflict with other labels. |
| Qacen | 8.0 | Clear `exact`, `probable`, and `same_line` policy. Five exact rows moved out after catalogue or cross-source checks. |
| annamistery | 6.0 | Good exact mappings and field images. The same pool selected fusion and thresholds. |
| Kofeinix | 5.5 | Complete 100-photo organizer corpus. It is reused and development-overlapping. |
| Stan | 5.5 | Complete corpus and explicit ambiguous rows. Labels are machine-assisted and rules were tuned on the corpus. |
| Enoscan | 4.0 | Useful fixtures with exact provenance. The set has only 10 rows and is a development fixture. |
| AbobaMakers | 3.5 | Fifty-four new field photos. Public machine-readable exact ground truth is absent. |
| Kairov | 3.0 | Twenty-eight additional field photos. Public ground truth is absent. |
| Willmorton | 1.0 | Three reused public images without public ground truth. |

## What to borrow

### P0: calibrate rejection

Borrow the explicit `found / probable / not_in_catalog` decision used by Anna and Qacen.
Use a held-out no-match set.
Do not select the threshold on the evaluation set.
The current 0% rejection rate is a larger product risk than the remaining Top-5 error.

### P0: add a selective OCR reranker

Borrow Stan's and Kofeinix's rule to run OCR when the visual margin is small.
Stan reports that OCR adds 12.5 to 17.2 percentage points on its real-photo corpus.
Do not run OCR on every confident query.
Use the current Top-5 candidates and compare producer, line, colour, sugar, grape, and
vintage tokens.

### P1: use candidate-union retrieval

Borrow Danya's union of visual Top-30 and OCR Top-10.
This design can recover a target that visual retrieval excludes before reranking.
Keep the union bounded.

### P1: test two-view fusion

Borrow Anna's full/letterbox plus segmentation fusion as an ablation.
Our segmentation can remove useful label context.
Do not replace the current pipeline until a held-out scored set confirms the gain.

### P2: add local geometry only for sibling labels

Borrow Danya's SIFT or another local matcher for visually close Top-5 candidates.
The scored Top-5 results show enough headroom for this reranking stage.
Run it only when the candidates belong to one label family or have a small margin.

## Artifacts

- Importer: `scripts/import_competitor_testsets.py`.
- Import tests: `tests/test_import_competitor_testsets.py`.
- Generated source inventory: `data/competitor-testsets/source-inventory.json`.
- Generated duplicate report: `data/competitor-testsets/overlap.json`.
- Generated manifests: `data/competitor-testsets/<set>/manifest.jsonl`.
- Run directories: `runs/2026-09-30T00*-lab-siglip2-p512-rot5-seg-*`.

The generated data files are outside git.
The report and importer preserve their reproduction commands.
