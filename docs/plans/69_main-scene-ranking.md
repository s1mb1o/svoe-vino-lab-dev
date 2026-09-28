# Plan 69: main-scene package ranking

Date: 2026-09-28

## Status

Implemented and verified on 2026-09-28.

## Problem

The query-photo package selector uses a bottle-first rule.
The rule selects a shelf bottle when a person holds a can in front of the shelf.
The rule also gives no explanation for its selection.

The catalogue-image processor MUST keep its present bottle-first rule.
This plan changes query photos of configured recognition pipelines only.

## Requirements

1. SAM3 MUST detect `wine bottle`, `can`, `packet`, `box`, and `hand` in one request.
2. The selector MUST rank all package instances without a package-class priority.
3. A package that overlaps a detected hand SHOULD get a strong positive signal.
4. The selector MUST also use relative area, center position, detector confidence,
   sharpness, visible mask fill, edge visibility, and shelf repetition.
5. A small shelf package MUST NOT win only because its box overlaps a large hand box.
6. When no hand is present, the selector SHOULD prefer a large, central, sharp, and
   isolated package.
7. The selected instance mask MUST make the package cut.
8. A photo with no package MUST keep the present white-background fallback.
9. A transparent photo MUST keep the present alpha-background rule.
10. The step trace MUST record the weights, every signal, every weighted contribution,
    every candidate score, and the selected candidate.
11. `/recognize` MUST show the recorded information in the `Result` data of the package
    step.
12. An old run MUST keep the old package-selection behavior when the run specification
    does not name the new selector.

## Selection rule

The selector computes each signal in the range from 0 to 1.

- `hand_contact` measures package-box overlap with a hand box.
  Relative package area reduces this signal for small packages.
- `area` is the square root of package mask area divided by the largest package mask
  area.
- `center` decreases with the distance from the image center.
- `confidence` is the SAM3 confidence.
- `sharpness` is the normalized grayscale gradient energy of the package crop.
- `mask_fill` is package mask area divided by package box area.
- `edge_visibility` decreases when the package box touches an image edge.
- `shelf_isolation` decreases when similar packages occur in the same horizontal band.

When SAM3 finds a hand, the selector uses these weights:

| Signal | Weight |
|---|---:|
| `hand_contact` | 0.40 |
| `area` | 0.22 |
| `center` | 0.14 |
| `sharpness` | 0.08 |
| `confidence` | 0.06 |
| `mask_fill` | 0.04 |
| `shelf_isolation` | 0.04 |
| `edge_visibility` | 0.02 |

When SAM3 finds no hand, the selector uses these weights:

| Signal | Weight |
|---|---:|
| `area` | 0.28 |
| `center` | 0.24 |
| `confidence` | 0.14 |
| `sharpness` | 0.12 |
| `shelf_isolation` | 0.10 |
| `mask_fill` | 0.08 |
| `edge_visibility` | 0.04 |

The highest weighted sum wins.
Relative area and detector confidence break an exact tie.

## Trace contract

The `sam3-package` trace result MUST contain these keys:

- `method`, `rule`, `box`, and `size` for compatibility with the present trace.
- `selection.version` for replay compatibility.
- `selection.mode` with `hand`, `scene`, `alpha`, or `white`.
- `selection.texts` with the SAM3 prompt.
- `selection.weights` with the active weights.
- `selection.hands` with the detected hand count.
- `selection.candidates` with the ranked audit records.
- `selection.selected` with the selected rank and label.

Each candidate audit record MUST contain its label, box, detector score, scene score,
signals, weighted contributions, shelf-peer count, rank, and selected state.
The record MUST NOT contain a mask body.

## Tests

1. A large central can that overlaps a hand MUST beat many shelf bottles.
2. A small bottle inside a hand box MUST not beat a large held package.
3. The main bottle MUST win in a scene with many bottles and no hand.
4. An exact score tie MUST have a stable result.
5. The selected mask MUST make the crop.
6. A photo with no package MUST use the white fallback.
7. A transparent photo MUST use the alpha rule without a SAM3 request.
8. A configured pipeline MUST record the selector version in its run specification.
9. The package step on `/recognize` MUST expose the selection audit in `Result`.
10. An old run specification MUST use the old selector during replay.

## A4 drawing

Create one A4 portrait PDF.
Show candidate detection, signal calculation, the hand and no-hand branches, ranking,
selection, segmentation, and trace output.
Render the PDF to PNG and inspect the complete page before delivery.

## Result

- `pipeline/main_scene.py` implements selector version 1.
- Configured embedding pipelines use the selector for query photos.
- The catalogue-image processor keeps the old bottle-first rule.
- The `Package selection and cut` result on `/recognize` shows the complete selection
  audit.
- Both supplied Abrau Fizz photos select `can` from 21 and 25 package candidates.
- The full test suite passes: 1,298 tests, with 5 skipped tests.
- The live server on port 8168 returns HTTP 200 after the restart.
- The A4 portrait PDF is `output/pdf/main-scene-selection.pdf`.
