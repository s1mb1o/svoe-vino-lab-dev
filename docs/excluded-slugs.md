# Excluded slugs

`excluded-slugs.json` names the wine slugs that are out of the benchmark.
The photos of an excluded slug MUST NOT be used for benchmarking.
A slug that is not in the file is included.

The path of the file is the value of `excluded_slugs_file` in `config.yaml`.
The default value is `svoe-vino-testset/excluded-slugs.json`.

## Why the file exists

Some slugs of the `vino-svoe.ru` catalogue hold an error.
The most frequent error is a wrong bottle photo: the picture of the card shows a
different wine.

The bottle photo of the slug is the reference of the benchmark.
A wrong reference makes every correct answer look wrong and every wrong answer look
correct. The measure of such a slug is noise, and the noise shifts the metrics of the
whole test set.

A defect of the source catalogue is not repaired in this project. The slug is excluded
instead. The benchmark then stays comparable between two runs, because the excluded
set is explicit and is under version control.

Read `docs/catalogue-defects.md` for the register of the known catalogue defects.
An excluded slug SHOULD also stand there.

## Format

```json
{
  "version": 1,
  "updated": "2026-09-17T15:18:40+0300",
  "note": "…",
  "count": 2,
  "excluded": {
    "abrau-dyurso-brut-rose-reserve-beloe-bryut-12": {
      "reason": "wrong bottle photo in the catalogue: the card shows the white brut",
      "ts": "2026-09-17T15:18:40+0300"
    },
    "another-slug-119": {
      "reason": "the card joins two different wines under one slug",
      "ts": "2026-09-17T15:41:02+0300"
    }
  }
}
```

| Field | Type | Meaning |
|---|---|---|
| `version` | integer | Version of the format. The present version is `1`. |
| `updated` | string | Time of the last write, ISO 8601 with the offset. |
| `note` | string | The rule and the purpose, in plain words, for a reader and for an LLM. |
| `count` | integer | Number of the entries in `excluded`. |
| `excluded` | object | Map of the excluded slugs. The key is the slug. |
| `excluded.<slug>.reason` | string | Why the slug is excluded. The field MUST NOT be empty. |
| `excluded.<slug>.ts` | string | Time of the exclusion, ISO 8601 with the offset. |

Rules:

1. The key MUST be a slug that has a directory in `my/`.
2. `reason` MUST state the error. `wrong bottle photo` alone is enough, but a short
   description of the error is better.
3. The file is written with sorted keys and 2 spaces of indent. A hand edit MUST keep
   this form, so a difference in `git` stays small.
4. The reader MUST accept the short form `"<slug>": "<reason>"` as well. The tool reads
   it and writes the long form at the next change.
5. A missing file means that no slug is excluded.

## How a slug is excluded

Use the review tool:

```bash
python3 scripts/review_server.py --no-browser
```

Each wine row holds an `Exclude` button under the bottle photo of the left column.

1. Press `Exclude`. The tool asks for the reason.
2. State the error and confirm. The row turns red and the button reads `Excluded`.
3. The tool writes `excluded-slugs.json` at once.

Press `Excluded` again to put the slug back in the benchmark. The tool asks for a
confirmation and then removes the entry.

The control `Slugs` in the header bar filters the table:

| Value | The table shows |
|---|---|
| `all` | Every wine. This is the default value. |
| `included` | Only the wines that are in the benchmark. |
| `excluded` | Only the excluded wines. |

## How a consumer MUST use the file

A benchmark, a report, or an export MUST read the file and MUST skip every photo of an
excluded slug. The photos stay on the disk in `my/<slug>/`. The file does not delete
them, because the labels of the reviewer keep their value for other work, such as the
training of a model.

The agent API follows the same rule:

- `GET /api/v1/wines` does NOT list an excluded wine. Add `include_excluded=1` to see
  it.
- `GET /api/v1/wine/<slug>` holds the fields `excluded` and `exclude_reason`.
- `GET /api/v1/stats` holds `excluded_wines` and `excluded_photos`.

Read `docs/API.md` for the whole agent API.

## Example: read the file in Python

```python
import json

with open("excluded-slugs.json", encoding="utf-8") as fh:
    excluded = json.load(fh)["excluded"]

def in_benchmark(slug):
    """Answer whether the photos of the slug are used for benchmarking."""
    return slug not in excluded
```
