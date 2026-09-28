# 27 — The IoU of the box of the main object in the run validator

Date: 2026-09-25.
Status: draft. It waits for a plan of the matcher change and for the approval of the
owner. Session: drink-atlas-workspace-ca [a2daf6].

## Goal

1. A photo of a test set MAY hold a box of the main object (plan 24). A person draws the
   box on the Testset page `/testset`.
2. The run validator (the benchmark `pipeline/benchmark.py` and the Runs page `/runs`)
   shows IoU metrics for the photos with a box.
3. A match on a photo with a true box passes only when the slug is right and the box of
   the matcher overlaps the true box at least partially.

## Decisions of the owner (2026-09-25T17:23:18+0300)

| Question | Decision |
|---|---|
| Where does the IoU work go? | A new plan 27, after plan 24. Plan 24 stores and exports the box. |
| What does "at least partially" mean? | Any overlap: IoU > 0. The slug is right, and the two boxes share at least one pixel. |
| A configuration that returns no box | IoU `n/a` for that configuration. The slug alone decides the match. The scores of the old configurations do not change. |

The words of the owner (Q3, 17:01:44): "in dataset user draws rect around item that is
main on scene. Run validator should display IoU metrics for these cases. However, it will
fails match if fail to find right bbox at least partially".

## The present state

- `test_photo` holds the true box (`box_left`, `box_top`, `box_right`, `box_bottom`), in
  the pixels of the photo after its EXIF orientation (schema 019).
- The answer of `svoe-vino-matcher` holds no box of the matched item. `shape_answer` of
  `svm/server.py` sends `slug`, `score`, `rank`, and `explain` alone.
- Each whole-image configuration embeds the whole photo, so it has no box. The label
  detector of `svm/detect.py` finds a label box for OCR; that box is not the box of the
  matched item.

## Proposal (to check with the owner)

1. `svoe-vino-matcher`: an optional `box` of the query item in the answer, in the pixels
   of the query image after its EXIF orientation, for a pipeline that crops the query. A
   pipeline with no crop sends no box. This is a change of another project, with its own
   plan.
2. `pipeline/benchmark.py`: `build_queries` puts the true box on each query row.
   `run_benchmark` stores the box of the answer in `results.jsonl`. `judge` of
   `match_scoring.py` gets the rule: with a true box and an answer box, a hit at rank 1
   needs IoU > 0; with no answer box, the slug alone decides.
3. `metrics.json`: `box_queries` (the queries with a true box), `box_answered` (the
   queries whose answer holds a box), `iou_mean`, `iou_median`, and `box_hit_rate` (IoU >
   0 among `box_answered`). A run with no answer box gives `n/a`.
4. The Runs page: the IoU cards, the two boxes on the photo of a row (true and answer),
   and a filter `holds a true box`.

## Open questions

- Q1. Which matcher pipeline gives the first box of the query item: a detector crop of
  the bottle, or the label box of `svm/detect.py`?
- Q2. Is the IoU of a hit at rank 1 enough, or does each candidate get its own box?
