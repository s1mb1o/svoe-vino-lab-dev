# Max-over-rotation matching of NaFlex p512 on the test set `my`, 2026-09-29

Source: owner messages of 2026-09-29 from 02:02:13 (rotated indexes of NaFlex p512) and
from about 07:18 (plan 82: implement max-over-rotation matching in the lab and the
matcher). Plan: [plans/82_rotated-reference-embeddings.md](../plans/82_rotated-reference-embeddings.md).
Session: drink-atlas-workspace-b6. Artifacts (not in git): `rotation-index-p512-2026-09-29/`
(the offline replay runs, the saved query vectors), the lab runs in `runs/`, and the
offline vectors in `work/rotation-index/`.

## Method

- Score: S(q, x) = max over θ of cos(E(q), E(R_θ(x))). Each full catalogue image of the
  view `full` has one vector for each angle θ: the SAM3 cut of the package on white,
  rotated counter-clockwise on a larger white canvas, with the scale of the 0° `resize`
  (the package keeps its pixel size). SAM3 runs one time, at import; the rotation is
  geometric; the only model on a rotated image is SigLIP2 so400m NaFlex
  (`max_num_patches` 512). A wine scores the best cosine of all its rows.
- Query: one vector of the photo (`as-is`: the photo as it is; `crop`: the SAM3 main
  package box, background kept; `crop-seg`: the SAM3 main package with its mask, the
  background made white — the lab twin of the matcher `hand_selection: true`).
- Test set `my`: 2,226 queries, 1,647 positive and 579 negative.
- Offline replay (`scripts/rotation_index_eval.py`): the baseline runs of the usual
  pipelines keep the query vector of each photo; the replay ranks the same vectors against
  a catalogue of rotated rows with the lab metrics code (`benchmark.run_benchmark`). The
  rotated rows come from `scripts/rotation_index_build.py` (2,270 images × 72 angles,
  160,560 vectors, 0 problems, 4,953 s). The replay with the 0° row alone repeats the
  official runs exactly.

## Results on `my`

| Query | Catalogue | R@1 | R@5 | R@10 | MRR | False match at 1 (of 579) |
|---|---|---:|---:|---:|---:|---:|
| as-is | 1 vector | 74.26 % | 94.11 % | 96.30 % | 0.8309 | 115 |
| as-is | rotated 0°–355°, step 5° (72) | **77.23 %** | **95.45 %** | 96.66 % | 0.8538 | 116 |
| as-is | rotated 0°–180°, step 5° (37) | 76.93 % | 95.39 % | 96.66 % | 0.8523 | 110 |
| crop | 1 vector | 79.48 % | 96.11 % | 97.27 % | 0.8694 | 111 |
| crop | rotated 0°–355°, step 5° | 79.66 % | 96.17 % | 97.27 % | 0.8704 | **102** |
| crop | rotated 0°–180°, step 5° | 79.60 % | 96.11 % | 97.21 % | 0.8702 | 105 |
| crop-seg | 1 vector | 78.87 % | 95.26 % | 97.15 % | 0.8642 | 107 |

The rotated rows of the as-is and crop lines are the offline replay. The crop-seg line is
the lab run `runs/2026-09-29T071123Z-lab-siglip2-p512-crop-seg-my-plan82` (0 errors).

### Lab runs of the rotated entry `…-p512-rot5` (plan 82)

The standard lab path: `pipeline/embedding_run.py --name <pipeline> --set my --workers 8
--label plan82`, with the lab index of `gx10-siglip2-so400m-patch16-naflex-p512-rot5`
(72 angles, 163,440 rows) and a new query vector for each photo. 0 errors, 0 HTTP 429.

| Query | 1 vector (p512) | rotated 5° (lab run) | Change | False match at 1: 1 vector → rotated |
|---|---:|---:|---:|---:|
| as-is | 74.26 % | **77.35 %** | +3.09 pp | 115 → 114 |
| crop | 79.48 % | 79.60 % | +0.12 pp | 111 → **100** |
| crop-seg | 78.87 % | **79.84 %** | +0.97 pp | 107 → 106 |

R@5 of the lab runs: as-is 95.39 %, crop 96.17 %, crop-seg 95.81 %. R@10: 96.66 %,
97.27 %, 97.02 %. MRR: 0.8542, 0.8702, 0.8708. Run directories:
`runs/2026-09-29T084644Z-lab-siglip2-p512-rot5-as-is-my-plan82`,
`runs/2026-09-29T084811Z-lab-siglip2-p512-rot5-crop-my-plan82`,
`runs/2026-09-29T084930Z-lab-siglip2-p512-rot5-crop-seg-my-plan82`.
The lab runs agree with the offline replay within 2 queries (as-is 77.35 % against
77.23 %, crop 79.60 % against 79.66 %): the query vectors of a new run differ a little
from the saved ones. `results.jsonl` of a rotated run is 19–23 MB, below the 29 MB of the
1-vector crop-seg run: the rows of one image give one item.

### Confident answers at the Telegram bot thresholds

The bot answers only when the top score is at least `BOT_MATCH_MIN_SCORE` 0.70 and the
margin to the second wine is at least `BOT_MATCH_MIN_MARGIN` 0.015. Max-over-rotation
raises the top score and the scores of the competing wines, so the thresholds need a check.

| Run | Confident answers | Precision of confident answers | Right and confident (of 1,647) | Confident on negatives (of 579) |
|---|---:|---:|---:|---:|
| as-is, 1 vector | 52.3 % | 75.9 % | 884 | 191 |
| as-is, rotated 0°–355°/5° | 53.7 % | 77.2 % | 923 | 183 |
| as-is, rotated 0°–180°/5° | 53.2 % | 77.3 % | 916 | 186 |
| crop, 1 vector | 66.2 % | 73.0 % | 1,076 | 306 |
| crop, rotated 0°–355°/5° | 66.1 % | 72.9 % | 1,073 | 308 |
| crop, rotated 0°–180°/5° | 66.4 % | 73.0 % | 1,078 | 310 |
| crop-seg, 1 vector | 67.3 % | 72.1 % | 1,080 | 329 |
| as-is, rotated 5° (lab run) | 53.9 % | 77.1 % | 925 | 186 |
| crop, rotated 5° (lab run) | 65.8 % | 73.1 % | 1,070 | 304 |
| crop-seg, rotated 5° (lab run) | 65.9 % | 73.1 % | 1,072 | 316 |

## Findings

1. The rotated catalogue helps the whole-photo query most: R@1 +2.97 pp (+49 queries),
   R@5 +1.34 pp. The present production matcher uses this query (`hand_selection: false`),
   so the rotated catalogue alone gives it about +3 pp R@1 with no change of the query.
2. With the SAM3 crop, the gain is small (R@1 +0.18 pp), and the false matches at 1 fall
   from 111 to 102.
3. The half range 0°–180° gives almost the full gain with half of the rows.
4. At the bot thresholds, the rotated catalogue gives the as-is query more confident answers
   (52.3 % → 53.7 %) with a higher precision (75.9 % → 77.2 %) and fewer confident answers
   on negatives (191 → 183). For the crop query the thresholds give the same result.
5. The masked crop (crop-seg) with 1 vector is 0.61 pp below the box crop at R@1, and it
   gives more confident answers on negatives (329). A crop query gives higher scores to the
   wrong wines too: the thresholds are calibrated for the as-is query.
6. The masked crop gains most among the crop queries: crop-seg with the rotated catalogue
   has the best R@1 of all configurations (79.84 %, +0.97 pp against its 1-vector run).
   Its pixels are closest to the rotated catalogue images (a package on white). The matcher
   twin is `hand_selection: true`; its selector is the matcher port of the lab main-scene
   selector, so its results can differ a little from the lab crop-seg.
7. Build speed: the gx10 NaFlex p512 model gives about 26–34 images per second; the GPU is
   at about 96 % during a build. More parallel requests give HTTP 429 (the lab clients retry
   it). About 1.5 h for the 163,440 vectors of the 5° index.

## Verification of the implementation (plan 82)

- The lab build of `…-p512-rot5` (`pipeline/build_embeddings.py --workers 6`): 2,270
  images, 163,440 vectors, 0 failures, 5,021 s (32.5 vectors/s).
- The 0° input of the lab builder equals the index PNG of `…-naflex-p512` byte for byte
  (sha256) for all 2,270 images, and the 0° row equals the p512 index row (cosine
  ≥ 0.99992).
- Each of the 163,440 rows of the lab index `…-rot5` equals the offline row of the same
  angle (cosine ≥ 0.99991; no row below 0.9999), and each record holds the angles 0°, 5°,
  …, 355° in order: the angle order and the row ranges are correct. The same check passed
  for the 767 images (27,612 rows) of `…-rot10` before its stop.
- A format 3 bundle of the rotated entry validates; the matcher loads it, and for 300 saved
  query vectors the matcher top-1 wine and its best angle equal the lab result in 300 of
  300 cases.
- The present 14 indexes keep their view hashes and `index.json` configs (no item became
  stale).
- The lab runs of `siglip2-p512-rot5-as-is` and `-crop` agree with the offline replay
  within 2 queries, and each candidate of a rotated run holds `angle`.

## Notes

- The owner stopped the 10° work (message of 10:17:26: no 10° runs when the 5° runs exist).
  The entry `…-p512-rot10` stays in `config.yaml` with 767 of 2,270 images built.
- Known: `FIX_LATER.md` item 1 — each rotated entry keeps its own copy of the 0° PNG files.
- One image of `…-rot10` failed with HTTP 429 while a lab run shared the gateway.
- At 11:43 two processes of this owner conversation started the same three rot5 runs;
  both stopped them, and b6 ran them again at 11:46 alone (0 errors, 0 HTTP 429).

## Recommendation

- For the production matcher (the whole-photo query), a rotated bundle of
  `…-p512-rot5` (format version 3) adds about +3 pp R@1 with no change of the query, and
  the bot answers more often with a higher precision. A switch of the production bundle is
  an owner decision (a gx10 deployment).
- With `hand_selection: true`, the rotated catalogue gives the best R@1 in the lab (79.84 %
  with crop-seg), but the crop queries give more confident answers on negatives at the bot
  thresholds: the thresholds need a new calibration first.
- The half range 0°–180° (37 rows) keeps almost all the gain of the full range (72 rows).
