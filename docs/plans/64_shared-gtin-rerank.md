# Plan 64: a shared GTIN re-ranks the top-k

Date: 2026-09-27.
Source: owner message of 2026-09-27T17:12:18+0300, answer "3" of 17:16:05, answers of
19:28:52.
Session: drink-atlas-workspace-4e [ff960b].

## Problem

Plan 58 limits the embedding match of a photo with a shared GTIN to the code wines. The
answer holds no other wine. A wine that has the same GTIN on its bottle, but no row in
`wine_code`, cannot come back at any rank. This case is real: until 17:02 on 2026-09-27,
`shato-pino-shiraz-krasnoe-suhoe-135` had no row for the GTIN `04680074271535` of
`shato-pino-shiraz-krasnoe-suhoe-14`.

The VLM re-rank of plan 48 compares only the cards of one cluster. The wines of a shared
GTIN are not always in one cluster. On 2026-09-27 the rules embedding
`gx10-siglip2-so400m-patch16-naflex-p256` has these facts:

- `shato-pino-shiraz-krasnoe-suhoe-14` and `shato-pino-shiraz-krasnoe-suhoe-135` (GTIN
  `04680074271535`) are in no cluster.
- `belmas-winery-viognier-belmas-vione-beloe-suhoe-122` is in no cluster.
  `belmas-winery-viogner-katya-vione-beloe-suhoe-135` is in the cluster `186bb11fa294`
  (GTIN `04630171632036`).

So the VLM never compares the wines of a shared GTIN.

The owner wants the photos of the 2017 vintage to match `shato-pino-shiraz-krasnoe-suhoe-14`
and the other photos to match `shato-pino-shiraz-krasnoe-suhoe-135` (owner message of
17:05:11). The rules build of plan 45 already has this logic: `VINTAGE_NOTE` gives a card
that states a year that year, and a card that states no year the answer `other`.

## Terms

- A shared GTIN, a unique code, and the code wines have the meaning of plan 58.
- The GTIN wines are the code wines of the shared GTIN that decides the answer of a photo.
- A GTIN link is a forced link of the cluster build between two Active wines that have the
  same GTIN in `wine_code`.

## Requirements

### The order of the answer

1. A unique code keeps the fast exit of plan 42.
2. A shared GTIN of a photo, with no unique code, does not limit the match. The embedding
   ranks every wine.
3. The answer puts the GTIN wines first, in score order. A GTIN wine that is not in the
   normal top-k also goes in. Then the other wines follow in score order, up to `top_k`.
4. A GTIN wine with no current vector goes after the ranked GTIN wines. It keeps the keys
   of a code candidate and the score `None`, as in plan 58.
5. Each candidate keeps its own score. So a score can rise after the last GTIN wine.
6. A shared QR URL does not change the match (plan 58, requirement 9).
7. The priority in one photo does not change: a unique code, then the first shared GTIN,
   then the normal match (plan 58, requirement 10).
8. The key `mode` of the trace step `barcode` is `first` for a shared GTIN. The value
   `limit` of plan 58 is no longer written.

### The VLM window

9. With a shared GTIN, the VLM re-rank acts when these conditions are true:
   - the rank-1 card is a GTIN wine,
   - the rank-1 card is in a cluster that holds a rule of the mode `sheet` or `verdict`,
   - one more GTIN wine of that cluster is in the first `window` positions.
10. The window holds only the GTIN wines of that cluster in the first `window`
    positions. Only these positions change their order. A wine that is not a GTIN wine
    does not move.
11. Mode `sheet`: the scores are the scores of plan 48, and the order sorts the window.
    Mode `verdict`: the prompt lists every card of the cluster, as in plan 48. A choice of
    a card outside the window keeps the base order.
12. With a shared GTIN, the normal trigger of plan 48 does not run. One photo gets at
    most one VLM call.
13. A photo with no shared GTIN gets the re-rank of plan 48 with no change.

### The GTIN links of the cluster build

14. The cluster build adds a GTIN link for each two Active wines of each GTIN of
    `wine_code` that 2 or more Active wines have. A GTIN link counts only when both wines
    are in the build.
15. The link goes into each view: `full`, `label`, and `combined`, as the manual pairs of
    plan 62.
16. A GTIN link has `by: ["gtin"]` and no vector evidence. A link that already exists gets
    `gtin` at the end of its list `by`.
17. A cluster with a GTIN link has the signal `gtin`. A cluster with no vector link and no
    manual link has the kind `gtin`.
18. The input hash of the build includes the GTIN pairs. With no GTIN pair, the hash
    stays the hash of the builds before this plan.
19. The limit `max_cluster_size` applies.
20. A QR URL gives no link. A QR URL can name a producer: on 2026-09-27, 5 wines of
    `agrolayn` have the QR URL `https://oooagrolain.ru/`.
21. The page `/clusters` shows the badge `gtin` in the light theme and in the dark theme.

### Rollout

22. The GTIN window can act only after a rebuild of `clusters.json` and a rules build of
    the changed clusters of `gx10-siglip2-so400m-patch16-naflex-p256`. The owner decides
    the time of these builds.

## Files

- `pipeline/embedding_run.py`: `Catalogue.rank` and `EmbeddingBackend.ask` take `first`
  instead of `only`.
- `pipeline/cluster_rerank.py`: `RuleBook.trigger`, `ClusterRerank.rerank`, and
  `ClusterRerank.ask` take `first`.
- `pipeline/barcode.py`: `CodeFirst.ask` asks with `first`; a new method puts the GTIN
  wines with no vector after the ranked GTIN wines; the module docstring.
- `pipeline/clusters.py`: a new helper `_gtin_pairs`, new lines in `context`, `build`, and
  `components`, the module docstring.
- `pipeline/pages/clusters.html`: one CSS line `.badge.gtin`.
- `tests/test_barcode_shared.py`: the tests of plan 58 change to the new order and the
  window.
- `tests/test_clusters.py`: a new test class.
- `README.md`, `ChangeLog.md`, `SMOKE_TESTS.md`.

## Risks

- The rebuild of `clusters.json` also takes in each other change of the index since the
  last build (2026-09-26T10:33). A cluster whose members change gets a new key. It has no
  rule until the rules build makes one.
- A wrong GTIN row joins two different wines in one cluster.
- A GTIN of N wines gives N*(N-1)/2 links and one cluster of N wines. A GTIN of more wines
  than `max_cluster_size` (50) stops the whole build with the message "raise the
  threshold", and that message does not name the cause (note of 2f [0e9cfe]). On
  2026-09-27 each shared GTIN has 2 wines.
- A GTIN wine with no current vector keeps the key `code` (plan 58). The step popup of
  `/runs` (`run_steps.py`) tests each candidate for `code`. So it shows such a photo as a
  fast exit of the code lookup. This fault exists since plan 58. This plan does not change
  `run_steps.py`.
- The runs before and after this plan are not equal for the photos of a shared GTIN.

## Result

Code done on 2026-09-27 by drink-atlas-workspace-4e [ff960b]. The rollout of requirement
22 was done at 20:10 to 20:22 (owner answer "Full rebuild now" of 20:09:06). Not
committed (owner answer "Leave it").

Rollout:

- Backups: `data/backups/clusters-naflex-p256-before-plan64-20260927T171003Z.json` and
  `data/backups/cluster-rules-naflex-p256-before-plan64-20260927T171003Z.json`.
- `build_clusters.py` at 20:10:14: 176 `combined` clusters. The GTIN clusters: `c022`
  (`1b446d041a52`, kind `full`, signals `full` and `gtin`: Belmas 122, Belmas 135, and
  `belmas-winery-viognier-katya-belmas-vione-beloe-suhoe-135`) and `c131`
  (`85432565966d`, kind `manual`, signals `manual` and `gtin`: the two Shato Pino Shiraz
  wines).
- `build_label_rules.py` from 20:11:08 to 20:20:47, exit 0: stage 1 had 40 cache hits and
  sent no call; stage 2 made 19 rules on QwenCloud (18 `sheet`, 1 `verdict`), 0 errors,
  157 rules restamped. The rule of `c131` has one vintage question: `-14` expects
  `2017`, `-135` expects `other`. The rule of `c022` asks for the name `Katya` and the
  spelling of the grape.
- 8168 restarted at 20:21:54 (pid 57108 -> 3472); `GET /api/dataset` answered 200. Only
  the plan 64 files were newer than the start of the old server. An embedding build that
  the old server started runs on (`start_new_session`).
- At 20:22 the artifact is stale again: after 20:10 the owner added 2 manual pairs and 5
  images. The GTIN pairs did not change.
- `recognize.py` on `barcode-rerank-siglip2-512-crop`, one VLM call for each photo:
  - The Belmas 122 photo with the EAN-13: the window holds Belmas 122 and Belmas 135 alone;
    the VLM answer "no Katya" keeps Belmas 122 at rank 1.
  - The test photo `shato-pino-shiraz-krasnoe-suhoe-14/03_manual.webp`, with and with no
    drawn EAN-13 `4680074271535`: the window holds the two Shato Pino Shiraz wines; the
    VLM reads the year `2022`, and the photo shows `SHIRAZ 2022`. So `-135` stays at rank
    1, as the rule of the owner says for a year other than 2017. The test set files this
    photo under `-14`.

- `Catalogue.rank(..., first=None)` sorts by (not in `first`, score, slug). With `first`
  empty or None, the order is the order before this plan. The `only` of plan 58 is gone.
- `CodeFirst.gtin_first` puts a wine of the GTIN with no vector after the ranked wines of
  the GTIN and cuts at `top_k`. The trace step `barcode` has `mode: first`.
- `RuleBook.trigger(candidates, window, first=None)` applies requirements 9 and 10.
  `ClusterRerank.rerank` calls `trigger` with two arguments when `first` is None, so a
  book with the old signature keeps working (`tests/test_pipeline_workers.py` has one).
- `clusters._gtin_pairs` reads the pairs. `manual_links` takes `by` (agreed with 2f
  [0e9cfe], option A). `components` gives the kind `gtin` and the signal `gtin`.
- Tests: `test_barcode_shared.py` 23 OK, `test_clusters.py` 27 OK (the plan 62 class
  unchanged), `test_cluster_rerank.py` 19 OK, `test_embedding_run.py` 38 OK,
  `test_rebuild_on_run.py` 17 OK (condition of c7 [09419d]), `test_pipeline_workers.py`
  4 OK. The full lab suite: 1,249 OK (5 skipped).
- A real photo (the Belmas 122 test photo `01_agent.webp` with a drawn EAN-13
  `4630171632036`) on `barcode-rerank-siglip2-512-crop` with `recognize.py`: `mode`
  `first`; Belmas 122 at rank 1 (0.9325), Belmas 135 at rank 2 (0.7247), then 8 other
  Belmas wines with scores from 0.8308 down. No step `cluster_rules`, because the present
  `clusters.json` has no cluster of the two wines.
- A read-only build in memory of the rules embedding (no file written): the present
  `clusters.json` (2026-09-26T10:33) is stale. A rebuild gives 176 `combined` clusters
  instead of 163. The GTIN links change one cluster: Belmas 122 joins `186bb11fa294`, which
  becomes the cluster `1b446d041a52` of 3 wines. The Shato Pino Shiraz wines already form
  the cluster `85432565966d` through the manual pair of the owner (plan 62); the GTIN link
  adds `gtin` to it. After the rebuild, 18 clusters have no rule: 49 cards, 37 with no
  stage 1 description. So the rules build makes about 37 calls to `qwen3.5-9b-nvfp4` and
  18 calls to `qwencloud-qwen3.8-max`.
