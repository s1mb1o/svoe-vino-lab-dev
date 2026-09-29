# ResearchLog

What was learned while this project was built. `ChangeLog.md` records what was done.

## 2026-09-29 — A label rule with a question that one card answers `null`

- Cluster `2d33f12d0b3e` (`aratti-kaberne-po-belomu`, `aratti-kaberne-po-belomu-1`) of
  `gx10-siglip2-so400m-patch16-naflex-p256` has a rule. The rule has the mode `verdict`
  and 0 valid questions.
- The one question asks for the sugar level. The expected answers are `null` (card A)
  and `semi-dry` (card B, `ПОЛУСУХОЕ`).
- `check_rule` in `pipeline/label_rules.py` counts only answers that are not `null`. A
  question is valid only with 2 or more different answers. So this question is not
  valid, and the mode falls to `verdict` (the rule text alone).
- The sheet score gives 0 to a `null` expected answer. A sheet with this one question
  cannot choose card A. The mode `verdict` can choose card A.
- The model left out the vintage (label 2023 and label 2024). Rule 2a of the prompt and
  `named_year` allow a vintage question only when the catalogue names state the years.
  Neither name states a year.
- The page shows the badge `stale`. The rule was built on 2026-09-26T16:14:59+0300 from
  the clusters with `input_hash` `f712cff2…`. The present clusters have `05f41a94…`. 176
  of the 182 rules of this embedding hold `f712cff2…`, so the badge is not specific to
  this cluster. `RuleBook` in `pipeline/cluster_rerank.py` does not read the stale state.
  The re-rank uses the rule.
- The manual pair of these two wines entered `wine_similar` at 2026-09-29T18:38:00Z.
  The clusters were built again at 21:38:43+0300. The key of the cluster did not change.
- A vintage fallback (a year question when no other question is valid) changes 3 of the
  177 `combined` clusters of p256: `c054` (2023/2024), `c116` (2022/2021), and `c117`
  (2023/2022). The years come from the stage-1 label descriptions. In each cluster the
  years are consecutive. The next vintage of the older card then shows the year of the
  newer card, and the fallback sends that photo to the wrong card.
- Both `official-real-photos` of `aratti-kaberne-po-belomu-1` show `2024`. Only one of
  them shows `ПОЛУСУХОЕ`. A year question gives card B for both photos. The present
  verdict rule gives card A for the photo without `ПОЛУСУХОЕ` (entry "Aratti 2024 false
  re-rank" of 2026-09-28).

## 2026-09-29 — NaFlex p512 rot5 references with barcode and cluster rerank

- Setup: `barcode-rerank-siglip2-p512-rot5-seg` against `barcode-rerank-siglip2-p512-seg`.
  The query steps, barcode options, rerank options, and workers are equal. Only the
  reference side changes: 72 angles at 5° steps for each full reference.
- Paired over 1,653 positives of `my`: R@1 82.70 % → 84.15 % (+24 net: 32 gained,
  8 lost). R@5 96.43 % → 97.04 % (+10 net). MRR 0.8922 → 0.9019.
- Negatives (578): false match at rank 1 107 → 103.
- The rerank step acted on 697 queries. In the baseline it acted on 731 queries.
- Confound: 3 of 208 clusters had no usable rule (QwenCloud HTTP 403). One of the 8 lost
  R@1 queries touches these clusters. No gain touches them.
- Without barcode and rerank, plan 82 measured R@1 +0.97 pp for the masked crop with the
  rot5 index (79.84 %). Here the gain is +1.45 pp. The query manifests differ (2,226 and
  2,231 queries). The report is `docs/reports/rotation-index-p512-2026-09-29.md`.
- The 0° full vectors and the label vectors of the rot5 entry equal those of
  `gx10-siglip2-so400m-patch16-naflex-p512` (cosine ≥ 0.99992). So the clusters of the
  two indexes are nearly equal: 203 of 208 combined keys are the same. The 5 other keys
  come from catalogue changes after the p512 cluster build of 2026-09-28.
- `qwencloud-qwen3.8-max` (the `rules_vlm` of `label_rules`) answered HTTP 403
  `AccessDenied.Unpurchased` on 2026-09-29 at about 20:17 and 20:36. A new cluster
  then gets an error record and no rerank.

## 2026-09-29 — F1@1 and F1@5 and the photos outside the dataset

- `match_scoring.f1` computes F1 over the positive photos alone.
- Precision is the hits at depth k divided by the answered positive photos.
- Recall is the hits at depth k divided by all positive photos.
- Every backend of the lab answers each photo. So F1@1 equals R@1, and F1@5 equals R@5.
- F1@5 is empty when the backend returns fewer than 5 candidates.
- A `no_match` photo (`__null__`) is not in F1. It has its own block and a rejection rate.
- 16 of 48 positives of `test-1` are photos of manual wines. The CSV of the organizers
  does not hold these wines. They stay in the metrics as `Active` wines (owner message of
  2026-09-29T19:42:59+0300). Without them, F1@5 of the 7 saved `test-1` runs was higher by
  +0.002 to +0.073.
- Before plan 87, a positive photo of a `Disabled` wine was a certain miss. The index
  holds `Active` wines alone (`matcher_wine`, `embeddings.read_inputs`).
- The removed card `abrau-dyurso-victor-dravigny-brut-shardone-beloe-bryut-12` (page 404)
  can have an active successor `abrau-dyurso-victor-dravigny-bryut`. Nobody checked
  this. So a photo of a removed wine is left out, and it does not become a `no_match` query.
- Read `docs/plans/87_benchmark-dataset-rule.md`.

## 2026-09-29 — Android device HTTP evaluation

- The Pixel 8 debug API used pack `20260929-dis-main` with 2,093 wines.
- The server listened on `*:18088`.
- The Pixel 8 Wi-Fi address was `192.168.86.51` during the test.
- The host could not connect to this Wi-Fi address.
- ADB forwarding from host port 18088 to device port 18088 worked.
- The two Workbench runs therefore used `device_ip=127.0.0.1`.
- The set `my` had 2,232 queries.
- A first unbounded eval run was stopped after 30 answered queries.
- The clean eval run used the first 10 queries.
- It had 10 answers, zero errors, recall@1 0.3, and median latency 4,349 ms.
- Its run is
  `runs/2026-09-29T134112Z-lab-android-device-eval-predict-my-pixel8-smoke-10`.
- The clean match run used the first 10 queries and `k=20`.
- It had 10 answers, zero errors, recall@1 0.3, recall@5 0.6, recall@10 0.9, and median
  latency 4,597 ms.
- Its run is
  `runs/2026-09-29T134204Z-lab-android-device-match-k20-my-pixel8-smoke-10`.
- The same Top-1 result appeared through both response contracts.
- The larger candidate response changed retrieval metrics but did not change model
  inference.
- A live `POST /api/run-jobs` started `android-device-match-k20` with
  `device_ip=127.0.0.1` and `limit=1`.
- The job finished with one answer and zero errors.
- Its `run.json` recorded `http://127.0.0.1:18088/v1/match` as the resolved backend URL.
- Its run is `runs/2026-09-29T135427Z-lab-android-device-match-k20-my`.

## 2026-09-29 — The slow `Save` of the `Add wine` dialog is a cold start of SigLIP 2 @512

Source: owner message of 2026-09-29T12:28:00+0300. Case: the wine
`__vino-shardone-sovinon-blan-kyuve`, created at 12:24:02. Evidence: `build.log` of
`data/catalog/embeddings/gx10-siglip2-so400m-patch16-512/`, the records of
`data/cache/models/`, and `GET /logs` of the gx10 gateway 18081.

- `POST /api/wine` runs plan 78: `manual_wines.add_wine`, then `rebuild_on_run.build`
  for `new_wine_embedding`, then `new_wine_workflow.verify`.
- The time of each step for this wine:
  - SAM3 `segment_multi`: 0.57 s.
  - The build start and the `request` event (2 images): 12:24:02.875 and 12:24:02.918.
  - `POST /v1/embeddings` to the gateway: 37.31 s. The gateway log shows
    `<siglip2-so400m-patch16-512> Health check passed` just before this request.
  - The vector file, `index.json`, and the build `done` event: 12:24:41.058 (0.84 s after
    the answer).
- The same 2-image request took about 0.1 s in the plan 78 trials at 01:16 and 01:19.
- The gateway entry `siglip2-so400m-patch16-512` has `ttl: 1800`. llama-swap stops the
  model after 30 minutes with no request. The next `Save` then waits for a cold start.
- The gateway description states "Cold start ~14 s · warm ~130 ms per 2 images". This
  cold start took 37 s. The cause of the difference is not measured. Possible causes are
  the weights on the NAS share `/mnt/ml`, `preflight-ram.sh`, and the load of other models
  on gx10 at the same time.
- The page sends one POST and renders the new card locally. The page adds no delay.
- `FIX_LATER.md` and `../matcher/docs/KNOWN_ISSUES.md` do not list this problem.

## 2026-09-29 — The alpha channel and the background fill of the SigLIP 2 models

Source: owner message of 2026-09-29T11:12:54+0300. Report:
[docs/reports/siglip2-alpha-background-2026-09-29.md](docs/reports/siglip2-alpha-background-2026-09-29.md).
Script: `scripts/alpha_background_probe.py`. Entries: the 8 SigLIP 2 entries of
`config.yaml` and `gx10-dinov3-vitb16` (control), gateway 18081.

- The gateway drops the alpha channel for each SigLIP 2 entry: an RGBA PNG and its Pillow
  `convert("RGB")` form give the cosine 1.000000 (a synthetic image, and 40 SAM3 cuts for
  each entry). The gateway does not composite on white (0.918–0.964 to the white composite).
- The SigLIP 2 models see the colour under a transparent pixel: red and blue under the same
  transparent area give 0.952–0.986 (DINOv3: 0.986).
- On 40 real cuts, a fill other than white moves the vector by a mean cosine of 0.95–0.98
  (minimum 0.906). SigLIP 2 reacts more to saturated fills than DINOv3. Black and grey are
  the fills nearest to white for SigLIP 2.
- The SAM3 cuts keep different colours under their transparent pixels (1,590 photo pixels
  or a mix, 362 white, 316 black, of 2,270). A raw RGBA cut gives 0.959–0.969 to its white
  form. So the step `white_background` and the transparency check are necessary.
- 1,926 of 2,270 full catalogue images (85 %) have transparent pixels. Of the 344 opaque
  images, 248 have a white or light border.
- The choice of white is the convention of plan 10 ("as on the catalogue images"). No
  retrieval test of another fill exists; the probe measures only the cost of a fill that
  differs from the index fill.

## 2026-09-29 — Hand-aware package selection of the query photos: effect on `my`

Owner question of 2026-09-29T11:28:17+0300: does the package cut use hands when a photo
shows several bottles?

- Two rules select the package of a photo.
  - Rule 1 is `derive.package_instance`. The SAM3 texts are `wine bottle, can, packet,
    box`. The largest wine bottle wins. A bottle that is printed on a packet or on a box
    gives the win to that packet or box. With no bottle, the largest instance wins. The
    catalogue images use this rule.
  - Rule 2 is `pipeline/main_scene.py` version 1. The SAM3 texts are `wine bottle, can,
    packet, box, hand`, in one request. A weighted score ranks the packages. With a hand,
    `hand_contact` has the weight 0.40. Its value is the share of the package box inside a
    hand box, times 1.5, not more than 1, times the area gate
    `min(1, relative_area / 0.4)`. Without a hand, the scene weights apply: area 0.28,
    center 0.24, confidence 0.14, sharpness 0.12, shelf isolation 0.10, mask fill 0.08,
    edge visibility 0.04. The hand signal is a box overlap. It does not prove a grip.
- Each configured lab pipeline uses rule 2 for the query photos:
  `embedding_run.build_pipeline_backend` sets `scene_selection=True`. The runs show rule 2
  from 2026-09-28T02:06+0300 (working tree). Commit `22eb086` holds it.
- The best run `2026-09-27T210917Z-lab-barcode-rerank-siglip2-512-crop-my-plan68-a`
  (R@1 85.55 %) finished at 2026-09-28T00:16+0300. It used rule 1. No run of
  `barcode-rerank-siglip2-512-crop` on `my` uses rule 2.
- Run `2026-09-28T012451Z-lab-siglip2-p512-crop-my` (rule 2, 2,226 queries): a hand in 439
  photos, no hand in 1,715 photos, the alpha or the white rule in 72 photos. One package
  candidate in 1,782 photos, no candidate in 72 photos, two or more in 372 photos.
- Two pairs of runs of one pipeline: rule 1 on 2026-09-27, rule 2 on 2026-09-28. The
  comparison uses the 1,453 positive photos with the same `image_sha256` and slug in both
  runs. A different package is a box IoU below 0.8.

| Pipeline | Different package | Of these, with a hand | Fixed | Broken | R@1 rule 1 → rule 2 |
|---|---|---|---|---|---|
| `siglip2-p512-crop` | 13 | 2 | 2 | 2 | 80.59 % → 81.07 % |
| `siglip2-p256-crop` | 13 | 2 | 2 | 2 | 76.12 % → 77.49 % |

- On `my`, rule 2 selects a different package for 0.9 % of the photos. Its net effect on
  R@1 is zero. The R@1 change comes from the photos with the same package. The index
  changed between the runs: 4,054 current items and 127 missing items on 2026-09-27,
  4,642 current items and 0 missing items on 2026-09-28.
- Limit: `my` holds few photos with a hand and several similar bottles. This comparison
  does not measure rule 2 on shelf photos.

Follow-up (owner question of 2026-09-29T11:35:25+0300: is it safe to use `hand`?):

- The photos with a changed package and a changed result (IoU below 0.8, rank 1 gained or
  lost). In none of them does the hand signal decide the choice.
  - `siglip2-p512-crop`: 2 photos broken, 2 photos fixed. Both broken photos have no hand.
    In both, the scene weight `center` selects a smaller bottle near the center instead of
    the largest bottle: `vinodelnya-raevskoe-renessans-krasnoe-kaberne-sovinon-suhoe-13/01_conf095.png`
    (rank 1 → 8) and `fanagoriya-velvet-season-risling-beloe-sladkoe-12/03_conf095.jpg`
    (rank 1 → 2). One fixed photo has a `box` that wins over the bottle (rule 2 gives no
    priority to a bottle). The other fixed photo shows a shelf with 52 candidates and 14
    hands; `hand_contact` is 0.003 for the selected bottle, so `center` and `area` decide.
  - `siglip2-p256-crop`: the same 2 broken photos. 2 photos fixed; in both, a `box` wins.
- SAM3 time of the package cut with no cache hit (`sam3-package`, `cached: false`, 1
  worker): run `2026-09-27T233939Z-lab-siglip2-p256-crop-my` with `hand`, 1,523 calls,
  median 1,500 ms, p95 5,888 ms. The runs with the old texts have few such calls: 21 in
  the three runs with 5 or more (medians 2,077 ms to 7,042 ms). These data do not show
  the time that the text `hand` adds.
- Crop variants in the lab, rule 2: the box cut is better than the cut with a white
  background outside the mask. `siglip2-p512-crop` 79.48 % against `siglip2-p512-crop-seg`
  78.87 %; `siglip2-p256-crop` 75.77 % against `siglip2-p256-crop-seg` 74.98 %;
  `barcode-siglip2-p256-crop` 77.53 % against `barcode-siglip2-p256-crop-seg` 76.68 %.
  The matcher option `hand_selection: true` uses the white background outside the mask.

## 2026-09-29 — Max-over-rotation on the real photos of `my` (gate G0 of plan 82)

The offline 5° vectors (`work/rotation-index/`, 2,270 images × 72 angles, 160,560 vectors,
0 problems, 4,953 s at 32.4 vectors/s) replayed with the saved query vectors of the two
usual NaFlex p512 pipelines (`scripts/rotation_index_eval.py`; 2,226 queries: 1,647
positive, 579 negative):

| Query | Catalogue | R@1 | R@5 | False match at 1 |
|---|---|---:|---:|---:|
| as-is | 1 vector | 74.26 % | 94.11 % | 115 |
| as-is | 0°–355°, step 5° | 77.23 % | 95.45 % | 116 |
| as-is | 0°–180°, step 5° | 76.93 % | 95.39 % | 110 |
| crop | 1 vector | 79.48 % | 96.11 % | 111 |
| crop | 0°–355°, step 5° | 79.66 % | 96.17 % | 102 |
| crop | 0°–180°, step 5° | 79.60 % | 96.11 % | 105 |

The lab runs of plan 82 with the lab index `…-p512-rot5` agree within 2 queries (as-is
77.35 %, crop 79.60 %) and add the masked crop: `crop-seg` 78.87 % → 79.84 % R@1 (+0.97
pp), the best R@1 of all configurations. The masked crop is closest to the rotated
catalogue images (a package on white).

The 1-vector replay repeats the official runs exactly. The rotated catalogue helps the
whole-photo query most (+2.97 pp R@1, +49 queries). With the SAM3 crop the gain is small
(+0.18 pp), and the false matches at 1 fall from 111 to 102. The gx10 NaFlex p512 model
gives about 26–34 images per second; the GPU is at about 96 % during a build, so more
parallel requests do not make the build faster.

## 2026-09-29 — Storage of `data/catalog/embeddings/` and use of the prepared images

Check of 2026-09-29, 07:50. The directory holds 17 GB. The vectors are small: one
`vectors-*.npy` of 4,642 float32 rows of 1,152 values is 21 MB. One `index.json` is 2 MB.
The prepared images in `images/` use almost all of the space: about 1.5 GB (1.4 GiB in
`du -sh`) for each of the 12 gx10 and local indexes, 55,701 files, 17.8 GB in total.

The prepared images of the 12 indexes are the same images. The `derivative_sha256` of each
common item is equal in all 12 indexes. A random sample of 40 names had equal bytes in all
12 directories. There are 4,527 unique derivatives. So about 16 GB are copies. The files
are separate inodes, not hard links. The T7 volume is APFS and had 582 GB free.

A prepared image is a function of the cut `data/catalog/cuts/<derivative_sha256>.png` and
of the steps: the white background and the resize. `scripts/rotation_index_build.py`
makes it again from the cut and compares the pixels (`pixels_equal_index`).

The matching step reads the vectors, not the pixels. The prepared images have these uses:

- `embeddings.item_status` gives the state `current` only when the prepared image exists.
  The lab catalogue of `embedding_run.py`, `catalog_copy.py`, `matcher_bundle.py`,
  `clusters.py`, `new_wine_workflow.py`, and the build use this state. If a directory
  `images/` is deleted, each item becomes `stale`. The lab then has no catalogue vector
  for that index, and the next build sends each item to the gateway again.
- The Embeddings page, the cluster pages, and the step popup of `/runs` show them as
  thumbnails.
- `scripts/rotation_index_build.py` and `scripts/rotation_similarity.py` read them.

The prod matcher does not read them. `catalog_copy.py` copies no prepared PNG file, and
`matcher/catalog.py` reads only `catalog.sqlite3`, `index.json`, and the vector file.

By the rules of plan 75, the prepared images are cache data. They are derived data.
`index.json` records the steps. `catalog/images/` and `catalog/cuts/` hold the inputs. So
the catalogue directory holds all the data that is necessary to make them again, and the
matcher does not need them. Stage 3 of plan 75 moves them to `cache/prepared/`, and the
status of an item then does not depend on its PNG file. Stage 3 is not started. Until
stage 3, a missing PNG file makes the item `stale`, and a build sends the item to the
model again. Exception: the index `android-siglip2-base-224-dis-white` runs the DIS model
in the step `segment_dis`, and no other file stores the DIS result. A new preparation of
these images runs DIS again. The last full build of this index took 3,833 s for 2,271
items. That time includes DIS and the embedding.

## 2026-09-29 — No segmentation, DIS, SAM3, and SigLIP2 SO400M compute levels

The complete plan 79 matrix used 2,226 `my` queries and 2,270 catalogue sources.
Barcode lookup was disabled. The 18 cells produced 80,898 vectors.
SAM3 improved R@1 against no segmentation for every tested SigLIP2 SO400M model.
The gains were 2.73 to 12.33 percentage points, and each paired R@1 test was significant.
SAM3 with fixed 512 was best at 81.42% R@1 and 96.66% R@5.

No segmentation with fixed 512 reached 78.69% R@1 and 95.75% R@5.
It was 2.73 pp below SAM3 at R@1, but the 0.91 pp R@5 difference was not significant.
It was 4.13 pp above DIS fixed 512 at R@1.
No segmentation also had higher R@1 than DIS with fixed 384 and NaFlex p1024.
Thus DIS did not give a consistent improvement over the full source image.

Model size had different effects on the input methods. DIS and SAM3 had strong gains from
NaFlex p256 to p512, then small and non-significant R@1 gains from p512 to p1024.
Without segmentation, the NaFlex p512 to p1024 gain was 5.34 pp and was significant.
Fixed models kept a significant gain from 384 to 512 with all three input methods.
Without segmentation, fixed 512 was 1.88 pp better than NaFlex p1024 at the comparable
high level.

DIS failed to find the object in five positive queries. SAM3 found an object in all
queries. Only three of these five queries were R@1 hits in the best SAM3 cell. They
explain 0.18 percentage points of its 6.86 percentage-point gain over DIS. The crop
difference on shared successful queries caused most of the gain.

Negative rejection had no consistent relation to input method or model size.
No pairwise negative-rejection difference against no segmentation was significant.
No SAM3-versus-DIS negative-rejection difference was significant. Read
[the model-matrix report](docs/reports/2026-09-29_segmentation-model-matrix.md).

## 2026-09-29 — test-1 shop photos and WineHack catalogue

The 54 test-1 shop photos have no source ground truth. Independent review found 35
photos with a catalogue card, 13 identifiable products without a matching card, and 6
multi-product scenes with no unambiguous target. There are no exact SHA-256 matches with
the previous lab images. The source's 93.17% result uses synthetic transformations of
catalogue photos and is not a field result.

On the 35 catalogue matches, `siglip2-p512-as-is` gives 31.4% family-aware Top-1 and
51.4% Top-5. The package crop gives 57.1% Top-1 and 80.0% Top-5. The current reranker
gives 71.4% Top-1 and 80.0% Top-5. Thus the crop and reranker fix ordering and scene
noise, but seven truths remain outside Top-5. All three profiles return a false card for
all 13 no-match products. Open-set refusal and catalogue coverage are the main field
gaps. Read
[the test-1 report](docs/reports/2026-09-29_test-1-dataset-benchmark.md).

The three WineHack catalogue files use the same 2,103 official slugs as the lab.
All eight source fields match our catalogue for every official slug. Their source CSV
has 2,044 exact duplicate rows. Their enriched CSV reduces it to 2,103 rows, but 58
image-file groups assign one file to multiple wines and cover 207 slugs. Its taste
matrix and pairings are rule-derived. The SQL creates 4,533 pairings and gives all
2,103 wines a NULL price. Its `roskachestvo_score` is an artificial, process-dependent
Python hash value. We can reuse the enrichment schema, but not these values or image
links. Read
[the WineHack report](docs/reports/2026-09-29_winehack-catalog-comparison.md).

## 2026-09-29 — Limits of the lab index for rotated reference vectors

Source: a read-only code survey for the owner message of 2026-09-29T02:02:13+0300 (rotated
catalogue indexes of NaFlex p512). Facts, with the code places:

1. An index item is keyed by (source_sha256, view): `embeddings.plan_items`,
   `embeddings.item_status` (the last record wins), the pruning of
   `build_embeddings.run`, `embedding_run.Catalogue` and `candidate_items`, `run_steps`,
   `clusters`, and `matcher_bundle._validate_records` (rejects repeats). So several
   vectors for one image and one view collapse to one, or are pruned by the automatic
   rebuild before a run (`rebuild_embeddings_on_run: true`).
2. The ranking maths already takes the maximum over the rows of a wine
   (`Catalogue.rank`, `matcher/bundle.py`), so more rows per wine work in the maths.
3. The builder writes one prepared PNG for each item, and an item is current only when
   its PNG exists. For 2,270 full images: 360 angles ≈ 817,200 vectors, about 215 GiB of
   PNG, 3.8 GB of vectors; 72 angles ≈ 163,440 vectors, about 43 GiB of PNG, 0.75 GB.
4. There is no rotation step. The view names are fixed to `full` and `label`.
5. `results.jsonl` of a run lists every row of each candidate; with 360 rows per image it
   would grow to several GB.
6. No query vector is cached: each new pipeline embeds all photos of `my` again (2,226
   queries on 2026-09-29: 1,647 positive, 579 negative).
7. Throughput of p512 on the gateway: 12 to 23 images per second on the model side, so
   817,200 vectors take about 10 to 19 hours and 163,440 vectors about 2 to 4 hours
   (estimate).
8. Latest results on `my` (2026-09-28, one worker): `siglip2-p512-as-is` R@1 74.26 %,
   R@5 94.11 %; `siglip2-p512-crop` R@1 79.48 %, R@5 96.11 %.

## 2026-09-29 — Rotation tests of DINOv3

Source: owner message of 2026-09-29T02:02:13+0300. Report:
[docs/reports/rotation-dinov3-2026-09-29.md](docs/reports/rotation-dinov3-2026-09-29.md).
The tests of the SigLIP2 rotation report, with `gx10-dinov3-vitb16` and
`gx10-dinov3-vitl16`. With one vector, DINOv3 is much more sensitive to a large rotation
(mean 0.63–0.65 over the rotated angles; SigLIP2 0.77–0.85) and less sensitive to the
black background (0.987–0.988 at 0°). With reference vectors over the full circle it
reaches higher scores than SigLIP2 (step 1°: 0.996–0.997 white with offset, 0.979–0.987
black), and it tolerates a small angle error better (0.995–0.997 at 0.5°). DINOv3 has no
difference between one image and a batch in a request.

## 2026-09-29 — Rotation and background sensitivity of SigLIP2 so400m

Source: owner message of 2026-09-29T01:10:49+0300. Report:
[docs/reports/rotation-similarity-2026-09-29.md](docs/reports/rotation-similarity-2026-09-29.md).
One catalogue main image (`avtohtonnoe-vino-kryma-beloe-suhoe`, 270 x 1024) was rotated
counter-clockwise in steps of 5°. The canvas grew to hold the rotated image, and the bottle
kept its pixel size. The cosine to the indexed `full` vector was measured on a white and on
a black background.

1. A small rotation costs much. At 1°, the cosine is 0.92 to 0.98. At 5°, it is 0.87 to
   0.95. The diagonals (115° to 135°, 225° to 235°) give the minimum, 0.70 to 0.78. The
   lossless angles 90°, 180°, and 270° give peaks of 0.82 to 0.95.
2. Most of the loss comes from the larger canvas, not from the rotation. The unrotated
   bottle, padded on white to the 45° canvas, loses 0.09 to 0.19. The rotation adds 0.00
   to 0.07.
3. The black background costs 0.017 to 0.032 at 0°, and 0.006 (fixed 256) to 0.034
   (NaFlex p1024) on average over all angles.
4. Self-retrieval over the whole index: fixed 256 and fixed 384 keep rank 1 at all 72
   angles on both backgrounds. NaFlex p512 loses rank 1 at 67 and 69 of 72 angles. The
   nearest other wine is a red blend of the same producer with the same label design.
5. There is no fixed-size model "siglip2-1024". The gateway serves the fixed sizes 256,
   384, and 512.
6. NaFlex p256 gives another vector when a request holds one image: cosine 0.994173 to the
   index vector of the same image, and 1.000000 in a batch of 2 or more. The other entries
   give 0.99981 or more. The matcher and the lab runs send one query image in each
   request, and the index was built in batches of 16. This was measured on one image. The
   server cause is not known.

Consequence: a tight, upright crop matters more than the background color. Deskewing a
rotated bottle before the crop could recover most of the loss. This is not tested.

Part 2 (owner message of 2026-09-29T01:34:10+0300): 10 reference vectors of the same
image (white, rotated 0° to 45° in steps of 5°), the score is the maximum cosine. The mean
over the rotated angles rises by 0.10 to 0.15, and the minimum rises from 0.70–0.78 to
0.84–0.91. The best reference is often the angle with the same canvas size as the query
(180° − θ has the canvas of θ). The multiples of 90° do not gain: the best reference is
0°, and 180° stays at 0.87 to 0.92. The rank in this test is optimistic, because only
this wine got the extra vectors. A fair test needs the extra vectors for every wine.

Part 3 (owner message of 2026-09-29T01:44:56+0300): six reference sets. The range of the
reference angles matters more than the step: 72 vectors over the full circle (step 5°)
give a mean of 0.964–0.982 on black and 0.963–0.976 on white with a +2.5° query offset;
91 vectors over 0°–90° (step 1°) give 0.940–0.954 and 0.958–0.966. The step 1° over the
full circle raises the white offset queries to 0.981–0.990. On black, the step adds 0.001
or less: the remaining loss of 0.02–0.04 comes from the background, and more angles cannot
remove it. White queries on the reference grid are trivial (1.000), so the offset queries
are necessary for the white case.

Part 4 (owner message of 2026-09-29T01:56:01+0300): full-circle sets with the steps 3°,
8°, 9°, 12°, computed from the saved 360 vectors. The score by the distance to the
nearest reference angle falls fastest in the first degree (white: 0.979–0.989 at 0.5°,
0.967–0.982 at 1°) and is almost flat past 2° (0.950–0.972 at 3° to 4.5°). So 30 vectors
over the full circle (step 12°) give the same or a higher mean than 91 vectors over
0°–90° (step 1°). The mean of one set is not monotonic in the step, because the distances
from the query grid (multiples of 5°) to the reference grid change irregularly; compare
sets by the distance, not by the step.

## 2026-09-28 — Android SigLIP2 Base 224 and DIS contracts

The Android application uses `vit_base_patch16_siglip_224.v2_webli`. The model returns
768 values. The LiteRT conversion identifies the source checkpoint as
`timm/vit_base_patch16_siglip_224.v2_webli`. Revision
`4c3661e5ac879a276ddc5ddc6d3f0ecc78fd5d82` was the present revision during this work.

The GX10 `transformers` backend loads this timm checkpoint through `AutoModel`. It returns
`pooler_output` with shape 1 by 768. Bfloat16 does not work in the present service because
the processor returns float32 input while the model bias is bfloat16. Float32 returns a
finite vector. The service normalizes it to length 1.

The Android LiteRT file is `siglip2_base_224_fp16.tflite` from
`litert-community/SigLIP2-base-patch16-224` revision
`509b5cbcf1a849f37696be08f8297c6cd3050bf4`. Its SHA-256 is
`a30ebb7b3ee15eaa68a18f9ab6a2ed740c15c343d25d898dc482317473320854`.
The GX10 timm processor uses `crop_pct=0.9`. Thus it resizes a 224 by 224 prepared image
to 248 by 248 pixels and takes the centered 224 by 224 crop. A 32-image comparison
without this crop had cosine values from 0.8103079 to 0.9761065. The same comparison
with this crop had cosine values from 0.9999990 to 0.9999999. The Android encoder now
uses the same crop.

The Android DIS model is `litert-community/DIS-ISNet-LiteRT`, file `dis.tflite`, at
revision `1b966dbe2f33bd5ca1299cf94fbab59265210b6b`. It accepts RGB float32 NCHW input
with shape 1 by 3 by 1024 by 1024. Its normalization is `x / 255 - 0.5`. The output is
one 1024 by 1024 soft mask. The model card calls this output an alpha mask. The measured
TFLite output of a real catalogue image was in the interval 0.5 to 0.731. Thus threshold
0.5 selected the full image. The reference DIS inference code applies per-image min-max
normalization before it uses the mask. The Android and workbench paths now apply this
normalization. The crop then uses threshold 0.5, rejects fractions below 0.005 and above
0.995, adds a 4 percent box margin, composites the normalized soft mask on white, and
centers the crop on a white square.

The shared llama-swap gateway was not reloaded. Another active project used SAM3. A
reload would unload that model. The build uses an isolated float32 endpoint on GX10
port 5997 instead.

## 2026-09-28 — The content of `data/`, and a split into catalogue, test data, and cache

The owner asked on 2026-09-28T16:21:20+0300 for three directories: one for the catalogue
and the embeddings, one for the test data, and one for the caches and the intermediate
files. A copy of the catalogue directory MUST be enough for the matcher, so that no bundle
build is necessary. These facts come from a read-only check. The database has schema 30.

### Content

- `data/lab.sqlite3` has a size of 27 MB. Its journal mode is `delete`.
- The catalogue tables are `wine_catalog` (2,104 rows), `wine_image` (2,421), `wine_code`
  (136), `wine_atlas_binding` (452), `wine_comment` (173), `wine_beverage_type`,
  `wine_favorite`, `wine_similar`, `wine_tag`, and `website_refusal`.
- The image tables are `image` (10,544 rows), `image_derivative` (4,681),
  `image_description`, `image_detail`, `image_label_description`,
  `image_derivative_absence`, `image_label_description_failure`, and `image_tag` (761).
- The test tables are `test_set` (5 rows), `test_photo` (4,600 rows for 3,474 files),
  `test_photo_comment` (1,637), and `test_variant` (189). They use about 3 MB.
- The table `image` is one register for all image files. The column `folder` names the
  directory: `main` 2,071 rows, `patched` 23, `additional` 302, `cropped` 4,674, and
  `testset` 3,474.
- `data/images/main` (141 MB), `data/images/patched` (20 MB), and
  `data/images/additional` (1.2 GB) are in git. `data/images/cropped` (3.2 GB) and
  `data/images/testset` (0.8 GB) are not in git.
- `data/embeddings/` has 12 directories. Each directory has `index.json` (2 MB), one
  vector file (14 MB to 21 MB), `build.log`, and `images/` with 4,642 prepared PNG files
  (1.4 GB). Four directories also have cluster files.
- The prepared PNG files are the same in the 12 directories. Each of the 4,642 files has
  the same size in the 12 directories. A sample file has the same MD5 in the 12
  directories. The 12 embeddings have the same `views` steps. The 12 copies use 17 GB.
- `embedding_hash` includes `view_config_hash`. `view_config_hash` includes the backend
  and the model. Thus `embedding_hash` is different for each embedding. A shared store of
  prepared PNG files needs a key that does not include the model.
- `data/cache/` holds the model call cache: `sam3`, `barcode`, `qwen3.5-9b-nvfp4`,
  `qwen3.8-max`, and `grounding-dino-base`. The code sets `model_cache.ROOT` to
  `data/cache/`. The configuration cannot change it.
- `data/backups/` holds 13 copies of the database and 2 copies of cluster files. The
  total is about 0.2 GB.
- `labdb.image_store` and `embeddings.embeddings_root` make the other data paths from
  `database_file` in `config.yaml`. 23 code files use these helpers or
  `model_cache.ROOT`. 37 code files open SQLite.

### Links between the catalogue and the test data

- `test_photo.place` and `test_variant.wine_slug` hold a wine slug. No foreign key exists.
  4,596 of the 4,600 `place` values are catalogue slugs.
- `test_photo.sha256` references `image`. Each of these rows has the folder `testset`.
- One test photo is also a catalogue image (`wine_image`, type `label_back`). It has one
  label cut and one row in each description table.
- One cut file (folder `cropped`) is also a catalogue image (type `main_patched`). It is
  the source of two other cuts.
- Each of the 761 `image_tag` rows belongs to a test photo.
- Six code files use the test tables. Four of these files also use catalogue tables:
  `pipeline/benchmark.py`, `pipeline/testsets.py`, `pipeline/lab_server.py`, and
  `pipeline/import_testset.py`.

### Cuts

- SAM3 or the alpha channel made 4,680 of the 4,681 cuts. One cut is a manual polygon.
  The column `settings` records the parameters of each cut.
- `embedding_hash` includes the SHA-256 of the cut. A new cut file with different bytes
  makes the items of all embeddings stale.

### Matcher and copy

- The bundle builder (plans 72 and 74) applies lab rules. It keeps the `Active` wines
  only. `main_patched` replaces `main`. A close-up is an item of the view `label` only.
  The builder keeps the current items only. It makes the card fields `page_url`,
  `image_url`, and `qr_urls`.
- The prod matcher reads a bundle of 25 MB in
  `/srv/svoe-vino-lab/prod/matcher/data/bundles/`. The file system `/` on gx10 has
  336 GB free (check of 2026-09-28).
- A file copy of the database during a write is not safe in the journal mode `delete`.
  The copy can hold a part of a transaction. A safe copy uses the SQLite backup API or
  `VACUUM INTO`, or a stopped lab server.
- A copy of an embedding directory during a build can get an `index.json` that names a
  vector file that the build deleted.

### Proposal (waiting for the owner)

The target layout is the same for each approach:

```text
data/
  catalog/    catalog.sqlite3, images/{main,patched,additional}/, cuts/, embeddings/<name>/
  testsets/   testsets.sqlite3, images/
  cache/      models/ (the model call cache), prepared/ (one prepared PNG per image and steps)
  backups/    copies of the databases
```

- Approach A: split the database into `catalog.sqlite3` and `testsets.sqlite3`. The lab
  attaches the catalogue database to the connection of the test database. The register
  of the test photos gets a different table name, so that each table name stays unique
  after `ATTACH`.
- Approach B: move the files, and keep one database as `catalog/catalog.sqlite3`. The
  test tables stay in this database. Only the test photo files move to
  `testsets/images/`. The split of approach A MAY follow later.
- Approach C: keep one working database. The lab writes `catalog/` as a snapshot after
  each change. This approach keeps a publish step.
- In each approach, the matcher reads `catalog.sqlite3` through fixed SQL views, and it
  reads `index.json` and the vector file of one embedding. Then the bundle builder is not
  necessary. A copy script refuses a copy during a build, copies the database with the
  SQLite backup API, and copies the other files with `rsync`.

Open questions: the approach; the place of the cut files (`catalog/cuts/` or `cache/`);
a flatten of the schema at the split (rule 12); the time of the move, because other
sessions change the matcher and the deploy files now.

The owner selected approach B now and the split of approach A later
(2026-09-28T16:50:22+0300). `docs/plans/75_data-layout.md` records the decisions and
the result of stage 1.

## 2026-09-28 — The gx10 service `qr-scanner` compared with `pipeline/barcode.py`

- The service is `POST http://192.168.86.14:18081/upstream/qr-scanner/scan` on the gx10
  llama-swap gateway. The documentation is `~/Admin/gx10/docs/inference/qr-scanner.md`.
- A request has two fields: `image` and `engine`. The values of `engine` are `auto`,
  `zxing-cpp`, `zxing-cpp-sr`, and `boofcv-qr-cpp`. A request has no other option.
- The engine `zxing-cpp` of the service is not the decoder of the lab. The service uses
  zxing-cpp 3.0.0. It calls `read_barcodes(gray)` with the defaults: all formats, one
  binarizer, and `try_downscale` on. The lab uses zxing-cpp 2.3.0, two binarizers
  (`LocalAverage`, `FixedThreshold`), `try_downscale=False`, and a list of formats.
- The lab keeps 2.3.0 because 3.1.1 can stall on an excise mark beside an EAN. No test
  measured 3.0.0 on that case.
- The service does not scale the photo and has no tile scan. The lab can scale the photo
  and cut the tiles before each request.
- The service cannot read `wine_code`, so it cannot stop at a unique hit. The lab can
  stop between two tile requests.
- `auto` always runs the step `sam3-vlm` (SAM3 and qwen3.5-9b, 8–15 s, load on the GPU).
  Only the server flag `--no-sam3-vlm` stops the step. That flag is in
  `~/llama-swap/config.yaml` on gx10. Each save of that file unloads every model.
- `GET /health` gives the library versions. It does not give the version of `server.py`
  or the server flags (`--sr-max-side`, `--unwarp-budget`, `--no-sam3-vlm`,
  `--vlm-model`). A cache key of the lab cannot see a change of these flags.
- The format names are different. The service gives `EAN-13`, `Code 128`, and `QR Code`.
  The lab uses `EAN13`, `Code128`, and `QRCode`.

## 2026-09-28 — Usage audit of `scripts/01_search.py` to `scripts/09_apply_moves.py`

- The lab server does not import or execute these nine scripts. They belong to the old
  test-set builder and the old JSON review tool.
- `scripts/run_pipeline.py` executes stages 02, 03, and 04. `scripts/finalize.sh`
  executes stages 05, 06, and 07 through the driver and direct calls. The README tells a
  user to execute stage 01, stage 08, and stage 09 manually.
- The default lab configuration does not contain the key `dataset`. Stages 01 through 08
  stop during import when they use the default `config.yaml`. Stage 09 loads the same
  configuration after its argument parser. The legacy scripts need
  `SVOE_VINO_REVIEW_CONFIG=config.old.yaml`.
- The two wrapper scripts do not set `SVOE_VINO_REVIEW_CONFIG`. Their documented commands
  do not work as written in this repository. All nine scripts accept `--help` when the
  legacy configuration variable is set.
- `scripts/04_verify.py` is still a code dependency. `scripts/bench_vlm_models.py`,
  `tests/test_model_cache.py`, and `tests/test_vlm_config.py` import its prompt, parser,
  or backend builder. The tests set the legacy configuration variable.
- `scripts/08_variants.py` and `scripts/09_apply_moves.py` are also part of documented
  legacy review workflows and smoke tests. The old review server has an Apply action that
  provides the same move and copy operation as stage 09.
- Historical logs show real use of stages 01 through 07. Stage 01 searched all 2,018
  wines and found 141,071 candidates. The stage 2 to 4 logs show completed download,
  embedding, and verification runs. `work/report_stats.json` records 1,984 kept photos
  and 1,974 official API checks from stages 05 and 07. The ChangeLog records a stage 06
  top-up run. The generated variant file has an update time of 2026-09-15.
- Eight scripts are byte-identical to the copies in `../svoe-vino-testset/scripts/`.
  Stage 04 differs. The lab copy adds the shared model-call cache and named VLM
  configuration.
- The nine files are not dead history, but they are not part of the current lab runtime.
  A cleanup can remove the legacy builder from this repository only after it changes the
  wrappers, README, smoke tests, and stage-04 import users, or moves those users to the
  canonical `svoe-vino-testset` implementation.
- Plan 70 completed that cleanup. The reusable stage-04 logic now belongs to
  `pipeline/wine_identity_vlm.py`. The numbered stages and their two drivers are gone.
  Current source, configuration, README, and smoke-test references are gone. Historical
  records keep the old names because they describe completed work.

## 2026-09-28 — Aratti 2024 false re-rank

Run `2026-09-27T221032Z-lab-barcode-rerank-siglip2-512-crop-official-real-photos`,
query `q-000003`.

- The embedding search was correct. `aratti-kaberne-po-belomu-1` was rank 1 at 0.8286.
  `aratti-kaberne-po-belomu` was rank 2 at 0.8082.
- Cluster `2d33f12d0b3e` used a verdict rule. The rule assigns the label with
  `ПОЛУСУХОЕ` to `aratti-kaberne-po-belomu-1`. It assigns a label without the text to
  `aratti-kaberne-po-belomu`.
- The catalogue image of `aratti-kaberne-po-belomu-1` shows `2024` and `ПОЛУСУХОЕ`.
  The test photo shows `2024`, but it does not show `ПОЛУСУХОЕ`.
- The cached SAM3 label cut is correct. It contains the complete front label and its
  bottom edge. The missing sugar text is not a crop error.
- The verdict VLM answered card A, `aratti-kaberne-po-belomu`. The re-ranker moved that
  card to rank 1 and moved the correct 2024 card to rank 2. The two score positions stay
  fixed, so the cards received 0.8286 and 0.8082 after the swap.
- The rule generator did not use `2024`. The catalogue names and slugs do not state
  vintage years. Its policy forbids a label-only year as a stable product feature.
- The historical run read the p256 cluster and rule files. The current p512 rule has the
  same one-sided `ПОЛУСУХОЕ` test. A switch to p512 rules alone does not prevent this
  failure.
- The unsafe condition is the use of missing text as positive evidence. A verdict rule
  with one expected text and one null expected value SHOULD return `unsure` when the
  text is absent. This keeps the correct embedding order for package variants.

## 2026-09-28 — Main-scene selection for a held can

Plan 69. The two source photos are `PXL_20260926_175323263.jpg` and
`PXL_20260926_175335432.jpg` from `СуперЛента-20260928`.

- The failure came from the selector, not from SAM3. SAM3 found the can in both photos.
  The old `derive.package_instance` rule selected a bottle whenever it found a bottle.
  It ignored a can even when the can was the largest and most confident instance.
- The first photo has 21 package candidates. The second photo has 25 package candidates.
  SAM3 also finds one hand in each photo when the prompt includes `hand`.
- The hybrid selector gives the first can a score of 0.9727. The next shelf bottle gets
  0.3917. The second can gets 0.9766. Its next shelf bottle gets 0.3459.
- A package-box and hand-box overlap alone is unsafe. A large hand box contains some
  small shelf bottles. The hand-contact signal therefore has a relative-area gate.
- The no-hand branch uses relative area, center position, detector confidence,
  sharpness, shelf isolation, mask fill, and edge visibility. This branch selects the
  main bottle when a scene holds many bottles.
- The complete pipeline `barcode-rerank-siglip2-512-crop` selects the can in both photos.
  It ranks `abrau-dyurso-fizz-beloe-bryut` first with scores 0.8333 and 0.8997.
- Live `/api/recognize` responses expose 21 and 25 candidate audit records in the step
  `Package selection and cut`. Each selected can has all eight signal values and weighted
  contributions. The mask body is not present in the audit.
- The catalogue-image processor keeps the old bottle-first rule. The new selector applies
  to query photos of configured embedding pipelines. A selector version in the run
  specification keeps old-run replay compatible.

## 2026-09-28 — The first self-test of `gx10-siglip2-so400m-patch16-512`

Session drink-atlas-workspace-49 [549156]. Plan 67
([docs/plans/67_embedding-selftest.md](docs/plans/67_embedding-selftest.md)). Run
`runs/2026-09-27T211801Z-lab-selftest-gx10-siglip2-so400m-patch16-512-dataset/`: 2,401
images of Active wines, 211 s with 4 workers, no errors. The index had 4,622 current and
3 failed items. Left out: 5 images of Removed wines and 1 of a Disabled wine.

| Image type | Images | Rank 1 | Rank 2 to 5 | Not in top 5 |
|---|---|---|---|---|
| `main` | 2,094 | 2,062 | 24 | 8 |
| `main_patched` | 21 | 21 | 0 | 0 |
| `full_front` | 100 | 100 | 0 | 0 |
| `full_back` | 85 | 85 | 0 | 0 |
| `label_front` | 2 | 2 | 0 | 0 |
| `label_back` | 99 | 62 | 21 | 16 |

- 69 misses in all: 32 `main` and 37 `label_back`. 27 of the `main` misses are files of
  2 or more Active wines. A shared file gives
  the same vector to each wine, so one of the wines is a miss. This is the known list of
  shared images, not an error of the index.
- 37 misses are `label_back` close-ups. A close-up searches the package space with the
  image as it is (owner answer), so a weak result is expected there.
- 3 misses are the original `main` of a patched wine
  (`abrau-dyurso-udelnoe-vedomstvo-imperatorskoe-beloe-bryut` rank 7,
  `czitronnyj-magaracha` rank 6, `rubin-golodrigi` rank 2). The index holds the
  `main_patched` of these wines alone, so the original photo differs from the patch.
- `vibes-cabernet-franc-pinot-noir-pino-nuar-krasnoe-suhoe-125`: rank 2. Its image and
  an image of `cabernet-franc-pinot-noir-2022` have the cosine 1.0000, so the two wines
  hold the same picture in two files. A candidate for a merge or for the relation
  `similar`.
- `fanagoriya-tochka-saperavi-krasnoe-suhoe-14` (`main` `9a3efb42…`, 3977 x 8347): not in
  the top 10, the best cosine is 0.7737. The image is in the index (row 4080 of the view
  `full`). The cause is a different package cut: the SAM3 answer of the query path
  (`data/cache/sam3/`, method `seg`) cuts the box `[0, 804, 1994, 8347]`, and the stored
  catalogue cut (`image_derivative`, kind `package`) has the box `[1768, 0, 3977, 8108]`.
  The photo seems to hold two bottles, and the two paths took a different one. So a test
  photo of this wine and the catalogue image can see different bottles. In this run no
  other full image of one wine misses its wine. A different cut that still ranks the wine
  first does not show in the self-test.

## 2026-09-27 — Why the view `label` of `/embedding` failed for 88 items

Session drink-atlas-workspace-1c [b72be3]. Plan 22
([docs/plans/22_label-cut.md](docs/plans/22_label-cut.md)).

- Each of the 88 failed items of `gx10-siglip2-so400m-patch16-naflex-p256` (build of
  20:07:53) had the error `no label cut yet`. `p512` and `p1024` had the same 88. Each
  source had a `package` cut and no `label` row, and no absence marker.
- 86 of them were `full_front` (49) and `full_back` (37) photos: 82 `clipboard-<ms>.png`
  pastes of 2026-09-27 09:06 to 20:04, and 4 `.jpg` uploads. The cause:
  `alternatives.store_alternative` made the package cut of a full photo alone. Only
  `seed_label_cuts.py` made the label cut of a full photo, and it last ran on
  2026-09-25. Manual wines and the website import had the same gap: the main image of
  `__aaaaa` had no label cut.
- 2 were `main` photos of rosé bottles with the text printed on the glass:
  `5478f9d5…` (Rose Cuvee Prestige De Gai-Kodzor) and `45738caa…` (Rose. Каберне Фран).
  SAM3 finds no label, and the package prompt finds a bottle, not a packet or box. So
  they get no absence marker, and each build fails them again. The seed of 2026-09-25
  reported the same two. A decision is open: a manual cut, or a not-applicable rule for a
  printed bottle.
- The seed of 20:38 took 0.55 s for each photo (98 photos, 54 s), with the enrichment
  frame run on the same SAM3. The seed of 2026-09-25 took 1.5 s for each photo.
- The entries other than the three naflex ones showed fewer failures only because
  their last build was older: the new photos were `missing` there, not `failed`.
- The old `set_type` wrote an empty `derive.Derivatives("label")` when the new type was
  a label type with a current close-up cut. `write_processed_rows` then read the missing
  attribute `source_sha256`, and the route failed. A change `label_front` to
  `label_back` of a close-up gave this error (test on the base code in the scratchpad).

## 2026-09-27 — The cluster describe prompt: key drift, and the cost of close-ups

Session drink-atlas-workspace-6b [e99257]. Plan 61
([docs/plans/61_label-descriptions.md](docs/plans/61_label-descriptions.md)).

- `label_rules.DESCRIBE_PROMPT` equals `describe_images.detail_prompt("package",
  "bottle")` of plan 29 character for character. Stage 2 sent it with other settings
  (JPEG at 1,536 px, strict `json_schema`, `max_tokens` 4,096 or 8,192).
- The 382 cluster descriptions (`json_object`, no schema): 132 (35 %) have the key `text`
  instead of `texts`, 2 of them also `number` instead of `numbers`; 1 has an extra
  top-level key `where`; 1 has no key `bottle`. The item forms vary: 47 `texts` items are
  strings, 111 `numbers` items are strings or numbers, `marks` items are objects with
  `description` and `place`, `place` alone, or `text` and `where`. `cluster_rerank.py`
  reads `texts` alone, so a drifted description gives it no text.
- The describe request of the cluster run and stage 3 give the same `describe_sha`
  (`5c76331d3c245e37`), so the records of `data/cache/` are shared.
- Live check with the exact cluster request (`qwen3.5-9b-nvfp4`, PNG at 2,048 px): 3 of
  4 answers had `text`. A cache hit of the cluster run took 0.3 s, a main bottle 15 to
  20 s. A `label_back` close-up reached `max_tokens` 1,500; the loop guard gave 2,021
  completion tokens at 3,000, 182 s in all.
- The first 39 rows of the backlog (the newest links first, many close-ups): 11 loop
  guards, 9 renames, 1 schema failure (no key `marks`), a median of 34 s for each new
  call with 8 workers while the enrichment frame run shares the model; about 6 images per
  minute.
- The full backlog (15:17 to 16:49, 2,162 of 2,166 images): 358 cache hits, 39 loop
  guards, 800 renames `text` -> `texts` (37 %), 21 renames `number` -> `numbers`. 2 images
  failed 3 times with a flat answer: repeated top-level `text` and `where` keys, which
  `json.loads` folds into one pair each. The rate rose from about 6 to about 22 images per
  minute when the queue left the new close-ups for the older `main` bottles.

## 2026-09-27 — `my-1` failures: the trigger coverage and the data, not the rule logic

Session drink-atlas-workspace-38 [2e502f]. Report:
[docs/reports/2026-09-27_my-1-failure-addendum.md](docs/reports/2026-09-27_my-1-failure-addendum.md).
It adds to [docs/reports/2026-09-27_my-1-failure-analysis.md](docs/reports/2026-09-27_my-1-failure-analysis.md).

- `my-1` is the R@1 residue of the same pipeline. 27 of its 30 new hits come from images
  that entered the index after the source run. 2 come from new `wine_code` rows.
- A replay of the re-rank on the saved VLM answers reproduces both runs. Three rule
  fixes (no vintage question, `other` gives 0, abstain on a verdict with no separating
  feature) change `my` R@1 by -1 to -4 of 1,644. The rule logic is not the lever.
- 90 of 157 genuine misses have a rank-1 card in no cluster. The confused catalogue pairs
  have a median NaFlex-p256 cosine of 0.910; the clusters need 0.95.
- 90 genuine misses differ in colour, sugar, or grape: a front-label text check can
  separate them. 53 differ only in ABV, vintage, line name, or nothing: a data decision.
- 4 `full_back` catalogue images win rank 1 for 12 misses. Their removal recovers none.

## 2026-09-27 — label-space fusion: the tower is the limit, not the rule

Session drink-atlas-workspace-d7 [604e28]. Report:
[docs/reports/2026-09-27_label-fusion.md](docs/reports/2026-09-27_label-fusion.md).

- A replay of 23 fusion rules on the saved per-view top-10 lists of the label run and the
  reference run of 01:17 and 01:19. No request, no model call.
- The present mean of `Catalogue.rank` costs 25 R@1 after the rerank in the replay (the
  real runs: 29). No rule beats the full tower after the rerank. A rule selected on 4
  folds and scored on the 5th gives 1,380 to 1,382 R@1 against 1,392.
- The label tower alone: 75.6 % R@1 before the rerank, against 82.2 % for the full tower.
  It is correct on 93 photos where the full tower is wrong; 48 of them are outside the
  rerank. The cosines and the margins do not show which tower is correct.
- Catalogue label cuts have a median long side of 417 px. Query label cuts have about
  800 to 950 px. This asymmetry is a hypothesis for the weak tower. It is not tested.
- The +3.4 points of `svoe-vino-matcher` (2026-09-22) came on a weaker base with no
  cluster rerank.

## 2026-09-27 — the choice of the SAM3 package instance

Session drink-atlas-workspace-86 [92610a]. The old rule of `Sam3Client.segment` took the
largest instance of `wine bottle, can, packet, box`. Four rules were replayed on the
cached SAM3 answers (`embedding_run.CachedSam3`, no request to SAM3). The set: the 154
catalogue images with a SAM3 package cut and the 2,155 query photos of run
`2026-09-26T173050Z-lab-barcode-siglip2-512-crop-my`.

| Rule | Query photos changed | Catalogue images changed | Wrong choices seen |
|---|---|---|---|
| A: the bottle always wins | 28 | 15 | 12 catalogue packets and bag-in-box: the bottle printed on the package wins |
| B: the bottle wins unless 90 % of it lies inside a larger package | 21 | 3 | 6 queries: a real bottle in an open gift box or in front of a crate loses (the 7th difference covers the same area) |
| C: the bottle wins when it has 50 % or more of the largest area | 20 | 2 | 8 queries: q-000108 (0.496), q-000236 (0.38), and the bottle-in-box photos |
| D: the bottle wins, except a bottle printed on a packet or a box | 28 | 4 | none seen |

- The owner chose D. `derive.package_instance` implements it. The implementation gave the
  same choice as the replay of D for each photo.
- A printed bottle has 0.005 to 0.21 of the packet area, and 0.015 to 0.06 of the
  bag-in-box area. A real bottle inside a `box` instance has 0.13 (the Ferrum crate) to
  0.36 (an open gift box, where one `box` instance covers the lid and the base). So a
  packet needs no area test. A box needs the test with the limit 0.1. The margin between
  0.06 and 0.13 is small. A new bag-in-box photo with a larger printed bottle can pass the
  limit.
- SAM3 often gives a `box` for a gift box, a tube, a crate, a cork crate, or a cardboard
  background. SAM3 also gives a second `wine bottle` for a bottle-shaped window of a
  wooden box (q-000042, score 0.5). The largest bottle is the real bottle there.
- A catalogue image with a bottle and its tube (`fanagoriya-tochka-saperavi-krasnoe-suhoe-14`,
  `fanagoriya-ice-wine-merlo-rozovoe-sladkoe-10`) now gets the bottle cut, not the tube.

## 2026-09-26 — the re-queue of schema 024 (`presentation_mode`)

Session drink-atlas-workspace-6c [c91c62]. The watcher sent the class prompt again for
2,092 images, with the four old values as fixed facts, to `qwen3.5-9b-nvfp4` on gx10.

- The result: 2,091 `on_package` and 1 `flat_surface`. The one flat label is the
  `label_back` photo `405b65f9…` of `vysokij-bereg-risling-zelenaya-seriya-1`, the photo of
  the owner message of 19:46:00. The catalogue holds almost no flat label.
- The fixed facts held: no row changed its four old values (compared with the backup of
  20:19:30).
- 2 answers left out the new key `presentation_mode` and failed the schema. Both passed on
  the next call.
- The run took 2 h 10 min, not the 10 to 30 min of the estimate. A call took 6 to 9 s, but
  the gateway answered HTTP 429 712 times, because the whole-catalog frame run of
  `drink-atlas-enrichment` used the same model with 8 workers. The watcher backed off 30 s
  after each 429. Two restarts of 8168 by other sessions did not lose a row.
- The watcher lives as long as 8168, so `caffeinate -w <watcher pid>` never ends by
  itself, and a restart of 8168 ends it early. A waiter that reads the pid from
  `/api/image-description-status` each minute moved `caffeinate` to each new watcher and
  stopped it when `pending` was 0.

## 2026-09-26 — the bottle test of the label rule in a close-up

Session drink-atlas-workspace-4f [0fa826], owner message of 2026-09-26T19:38:53+0300. A
read-only pass over the cached SAM3 answers (`DETECT_TEXTS`) of the 2,037 photos of
`data/lab.sqlite3`. Each photo had a cached answer; the pass sent no SAM3 request.

- The photo `d9f847bd…` (`label_back`): the real label had 1,353,980 mask pixels, a box
  IoU of 0.84 with the bottle, and a mask IoU of 0.82. The bottle filled 86 % of the frame.
  The bottle test (`BOTTLE_IOU` 0.80) dropped the label. A QR sticker of 176,368 px won.
- In 12 of the 2,037 photos, the present rule selects a label that is not the largest
  label. 11 are `main` photos: gift tubes (Fanagoriya Ice Wine, Lenty) and cartons or
  packets (Kartuli Supris, Gloria de Luna, Evropak Shiraz). There the largest label is the
  whole package: box IoU 0.92 to 0.99 and mask IoU 0.89 to 0.98 with the bottle. The
  bottle test does its job there. On the cartons, the present cut is a small part of the
  face, for example `QUALITY WINES`; this is a separate question.
- A mask IoU threshold of 0.85 separates the close-up (0.82) from the 11 catalogue
  photos (0.89 and more) on this data. The margin is small, and the data holds one
  close-up only. The owner selected the rule by the photo type instead.
- `detect` is not a safe signal of a close-up for a catalogue photo: one Fanagoriya
  `main` photo (bottle in 8 % of the frame, no neck found) gives `label`.

## 2026-09-26 — wine_slug renames in the website import run of 07:48

Session drink-atlas-workspace-0d [ab062e], owner messages of 2026-09-26T19:16:31+0300 to
19:23:19. A read-only check of `work/website-import/20260926T074810/diff.json`: 73
missing wines and 79 new wines, so 5,767 pairs. `import_website.renames` takes 0.03 s.

- 4 pairs match. 3 match by the same image alone. `ya-jla-risling` -> `yaiyla-riesling`
  matches by the same image and a slug distance of 3.
- The rule "same name and producer" finds 0 pairs, also after the normalization (lower
  case, `ё` -> `е`, no punctuation). The website changed the producer strings, for
  example `One Barrel (Уан Баррел)` -> `One Barrel by Dmitry Maslov (OBDM)`. It changed the
  script of the names too, for example `Яйла Рислинг` -> `YAIYLA RIESLING`.
- A looser check (the same producer and a name token overlap of at least 0.5) found 2
  other pairs: `merlo-litavshhuk` -> `merlo-2` and
  `usadba-perovskih-rkatsiteli-beloe-suhoe-13` -> `rkacziteli-kvevri`. They are not
  proven renames. The owner did not ask for this rule.
- The One Barrel pairs cross. The stored main image of the old Chardonnay row
  (`one-barrel-uan-barrel`) is the website image of the new `pinot-noir-2024`. The
  stored main image of the old Pinot Noir row is the website image of the new
  `chardonnay-2024`. The dialog shows a red wine bottle on the old Chardonnay row. So the
  two lab rows probably hold swapped main images. A person must check this.
- 9 tables reference `wine_catalog (wine_slug)` with no `ON UPDATE CASCADE` (schema 005,
  007, 008, 009, 010, 011, 012, 013, 023). A real slug rename must change each of them.
  The owner chose "display only" on 2026-09-26T19:22:30+0300.

## 2026-09-26 — `data/lab.sqlite3` against `svoe-vino-testset` and `derived/`

Session drink-atlas-workspace-9e [4644ab], owner message of 2026-09-26T17:28:03+0300.
A read-only comparison of a snapshot of `data/lab.sqlite3` (17:29) with each source of
`pipeline/seed_from_testset.py`. The script used the parse and map functions of the seed
tools. So "equal" means "equal to the rows that the seed writes from the files of today".
No source file changed after the start of the seed (07:34).

- `svoe-wino-hackaton/dataset/derived/` holds no database. It holds JSONL files and image
  folders. The only SQLite file of `svoe-vino-testset` is `work/state.db`: the work state
  of the photo hunt of 2026-09-18 (2,105 wines, 233,368 candidates). The seed does not
  read it.
- Equal: the three test sets. `my` 4,043 photos, `official-real-photos` 100,
  `vlmrerank-8b-failed` 180. Each path and each SHA-256 is equal. Each label column, each
  wine note, the label note, the excluded slugs, and the variant groups are equal.
  `test_set.edited_at` is NULL for each set.
- Equal: the 2,103 wines of `wine_catalog` (9 fields) against the Strapi CSV and against
  `catalog.jsonl`. The 26 codes against `code-map.json`. The 367 Atlas bindings (364
  automatic, 3 manual) against the two JSONL files. The 15 patches against
  `patched-official-2026-09-17/`. No additional photo on either side.
- Difference 1: 52 wines have an official photo in `catalog.jsonl` (method
  `live-og-image`) and no `main` row in the lab. `seed_images.py` matches by name alone;
  the `og:image` load is the open later step 1 of plan 08. 7 of the 52 wines have a patch.
  So 45 wines have no picture in the lab and a picture in the test set.
- Difference 2: 5 wines have a `main` row (`name-identical`) in the lab and no photo in
  `catalog.jsonl` (`unresolved`, "the page did not answer"), for example
  `beloe-polusladkoe` and three `zb-vajn-*` wines.
- Difference 3: the lab-only patch of `shato-pino-kaberne-sovinon-merlo-krasnoe-suhoe-135`
  (`manual`, SHA-256 `00bae0ae…`). The test set file has the same name and size
  (273 × 1000), but other bytes (`5de219e9…`).
- Difference 4: the manual pair of `manual-groups.json` (`my` and
  `vlmrerank-8b-failed`) is not in `test_variant`. The owner skipped manual pairs for
  plan 24 on 2026-09-25T17:01:44+0300.
- Difference 5: the lab makes its own cuts. The package cut is byte-equal to
  `derived/official-2026-09-17/cropped/` for 1,905 of 2,047 wines with the same source;
  box IoU >= 0.9 for 2,043. The label cut uses another SAM3 rule (plan 22): the same box
  for 23 wines, median IoU 0.978, IoU < 0.5 for 68.
- Lab-only rows: 2,034 image descriptions and 2,028 image details (VLM, 07:42 to 07:59).
- Not imported by design: `trash/` (360 files of `my`), 12 loose files in `my/photo/`,
  `selection.json`, `runs/`, `catalog-cluster*.json`, and the Drink Atlas match-test files
  of `derived/`.

## 2026-09-26 — the rules of `qwen3.8-max` against the rules of `qwen3.5-9b-nvfp4`

Session drink-atlas-workspace-39 / CLUSTERS [fb59ad]. The same 163 clusters, the same
stage 1 descriptions (the 9B), the same query VLM (the 9B), label `bench49` against
`bench48` (the 9B rules) and `bench45` (no re-rank), 2,209 photos of `my`.

- The build: 163 calls to `qwen3.8-max` with thinking, 4 at the same time (the log gives
  3.9 calls in flight on average), 61 min, 0 errors and no refusal of QwenCloud. One rule:
  median 70 s, maximum 259 s. The «Фантом» rule: 3,595 reasoning tokens, 338 answer
  tokens, and the right colours (pink, dark red, purple); the 9B had «dark blue» for B.
- The shape of the rules: fewer questions (170 valid against 229), more rules of one
  question (97 against 67), fewer `vintage` questions struck by the check (3 against 27),
  more `verdict` rules (32 against 24), and 13 rules that separate the cards by the alcohol
  value alone (1 for the 9B).
- R@1 of `rerank-siglip2-512-crop`: 83.82 % against 83.26 % (the 9B rules), +0.55 points,
  25 wins and 16 losses, exact McNemar p 0.21: the difference is not significant.
  Negatives rejected 84.42 % against 85.10 %, 3 wins and 7 losses, p 0.34. Against no
  re-rank: +2.52 points, 52 wins and 11 losses, p 1.7e-07. The barcode twin: 85.17 %.
- The rules of `qwen3.8-max` lose less in mode `sheet` (7 losses against 13) and more in
  mode `verdict` (4 positive and 2 negative losses). 22 of their 32 `verdict` rules name
  every card as indistinguishable, and the query model still names a card. A post hoc
  replay with the base order for these 48 photos gives no net gain (R@1 -0.13 points,
  negatives +0.34 points).
- The cache: each answer of QwenCloud is a record of `data/cache/qwen3.8-max/`. The key is
  the SHA-256 of the endpoint, the model, the request options (the thinking switch
  included), the prompt, and the SHA-256 of each image, so a record of `qwen3.5-9b-nvfp4`
  never answers a call of `qwen3.8-max`. No record holds the API key.

## 2026-09-26 — a VLM request that times out while the service lives (plan 49)

Session drink-atlas-workspace-0d [ab062e]. Read `docs/plans/49_vlm-timeout-probe.md`.

- The detail request of one image (`a902e43a5f77…`, `package` prompt, `bottle`, the cut
  at 1536 px) timed out 45 times from 2026-09-25T23:02Z to 2026-09-26T07:38Z. The vLLM
  log of `qwen3.5-9b-nvfp4` on gx10 showed 1 running request at about 22 tokens/s for the
  full 300 s: about 6,600 tokens. A valid answer of this image has about 380 tokens.
- The same request in a batch with other requests ended with `finish_reason` `stop` in
  17 s (a streamed copy) and in 21.1 s (the watcher at 07:39:21Z). So the long output of
  greedy decoding (`temperature` 0) depends on the batch. The text of the long output was
  not seen; a repetition loop is an inference.
- With `max_tokens` 8192 and about 22 tokens/s for one request, the service needs about
  370 s to stop at `max_tokens`. The client timeout of 300 s ends the request first. So a
  timeout, not `finish_reason` `length`, is the visible symptom of a long output.
- llama-swap (port 18081) answers `GET /v1/models` from its own configuration. It does not
  prove that vLLM behind it serves. A chat request of 1 token with no image answered in
  0.12 s on 2026-09-26; it proves that the model serves.
- A read timeout of `urllib` (the server took the request and sent no header in time)
  comes as a bare `TimeoutError` ("timed out"). A connect timeout comes as a `URLError`
  ("<urlopen error timed out>").

## 2026-09-26 — plan 48: the cluster re-rank adds 2.0 points of R@1 on `my`

Session drink-atlas-workspace-39 / CLUSTERS [fb59ad]. Label `bench48`, 2,209 photos, the
rules of the `combined` clusters of `gx10-siglip2-so400m-patch16-naflex-p256` (plan 45,
`qwen3.5-9b-nvfp4`), the query VLM `qwen3.5-9b-nvfp4` with thinking off.

- `rerank-siglip2-512-crop` against `siglip2-512-crop` (bench45): R@1 81.29 % → 83.26 %,
  MRR 0.878 → 0.889, R@5 unchanged (the step orders only the top 5); 48 wins, 16 losses,
  exact McNemar p 7.7e-05. Negatives rejected 82.88 % → 85.10 %, 16 wins, 3 losses,
  p 0.0044. The barcode twin gives the same differences: 82.58 % → 84.55 %.
- The rules of one embedding serve a pipeline of another embedding: the clusters of the
  NaFlex p256 embedding and the answers of siglip2-512 work together.
- The trigger acted on 574 photos, the number of the analysis before the plan. Mode
  `sheet` 537 photos (111 changed), mode `verdict` 37 (14 changed). No VLM error.
- The losses name the weak points of the rules of the 9B model and of the check of plan
  45: a question about the background colour; a six-digit number on the edge of the label
  (it changes from bottle to bottle, and `SERIAL` does not catch «number»); features
  outside the SAM3 label cut (a neck ribbon, a text at the bottom edge); a verdict by the
  vintage year alone; an expected text with a reading error of stage 2. The misreads of
  the query VLM: «Demi-Sec» for «Demi-Sucré», a kosher mark `not visible`.
- Time: a VLM call took a median of 2.7 s with 4 photos at a time; a photo with the step
  a median of 5.1 s. A second run of the same photos reads every answer from the model
  cache.

## 2026-09-26 — the full benchmark on `my`: siglip2-512 with the barcode step is best

Session drink-atlas-workspace-39 / CLUSTERS [fb59ad]. 45 runs, label `bench45`, 2,209
photos (1,625 positive, 584 negative). The tables are in
`docs/reports/2026-09-26_full-benchmark-my.md`.

- R@1: `barcode-siglip2-512-crop` 82.6 %, `barcode-siglip2-512-as-is` 82.0 %,
  `siglip2-512-crop` 81.3 %, `barcode-siglip2-p512-crop` 81.1 %. The official recognizer
  67.6 %. The DINOv3 entries 29.8 to 44.4 %.
- The barcode step: +1.2 to +1.3 points for each of the 22 pipelines, 19 to 21 photos won,
  0 lost. The same photos carry a code in each pipeline, so the gain does not depend on
  the embedding. The median time goes from about 170 ms to about 360 ms.
- Against plan 40 (label `bench40`, 2026-09-25, the same photo counts): each pipeline is
  1.3 to 2.4 points higher. The cause was not examined.
- A cluster re-rank can act on the best plain run (`siglip2-512-crop`) as follows, with the
  `combined` clusters and the rules of `gx10-siglip2-so400m-patch16-naflex-p256`: the
  rank-1 card and another card of its cluster in the top 5 on 574 photos (179 negatives);
  89 of the 304 misses have the true card in the cluster of the rank-1 card inside the top
  5; 257 hits at rank 1 are exposed. «All top 5 in one cluster» acts on 37 photos and can
  fix 2 misses, because 132 of the 163 clusters have 2 wines. 161 misses have a rank-1 card
  in no cluster.
- A shell pitfall: `python3` of the Mac has no zxing-cpp. A barcode pipeline MUST run with
  `embedding_python` (`~/.venvs/svoe-vino-lab/bin/python`); else it stops at once with «the
  key `barcode` needs zxing-cpp 2.3.0 in this Python».

## 2026-09-26 — health checks: the llama-swap lists load nothing, `/upstream/` loads, and a repeated prompt stops llama.cpp `qwen3.5-9b`

Session drink-atlas-workspace-cc [d62b09], plan 46 (the Health page).

- llama-swap on gx10 (`http://192.168.86.14:18081`): `GET /v1/models` lists 49 models, each
  with `status.value` `loaded` or `unloaded`. `GET /running` lists the models that run,
  with `state` (`ready`) and `ttl` (0: no automatic unload). Both answer in about 3 ms and
  load no model. `GET /logs` gives the proxy log; `GET /logs/stream/upstream` gives the
  output of the model processes.
- A request to `/upstream/<model>/<path>` starts the model. A probe of
  `GET /upstream/sam3/health` at about 10:37 loaded SAM3: 10 s with no answer, and HTTP
  409 on a second path during the load. No other model stopped.
- SAM3 answers `GET /upstream/sam3/health` in about 8 ms when it runs:
  `{"status": "ok", "model": "facebook/sam3", "device": "cuda", "dtype": "fp16",
  "workers": 1, "batch_size": 4}`.
- QwenCloud (`token-plan…/compatible-mode/v1`) and DashScope
  (`dashscope-intl…/compatible-mode/v1`) answer `GET /models` with the key in about 1 s.
  The lists hold `qwen3.8-max`, `qwen3.8-flash`, and `qwen3.7-flash`. A chat request of
  1 token takes 1.1 to 1.9 s.
- The vino-svoe.ru API has no `/v1/info` (HTTP 404, `Cannot GET /v1/info`; that route is a
  route of svoe-vino-matcher). `GET /v1/wines?page=1&perPage=1` answers in 0.4 to 1.6 s
  with `totalItems` 2109.
- The crash. At 11:24:33 the browser test sent the 1-token prompt of 11:10 again to
  `qwen3.5-9b` (llama.cpp 45b455e of 2026-05-18, `llama-server`, pinned, `ttl` 0). The
  upstream log: `selected slot by LCP similarity, sim_best = 1.000`, then `need to
  evaluate at least 1 token for each active slot (n_past = 16, task.n_tokens() = 16)`,
  `n_past was set to 15`, and a backtrace through `ggml_abort` in
  `server_context_impl::update_slots`. llama-swap logged `http: proxy error: EOF`,
  answered HTTP 502 with an empty body, and then logged `upstream exited unexpectedly`.
  The model did not run after that.
- The cause, in `tools/server/server-context.cpp` of that commit: on a full prompt match
  the server keeps one token to evaluate (`[TAG_PROMPT_LOGITS]`) and removes the
  positions from 15 to the end. The recurrent state of the hybrid model cannot drop one
  position, so `common_context_seq_rm` calls `GGML_ABORT("failed to remove sequence …")`.
  A prompt that differs takes the checkpoint path (`restored context checkpoint` or
  `forcing full prompt re-processing`), which is the path of each chat. The request of
  11:10 worked, because the slot then held another prompt.
- The fix of the check: each chat request holds a new random token. `cache_prompt: false`
  (a field of llama.cpp) also skips the reuse. It was not used, because another service
  can refuse an unknown field.
- No OOM: earlyoom reported 62 % of the memory available at 11:25, and the kernel log had
  no kill.
- The image description watcher repeats a 300 s timeout of one detail image,
  `a902e43a5f77`, about every 5 to 9 minutes since 05:40Z at least. At the same time
  `qwen3.5-9b-nvfp4` stays loaded and answers a 1-token request in about 65 ms.

## 2026-09-26 — plan 45 run: 163 label rules of `qwen3.5-9b-nvfp4`, and the «Фантом» colours

Session drink-atlas-workspace-39 / CLUSTERS [fb59ad]. `pipeline/build_label_rules.py
--name gx10-siglip2-so400m-patch16-naflex-p256` from 10:35 to 11:16 (2,511 s), after the
cluster build of 10:33:43 (163 `combined` clusters, 382 wines). Thinking off in both
stages. The service accepts 20 images in one prompt since the change of the owner.

- Stage 1: 382 descriptions, 0 errors. 5 answers came from the model cache (cards that
  share a main image). 5 answers reached `max_tokens` 1,500 and were valid at the second
  attempt with `repetition_penalty` 1.15 and 3,000 tokens. One call: median 15.6 s, p90
  24.4 s, maximum 38.0 s, with 4 calls at the same time and the watcher of plan 29 on the
  same model.
- Stage 2: 163 rules, 0 errors: 139 `sheet`, 24 `verdict`, 0 `none`. One call: median
  8.9 s, p90 12.7 s, maximum 27.8 s, with 2 calls at the same time.
- The questions: 223 valid and 17 not valid of kind `feature`; 5 valid and 27 not valid
  of kind `vintage` (a year that the name or the slug does not state); 1 valid and 9 not
  valid of kind `alcohol`. Valid questions for each rule: 0 in 24, 1 in 67, 2 in 55, 3 in
  16, 4 in 1. The prompt asks for 1 to 3 questions; the code does not cut a fourth one.
- The mode `verdict` holds weak rules. Examples: `45beb9f24dd6` «All three cards have
  identical labels; no visual feature on the label distinguishes them.»; `5d865603962e`
  «If the label shows '2024', it is Card B; otherwise, it is Card A.» (a year that only
  the label shows); `a1519f95d8a3` names three grape texts with the year 2022, and its
  questions were of kind `vintage`, so the check struck them. The check of
  `svoe-vino-testset` gives `verdict` to each rule text that names no feature outside the
  label. Plan 06 of `svoe-vino-testset` (Q2) records the same weakness.
- The «Фантом» cluster `a29e59138ed4`, after the new note of the owner (11:04:53: «… and its
  background color. Alcohol percentage is not relevant.»): the rebuild after the note
  (11:16:39, 12.5 s) gave 2 valid questions, the ratio (30/70, 50/50, 70/30) and «What is
  the color of the small box in the bottom left corner of the label?» with pink, dark
  blue, and purple. No alcohol question. The rule text names the ratios only.
- The colour of card B is wrong. In the label cut of `…-fantom-5050-…` the box is dark
  burgundy (the most saturated pixels have a mean of RGB 107, 103, 123 on white; visible
  as maroon), not dark blue. The boxes of A (pink, mean 189, 97, 135) and C (purple, mean
  142, 103, 164) are right. `qwen3.8-max` of `svoe-vino-testset` wrote «dark red» for B.
  A query photo of B can then get the answer `other` or `purple` for this question.

## 2026-09-26 — plan 45 probe: `qwen3.5-9b-nvfp4` takes 1 image, and thinking gives no rule

Session drink-atlas-workspace-39 / CLUSTERS [fb59ad], plan 45 (the label rules of the
embedding clusters), 09:30 to 09:51. Direct requests from the Mac to llama-swap 18081,
one at a time, for the «Фантом» cluster `a29e59138ed4` (3 cards) of the view `combined`
of `gx10-siglip2-so400m-patch16-naflex-p256`. The prompts are those of
`svoe-vino-testset/scripts/cluster_rules.py`. Scratch code: `probe_rules.py`,
`probe_montage.py`, `probe_montage_nothink.py` in the scratchpad of the session. A small
sample: one cluster.

- The service is vLLM (`docker compose` of `vllm-qwen35-9b-nvfp4` behind llama-swap).
  `GET /upstream/qwen3.5-9b-nvfp4/v1/models` gives `Qwen3.5-9B-NVFP4` with
  `max_model_len` 32,768.
- The service accepts one image in one prompt. 2 or 3 images give HTTP 400:
  `At most 1 image(s) may be provided in one prompt. (parameter=image)`. Stage 2 of
  `svoe-vino-testset` sends one image for each card, so it cannot run on this service.
- The key `repetition_penalty` of the request is accepted (HTTP 200).
- Stage 1, the package cut of each card enlarged to 2,048 pixels (541 × 2048), thinking
  off, JSON mode: 3 of 3 HTTP 200, 14.1 to 18.3 s, 339 to 445 completion tokens, valid
  JSON, vintage 2018 on each. The ratio mark of the label: card A (30/70) and card C
  (70/30) read no ratio; card B (50/50) read `9/9`. So the enlargement did not make the
  small mark readable. The 2026-09-25 repeat of `svoe-vino-testset` read card B as `8/8`.
- Stage 2 with one image, a montage of the 3 label cuts (each scaled to a long side of 768
  pixels under a caption strip «Card A» to «Card C»; 1298 × 832 pixels; 3,019 prompt
  tokens):
  - thinking on, JSON mode: 502.8 s, `finish_reason: length` at `max_tokens` 12,000,
    36,751 characters of reasoning, empty content;
  - thinking on, no JSON mode: 508.3 s, the same, 34,736 characters of reasoning.
  - The reasoning starts with an ordered analysis of each card and does not reach an
    answer. The speed is about 23.9 tokens/s.
  - thinking off, JSON mode: 12.5 s, 262 completion tokens, valid JSON. Question 1 asks
    for the blend ratio, with 30/70, 50/50, and 70/30: a valid `feature` question.
    Question 2 asks for the alcohol value, 14.4 %, 14.5 %, and 14.7 %: the check makes it
    not valid, because question 1 is valid. The rule text names the three ratios. The
    answer 50/50 of card B comes from the catalogue name and the note, not from the
    printed mark.
- Side observation: from about 09:00 to at least 09:27 the watcher of plan 29 repeated a
  detail call of `a902e43a5f77` that timed out after 300 s each time (not counted).

## 2026-09-26 — the barcode step: zxing-cpp 2.3.0 on Python 3.14, and a check on real photos

Session drink-atlas-workspace-1c [800d92], plan 42.

- zxing-cpp 2.3.0 has no wheel for Python 3.14 on macOS arm64. PyPI has wheels of 3.0.0
  and 3.1.x for this Python. The matcher keeps 2.3.0, because 3.1.1 can stall on an
  excise mark beside an EAN. `pip install --no-binary zxing-cpp zxing-cpp==2.3.0`
  builds it from the source in `~/.venvs/svoe-vino-lab` with the Homebrew cmake and ninja
  and the Apple C++ compiler.
- A check of the decoder (`barcode.Decoder` with the options of the twins, and a lookup
  made from `svoe-vino-matcher/dataset/code-map.json` with `codes.clean`): 169 photos
  of the 22 wines of the code map in `svoe-vino-testset/dataset/*/photo/`. 40 photos
  gave a hit of the right wine, 0 gave a wrong wine, and 129 gave no hit. The time for
  each photo was 230 ms (median) and 619 ms (maximum), with the tile scan on each miss.
  36 hits were EAN-13, 2 were Code 128 with a GTIN-13 (`4630171630094`), and 2 were a QR
  URL. These photos are the photos that the reviewer used to enter the codes. So the
  check shows that the decoder and the lookup work. It does not measure the rate of the
  codes in a test set.

## 2026-09-26 — the embedding entries with the basic pipelines: `siglip2-512` is best

Session drink-atlas-workspace-e2 [9e7fe4], plan 40. 22 pipelines (as is and crop, for each
of the 11 entries of `embeddings`), 44 runs on `my` and `official-real-photos`. The full
report is [docs/reports/2026-09-26_embedding-benchmark.md](docs/reports/2026-09-26_embedding-benchmark.md).

- R@1 on `my` (1,625 positive photos): `siglip2-512-crop` 79.8 %, `siglip2-512-as-is`
  79.1 %, `siglip2-p512-crop` 78.6 %, `siglip2-p14-384-crop` 77.5 %; `siglip2-p256-crop`
  73.9 %, `siglip2-p256-as-is` 64.5 %; DINOv3 41 % at best.
- More image patches give a better R@1 in the SigLIP2 family (1,024 > 729 > 576 > 256; the
  counts come from the model names). At about the same patch count, NaFlex beats a square
  input.
- The crop of the package helps each entry; the gain falls from +9.3 points
  (`siglip2-p256`) to +0.7 points (`siglip2-512`) when the model sees more detail.
- The local copy of `siglip2-p256` and the gateway give nearly the same metrics, but 65
  positive photos differ at rank 1. The cause is not known.
- On the 44 photos of `official-real-photos` whose wine has a catalogue image,
  `siglip2-512-crop` gets 93.2 % at rank 1 and vino-svoe.ru 59.1 % (90.9 % at rank 5).
- Data: 15 of 59 positive photos of `official-real-photos` and 34 of 1,625 of `my` show
  wines with no catalogue image. Two catalogue cards (`fanagoriya-100-ottenkov-…`,
  `avtohtonnoe-vino-kryma-beloe-suhoe`) hold photos of other wines.
- A run of 2,209 photos takes 72 to 138 s through the gateway with 4 photos at a time,
  and 333 to 446 s for the local entry on this Mac (MPS), with cached SAM3 answers.

## 2026-09-26 — a cached SAM3 answer hides about 1.2 s per photo of `siglip2-p256-crop`

Session drink-atlas-workspace-d3 [4920ce], plan 39 (the checkbox `Use caches`). Two jobs
of `siglip2-p256-crop` ran on the first 3 queries of the set `my`, one after the other,
at 01:51, through llama-swap 18081 on gx10.

| | `Use caches` off | `Use caches` on |
|---|---|---|
| Run | `2026-09-25T225101Z-lab-siglip2-p256-crop-my` | `2026-09-25T225128Z-lab-siglip2-p256-crop-my` |
| SAM3 requests | 3 (3 records written again) | 0 (3 cache hits) |
| Latency per photo | 1,276, 1,300, 1,329 ms | 97, 116, 140 ms |

- The latency of an embedding run includes the SAM3 call. With a cache hit, the latency
  is about the time of the embedding request alone. The run `siglip2-p256-as-is` of `my`
  (no SAM3) has a median of 137 ms.
- The full run `2026-09-25T220729Z-lab-siglip2-p256-crop-my` (before plan 39) had 406 of
  2,209 queries (18 %) under 400 ms. These queries very likely read SAM3 from the cache.
  This is an inference from the latency; the run files do not record a cache hit. Its
  median of 1,302 ms is near the real time; its lower decile of 159 ms is not.
- For a comparison of latency, a run needs `Use caches` off. The key `use_cache` of
  `run.json` and the tag `no cache` of `/runs` show such a run.

## 2026-09-26 — 8 detail requests at the same time: 7.8 times the rate, the same call time

Session drink-atlas-workspace-d3 [4920ce], plan 35. The watcher `describe_images.py`
sends up to `image_description.workers` (8) detail requests at the same time since the
restart of 8168 at 2026-09-26T00:36:23+0300. The model is `qwen3.5-9b-nvfp4` on gx10,
through llama-swap 18081. Source of the numbers: the `detail ok` lines of
`work/describe_images.log` (no cache hit in either period) and the records of
`data/cache/qwen3.5-9b-nvfp4/` with `response_format` `json_schema`.

| | One request at a time | 8 requests at the same time |
|---|---|---|
| Period (local time) | 2026-09-25 23:41:09 to 2026-09-26 00:09:39, no timeout | 00:36:39 to 00:42:32 |
| Details | 98 | 157, and 1 timeout |
| Call time: mean, median, p90, max | 17.6, 15.7, 26.5, 36.1 s | 16.0, 15.2, 23.7, 32.5 s |
| Wall time per image | 17.6 s | 2.26 s |
| Details per minute | 3.4 | 26.5 |
| Tokens/s per call (cache records): median, p10, minimum | 21.7, 16.3, 14.8 (111 calls, 23:28 to 00:36) | 22.1, 21.2, 20.4 (147 calls) |

Findings:

- The rate rose 7.8 times. The time of one call did not rise: one stream keeps about
  22 tokens/s with 8 streams at the same time. A likely reason: the decode of a 9B model
  is bound by the memory bandwidth, so vLLM runs 8 streams in one batch for almost the
  cost of one. This reason is not measured.
- The risk of plan 35 did not occur: no good answer came near the timeout of 300 s. The
  longest call took 32.5 s. 8,192 tokens take about 371 s at the median rate and about
  402 s at the slowest call (20.4 tokens/s).
- The limit of `workers` on gx10 is not known. 8 is not proved to be the best value. A
  higher value is not tested. The gateway also serves SAM3, SigLIP 2, and other models.
- One timeout came under 8 workers too: `ac892b17a4bf` at 00:42:29. The watcher stopped
  the new calls for 30 s; the 7 calls that ran finished between 00:42:32 and 00:42:55; the
  watcher went on at 00:42:59. The next call of the same image gave a valid answer in
  16.3 s (00:43:16).
- Three timeouts of 2026-09-25/26 were stuck requests, not loops of the model: the next
  call of the same image, with the same payload, gave a valid answer in 13 to 22 s
  (`f8cf4e3ef618`: 2 timeouts under one request at a time, then 21.3 s under 8 workers;
  `24e28aea6a4d`: 2 timeouts, then 13.3 s; `ac892b17a4bf`: 1 timeout, then 16.3 s). The
  cause of a stuck request is not known. The entry of drink-atlas-workspace-15 below
  holds the conclusion for the timeout rule: a counted timeout would burn the attempts of
  good images.
- At this rate, the 1,464 details that were pending at 00:42 take about 1 hour, not
  about 7 hours.

## 2026-09-26 — plan 33 live check: the embedding runner on `official-real-photos`

Session drink-atlas-workspace-ab [539687]. The command was
`python3 pipeline/embedding_run.py --name gx10-siglip2-so400m-patch16-naflex-p256 --set
official-real-photos`: one photo at a time, from this Mac, through llama-swap 18081. The
index of 2026-09-25 18:14 gave 3,926 current items. 111 stale `label` items (after the
label cuts of 20:53), 3 missing items, and 4 failed items stayed out. During the run the
VLM watcher of plan 29 held the GPU of gx10 at 96 %. The run is
`runs/2026-09-25T205359Z-lab-gx10-siglip2-so400m-patch16-naflex-p256-official-real-photos/`.

Findings:

- 80 queries (59 positive, 21 negative), 0 errors, 437 s. The latency of a photo had a
  median of 4.0 s, a p90 of 6.1 s, and a maximum of 39.3 s. A photo costs two SAM3 calls,
  the steps, and one embedding request. The SAM3 statistics showed a mean latency of
  2.4 s at 73 % load. The first request of the smoke run took 51 s, because the gateway
  loaded `siglip2-so400m-patch16-naflex`, which was not loaded at 23:52.
- Each of the 80 photos got a package cut and a label cut. The contact sheets of 8 missed
  photos showed correct cuts: the bottle on white and the label on white.
- All positive photos: recall@1 0.525 (31 of 59), recall@5 0.712 (42), recall@10 0.729
  (43). The official recognizer on the same 80 photos (run of 2026-09-25 22:32) had 34,
  55, and 57 of 59.
- 15 of the 16 positive photos outside the top 10 show 10 wines with no row in
  `wine_image`: `balaklava-muskat`, `bukovinka`, `czitronnyj-magaracha`, `oleg`,
  `pobeda`, `pozdnij-sbor-krasnoe`, `roze-2`, `rozovoe-zoloto`, `rubin-golodrigi`, and
  `zhemchuzhnaya-9-aligote-czitron`. The index holds no vector of these wines, so no
  embedding configuration can find them. The official recognizer had all 15 photos in
  its top 5, 8 of them at rank 1.
- The 44 positive photos whose wine has a catalogue image: this run 31, 42, and 43 at
  rank 1, 5, and 10; the official recognizer 26, 40, and 42. The sample is small: the
  difference at rank 1 is 5 photos.
- The one miss of a wine with an image is `denisov_pazori_risling`. Its top 3 were three
  wines «Императорское» of Абрау-Дюрсо, at a score of 0.70 to 0.71.
- Negative photos: 4 of 21 false matches at rank 1, the same count as the official
  recognizer.
- A direct call of `run_routes.inputs_view` made the two model inputs of a query again in
  1.1 to 1.2 s, from the SAM3 cache, with no request. The data URL of an input with a long
  side of 1024 px is 0.8 to 1.5 MB.

Options, not chosen yet:

- Give the 10 wines a main image in the catalogue, then build the embedding entries
  again. The runs of all configurations can then find them.
- Compare the embedding configurations on the 44 photos whose wine has an image.

## 2026-09-25 — a detail call that times out blocks the detail queue

Session drink-atlas-workspace-15 [40dc83]. The trigger: the retry of the one failed
detail (`e049e469…`, `usadba-mezyb-shishka-merlo-vione-rozovoe-suhoe-125`) after the
change of `max_tokens` from 4096 to 8192. Its input is a `package` cut of 1851 × 6279
px. At 4096 the model repeated the label texts until `max_tokens` cut the answer, 3
times, about 188 s each.

Findings:

- The speed of the detail calls on gx10 (`qwen3.5-9b-nvfp4`) is 21.8 tokens/s, with the
  prompt time included (297 records of `data/cache/`, p10 21.6, p90 21.9). A normal
  answer has a median of 328 and a maximum of 1,678 completion tokens.
- `TIMEOUT_SECONDS` of `describe_images.py` is 300 s. At 21.8 tokens/s a call ends at
  about 6,500 tokens. So with `max_tokens` 8192 a looping answer ends in a timeout, not
  in `finish_reason: length`.
- A timeout is a failure of the service (`counted=False`): `vlm_attempts` stays, the
  watcher waits (30 s, then doubling to 600 s), and `pending` gives the same image
  again, because its link is the newest. The image blocks every other detail. The
  retry at 23:29 timed out at 23:34:17 and 23:39:47. Setting `vlm_attempts` back to 3
  freed the queue at 23:41:09.
- A timeout is not always a loop of the model. `24e28aea6a4d` (`rubin-premium`, a
  `package` cut of 116 × 484 px) timed out at 2026-09-26T00:14:39 and 00:20:09 under the
  serial watcher. Its `vlm_attempts` was set to 3 at 00:20:23 to free the queue (on at
  00:21:25). After the restart with 8 workers (00:36:23) and a reset to 0 at 00:41:25,
  the same request gave a valid answer in 13.3 s (00:41:39, 4 texts). d3 [4920ce] saw the
  same for `f8cf4e3ef618`: two timeouts (00:28:51, 00:34:21), then a valid answer in 21.3
  s. The cause is not known: a request stuck in the gateway or the server, or an output
  that depends on the batch. `e049e469…` differs: it was cut off at 4096 three times, a
  real loop. Before, 98 serial details from 23:41 to 00:14 had a median call time of
  15.7 s and a maximum of 36.1 s (measured by d3).
- So a timeout that counts would burn the attempts of good images. A timeout above the
  time to write `max_tokens` tokens separates the two cases: a loop ends as a counted
  cut-off (`finish_reason: length`), and a timeout then means a stuck request, which the
  retry that is not counted handles well.

- The speed with 8 workers (measured by d3 [4920ce], `usage.completion_tokens` / `ms` of
  the detail records): serial, 111 calls, median 21.7 tokens/s, p10 16.3, min 14.8;
  8 workers, 147 calls in about 5 min, median 22.1, p10 21.2, min 20.4. One stream does
  not become slower with 8 at once. 8192 tokens take about 371 s at the median, 402 s at
  20.4, and 553 s at 14.8 tokens/s. A busier gateway (other models on llama-swap) can be
  slower.

Options, not chosen yet:

- A timeout that follows `max_tokens`, for example `max_tokens / 15 + 60` s (606 s for
  8192; it covers the slowest measured call, 14.8 tokens/s). A loop then ends as a
  counted cut-off after about 6 to 9 min, and a stuck request holds one worker for about
  10 min before its retry that is not counted.
- A smaller `max_tokens` of the `vlm` entry, with the timeout of 300 s. The longest
  normal detail answer is 1,678 tokens (297 records), 791 and 693 in the later samples.
  At 3072 a loop ends as a counted cut-off after about 150 s (20.4 tokens/s) to 210 s
  (14.8), below 300 s. Stuck requests come under 8 workers too (d3 [4920ce]: 1 in 158
  calls, `ac892b17a4bf` at 2026-09-26T00:42:29, a valid answer at the next call). At 26.5
  details per minute that is one every 6 min: a timeout of 300 s then holds about 0.8
  of 8 workers on average, 606 s about 1.7.
- Count a timeout as a failure of the image. Risk: an overloaded service or a stuck
  request burns attempts of good images (seen two times on 2026-09-26).
- A loop guard in the detail request, as `LOOP_GUARD` of `scripts/cluster_rules.py`
  (`repeat_penalty` 1.15 on llama.cpp). It changes the answers and the cache keys.

## 2026-09-25 — the label cut of a photo with more than one label

Session drink-atlas-workspace-cb [48de03]. The trigger: a label close-up (Agora
Chardonnay) with an art label above a text label. The rule of `build_labels.py` kept the
largest label (the art label) as a segment. The text label was lost, and the dark strip
`AGORA` inside the art label was a hole, because SAM3 gave it as its own instance.

The measurement used 251 SAM3 answers of `data/cache/sam3/` (250 catalogue images), with
no new request. The share of photos that would get the box of the labels:

| Rule for a second label | Photos |
|---|---|
| Any second label | 132 |
| Area >= 15 % of the main label | 73 |
| Area >= 25 % | 31 |
| Area >= 25 % and width >= 60 %, centre on the bottle, < 80 % inside the main label | 13 |

- A plain count sends half of the catalogue to a box. The second labels are mostly neck
  labels, capsules, and shoulder foils. The box then runs up to the neck, and the cut is
  almost the whole bottle.
- The area alone keeps many neck labels. The width test removes most of them: a neck
  label is narrow.
- The chosen rule (the last row) gives the box for two labels one above the other, and
  for sparkling wines with a large shoulder label (Abrau-Durso). The run on all 2,021 full
  originals gave 111 boxes (5.5 %).
- Known weak cases of the box: text printed on the glass that SAM3 calls a label
  (`cock-test-belle-...`), and a narrow body label with a wide neck label
  (`zb-vajn-spumante-...`): the box is then almost the whole bottle. A tetra pak with no
  real label (`soyuz-vino-lak-dazyur-...`) got two small icons as labels; the old segment
  cut was one of these icons.
## 2026-09-25 — embedding-dependent cluster spaces

Status: measured with the current
`gx10-siglip2-so400m-patch16-naflex-p256` index at cosine `0.95`. The builder read
4,039 current items and four failed items. It expanded the items to 4,097 wine-image
assignments: 2,048 rows in `full` and 2,045 rows in `label`.

| Space | Links | Clusters | Wines | Largest |
|---|---:|---:|---:|---:|
| `full` | 214 | 147 | 334 | 6 |
| `label` | 154 | 108 | 244 | 8 |
| `combined` union | 274 | 168 | 397 | 8 |

- Only 94 wine pairs pass in both spaces. Thus `full` and `label` contain different
  evidence. A single mixed vector space would hide this difference.
- The matcher and the old cluster builder both let the best image vector of one wine
  win. The new artifact applies the same rule to every indexed main or additional
  image. It records the winning image pair.
- The database held three additional images during the first direct measurement. They
  created no new edge at `0.95`. This sample is too small to justify main-only clusters.
  An additional image can become the best retrieval vector later, so it stays in the
  applicable space.
- `main_patched` replaces `main`. The two source images do not compete as if they were
  two views of the current product.
- The old test-set cluster builder also added name and benchmark-confusion edges. These
  signals do not depend on one embedding. The new core artifact excludes them. A Runs
  view can add benchmark confusions as a visible overlay later.
- A VLM difference rule must have the same observation space as its query image. The
  current matcher sends a label crop. Therefore it can use a `label` rule only. A later
  package reranker needs a separate `full` rule.
- Difference discovery belongs in an offline build. The VLM sees the typed cluster
  images, detailed descriptions, catalogue facts, and the reviewer note. The result is
  a validated set of closed questions with expected answers and source-image evidence.
  Query time sends one image and these questions. Each question allows its known
  answers, `other`, and `not visible`. This design avoids an open-ended discovery call
  for each query.

## 2026-09-25 — plan 29 live check: the key drift of the package prompt, and `json_schema`

Status: measured on 2026-09-25 from 20:45 to 20:52 MSK by session drink-atlas-workspace-a7
[bbd3b6], with the plan 29 code on a scratch copy of `data/lab.sqlite3` (schema 020 there
alone). `qwen3.5-9b-nvfp4`, thinking off, `max_tokens` 4096, long side 1,536, the cut of
`image_derivative`.

| Image | Prompt | `response_format` | Result | Time |
|---|---|---|---|---|
| `avtohtonnoe-vino-kryma-beloe-suhoe` (`07d588a4…`, full front) | package, `bottle` | `json_object` | fails: key `text`, a list of strings | 15.1 s |
| `soyuz-vino-izola-del-sole-roze-v-banke-…` (`e3c38e97…`) | package, `can` | `json_object` | valid, 6 texts | 21.0 s |
| `soyuz-vino-el-krusero-tinto-…` (`0169a8f4…`) | package, `tetra_pak` | `json_object` | fails: key `text`, `numbers` as strings | 19.7 s |
| `2239638a9aeb…` (back label close-up) | label, `bottle` | `json_object` | valid, 16 texts | 99.4 s |
| `07d588a4…` | package, `bottle` | `json_schema`, strict | valid, 6 texts with `where` | 15.1 s |
| `0169a8f4…` | package, `tetra_pak` | `json_schema`, strict | valid, 11 texts with `where` | 31.0 s |

- With the probe of 19:20, the package prompt gave the key `text` in 3 of 4 answers. The
  label prompt gave valid keys in 2 of 2 answers.
- `temperature: 0` repeats the same answer, so a retry of a key drift fails again. With
  `json_object` alone, most package images would stop after 3 failures.
- The gateway 18081 honours `response_format: {"type": "json_schema", "json_schema":
  {"name": ..., "strict": true, "schema": ...}}` for this model: the same payload gave the
  keys of the schema. The schema of `describe_images.detail_schema` (type lists such as
  `["string", "object"]`) was accepted.
- The OCR of small text stays weak: «ПИСАДКОЕ КРАСНОЕ» for «ПОЛУСЛАДКОЕ КРАСНОЕ», and
  "Icosa del Sole" on the `izola-del-sole` can.
- A second check at 21:50 with the final code (`json_schema` in the request, owner answer
  of 21:45:41): 8 of 8 answers were valid, the 2 images that failed before and 6 more
  `bottle` package cuts. The times were 13 to 31 s; the first request took 286 s. The
  cause of the 286 s is not known: a first compile of the `json_schema` grammar, or the
  SAM3 run of drink-atlas-workspace-cb on the same gx10.
- More OCR errors of small text in that check: «Усадьба Черовских» for «Усадьба
  Перовских», "Listo" for "Listva".

## 2026-09-25 — a probe of the detail prompts on `qwen3.5-9b-nvfp4`

Status: measured on 2026-09-25 at 19:20 MSK by session drink-atlas-workspace-a7
[bbd3b6]. The prompts are the two prompts of the owner message of 19:14:31, sent
verbatim. Three requests, one at a time, through llama-swap 18081: thinking off,
`response_format: json_object`, `max_tokens` 4096, the cut of `image_derivative` as a
JPEG (`describe_images.image_data_url`). No cache record, no database write.

| Case | Input | Long side | Time | Prompt tokens | Completion tokens |
|---|---|---|---|---|---|
| package prompt, `bottle` | package cut `2e667cfd…` (353 × 1,136, `myshako-igristoe-beloe-polusladkoe`) | own size | 15.7 s | 582 | 346 |
| label prompt | label cut `9f3d8fce…` of a back label close-up (`avtohtonnoe-vino-kryma-beloe-suhoe`) | 1,024 | 79.3 s | 1,059 | 1,759 |
| label prompt | the same cut | 1,536 | 60.5 s | 2,051 | 1,324 |

- Each answer ended with `finish_reason: stop` and parsed as JSON.
- The package answer used the key `text` instead of `texts`. So a schema check of each
  answer is necessary, and a key drift MUST count as a failure.
- The package answer read the large texts. It misread the small line «ИГРИСТОЕ ВИНО» as
  «ИГРИСТОВОЕ ВИНО», and it did not report «ВИНОДЕЛЬНЯ». The source cut is small (353 ×
  1,136). The model gave `bottle` as an object `{colour, shape, capsule}` and each mark
  as `{place}` with no description.
- The back label answer read each text block of the label correctly, also the address,
  the e-mail, the bottling date, and the barcode digits. `vintage` came as the string
  `"2021"`.
- A back label needs about 1,300 to 1,800 completion tokens. The limit of
  `describe_images.MAX_TOKENS` (300) is too small for the detail prompts.
- At 16 s for each package image, about 2,020 images take about 9 hours. This is an
  estimate from one request.

## 2026-09-25 — the label files of the test sets and the Testset page (plan 24)

Status: measured on 2026-09-25 by session drink-atlas-workspace-ca [a2daf6] on the three
sets of `svoe-vino-testset/dataset/` and on a copy of `data/lab.sqlite3`.

- The label entries hold these fields alone: `label`, `ts`, `comment`, `proposed`, `by`,
  `confidence` (a float), `source_url`, `moved_from`, `copied_from`, `reassign_to`, and
  `prefilled_from` (an object; `official-real-photos` alone). No entry is empty, no entry
  holds `ts` alone, and no entry holds `delete` or `copy_to`. No entry names a missing
  file. So the columns of schema 019 keep every value, and `extra` stays empty for the
  three sets.
- The longest texts: a photo comment of 1,387 characters, a wine note of 2,671, a reason
  of 100. The limit of 4,000 of the old tool holds.
- The round trip (the new import, then `export_testset.py`) gives the same `labels`,
  `wines`, excluded slugs, `note`, and `counts` as the source files; the JSON text with
  sorted keys is equal too. The import of the three sets takes about 5 s when the store
  holds each file (the SHA-256 of 4,323 files).
- `image.width` and `image.height` are the size of the file header
  (`imagestore.pixel_size`), before the EXIF orientation. None of the 3,453 distinct test
  photo files has an orientation other than 1 (3,449 with 1, 4 with none). The box check
  reads the orientation of the stored file at each write, so a turned photo gets the size
  that the browser shows.
- `GET /api/testset?set=my` answers 3.1 MB in about 0.14 s (2,106 rows, 4,043 photos).
  The first draw of the page in headless Chromium took 0.8 to 0.9 s.
- At 390 px the navigation of the page was 393 px wide: `.nav` had `flex: none`, so it
  did not shrink. `width: 100%` in the phone rule lets the links wrap.

## 2026-09-25 — the image descriptions of plan 26 with `qwen3.5-9b-nvfp4`

Status: measured on 2026-09-25 from 17:03 to 17:08 by session drink-atlas-workspace-ca
[af6346]. Four check requests and the first minutes of the backlog. A small sample.

- The time of one image is 2.2 to 2.8 s (JPEG, long side 1024, thinking off, JSON mode,
  the model loaded). The first request of the day took 19.9 s; its cause was not
  examined. At 2.5 s the backlog of about 2,020 images takes about 1.5 hours.
- Each answer of the sample was valid against `ANSWER_SCHEMA`. No answer needed a retry.
- A fixed fact in the prompt pulls the other values: on a scratch copy of the database,
  the preset `package_view: back` with `content_roles: ["back_label"]` on a catalogue
  photo gave the answer `back` and `["back_label"]`. The preset `package_type: keg` on a
  bottle photo gave the answer `bottle`. So a wrong preset can also make the VLM values
  wrong; the stored value of the preset stays in both cases. `vlm_answer` shows what the
  VLM said. Do not judge the VLM by the rows with presets.
- The two example wines of the owner: the VLM answered `tetra_pak` and `can`, the same as
  the presets, with `full_package`, `front`, and `["front_label"]`.
- A reload of the model on gx10 at about 17:55: the gateway refused one connection at
  17:55:49 (not counted), and llama-swap showed `qwen3.5-9b-nvfp4` as `starting`. The next
  request waited in llama-swap and got its answer after 279.6 s, at 18:00:37. The timeout
  of the watcher is 300 s, so a slower load gives a timeout; that failure is not counted,
  and the watcher waits and asks again. The cause of the reload was not examined. The
  indicator shows a time per image that is too long for the next 20 images, because the
  mean holds this one call.

## 2026-09-25 — `qwen3.5-9b-nvfp4` of gx10 and the VLM endpoints of the scripts

Status: one live request on 2026-09-25 at about 16:21 by session drink-atlas-workspace-ca
[af6346]. One request is a small sample.

- The gateway `/v1/models` has no `qwen9.5-9b`. The owner chose `qwen3.5-9b-nvfp4`. The
  gateway serves it under the name `Qwen3.5-9B-NVFP4`.
- The request held one generated PNG of 480 × 160 pixels with the text
  `CHATEAU TEST 2021`, JSON mode, `temperature: 0`, and
  `chat_template_kwargs.enable_thinking: false`. It gave HTTP 200 in 19.9 s,
  `finish_reason: stop`, 111 prompt tokens and 24 completion tokens, and the right JSON
  `{"text": "CHATEAU TEST 2021", "year": 2021}`. The answer held no reasoning text, so
  the thinking switch of `chat_template_kwargs` works for this model. The cause of the
  time of 19.9 s was not examined. The model was loaded before the request, next to
  `qwen3.5-9b`, `qwen38-27b-nvfp4`, and `sam3`.
- The gx10 gateway needs no key. `CREDENTIALS.md` names `QWENCLOUD_TOKEN_PLAN_API_KEY`
  for the QwenCloud Token Plan and `QWENCLOUD_PAYGO_API_KEY` for DashScope. The old
  backends of `scripts/04_verify.py` read `QWEN_API_KEY` and `DASHSCOPE_API_KEY`. Both
  variables were not set in the shell of this session, so the two cloud backends were
  ignored before this change.
- `scripts/common.py` needs the key `dataset`, and `config.yaml` has none. So
  `scripts/04_verify.py` and `scripts/cluster_rules.py` run only with
  `SVOE_VINO_REVIEW_CONFIG=config.old.yaml`. This was true before this change too.

## 2026-09-25 — The model services of gx10 for the cache of plan 25

Status: measured on 2026-09-25 by session CACHE [31e42f]. One photo for each number.

- The SAM3 answer with masks is small. A catalogue photo of 906 × 1280 pixels, sent as a
  PNG of 766,538 bytes: 13,437 bytes for `derive.SAM3_TEXTS` (3 instances, 1.1 s), and
  34,464 bytes for `alternatives.DETECT_TEXTS` (12 instances, 1.2 s). Estimate: about
  2,000 originals and 2 noun lists give about 100 MB of cache records.
- `GET /upstream/sam3/health` answers `"model":"facebook/sam3"`, `"dtype":"fp16"`,
  `"workers":1`. The answer of `POST /segment_multi` has no model field.
- The gateway serves three Grounding DINO models: `grounding-dino-base`
  (`IDEA-Research/grounding-dino-base`, float32), `mm-gdino-base`
  (`openmmlab-community/mm_grounding_dino_base_o365v1_goldg_v3det`), and
  `mm-gdino-base-all`. One process serves one checkpoint, at
  `/upstream/<model>/detect`. The request is multipart: `image`, `texts`, `threshold`
  (default 0.25), `text_threshold` (default 0.25). The answer holds `count`, `width`,
  `height`, `model`, `prompts`, and `instances` (boxes and scores, no masks).
- The first GDINO call of the session took 9,667 ms (a cold start, a guess). A cache hit
  of any service takes 0 to 62 ms in the process, most of it the JSON parse.
- A GET of `/upstream/<model>/health` goes through llama-swap. The cache key therefore
  does not hold the checkpoint of `/health`: such a check before each lookup could start
  the model also for a run that the cache answers completely. Not measured; the reason
  is the start-on-demand rule of the gateway.
- `qwen3.5-9b` with the payload of `scripts/04_verify.py` (`max_tokens` 150, no
  `chat_template_kwargs`) answered `finish_reason` `length` with an empty `content` and
  about 500 characters of `reasoning_content`: the thinking of the model takes the whole
  budget. With `chat_template_kwargs.enable_thinking` false (the payload of
  `scripts/cluster_rules.py`), it answered in 1,033 ms. `04_verify.py` uses
  `qwen3-vl-32b` by default, so the default run is not affected.
- A VLM hit after SAM3 depends on the bytes that the VLM gets, not on the SAM3 cache.
  The VLM key holds the sha256 of each sent image. Measured at about 15:25 on 4 main
  photos with no transparency (method `seg`): 3 live SAM3 calls of one photo gave the same
  answer each time (no cache), and `derive.derive_image` gave the same PNG bytes on a miss,
  on a hit, and with a new client. So one original and one code version give one VLM
  input. A change of the processing, of its settings, or of the Pillow version can change
  the bytes: then the VLM gets a miss, never a wrong hit. 4 photos are a small sample:
  SAM3 is fp16 with a batch of 4, so a different batch under load could change a mask
  (not seen).

## 2026-09-25 — A lab server that an agent starts with `nohup … &` can stop with no trace

Status: one observation and a guess, not a proven cause.

- The lab server that session ff started at 12:50:39 with
  `nohup python3 pipeline/lab_server.py --no-browser >> work/lab_server.log 2>&1 &` from
  its tool shell stopped at about 13:03:30. The log has no traceback and no stop line,
  and no session stopped it. The guess of ff: a cleanup of the processes of its tool shell.
- A server started that way keeps the process group of the tool shell, also after the
  shell exits (checked with `ps -o pid,ppid,pgid`: parent 1, group of the old shell).
  `nohup` blocks SIGHUP alone. A kill of that process group stops the server.
- Mitigation, used since 13:20 on 2026-09-25: start the server in its own session, so it
  leads its own process group:

  ```bash
  python3 -c "import subprocess; subprocess.Popen(['python3', 'pipeline/lab_server.py', '--no-browser'], stdin=subprocess.DEVNULL, stdout=open('work/lab_server.log', 'ab'), stderr=subprocess.STDOUT, start_new_session=True)"
  ```

  The new process has PGID = PID. Rule 23 of `AGENTS.md` does not name this form yet; the
  owner decides.

## 2026-09-25 — The rebuild of `image` for the test sets, and the test photos in the lab

Status: tested on a `.backup` copy of `data/lab.sqlite3` (version 15) on 2026-09-25, then
applied to the live database, for schema 016.

- The rebuild of `image` (create new, copy with the rowid, `DROP TABLE image`, rename)
  works with the present `labdb.migrate`. Three tables reference `image`: `wine_image`,
  `image_derivative` (two columns), and `test_photo`. Their foreign keys name the table,
  so they point to the new table after the rename. The rows of `image` (4,054),
  `wine_image` (2,051), and `image_derivative` (2,023) stayed. `PRAGMA
  foreign_key_check` found no problem. Q1 fact 2 of plan 12 (the failed rebuild) holds
  only for the old `migrate`, which ran with the foreign keys on.
- The server needs no restart after a schema file that changes no column that its code
  reads. It checks the version on each request, so it answers HTTP 200 again when the
  migration is done.
- The three sets hold 4,323 photo rows and 3,453 distinct files. In `my`, 690 rows hold
  the bytes of an earlier row of `my`. This check did not find the cause. All 180 photos of
  `vlmrerank-8b-failed` are photos of `my`. 4 test photos have the bytes of a lab image:
  2 in `additional` and 2 in `patched`.
- The labels of `my` that are NULL: 1,487. Of these, 428 files have no entry in
  `review-labels.json`, and 1,059 entries have no `label` field.

## 2026-09-25 — A rebuild of a parent table in a schema file

Status: tested on a `.backup` copy of `data/lab.sqlite3` (version 13) on 2026-09-25 with
SQLite 3.53.4 of Python 3.14, for schema 014.

- `labdb.migrate` ran each file inside `BEGIN … COMMIT` with the foreign keys on. The
  rebuild of `wine_catalog` (create new, copy, `DROP TABLE wine_catalog`, rename) failed
  at the COMMIT with `FOREIGN KEY constraint failed`.
- `PRAGMA defer_foreign_keys = ON` in the file does not help: the COMMIT fails in the
  same way, also after the new table has the name `wine_catalog`.
- `PRAGMA foreign_keys = OFF` has no effect inside a transaction. It MUST be set before
  BEGIN. With the foreign keys off, the rebuild worked, and `PRAGMA foreign_key_check`
  before the COMMIT found no broken link. This is the procedure of the SQLite ALTER TABLE
  documentation.
- The rename of `wine_catalog_new` to `wine_catalog` does not rewrite the CREATE text of
  the child tables: each still says `REFERENCES wine_catalog`. The rowids, the comment
  ids, and the row counts of the 6 tables did not change.

## 2026-09-25 — The spelling of Cyrillic letters in the slugs of vino-svoe.ru

Status: a comparison of the words of `name` with the words of `wine_slug` in
`data/lab.sqlite3` on 2026-09-25, 1,783 matched words.

- The most common spelling of each letter: `х` h (175), `ц` ts (128; cz 26), `ш` sh,
  `ч` ch, `ж` zh, `й` y (258; j 71), `ы` y, `ю` yu, `я` ya, `ё` yo, `э` e, `ь` and `ъ`
  nothing. `щ` has one sample: shh.
- With this spelling, the name alone gives the website slug for 325 of 2,103 wines, and
  the start of the slug for 21 more. Most other slugs add the producer, the grapes, or
  the type, for example `fanagoriya-100-ottenkov-shardone-beloe-suhoe-14`.

## 2026-09-25 — Why each label item of `/embedding` fails

Status: code reading and a read-only probe of SAM3 on gx10 on 2026-09-25 (owner message
of 12:11:50). `data/lab.sqlite3` at version 12.

- Each of the 2,021 `label` items of `gx10-siglip2-so400m-patch16-naflex-p256` fails with
  `no label cut yet`. `build.log` holds no other error of the view `label`.
- The cause is in `embeddings.read_inputs`: it sets `cuts["label"]` to `None` for each
  source. The view `label` starts with `segment target: label`, so `prepare` raises
  `ItemError(NO_CUT["label"])` before any request to the model. No label image is made,
  and no vector.
- The label cut of a full photo does not exist. Plan 10, "Work outside this plan", states
  it as not started. `image_derivative` has the primary key `source_sha256`, so it holds
  one processed file for each original: the package cut. It has no place for a second
  cut.
- The database holds no close-up (`label_front`, `label_back`) of an Active wine: each
  of the 2,021 sources has the role `full`.
- `alternatives.label_instance` and `alternatives.label_cut` (the rule of
  `svoe-wino-hackaton/scripts/build_labels.py`) work on full photos too. Probe: 8 random
  full sources, the nouns `label, bottle` and `barcode, bottle, label, bottle neck, can`.
  Each noun set found a label on 8 of 8, with the same box. The cut covered 10 % to 52 %
  of the photo; the score was 0.85 to 0.98. SAM3 took 0.4 to 0.8 s for each photo. By
  eye, each cut is the front label with no bottle and no background.
- A label cut of each full source takes about 2,021 × 0.6 s ≈ 20 min on gx10.
- The real run (12:46:36 to 13:36:59) took 3,022 s, 1.5 s for each photo, not 0.6 s. The
  seed process waited on the SAM3 socket for about 75 % of the time (`sample`). The gx10
  GPU was at 96 %, with vLLM, two Qwen models, and ComfyUI next to SAM3. Batches of 50
  took 36 s in quiet minutes and several minutes in busy ones.
- Result: 2,019 of 2,023 full originals have a label cut. SAM3 found no label on 4:
  `3e9045b9…`, `45738caa…`, `5478f9d5…`, `97e800d0…`.
- The bar of a build showed `0 / 2023` for 41 s once. Two later logs got the first
  `progress` line after 2 to 4 s. The log of the slow build was overwritten, so the cause
  is not proved; the likely cause is the cold start of the SigLIP model on the gateway,
  which was not loaded at 12:57 (`/running` listed `qwen3.5-9b`, `qwen38-27b-nvfp4`,
  `sam3`).

## 2026-09-25 — The slug prefix of a manual wine

Status: queries of `data/lab.sqlite3` on 2026-09-25 for plan 20, 2,103 wines.

- No slug starts with `_`. So the prefix `__` of a manual wine cannot collide with a slug
  of the catalogue.
- Each slug holds `a-z`, `0-9`, `-`, and `_` alone. 36 slugs hold `_`, for example
  `denisov_pazori_risling`. The longest slug has 139 characters.
- `category` has 4 values (`Белое`, `Красное`, `Розовое`, `Оранжевое`). `color` is free
  text with 826 distinct values. There are 135 producers and 9 regions.
- Python 3.14 has no module `cgi`, so `http.server` has no multipart parser. The route
  `POST /api/wine` takes JSON with the image in base64.

## 2026-09-25 — A barcode tells the back of a package

Status: probed on 2026-09-25 for plan 16. Read-only calls to SAM3 on gx10, with the noun
`barcode` added.

- 16 random photos of `frap-public-small/objects/images`, judged by eye. With the first
  rule (a barcode whose centre lies on the largest bottle or can): 4 wrong sides. A
  front of a Kopke bottle got 4 barcodes: two faint ones (score 0.38 and 0.56, height 1 %
  of the photo) in the text of its label, two beside it. A front view of a PET bottle got
  a narrow barcode on the edge of the label that wraps the side (score 0.80, 6 % of the
  bottle width). A glass decanter with a hanging tag got the barcode of the tag. The
  back of a decanter with an information label had no barcode.
- Real back barcodes had scores of 0.94 and 0.95 and 18 % and 30 % of the bottle width.
  The limits 0.7 and 10 % keep them and reject the first two errors. Then 13 or 14 of
  16 sides are right. The limits came from these errors, so this is no accuracy
  measure.
- 15 lab photos with no back view (12 catalogue `main` images and the 3 owner photos of
  `avtohtonnoe-vino-kryma-beloe-suhoe`) gave no back type with the limits.
- A novelty decanter in the shape of a cat has no neck. The detection calls it a label.
- The time of one SAM3 call grows with the nouns. 7 lab images (4 catalogue images, 3
  owner photos): six nouns 5.2 s, the five nouns `barcode, bottle, label, bottle neck,
  can` 4.4 s, the four nouns without `can` 3.9 s. The types were the same, except the
  can: without the noun `can` it became `label_front`. `label` alone found a label cut in
  7 of 7 images.

## 2026-09-25 — The catalogue API of vino-svoe.ru for the website import

Status: probed on 2026-09-25 from this Mac for plan 18. Read-only requests. No proxy is
necessary.

- `robots.txt` of `api.vino-svoe.ru` disallows everything except `*/img/*` and
  `*/file-proxy/str-api-file-name/*`. `robots.txt` of `vino-svoe.ru` allows the wine
  pages and `wines-sitemap.xml`. The owner chose the API with this knowledge.
- `GET /v1/wines?page=N&perPage=30`: 30 is the maximum. 2,105 wines on 71 pages, no
  duplicate slug. A list item holds `slug`, `title`, `manufacturer`, `category`,
  `color`, `region`, and `image.url`, but no description and no grapes. The card
  `GET /v1/wines/<slug>` holds them.
- `GET /v1/file-proxy/str-api-file-name/uploads/<name>` returns the original upload.
  Its SHA-256 equals the stored `main` image of the Strapi delivery of 2026-09-17. The
  resize proxy `/v1/img/...` does not give the original.
- The slug set and the image names of the API equal those of `wines-sitemap.xml`.
- The API `category` holds the colour and the sweetness (19 values, for example
  `Белое сухое`). The first word is one of the four values of `wine_catalog.category`.
- The grape names of a card, joined with `, `, and the trimmed `description` equal the
  delivery for 3 of 3 sampled wines. A `title` can have a leading space.
- Compared with the delivery of 2026-09-17: 73 new wines, 71 missing wines, 52 wines
  with no `main` row. 13 wines have another upload name; 10 of them have the same bytes,
  and 3 have new bytes (`vintazh-premium`, `muskat-premium`, `shardone-rezerv`). 7 wines
  have 9 changed list fields.
- The 10 names with the same bytes are not new uploads. Each has `match_method` =
  `name-identical`: the delivery held several equal copies of the file, and
  `seed_images.py` took the first name in sort order. The website uses another copy. So
  a different name does not prove a changed image. The import compares bytes.
- No response header gives a hash or a date of the original. `HEAD` of
  `/v1/file-proxy/...` gives `Content-Length` (the exact size of the original),
  `Content-Type`, and `Accept-Ranges: bytes`, but no `ETag` and no `Last-Modified`. The
  server is `QRATOR`. A `Range: bytes=0-0` request answers 206 with
  `Content-Range: bytes 0-0/<size>`. The resize proxy `/v1/img/...` gives other bytes
  (59,306 bytes for an original of 90,880 bytes). The `image` object of the API holds
  `altText` and `url` alone.
- `wines-sitemap.xml` gives a `lastmod` for each of the 2,105 wines. The 3 wines with new
  image bytes have `lastmod` on 2026-09-17 (after 19:00) and 2026-09-22. The 10
  `name-identical` wines have `lastmod` from January to July 2026. Only 10 known wines
  have `lastmod` on or after 2026-09-17. It is not known whether a replacement of a file
  in the Strapi media library changes the `lastmod` of the wine.
- The list of the API is in the order of creation, the newest first.
  `https://vino-svoe.ru/api/wines` is the same list (the same 8 fields, 2,105 items).
  The `robots.txt` of `vino-svoe.ru` disallows `/api/*`. 71 of the 73 new wines are in
  the first 90 positions. The other 2 (`pinot-noir-2024`, `chardonnay-2024`) are at
  positions 1,047 and 1,048: their image is the image of a missing wine, so they are
  probably renamed slugs of old wines. So a read of the first pages alone does not find
  each new wine. A missing wine needs the full list anyway. The list is 71 requests.
- A reused HTTPS connection answers a `GET` of an original (52 KB mean) in 0.16 s and a
  `HEAD` in 0.16 s. A new connection for each request needs 0.53 s and 0.45 s. So a size
  check with `HEAD` saves no time, and the pause of 0.25 s sets the time of a run.
- A full compare with one reused connection (2026-09-25, 12:51 to 13:03) took 11.5
  minutes for 2,255 requests and 150 MB: the list in about 40 s, the images in about
  10.5 minutes. The run of plan 18 with a new connection for each request took 22.5
  minutes. The pause of 0.25 s alone would allow about 9.5 minutes.
- JPEG, PNG, and WebP hold no checksum of the whole file. PNG has a CRC-32 in each
  chunk; the CRC of `IHDR` covers the header fields alone. WebP (RIFF) and JPEG hold no
  checksum.

## 2026-09-25 — SAM3 tells a full package from a label close-up

Status: probed on 2026-09-25 for plan 16. Read-only calls to SAM3 on gx10.

- Set: 12 random catalogue `main` images of `data/lab.sqlite3` (11 bottles, 1 can), 4
  label crops of 4 of them (45 % to 85 % of the height), and the patch photo of
  `avtohtonnoe-vino-kryma-beloe-suhoe` (the upper part of a bottle, other bottles behind
  it). Nouns `bottle, bottle neck, can, label, wine bottle label`, threshold 0.35, long
  side 1536 px.
- The neck rule of the FRAP prototype (workspace `ResearchLog.md`, 2026-09-23) alone: 11
  of 12 full, 4 of 4 crops, and the patch photo wrong. The can has no neck. The necks of
  the bottles behind the patch photo counted.
- Rule 10 of plan 16 adds two tests: the neck lies inside the largest bottle (2 %
  tolerance), and a can that covers 90 % of the height of a photo at least two times as
  tall as wide is a full package. It gave 17 of 17 on the same set. The rule was fitted
  to this set, so the number does not measure its accuracy.
- SAM3 finds a `bottle` in a label crop too: the bottle box then fills the crop, and the
  neck is missing or touches the top edge.
- In a label crop the label box can equal the bottle box. The rule of `build_labels.py`
  then rejects the label as the package. The label cut of plan 16 falls back to the
  largest label.
- A browser check on a copy of the database with the live SAM3: a whole catalogue bottle
  got `front_full`, a crop of its label `front_label` (named `full_front` and
  `label_front` since schema 012). The two uploads with detection and
  processing took 2.5 s together; a change from `FL` to `FF` took 0.7 s.

## 2026-09-25 — Why a save of a code on `/dataset` took a couple of seconds

Status: measured on 2026-09-25. Fixed the same day (plan 11, decision O2, point 6).

- The server is fast. `add_code` and `remove_code` on a copy of `data/lab.sqlite3` took
  1 to 4 ms on the T7 drive and on the internal disk. `GET /api/dataset` took 30 to
  80 ms.
- The page was slow. `saveGtin`, `saveBarcode`, and `saveQrUrl` called the full
  `render()` two times: once for the busy mark, and once after the answer. The `+`
  button and the cancel called it one more time. `render()` builds all 2,103 cards
  again, each with its image.
- Headless Chromium on this Mac: a full `render()` took 234 to 306 ms to the paint.
  `renderCard()` of one card took 17 to 28 ms. One save took about 540 ms. A comment in
  the page gives about 0.7 s for a full render. The browser window of the owner was
  slower again: "a couple of seconds". That time was not measured.
- `applyView()` takes about 13 ms. So the cost is the DOM of 2,103 cards, not the filter.
- The state buttons already used `renderCard(slug)`. The code editors now do the same.
  After the fix, a GTIN save took about 60 ms and the `+` button about 50 ms.
- Limit: `renderCard` does not apply the text search again. A card whose GTIN you
  remove stays in a search for that GTIN until the next full render.

## 2026-09-25 — SIGINT does not stop a lab server that a script started in the background

Status: seen on 2026-09-25 at the deploy of schema 008. Not checked at the source.

- Rule 23 of `AGENTS.md` says: stop the process on port 8168 with SIGINT. `kill -INT` on
  the running `python3 pipeline/lab_server.py --no-browser` (PID 49812) did nothing: the
  port stayed open for more than 5 s. `kill -TERM` stopped it at once.
- A probable cause: a shell that is not interactive starts a command with `&` with SIGINT
  set to "ignore". Python then does not install its handler for SIGINT, so the server
  gets no `KeyboardInterrupt`. macOS `ps` has no field that shows the ignored signals, so
  this cause is not confirmed.
- The lab server holds no state between requests. It opens the database for each request,
  and each write is one transaction. So SIGTERM is a safe stop. The log line `stopped`
  of `main` does not appear after SIGTERM.
- The same failure came again at the restarts of 10:32:52, 11:16:21, and about 11:22.
  At 11:22 the process state was `SN` (sleeping), not `U`, so it was not disk
  contention. SIGTERM stopped the process each time.
- Decision: the owner chose SIGTERM on 2026-09-25 at 11:29:27. Rule 23 of `AGENTS.md`
  names SIGTERM since then.

## 2026-09-25 — the GS1 check digit and the GTIN-14 form

Status: used in `pipeline/codes.py` and in `pipeline/pages/dataset.html`. Tested with the
23 GTINs of `code-map.json` and with an EAN-8 and a UPC-A example.

- The check digit is the last digit. The other digits get the weights 3 and 1 in turn,
  from the right: the digit next to the check digit gets 3. The check digit is
  `(10 - sum mod 10) mod 10`.
- A leading zero adds 0 to the sum, so the GTIN-14 form (leading zeros up to 14 digits)
  has the same check digit as the value as read. The seed and the server check the value
  as read, then store the GTIN-14 form.
- The (01) field of a DataMatrix code gives 14 digits, for example `04630037251630`. The
  EAN-13 code of the same product gives `4630037251630`. The GTIN-14 form gives both one
  row. The owner chose this form on 2026-09-25.
- The check digit does not prove that a GTIN exists. For example, `00000000000000` has a
  valid check digit, and `codes.py` accepts it.

## 2026-09-25 — drop the column `image.folder` in place, not with a table rebuild

Status: tested on 2026-09-25 on a backup copy of `data/lab.sqlite3` (schema 7: 4,042
`image` rows, 2,046 `wine_image` rows, 2,018 `image_derivative` rows). SQLite 3.53.4 in
Python. The result shapes the schema file of the flat image store.

- A rebuild of `image` fails in `pipeline/labdb.py`. drink-atlas-workspace-20 found it:
  `CREATE image_new`, `INSERT … SELECT`, `DROP TABLE image`, `ALTER TABLE image_new
  RENAME TO image` ends in "FOREIGN KEY constraint failed" at `COMMIT`, also with
  `PRAGMA defer_foreign_keys = ON`. The `DROP` counts one deferred violation for each child
  row. The `RENAME` does not clear the counter. `labdb.migrate` runs each file in one
  transaction with `foreign_keys = ON`, and this pragma cannot change inside a transaction.
- `ALTER TABLE image DROP COLUMN folder` works in the same wrapper:
  `executescript("BEGIN; ALTER TABLE image DROP COLUMN folder; PRAGMA user_version = N;
  COMMIT;")` on a connection with `foreign_keys = ON`. All 4,042 rows stay.
  `PRAGMA foreign_key_check` returns no row. `PRAGMA integrity_check` returns `ok`.
- SQLite allows `DROP COLUMN` (3.35 and later) only for a column that is not a key, not
  indexed, not in a foreign key, not in a view or a trigger, and not in a CHECK of another
  column. The CHECK of `folder` belongs to `folder` itself, so the drop is allowed.
- A later change that needs a real rebuild of a parent table needs the 12-step procedure
  of SQLite in `labdb.py`: `PRAGMA foreign_keys = OFF` before `BEGIN`, `PRAGMA
  foreign_key_check` before `COMMIT`, then `foreign_keys = ON`.

## 2026-09-25 — the SigLIP 2 models of the gx10 gateway

Status: read from `GET http://192.168.86.14:18081/v1/models` on 2026-09-25. The result
shapes the embedding configuration of the Embeddings page.

- The API route is `POST http://192.168.86.14:18081/v1/embeddings`. The address
  `http://192.168.86.14:18081/ui/#/models/<id>` is the llama-swap UI page of a model. It
  is not an API route.
- `siglip2-so400m-patch16-naflex`: image and text, 1152-d, L2-normalized, native aspect
  ratio. The default patch budget is 256 patches of 16 px. The request field
  `max_num_patches` changes the budget, from 1 to 4096. Cold start about 48 s. Warm about
  30 ms for 2 images. Reserve about 7 GB.
- `siglip2-so400m-patch14-384`: fixed 384 x 384 input, squash with no crop. It is not
  NaFlex. The field `max_num_patches` gives HTTP 400. Its vectors are identical to the
  removed model ID `siglip2`, so the old `siglip2` indexes stay valid.
- The gateway also serves `siglip2-so400m-patch16-256`, `-384`, and `-512` (fixed size),
  and the image-only `naflexvit_so400m_patch16_siglip.v2_webli` (timm).
- The Hugging Face repository of the NaFlex model is `google/siglip2-so400m-patch16-naflex`.
  The repository `google/siglip2-so400m-patch14-384` is a different model.
- The input images of the gateway MUST be JPEG, PNG, or WebP data URIs.
  `scripts/common.py` `data_url` sends a JPEG of quality 88 when it resizes. A JPEG
  changes the pixels that the model sees.
- The gateway drops the alpha channel of an RGBA PNG. Measured on 2026-09-25 with
  `dinov3-vitb16-pretrain-lvd1689m` and a 256 x 512 test image: an RGBA image and the
  same image with the alpha removed by Pillow `convert("RGB")` give cos 1.0000. The same
  RGBA image with a red and with a blue colour under the transparent pixels gives cos
  0.9750. So the model sees the colour under a transparent pixel. The SigLIP 2 models
  were not measured. The probe script is not kept.
  (2026-09-29: the SigLIP 2 models are measured; read the entry "The alpha channel and
  the background fill of the SigLIP 2 models" and
  `docs/reports/siglip2-alpha-background-2026-09-29.md`.)
- The llama-swap folder "Image embeddings" holds 12 models: the 9 models of the list
  above and `wemm-embed-2b`, `wemm-embed-4b`, `wemm-embed-9b`.
  `naflexvit_so400m_patch16_siglip.v2_webli` accepts `max_num_patches` (1 to 4096,
  default 256). `PE-Core-L14-336` squashes to 336 x 336, 1024-d. `dinov3-vitb16` is
  768-d, `dinov3-vitl16` is 1024-d, both image-only.
- NaFlex works on this Mac. Measured on 2026-09-25 in `~/.venvs/svoe-vino-lab` (torch
  2.14.0, transformers 5.17.0, torchvision 0.29.0, `mps`): 4 card images of 4 wines,
  variant C, long side 1024 px, `max_num_patches` 256. The cos of the local vector and
  the gateway vector of the same PNG: 0.9946, 0.9986, 0.9985, 0.9903. The cos between
  two different wines: 0.65 to 0.69. The model load took 18.4 s. The first batch of 4
  images took 3.4 s. The model files are 4.54 GB (`model.safetensors`).
- The first build of `gx10-siglip2-so400m-patch16-naflex-p256` on 2026-09-25: 2,018 full
  items (variant C, long side 1024 px) in 216 s over two runs (a stop with SIGTERM
  after 416 items, then 1,602 items), so about 9 items per second from this Mac over the
  T7 disk. The directory holds 397 MB: about 200 KB for each PNG. A third run found
  2,018 current items and ended in 0.3 s.
- The image processors of `transformers` 5 need `torchvision`. Without it,
  `AutoImageProcessor` raises `ImportError`.
- The system `python3` of this Mac (Homebrew 3.14) has `torch` 2.11.0, and `mps` is
  available. `import transformers` fails with `Unable to compare versions for
  numpy>=1.17: need=1.17 found=None`. The cause: site-packages holds two numpy
  `dist-info` directories, `numpy-2.4.4.dist-info` and `numpy-2.5.3.dist-info`.
  `svoe-vino-matcher/.venv` has no `torch`.
- The Hugging Face cache holds `google/siglip2-so400m-patch14-384` alone. It does not
  hold `google/siglip2-so400m-patch16-naflex`.
- `svoe-vino-matcher/index/` stores one index as `<path>-<hash10>.npz` with the arrays
  `item_ids`, `slugs`, and `vectors` (float32, N x 1152), and a `.meta.json` with the
  settings and the build facts.

## 2026-09-25 — the SAM3 noun `box`

Status: measured on the 143 files of `data/images/main/` with no transparent pixels.
The texts were `wine bottle, can, packet` first, then `wine bottle, can, packet, box`.

- With `box`, 137 of 143 processed files stay byte-identical. 6 change.
- 4 bag-in-box images of Союз-Вино (6 wines) are correct now: the mask is the whole box.
  Before, SAM3 took the bottle that is printed on the box, or it found nothing.
- 2 images are worse now. On `ona-skazala-da` (a photo of a table) the largest instance
  is a wooden crate. On `fanagoriya-tochka-saperavi-krasnoe-suhoe-14` (a bottle and its
  tube) the largest instance is the tube.
- A rule can separate the cases: a box wins when it holds the bottle instance. The
  bottle of a bag-in-box is printed inside the box. The crate and the tube stand next to
  the bottle.
- The run took 1 min 31 s for 143 requests.

## 2026-09-25 — the processing of the main images with SAM3

Status: measured on the 2,018 files of `data/images/main/` with `pipeline/derive.py`.

- 1,875 files hold transparent pixels. 143 files are RGB with no alpha channel.
- A crop by the alpha rule takes about 0.11 s for each file and gives a PNG of about
  0.5 MB. The full run took 4 min 25 s. The processed files take 1.2 GB.
- SAM3 answered each of the 143 requests. It found a package on 142 files. On one
  bag-in-box image it found nothing for `wine bottle, can, packet`.
- On 3 other bag-in-box images, the largest instance is the bottle that is printed on the
  box. A noun for the box, for example `box`, is not tested yet.
- On a photo of a scene, SAM3 finds the bottle. The mask edge of such a photo can be rough.

## 2026-09-24 — the pixel sizes of the main images

Status: measured with Pillow on the 2,018 files of `data/images/main/`.

- A read of the size from the file header takes about 2 s for all 2,018 files.
- The smallest image is 120 x 460 pixels. The next are 140 x 532 and 116 x 700.
- The largest images are 3977 x 8347 and 6337 x 9506 pixels.
- The median is 385,200 pixels.

## 2026-09-24 — the offline match of the main images

Status: measured on `official-2026-09-17` and on the 2,103 wines of `data/lab.sqlite3`.
The result shapes `docs/plans/08_seed-images.md`.

- The delivery holds no Strapi database dump. `prod-svoe-vino-strapi/` holds the flat
  folder `strapi/uploads` alone: 15,803 files, of them 15,199 `.webp`. 6,241 file names
  carry the Strapi suffix `_<10 hex>` and are not a resized variant. The match index
  holds these 6,241 files.
- The match of `build_catalog.py` uses `csv_photo_name`. The wine name is not part of it.
- Stage 1 of `build_catalog.py`, offline:
  - one candidate: 2,023 wines;
  - several candidates: 75 wines, of them 23 with equal bytes and 52 with different bytes;
  - no candidate: 5 wines.
- So an offline run with no live answer finds 2,046 wines, and 57 wines get no file.
- `derived/official-2026-09-17/catalog.jsonl` holds the live answers of 2026-09-17:
  2,023 `csv-name-unique`, 70 `live-og-image`, 10 `unresolved`. It names a file for 47 of
  the 52 wines with different bytes and for the 5 wines with no candidate. For the 2,023
  wines with one candidate, it names the same file each time.
- The 2,046 found wines use 2,018 different files, 135 MB. So some wines share a file:
  2,023 `name-unique` wines use 1,998 files, and 23 `name-identical` wines use 20 files.
- A survey of the test sets of `svoe-vino-testset` is in the section "Input for the
  test set step" of plan 08.

## 2026-09-24 — keys and dependencies of `strapi_output0709.csv`

Status: measured on the file of `official-2026-09-17`. The result shapes the table
`wine_catalog` of `docs/plans/07_sqlite-lab-database.md`.

- The file has 4,147 data rows and nine columns: `Название вина`, `Категория`, `Цвет`,
  `Регион`, `Сорт винограда`, `Описание`, `Винодельня`, `Slug`, `Название фото`.
  It has no byte order mark. SHA-256:
  `12a1b0b620db7a2264b094446861e83940a927708d65a1b7ccffda7ec3aeffee`.
- 2,044 rows are exact copies of an earlier row. 2,103 distinct rows remain, one per
  `Slug`. No slug has two different rows.
- `Slug` is the only candidate key. `Название фото` has 2,090 distinct values: 13 photo
  names are shared by two slugs, for example `DSC09173.webp` for `aligote-barrel-2024`
  and `aligote-barrel-2025`. `Описание` has 2,083 distinct values.
- `Винодельня → Регион` does not hold. Three of the 135 producers appear in two regions:
  Olymp Winery, Vibes, and Союз-Вино. So `region` is not a transitive dependency.
- (`Винодельня`, `Название вина`) is not a key: 64 pairs have more than one slug. These
  are vintages, alcohol values, and other variants.
- `Сорт винограда` is a list. A wine has 0 to 9 grapes, 140 distinct grape names. 344
  values use `,`, and 2 values use ` и `. 2 wines have an empty value:
  `beloe-polusladkoe` and
  `igristoe-zhemchuzhnoe-vino-polusuhoe-krasnoe-di-kaspiko-fiori-di-mare-di-caspico-fiori-di-mare`.
- 198 values of the distinct rows have outer white space: 31 in `Название вина`, 120 in
  `Описание`, 37 in `Цвет`, and 10 in `Винодельня`. `build_catalog.py` of
  `svoe-wino-hackaton` trims them with `str.strip()`.
- `Категория` has 4 values. `Регион` has 9 values.

## 2026-09-24 — stage 1 A/B: `qwen3.8-max` against `qwen3.5-9b`

Status: measured on 133 cards. The open questions are Q7 and Q8 of
`docs/plans/06_label-only-cluster-rules.md`. No project file and no rule changed.

- Sample: the cards of the 43 mixed clusters and the 31 cluster cards with a year in
  the name, 133 cards. `qwen3.8-max` of QwenCloud, thinking off, got the unchanged
  `DESCRIBE_PROMPT` through `describe()` of `scripts/cluster_rules.py`, twice: with the
  whole catalogue picture (the input of the stored `qwen3.5-9b` descriptions) and with
  the label crop. Both pictures went at a long side of 2048 pixels.
- 266 calls, 0 errors. Median 15.7 s for the whole picture and 18.7 s for the label
  crop. Tokens: 184,425 prompt and 61,016 completion for the whole picture; 358,515
  and 50,070 for the label crop.
- On the 31 cards with a year in the name, each of the three variants gives that year
  for 23 cards.
- The three readings of the label year agree on 119 of the 133 cards. `qwen3.8-max`
  wrote no transliteration in stage 1.
- The 14 cards with different readings, judged by eye on enlarged pictures:

| Card | On the picture | 9B | max, whole | max, label crop |
|---|---|---|---|---|
| `abrau-dyurso-pino-nuar-krasnoe-suhoe-125` | «урож. 2024 года» | 2024 right | 2021 wrong | 2023 wrong |
| `abrau-dyurso-risling-beloe-suhoe-12` | «урож. 202? года», last digit unreadable | none, wrong | 2020 ? | 2021 ? |
| `b-yu-rne-pino-gri-beloe-suhoe` | 2024 on a lower label strip | right | right | the strip is not in the crop |
| `b-yu-rne-pino-gri-pozdnij-sbor-sladkoe-beloe` | 2025 on a lower label strip | right | right | the strip is not in the crop |
| `leto-kaberne-fran-rezerv-2020-suhoe-krasnoe` | four blurred characters on the edge | none ? | 2021 ? | none ? |
| `locantita-more` | «2023», probably, inside the main label | none, wrong | right | none, wrong |
| `novyy-svet-…-kyuve-de-prestizh-shardone-125` | 2013 on the glass | right | right | not in the crop |
| `novyy-svet-…-kollektsionnoe-…-shardone-125` | 2016 on the neck band | right | right | not in the crop |
| `novyy-svet-…-vyderzhannoe-bryut-…-125` | 2018 on the neck band | none, wrong | right | not in the crop |
| `novyy-svet-…-vyderzhannoe-polusladkoe-rozovoe-…-125` | 2018 on the neck band | none, wrong | right | not in the crop |
| `shato-pino-petnat-pino-gri-beloe-ekstra-bryut-11` | a handwritten «2020», probably | none, wrong | right | none, wrong |
| `soyuz-vino-kubanskoe-traditsionnoe-…-11` | «ТРАДИЦИИ ВИНОДЕЛИЯ 1976», a table wine, no vintage | 1976, wrong | none, right | none, right |
| `vinodelnya-berdyaeva-risling-risling-reynskiy-beloe-suhoe-121` | 2022 printed vertically beside «РИСЛИНГ» | none, wrong | right | right |
| `vinodelnya-byurne-sira-krasnoe-suhoe-135` | 2019 on a lower label strip | right | right | not in the crop |

- On these 14 cards: `qwen3.8-max` on the whole picture is right 11 times, wrong once,
  and unknown twice. `qwen3.5-9b` is right 6 times, wrong 7 times, and unknown once.
  The label crop is right twice and wrong 3 times; for 7 cards the year is outside the
  crop; 2 are unknown.
- The one card where the 9B wins is the probe of 2026-09-23 that kept stage 1 local.
- The label crop is a poor input for stage 1: the SAM3 crop keeps one label mask. It
  cuts away a lower label strip (Бюрнье: the grape, the sugar level, and the year are
  all on it; the main labels of two Бюрнье cards are identical) and a neck band (Новый
  Свет: the vintage). Inside the crop, `qwen3.8-max` missed two years that it read on
  the whole picture.
- The query crop of the re-rank is made the same way. Whether it drops such strips on
  real photos was not measured: c001 triggered the step on one test photo only.

## 2026-09-24 — the review page and the index builder need one ignore source

An ignore control in a page is not enough. The index builder must read the same state,
and the index name must change with that state. Otherwise a rebuild can reuse vectors
that contain an ignored image. The shared document identifies a main image by kind and
slug. It identifies an additional image by kind, slug, and exact file name. Photo and
label decisions stay independent.

The page also uses the exact prepared directories. It does not replace a missing crop
or label with the catalogue image. This makes missing preprocessing visible.

## 2026-09-24 — a raw image route can also give a browser preview

The Dataset page needs raw image URLs for its image elements. A clicked image also
needs a checkerboard viewer, because a native browser image tab does not show a clear
boundary for transparent pixels. The page opens this viewer as a modal, so the list
keeps its scroll position. Its arrows use the filtered and sorted records already on
the page. The catalogue and patch routes also use content negotiation for a direct
navigation. A request that accepts HTML gets the standalone viewer. An image request
gets the original bytes. The parameters `view=1` and `raw=1` make either result
explicit.

## 2026-09-24 — the Dataset page follows the full-list review flow

The owner requested the same continuous list as the Review page. The Dataset page now
puts every filtered catalogue record in one document. It has no row-size selector and
no page buttons. Search waits 180 ms after input before it rebuilds the list. Image
elements keep `loading="lazy"`, so the browser can defer images below the viewport.

## 2026-09-24 — label-only rules: the full benchmark

Status: measured. Run
`runs/2026-09-24T080721Z-svm-label-gw-cluster-rules-label-only-rules`, 2,180 photos.
Plan: `docs/plans/06_label-only-cluster-rules.md`; its section «Result» holds every
number.

- Against the base: R@1 0.8161 → 0.8355, 61 wins, 30 losses, p 0.002; negatives
  rejected 0.8262 → 0.8451, 12 wins, 1 loss, p 0.003. Both halves of the wines improve:
  half A 33 wins and 18 losses, half B 28 wins and 12 losses.
- Against the rules of 2026-09-23 (run v2): +0.0038 R@1, 27 wins, 21 losses, p 0.47.
  The label-only rules are not significantly better than the rules of 2026-09-23.
  They keep the label-only and the vintage decisions of the owner at the same accuracy.
- The grape answers improved from 67 % to 89 % correct, and `not visible` fell from
  25 % to 9 %. A grape written in the alphabet of the label, and a label crop in
  stage 2, are the two changes that touch these answers. This run does not separate
  their effects.
- c032, the first cause of the losses of the run v2, gives 4 wins and 0 losses
  against the run v2.
- The re-rank moves only the cards of the first 5 positions. A replay with 10 positions
  adds 1 win (R@1 0.8361). In one c013 photo the rule scored the true card best, but
  that card stood at base rank 6.
- With a quiet gx10, a VLM call took 2,574 ms (median), and 84.5 % of the photos met
  the 3,000 ms SLA.

## 2026-09-24 — vintage variants when every card states a year: c129

Status: measured on the rules files and on the runs v2 and base. The open questions
are Q1 and Q2 of `docs/plans/06_label-only-cluster-rules.md`.

- c129 holds `esse-mama-marselan-krasnoe-suhoe-115` («MaMa», 11.5 %) and
  `esse-mama-marselan-krasnoe-suhoe-135` («МаМа», 13.5 %). The cluster exists only by
  the `confusion` signal. The two catalogue labels print the same texts: «MAMA»,
  «MARSELAN/MALBEC», «ESSE UNPLUGGED», and «CRIMEA 2022» or «CRIMEA 2024». The colour
  shade differs: the 2022 label is orange red, the 2024 label is dark red. The alcohol
  value is not on the front label.
- `esse-mama-marselan-krasnoe-suhoe-135/01_conf095.jpg` shows «CRIMEA 2020» (checked
  on an enlarged crop). No card states 2020.
- The query VLM of the run v2 read 2022 on `...-115/01`, 2020 on `...-115/02`, 2020 on
  `...-115/03`, and 2020 on `...-135/01`. The test labels thus put two photos of 2020
  on the 2022 card and one on the 2024 card.
- The base answers the 2022 card for all four positive photos: 3 of 4 right. In the
  run v2 the question of the year gave -1 to both cards for 2020, so the base answer
  stayed.
- The rules of 2026-09-24 hold no valid vintage question for c129, because the names
  state no year. The mode is `verdict` with the rule text «If the label reads CRIMEA
  2022, it is card A; if it reads CRIMEA 2024, it is card B.»
- 16 of the 33 verdict rules decide by a label year alone, over 39 test photos: c049,
  c070, c073, c122, c129, c130, c158, c162, c167, c168, c205, c219, c220, c229, c240,
  and c254. The check of mode `sheet` removes such a year; the text of mode `verdict`
  keeps it.
- `scripts/08_variants.py` joins two cards with the same `producer` and the same
  `name`. «MaMa» and «МаМа» differ by the alphabet, so the two cards are in no variant
  group.

## 2026-09-24 — label-only rules: the probes before the rebuild

Status: measured on the rules file of 2026-09-23 and on three test builds. Plan:
`docs/plans/06_label-only-cluster-rules.md`.

- 45 photos of the run v2 used a question about the glass. The VLM answered
  `not visible` for 29 of them, because the step sends the label crop alone. A replay
  without these questions changes no rank-1 card.
- The new checks, applied to the stored answers of 2026-09-23 without a call: 13
  questions become kind `bottle`, and 93 vintage questions lose every year, because
  the card names do not state them. 22 clusters held such a vintage question as their
  only valid question. 5 vintage questions stay valid, and each takes its years from
  the names: c002, c074, c105, c114, and c186.
- 629 of the 630 cluster cards have a label crop. The median label crop has 31 % of the
  long side of the whole picture, so at one long side the label is about three times
  larger. 291 label crops have a long side below 400 pixels; an enlarged crop holds no
  more detail than its source.
- 43 cards of 21 clusters share one catalogue picture, byte for byte, with another card
  of their cluster. Examples: «БЮРНЬЕ.ПИНО БЛАН» and «БЮРНЬЕ.ВИОНЬЕ»; «Красностоп
  Резерв» and «Гренаш»; «Пухляковский» and «Рислинг». The label crop of such a card
  shows the label of the other card.
- `qwen3.8-max` with label crops wrote the printed Cyrillic grape names in a Latin
  transliteration: «Krasnostop», «Chardonne», «Merlo». With the rule «exactly as the
  label prints it, in its own alphabet» it wrote «КРАСНОСТОП», «ШАРДОНЕ», «МЕРЛО».
- With label crops, the model trusts the picture more than the card name. c001 gave
  «ПИНО БЛАН» the text «ВИОНЬЕ» of the shared picture; the rule of 2026-09-23 had taken
  «Пино Блан» from the name. A caption that names the card with the same picture
  fixed c108 («Красностоп» against «Гренаш», and the mark «Резерв»). c001 kept the two
  cards as indistinguishable.
- The model asked a vintage question about years that only the picture shows (c001),
  and a question about the background colour of the label (c001), against the prompt.
  The code check removes the first. The code does not check the second.
- One stage 2 call for a cluster of 6 to 10 cards took 68 to 118 s with label crops.

The vintage variants, measured before the owner chose where a year comes from:

- By the card names alone, 7 clusters hold cards with a year and cards without one.
  Only 2 of them hold one wine with and without a year: c158 («Аристов Каберне
  Совиньон Розе 2020» and «… Розе») and c161 («Шато Тамань Резерв Мюллер-Тургау
  Лимитед Эдишн 2021» and the same name without a year). The two clusters hold 3
  positive test photos.
- By the names and the label descriptions, 43 clusters are mixed. 309 of the 630
  cluster cards have no label vintage in their description, and 11 have an
  unreadable or implausible one.
- c013: the test labels do not follow the rule of the vintage variants. On the 8
  positive photos of its three Pinot Noir cards, by the years that the query VLM read
  in the run v2, the rule and the test labels give the same card for 2 photos.
- The query VLM wrote the year instead of `other` in 4 of the 5 answers of c013 about
  a year that no card listed: 2020, 2022, 2022, and 2022. The matcher therefore maps
  such a year to `other`.
- QwenCloud answered HTTP 400 «Download multimodal file timed out» for 2 of 182 stage
  2 calls. The client does not repeat a 4xx answer; the next run built both rules.

## 2026-09-24 — label rules: the answers by question type, the misses, and the replay

Status: measured by replay. No new VLM call was made. Sources: the run
`2026-09-23T224548Z-svm-label-gw-cluster-rules-qwen38max-rules-v2`, its base
`2026-09-23T121203Z-svm-label-gw-difference-alpha-patches`, and
`dataset/catalog-cluster-rules.json` of 2026-09-24. Every number below was found after
the run, so every number is post hoc. A change that these numbers suggest MUST be
chosen on one half of the wines and reported on the other half.

### The answers by question type

The set: the positive photos where the step acted in mode `sheet` and the true card is
in the cluster. Each valid question of the rule counts once. The type comes from the
text of the question.

| Type | Answers | Correct | `not visible` | The value of another card | A value that no card expects | The true card expects null |
|---|---:|---:|---:|---:|---:|---:|
| sugar level | 202 | 86 % | 6 % | 3 % | 1 % | 3 % |
| vintage year | 164 | 26 % | 10 % | 24 % | 35 % | 5 % |
| grape | 163 | 67 % | 25 % | 2 % | 1 % | 4 % |
| yes/no mark | 160 | 86 % | 5 % | 9 % | 0 % | 0 % |
| name or line text | 108 | 94 % | 3 % | 3 % | 1 % | 0 % |
| wine colour | 105 | 74 % | 22 % | 1 % | 3 % | 0 % |
| ratio or blend | 29 | 34 % | 55 % | 10 % | 0 % | 0 % |

- The vintage answer differs from the expected year in 59 % of the answers. The valid
  vintage questions hold 146 expected years. Only 17 of these years are in the name or
  the slug of the card. The other years come from the catalogue photo. A catalogue
  photo shows one vintage, and a customer photo can show another vintage. Such a year
  is a property of the photo, not of the card.
- The rules file holds one impossible year: c001 expects 2029 for
  `vinodelnya-byurne-kaberne-fran-krasnoe-suhoe-135`.
- 5 valid questions ask for the colour of the wine through the glass: c006, c046, c089,
  c111, and c116. The step sends the label crop on white. That picture does not show
  the glass.

### The positive misses after the step

270 positive photos have the true card below rank 1 after the step.

| Cause | Photos |
|---|---:|
| The true card is not in the top 10 | 31 |
| The step did not act, because the rank-1 card is in no cluster | 67 |
| The step did not act, for another cause | 3 |
| The step acted, but the true card is not in the cluster or not in the window | 20 |
| The VLM call failed | 1 |
| Mode `verdict` named a wrong card or `unsure` | 37 |
| Mode `sheet` gave a wrong card a higher score | 41 |
| Mode `sheet` got `not visible` for every question | 34 |
| Mode `sheet` gave a tie with the true card, and the base order stayed | 36 |

- In 45 of the 67 photos with no cluster, the true card has the producer of the rank-1
  card. The true card stands at rank 2 in 33 of the 67 photos. The median base gap
  between rank 1 and the true card is 0.017.
- In the 34 photos with `not visible` for every question, a grape question separates
  the true card in at least 15 photos, and a ratio question in 11 photos.

### The replay of the score variants

The replay uses the recorded answers and the candidate lists of the base run. The
served score gives the numbers of the run: R@1 0.8313, 47 wins, 22 losses.

| Variant | R@1 | Wins | Losses | Negative wins | Negative losses |
|---|---:|---:|---:|---:|---:|
| the served score | 0.8313 | 47 | 22 | 11 | 3 |
| no vintage question | 0.8375 | 49 | 14 | 11 | 3 |
| a yes/no question counts «yes» only | 0.8281 | 42 | 22 | 9 | 2 |
| an answer that no card expects gives no evidence | 0.8313 | 45 | 20 | 11 | 3 |
| the three changes above | 0.8356 | 44 | 12 | 9 | 2 |
| the three changes and a margin guard of 0.05 | 0.8356 | 44 | 12 | 9 | 2 |
| mode `verdict` off | 0.8294 | 37 | 15 | 10 | 3 |

- The removal of the vintage question is the only variant that removes losses and
  keeps every win.
- «Yes» only removes 5 wins and no loss. This data does not support that candidate
  change.
- A margin guard of 0.05 changes nothing after the other changes. It also saves few
  VLM calls: 843 of the 906 photos where the step acted have a base gap below 0.05.

### The 8B cross-encoder on the same photos

The run `2026-09-18T195710Z-svm-vlmrerank-8b-siglip2-448-bench` shares 1,332 positive
photos with the run of the step. A shared photo has the same bytes and the same true
card in both runs.

| System | R@1 on the 1,332 photos |
|---|---:|
| `vlmrerank-8b-siglip2-448` | 0.8716 |
| the cluster rule step | 0.8213 |
| the base of the step (`difference`) | 0.8048 |

- The 8B system is right on 122 photos where the step is wrong, and wrong on 55 photos
  where the step is right. Exact McNemar p 5.2e-07.
- Both systems miss 116 photos. An oracle of the two systems reaches R@1 0.9129.
- On 518 shared negative photos, the forbidden slug stands at rank 1 87 times for the
  8B system and 74 times for the step.
- A simulation puts the 8B scores inside the window of the step only, on 1,850 shared
  photos. It reaches R@1 0.8266 against 0.8213 for the step. Against the base, it has
  70 wins and 41 losses, and the step has 43 wins and 21 losses. The lead of the 8B
  system therefore does not come from the order inside the window.
- The two runs are five days apart. The index, the patches, the labels, and the base
  differ. The comparison is a comparison of two systems, not of two re-rank steps.

## 2026-09-24 — the R@1 failures of the pipeline `svm-vlmrerank-8b-siglip2-448`

Source: the run `2026-09-18T195710Z-svm-vlmrerank-8b-siglip2-448-bench`. The run holds
1,881 queries: 1,356 positive photos and 525 negative photos. R@1 is 86.4 %.

- 184 positive photos have their true slug not at rank 1. They fall on 112 wines.
- The rank of the true slug of these photos: rank 2 for 137 photos, rank 3 for 17,
  rank 4 for 2, rank 6 for 1, rank 7 for 3, and absent from the top 10 for 24. 74 % of
  the failures therefore stand at rank 2.
- 90 negative photos got their forbidden slug at rank 1. The owner chose to keep them
  out of the failure set.
- Every file of the 184 photos still has the SHA-256 that the run recorded.
- The query set of `default` grew after the run. On 2026-09-24 it holds 2,181 photos:
  1,600 positive and 581 negative.

The labels changed after the run. The state of 2026-09-24, for the photos of the run:

| Label in the run | Label on 2026-09-24 | Rank 1 of the run | Photos |
|---|---|---|---|
| `positive` | `negative` | another slug | 4 |
| `positive` | `negative` | its own slug | 3 |
| `negative` | `positive` | its own slug | 1 |
| `negative` | `positive` | another slug; its own slug at rank 4 | 1 |
| `negative` | `variant` | another slug | 2 |
| `negative` | `unusable` | its own slug | 1 |
| `negative` | the file is gone | its own slug | 1 |
| `negative` | the file is gone | another slug | 1 |

9 of the 184 photos lie on slugs that were excluded after the run.

`--from-run` does not give the same set. `failed_before()` reads the label that the
earlier run recorded, not the label of today. On the labels of 2026-09-24,
`--from-run <run> --only positive` selects 172 photos. These are the 171 photos of
`vlmrerank-8b-failed` and `agrolayn-mountain-eagle-traminer-traminer-beloe-suhoe-12/01_agent.jpg`.
That photo was `negative` in the run, and the run answered its own slug at rank 1. The
photo carries `positive` now, so that answer was correct. `failed_before()` repeats it
because the run counted it as a false match.

Neither selection holds
`abrau-dyurso-udelnoe-vedomstvo-imperatorskoe-beloe-bryut/04_conf095.jpg`. That photo was
`negative` in the run, and the run answered another slug at rank 1. The photo carries
`positive` now, so the run missed it at rank 1 by the label of today. The rule of the
failure set reads the label of the run, and this photo was not `positive` there.

Decision: the failure set is a frozen copy in a dataset of its own. The owner chose it
on 2026-09-24.

| Option | For | Against |
|---|---|---|
| A frozen copy in `dataset/vlmrerank-8b-failed/` (chosen) | The set does not change when `default` changes. The review tool can open it with no risk to `default`. The pattern is the pattern of `official-real-photos`. | A label fix in `default` does not reach the copy. 45 MB of copies. |
| A dataset that shares `photo_dir` with `default` and holds its own label file | No copies. | The review tool of that dataset shows every other photo of `default` as unlabelled. A move or a delete there changes `default`. |
| `--from-run` with no new dataset | No new files. The page `/runs` shows the earlier answer of each photo. | It is not a separate test set. Each run takes the set from the live labels, and it reads the label of the earlier run (see above). |

Consequences: a reviewer who fixes a label of one of these photos MUST fix it in both
datasets, or build the set again. The runs of the set stand in its own `runs_dir`, so
the review tool on port 8154 does not show them. Port 8167 is assigned to the review
tool of the set.

## 2026-09-23 — the public wine sitemap is the slug authority

The public `sitemap.xml` is an index. It names `wines-sitemap.xml`. The wine sitemap
holds one `/wines/<slug>` URL per public wine. The Dataset validator uses this file
instead of finding links in rendered pages.

The check on 2026-09-23 found 2,103 catalogue slugs and 2,105 website slugs. The sets
have 2,032 slugs in common. The catalogue has 71 slugs that are not on the website.
The website has 73 slugs that are not in the catalogue. These numbers describe the
live website at that time. They are not fixed test values.

The source URL uses the image resize service. A probe of `Сира Нуво` returned the same
upload file name as the catalogue and as `og:image` on the wine page. The downloaded
bytes did not have the SHA-256 of the local upload file. The resize service re-encoded
the WebP. The SHA-256 check must therefore report an exact byte result. It must not
state that a byte mismatch proves different visible content.

The wine page puts its source image in `og:image`. The dimensions in that URL can
differ from the catalogue source URL. The upload file name stays the stable part for
the page association check.

## 2026-09-23 — the Dataset page must keep the original image separate from the patch

The normal image route cannot serve the comparison page. `GET /img/bottle` applies
the display order: crop, patch, then catalogue image. This order hides the original
image when a patch exists.

The page `/dataset` uses two explicit read-only routes. `GET /img/catalog` serves
`local_path` of the source record. `GET /img/patch` serves the file from `patch_dir`.
The two routes let a reviewer compare the source and the correction in one row.

The configured catalogue has 2,103 records and 15 patches on 2026-09-23. The page
renders one page of records at a time. This limit keeps the document and its image
requests small. Search still reads every field of every record in the browser.

## 2026-09-24 — label rules: the full benchmark

Status: measured. Run
`runs/2026-09-23T224548Z-svm-label-gw-cluster-rules-qwen38max-rules-v2`; report
`cluster-rules-report.md` of the run. Plan: `docs/plans/05_cluster-label-rules.md`.

| Metric | Base | Re-rank |
|---|---:|---:|
| R@1 of 1,600 positives | 0.8156 | 0.8313 |
| MRR | 0.8833 | 0.8929 |
| R@5 | 0.9656 | 0.9656 |
| Negatives rejected (581) | 0.8262 | 0.8399 |

- Positives: 47 wins, 22 losses, exact McNemar p 0.004. Negatives: 11 wins, 3 losses,
  p 0.057.
- The step acted on 906 of 2,181 photos and changed the order of 110. Mode `sheet`: 811
  photos, 47 wins and 18 losses over both labels; mode `verdict`: 95 photos, 11 wins and
  7 losses. One VLM call failed.
- Without the clusters that only the `confusion` signal joins (replay): R@1 0.8244,
  27 wins, 13 losses, p 0.038. This is the number that the test photos did not shape.
- The post hoc score («an answer that no card expects gives no evidence»): 45 wins and
  20 losses, p 0.003; without the `confusion` clusters 25 and 11, p 0.029. It does not
  change the result.
- «Фантом»: 4 of 17 positive photos right in the base, 10 with the rule of the note.
- The base score gap of a change: below 0.02 below rank 1, 44 wins and 13 losses; at
  0.05 or more, 1 win and 5 losses.
- Latency: median 3,757 ms where the step acted, 283 ms elsewhere; 77.6 % of the photos
  within the 3,000 ms SLA (97.9 % for the base). The gx10 GPU stood at 95 % from other
  jobs, so a VLM call took 5.4 s (median) instead of about 2.4 s on a quieter host.

The two main causes of the losses:

1. A vintage that only the catalogue photo shows. c032 holds «Аристов. Кюве Александр.
   Блан Де Блан» (18 months, the photo shows 2022) and «... Blanc de Blancs 36» (36
   months, 2021). Four positive photos of the first card show 2021, so the rule moved
   them to the second card. The months of ageing separate the two cards, and the VLM
   answered `not visible` for them. A year that the card data does not state is not a
   stable feature of a card: the next bottle can carry the next vintage.
2. A «no» for a mark that the VLM does not see. c246: the positive photo of «Совиньон
   Блан. Авторская технология» got «no» for «АВТОРСКАЯ ТЕХНОЛОГИЯ».

Candidate changes, each chosen after this run and therefore post hoc, to be measured
on one half of the wines and reported on the other half:

- use a vintage year only when the name or the slug of the card states it;
- in a yes/no question, count only «yes» as evidence;
- a margin guard near 0.05, as `group.max_gap` of the kind `difference`.

## 2026-09-24 — label rules: the first full run was stopped

Status: measured on the first 510 photos, then stopped.

Run `runs/2026-09-23T221137Z-svm-label-gw-cluster-rules-qwen38max-rules` held the 156
rules of `qwen3.8-max`. It was stopped after about 600 photos, and it holds no metrics.

- On the first 510 paired photos: positives 8 wins, 6 losses; negatives 3 wins, 0
  losses. The step acted on 253 photos and changed the order of 24.
- 9 of 15 verdict calls failed with «the answer is not a JSON object». The local model
  wrote a text analysis, such as «Based on the provided image and the rule, here is the
  analysis», cut at `max_tokens` 256, in about 21 s. `response_format: json_object` is
  not enforced by the gateway. A `json_schema` with the letters and `unsure` is
  enforced: the same prompt answered `{"wine": "B"}` in 1.0 s. The matcher now sends
  that schema in mode `verdict`, and the run was repeated.
- The gx10 GPU stood at 95 % with a load average of 23 from other jobs during the run.
  A sheet call took 6.1 s (median) instead of 2.4 s in the partial run. The latency of
  these runs is therefore not the latency of a quiet host.

## 2026-09-24 — label rules: stage 2 on `qwen3.8-max`

Status: measured on 3 clusters and 2 labels.

`qwen3.8-max` of the QwenCloud Token Plan takes pictures (`image_tokens` in `usage`).

| Probe | Result |
|---|---|
| Abrau-Durso Pinot Noir 2024, native 312 x 1000, thinking off | 7.3 s; «урож. 2014 года» — wrong |
| The same at a long side of 2048, thinking off | 8.0 s; 2021 — wrong |
| The same at 2048, thinking on | 94.2 s, 4,699 tokens; «УРОЖАЙ 2021 ГОДА» — wrong |
| `qwen3.5-9b` at 2048, thinking off (for comparison) | 2024 — right |
| «Фантом 30/70» at 2048, thinking off | 9.7 s; the ratio box was not read |
| Thinking without streaming, and `response_format: json_object` without thinking | both work |

So the cloud model reads small print no better than the local model, and stage 1
stays local. Stage 2 is a reasoning task over the descriptions, the card data and the
note, and there the cloud model is better. The three rules, rebuilt with the new
prompt of «major differences» (39 s, 40 s, and 68 s with 4 requests at a time):

| Cluster | `qwen3.5-9b` | `qwen3.8-max` |
|---|---|---|
| «Фантом» | the ratio, the alcohol value (dropped by the code), the colour of the box | the blend ratio alone |
| Abrau-Durso Pinot Noir | the vintage, «Бут. №» (dropped by the code), «ГРК» | the grape, which separates «Каберне Совиньон» from «Пино Нуар», and the vintage |
| Fanagoria Primum Alveus | a Roman numeral, the vintage, the name line, the capsule colour | the vintage and the sugar level |

The vintage question of Abrau-Durso still gives null to the card with no year, so the
served score keeps the fault of the partial run for years that no card holds. The
post hoc score of `scripts/cluster_rules_report.py` measures that fault.

After 41 rules, a check found that no kosher question was used. The model gave the
mark to the kosher cards and null to the others, as rule 3 of the prompt said, and the
code keeps a question only when two cards hold two different non-null answers. Rule
3a now asks for a yes/no question with "yes" or "no" for each card. c006 then held
«Does the label show a kosher mark (the line 'КОШЕРНАЯ КОЛЛЕКЦИЯ')?» with two yes and
four no, beside the sugar level and the colour of the wine.

## 2026-09-23 — label rules: the partial benchmark with 3 rules

Status: measured. Run `runs/2026-09-23T193559Z-svm-label-gw-cluster-rules-partial-3-rules`,
2,181 photos, against the base run `2026-09-23T121203Z-svm-label-gw-difference-alpha-patches`.
Only 3 clusters held a rule: «Фантом» (c054), Abrau-Durso Pinot Noir (c013), and
Fanagoria Primum Alveus. The report is `cluster-rules-report.md` in the run directory.

| Metric | Base | Re-rank |
|---|---:|---:|
| R@1 of 1,600 positives | 0.8156 | 0.8175 |
| MRR | 0.8833 | 0.8849 |
| Negatives rejected | 0.8262 | 0.8279 |

- The step acted on 35 photos. Positives: 6 wins, 3 losses, exact McNemar p 0.508. No
  VLM call failed.
- «Фантом»: 4 of 17 positive photos right in the base, 9 with the rule of the note.
- c013: 0 wins, 2 losses. Two causes:
  1. The vintage question expects no year for `abrau-dyurso-abrau-dyurso-pino-nuar-krasnoe-suhoe-13`,
     2023, 2023, and 2024. The test photos show 2019, 2020, and 2022, which no card
     holds. With the score «a different answer gives -1», an unseen year counts against
     every card with a year, so the card with no year wins. The test labels put such a
     bottle on the 2023 card.
  2. The question «Does the label contain the text 'ГРК'?» comes from a description
     and gets random answers.
- Latency: median 2,977 ms where the step acted, 244 ms elsewhere. The VLM call alone:
  median 2,390 ms.

A candidate change of the score, found by looking at these losses and therefore
post hoc: an answer that equals the expected answer of no card gives no evidence. The
full run records every answer, so the report can replay this score without a new call.

## 2026-09-23 — label rules for the catalogue clusters: the probes

Status: measured on a few cards and photos. The benchmark follows in the next entry.
Plan: `docs/plans/05_cluster-label-rules.md`.

The VLM is `qwen3.5-9b` on the llama-swap gateway of gx10: llama.cpp, Q4_K_M weights,
1 slot, a context of 32,768 tokens, about 37 tokens/s. It is pinned and resident, and
the enrichment worker of `drink-atlas-enrichment` uses the same slot.

| Probe | Result |
|---|---|
| One label description, thinking on | 28.3 s, 966 completion tokens, of which about 2,900 characters of reasoning |
| The same with `chat_template_kwargs.enable_thinking: false` | 3.0 s, 100 completion tokens |
| A WebP data URL | HTTP 400. A PNG data URL works. |
| `response_format: {"type": "json_object"}`, two pictures in one message | valid JSON, 2.8 s |
| The full stage 1 prompt at the native size of the photo | 7 to 10 s for one card |
| The full stage 1 prompt at a long side of 2048 pixels | 11 to 24 s for one card; about 19 s on average in the batch |
| One question of the sheet about a query crop | 1.0 to 2.2 s |

Small print. The catalogue photo of «Фантом 30/70» has 264 x 1000 pixels, and its
ratio box is about 15 pixels wide. No probe read the ratio from a catalogue photo:
the model read `100`, then `25` and `100`, in the box. At 312 x 1000 pixels the model
read «урож. 2024» of `abrau-dyurso-pino-nuar-krasnoe-suhoe-125` as `2021`, and «ФАНТОМ»
of `...-7030-...` as `PHANTOM`. At a long side of 2048 pixels it read both right. Stage 1
therefore scales every picture to a long side of 2048, UP or down.

The first rules. Three clusters were built three times while the prompt changed:

- «Фантом» (3 cards). With the note of the reviewer, the question about the bottom
  left corner holds 30/70, 50/50 and 70/30. Without the rule «the descriptions can
  hold errors», the model made a second question from the false `PHANTOM`. That
  question would cancel the right one at query time. The model also asked for the
  alcohol value, which differs by 0.1 to 0.3 points; the code now drops such a
  question when another question separates the cards.
- Abrau-Durso Pinot Noir (4 cards). The vintage question is right: none, 2023, 2023,
  2024. The model also asked for «Бут. №», a bottle number that changes from bottle to
  bottle; the code now drops such a question. The model did NOT use «ПИНО НУАР»
  against «КАБЕРНЕ СОВИНЬОН», and it named the two cards indistinguishable. The OCR
  words of the base pipeline separate these two cards already, and a tie keeps the base
  order, so this miss costs no new error.
- Fanagoria Primum Alveus (9 cards). Four questions: a Roman numeral, the vintage, the
  name line, the colour of the capsule. The vintages come from the card names.

A smoke test through the served pipeline on four «Фантом» photos: two photos of 30/70
moved from rank 3 and rank 2 to rank 1; one photo of 70/30 stayed at rank 1; one photo
of 50/50 stayed wrong, because the model answered `other` for the ratio and `Purple`
for the colour of the box.

The ceiling and the leakage, measured on the run
`2026-09-23T121203Z-svm-label-gw-difference-alpha-patches` (R@1 0.8156):

- 179 of the 295 misses hold the true card in the cluster of the answer.
- 48 links of the cluster file hold the `confusion` signal alone. 60 of the 179 misses
  need such a link, so 119 remain without the `confusion` signal.
- With a window of 5, the step acts on 906 of 2,181 queries; with a window of 2, on
  766. Of the 636 positive queries in the window of 5, 436 are right already.

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
  temporary file in 10 s. The 2026-09-23 entry of `drink-atlas-core/ResearchLog.md` has the details.
  The fix of the query was applied in the Core code on the same day. Core serves it since its
  restart at 09:27.
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
