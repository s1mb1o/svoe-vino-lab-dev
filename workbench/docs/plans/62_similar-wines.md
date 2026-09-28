# Plan 62: the manual relation `similar` between two wines

Date: 2026-09-27

Source: owner message of 2026-09-27T15:12:00+0300 and the owner answers of 15:22:00
(`docs/owner-messages.md`).

## Goal

A person marks two wines as similar on `/dataset`. The relation has no direction: the
pair shows on the card of each wine. The cluster build of each embedding
(`pipeline/clusters.py`, plan 30) uses each pair as one more link.

## Decisions of the owner

1. A pair is a forced link of the union-find build. When a cluster holds one wine of a
   pair, the other wine joins that cluster. When the two wines are in two clusters, the
   two clusters become one cluster. Each wine stays in one cluster.
2. A pair of two wines that are in no vector cluster makes a cluster of 2 wines.
3. The pairs go to each view: `full`, `label`, and `combined`.

## Data

Schema file `pipeline/schema/NNN_wine_similar.sql`. The number is fixed at the entry of the
file (rules 25 and 26 of `AGENTS.md`). The next free number on 2026-09-27T15:25 is 028.

```sql
CREATE TABLE wine_similar (
    wine_slug_a TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    wine_slug_b TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    created_at  TEXT NOT NULL CHECK (created_at GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
    PRIMARY KEY (wine_slug_a, wine_slug_b),
    CHECK (wine_slug_a < wine_slug_b)
) STRICT;
CREATE INDEX wine_similar_b ON wine_similar (wine_slug_b);
```

- One row is one pair. The smaller slug is always in `wine_slug_a`. So one pair has one
  row, and the pair (A, B) is the same pair as (B, A).
- `created_at` is the UTC time of the mark, as `wine_favorite.created_at`.
- A wine of each state MAY have a pair. The cluster build uses only the pairs of two
  wines that the build knows (item 12).

## Module `pipeline/similar_wines.py`

4. `pair(slug, other)` returns the stored order `(a, b)`. Two equal slugs raise
   `SimilarError`.
5. `partners(conn, slug=None)` returns wine slug -> the list of its partner slugs, in rowid
   order. A wine with no pair has no key.
6. `pairs(conn)` returns the sorted list of `(a, b)`.
7. `count(conn)` returns the number of pairs.
8. `add(conn, slug, other, now=None)` adds one pair. A pair that exists raises
   `DuplicateError`.
9. `remove(conn, slug, other)` removes one pair. It returns False for a pair that does
   not exist.

## Routes of the lab server

10. `POST /api/dataset-similar` with the body `{"slug", "other"}` adds one pair.
    `DELETE /api/dataset-similar?slug=&other=` removes one pair.
    - The answer: `ok`, `slug`, `other`, `similar` (the partners of `slug`),
      `other_similar` (the partners of `other`), `total` (the number of pairs), and
      `added` or `removed` (the stored pair).
    - HTTP 400: no slug, no other slug, or two equal slugs.
    - HTTP 404: a wine that does not exist, or a DELETE of a pair that does not exist.
    - HTTP 409: a POST of a pair that exists.
11. `GET /api/dataset` sends `similar_editor: true` and `similar_pairs` (the number of
    pairs). Each record holds `_similar`: the list of the partner slugs.

## The cluster build

12. `clusters.context` reads the pairs. It keeps a pair only when both wines are in the
    wines of the build (`embeddings.read_inputs`: the Active wines with at least one
    image).
13. The identity of the input hash gets the key `similar` (the kept pairs) only when there
    is at least one kept pair. So the hash of an artifact with no pair does not change,
    and an existing `clusters.json` stays current after the deploy. A change of the kept
    pairs makes the artifact stale on `/clusters`.
14. `clusters.build` adds each kept pair to the links of each view. A pair that has a
    vector link already gets `manual` in its list `by`. Another pair gets a new link
    `{"a", "b", "by": ["manual"], "spaces": {}}`.
15. `components` adds `manual` to `signals` when a link of the cluster is manual. The key
    `kind` keeps its vector meaning (`full`, `label`, or `mixed`). A cluster with manual
    links alone has the kind `manual`.
16. `max_cluster_size` applies to the clusters with manual links too.

## The pages

17. `/dataset`: each card has the editor `Similar wines` after the editor
    `Atlas Core product`. It lists the partners: the slug as a link to the card, the name,
    and a remove button `×`. The button `+` opens an input with a list of the wine slugs
    of the page. Enter or the save button adds the pair. Escape or the cancel button
    closes the input. A save or a remove draws again the cards of both wines. The page
    shows the editor only when `GET /api/dataset` sends `similar_editor`, so the review
    tool keeps its page.
18. `/clusters`: the Signal column shows the badge `manual`. The badge has its own colour
    in the light and the dark theme.

## Effects on other parts

19. A cluster that gets a new member gets a new key (`cluster_key`). Its note is inherited
    by the member overlap, as today. Its label rule is lost until
    `pipeline/build_label_rules.py` runs again. The re-rank (plan 48) has no rule for that
    cluster until then. The same happens today after each change of the images.
20. A change of a pair does not start a build. The owner builds the clusters on
    `/clusters`.

## Deploy

21. The entry of the schema file, the migration of `data/lab.sqlite3` with
    `pipeline/labdb.py`, and the restart of 8168 belong together (rule 27).

## Tests

22. `tests/test_similar_wines.py`: the module functions.
23. `tests/test_lab_server.py`: the routes and the key `_similar` (a new class at the end).
24. `tests/test_clusters.py`: a pair merges two clusters; a pair of two wines with no
    link makes a cluster of kind `manual`; a pair with a wine that is not in the build is
    ignored; the input hash with no pair does not change.
25. `tests/test_labdb.py`: VERSION and the table list.
26. Smoke tests SW1 and later in `SMOKE_TESTS.md`.

## Result

Done on 2026-09-27. Schema 028 was entered and migrated at 15:46:57. 8168 was restarted
at 15:47 (pid 47252). The full suite gives 1,223 tests OK (5 skipped). A browser check on
a scratch server with a copy of the database passed 19 of 19 checks. A check on 8168 with
the writes mocked passed 5 of 5. A build on the real vectors of
`gx10-siglip2-so400m-patch16-naflex-p256`, in memory, put a wine with no cluster into
cluster c001 of the view `combined` (8 -> 9 wines).

## Note of 2026-09-27: the name `Hard cases`

The owner message of 2026-09-27T23:11:41+0300 states that a pair holds two wines that are
hard to distinguish (hard cases), not two similar wines. The answers of 23:15:34 chose the
visible name `Hard cases` and a change of the visible text alone. The editor of `/dataset`,
its tooltips, its alerts, and its confirmation say `Hard cases` or `hard case`. The
identifiers keep the name `similar`: the table `wine_similar`, the route
`/api/dataset-similar`, the keys `_similar` and `similar_pairs`, the module
`similar_wines.py`, the key `similar` of the cluster build, and the CSS classes. So the
input hash of the clusters does not change. The error texts of the server keep the word
`similar`.
