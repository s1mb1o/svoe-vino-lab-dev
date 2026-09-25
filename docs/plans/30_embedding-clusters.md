# 30 — Embedding-dependent clusters

Date: 2026-09-25.
Status: approved for implementation on 2026-09-25. The owner selected option 1.

## Goal

1. Re-enable the Clusters page of the lab server.
2. Build clusters from one selected lab embedding.
3. Store each cluster artifact in the directory of that embedding.
4. Keep `full` and `label` as separate similarity spaces.
5. Let every indexed image contribute in its applicable space.
6. Build a combined graph from the union of the `full` and `label` edges.
7. Store the exact source images that produced each edge.
8. Define the later VLM difference-rule contract.

## Sources reviewed

The design uses the findings and code of these projects:

- `svoe-vino-testset/scripts/10_clusters.py`;
- `svoe-vino-testset/scripts/cluster_rules.py`;
- `svoe-vino-testset/docs/plans/04_catalog-clusters.md`;
- `svoe-vino-testset/docs/plans/05_cluster-label-rules.md`;
- `svoe-vino-testset/docs/plans/06_label-only-cluster-rules.md`;
- `svoe-vino-matcher/svm/index.py`;
- `svoe-vino-matcher/svm/config.py`;
- `svoe-vino-matcher/svm/cluster_rules.py`.

The matcher can store more than one vector for one wine. It ranks the best vector of
each wine. The old cluster builder also used the highest cosine over all vectors of two
wines.

The matcher keeps package and label indexes separate. The old cluster builder kept
`photo` and `label` as separate edge signals. It joined the two signals only in the
component graph.

## Measurement of the current lab embedding

The measurement used
`data/embeddings/gx10-siglip2-so400m-patch16-naflex-p256` and cosine threshold `0.95`.

| Space | Edges | Clusters | Cards | Largest cluster |
|---|---:|---:|---:|---:|
| `full` | 214 | 147 | 334 | 6 |
| `label` | 154 | 108 | 244 | 8 |
| union | 274 | 168 | 397 | 8 |

Only 94 edges occur in both spaces. The two spaces carry different information.

The database held three additional images at the time of the measurement. These images
created no new edge at threshold `0.95`. This small set does not measure the future
effect of additional images.

## Decisions

### D1. One artifact belongs to one embedding

The directory `data/embeddings/<name>/` holds these files:

```text
clusters.json
cluster-notes.json
cluster-rules.json
```

This plan writes `clusters.json` and `cluster-notes.json`.

This plan reads `cluster-rules.json` when that file exists. This plan does not call a
VLM to write rules. Plan 29 owns the detailed image descriptions that the rule builder
will use. A later implementation will write the rule builder after that data contract
is stable.

A cluster rebuild MUST replace `clusters.json` alone. It MUST NOT delete the notes or
the rules.

### D2. Effective main image

For one wine, `main_patched` replaces `main`. The two images MUST NOT both enter a
cluster build.

This is the same input rule as an embedding build.

### D3. Additional images

Every indexed additional image contributes.

- `full_front` and `full_back` contribute to `full` and `label`.
- `label_front` and `label_back` contribute to `label` alone.

This rule makes the cluster graph agree with the candidate space of the embedding.
An additional image can be the best vector of a wine. The cluster builder MUST not hide
that possible retrieval result.

### D4. Separate similarity spaces

The builder MUST compare `full` vectors with `full` vectors alone.

The builder MUST compare `label` vectors with `label` vectors alone.

The builder MUST NOT compare a `full` vector with a `label` vector.

The combined graph uses the union of the two edge sets.

### D5. Best image pair of a wine pair

One wine can have more than one vector in one space. For each pair of wines, the edge
similarity is the highest cosine over their vectors in that space.

The edge stores both source SHA-256 values and both image types that produced this
highest value.

This evidence lets the page show whether a main image or an additional image created
the edge.

### D6. Thresholds

The initial threshold is `0.95` in each space. This value comes from the old measured
SigLIP 2 cluster build. It is not calibrated for every embedding model.

Changed on 2026-09-26 (owner messages of 00:16:00 to 00:20:00): the block `clusters` of
`config.yaml` holds `full_threshold` and `label_threshold`. The page has no threshold
input. The button "Build clusters" sends no threshold, and the route
`POST /api/clusters/<name>/build` refuses a body with a threshold (HTTP 400). The command
`pipeline/build_clusters.py` takes the values of the block; its options
`--full-threshold` and `--label-threshold` replace them for one build. A missing key of
the block takes `0.95`. A build stores both values in `clusters.json`. The summary of the
page shows them.

Each threshold MUST be a finite number from `-1` through `1`.

### D6a. Build limits

The owner chose this safeguard on 2026-09-25 (option A).

A build with full threshold `0.5` gave 2,055,813 full links, one cluster of 2,045 wines,
and a 5 GB `clusters.json`. Each page request parsed the whole file. The page was not
usable.

- A build MUST stop when one vector space has more than `MAX_LINKS` (20,000) wine pairs.
  The search checks the count after each row. So a too-low threshold does not fill the
  memory.
- A build MUST stop when one of the three views has a cluster with more than
  `MAX_CLUSTER_SIZE` (50) wines. This limit also stops a chain of links.
- A build that stops writes no file. The old `clusters.json` stays. The page shows the
  error of the build request (HTTP 400).
- The keys `max_links` and `max_cluster_size` of the block `clusters` of `config.yaml`
  set the two limits (owner answer of 2026-09-26T00:19:00: one global block). A missing
  key takes the value of `CONFIG_DEFAULTS` in `pipeline/clusters.py`. The page and the
  command have no option for them. An unknown key of the block, or a value that is not
  valid, stops the build.

Measurement on 2026-09-25, SigLIP 2 lab embedding:

| Thresholds | Full links | Largest cluster | Result |
|---|---:|---:|---|
| `0.95` / `0.95` | 214 | 8 (`combined`) | pass |
| `0.9` / `0.9` | 1,264 | 24 (`full`, `combined`) | pass |
| `0.85` / `0.85` | — | 184 (`full`) | stop |
| `0.5` / `0.95` | more than 20,000 | — | stop |

Options that were not selected:

- A size check before the page reads `clusters.json`. It protects the page from a large
  file that exists already.
- Storage of fewer links, for example a spanning tree for each cluster. A cluster of
  2,045 wines stays useless.
- A minimum threshold. D6 states that `0.95` is not calibrated for every model. A fixed
  minimum can block a valid threshold of another model.

### D7. Components

An edge passes when its cosine is at or above the threshold of its space.

A cluster is a connected component with at least `min_cluster_size` wines. The key
`min_cluster_size` of the block `clusters` of `config.yaml` sets it; a missing key is
`2` (owner message of 2026-09-26T01:04:00+0300, answer of 01:05:00: the build drops the
smaller components). The page has no input "Minimum size". The counts of a view count
the stored clusters alone; `links` counts every link of the view. `min_cluster_size`
MUST NOT be more than `max_cluster_size`. `settings` of `clusters.json` stores it.

The file stores the components of three views:

- `full` uses only `full` edges;
- `label` uses only `label` edges;
- `combined` uses the union of both edge sets.

A wine can occur in one component of each view.

The cluster key is the first 12 hexadecimal digits of the SHA-1 of the sorted wine
slugs. It is stable while the members stay equal.

The displayed cluster id is its position in the current sort order. It is not stable.

### D8. No catalogue-name or benchmark-confusion edge

This artifact holds embedding edges alone.

The old cluster file also held `name` and `confusion` edges. A `confusion` edge depends
on selected test runs. It does not belong to one embedding artifact. A catalogue-name
edge carries no embedding evidence.

The Runs page MAY show benchmark confusions as an overlay later. Such an overlay MUST
NOT silently change `clusters.json`.

## Input identity and stale status

The cluster input hash is the SHA-256 of canonical JSON with these values:

- the embedding name;
- the vector file name;
- the vector dimension;
- each indexed item: source SHA-256, view, role, embedding hash, and row;
- each current assignment: wine slug, image type, and source SHA-256.

The thresholds do not enter the input hash. They stay in the build settings.

The page recomputes the input hash without reading the vector matrix. The artifact is
stale when the current input hash differs from the stored input hash.

The file also records the vector file, the embedding update time, and the counts of
the indexed and excluded items.

The cluster builder MUST refuse a build while the embedding build holds its lock.

An indexed item that is stale against the current database input MUST NOT contribute.
The artifact records the counts of current, stale, missing, and failed items. A build
can complete with failed or missing items. The page MUST show these counts.

## `clusters.json`

The file has this shape:

```json
{
  "version": 1,
  "embedding": "gx10-siglip2-so400m-patch16-naflex-p256",
  "built_at": "2026-09-25T20:00:00+0300",
  "input_hash": "<64 hex>",
  "inputs": {
    "index_file": "index.json",
    "vectors_file": "vectors-12345678.npy",
    "updated_at": "...",
    "dim": 1152,
    "status": {"current": 4039, "stale": 0, "missing": 0, "failed": 4}
  },
  "settings": {"full_threshold": 0.95, "label_threshold": 0.95},
  "spaces": {
    "full": {"counts": {}, "clusters": []},
    "label": {"counts": {}, "clusters": []},
    "combined": {"counts": {}, "clusters": []}
  }
}
```

One cluster has these fields:

```json
{
  "id": "c001",
  "key": "0123456789ab",
  "kind": "mixed",
  "size": 3,
  "signals": ["full", "label"],
  "slugs": ["wine-a", "wine-b", "wine-c"],
  "links": []
}
```

`kind` is `full`, `label`, or `mixed`. In a single-space view, the value equals the
space. In the combined view, `mixed` means that the component has both edge signals.

One link has one record per available signal. The signal record holds the similarity,
the source SHA-256 and image type on each side, and each prepared-image URL.

## Notes

`cluster-notes.json` stores notes by their cluster key. A note also stores the slugs of
the cluster at the time of the write.

After a rebuild, an exact cluster key gets its exact note. If no exact key exists, the
page MAY assign the old note with the largest member overlap. The page marks that note
as inherited. A write under the new key does not delete the old note.

A note has at most 4,000 Unicode characters.

Every note write is atomic. A file lock serializes writers.

## Routes

The lab server gets these routes:

| Method | Route | Result |
|---|---|---|
| GET | `/clusters` | the page |
| GET | `/api/clusters` | the embedding configurations and their artifact status |
| GET | `/api/clusters/<name>` | one artifact with current card and image data |
| POST | `/api/clusters/<name>/build` | build `clusters.json` with the two thresholds |
| POST | `/api/clusters/<name>/note` | write or clear one cluster note |

The build route runs in the request thread. The lab server uses
`ThreadingHTTPServer`, so other requests continue. A cluster lock prevents two builds
of one embedding at the same time.

The build route returns HTTP 201 after the file is complete. It returns HTTP 409 when
an embedding build or another cluster build runs.

## Page

The Configuration control selects one embedding entry. The URL query `name` keeps the
selection.

The Space control selects `combined`, `full`, or `label`. The URL query `space` keeps
the selection.

The page shows:

- the artifact path and stale status;
- the embedding update time and vector file;
- the item-status counts;
- the thresholds and the Build clusters button;
- filters for size and text;
- one block per cluster;
- every wine and each model input that belongs to the selected space;
- each edge, its cosine, its signal, and the exact winning image pair;
- the note editor;
- an existing difference rule when `cluster-rules.json` holds one.

The hash `#<slug>` opens and scrolls to the component of that wine.

The page follows the system light or dark theme.

## VLM difference rules

The rule builder runs offline. It MUST NOT discover cluster differences during each
match request.

The rule builder uses one current cluster and one rule space. The current matcher sends
a label crop at query time. Its rules therefore use the `label` rule space.

A future full-package reranker MUST use a separate `full` rule. A rule MUST NOT ask for
a feature that its query image does not show.

### Offline input

For each wine, the rule builder receives:

- the typed prepared images of the rule space;
- the effective main image and applicable additional images;
- the detailed image descriptions from plan 29;
- the catalogue name, producer, category, colour, grapes, and region;
- the reviewer note;
- a caption that identifies an image reused by more than one wine.

The VLM sees the images and the descriptions. The descriptions alone are not trusted.

### Offline answer

The answer is one JSON object:

```json
{
  "differences": "short summary",
  "questions": [
    {
      "id": "q1",
      "question": "What grape name is printed on the label?",
      "kind": "text",
      "answers": {"wine-a": "РИСЛИНГ", "wine-b": "ШАРДОНЕ"},
      "evidence": {"wine-a": ["<sha256>"], "wine-b": ["<sha256>"]}
    }
  ],
  "indistinguishable": []
}
```

The code validates each question.

- At least two wines MUST have two different non-null expected answers.
- An expected answer MUST name its supporting image evidence.
- A label rule MUST use printed label features alone.
- A label rule MUST reject glass, liquid, capsule, cork, and bottle-shape features.
- Every rule MUST reject bottle numbers, serial numbers, batch numbers, and lot numbers.
- A vintage value MUST follow the current catalogue vintage policy.
- A design, colour shade, font, or pattern SHOULD NOT be a discriminator unless the
  reviewer note explicitly allows it.

`cluster-rules.json` has one map for each rule space. The key of one rule in that map is
the cluster key. Thus the same member set can have different `label` and `full` rules.
One rule stores the cluster input hash, the prompt version, the model entry, the complete
prompt, the raw reply, the validated questions, and any validation error. A rule is
stale when one of these inputs changes.

```json
{"version": 1, "spaces": {"label": {"<cluster-key>": {}}, "full": {}}}
```

### Query prompt

The query-time VLM gets one query image and the validated questions. Each question
lists only its allowed answers, plus `other` and `not visible`.

The query-time prompt MUST state:

- inspect the label alone;
- report only visible evidence;
- do not guess;
- choose from the listed options;
- answer `not visible` when the feature is absent or unreadable.

The query answer maps each question id to one option. An equal answer adds evidence for
a wine. A different visible answer removes evidence. `not visible` changes no score.
If no wine wins, the base embedding order stays unchanged.

This two-stage design follows the measured `cluster_rules` pipeline of
`svoe-vino-matcher`. It avoids a new difference-discovery call for each query.

## Implementation files

- `pipeline/clusters.py`: input identity, similarities, components, files, and notes.
- `pipeline/build_clusters.py`: the command line build.
- `pipeline/cluster_routes.py`: the page API.
- `pipeline/pages/clusters.html`: the page.
- `pipeline/lab_server.py`: route delegation and removal of the disabled page.
- `tests/test_clusters.py`: graph, image roles, evidence, stale status, and notes.
- `tests/test_build_clusters.py`: command line and file integration.
- `tests/test_cluster_routes.py`: API and page routes.
- `tests/test_lab_server.py`: lab server delegation.

## Verification

1. Run the new unit and route tests.
2. Run all lab tests.
3. Build clusters for the current NaFlex embedding.
4. Compare the result with the direct measurement in this plan.
5. Restart the lab server on port 8168 with SIGTERM.
6. Check `GET /api/dataset` for HTTP 200.
7. Check the page in light and dark themes.
8. Check a cluster that has a `full` edge and a cluster that has a `label` edge.
9. Check the configuration and space query parameters.
10. Check a note write and clear.

## Risks

- A threshold has a different meaning for another embedding model. The page records the
  values and lets the owner change them.
- A high-similarity additional back image can join product lines through common legal
  text. The stored source evidence makes this edge visible for review.
- Connected components can chain through several edges. The page shows every edge.
- An incomplete embedding produces an incomplete graph. The page shows every excluded
  item count.
- A later label-cut rebuild makes the embedding and its clusters stale. The page MUST
  not present stale artifacts as current.
