# Active work of the sessions

This file shows the present work of each agent session of this project. The rules are in
[AGENTS.md](AGENTS.md), section "Work of the sessions". In short:

- Read this file before you change a file.
- Keep one section for your session. Change your own section alone.
- Do not change a file that another section lists. Send that session a message.
- Remove your section when your work is committed.

The form of a section:

```text
## <session name>

- Task: <one line>
- Source: <a plan, or the time of an owner message>
- Files: <the paths or globs that this session changes>
- State: active | waiting: <reason>
- Updated: <local time in ISO 8601>
- Agreements: <the agreements with other sessions, if any>
```

## drink-atlas-workspace-39 [fb59ad]

- Earlier name: drink-atlas-workspace-43 [58637c] (the same conversation after a reload).

- Task: (1) done: safeguard A of the cluster build (limits of links and of the largest
  cluster). (2) the thresholds and the limits come from a new block `clusters:` of
  `config.yaml`; the page `/clusters` has no threshold input.
- Task (4): the key `min_cluster_size` of the block `clusters:` of `config.yaml`: the build
  stores no smaller cluster; the input "Minimum size" of `/clusters` goes away. Owner
  message of 2026-09-26T01:04:00+0300, answer of 01:05:00. Files: `pipeline/clusters.py`,
  `pipeline/pages/clusters.html`, my block of `config.yaml`, `tests/test_clusters.py`,
  `tests/test_build_clusters.py`, `tests/test_cluster_routes.py`,
  `docs/plans/30_embedding-clusters.md`. A restart of 8168. State: done. 29 cluster tests
  OK; 8168 restarted by 39 at 01:06:21 (pid 89346); a live build from the config gave
  `min_cluster_size: 2` in `settings` and the same clusters; 15 browser checks pass.
- Task (3): each header control of `/dataset`, `/embedding`, `/clusters`, `/testset`,
  `/runs` (selects, number inputs, search boxes) is stored in `localStorage` on change and
  restored at page load. A URL value wins; a stored value that is no longer a choice is
  ignored. Code in each page; no server change, no restart. Owner message of
  2026-09-26T00:30:00+0300, answers of 00:33:00. Files: separate hunks (the header
  state code, one start-up call) in `pipeline/pages/dataset.html`,
  `pipeline/pages/embedding.html`, `pipeline/pages/clusters.html`,
  `pipeline/pages/testset.html`, `pipeline/pages/runs.html`. Agreed (about 00:33 to
  00:35): 6a (embedding, runs, testset), 28 and e2 (testset; e2 keeps `svl.testset.sidebar`,
  `setSide`, `initSide`), ab (runs; keep `evenCards`), cb (dataset; keep its `init` lines).
- Source: owner messages of 2026-09-25T23:00:00+0300, 23:10:30, the answer "A", the answer
  "2" of 2026-09-26T00:06:30, "define limits in config" of 00:16:00, the answers of
  00:19:00 (one global block; limits and thresholds), and 00:20:00 (no thresholds in the UI).
- Files: `docs/owner-messages.md` (append), `pipeline/clusters.py`,
  `pipeline/build_clusters.py`, `pipeline/cluster_routes.py`, `pipeline/pages/clusters.html`
  (the threshold inputs, the build request, the summary; the owner asked for this UI
  change, the section a9 is stale), `tests/test_clusters.py`, `tests/test_cluster_routes.py`,
  `tests/test_build_clusters.py`, `docs/plans/30_embedding-clusters.md`. After agreement:
  `config.yaml` (a new block `clusters:` after the `embeddings:` list), the cluster
  paragraph of `COMMANDS.md`, one bullet in `ChangeLog.md`, one row in `SMOKE_TESTS.md`.
  A restart of 8168. Done: the rebuild of the clusters of
  `gx10-siglip2-so400m-patch16-naflex-p256` at 0.95 / 0.95 (00:07:14, 1.0 MB).
- State: done, not committed. The section stays until the commit (rule 20). Task 2 is
  live since the restart of 8168 by d3 at 00:36:23 (a build request with a threshold
  answers HTTP 400; the page has no threshold input). Task 3: the five pages pass a
  Playwright check (restore after reload, the URL wins, an unknown stored set gives the
  default set, no page error). An address with a view key restores no stored view
  control (a missing key is the default; proposal of 28, applied in `testset.html` and
  for the image of `clusters.html`); 14 checks pass. Open: the owner decides on the `ChangeLog.md` bullet and
  the `SMOKE_TESTS.md` rows (stale sections 5c, a9, 3b).
- Updated: 2026-09-26T01:37:40+0300
- Agreements: 15 [40dc83] (now drink-atlas-workspace-cb [395cc7]) agreed at about 23:28
  to one separate bullet under its bullet in `ChangeLog.md` and one new row in
  `SMOKE_TESTS.md`; its bullet and its rows S11 and DT9 to DT12 stay as they are. 15
  restarts 8168 near 23:29 for its own change. d3 [4920ce] adds its own separate bullet
  in `ChangeLog.md` and row in `SMOKE_TESTS.md`; 39 agreed (request after 23:44).
  drink-atlas-workspace-43 [c33611] (a new session, not the earlier name of 39) adds the
  heading `## 2026-09-26` with one bullet in `ChangeLog.md` and row IW17 in
  `SMOKE_TESTS.md`; 39 agreed (request after 00:00).
  ab [539687], 6a [792d65], d3 [4920ce], cb [395cc7] agreed (about 00:20 to 00:23) to the
  new block `clusters:` of `config.yaml` after the `embeddings:` list (6a, d3, cb) and to
  the cluster paragraph of `COMMANDS.md` (ab, 6a, d3). d3 restarts 8168 and deploys this
  code with it.
  28 [5ddfae] removes `, "#slugsel"` from the line `HEADER_IDS` of `testset.html` in the
  same edit as its removal of the select `Slugs` (owner message of 00:39:13); 39 agreed.
  28 [5ddfae] (plan 37, `#wine` becomes `#cluster`) reads the consts `HEADER` and
  `URL_VIEW` of the block of 39 in its own hunk of `load`; 39 does not rename them.
  d3 [4920ce] changes the label `every run` to `All` in `renderConfigs` of `runs.html`
  and the comment above it (owner answer of 01:19:00); 39 agreed.
  43 [c33611] changes the job rows of `embedding.html` (`.job`, `.job-stop`, `showJobs`;
  owner message of 01:24:00) and adds its own README.md, SMOKE_TESTS.md (EB41 to EB43),
  and ChangeLog.md hunks; 39 agreed.
  43 [c33611] changes the job rows of `testset.html` (`.job`, `.job-stop`, `showRunJobs`;
  owner message of 01:32:00) with its own README.md, SMOKE_TESTS.md, ChangeLog.md hunks;
  39 agreed.
  e2 [9e7fe4] adds plan 38 hunks to `runs.html` (candidate card, large view of the
  catalogue items; owner message of 01:23:11); 39 agreed.
  d3 [4920ce] adds plan 39 hunks ("Use caches": `#run-cache` in the Run dialog of
  `testset.html`, the tag `no cache` in `runs.html`; owner answers of 01:32:00); 39 agreed.
