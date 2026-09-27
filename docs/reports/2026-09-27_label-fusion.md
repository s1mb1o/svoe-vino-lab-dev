# Label-space embeddings and their fusion with the full-bottle embeddings in the top-k

Date: 2026-09-27. Source: owner message of 2026-09-27T10:13:59+0300. Session
drink-atlas-workspace-d7 [604e28]. Research only: no code or configuration changed.

## 1. Summary

1. The lab already has a two-tower pipeline: `barcode-rerank-siglip2-512-crop-label`.
   Both towers use the index of `gx10-siglip2-so400m-patch16-512`. The view `full`
   searches the package vectors. The view `label` searches the label vectors.
   `Catalogue.rank` fuses the two by the mean of the best cosine of each view.
2. The mean makes the answer worse. After the rerank, R@1 falls from 1,392 to 1,363 of
   1,644 positive photos. This is the measurement of
   [label-comparison-final.md](2026-09-27_all-profile-rerun/label-comparison-final.md).
   The label run is also slower: a median of 1,800 ms per photo against 186 ms. Most of
   the extra time is the SAM3 label call.
3. A replay of 23 fusion rules on the saved per-view top-10 lists found no rule that beats
   the full tower after the rerank. The best rule in-sample gives +1 R@1. A rule that is
   selected on 4 folds and scored on the 5th gives 1,380 to 1,382, against 1,392.
4. The two towers make different errors. The label tower alone is correct on 93 photos
   where the full tower is wrong. A perfect pick of the two gives 1,419 R@1 before the
   rerank, against 1,352. The cosines and the margins do not show which tower is correct.
5. The label tower alone is weak: 75.6 % R@1 against 82.2 % for the full tower, before the
   rerank. The fusion rule is not the limit. The quality of the label tower is the limit.
6. In `svoe-vino-matcher` on 2026-09-22, the same kind of fusion gave +3.4 points of R@1
   (p = 0.00045). That base was weaker (the gateway SigLIP 2 at 384 px, R@1 0.759), and
   it had no cluster rerank. The present full tower (SigLIP 2 at 512 px on the package
   cut) and the cluster rerank already correct most of those cases.

## 2. What the lab does now

- `pipeline/embedding_run.py`, `Catalogue.rank`: for each view of the photo, the best
  cosine of each wine over its items of that view. The score is `total / count`, where
  `count` is the number of views in which the wine has a vector.
- A wine with no label vector gets the mean of one view. Its score is then not comparable
  with the score of a wine with two views. The index has 2,051 full-view wines and 2,047
  label-view wines, so the effect is small today.
- The config names one `embedding` for each pipeline. So both towers MUST use the same
  model and the same index. A label tower from another model is not possible now.
- The label SAM3 call (`segmenter.instances` with `alternatives.DETECT_TEXTS`) is a second
  SAM3 call after the package call. A cache miss took about 1.8 s. The answer of that call
  also holds the `bottle` instance.
- Every index in `data/embeddings/` holds label vectors (2,095 to 2,103 label items). The
  label run of 01:19 filled the SAM3 label cache for 2,202 photos of the set `my`.

## 3. The replay

The script: [fusion_replay.py](2026-09-27_label-fusion/fusion_replay.py). It reads
`results.jsonl` of two runs. It sends no request and writes no file. It runs in about 6 s.

- Label run: `2026-09-27T011951Z-lab-barcode-rerank-siglip2-512-crop-label-my`.
- Reference run: `2026-09-27T011711Z-lab-barcode-rerank-siglip2-512-crop-my`.
- Both runs have the same photos, index, and full-tower inputs. Both ran before the new
  package rule of `derive.package_instance` (ResearchLog entry of 2026-09-27).

Method:

- The step `search` of each view holds the top 10 wines of that view. The candidates hold
  both cosines of the 10 fused wines. An unknown cosine gets the 10th cosine of its view,
  which is an upper bound.
- Check: the replay of the mean gives the recorded base rank 1 on 2,143 of 2,204 photos.
  The replayed base R@1 is 1,352 (full) and 1,328 (mean). The recorded values are 1,351
  and 1,332. The difference comes from rounded cosines, ties, and the upper bound.
- The rerank is not replayed. In table 2, a photo where the reference run ran the rerank
  keeps the final answer of the reference run. Each other photo takes the fused order.
- Rules: weighted sums, reciprocal rank fusion (RRF), a per-photo min-max scale, the label
  as a re-order of the full top 2, 3, or 5, and a gate that uses the label only when the
  full margin is small.

Main rows (1,644 positive photos, 584 negative photos):

| Rule | R@1 before rerank | R@1 after rerank | R@5 | False match at 1, after |
|---|---:|---:|---:|---:|
| full only (reference) | 1,352 | 1,392 | 1,595 | 90 |
| mean, w_full 0.5 (present rule) | 1,328 | 1,367 | 1,577 | 91 |
| weighted, w_full 0.75 | 1,365 | 1,390 | 1,596 | 92 |
| weighted, w_full 0.90 | 1,353 | 1,391 | 1,595 | 89 |
| RRF k 10, w_label 0.5 | 1,346 | 1,384 | 1,598 | 94 |
| margin gate 0.010, w_full 0.7 | 1,369 | 1,393 | 1,591 | 93 |
| label only | 1,242 | 1,317 | 1,555 | 85 |
| grouped 5-fold selection (3 seeds) | | 1,380 to 1,382 | 1,591 to 1,593 | 91 to 92 |

The full tables are in the output of the script.

Where the 93 label-only wins go:

- 19: the rerank of the reference run already corrects them.
- 26: the rerank ran, and the reference answer stays wrong.
- 48: the rerank did not run, and the reference answer stays wrong. This is the best
  target for a label tower: a confusion between wines that are not in one cluster.

R@5 of the full tower is already 97.0 %. No rule adds more than 4 photos to R@5. So the
label tower cannot add much to the candidate pool of the rerank.

## 4. Why the label tower is weak: hypotheses

These are hypotheses. No experiment tested them.

1. Resolution asymmetry. Catalogue label cuts are small: median long side 417 px, p10
   263 px. Query label cuts are about 800 to 950 px. The model scales both to 512 x 512.
   The catalogue side is scaled up and soft. The query side is sharp.
2. Distortion. `siglip2-so400m-patch16-512` squashes each input into a square. A NaFlex
   entry keeps the aspect ratio.
3. Same model, same errors. Both towers use one model. A label tower from another model
   family can make more different errors. The benchmark of plan 40 found that at least
   one of 22 pipelines is correct at rank 1 on 92.3 % of the photos.
4. One label for many wines. Wines of one line often share the label. The capsule, the
   glass, and the wine colour are only in the full view.

## 5. Options

### A. Measure label towers first (recommended)

1. Run a label-only pipeline for 3 or 4 entries on the set `my`, with `--config` of a
   scratch copy and `--runs-dir` under `work/`. Candidates: `siglip2-512` with the query
   label scaled down to the catalogue size (hypothesis 1), `siglip2-naflex-p1024`,
   `siglip2-p14-384`, `pe-core-l14-336`. The SAM3 label cache is full, so each run sends
   only embedding requests to gx10.
2. Fuse each label run with the full tower of the reference run offline, with the
   replay script and the grouped folds. A cross-model fusion needs no code change for
   this test.
3. Build the fusion code (option B) only for a tower with a gain in the held-out folds.

### B. Build a configurable fusion now

- A pipeline key `fusion`, for example `{method: weighted, weights: {full: 0.8, label:
  0.2}}` or `{method: rrf, k: 60}`. The present mean stays the default.
- A per-view key `embedding`, so that the label tower can use the index of another entry.
- A missing view gets a floor value, not a smaller divisor.
- The trace and the run page show the list of each tower and the fused list.
- Risk: the replay shows no gain with the present label tower. The code has value only
  with a better tower.

### C. Use the label tower only for narrow decisions

- A tie-break between near-equal full candidates that are not in one cluster (the 48
  photos), or more candidates for the rerank.
- The replay of the margin gate and of the top-n re-order gives -9 to +1 R@1 after the
  rerank. The held-out folds give a loss. Not recommended now.

### A precondition of each option

A live label tower needs a faster label cut. The label SAM3 call costs about 1.8 s for a
new photo. Two ways: send the two SAM3 calls at the same time, or take the package cut
from the answer of the label call. The second way changes the package cut, so it needs a
new full-tower run.

## 6. Open questions

1. Is the target the lab benchmark (R@1 after the rerank), or the latency of the demo?
2. May the label-only runs of option A use gx10 now? About 3 min for each entry, from the
   bench40 timing (67 min for 44 runs).
3. Is a text tower in scope? For example, an OCR or VLM reading of the label, matched
   with the card fields. The cluster rerank already reads the label for cluster cases.
