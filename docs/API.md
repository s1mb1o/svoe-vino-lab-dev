# The agent API of the review tool

`scripts/review_server.py` answers an HTTP API under `/api/v1/`. An agent uses it to
read the wines, to look at the pictures, and to propose a photo for a wine.

The server MUST be running:

```bash
python3 scripts/review_server.py --no-browser      # http://127.0.0.1:8154
```

Every write goes through this one server, so a write of the agent and a click of the
reviewer cannot overwrite one another.

## The rule of the proposals

An agent MUST NOT write a label. A label is the decision of the reviewer.
An agent writes a **proposal**: the photo lands in `my/<slug>/` as `NN_agent.<ext>`,
and its entry holds `proposed`, `by`, `confidence`, and `source_url`.

A proposal is not counted in `labelled`. The card shows a dashed border and a tag with
the confidence. The reviewer opens the filter `holds a photo proposed by an agent` and
answers with the keys `1` to `4`. Only then the photo has a label.

## Read

### `GET /api/v1/stats`

```json
{ "wines": 844, "photos": 2023,
  "excluded_wines": 3, "excluded_photos": 7,
  "counts": { "positive": 534, "negative": 203, "unusable": 61, "variant": 0,
              "labelled": 798, "proposed": 0, "commented": 15, "wine_notes": 2 },
  "variant_groups": 28 }
```

`excluded_wines` and `excluded_photos` count the wines and the photos that are out of
the benchmark. Read `docs/excluded-slugs.md`.

### `GET /api/v1/wines`

| Parameter | Meaning |
|---|---|
| `filter` | `all`, `unlabelled`, `needs_positive`, `has_proposal`, `fully_labelled`, `in_variant_group` |
| `q` | a part of the slug, the name, or the producer |
| `limit` | 1 to 500, default 50 |
| `offset` | default 0 |
| `include_excluded` | `1` also lists the excluded wines. The default value leaves them out. |

`needs_positive` is the work list of an agent: the wines with no confirmed photo.

An excluded wine is out of the benchmark, so the list leaves it out. An agent MUST NOT
hunt photos for such a wine. Read `docs/excluded-slugs.md`.

```json
{ "total": 571, "offset": 0, "limit": 50, "wines": [ { "slug": "...", "name": "...",
  "producer": "...", "photos_total": 1, "labels": {...}, "unlabelled": 0,
  "proposed": 0, "bottle_path": "/Volumes/...", "bottle_url": "/img/bottle?slug=...",
  "variant_group": null, "wine_note": "",
  "excluded": false, "exclude_reason": "" } ] }
```

`excluded` states that the photos of this wine are NOT used for benchmarking.
`exclude_reason` states the error of the card, most often a wrong bottle photo.

### `GET /api/v1/wine/<slug>`

The same record with `description` and with `photos`. Each photo holds:

```json
{ "file": "01_conf095.jpg",
  "path": "/Volumes/.../my/<slug>/01_conf095.jpg",
  "url": "/img/photo?slug=<slug>&file=01_conf095.jpg",
  "conf": 95, "label": "positive", "proposed": null, "by": null,
  "confidence": null, "source_url": null, "comment": null,
  "reassign_to": null, "moved_from": null }
```

`path` is an absolute path on this machine. An agent reads the picture from the path
with its own file tool; the bytes do not travel through the API.

`variant_group` names the wines that hold the same wine in another bottle, with the
path of each bottle photo. Read it before a decision: the photos of two variants
differ only in a small detail.

### `GET /api/v1/wine/<slug>/photos?label=positive`

Only the photos with that label. Leave `label` out for every photo.

### `GET /img/bottle?slug=<slug>` and `GET /img/photo?slug=<slug>&file=<file>`

The picture itself, for a browser. An agent SHOULD use `path` instead.

## Write

### `POST /api/v1/propose`

```json
{ "slug": "agora-risling",
  "url": "https://otzovik.com/.../photo.jpg",
  "proposed": "positive",
  "confidence": 0.91,
  "source_url": "https://otzovik.com/review_1234.html",
  "comment": "the label and the capsule match the catalogue bottle",
  "by": "claude-code" }
```

The server fetches the address, stores the picture as `NN_agent.<ext>`, and writes the
proposal. `confidence` MUST be between 0 and 1. `proposed` MUST be `positive`,
`negative`, `unusable`, or `variant`.

The address MUST be `http`, `https`, or a `data:` URL. An `http` or `https` address
MUST NOT resolve to a local or a private address. The media type is always read from
the first bytes of the file, not from the address and not from the server header.

A `data:` URL is the way to propose a picture from a host that the server cannot
fetch: a host that blocks this machine, or a host that omits its intermediate
certificate. Fetch the bytes yourself, then send
`"url": "data:image/jpeg;base64,<base64>"`. This also proves that the stored file is
the file the agent judged. Keep the page address in `source_url`, because the `url`
field then holds the data URI and not an address.

Answer: `{ "ok": true, "slug": ..., "file": "07_agent.jpg", "photos": [...],
"counts": {...} }`.

## The other routes

These belong to the page, and an agent MAY use them:

| Route | Work |
|---|---|
| `POST /api/label` | `{slug, file, label}`; the decision of the reviewer |
| `POST /api/comment` | `{slug, file, text}`; a note about one photo |
| `POST /api/wine-comment` | `{slug, text}`; a note about a whole wine |
| `POST /api/reassign` | `{slug, file, to}`; record that a photo belongs to another slug |
| `POST /api/fetch-image` | `{slug, url}`; add a picture without a proposal |
| `GET /api/reload` | read `my/` again after the pipeline wrote it |

An agent SHOULD use `/api/v1/propose` and NOT `/api/label`.

## Errors

Every error answers a JSON object with one field `error`. The status is `400` for a
bad request, `404` for an unknown wine or route, `502` when the embedding service
fails, and `503` when the index is absent.
