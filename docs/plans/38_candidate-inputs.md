# Plan 38: the catalogue inputs of a candidate of an embedding run

Date: 2026-09-26

Source: owner message of 2026-09-26T01:23:11+0300 and the answers of 01:29:00.

## 1. Goal

A run of a pipeline of the backend `embedding` (plan 33, plan 34) ranks the wines with the
cosine of the query vector and the catalogue vectors. The owner wants to see, for one
candidate of one photo, each catalogue input of that wine that went to the model, and the
cosine that the run got for it.

## 2. Owner choices

1. A click on a candidate card opens the large view. The rail under the image shows the
   catalogue inputs of that wine. A click on the query photo stays as it is: the rail
   shows the model input of the photo.
2. The run records the cosine of each item. The page does not compute a cosine.
3. The rail shows each item of the wine in the index. An item of a view that the query
   does not have shows "not compared" and no cosine. The best item of each view gets a
   mark.

## 3. Facts

1. The index of an embedding entry holds one item for each catalogue image and view. The
   file `data/embeddings/<name>/images/<source_sha256>_<view>.png` holds the exact PNG
   bytes that went to the model (`build_embeddings.run` writes the bytes and sends the
   same bytes). The route `/embeddings/<name>/images/<sha256>_<view>.png` serves it.
2. A build writes the file again when the steps of a view change. The item gets a new
   `embedding_hash`. So the file of an old run is gone when the hash changed.
3. Before this plan, a candidate held `slug`, `score`, `rank`, and the best cosine of each
   view of the query. It did not name the item of the best cosine.
4. Most wines have one catalogue image. The index gives them two items: `full` and
   `label`. The pipeline `siglip2-p256-as-is` has the query view `full` alone, so only the
   `full` items were compared.

## 4. The run file

`embedding_run.Catalogue.rank` adds the key `items` to each candidate. The key holds
each current item of the wine in the index of the run, in the view order of the entry.
Inside a view, the highest cosine is first. Each item holds:

| Key | Value |
|---|---|
| `sha256` | the `source_sha256` of the catalogue image |
| `view` | the view of the item in the index |
| `type` | the image type of the wine column, for example `main` or `main_patched` |
| `embedding_hash` | the `embedding_hash` of the item in the index of the run |
| `cosine` | the cosine to the query vector of the same view, 4 decimals; null when the query has no vector of this view |

The other keys of a candidate do not change. `Catalogue.__init__` builds the rows of each
wine one time, so `rank` does not search the rows for each candidate.

`/api/run` removes `items` from its rows. The page reads the items with the new route.

## 5. The route

`GET /api/run-candidate?id=<run>&query=<query id>&slug=<slug>` answers:

- `run`, `query`, `slug`, `score`, `views` (view -> the best cosine of the candidate),
  `items`, `notes`.
- Each item holds the keys of section 4, and `best`, `state`, `url`, `width`, `height`.
- `best` is true for the item whose cosine equals the best cosine of its view.
- `state` is `same` when the present index holds the item with the same
  `embedding_hash`. Then `url` names the PNG, and the PNG is the input of the run.
  `changed` means another hash, and `gone` means no item. Then `url` is null, because the
  input of the run is no longer on disk.
- A run from before this plan has no `items`. The route then lists the items of the wine
  in the present index, with `cosine` null and `state` `current`, and adds a note.
- A run that is not of the backend `embedding` gets no item and a note.

`embedding_run.candidate_items` builds the answer. `run_routes.candidate_view` finds the
row and the candidate.

## 6. The page

1. The candidate image gets `data-cand` with the slug. The row gets `data-query-id`.
2. For a run of `kind: embedding`, the large view of a candidate image calls the route
   and fills the rail. The first element is a note with the score and the best cosine of
   each view. Each item shows its PNG, the view, the cosine, and the image type. The
   best item gets the badge `best`. A "not compared" item is dim. An item with no file
   shows a text card.
3. A click on an item shows its PNG large, as for a model input of the query photo.
4. For another run, the rail of a candidate stays empty, as before.

## 7. Tests

`tests/test_embedding_run.py`: the key `items` of a run with two views and of a run of
the as-is pipeline; the route for a new run, for an index that changed, for an old run,
for an unknown slug; `/api/run` sends no `items`. The three present checks of the key set
of a candidate get `items`.

## 8. After the code

1. A restart of 8168 for the route.
2. The run `2026-09-25T220722Z-lab-siglip2-p256-as-is-my` has no `items`. A new run of the
   pipeline records them. The owner decides when to start it.

## 9. Result

Done on 2026-09-26.

1. `embedding_run.py`: `Catalogue.__init__` keeps the item of each matrix row and the rows
   of each wine; `Catalogue.items_of` and `Catalogue.rank` write `items`;
   `candidate_items` builds the answer of the route.
2. `run_routes.py`: the route `/api/run-candidate` (`candidate_view`); `run_view` removes
   `items`.
3. `runs.html`: `data-cand` on a candidate image, `data-query-id` on a row, `RUN`,
   `loadCandInputs`, `renderCandInputs`, and their CSS. The notes of the strip of a
   candidate take the text colour, because the old note colour is not readable in the
   light theme.
4. 33 tests of `tests/test_embedding_run.py` pass (9 new). A probe run of 30 queries on
   the set `my` recorded the items with the real index. 30 browser checks pass on a test
   copy on port 8175 in both themes. The page scrolls sideways at a width of 390 px also
   with the large view closed; that is older than this plan.
5. A finding: the photo `q-000001` of the set `my` is also the `main_patched` image of
   `fanagoriya-100-ottenkov-krasnogo-kaberne-kaberne-sovinon-krasnoe-suhoe-135`. The
   package cut of that file gets the cosine 0.8141 to the photo as it is, so the wrong
   wine takes rank 1.
