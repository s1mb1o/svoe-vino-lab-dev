# 43 — The lab uses the embedding clusters alone

Date: 2026-09-26.
Status: approved for implementation on 2026-09-26.
Source: owner message of 2026-09-26T07:32:51+0300 and the answers that follow it in
`docs/owner-messages.md`.

## Goal

1. The lab reads cluster data only from `data/embeddings/<name>/` (plan 30).
2. The lab stops reading `dataset/catalog-clusters.json`,
   `dataset/catalog-cluster-rules.json`, and `dataset/catalog-cluster-notes.json`.
3. The three files and the scripts that write them go to `.attick`.

## Readers before this plan

| Reader | File |
|---|---|
| `GET /api/run-clusters` of `pipeline/run_routes.py`, and the cluster frames and the VLM box of `pipeline/pages/runs.html` | `catalog-clusters.json`, `catalog-cluster-rules.json` |
| `scripts/10_clusters.py` | writes `catalog-clusters.json` |
| `scripts/11_cluster_rules.py`, `scripts/cluster_rules.py` | read `catalog-clusters.json`; write `catalog-cluster-rules.json` |
| `scripts/cluster_rules_report.py` | `catalog-clusters.json`, `catalog-cluster-rules.json` |
| `/clusters`, `/api/clusters`, `/api/cluster-note`, `/api/cluster-rule-edit`, `/api/cluster-rule` of `scripts/review_server.py` | all three files |

No project outside the lab reads the lab copy. `svoe-vino-matcher` and
`svoe-vino-testset` read `svoe-vino-testset/dataset/catalog-clusters.json`.

Plan 41 (session f4) removed the use of the two files from `pipeline/run_steps.py` on
2026-09-26.

## Decisions

### D1. The embedding of a run

`GET /api/run-clusters?id=<run id>` reads `run.json` of the run.

- When `backend.kind` is `embedding`, the embedding name is `backend.embedding`.
- A run of an embedding configuration (before plan 34) has no `backend.embedding`. Its
  embedding name is `backend.id`.
- A run of another kind has no embedding. The route answers no cluster.

The route does not read `config.yaml` to find the embedding. A run keeps its embedding
after a change of `config.yaml`.

### D2. The clusters of the run

The route reads `data/embeddings/<name>/clusters.json` with `clusters.load_artifact`.
It uses the view `combined`, as the Testset page does (plan 37).

The answer holds `exists`, `embedding`, `space`, `file`, `built_at`, `stale`,
`clusters`, and `cards`. One cluster holds `id`, `key`, `kind`, `size`, `slugs`, and
`rule`.

`stale` comes from `clusters.artifact_status`. It is `null` when the status cannot be
computed, for example when `config.yaml` has no entry of that name.

### D3. The rules of the clusters

The route reads `data/embeddings/<name>/cluster-rules.json` with `clusters.load_rules`.
It uses the space `label`, because the current matcher sends a label crop (plan 30). The
key of a rule is the cluster key. The route sends the keys `mode` and `questions` of the
rule.

No `cluster-rules.json` exists on 2026-09-26. So `rule` is `null` for every cluster.

The VLM box of `/runs` keeps its fallback: it shows the questions of the rule whose
`valid` is true. Open point: the future rule builder of plan 30 MUST mark each accepted
question with `valid: true`, or this page code MUST change.

### D4. The Runs page

- `loadRun` reads `/api/run-clusters?id=<run id>` for each new run. The page does not
  read the clusters at start.
- The link of a frame opens `/clusters?name=<embedding>&space=combined#<slug>`.
- The title of a frame reads `cluster <id> · <kind> · <size> wines`. A stale artifact
  adds `· stale`.
- A run with no embedding shows no frame. Its VLM box shows only what the run recorded.

### D5. Retirement

These files move to `../.attick/svoe-vino-lab/` with the same relative path:

- `dataset/catalog-clusters.json`;
- `dataset/catalog-cluster-rules.json`;
- `dataset/catalog-cluster-notes.json`;
- `scripts/10_clusters.py`;
- `scripts/11_cluster_rules.py`;
- `scripts/cluster_rules_report.py`.

The lab git repository loses these files. The git history keeps them.

`scripts/review_server.py` loses these parts:

- the routes `/clusters`, `/api/clusters`, `/api/cluster-note`,
  `/api/cluster-rule-edit`, and `/api/cluster-rule`;
- the handlers `_clusters_view`, `_with_rules`, `_set_cluster_note`,
  `_edit_cluster_rule`, and `_build_cluster_rule`;
- `_rule_lock`;
- `PAGE_CLUSTERS`;
- `import cluster_rules`;
- the link `Clusters` in the navigation of its own pages;
- the request of `/api/clusters` in its runs page. The map `CLUSTER` stays empty, so the
  page shows no frame.

`PAGE_DATASET` of the review tool is `pipeline/pages/dataset.html` of the lab. This plan
does not change that page. Its link `Clusters` gives HTTP 404 in the review tool.

### D6. `scripts/cluster_rules.py` stays

Owner answer of 2026-09-26: keep `scripts/cluster_rules.py` and its three tests. The
later rule builder of plan 30 can use its VLM client, its prompts, and its checks.

After this plan, only tests import the module. Its default paths name the moved files.
So `load_clusters`, `load_rules`, and `load_notes` answer empty values.
`scripts/common.py` keeps `CLUSTERS_FILE` for this module.

### D7. The reviewer note

The one note of `catalog-cluster-notes.json` goes to
`data/embeddings/gx10-siglip2-so400m-patch16-naflex-p256/cluster-notes.json` under the
key `a29e59138ed4`. That cluster holds exactly the same three wines in all three views.
The note keeps its text, its slugs, and its `updated_at`.

## Files

- `pipeline/run_routes.py`: `CLUSTERS_FILE`, `RULES_FILE`, `cluster_key` go; the branch
  `/api/run-clusters` passes the run directory and the query; `clusters_view` is new.
- `pipeline/pages/runs.html`: `init`, `loadRun`, `candStrip`, and the comments of
  `CLUSTER` and `CARDNAME`.
- `tests/test_run_routes.py`: the test of `/api/run-clusters`.
- `scripts/review_server.py`: D5.
- `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`, `docs/API.md`, `docs/openapi.yaml`.
- `data/embeddings/gx10-siglip2-so400m-patch16-naflex-p256/cluster-notes.json` (new, not
  in git).

## Verification

1. Run all lab tests.
2. Start `scripts/review_server.py` on a free port. Check `/runs` and `/dataset` for
   HTTP 200 and `/clusters` for HTTP 404.
3. Restart the lab server on port 8168 (rules 22 to 24 of `AGENTS.md`).
4. Check `/api/run-clusters?id=<an embedding run of the NaFlex p256 embedding>`: 168
   clusters, `stale` present.
5. Check `/api/run-clusters?id=<a run of vino-svoe-search-by-photo>`: no cluster.
6. Open `/runs` in light and dark themes. Check a frame and its link.

## Result of 2026-09-26

- `python3 tests/test_run_routes.py`: 7 tests OK. The full suite: 768 tests OK, 5 skipped.
- The review tool, started with `SVOE_VINO_REVIEW_CONFIG=config.old.yaml` (the lab
  `config.yaml` has no key `dataset`): `/runs`, `/embedding`, `/docs`, and `/api/runs`
  answer 200 with no link `Clusters`. `/clusters`, `/api/clusters`, and
  `POST /api/cluster-note` answer 404.
- The lab server of port 8168 started at 07:44:40, after the write of `run_routes.py` at
  07:44:27 (a restart by another session). So this plan needed no restart of its own.
- `/api/run-clusters?id=2026-09-25T220729Z-lab-siglip2-p256-crop-my`: embedding
  `gx10-siglip2-so400m-patch16-naflex-p256`, 168 clusters, 393 card names, `stale: true`
  (the vectors changed at 01:56, after the cluster build of 01:06). A run of
  `vino-svoe-search-by-photo`: `embedding: null`. A run of `dinov3-vitb16-crop`:
  `exists: false`. `id=none`: 404.
- Playwright, light and dark: 18 checks pass. 153 frames on the first 100 rows of the
  embedding run; the title reads `cluster c074 · full · 2 wines · stale`; the link opens
  that cluster on `/clusters`; a switch to the remote run clears the frames; no page error.
- `/api/clusters/gx10-siglip2-so400m-patch16-naflex-p256` shows the Fantom note on
  `c022` (`full`), `c015` (`label`), and `c030` (`combined`), not inherited.
