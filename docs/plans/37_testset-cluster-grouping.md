# 37 — Group the wines of `/testset` by the clusters of an embedding

Date: 2026-09-26.
Status: approved. The owner selected the four recommended options on
2026-09-26T00:46:18+0300.

## Source

Owner message of 2026-09-26T00:42:25+0300:

```text
Wine: [    ] -> Clusters: [ No / embedding #1 / .... ] <- show wines groupped by clusters. 

Other filters are applied too
```

## Decisions

1. The select `Clusters` (`#cluster`) takes the place of the select `Wine` (`#wine`).
   The values `in a variant group` and `removed from the catalogue` go away. The tag
   `variant group of N`, the sort `variant group first`, and the badge `Removed` stay.
2. The first option is `No` (value `all`). Each other option is one embedding of
   `config.yaml` that has a `clusters.json`. The text is
   `<embedding> (<N> clusters)`, with `, stale` when `GET /api/clusters` states that the
   inputs changed after the build.
3. The page uses the view `combined` alone.
4. With an embedding selected, the table lists only the wines that are in a cluster of
   that view and that pass the other filters (`Progress`, `Verdict`, `Marks`, `Find`).
   A wine in no cluster is hidden. A cluster can show in part.
5. The rows of one cluster stand together. A cluster takes the place of its first row in
   the present sort order. Inside a cluster, the rows keep the sort order.
6. A header row stands above each cluster:
   `<id> · <shown> of <size> wines shown · <signals>` and the link `open on /clusters`.
   `<id>` is the `id` of the cluster, for example `c001`, the same as on `/clusters`.
   `<signals>` is `full`, `label`, or `full + label`. The link opens
   `/clusters?name=<embedding>&space=combined#<first slug>` in a new tab.
7. A wine with no photo in the set shows in its cluster when `Progress` is `all`. The
   other filters hide it, as before.
8. The row `No Match` stays the first row. It is not part of a cluster.
9. The count line adds `· <K> clusters of <embedding>`.

## Data

- `GET /api/clusters` gives the list. The page reads it one time, at the first load.
- `GET /api/clusters/<name>` gives the clusters (`artifact.spaces.combined.clusters`,
  about 1.3 MB, 0.2 s for the present file). The page reads it at the first use of that
  embedding and keeps it until the next page load.
- No server route changes. No restart of 8168 is necessary.

## Address and storage

- The address key `cluster` replaces `wine`. An old address with `filter=grouped` or
  `filter=removed` opens with `Clusters` on `No`. An old address with `wine=…` alone
  holds no key of `VIEW_PARAMS`. So the page ignores the key and restores the stored
  view, as for an address with no view key (the rule of session 39).
- `#cluster` is in `FILTER_AXES`. So the resets of `showGroup` and `openFromHash`, the
  `change` listener, and the localStorage block of session 39 (`HEADER_IDS`) take it.
  `render` gives `matchFilter` the three other axes alone.
- The options of `#cluster` arrive after the start-up restore of session 39. So
  `load(…, true)` fills the options first, then applies the stored value (when the
  address holds no view key), then runs `readViewFromUrl`.

## Files

- `pipeline/pages/testset.html`: the select, `FILTER_AXES`, `matchAxis`, `render`, a new
  block for the cluster data and the header row, `VIEW_PARAMS`, `load`, CSS for
  `tr.cl-head`.
- `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`.

## Changes

Owner message of 2026-09-26T01:06:36+0300 and the answers of 01:08:49:

1. `Sort` gets `cluster size, largest first` (`cluster_size`). With an embedding in
   `Clusters`, the clusters stand by the size of the whole cluster, the largest first. A
   tie goes by the cluster id. Inside a cluster, the rows go by slug. With `Clusters` on
   `No`, the option is disabled. A stored or linked `cluster_size` then gives `slug`.
2. The button `Additional settings` (`#more-btn`) shows or hides a second row (`#more`)
   with `Marks` and `Clusters`. The button shows `· N` when N of the two are not at
   their default. The key `svl.testset.more` of localStorage keeps the open state. The
   ids of the selects and the address keys do not change.
