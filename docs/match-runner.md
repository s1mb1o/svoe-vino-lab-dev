# The match runner and the format of `runs/`

`scripts/match_run.py` sends every annotated photo to one **match backend** and writes
the answer into one directory under `runs_dir`. One directory is one run. The directories
are the history: two runs of two backends, or of two versions of one backend, stand next
to each other and are compared field by field.

```bash
python3 scripts/match_run.py --list-backends
python3 scripts/match_run.py --backend official-api
python3 scripts/match_run.py --backend organizers --limit 50 --label smoke
python3 scripts/match_run.py --dry-run
python3 scripts/match_run.py --backend svm-siglip2-448 --photos-dir ~/photos
```

The review tool shows the runs at `http://127.0.0.1:8154/runs`.

## The query set

The set is built from the files that the dataset of `config.yaml` names: `label_file`,
`photo_dir`, `excluded_slugs_file`, and `variant_groups_file`. `--dataset <name>`
chooses the dataset; the default is the one named `default`. Each dataset holds its own
`runs_dir`, so the runs of one dataset never stand in the table of another. `run.json`
records the dataset in `options.dataset`.

| Label | Count on 2026-09-17 | In the set | Truth |
|---|---|---|---|
| `positive` | 979 | yes | the slug of the directory |
| `negative` | 364 | yes | none; the answer MUST NOT be that slug |
| `variant` | 45 | only with `--variants` | the slug, or its variant group |
| `unusable` | 118 | no | — |
| no label (an agent proposal) | 264 | no | — |
| `no_match` | the files of `photo_dir/__null__/` | yes | none; the answer MUST be no answer |

A photo of an excluded slug never enters the set. Read `docs/excluded-slugs.md`.

A `no_match` photo comes from the directory `__null__`, the virtual NULL wine of the
review tool. No card of the catalogue shows that wine. The directory is the statement,
so the photo needs no label of its own; it stays out only when it carries `unusable`,
when it is marked for deletion, or when `__null__` stands in `excluded-slugs.json`.
`--only no_match` runs these photos alone, and `--only positive` and `--only negative`
leave them out.

The runner states two of these rules on the console, because neither is visible in
the counts of the query set:

- `variant photos:` states the effect of `--variants`. With `off` it states how many
  variant photos stay out. With `strict` and with `group` it states how many enter
  the set and which slug counts as a true match.
- `excluded slugs:` states how many slugs `excluded-slugs.json` holds and how many
  photos stay out because of them. The runner prints this line also when the count
  is 0, so an empty file is not read as a missing check.

The order is `sorted(image_path)`, so `query_id` is stable between two runs of the same
set. `image_path` is `<slug>/<file>`, relative to `photo_dir`.

## A plain directory of photos

`--photos-dir DIR` replaces the query set with the image files of one directory. Use it
to see what a backend answers for photos that the project holds no label for.

```bash
python3 scripts/match_run.py --backend svm-siglip2-448 --photos-dir ~/Downloads/photos
python3 scripts/match_run.py --backend official-api --photos-dir ~/photos --limit 20
```

The walk is recursive. A file enters the set when its extension is one of `.jpg`,
`.jpeg`, `.png`, `.webp`, `.gif`, or `.bmp`. A hidden file and a hidden directory stay
out. The order is `sorted(image_path)`, and `image_path` is the path of the file against
`DIR`.

Such a directory holds **no ground truth**. Every row carries:

| Field | Value |
|---|---|
| `label` | `unlabelled` |
| `slug` | `""` |
| `truth` | `[]` |
| `outcome` | `answered` when a candidate came back, `no_answer` when none did |
| `rank_of_truth` | `null`, always |

So the run states no correctness. `metrics.json` holds every share as `null`, and the
block `unlabelled` holds the counts that need no truth: `n`, `answered`, `no_answer`,
`errors`, `top_score_median`, and `score_margin_median`. `summary.md` holds a shorter
form for a person. The latency numbers are the same numbers as in any other run.

A high top score is not a proof of a correct answer. A person MUST read the photos at
`/runs` to judge the answers.

`--photos-dir` MUST NOT be used with `--from-run`, `--only`, or `--variants`. Each of
these three needs the labels of the project. The runner refuses the combination.

The name of the run directory carries the mark `dir`, for example
`2026-09-21T114536Z-svm-siglip2-448-dir-smoke`. `run.json` holds the directory in
`options.photos_dir`. The page `/runs` reads that field to serve the photos, so the
directory MUST stay in place while a person reads the run.

## The repeat of a run

`--from-run <run>` takes the photos of an earlier run that failed and asks the backend
about those photos only. Use it after a change of the recognizer: the answer to "did the
change help?" costs one request per failure instead of one per photo.

```bash
# every photo that was not correct at rank 1
python3 scripts/match_run.py --backend my-service --from-run runs/2026-09-17T133617Z-official-api

# every photo whose true slug was not in the first 10
python3 scripts/match_run.py --backend my-service \
  --from-run runs/2026-09-17T133617Z-official-api --rerun-depth 10

# only the positive photos that were not in the first 10
python3 scripts/match_run.py --backend my-service --only positive \
  --from-run runs/2026-09-17T133617Z-official-api --rerun-depth 10
```

`--rerun-depth K` states how many candidates count as an answer. The default is 1.

| Label | A photo is repeated when |
|---|---|
| `positive`, `variant` | the true slug was absent, or stood deeper than rank K |
| `negative` | its own slug DID come back inside rank K, because that slug is the wrong answer |
| any | the request failed: a timeout, an HTTP error, or an answer with no slug |

Raising K therefore repeats fewer positive photos and more negative photos. That is the
same rule read from both sides: inside K is where an answer counts, a positive photo MUST
be there, and a negative photo MUST NOT. Add `--only positive` when only the recall
matters.

The photo is matched by `image_path`, not by `query_id`. A `query_id` names a place in one
query set, and the set changes when a label changes; the path names the same photo in
every run. Each repeated photo **keeps the `query_id` of the earlier run**, so the two
`results.jsonl` files join on that field. The ids of a repeat run are therefore not
contiguous.

A photo of the earlier run that is no longer in the set, and a photo of the set that was
not in the earlier run, are both counted and printed. Neither enters the repeat.

### What a repeat run adds to its files

Every row of `results.jsonl` carries `previous`, which holds the `rank_of_truth`, the
`outcome`, and the `predicted_slug` of the earlier run.

`metrics.json` carries a `subset` block:

```json
"subset": {
  "based_on": "2026-09-17T133617Z-official-api",
  "rerun_depth": 1,
  "photos_in_earlier_run": 1343,
  "n": 507,
  "recovered_at_1": 122,
  "recovered_at_depth": 122,
  "still_failing": 385,
  "note": "Every photo of this run failed in the earlier run. …"
}
```

**The shares of a repeat run are not the shares of the set.** Every photo in it failed
before, so its `match_share` describes the failures only. The numbers to read are
`recovered_at_1`, `recovered_at_depth`, and `still_failing`. `run.json` states the same
in `based_on`, with the rule in plain words, and `summary.md` states it in the first
paragraph. The page `/runs` marks such a run with the tag `repeat d<K>` and puts the
warning above the cards, and each photo row states what the earlier run answered.

The name of the directory holds the mark too:
`2026-09-17T140501Z-my-service-repeat-d10-<label>`.

## The directory

The name is `<UTC time>-<backend id>[-<label>]`, for example
`2026-09-17T130947Z-official-api-smoke`.

| File | Content |
|---|---|
| `run.json` | What ran. |
| `queries.tsv` | The manifest, in the form of the jury harness. |
| `queries.jsonl` | The same rows with the truth of each photo. |
| `predictions.jsonl` | The answer in the format of the organizers. |
| `results.jsonl` | The full record of every photo. |
| `metrics.json` | The aggregate. |
| `summary.md` | The same numbers for a human. |

`--dry-run` writes `run.json`, `queries.tsv`, and `queries.jsonl` only.

### `queries.tsv`

The columns of the organizers: `query_id<TAB>image_path`, with that exact header. The
file works with the harness of the organizers without a change:

```bash
./participant_test.sh --images-dir dataset/my/photo \
  --manifest runs/<run id>/queries.tsv \
  --endpoint http://127.0.0.1:8080/v1/eval/predict --output /tmp/predictions.jsonl
```

### `queries.jsonl`

One JSON object per photo.

| Field | Type | Meaning |
|---|---|---|
| `query_id` | string | `q-000001`, and so on. |
| `image_path` | string | `<slug>/<file>`, relative to `photo_dir`. |
| `image_sha256` | string | The SHA-256 of the file. |
| `slug` | string | The directory of the photo. |
| `label` | string | `positive`, `negative`, or `variant`. |
| `truth` | array | The slugs that count as correct. Empty for a negative photo. |

### `predictions.jsonl`

**The format of the organizers, with no extra field.** This file is the submission.

```json
{"query_id":"q-000001","image_path":"kokur-suhoe-2025/01_conf095.jpg","image_sha256":"8d9c821e...","predicted_slug":"kokur-suhoe-2025","latency_ms":842}
```

| Field | Type | Meaning |
|---|---|---|
| `query_id` | string | The id of `queries.tsv`. |
| `image_path` | string | The path of `queries.tsv`. |
| `image_sha256` | string | The SHA-256 of the file that was sent. |
| `predicted_slug` | string or `null` | The Top-1 slug. `null` when no valid slug came back. |
| `latency_ms` | integer | The whole request, from the first byte sent to the last byte read. |

The rows stand in the order of the manifest. The file is written line by line, so an
interrupted run keeps the rows it already has.

### `results.jsonl`

One JSON object per photo. This is the file that the page at `/runs` reads.

| Field | Type | Meaning |
|---|---|---|
| `query_id`, `image_path`, `image_sha256` | | As above. |
| `slug` | string | The directory of the photo. |
| `label` | string | `positive`, `negative`, or `variant`. |
| `truth` | array | The slugs that count as correct. |
| `candidates` | array | Every candidate that came back, in the order of the answer. |
| `candidates[].slug` | string | The slug of the candidate. |
| `candidates[].score` | number or `null` | The score of the backend. `null` when the backend states none. A missing score is never read as a score of zero. |
| `candidates[].rank` | integer | 1 for the first candidate. |
| `predicted_slug` | string or `null` | The slug at rank 1. |
| `rank_of_truth` | integer or `null` | Where the true slug stands. For a negative photo it is where **its own slug** stands, which is a defect, not a success. |
| `outcome` | string | See the table below. |
| `latency_ms` | integer | The whole request. |
| `http_status` | integer or `null` | The HTTP status. `null` when the request never got an answer. |
| `error` | string or `null` | The failure: a timeout, an HTTP status, or an answer that holds no slug. |

The values of `outcome`:

| Value | Label | Meaning |
|---|---|---|
| `hit` | positive, variant | The true slug is at rank 1. |
| `miss` | positive, variant | The true slug is not at rank 1. |
| `no_answer` | any | No candidate came back. |
| `false_match_at_1` | negative | **The error.** The backend answered with the slug of a photo that shows a different wine. |
| `other_slug_at_1` | negative | Another slug came at rank 1. The photo may genuinely be that wine, so this is not verifiable and is not a success. |
| `false_match_in_top_k` | negative | Only with `--negative-strict`: the slug stands anywhere in the list. |

One slug keeps its first rank only. A backend that returns the same slug twice does not
get two chances.

### `metrics.json`

```json
{
  "run_id": "2026-09-17T130947Z-official-api",
  "backend": "official-api",
  "top_k": 10,
  "has_scores": true,
  "negative_strict": false,
  "queries": { "total": 1343, "positive": 979, "negative": 364, "variant": 0,
               "no_match": 0 },
  "positive": {
    "n": 979, "recall_at_1": 0.61, "recall_at_5": 0.74, "recall_at_10": 0.78,
    "mrr": 0.66, "no_answer": 12, "errors": 3,
    "rank_histogram": { "1": 597, "2": 61, "3": 34, "4-10": 42, "absent": 245 }
  },
  "negative": {
    "n": 364, "false_match_at_1": 18, "false_match_in_top_k": 44,
    "other_slug_at_1": 340, "no_answer": 6, "errors": 1,
    "slug_rank_histogram": { "1": 18, "2": 12, "4-10": 14, "absent": 320 },
    "false_match_scores": { "median": 0.71, "max": 0.88 }
  },
  "no_match": {
    "n": 24, "rejected": 9, "false_match_at_1": 15, "rejection_rate": 0.375,
    "errors": 0, "false_match_scores": { "median": 0.58, "max": 0.74 }
  },
  "latency_ms": { "median": 842, "p95": 1930, "max": 4100, "comparable": true },
  "wall_s": 1180
}
```

### The numbers that the specification of the task asks for

`docs/task-10-specification.pdf` of the hackathon names four measures. The runner
computes each one, and the page shows them in the first row of the cards.

| Field | Where | What the specification says |
|---|---|---|
| `positive.match_share` | section 2, section 7.1 | "процент совпадения с контрольной выборкой". The target is 90 to 100 percent. `target_match_share` holds the target, so a reader needs no second document. It is the same number as `recall_at_1`, under the name of the task. |
| `positive.f1_at_1`, `positive.f1_at_5` | section 2.3, section 4 | "F1 в поисковой выдаче для топ-1 и топ-5 карточек". Each block holds `precision`, `recall`, and `f1`. A service that answers every photo gets precision = recall = F1. A service that abstains answers fewer photos, and then the three differ. `f1_at_5` is `null` when the backend returns fewer than 5 candidates. |
| `latency_ms.within_sla`, `within_sla_share` | section 2 | "Целевое время ответа (SLA) — до 3 секунд". `sla_ms` holds the limit of 3000 ms. |
| `positive.near_duplicate_confusion` | section 2 | "много near-duplicates... Именно они главный источник ошибок". The count of the wrong answers whose slug stands in the variant group of the true wine. The count uses `variant-groups.json` whatever `--variants` says. |
| `positive.score_margin` | section 2 | "отрыв между 1-м и 2-м результатом должен быть ощутимым". The median difference between the score of the first and of the second candidate, for the correct answers and for the wrong answers apart. A wrong answer with a large margin is a confident error, which is the worst kind. |

The block `no_match` is `null` when the set holds no such photo. `rejection_rate` is
`rejected / n`: the share of the photos that the backend refused, which is the only
correct outcome for them. `false_match_scores` holds the score that a wrong answer
reached. A threshold that MUST refuse these photos stands above `max`.

Rules that a reader MUST know:

1. `recall_at_5` and `recall_at_10` are `null` when `top_k` is smaller than the k. A
   backend that answers Top-1 cannot be measured at 5, and a zero would be a lie.
2. `rank_histogram` answers "how far from R@1". The key `absent` counts the photos whose
   true slug never came back. With a Top-1 backend every miss lands in `absent`.
3. The `negative` block never states a success. Only `false_match_at_1` is proven.
   `other_slug_at_1` is unverifiable, because the reviewer stated which wine the photo is
   **not**, and did not state which wine it **is**.
4. `false_match_scores` holds the score of the wrong Top-1 answers. Compared with the
   scores of the true positives it states whether a confidence threshold would remove
   these errors without a cost in recall.
5. `latency_ms.comparable` is `false` when the run used more than one worker. Only a serial
   run is comparable to the harness of the organizers, which sends one request at a time.
6. `has_scores` is `false` when no candidate carried a score. A run without scores is
   never read as a run with a score of zero.

### `run.json`

| Field | Meaning |
|---|---|
| `run_id` | The name of the directory. |
| `tool` | The script that wrote the run. |
| `started`, `finished`, `wall_s` | The time of the run. |
| `git_commit` | The commit of this repository at the time of the run. |
| `options` | Every command line option. |
| `backend` | The definition of the backend, **with the secrets redacted**. A header value `env:NAME` keeps the name; any other header value becomes `(redacted)`. |
| `config` | Every path of `config.yaml`, resolved. |
| `query_set`, `left_out` | The counts of the set, and why a photo stayed out. |
| `answered` | How many photos got an answer. A smaller number than `query_set.total` means that the run stopped early. |

## The page at `/runs`

`scripts/review_server.py` answers `/runs`. The header holds the navigation `Review`
and `Runs` at the top right. `Review` opens `/`, the page of the photo review.
The page holds three parts:

1. **The table of the runs.** One row per directory: the backend, the time, R@1, R@5,
   R@10, the false matches, and the median latency. A click opens the run. The address
   holds the run id after `#`, so a run is a link.
2. **The metrics.** The cards hold R@1, R@5, R@10, MRR, and the error counts. Two
   histograms follow: the rank of the true slug for the positive photos, and the rank of
   the own slug for the negative photos.
3. **The photos.** One row per photo: the photo at the left, and the candidates at the
   right, the highest score first. Each candidate shows the catalogue bottle photo of its
   slug, its rank, and its score.

### A run of a plain directory

A run of `--photos-dir` holds no ground truth. The page states it above the cards: it
names the photo count, the count with a candidate, the count with none, the errors, the
median top score, and the median gap to the second candidate. Every share stands as a
dash, because no share can be computed. A dash here is not a failure of the backend.

No candidate carries a green or a red border in such a run, because no slug is expected
and no slug is forbidden. The photo comes from `/img/runphoto?id=<run>&file=<path>`,
which reads `options.photos_dir` of `run.json`. `/img/photo` never leaves `my/`, so it
cannot serve these photos. The photos MUST stay in that directory while a person reads
the run.

The filter of the page keeps `all`. Every other filter selects by a label or by a rank,
so it keeps no row of such a run. The order `score_desc` is the useful one: the answers
that the backend is most sure of stand first.

The colours of a candidate:

| Border | Meaning |
|---|---|
| Green | The expected slug. A dashed green card at the front of the strip states that the expected wine never came back. |
| Red | The slug of a negative photo: the wine that the answer MUST NOT hold. |
| Dashed green | The true wine of a negative photo. Read the next section. |
| None | Any other candidate. |

The filter of the page selects what to look at: every photo, the misses, the photos whose
true slug stands at rank 2 or deeper, the photos whose true slug stands at rank 2 to 5,
the photos whose true slug is not in the top 5 or not in the top 10, the photos whose true slug never came back, the false matches of the
negative photos, the negative photos whose wrong wine stands above the true wine, the
photos that a defect of the set marks, or the failed requests.

The filters `after_5` and `after_10` read "not in R@5" and "not in R@10": a true slug that
never came back is in, because it counts as a failure at every depth. That is the rule of
`failed_before()`, which `--from-run` and `--rerun-depth` use. The filter `near` keeps the
older reading and leaves such a photo out. The filter `rank_2_5` keeps the reading of
`near` as well: it holds the photos whose true slug came back at rank 2 to 5, which is the
band that R@5 wins and R@1 loses.

### The true wine of a negative photo

A negative photo states one wine that the photo does NOT show. It states no wine that the
photo does show, so `outcome` alone cannot say whether the answer was good.

One photo file often stands in the set two times: `positive` for the wine that it shows,
and `negative` for a wine that it does not show. The two rows hold the same
`image_sha256`, because the bytes are equal. The server reads that pair and gives the
negative row the slug of its positive twin. The page then marks the true wine with a
**dashed green** frame, and the run can be read in full: the true wine SHOULD stand above
the wine that the negative label forbids.

The comparison uses the first rank of a slug, which is the rule of `judge()`.

| `twin.verdict` | Meaning |
|---|---|
| `above` | The true wine stands above the forbidden wine. The answer is good. |
| `below` | The forbidden wine stands above the true wine. **The error.** The row carries the tag `negative_above_positive` and the filter of the same name selects it. |
| `no_forbidden` | The forbidden wine never came back. Nothing contradicts the true wine. |
| `absent` | The true wine never came back. A dashed green card stands after the answer, apart from it. |
| `null` | The photo has no positive twin in this run. |

The index reads one run only. A photo whose twin was not in that run gets no twin here.
A run made with `--only negative` or with a small `--limit` therefore shows fewer twins
than the whole set holds. The label `variant` is left out of the index: it groups the same
wine in another bottle and states no truth about the photo.

**The defect of the set.** One photo can be `positive` for one wine only. Two positive
slugs on one photo, or the same slug both `positive` and `negative`, is a defect of the
set. The field `twin.conflict` marks the rows of such a photo, the row carries the tag
`twin_conflict`, and the filter of the same name selects them, so the reviewer can repair
the set by hand. Until the set is repaired, the page marks every true wine of the group
with the dashed green frame. The check `shared_positive` of the review page finds the same
defect over the whole photo set, not over one run.

The field `twin` is added by the server when it reads a run. It is not written to
`results.jsonl`, so an old run gets the marks as well.

**The order of the runs.** A click on a column of the table of the runs sorts by that
column. A second click on the same column turns the order around. The run, the time, and
the backend start at the newest or the last; every number starts at the smallest. The
order is made in the browser, so it costs no request.

**The order of the photos.** The control `Sort` orders the rows. The order is made by the
server before the rows are cut into pages, so it holds over the whole run and not over
the 100 rows on the screen.

| Value | Order |
|---|---|
| `manifest` | The order of the run, which is the order of `queries.tsv`. The default. |
| `worst` | The most wrong first: a false match of a negative photo, then a true slug that never came back, then the deepest rank. |
| `rank` | The rank of the true slug: 1 first, then deeper, then the photos whose true slug never came back. |
| `score_desc`, `score_asc` | The score of the answer at rank 1. A row with no score stands last in both orders. |
| `latency_desc`, `latency_asc` | The time of the request. |
| `path` | The path of the photo, A to Z. |

`GET /api/run` takes the same value in `sort`. An unknown value is refused and the answer
names every accepted value.

## `backends.yaml`

One entry defines one recognizer. `--backend <id>` selects it.

| Key | Required | Default | Meaning |
|---|---|---|---|
| `id` | yes | — | The name for `--backend`, for the directory name, and for `metrics.json`. It MUST be unique. |
| `label` | no | the `id` | Free text for a human. |
| `url` | yes | — | Where the POST goes. |
| `field` | no | `image` | The name of the multipart field that carries the image. The jury harness sends `image`. |
| `response` | no | `auto` | How to read the answer: `auto`, `slug-object`, `slug-array`, or `candidates`. A fixed value refuses the other shapes, so a backend that changes its answer fails loudly. |
| `query` | no | none | Query-string parameters. The official API needs `limit`. |
| `top_k` | no | `1` | How deep the tool scores: `recall@k`, the histograms, and `--negative-strict` stop here. |
| `timeout_s` | no | `30` | One request. |
| `workers` | no | `1` | How many requests this server takes at the same time. `--workers N` wins over it. |
| `headers` | no | none | Extra HTTP headers. A value `env:NAME` is read from the environment variable `NAME`. |

**A token MUST NOT stand in this file.** Use `env:NAME`. `run.json` records the header
name and redacts the value.

The accepted answers of `response: auto`:

| Shape | Source |
|---|---|
| `{"slug": "..."}` | the contract of the jury |
| `[{"slug": "..."}, …]` | the present official API |
| `{"data": [...]}`, `{"items": [...]}`, `{"results": [...]}`, `{"wines": [...]}`, `{"matches": [...]}` | a wrapped list |
| `{"candidates": [{"slug": "...", "score": 0.93}]}` | a list with a score |

A score is read from `score`, `confidence`, `similarity`, `sim`, or `probability`.

## Options of the runner

| Option | Meaning |
|---|---|
| `--backend <id>` | The backend. Required, except with `--dry-run`. |
| `--dataset <name>` | The dataset of `config.yaml` to match against. The default is the dataset named `default`. An unknown name stops the runner and names every dataset of the file. |
| `--list-backends` | Print every backend of `backends.yaml` and stop. |
| `--limit N` | Stop after N photos. Use it for a trial run. |
| `--photos-dir DIR` | Match the image files of this directory instead of the photo set of the project. The walk is recursive. The directory holds no ground truth, so the run states no correctness. Not allowed with `--from-run`, `--only`, or `--variants`. |
| `--only positive\|negative\|all` | Take one kind of photo only. |
| `--variants off\|strict\|group` | Take the variant photos into the set. `strict` accepts the own slug; `group` also accepts a slug of the variant group. The default is `off`. |
| `--negative-strict` | Count the slug anywhere in the top-k as a false match. |
| `--workers N` | Run N requests at once. Without it, the key `workers` of the backend decides, and 1 is the last default. The latency of a run with more than one worker is NOT comparable to the jury harness, and `metrics.json` states it. |
| `--from-run <run>` | Repeat only the photos that failed in that earlier run. Takes the directory or its `results.jsonl`. |
| `--rerun-depth K` | With `--from-run`: how many candidates count as an answer. The default is 1. |
| `--label <text>` | A word for the name of the directory. |
| `--dry-run` | Build the query set and the manifests. Call nothing. |
