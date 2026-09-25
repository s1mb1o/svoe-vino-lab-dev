# Plan 40: the benchmark of the embedding entries with the basic pipelines

Date: 2026-09-26

Source: owner message of 2026-09-26T01:43:59+0300. The owner asked this session to
answer its own questions and to log them in [QUESTIONS.md](../../QUESTIONS.md) (Q2 to
Q11).

## 1. Goal

Run the two basic pipelines of the owner message of 2026-09-26T00:45:33+0300 with each
entry of the key `embeddings` of `config.yaml`. Compare the results. Write a report of
the benchmark.

## 2. The basic pipelines

| Form | The steps of the test photo (view `full`) |
|---|---|
| `as-is` | `white_background`, `resize` 1024 |
| `crop` | `segment` `package`, `white_background`, `resize` 1024 |

The catalogue side is the index of the entry. All 11 entries prepare the catalogue with
the same steps: the view `full` is the package cut with the background removed, on
white, 1024 px; the view `label` is the label cut, prepared the same way. The query has
the view `full` alone, so only the `full` items of the index count.

## 3. The entries and the new pipelines

The pipelines `siglip2-p256-as-is` and `siglip2-p256-crop` exist. This plan adds 20
pipelines: one pair for each other entry.

| Entry | Short name |
|---|---|
| `gx10-siglip2-so400m-patch16-naflex-p256` | `siglip2-p256` (present) |
| `gx10-siglip2-so400m-patch16-naflex-p512` | `siglip2-p512` |
| `gx10-siglip2-so400m-patch14-384` | `siglip2-p14-384` |
| `gx10-siglip2-so400m-patch16-256` | `siglip2-256` |
| `gx10-siglip2-so400m-patch16-384` | `siglip2-384` |
| `gx10-siglip2-so400m-patch16-512` | `siglip2-512` |
| `gx10-naflexvit-so400m-patch16-siglip2-p256` | `naflexvit-p256` |
| `gx10-pe-core-l14-336` | `pe-core-l14-336` |
| `gx10-dinov3-vitb16` | `dinov3-vitb16` |
| `gx10-dinov3-vitl16` | `dinov3-vitl16` |
| `local-siglip2-so400m-patch16-naflex-p256` | `local-siglip2-p256` |

## 4. The indexes

1. `gx10-siglip2-so400m-patch16-512` has no index. `build_embeddings.py` builds it. A full
   build took 806 s for `gx10-dinov3-vitl16` on 2026-09-25.
2. The catalogue gives 4,047 items now. 4 of them are `label` items with no label cut, so
   they fail in each entry; they do not count for these pipelines. The index of
   `siglip2-p256` holds the other 4,043. The indexes of 2026-09-25 hold 4,039.
   `build_embeddings.py` adds the missing items to each index, so each run compares the
   same catalogue.

## 5. The runs

1. Sets: `my` (2,209 queries) and `official-real-photos` (80 queries). The runs of
   `vino-svoe-search-by-photo` on `official-real-photos` are the baseline of the present
   recognizer.
2. `embedding_run.py --name <pipeline> --set <set> --workers 4` for a gx10 entry, and
   `--workers 1` with `embedding_python` for the entry of the backend `local`.
3. One entry at a time, so the gateway holds one embedding model at a time. The VLM
   watcher of 8168 keeps its model. Before the first run: `free -h` on gx10 (50 GiB
   available at 01:52).
4. The `as-is` runs first: they send no SAM3 request. The `crop` runs of `my` start after
   the run job `siglip2-p256-crop` of the owner ends, so that the SAM3 answers of the set
   are in `data/cache/sam3/`.
5. A driver script runs the queue in the background. `caffeinate -ims -w <pid>` holds the
   Mac awake. A row in `~/Admin/GPU_TASKS.md` records the queue.

## 6. The report

`docs/reports/2026-09-26_embedding-benchmark.md`, and an entry in `ResearchLog.md`. For
each pipeline and set: R@1, R@5, R@10, MRR of the positive photos; the false match at 1
and the share of the negative photos with the slug in the top 10; the median latency;
the errors. The report ranks the entries by R@1 on `my`, compares `as-is` with `crop`,
and names the gaps of the method.

## 7. Result

To be written after the work.
