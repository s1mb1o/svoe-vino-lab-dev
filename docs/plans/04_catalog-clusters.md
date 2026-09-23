# 04 — Catalogue clusters

Date: 2026-09-22.
Status: implemented on 2026-09-22. The project owner selected the four decisions below.
The section "Changes during the implementation" states what the measurement changed.

## Goal

Find the groups of catalogue cards that the matcher confuses, or can confuse.
Show these groups on a new page of the review tool.
A later re-rank step reads the same file.
Read `ideas/rerank-duplicate-catalog-cards.md` in the workspace root for that step.

## Decisions

| Question | Options | Decision | Reason |
|---|---|---|---|
| Link signals | several signals with evidence; names only; two layers | several signals with evidence | One signal alone misses a class of pairs. The names miss the look-alike lines. The photos miss `abrau-dyurso-pino-nuar-krasnoe-suhoe-12`. |
| Scope | the whole catalogue; the wines of `my/` only | the whole catalogue | The re-rank needs the cluster of every card. This includes a card with no test photo. |
| Page | view only; view and edit | view only | The first version shows the clusters. Edits come in a later version. |
| Placement | a new script and a new file; extend `08_variants.py` | a new script and a new file | `variant-groups.json` and the main table stay as they are. |

## The links

A link joins two cards. A link records every signal that passed.

| Signal | Rule | Source |
|---|---|---|
| `name` | The same producer, the same name, and the same category after normalisation. The words of the producer are removed from the name. The grapes of one card MUST be a subset of the grapes of the other card, or one field MUST be empty. | `catalog.jsonl` |
| `photo` | The SigLIP 2 cosine of the two catalogue photos is at or above `photo_threshold` (0.95). | the matcher index of the whole photo, an `.npz` file |
| `label` | The SigLIP 2 cosine of the two label crops is at or above `label_threshold` (0.95). | the matcher index of the label crops, an `.npz` file |
| `confusion` | For positive photos of card A, a match run answered card B at rank 1. The count over both directions and all runs is at or above `min_confusions` (2). | `results.jsonl` of each configured run |

Normalisation: lower case, `ё` becomes `е`, only the letters and the digits stay.
The name words become a sorted set, so a change of word order gives the same key.
A card whose name holds no word after the removal gets no `name` key.

A confusion counts only when the current label file still marks the photo `positive`
for card A. An old run can hold a label that a reviewer changed later.

The script reads the vectors of the matcher index. It does not call gx10.
An index can hold more than one vector for one card. The cosine of two cards is then
the highest cosine over their vectors.

## The clusters

- A cluster is a connected component over every link.
- A cluster holds 2 or more cards. A card is in at most one cluster.
- `kind` has three values:
  - `same-wine`: the `name` links alone connect every card of the cluster.
  - `look-alike`: the cluster holds no `name` link.
  - `mixed`: all other clusters.
- The cluster id is the position in the sort order of the file. The id is not stable
  between two builds. The page addresses a cluster through a member slug:
  `/clusters#<slug>`.

The choice of the owner said "same wine when a name link exists". A cluster can hold a
`name` link and a `photo` link to a third card. The value `mixed` names that case.

## The file

`svoe-vino-testset/dataset/catalog-clusters.json`. `config.yaml` names the path.

```json
{
  "version": 1,
  "built_at": "2026-09-22T23:40:00+0300",
  "settings": {"photo_threshold": 0.95, "label_threshold": 0.95, "min_confusions": 2},
  "inputs": {"catalog_file": "...", "photo_index": {"file": "...", "built_at": "..."},
             "label_index": {"file": "...", "built_at": "..."},
             "label_file": "...", "runs": [{"id": "...", "used": 0, "stale": 0}]},
  "counts": {"cards": 2103, "clusters": 0, "cards_in_clusters": 0,
             "kinds": {}, "links": {}, "sizes": {}},
  "clusters": [
    {"id": "c001", "kind": "same-wine", "size": 3,
     "signals": ["confusion", "name", "photo"],
     "slugs": ["..."],
     "confusions": 0,
     "links": [{"a": "...", "b": "...", "by": ["name", "photo"],
                "name": "same", "photo": 0.9772, "label": 0.9107,
                "a_as_b": 0, "b_as_a": 0, "photos": []}]}
  ]
}
```

`photo` and `label` of a link hold the cosine also when that signal did not pass.
`by` names the signals that passed. `name` of a link is `same` when the `name` signal
passed, `grapes-differ` when the two cards share one name key and the grapes disagree,
and null for two name keys. `a_as_b` counts the positive photos of `a` that a run
answered as `b`. `photos` holds at most 6 of these photos.

## The page

- `GET /clusters` is the page. `GET /api/clusters` answers the file and one record for
  each card of a cluster.
- The card record holds the name, the producer, the category, the grapes, the page URL,
  the `patched` mark, the `has_label` mark, and the label counts of the active dataset.
- The route reads the file at each request. A new build needs no restart.
- The page shows one block for each cluster: the catalogue photos side by side, the card
  fields, and a table of the links with their evidence.
- The page holds filters for the kind, the signal, the size, and a text search. It holds
  a sort and the image selector `package / label`.
- A member links to `/#<slug>` of the review page and to the catalogue page.
- A click on an image opens a large view. `Left` and `Right` move inside the cluster.
  `Up` and `Down` move to the same place in the previous or the next cluster. The owner
  asked for this on 2026-09-22, after the first version.
- The page follows the system colour scheme. It uses `THEME_CSS`.
- The page writes nothing.

## Steps

1. Write `scripts/10_clusters.py`. Measure the link counts and the cluster sizes. Set
   the default values from the measurement.
2. Add the `clusters` block to `config.yaml`. Read it in `scripts/common.py`.
3. Add `GET /api/clusters` and `GET /clusters` to `scripts/review_server.py`. Add the
   link `Clusters` to the navigation of every page.
4. Update `docs/openapi.yaml`, `docs/API.md`, `README.md`, `SMOKE_TESTS.md`,
   `ChangeLog.md`, and `ResearchLog.md`.
5. Check the page in the light theme and in the dark theme, on a second port.

## Risks

- Chaining. A chain of links can join a whole product line into one cluster. The
  measurement of step 1 states the size of the largest cluster.
- A stale index. The name of an index file holds a digest. A rebuild of the index
  writes a new name, so `config.yaml` MUST name the new file. The page states the
  build time of each index.
- Noisy test labels. One image is a positive photo of three cards (see the workspace
  `ResearchLog.md`, 2026-09-22). Its confusions join those cards, which is correct for
  this purpose.

## Changes during the implementation

The measurements are in `ResearchLog.md`, 2026-09-22.

1. The `name` signal got the grape rule. 32 of 107 name pairs held different grapes,
   and 15 of them are different wines of one line under one name, such as the line
   «Иноходец» of «Вина Арпачина». The rule keeps 92 pairs.
2. `min_confusions` is 2, not 1. With 1 the largest cluster held 38 cards, and the Pinot
   Noir cards stood in a cluster of 21 Abrau-Durso cards. With 2 the largest cluster
   holds 10 cards, the same as with no confusion signal.
3. `name` of a link holds three values, not a boolean, so the page can state
   `grapes differ`.

The result with the defaults: 255 clusters over 630 cards, the largest of 10 cards;
53 `same-wine`, 22 `mixed`, 180 `look-alike`.

## Later

- Attributes of each card, such as the vintage and the alcohol value. This is the
  difference list of the re-rank step.
- Review actions on the page: confirm a cluster, split a cluster.
