# ResearchLog

What was learned while this project was built. `ChangeLog.md` records what was done.

## 2026-09-23 — the positive photos of Primum Alveus Brut 2014 show the vintage 2017

Status: observation. No label was changed. The owner decides about the labels.

- `dataset/my/review-labels.json` marks four photos of
  `fanagoriya-primum-alveus-brut-2014-shardone-igristoe-bryut-beloe-12` as `positive`:
  `02_manual.webp` to `05_manual.webp`. The time stamps are 2026-09-18 07:49:39 to
  07:49:43. `01_conf090.jpg` is `negative`.
- Each of the four photos shows the vintage 2017:
  - The front label on `02_manual.webp`, `03_manual.webp`, and `05_manual.webp` prints
    «2017» and the numeral `VII`.
  - `04_manual.webp` shows the back label. It prints «ГОД УРОЖАЯ – 2017».
- The catalogue picture of the 2014 card prints «2014» and the numeral `V`. The
  catalogue picture of `fanagoriya-primum-alveus-brut-2017-shardone-igristoe-bryut-beloe-12`
  prints «2017» and the numeral `VI`.
- Run `2026-09-23T050800Z-svm-label-gw-ensemble-hardcase-base` puts the 2017 card at
  rank 1 for `02_manual.webp` (q-000999) and `05_manual.webp` (q-001002). The run counts
  both answers as misses. The 2014 card is at rank 5.
- If the four labels are wrong, R@1 is too low for this group. A vintage rule that
  selects the 2017 card for these photos is then counted as an error.

## 2026-09-23 — the start of the review tool waits on a loaded T7 drive

Symptom: `python3 scripts/review_server.py` printed the configuration report. Then it
printed nothing for more than 45 s. The process did not hang. At 87 s after the start,
it listened on `127.0.0.1:8154` and answered HTTP 200.

### Where the time goes

A `sample` of the process at about 45 s after the start put 2,654 of 2,660 samples in
`stat()`. The process state was `U`, which is a wait for the disk. The process had used
0.19 s of CPU time.

Before the first line after the report, the start path calls `stat()` 8,152 times on
`/Volumes/T7_2TB`:

| Step | Call | Count |
|---|---|---:|
| `common.load_patches` | `os.path.isfile()` for each picture of `patch_dir` | 15 |
| `common.load_bottle_labels` | `os.path.isfile()` for each picture of `bottle_cropped_dir` | 2,093 |
| `common.load_bottle_labels` | `os.path.isfile()` for each picture of `bottle_label_dir` | 2,092 |
| `common.load_bottle_labels` | `os.path.isfile()` for each picture of `bottle_label_box_dir` | 2,092 |
| `build_rows` | `os.path.isdir()` for each wine directory of `photo_dir` | 1,860 |

`build_rows` also calls `os.listdir()` one time for each wine directory, through
`scan_photos`.

With a warm cache, all start steps took 2.8 s together. The directory steps took 0.12 s
of that time. So the cost comes from the cold metadata on the drive, not from the code.

### A cold `stat()` waits for the drive

One disk read brings the metadata of several files into the cache. So most cold `stat()`
calls return at once, and some calls wait for the disk. Two tests on 2026-09-23:

- 200 cold files of `svoe-wino-hackaton/dataset/derived/official-2026-09-17/labels-cache`:
  0.78 s in total. The slowest call took 349 ms.
- 1,297 cold files of `frap-public-small/objects/images`: 30.2 s in total. This is 23 ms
  for each call on average.

Cause: other jobs loaded the same drive. `iostat` showed about 20 MB/s and 100 to 400
transfers per second on `disk6`, the physical T7 disk, without a pause. These jobs used
the drive at that time:

- The PostgreSQL server of `drink-atlas-core`. Its data directory
  `drink-atlas-core/.runtime/postgres` is on the T7 drive. Five sessions were in `COMMIT`
  in state `U`.
- Two `scripts/fill_references_parallel.py` jobs of `drink-atlas-enrichment`, for the
  providers `lenta` and `rskrf`.
- `scripts/match_run.py` of this project, started by a night A/B script of another
  session.

### What the `drink-atlas-core` database does

A second check at about 08:20 found the source of the core load. The six database
sessions belong to the core API server (`drink_atlas_core.cli serve --port 8156`). Its
HTTP clients are the two `fill_references_parallel.py` jobs: `lenta` with 9 connections
and `rskrf` with 1 connection.

- The database reads from memory. In 10 s it read 2.3 GB of pages from shared buffers
  and 0.1 MB from the operating system.
- The database writes temporary files. Two measurements of 10 s gave 94.7 MB and
  148.2 MB of temporary files. The WAL of the core sessions was less than 0.1 MB in 10 s.
- The cause is the card lookup `barcode_references.card()` of `drink-atlas-core`. The
  fill job calls it for each GTIN through `GET /v1/barcode-references/{gtin}`. The
  subquery `NEWEST_CARD` reads all cards of the provider and sorts them before the GTIN
  filter. For `lenta`, one lookup read 10,581 rows, sorted them with
  `external merge  Disk: 6760kB`, and kept 1 row. `work_mem` is 4 MB.
- The cost of one lookup grows with the count of stored cards of the provider.
- At 08:38, `work_mem` of the core cluster was raised to 16 MB. After that, the pool wrote no
  temporary file in 10 s. The 2026-09-23 entry of `drink-atlas-core/ResearchLog.md` has the details
  and a proposed fix of the query.
- The test suite of `drink-atlas-core` ran at the same time in another session. Its
  upgrade tests call `CREATE DATABASE` and `DROP DATABASE`. The PostgreSQL log showed a
  checkpoint `immediate force wait` every 30 to 60 s. Each checkpoint took 5 to 10 s. The
  tests are the most likely cause of these checkpoints.

### `os.scandir()` needs no `stat()` for the file type

On APFS, the directory listing carries the file type. `DirEntry.is_file()` and
`DirEntry.is_dir()` read that type, so they need no `stat()` for a regular file or for a
directory. For a symbolic link, they call `stat()` on the target, as `os.path.isfile()`
does. Test on the 1,297 cold files of `frap-public-small/objects/images`:

| Call | Time |
|---|---:|
| `os.scandir()` and `DirEntry.is_file()` for each entry | 0.001 s |
| `os.path.isfile()` for each entry, after that | 30.2 s |

### Consequences

- While such jobs run, a start on a cold cache can take minutes. The tool prints no line
  during the scans, so the start looks like a hang.
- `/api/reload` calls the same loaders and `build_rows`. A reload has the same cost.
- `scripts/03_embed.py` and `scripts/08_variants.py` call `common.load_patches` and
  `common.load_cropped_bottles` at import. They pay the same cost at start.
- The entry of 2026-09-15 states that `my/` is cheap. That statement was true for 814
  directories on a drive without load. It is not true for 1,860 directories on a loaded
  drive.
- `os.scandir()` can remove all 8,152 `stat()` calls. The `os.listdir()` call of
  `scan_photos` still opens each wine directory. So a cold start still reads the metadata
  of 1,860 directories.

## 2026-09-22 — catalogue clusters: a photo finds a label line, and one confusion chains a range

Question: which signals join two catalogue cards into one cluster for a later re-rank
step, and with which defaults? The tool is `scripts/10_clusters.py`. The plan is
`docs/plans/04_catalog-clusters.md`. Every number below is over the whole catalogue of
2,103 cards. The vectors are the SigLIP 2 gateway indexes of `svoe-vino-matcher`:
`gateway-ad42b0653c` for the photo (2,093 cards) and `gateway-877e0dd4a8` for the label
crop (2,092 cards).

### A photo similarity finds a label line, not a wine

The three Abrau-Durso Pinot Noir cards are one wine. The photo cosines:

| Pair | Photo cosine | Label cosine |
|---|---:|---:|
| `-125` and `abrau-dyurso-abrau-dyurso-pino-nuar-krasnoe-suhoe-13` | 0.977 | 0.911 |
| `-12` and `-125` | 0.879 | 0.893 |
| `-12` and `-13` | 0.878 | 0.915 |

The nearest photos of `-12` are the Chardonnay `abrau-dyurso-shardone-beloe-suhoe-13`
(0.898) and the Cabernet Sauvignon `abrau-dyurso-kaberne-sovinon-krasnoe-suhoe-125`
(0.890). Both come before its own siblings. The line «Русский винный дом» holds one
label design for every grape, and the catalogue photo of `-12` has another colour than
the photos of its siblings. A threshold low enough to join `-12` to its siblings joins
the whole line first.

A photo threshold alone, as connected components:

| Photo cosine | Pairs | Same producer | Clusters | Cards | Largest |
|---|---:|---:|---:|---:|---:|
| 0.99 | 36 | 35 | 34 | 69 | 3 |
| 0.97 | 102 | 101 | 80 | 173 | 4 |
| 0.95 | 223 | 221 | 153 | 343 | 7 |
| 0.93 | 492 | 490 | 242 | 618 | 14 |
| 0.90 | 1,126 | 1,123 | 330 | 1,029 | 20 |
| 0.85 | 3,268 | 3,242 | 305 | 1,574 | 64 |

The label crop gives a similar curve: 260 pairs at 0.95, largest cluster 10. So the
two image signals stay at 0.95, and the `name` signal joins the cards of one wine.

### The name signal needs the grapes

The key is the producer, the name without the producer words, and the category. The
exact producer and name give 69 groups and miss `-13`, whose name is
«Абрау-Дюрсо Пино Нуар». The normalised key finds all three Pinot Noir cards.

32 of the 107 name pairs held different grapes. 15 of them are different wines of one
line: the line «Иноходец» of «Вина Арпачина» holds one card for each grape
(Алиготе, Кумшацкий, Пухляковский, Сибирьковый) under one name. The other 17 are one
wine whose cards list the grapes in two ways, such as «Рислинг» against «Рислинг
Рейнский», or a main grape against the whole blend. The rule: the grapes of one card
MUST be a subset of the grapes of the other card, or one field MUST be empty. It keeps
92 name pairs.

### One confusion chains a range together

The confusions come from the runs `2026-09-22T084237Z-svm-siglip2-448` (326 wrong
answers at rank 1, 0 stale) and `2026-09-18T195710Z-svm-vlmrerank-8b-siglip2-448-bench`
(184 wrong answers, 4 stale). A stale answer is a photo that the current label file no
longer marks `positive` in the folder of its card.

All four signals, with the grape rule:

| Least confusions for a link | Confusion links | Clusters | Cards | Largest |
|---|---:|---:|---:|---:|
| 1 | 274 | 262 | 771 | 38 |
| **2** | **100** | **255** | **630** | **10** |
| 3 | 47 | 243 | 588 | 10 |
| no confusion signal | 0 | 232 | 562 | 10 |

With 1 photo, the Pinot Noir cards stand in a cluster of 21 Abrau-Durso cards:
sparkling wines, the «Императорское» line, the Riesling, the Chardonnay. A single
confused photo is weak evidence, and some are label errors of the test set. With 2
photos the largest cluster is the same as with no confusions at all, and 100 links
stay. The default is 2.

With the default, the Pinot Noir cluster holds 4 cards: the three Pinot Noir cards and
the Cabernet Sauvignon `-125`. Two positive photos of `-12` were answered as that
Cabernet. Its label crop is blue-grey, as the catalogue photo of `-12` is.

### The result with the defaults

255 clusters over 630 cards. 53 `same-wine`, 22 `mixed`, 180 `look-alike`. Sizes: 194
of 2 cards, 31 of 3, 18 of 4, 5 of 5, 2 of 6, 3 of 7, 1 of 9, 1 of 10.

5 clusters cross a producer. Two of them hold a photo pair: Château Le Grand Vostock
against Шато Ай-Даниль at cosine 1.000, which is the known shared picture of the
catalogue, and Loco Cimbali against Золотая Балка «Blanc de Neige» at 0.958. The other
three hold confusions alone.

The script reads the vectors and needs no service. One run takes under a second.

## 2026-09-19 — a grey 32 by 32 signature cannot compare two wines; colour and 128 px can

Question: how does the review tool find two wines whose CATALOGUE bottle photo is the
same picture? Such a pair is a defect of the catalogue: the matcher cannot separate the
two wines by the image, and one of the two cards names the wrong bottle.

The catalogue of 2026-09-17 holds 2,103 cards, and 2,093 of them have a bottle photo on
disk. That is 2,189,278 pairs. A full compare at full resolution is not possible in the
time of a check, so the compare needs a signature.

### The grey 32 by 32 signature is not enough

The first attempt reused `photo_signature`, which the check `candidate_is_catalog_photo`
already uses: composite on white, convert to grey, crop to the bounding box of the
bottle, resize to 32 by 32. With numpy the 2.19 million pairs measure in 3.4 seconds.

The result looked wrong. 227 pairs measured under 1.0 of 255, and 931 measured under
6.0. Eight of the closest pairs were read by eye against the pictures themselves:

| pair | measured | what the pictures show |
|---|---|---|
| `abrau-...-bayanshira` / `abrau-...-madrasa` | 0.00 | one picture, under a white wine and a red wine |
| `agora-yachting-cabernet-sauvignon` / `agora-yachting-sauvignon` | 0.00 | one picture, and its label reads `SAUVIGNON` |
| `chateau-le-grand-vostock-krasnostop-rezerv` / `shato-ay-danil-grenash` | 0.00 | one picture, under two different producers; the label reads `ГРЕНАШ` |
| `method-classic-kokur` / `pino-nuar-2025` | 0.00 | one picture; the label reads `ПИНО НУАР` |
| `katharon-katharon-kaberne-fran` / `katharon-katharon-merlo` | 0.12 | TWO pictures of one bottle design; the label text differs |
| `fanagoriya-brule-cabernet-franc` / `fanagoriya-brule-muscat-ottonel` | 0.14 | TWO pictures; one is a rosé and the other is a dark green bottle |

The two populations overlap. A true duplicate measures 0.00 and a different picture
measures 0.09. The reason is the signature itself: 32 by 32 grey holds no colour and no
text of the label. Two wines of one producer line share the bottle shape and the label
layout, and the signature keeps nothing else. The measure is real; it answers a question
that is not the question asked.

### Colour and 128 pixels separate the two populations

Four signatures were measured against six hand-checked duplicates and five hand-checked
different pictures. The crop and the composite on white are the same in all four.

| signature | largest value of a duplicate | smallest value of a different picture |
|---|---|---|
| 32 by 32 grey | 0.00 | 0.09 |
| 64 by 64 grey | 0.00 | 0.11 |
| 64 by 64 colour | 0.00 | 0.12 |
| 128 by 128 colour | 0.00 | 0.18 |

Every duplicate measures exactly 0.00 at every resolution, and the gap to the nearest
different picture grows with the resolution and with the colour. 128 by 128 colour gives
the widest gap and is the choice.

A 128 by 128 colour signature is 49,152 bytes against 1,024 bytes. All 2.19 million
pairs at that size are about 107 billion operations, which is too slow. The check
therefore runs in two stages: the grey signature names the near pairs of the whole
catalogue in 3.4 seconds, and the colour signature measures those pairs alone in 7.5
seconds. The coarse cut is 3.0 of 255, which is far above the 0.5 band where the two
populations of the grey signature lie, so the cut loses nothing.

### The duplicates of this catalogue are all byte-identical

The 504 pairs under the coarse cut were measured again with the colour signature:

| colour distance | pairs | of which byte-identical |
|---|---|---|
| exactly 0.000 | 29 | 29 |
| 0.001 to 0.100 | 1 | 0 |
| 0.100 to 0.500 | 17 | 0 |
| 0.500 to 1.000 | 70 | 0 |
| 1.000 to 5.000 | 357 | 0 |

Every pair that is one picture is byte-identical, and the next pair measures 0.069. This
catalogue holds no resized copy and no re-encoded copy of a bottle photo, unlike `my/`,
where `candidate_is_catalog_photo` finds such copies. A SHA-256 alone would find all 29
pairs of today. The signature is kept because it does not depend on that property: a
later import of the catalogue may hold a resized copy, and a SHA-256 would miss it.

### The two tags

The cliff between 0.000 and 0.069 carries a meaning, and the check reports both sides of
it with a different tag.

`same pic` is a distance under 0.05. The two cards carry one picture. This is a defect.
On the catalogue of today it is 27 clusters over 55 wines.

`twin` is a distance from 0.05 to 1.0. The two pictures are different photographs of a
bottle that looks nearly the same. On the catalogue of today it is 43 clusters, and they
are producer lines: 8 wines of `fanagoriya-primum-alveus`, 6 of
`chteau-le-grand-vostock ... reserve`, 5 of `fanagoriya-brule`. This is not a defect by
itself. The reviewer judges it, and the pair is a candidate for a variant group.

### The cluster, not the pair

Three wines that carry one picture give three pairs. The check joins the pairs with a
union-find and reports one cluster of three. The reviewer reads the whole cluster from
any one of its rows, and the count of the findings then states the number of defects and
not the number of pairs.

## 2026-09-18 — a crop to the bottle finds twice as many catalogue renders in `my/`

Question: how does the review tool find a candidate photo in `my/<slug>/` that is the
catalogue bottle photo of the same wine? The set MUST hold real-world photos only. The
requirement names two cases: the bytes are equal, and the content is equal but the size
differs.

The first case is a SHA-256 of the two files. The second case needs the pixels, because
a resized copy, a re-encoded copy, and a copy with another white margin all hold other
bytes.

Method. Each picture is reduced to one signature: composite on white, convert to grey,
resize to 32 by 32. The measure of two signatures is the mean absolute difference (MAD)
of the 1,024 values, on the scale 0 to 255. The measure ran over the whole set of
2026-09-18: 1,853 wines, 4,112 pairs of one candidate photo and one catalogue bottle
photo. 66 pairs were then compared by eye across the whole range of the measure.

### Result 1 — no candidate photo is byte-equal to its catalogue bottle photo

0 of the 4,112 pairs have equal bytes. The byte case alone finds nothing on this set.
Every leaked render came in through a re-encode or a resize. The check MUST read the
pixels; a digest is not enough.

### Result 2 — a crop to the bottle is the step that makes the measure work

Two variants of the signature were measured.

| Variant | Pairs under MAD 10 | First false pair seen |
|---|---|---|
| Plain: grey, resize to 32 by 32 | 143 | MAD 12.5 |
| Crop: grey, crop to the content, resize to 32 by 32 | 304 | MAD about 16 |

The crop takes the bounding box of every pixel that is more than 18 grey values under
white, and resizes that box. It removes the white margin and the aspect ratio from the
measure.

The plain variant misses a copy that carries another margin. Measured cases: the same
picture scored MAD 119.9 (`aya-organic-wine-viney`), 114.8 (`vinodelnya-vedernikov-ve`),
93.7 (`agrolayn-mountain-eagle`), and 71.1 (`villa-sofiya-merlo-kaber`) in the plain
variant, against 6.1, 2.0, 0.8, and 2.6 in the crop variant. A margin is common, because
the catalogue render and the copy on a shop page are cut differently.

### Result 3 — the threshold

The samples of the crop variant, by eye:

| Band | Sampled | Result |
|---|---|---|
| MAD under 6 | 21 pairs | every pair is the same picture |
| MAD 6 to 11 | 18 pairs | every pair is the same picture |
| MAD 11 to 19 | 18 pairs | mixed; clear false pairs from about 16 |
| MAD 19 to 30 | 9 pairs | mostly different wines |

The threshold is set to 10.0, one step under the first uncertain case. On the set of
2026-09-18, 304 of the 4,112 pairs are under the threshold. The measurement pass read
every pair. The check in the tool leaves out a photo that is already marked `unusable` or
marked for deletion, so it reports 282 photos in 241 wines. 23 of the reported photos
carry the label `positive`, which makes them defects of the benchmark, not only of the
set.

A copy over the threshold is not reported. The check misses it. The measure has no sharp
edge between the two classes, so no threshold reports every copy and no false pair.

### Result 4 — the forms of a copy that the check finds

A made copy of one catalogue bottle photo, 260 by 1000 pixels with an alpha channel:

| Copy | Measure | Found |
|---|---|---|
| The same file | 0 (equal bytes) | yes |
| Half size, JPEG quality 82 | 0.28 | yes |
| Quarter size, PNG | 0.35 | yes |
| The same size, JPEG quality 70 | 0.18 | yes |
| The same picture with a wider white margin | 0.12 | yes |
| The same picture flattened on BLACK | over the threshold | no |

The last row is the second limit of the check. The check composites a transparent picture
on WHITE. A render that was flattened on another colour measures far over the threshold.
A shop page nearly always uses white, so this case is rare.

### Result 5 — the cost of the run

The check reads the pixels of every candidate photo and of every catalogue bottle photo,
about 6,000 files. Pillow releases the interpreter lock while it decodes, so threads
help.

| Pass | Time |
|---|---|
| One thread | about 120 s |
| Eight threads | about 50 s to 73 s |

`Image.draft("RGB", (512, 512))` lets a JPEG decode at a reduced scale and saves about a
third of the time. The other formats ignore the call. The result is not cached: a cache
would have to follow every write of every file.

The catalogue volume itself is fast. A read of 10 bottle photos takes 6 ms, and
`os.listdir` over the 15,803 files of the strapi `uploads` directory takes 13 ms. The
cost of the run is the decoding, not the disk.


## 2026-09-17 — the official API takes parallel requests; 4 at once is the best rate

Question: can `scripts/match_run.py --backend official-api` send several requests at
once, and does `api.vino-svoe.ru` answer with throttling or with a ban?

Method. Two parts.

1. The runner against a local mock that sleeps 1 s per request. The mock counts how many
   requests it holds at the same time. This states whether `--workers` reaches the
   server, without any traffic to the official API.
2. The official API from `cloudzy-ams` (104.194.134.114, Amsterdam), not from this Mac.
   The intermediate host carries the risk of a block. 12 photos, sent three times: one at
   a time, 4 at once, 8 at once, with a pause of 5 s between the parts. 36 requests in
   total. The request is the same `multipart/form-data` that `match_backends.py` builds.

### The runner

| `--workers` | Wall time, 8 photos | Peak requests at the server |
|---|---|---|
| 1 | 8.2 s | 1 |
| 4 | 2.2 s | 4 |
| 8 | 1.2 s | 8 |

`HttpMultipartBackend.ask()` holds no mutable state, so the threads do not interfere.
`pool.map` gives the answers in the order of the query set, so `predictions.jsonl` and
`results.jsonl` keep that order at every worker count.

Ctrl+C stops a parallel run at once: the iterator of `Executor.map` cancels the futures
that did not start. A run of 40 photos with 4 workers ended 0.2 s after the signal and
still wrote `metrics.json` and `summary.md`. Because the answers are read in order, a
few answered photos that wait behind a slower photo are lost on the stop.

### The official API

| Part | Requests at once | Wall time | Median latency | Fastest | Slowest | Status |
|---|---|---|---|---|---|---|
| A | 1 | 28.4 s | 2377 ms | 724 ms | 4539 ms | 201 x 12 |
| B | 4 | 8.8 s | 2075 ms | 865 ms | 3861 ms | 201 x 12 |
| C | 8 | 6.1 s | 3198 ms | 2264 ms | 4788 ms | 201 x 12 |

Findings.

1. No throttling and no ban. All 36 requests answered 201. No answer carried
   `Retry-After` and no answer carried a rate-limit header. Every answer held candidates.
2. 4 requests at once cost nothing. The wall time fell by 3.2x and the median latency
   did not rise. The server answers these in parallel.
3. 8 requests at once meets a queue. The wall time fell by 4.7x, but the median latency
   rose from 2377 ms to 3198 ms, about 35 percent. The fastest answer rose from 724 ms to
   2264 ms, which is the mark of a queue in front of a limited pool.
4. The API answers 201, not 200. The runner does not test for 200, so this does not
   matter to it.

Rule: use `--workers 4` for a sweep. Use `--workers 1` for a run whose latency is
compared with the jury harness, because `metrics.json` then sets
`latency_ms.comparable` to `false`.

Limit of this probe: 36 requests in about 45 seconds. A rate limit over a longer window,
a daily quota, and a ban that needs more requests are NOT excluded. A full run is 1343
requests and was not made.

## 2026-09-17 — latency of the back-label call: the local 9B wins by 60x when thinking is off

Question: how fast does each vision model see that `04_manual.webp` of
`shato-pino-exclusive-pino-nuar-merlo-krasnoe-suhoe-135` is a back label and not the
front label?

Method. One photo pair, the catalogue reference and the back-label photo. The prompt is
the production prompt of `04_verify.py` without a change. `maxside` 448, `temperature` 0,
`max_tokens` 150 for the cloud models. 5 calls for each model. The correct answer is
`same_wine=false` and `front_label=false`. The script is
`backlabel_bench.py` in the session scratchpad. It is not part of this project.

Result 1: every model gives the correct answer in every call. Latency differs by 60x.

| Endpoint | Model | Median | Min | Max | Correct |
|---|---|---|---|---|---|
| gx10 | `qwen3.5-9b`, `enable_thinking=false` | 0.74 s | 0.72 s | 1.05 s | 3/3 |
| qwencloud | `qwen3.6-flash` | 7.89 s | 7.86 s | 13.02 s | 5/5 |
| qwencloud | `qwen3.8-flash` | 12.76 s | 6.93 s | 16.93 s | 5/5 |
| gx10 | `qwen3.5-9b`, thinking on | 44.45 s | 42.69 s | 46.44 s | 5/5 |
| qwencloud | `qwen3.8-max` | 61.06 s | 13.64 s | 196.28 s | 5/5 |

Result 2: `qwen3.8-max` is not slow on average, it is unstable. Its five calls ran
13.6 s, 27.4 s, 61.1 s, 79.5 s, and 196.3 s. The spread agrees with the p90 of 105 s in
`work/vlm_bench_report.md`. A per-photo timeout does not fix this model. Only a lower
tier does.

Result 3: on `qwen3.5-9b` the thinking budget is the whole cost. Thinking on spends
about 5 350 characters of `reasoning_content` and 44 s. Thinking off spends 0 and
0.74 s, and the answer stays correct.

Result 4: the text `/no_think` in the user message does not stop the thinking of
`qwen3.5-9b` on llama.cpp. `reasoning_content` still held 1 273 characters and
`content` came back empty. The field that works is
`"chat_template_kwargs": {"enable_thinking": false}` in the request body.
Code that sends `/no_think` to this server silently loses its answer when
`max_tokens` is small.

Result 5: a small `max_tokens` is a trap for a thinking model. With `max_tokens` 150 the
five calls to `qwen3.5-9b` returned an empty `content`, because the budget went to
`reasoning_content`. The call looks like a parse failure, not like a budget failure.

Open question: this test uses one photo. It measures latency, not accuracy. The
accuracy of `qwen3.5-9b` with thinking off is not measured on the 300-pair set.

## 2026-09-16 — which vision model for stage 4: three Qwen models are equal in accuracy, not in cost

Question: for the stage 4 identity check, how does `qwen3.7-flash` compare with
`qwen3.8-max` and `qwen3.8-flash`?

Method. The benchmark uses the production prompt of `04_verify.py` without a change,
two images at `maxside` 448, `temperature` 0, and the endpoint `dashscope-intl`.
The ground truth is `review-labels.json`. The sample holds 300 photo pairs:
150 `positive`, 100 `negative`, 50 `unusable`. The seed is 20260915.
Every model answered every pair. 1200 calls ran with no error and no parse failure.
`scripts/bench_vlm_models.py` makes the calls. `scripts/bench_vlm_score.py` scores them.
The decision rule is the production rule of stage 5:
`same_wine AND NOT studio AND front_label`.

The label `unusable` is a fuzzy negative. Such a photo can show the correct wine and
still not belong in the set. The main measure therefore uses `positive` against
`negative` only, 250 pairs. The `unusable` stratum is reported apart.

Result 1: the three models have the same accuracy.

| Model | Precision | Recall | F1 | Accuracy |
|---|---|---|---|---|
| `qwen3.8-max` | 0.784 | 0.873 | 0.826 | 0.780 |
| `qwen3.8-flash` | 0.765 | 0.867 | 0.812 | 0.760 |
| `qwen3.7-flash` | 0.831 | 0.753 | 0.790 | 0.760 |
| `qwen3-vl-flash` | 0.693 | 0.887 | 0.778 | 0.696 |

A McNemar test on the paired decisions finds no difference between the three models:
`3.7-flash` against `3.8-flash` p=1.00, `3.7-flash` against `3.8-max` p=0.59,
`3.8-flash` against `3.8-max` p=0.55. The difference to `qwen3-vl-flash` is real
(p=0.0086 against `3.8-max`, p=0.044 against `3.8-flash`).

Result 2: the error profile differs, and this difference is real.

| Model | Rejects a wrong wine | Accepts the right wine | Rejects an unusable photo |
|---|---|---|---|
| `qwen3.7-flash` | 77/100 | 113/150 | 14/50 |
| `qwen3.8-flash` | 60/100 | 130/150 | 10/50 |
| `qwen3.8-max` | 64/100 | 131/150 | 7/50 |
| `qwen3-vl-flash` | 41/100 | 133/150 | 19/50 |

`qwen3.7-flash` is stricter. It rejects a wrong wine more often (p=0.0005 against
`3.8-flash`, p=0.0146 against `3.8-max`) and it misses the right wine more often
(p=0.0023 and p=0.0014). `qwen3.8-flash` and `qwen3.8-max` are equal on every
stratum (p=0.56, p=1.00, p=0.45). The two answers cancel, so the net accuracy is
equal while the behaviour is not.

Result 3: the cost is not equal.

| Model | Latency median | Latency p90 | Completion tokens for 300 calls |
|---|---|---|---|
| `qwen3-vl-flash` | 1.8 s | 2.3 s | 9 907 |
| `qwen3.8-flash` | 5.8 s | 20.7 s | 180 214 |
| `qwen3.8-max` | 20.7 s | 105.2 s | 575 401 |
| `qwen3.7-flash` | 25.6 s | 47.8 s | 778 220 |

The prompt cost is near 450 tokens for every model. The completion cost is not:
`qwen3.7-flash` and `qwen3.8-max` write a long reasoning trace for a yes or no
question. `qwen3.7-flash` spends 4.3 times the completion tokens of `qwen3.8-flash`
and runs 4.4 times slower, for the same net accuracy.

Result 4: the stated confidence carries no signal. Mean confidence when the answer
was right against when it was wrong: `3.7-flash` 0.954 / 0.950, `3.8-flash`
0.946 / 0.935, `vl-flash` 0.924 / 0.922. Only `3.8-max` shows a small gap,
0.918 / 0.876. Do not use the `confidence` field as a filter.

Result 5: no model rejects an unusable photo. The best is `qwen3-vl-flash` with
19/50. A reasoning model is worse, not better: `qwen3.8-max` rejects 7/50. The
prompt does not ask about photo quality, so this is a gap of the prompt, not of
the model.

Conclusion.

1. `qwen3.8-max` gives nothing over `qwen3.8-flash`. It is equal on every stratum
   and costs 3.2 times the completion tokens and 3.6 times the latency. Do not use
   `qwen3.8-max` for this task.
2. Choose between `qwen3.8-flash` and `qwen3.7-flash` by the cost of the error,
   not by the accuracy. The candidate pool is large and the acceptance rate is
   8.6 percent, so a false positive costs more than a false negative: a wrong wine
   enters the set, and a missed photo is replaced by the next candidate. This
   favours `qwen3.7-flash`, which rejects 77 percent of wrong wines against 60
   percent. The price is 4.3 times the completion tokens.
3. `qwen3-vl-flash` is 14 times cheaper than `qwen3.8-flash` in completion tokens
   and answers in 1.8 s, but it accepts 59 of 100 wrong wines. Use it only as a
   first filter before a stricter model.

Open questions.

1. The production model `qwen3-vl-32b` on gx10 was not in this benchmark. A
   comparison against the local model was not made, so this result does not say
   whether stage 4 should change.
2. The prompt was not tuned for any model. A strict instruction about photo
   quality may repair result 5 for every model.
3. `enable_thinking` was not set to false. The long reasoning traces of
   `qwen3.7-flash` and `qwen3.8-max` may not be needed for this task.

## 2026-09-15 — a perceptual hash does not find the variants of a wine

Task: find the catalogue bottle photos that are so similar that a reviewer mixes
them up. Example given by the project owner:

    abrau-dyurso-pino-nuar-krasnoe-suhoe-12
    abrau-dyurso-pino-nuar-krasnoe-suhoe-125

The two photos hold the same label design of "Абрау-Дюрсо Пино Нуар" in two colours:
a light blue label with a purple capsule, and a cream label with red print and a red
capsule.

A 16x16 dHash was measured first. It failed:

| Pair | Hamming distance of 256 bits |
|---|---|
| pino-nuar-12 and pino-nuar-125, the same wine | 76 |
| pino-nuar-125 and shardone-12, different wines | 29 |
| pino-nuar-12 and shardone-13, different wines | 34 |

The hash ranks the wrong pairs first. Two reasons were found:

1. A bottle photo is mostly bottle. The silhouette holds most of the bits, and every
   dark bottle of one producer holds the same silhouette. The label, which is the
   part that differs, holds few bits.
2. The catalogue stores the photos in two shapes. Some are square, 2362x2362 with a
   wide empty margin. Others are a tight cut, such as 312x1000. A trim of the margin
   by the alpha channel was added and did not repair the ranking.

The difference between two variants is mostly colour, and a grey dHash drops colour.

Conclusion: the metadata of the catalogue answers this question better than the
pixels. Two slugs with the same `producer` and the same `name` in `catalog.jsonl`
are variants of one wine. This step is exact, costs nothing, and catches the example
pair. It gives 28 groups over 63 of the 814 wines of `my/`.
The image step now uses SigLIP2 embeddings through the gx10 service, not a hash.

## 2026-09-15 — the image step MUST NOT run beside stage 4

`scripts/08_variants.py` and stage 4 of the pipeline use the same llama-swap service
on gx10 (`http://192.168.86.14:18081`). The service holds one model at a time. A
request for `siglip2` while stage 4 runs makes the service drop `qwen3-vl-32b` and
load `siglip2`, and the 8 concurrent stage 4 requests then stall. Run the image step
after the pipeline stops, or run `08_variants.py --no-image`.

## 2026-09-15 — decision: three labels, not two verdicts

Question: is a photo that shows a different wine a rejection or a sample?

Options:

1. Two labels, `positive` and `negative`. Simple, but the name and the colour of the
   second label read as "rejected", and the card was dimmed like waste.
2. Three labels, `positive`, `negative`, `unusable`. One more decision per photo.
3. Four labels, with `hard negative` and `easy negative` apart. The finest negative
   set, but the slowest pass over 1,892 photos.

Decision: option 3 of the list above was not taken; three labels were chosen.
A `negative` photo is a wanted result. The set needs negative samples, so a photo
that shows a different wine stays in the set as a negative sample of its slug.
Without a third label the negative set would hold search noise, such as a photo with
no bottle or an unreadable photo, and could not be used as it is. `unusable` is the
only label that takes a photo out of the set.

Consequences:

- The negative card has its own blue colour and is not dimmed. Only `unusable` is dimmed.
- The pass costs one more decision per photo than a two-label pass.
- The split between a hard negative and an easy negative is not recorded. A later pass
  can add it, because the slug of the wine and the file name of the photo are kept.

## 2026-09-15 — decision: the label file was renamed while it held no data

The file was `review-verdicts.json` with `verdict: "yes" | "no"`. It is now
`review-labels.json` with `label: "positive" | "negative" | "unusable"`, `version` 2,
and the top key `labels`. The rename was made at the moment the file held no real
label, so no migration step was needed. A reader of the file now needs no README to
understand that a negative photo is kept on purpose.

## 2026-09-15 — `stat` on the strapi `uploads` directory is very slow

The strapi dump holds all media in one flat directory:
`../svoe-wino-hackaton/sources/official-2026-09-15/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads`.
The directory holds about 15,800 files. It sits on the external volume `/Volumes/T7_2TB`.

Measured behaviour:

- `os.path.exists()` on 200 files in that directory did not finish in 120 s.
- `os.listdir()` on that directory did not finish in 120 s on a cold cache.
- `ls -la` on the parent directory answered at once.

Consequence for the review tool: the first version tested each of the 811 bottle photo
paths at start. The start did not finish. The tool now trusts the `local_path` field of
`catalog.jsonl` and does not test the file at start. The browser requests each bottle
photo only when its row scrolls into view, so the cost is spread over the review pass and
the operating system cache absorbs it. `/img/bottle` answers 404 when the file is absent.

Rule for any other tool in this workspace: do not walk or `stat` the strapi `uploads`
directory in a start path. Read `../svoe-wino-hackaton/derived/catalog.jsonl` instead.
`../svoe-wino-hackaton/scripts/build_catalog.py` writes that file and pays the cost once.

By contrast, `my/` is cheap. 814 `listdir` calls over `my/` finish in a few seconds.

## 2026-09-15 — slug coverage of `my/` against the strapi catalogue

`catalog.jsonl` holds 2,103 slugs. `my/` holds 814 slug directories with 1,892 photos.

- 811 of the 814 slugs are present in `catalog.jsonl`.
- 3 slugs are absent from `catalog.jsonl`:
  `chateau-tamagne-select-blanc-brut-svo-yo-vino`,
  `vinodelnya-uzunov-bunt-tsitronnyy-magaracha-beloe-suhoe-139`,
  `vinodelnya-uzunov-roze-kaberne-sovinon-rozovoe-ekstra-bryut-127`.
- 1 slug is present but has no `upload_file`:
  `fanagoriya-fanagoriya-hey-bey-shardone-beloe-suhoe-13`.

So 4 wines have no catalogue bottle photo for column 1 of the review table.
The `my/` set was built from `wines.jsonl` of the `vino-svoe.ru` dump, and the strapi
dump is a separate export. The two slug sets are not identical.

Photo count per wine: 1 photo for 321 wines, 2 for 136, 3 for 131, 4 for 224, 5 for 2.

## 2026-09-16 — Image sources for the agent hunt

Findings from batch 1 of the agent photo hunt (6 agents, wines 1-48 of the
`needs_positive` queue). They apply to every later batch.

### Reachability from this Mac

| Host | Result | Route to use |
|---|---|---|
| `otzovik.com` HTML | 507 captcha | fetch on `alphavps-bg` |
| `otzovik.com` HTML from `alphavps-bg` | 507 on some pages | site search `?search_text=` works |
| otzovik images | 403 direct | fetch on `alphavps-bg`, post as `data:` URL |
| `irecommend.ru` HTML | 200 | direct |
| `irecommend.ru` image host | 1.5 kB error page | use `cdn-irec.r-99.com` instead |
| `yandex.ru/images` | 200 | direct |
| `duckduckgo.com` | no answer | not usable |

### Yandex Images without a captcha

Two forms work from this Mac. Both honour the `site:` operator.

1. Parse the `serpList` JSON out of the result HTML. Page with `&p=N`.
2. Call the JSON endpoint with `format=json&request={...}` and the header
   `X-Requested-With`.

Batch 1 used these for nearly every candidate. One agent used 2 WebSearch calls,
one used 0. The WebSearch budget is not the limit; the sites are.

### The `data:` URL ingest path

`POST /api/v1/propose` accepts a `data:` URL. `fetch_image` handles it before the
SSRF guard and sniffs the real media type from the first bytes. This is the way to
propose an image from a host that blocks this Mac. Verified before batch 1 started.

### Recurring judgement problems

- **Pre-rebrand labels.** AGORA (cream top band) and Burnier (single label with a
  knight-helm crest, before the 2024 two-part design) both have many real review
  photos of the older dress. The catalogue render shows the new dress. Open question
  for the project owner: `positive`, `variant`, or `negative`.
- **Sibling traps.** `alma-valley-merlo-rezerv` `-14` and `-15` differ only in the
  bottom label line. AGORA *Muscat* and *Muscat Rkatsiteli* share the bottle and the
  band. Abrau *Русское шампанское* and *Русское игристое* share the diamond bottle.
- **Duplicate catalogue rows.** `aligote-avtorskoe` and `aligote-avtorskoe-vino`
  carry the same `bottle_path`. They are one wine.

### Agent operation

Agents MUST get a per-agent scratchpad subdirectory. In batch 1 two agents wrote a
helper script of the same name into one shared directory and one overwrote the other
mid-run. No data was lost, because proposals go straight to the server.

### Why `propose` fails on some https hosts (diagnosed 2026-09-16)

An agent reported "the review server cannot fetch https URLs". That statement is too
broad. The true rule is narrower.

`fetch_image` succeeds on `https://upload.wikimedia.org/...` and reaches
`https://example.com/`. It fails on `https://porusski.me/` with
`CERTIFICATE_VERIFY_FAILED`.

Cause: `porusski.me` does not send its intermediate certificate
(`GlobalSign GCC R6 AlphaSSL CA 2025`). `curl` still gets HTTP 200, because curl
follows the AIA extension and downloads the missing intermediate. Python `urllib`
with OpenSSL does not do AIA chasing.

A different CA bundle does NOT fix it. Tested with `certifi`
(`/opt/homebrew/lib/python3.14/site-packages/certifi/cacert.pem`): same failure. The
chain is incomplete at the source, not missing a root here.

Consequence: no change to `review_server.py` is needed or useful. The `data:` URL
path is the general answer. An agent SHOULD fetch the bytes with `curl` (locally or
on `alphavps-bg`), inspect those exact bytes, and post them as a `data:` URL. This
also guarantees that the stored file is the file the agent judged.

Cost: the `url` field of such a proposal holds the data URI, not the address. The
`source_url` field MUST therefore carry the page address, so the reviewer can return
to the source.

### Sources, ranked by yield in batch 1

1. **Vivino** — the best source for obscure Russian wines. `explore?search_term=`
   fetched on `alphavps-bg` gives per-vintage user label photos.
   `images.vivino.com` IS reachable from this Mac, so those proposals need no
   `data:` URL.
2. **otzovik** — richest review photos. `/reviews/<product>/gallery/` lists every
   photo of a product. Full size = the `_t.jpeg` thumb with `_t` removed.
3. **porusski.me** — a wine-of-the-week series with real-setting photography.
4. **dzen.ru**, **garryspirit.ru** — blog photos, often lineup shots.
5. **irecommend** — good when it answers. It did not answer for most of batch 1.

### Discovery engines

- `bing.com/images/search?q=` works from this Mac. Parse the `m="{...}"` attributes;
  each carries `murl` and `purl`. Add `&qft=%2bfilterui%3aphoto-photo` to drop
  renders. The `site:` operator breaks it.
- `yandex.ru/images`: two agents parsed `serpList` JSON out of the HTML and the
  `format=json` endpoint successfully; a third got an empty JS-only shell. Treat it
  as unreliable, not as broken.
- Bing **web** search and DuckDuckGo gave nothing through curl.

### Rate limits measured in batch 1

- `irecommend.ru` tolerates about 5 page fetches, then answers HTTP 521. It locked
  out both this Mac and `alphavps-bg` at about 00:20 and did not recover that night.
  Use gaps well over 4 s.
- `otzovik.com` on the VPS starts to answer 507 after about 3 requests. Use gaps of
  10 s or more.
- otzovik **images** on `i20NN.otzovik.com`: one agent downloaded them straight from
  this Mac, another needed the VPS. Try direct first, fall back to the VPS. Note that
  `i.otzovik.com` (the bare host) answers 403 and is NOT the image host.

### Proposals an agent cannot take back

An agent has no delete route, by design. `hunter-05` posted a proposal at 0.85, then
enlarged the label and found it was the dry Aratti Мускат Белый, not the semi-dry of
the slug. It could only add a correction comment. The reviewer MUST read photo
comments before accepting a proposal. See `aratti-muskat-belyj-polusuhoe`
`02_agent.jpg`.

## 2026-09-16 — Batch 2 source findings

These correct and extend the batch 1 list. Engine reachability changes hour by hour.
Treat every engine as unreliable and keep two alternatives ready.

### Shop sites are better than review sites for obscure wines

- **cigarpro.ru** — the best single source. 5-6 own photographs per product, in a
  fixed order: studio on white, label crop, back label, bottle on a shop shelf, close
  bottle shot. Two or three of each set are usable.
- **cru.ru** — own camera photographs, sometimes in a shop setting. Search with
  `https://www.cru.ru/search/?q=<query>`. It gave the strongest photo for 4 of 8
  wines in one slice.
- **vinoteki.ru** — working site search, one unique image per product page.
- **alcoplaza.ru** — `photo_it/photoNNNNN.jpeg`.
- **cdn.metro-cc.ru** — `ru/ru_pim_<code>_01.png`. `_02` is always the back label.

### Engine state on 2026-09-16

- `yandex.ru/images` works from this Mac when you parse the `data-state="{...}"`
  blobs and walk to `serpList.items.entities` (`origUrl`, `snippet.url`). A working
  parser is at `work/hunt/scratch/hunter-10/yx.py`.
- `bing.com/images` worked for two batch 1 agents and returned unrelated result sets
  for a batch 2 agent, with and without a cookie session. Verify before you trust it.
- `otzovik.com` answered 507 for a whole run from this Mac AND from `alphavps-bg`.
  The numbered image hosts `i20NN.otzovik.com` kept serving files, so image results
  found through a search engine stay usable.
- `irecommend.ru` answered 521; the mirror `cdn-irec.r-99.com` served the same paths.
- `rskrf.ru` (Roskachestvo) is a JavaScript shell. Every page and image request
  returns the same 13602-byte HTML. Skip it.
- Dead or JS-only: DuckDuckGo images, go.mail.ru, wine-shopper, winestreet,
  simplewine, okmarket.

### Vivino: two agents disagree, and the reason is the policy

One batch 1 agent called Vivino the best source and proposed from it at 0.85-0.95.
A batch 2 agent found no user photos at all and only the main label shot.
Both are right. Vivino's images are tight label crops. Batch 1 allowed that form;
POLICY.md rule 5 forbids it. Vivino is therefore of little use under the current
policy. `https://www.vivino.com/api/wines/<id>/reviews?per_page=50` answers without
authentication from `alphavps-bg`, but the payload carries no image field.

### Detect a re-used catalogue render before proposing it

A shop pack shot is often the same file as the catalogue render. Compare the
candidate with the catalogue bottle by normalised pixel correlation first. Measured:
0.99 for a producer pack shot that was the same image, 0.26 and 0.38 for genuinely
independent photographs. A search engine will also surface the catalogue render
itself as if it were a user photo.

### Correlation baseline, corrected

hunter-10 proposed normalised pixel correlation against the catalogue render to catch
a re-used render. hunter-11 measured the baseline and it is not what the first numbers
suggested:

- identical file: 1.00
- two INDEPENDENT studio shots of the same bottle: about 0.45
- ordinary independent photographs: 0.02 to 0.46

So 0.45 is normal and is NOT evidence of a re-used render. Only a score near 1.00
means the same file. Use the check to reject duplicates, never to rank candidates.

### Vivino is not uniformly a label crop

A note to correct the tip that was relayed to batch 2 hunters. hunter-09 found only
tight label crops on Vivino and called it useless under POLICY rule 5. The relay
generalised that to "skip Vivino". hunter-11 then found Vivino user snapshots that
show a hand, a room or a shop behind the bottle, which are bottle-in-context photos,
not crops. Those are usable. Judge each Vivino image on what it shows. Three such
proposals are flagged in hunter-11's report for the reviewer to confirm.

### bing.com/images: the fix

Three agents reported that `bing.com/images` answers with result sets for unrelated
queries. One agent found the cause and the fix.

Send a **Windows** Chrome User-Agent AND the cookie `SRCHHPGUSR=SRCHLANG=ru`, and
encode spaces in the query as `+`. With a Mac User-Agent, or without the cookie, Bing
returns the unrelated-garbage result sets. With them, it works and gives good shop
leads.

### More site behaviour

- `winestyle.ru` allows about one page per host, then answers 403 for the rest of the
  run.
- `alcoplaza.ru` sells Desono under a URL containing `rkatsiteli-orange` but
  photographs the plain Desono Rkatsiteli, with no `ORANGE` line. A URL is not
  evidence of what the photo shows.
- `winemore` and Roskachestvo served byte-identical files for one wine.
- `cdn.metro-cc.ru` `_01` is often the producer render that the catalogue already
  holds. Correlation-check it.
- Reaching `i20NN.otzovik.com` directly from this Mac is unreliable: two agents
  downloaded from it, one got a TLS handshake failure and had to use `alphavps-bg`.
  Try direct, fall back to the VPS.

### The catalogue renders come from wine.rbc.ru

The strapi render filenames are derived from
`rbcwine.storage.yandexcloud.net/media/wines/<id>_<hash>.png`. Any image served from
an rbcwine address IS the catalogue photo. Reject it by the URL alone; no correlation
check is needed.

### Correlation baseline, second correction

hunter-08 measured 0.26 to 0.76 for shop pack shots that are genuinely different
photographs of the same bottle. The two highest, 0.76 and 0.745, were then confirmed
by eye as different photographs.

Combined with hunter-11's measurements, the rule is: only a score at or very near 1.00
proves the same file. A score of 0.76 proves nothing. Never use this number to rank
candidates, and never reject a candidate on a score below about 0.95 without looking
at it.

### A shop page often files a photo under the wrong product

Measured in one slice alone: alcoplaza filed a Совиньон back label under Chardonnay;
cru.ru filed a Сира photo under Chardonnay; metro filed a Мерло back label under
Chardonnay; bestwine24 served Авторское Каберне for a Саперави query; alcoplaza sells
Desono under a URL containing `rkatsiteli-orange` but photographs the plain
Rkatsiteli. A product URL is NOT evidence of what the photo shows. Read the label in
the picture, every time.

### Label generations recorded by the hunt

- **Chateau de Talu "Уроки французского"** has three generations. G1: Latin name and
  Latin grape. G2 (the catalogue): Latin name and Cyrillic grape. G3 (current):
  Cyrillic `ШАТО де ТАЛЮ` and Cyrillic grape. G2 was short-lived, so a G2 photo is
  rare. The illustration names the grape: bicycles = Каберне Фран, photographer with
  a tripod = Мерло, badminton = Шардоне, easel painter = Сира.
- **Massandra Авторское Саперави**: three signatures (ОСМАНОВ, СИНИЦКИЙ, ВАТАМАН) =
  the 2021 catalogue bottle; two signatures = the 2022 release.
- **Золотая Балка Брют белое**: the oval `Брют белое / РОССИЙСКОЕ ИГРИСТОЕ ВИНО` label
  is current; the round `1889 / БРЮТ / КРЫМСКОЕ ШАМПАНСКОЕ` label is older. The
  capsule and the neck medallion are the same on both, so only the body text
  separates them.
- **Chateau Andre Мерло**: crimson label with the year on its own band (2023) is the
  catalogue bottle; cream label with a coloured drawing, a wild boar and an inline
  year (2022) is older.

### The duplicate-render check, settled (2026-09-16)

Four agents measured normalised pixel correlation against the catalogue render and
reported baselines that did not agree: 0.99 for a known duplicate, about 0.45 for
independent studio shots, up to 0.76 for independent shots, and 0.59 for a case one
agent called a duplicate. The spread made the check useless.

The cause: they correlated the WHOLE frame. A studio render on white carries a large
and variable white margin. Two crops of ONE asset with different margins correlate
poorly; two different photographs with similar margins correlate well. The number was
measuring the padding, not the bottle.

**The correct method: crop both images to the bounding box of the non-white content,
resize both to one size, then correlate.**

```python
a = np.asarray(im); mask = a.astype(int).sum(2) < 720   # non-white
ys, xs = np.where(mask)
im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
```

Measured on the case that prompted this, the grandvostock.ru render of
`chteau-le-grand-vostock-cabernet-sauvignon-reserve-...-14`:

| measure | whole frame | cropped to the bottle |
|---|---|---|
| correlation | 0.591 | **0.982** |
| mean absolute difference | — | 5.8 of 255 |
| bounding box | — | 448x1672 against 443x1667 |

The whole-frame number said "independent photograph". The cropped number says "the
same asset". The agent that withheld the image on a whole-frame 0.59 reached the right
answer for a weaker reason than it had.

Rule for later batches: crop to the bottle, then correlate. A value at or above about
0.95 means the same asset; reject it. Below that, LOOK at the image; do not decide on
the number alone. The earlier whole-frame baselines in this log are superseded.

## 2026-09-16 — The irecommend run: the answer is "irecommend does not cover these wines"

Five agents worked the 33 wines that batches 1 and 2 left short of 3 proposals.
irecommend answered HTTP 521 through both earlier batches, so the question was whether
the 521 wall had been hiding usable photos.

**It was not.** irecommend held a matching product for only **2 of the 33 wines**.
The run produced 13 proposals, and 10 of those came from other sites that the agents
searched after irecommend came up empty.

| agent | wines | irecommend had the wine | proposals |
|---|---|---|---|
| irec-01 | 7 | 2 | 3 |
| irec-02 | 7 | 0 | 0 |
| irec-03 | 7 | 0 | 9 (all from dzen, wildberries, alcoplaza, lublu-vino) |
| irec-04 | 7 | 0 | 1 (alcoplaza) |
| irec-05 | 5 | 0 | 0 |

**The reason, and the rule it gives us.** irecommend indexes the mass-market SKU of a
producer, not the reserve, limited, kosher, or single-vineyard bottle. Measured:
irecommend carries 4 AGORA products of the ~10 in the catalogue; the Abrau sparklings
and the still Купаж, but no reserve still wines; Alma Valley entry level only, no
Reserve tier; Grand Vostock without its whole Reserve line; no Агролайн, no Aratti, no
Bakla Vines at all.

Rule for a later irecommend run: first list the 4 to 6 products the producer actually
has on irecommend, then screen the slice against that list. Most of the effort of this
run went into proving absence one wine at a time.

Two agents proved absence properly rather than assuming it: irec-02 ran positive
controls (a `site:` query that returned exactly one known product, and two genuine
irecommend products surfaced by the same pipeline) before concluding, and irec-05
enumerated each product line through paged queries.

### Mirror detail

On `cdn-irec.r-99.com`: `imagecache/copyright1` is the large render, about 250 kB, and
`imagecache/copyright` the small one, about 50 kB. `copyright2`, `big`, `large` and the
bare `user-images` path all answer 404. `/content/<slug>` and `/srch` answer 301: the
mirror carries image paths only, so irecommend text is unreachable by any route.

The `user-images/<id>/` number is the UPLOADER's user id, not a product id. It does not
group by wine.

### A hazard in the API: `/api/wine-comment` REPLACES the note

It does not append. irec-04 overwrote the notes that hunter-05 and hunter-06 had left
on 7 wines, noticed, and restored them ahead of its own text, so nothing was lost. An
agent MUST read the current note with `GET /api/v1/wine/<slug>` and write the old text
back together with its own. This is worth fixing in the server.

### A session rate limit can kill every agent at once (2026-09-16)

Six cigarpro agents were launched together and all six died on the same HTTP 429
session limit. They were not lost work: 86 proposals had already reached the server,
because a proposal is written the moment it is made. What WAS lost was every agent's
results file and report, because each agent writes that only at the end.

Recovering the state cost nothing extra: `review-labels.json` is the truth, so the
remaining work was computed by asking which slice wines still hold no proposal. 32 of
the 72 wines were finished; 40 were not.

Two rules follow.

1. An agent MUST write its results file after the first wine and update it per wine.
   `work/hunt/cigarpro/HOWTO.md` now says so.
2. Resume by recomputing from `review-labels.json`, never by re-running a whole slice.
   Re-running would make duplicate proposals for wines that were already done.
