# 48 — The cluster re-rank at query time

Date: 2026-09-26.
Status: implemented and measured on 2026-09-26. The section "Result" holds the benchmark.
Written by drink-atlas-workspace-39 [fb59ad], also named CLUSTERS [fb59ad].
Source: the owner messages of 2026-09-26T13:04:00+0300 (the question about the trigger)
and 13:10:00 («implement»), and the answer of 14:56:00 in
[owner-messages.md](../owner-messages.md).

## Goal

1. A lab pipeline can re-rank the cards of one cluster with the label rules of plan 45.
2. The step acts only when cards of one cluster compete at the top of the answer.
3. The benchmark measures the step against its base pipeline on the test set `my`.

## Decisions

| Question | Decision | Reason |
|---|---|---|
| The trigger | the rank-1 card is in a cluster whose rule has the mode `sheet` or `verdict`, and at least one other card of that cluster is in the first `window` (5) positions | The owner proposed «all top-k from one cluster». On `siglip2-512-crop` that acts on 37 photos and can fix 2 misses, because 132 of the 163 clusters have 2 wines. This trigger acts on 574 photos and can fix 89 of the 93 misses whose true card is in the cluster of the rank-1 card. The owner answered «implement» to this proposal. |
| The order | only the cards of the cluster inside the window change their order; every other candidate keeps its position, and every position keeps its score | as `svoe-vino-matcher` (plan 05 of `svoe-vino-testset`) |
| The rules | `rerank.rules` names one embedding directory; its `clusters.json` (view `combined`) and `cluster-rules.json` (space `label`) serve every pipeline | A cluster is a group of catalogue cards that look alike. The rules of `gx10-siglip2-so400m-patch16-naflex-p256` are the only rules on 2026-09-26. |
| The picture | the SAM3 label cut of the photo on white, else the whole photo, scaled UP or down to 1,536 pixels | as `svoe-vino-matcher`; the rules are label-only rules |
| The VLM | `qwen3.5-9b-nvfp4`, thinking off, `max_tokens` 256, timeout 180 s | the model of plans 29 and 45; the probe of plan 45 found no answer with thinking |
| The prompts | `SHEET_PROMPT` and `VERDICT_PROMPT` of `svoe-vino-matcher/svm/cluster_rules.py`, verbatim | A test compares them. |
| A failure | a VLM failure, an answer that is not JSON, or no winner keeps the base order, and the step records the error | The photo keeps its base answer. |
| The barcode step | the re-rank runs inside the barcode step | A code hit answers the photo first, and the re-rank does not run. |
| The file of `f4` | one separate hunk in `build_pipeline_backend` of `pipeline/embedding_run.py` | owner answer of 14:56:00; the stale section of session f4 lists the file |

## The step

For each photo:

1. The base backend (`embedding_run.EmbeddingBackend`) answers the photo.
2. A photo with an error, with no candidate, or with a candidate of the code lookup keeps
   its answer.
3. The trigger (see "Decisions"). A photo that does not trigger the step keeps its answer,
   and no VLM call goes out.
4. Mode `sheet`: the VLM gets `SHEET_PROMPT` with the valid questions. The options of a
   question are its expected answers, `other`, and `not visible`. An answer equal to the
   expected answer of a card gives +1 to that card; a different answer gives -1; `not
   visible` or a null expected answer gives 0. In a question of kind `vintage`, an answer
   with one year counts as that year when a card expects it, else as `other`.
5. Mode `verdict`: the VLM gets `VERDICT_PROMPT` with the name and a short label
   description of each card and the rule text. The request holds a JSON schema that
   allows the letters and `unsure`. The chosen card moves to the first position of the
   window.
6. The cards of the cluster inside the window take the new order. A tie keeps the base
   order.
7. Each card of the cluster in the window gets `explain` with `kind: cluster_rules`, the
   cluster key, the mode, the window, the questions and the answers (or the rule text,
   the letters, and the answer), the scores, `changed`, the time of the call, `cached`,
   `error`, and its base rank and base score. The VLM box of `/runs` reads this record.
8. The trace of the photo (plan 41) gets the step `cluster_rules`. The latency of the
   photo holds the time of the step.

The VLM answers go through `pipeline/model_cache.py`, so a second run of the same photos
makes no call.

## The configuration

A pipeline of the backend `embedding` takes the optional key `rerank`:

```yaml
  - name: rerank-siglip2-512-crop
    backend: embedding
    embedding: gx10-siglip2-so400m-patch16-512
    views: *crop-views
    rerank: &rerank-options
      rules: gx10-siglip2-so400m-patch16-naflex-p256
      window: 5
      vlm: qwen3.5-9b-nvfp4
      thinking: false
      side: 1536
      max_tokens: 256
      timeout_s: 180
  - name: barcode-rerank-siglip2-512-crop
    backend: embedding
    embedding: gx10-siglip2-so400m-patch16-512
    barcode: *barcode-options
    rerank: *rerank-options
    views: *crop-views
```

- `rules` MUST name an entry of the key `embeddings`. Its directory MUST hold
  `clusters.json` and `cluster-rules.json`, else the run stops at the start.
- `window` is an integer of at least 2. An unknown key stops the check of the pipeline.

## Code

| File | Change |
|---|---|
| `pipeline/cluster_rerank.py` | new: the options, the prompts, the answers, the order, `RuleBook`, `ClusterRerank` |
| `pipeline/pipelines.py` | the key `rerank` of the backend `embedding`; `rerank.rules` MUST be an entry of `embeddings` |
| `pipeline/embedding_run.py` | `build_pipeline_backend` puts `ClusterRerank` around the embedding backend, inside `CodeFirst` |
| `pipeline/label_rules.py` | `ask`: an optional JSON schema (`json_schema`) |
| `config.yaml` | the pipelines `rerank-siglip2-512-crop` and `barcode-rerank-siglip2-512-crop`, with a comment |
| `tests/test_cluster_rerank.py` | new, 19 tests: the answers, the trigger, the order, the backend with a fake VLM, the key of a pipeline, the prompts against `svoe-vino-matcher` |
| `README.md`, `COMMANDS.md`, `SMOKE_TESTS.md` (RR1 to RR6), `ChangeLog.md`, `ResearchLog.md` | own hunks |

## Known limits

- The frames of the clusters on `/runs` read the clusters of the embedding of the run
  (`/api/run-clusters`, plan 43). The embedding `siglip2-512` has no `clusters.json`, so a
  run of `rerank-siglip2-512-crop` shows no frame. The VLM box shows the step, with the
  cluster key instead of the cluster id.
- The step popup of `/runs` (plan 41, `run_steps.py`) does not name the step
  `cluster_rules`. The trace holds it.
- The rules come from `qwen3.5-9b-nvfp4` and hold errors, for example the colour of card
  B of the «Фантом» cluster (`ResearchLog.md`, 2026-09-26).

## The benchmark

1. A smoke run of 8 photos with the real VLM (15:05): 4 misses of `siglip2-512-crop` whose
   true card stood at rank 2 moved to rank 1; 4 hits stayed. One VLM call took 0.9 to
   1.5 s.
2. A row in `/Users/ashmelev/Admin/GPU_TASKS.md`.
3. `embedding_run.py --name rerank-siglip2-512-crop --set my --workers 4 --label bench48`,
   then the same for `barcode-rerank-siglip2-512-crop`, with `embedding_python`.
4. The paired comparison with the base runs of plan 45 (label `bench45`): R@1, R@5, MRR,
   the false matches of the negatives, the wins and the losses at rank 1, and the exact
   McNemar test.

## Result

Measured on 2026-09-26, 15:09 to 15:28, label `bench48`, 2,209 photos of `my` (1,625
positive, 584 negative), against the runs of plan 45 (label `bench45`) on the same photos.
`scripts/compare_runs.py` gives the paired numbers; `work/bench48/rerank_stats.py` the view
of the step.

| Pipeline | R@1 | R@5 | MRR | Negatives rejected | Median ms |
|---|---:|---:|---:|---:|---:|
| `siglip2-512-crop` | 81.29 % | 95.63 % | 0.878 | 82.88 % | 172 |
| `rerank-siglip2-512-crop` | **83.26 %** | 95.63 % | 0.889 | **85.10 %** | 223 |
| `barcode-siglip2-512-crop` | 82.58 % | 96.74 % | 0.890 | 82.88 % | 376 |
| `barcode-rerank-siglip2-512-crop` | **84.55 %** | 96.74 % | 0.901 | **85.10 %** | 561 |

- Positives: +1.97 points, 48 wins and 16 losses, exact McNemar p 7.7e-05, for both pairs.
- Negatives: +2.23 points, 16 wins and 3 losses, p 0.0044, for both pairs.
- The step acted on 574 photos, as the analysis before the plan predicted: 537 of mode
  `sheet` (111 changed; positives 42 wins and 13 losses; negatives 16 wins and 3 losses)
  and 37 of mode `verdict` (14 changed; positives 6 wins and 3 losses). 0 VLM errors. Each
  of the 574 photos had a label cut.
- 48 of the 89 misses that the step could fix are fixed.
- Time: one VLM call median 2.7 s, p90 4.1 s, with 4 photos at a time and the watcher of
  plan 29 on the same model. A photo with the step: median 5.1 s; without it: 184 ms. The
  barcode run got every VLM answer from the cache (the same label cuts and prompts), so its
  photos with the step took 0.8 s.
- The 16 losses: a small mark read wrong (a sugar level «Demi-Sec» for «Demi-Sucré», a
  kosher mark `not visible`); questions that the check of plan 45 lets through (the
  background colour of the label; a six-digit number on the edge of the label, which
  changes from bottle to bottle); features outside the label cut (a neck ribbon, a text
  at the bottom edge); a verdict by the vintage year alone (`ee8d0719c613`, 3 losses); and
  an expected text with a reading error of stage 2 («УНИКАЛ» for «УЗНАЙ»).

Candidate changes, each chosen after this run (post hoc), to be measured on one half of
the wines and reported on the other half:

- strike a question about a colour, a background, or a design unless the note names it;
- strike a question whose answers are numbers of 5 or more digits;
- count only «yes» as evidence in a yes/no question;
- a margin guard on the base score gap.
