# 68 — The re-rank reads the rules of its own embedding

Date: 2026-09-28

Status: draft. Session drink-atlas-workspace-31 [e1f2c7].

Source: the owner message of 2026-09-28T00:04:51+0300 («use same embedding for rules and
used for embedding») and the answers of 00:06:31 in
[owner-messages.md](../owner-messages.md).

## Problem

The pipelines `rerank-siglip2-512-crop`, `barcode-rerank-siglip2-512-crop`, and
`barcode-rerank-siglip2-512-crop-label` search with `gx10-siglip2-so400m-patch16-512`.
Their re-rank reads `clusters.json` and `cluster-rules.json` of
`gx10-siglip2-so400m-patch16-naflex-p256` (the key `rerank.rules`). The reason is history:
on 2026-09-26 the NaFlex p256 rules were the only rules (plan 48). No measurement chose
this.

The clusters decide when the re-rank acts. The trigger needs the rank-1 wine and one
more wine of its cluster in the first 5 positions of the 512 ranking. A pair of wines that
the 512 model confuses, but that NaFlex p256 did not put in one cluster, never gets the
re-rank.

## Decisions of the owner

| Topic | Decision (answers of 2026-09-28T00:06:31+0300) |
|---|---|
| The rule | Code rule. The key `rerank.rules` is removed. The re-rank reads `clusters.json` and `cluster-rules.json` of the directory of the pipeline key `embedding`. A config with `rerank.rules` stops at the start with an error. |
| Stage 1 | Describe all again. `build_label_rules.py` describes each card of the new clusters with `qwen3.5-9b-nvfp4` on gx10. No description is copied from the NaFlex p256 file. |
| Measurement | Two runs of `barcode-rerank-siglip2-512-crop` on the set `my`, on the same index: run A with the NaFlex p256 rules (the code before this plan), run B with the 512 rules. |

## Steps

1. Run A: `barcode-rerank-siglip2-512-crop` on `my` with the present code and rules.
2. Build the clusters of `gx10-siglip2-so400m-patch16-512`:
   `python3 pipeline/build_clusters.py --name gx10-siglip2-so400m-patch16-512`. The
   thresholds come from the block `clusters` of `config.yaml` (0.95 and 0.95). The build
   writes only into `data/embeddings/gx10-siglip2-so400m-patch16-512/`.
3. The note of the owner (open question Q1).
4. Build the rules: `python3 pipeline/build_label_rules.py --name
   gx10-siglip2-so400m-patch16-512`. Stage 1: `vlm` of the block `label_rules`
   (`qwen3.5-9b-nvfp4`, gx10). Stage 2: `rules_vlm` (`qwencloud-qwen3.8-max`). The command
   runs under `caffeinate -ims`.
5. The code change and the config change go live together (see "Code"). Then the restart
   of 8168, because the lab server holds `cluster_rerank.py` and `pipelines.py` in memory
   and reads `config.yaml` at each request.
6. Run B: the same pipeline on `my` with the new code and the 512 rules.
7. The comparison of A and B: R@1, R@5, MRR, the wins and the losses of the re-rank, the
   number of photos that trigger the re-rank, and the latency.

## Code

| File | Change |
|---|---|
| `pipeline/cluster_rerank.py` | `OPTION_KEYS` loses `rules`. `check_options` refuses the key `rules` with a clear error. `ClusterRerank` takes the name of the pipeline embedding and reads the rules of its directory. The spec of the run keeps the key `rerank.rules`, with the name of the embedding, so the readers of old runs do not change. The module docstring. |
| `pipeline/embedding_run.py` | `build_pipeline_backend` gives `pipeline.embedding` to `ClusterRerank`. |
| `pipeline/pipelines.py` | The check of `rerank.rules` goes. |
| `config.yaml` | The line `rules:` of `&rerank-options` goes. The comment before `rerank-siglip2-512-crop` changes. |
| `tests/test_cluster_rerank.py` | The fixture and the option tests follow the new rule. A new test: the key `rules` stops the check. |
| `docs/plans/48_cluster-rerank.md` | A note at the end that points to this plan. |

The other lines of `cluster_rerank.py` and `embedding_run.py` stay byte-identical. The
uncommitted hunks of plans 58 and 64 are in the same files.

## What does not change

- The NaFlex p256 folder keeps its `clusters.json`, `cluster-rules.json`, and
  `cluster-notes.json`. The page `/clusters` shows them as before.
- The VLM, the window, the prompts, and the trigger of the re-rank.

## Open questions

- Q1: the note of the owner on the «Фантом» cluster is in
  `gx10-siglip2-so400m-patch16-naflex-p256/cluster-notes.json`. The key of a cluster is the
  hash of its slugs. A copy of the file into the 512 folder gives the note to a 512 cluster
  with the same three wines. Copy it or not?
- Q2: permission for separate hunks in `cluster_rerank.py`, `embedding_run.py`,
  `config.yaml`, and `pipelines.py`. The stale sections 4e, df, c7, f4, 1d, 1b, and
  codex-profile-latency list these files.
- Q3: permission for the restart of 8168 in step 5.

## Risks

- Stage 1 and the re-rank of the runs use the gx10 gateway. The label watcher of plan 61
  uses it too, and got HTTP 429 answers on 2026-09-27. The build can be slow. Its duration
  is not known.
- Between step 5 and the end of the restart, the lab server runs the old code with the
  new config. The three re-rank pipelines then show a config error on `/testset` and
  `/recognize`. The window is short.
- The 512 clusters can differ in number and size from the NaFlex p256 clusters. A cluster
  with more than 20 cards gets no rule (`rules_max_images`).
