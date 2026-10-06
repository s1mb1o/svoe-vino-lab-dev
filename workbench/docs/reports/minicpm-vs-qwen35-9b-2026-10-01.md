# minicpm-v-4.5 and minicpm-v-4.6 compared with qwen3.5-9b-nvfp4

Date: 2026-10-01.
Source: owner message of 2026-10-01T00:11:00+0300 (`minicpm-v-4.6`); owner answers of
00:16:00 ("Replay + lab run", baseline `qwen3.5-9b-nvfp4`); owner message of
2026-10-01T10:34:00+0300 (add `minicpm-v-4.5`).
Artifacts: `docs/reports/minicpm-vs-qwen35-9b-2026-10-01/` (not in git).

## Result

Keep `qwen3.5-9b-nvfp4` for all four VLM tasks of the workbench.

- `minicpm-v-4.6` (1.3 B) is not usable for any of the four tasks. It is the fastest model,
  but most answers fail the checks of the pipeline, and it reads Cyrillic text badly.
- `minicpm-v-4.5` (8.7 B) is usable. Its answers are valid, its class values agree with
  qwen, its Cyrillic text is clean, and its re-rank result equals the qwen result
  (R@1 82.55% against 82.60%). But each call is about 2 to 3 times slower than qwen, and
  about 1 call in 10 of the label stages reaches the timeout of 300 s.
- So `minicpm-v-4.5` gives no gain over qwen. It is a possible fallback when the vLLM
  service of qwen is not available.

| Task | qwen3.5-9b-nvfp4 | minicpm-v-4.6 | minicpm-v-4.5 |
|---|---|---|---|
| Stage 1 class JSON: valid | 100/100 | 0/100 | 100/100 |
| Stage 2 detail JSON: valid | 99/100 | 85/100 | 85/100 |
| Stage 3 label JSON: valid | 99/100 | 16/100 | 88/100 |
| Stage 2: catalogue name words found (paired with qwen) | 68% / 71% | 40% | 64% |
| Stage 2: words that mix alphabets | 0 | 64 | 1 |
| Re-rank R@1 on `my` (base 81.00%) | 82.60% | 81.00% | 82.55% |
| p50 ms: stage 1 / 2 / 3 / re-rank VLM | 3311 / 16420 / 21180 / 5804 | 1930 / 4563 / 3528 / 2323 | 5938 / 48598 / 54797 / 11696 |

The qwen name recall is 68% against the minicpm-v-4.6 set and 71% against the
minicpm-v-4.5 set (each model is paired with qwen on the images valid in both).

## The compared tasks

| Task | Code | Request |
|---|---|---|
| Stage 1: class JSON | `describe_images.describe` | `PROMPT`, image 1024 px, `json_object` |
| Stage 2: detail JSON | `describe_images.describe_detail` | `PACKAGE_PROMPT` or `LABEL_PROMPT`, cut 1536 px, strict `json_schema`, `max_tokens` 8192 |
| Stage 3: label JSON | `describe_images.describe_label` | `label_rules.DESCRIBE_PROMPT`, 2048 px, `json_object`, `max_tokens` 1500 |
| Cluster re-rank | `cluster_rerank.ClusterRerank` | `SCORE_PROMPT`, label cut 1536 px, `json_schema`, `max_tokens` 256 |

All prompts are in English. The language skill of a model applies to the label text that
the model must copy.

## Method

- Gateway `http://192.168.86.14:18081/v1`. `qwen3.5-9b-nvfp4`: vLLM, pinned.
  `minicpm-v-4.6`: MiniCPM-V 4.6, 1.3 B, llama.cpp, Q8_0. `minicpm-v-4.5`: MiniCPM-V 4.5,
  8.7 B (Qwen3-8B), llama.cpp, Q8_0, 4 slots.
- Descriptions: `replay.py` sends the requests of the pipeline code itself for 100
  catalogue images (random, seed 20261001; `minicpm-v-4.5` got the same 100 images with
  `--shas-from`). Each image has a stored answer in `image_description`, `image_detail`,
  and `image_label_description`. Each model got fresh calls. `model_cache` was off, so no
  call read or wrote the shared cache. 4 parallel requests for each model. The models
  ran one after the other: qwen and minicpm-v-4.6 on 2026-10-01 00:18 to 00:55,
  minicpm-v-4.5 on 2026-10-01 about 10:47 to 12:02.
- Re-rank: lab runs of `run_job.py` on the test set `my` from a scratch copy of
  `config.yaml`: `barcode-siglip2-p512-rot5-seg` (base, no re-rank),
  `barcode-rerank-siglip2-p512-rot5-seg` (qwen), and two twins of it with
  `rerank.vlm: minicpm-v-4.6` and `rerank.vlm: minicpm-v-4.5`. `config-scratch.diff`
  shows the changes of the copy.
- The shared `config.yaml`, the catalogue database, and `workbench/runs/` did not change.

## Stage 1: class JSON

| Model | Valid answers | All 5 fields = stored qwen | All 5 fields = fresh qwen | p50 / p90 ms |
|---|---|---|---|---|
| qwen, pipeline request | 100/100 | 89/100 | — | 3311 / 3808 |
| minicpm-v-4.6, pipeline request | 0/100 | — | — | 1930 / 2571 |
| minicpm-v-4.5, pipeline request | 100/100 | 92/100 | 91/100 | 5938 / 7313 |
| minicpm-v-4.6, strict `json_schema` (not the pipeline request) | 88/100 | 5/88 | 5/88 | 1750 / 1892 |
| minicpm-v-4.5, strict `json_schema` (not the pipeline request) | 100/100 | 93/100 | 92/100 | 4880 / 6060 |

The values of the valid answers:

| Field | qwen (100) | minicpm-v-4.6 strict (88) | minicpm-v-4.5 (100) |
|---|---|---|---|
| `subject_scope` | full_package 96, label_closeup 4 | label_closeup 47, full_package 41 | full_package 96, label_closeup 4 |
| `package_view` | front 91, back 9 | front 88 | front 91, back 9 |
| `content_roles` | front 83, back 9, both 8 | both 88 | front 86, back 9, both 5 |

- With the pipeline request, minicpm-v-4.6 writes values that are not in the enums, for
  example `"subject_scope": "the label of a wine bottle"`. 4 answers are not JSON.
- minicpm-v-4.5 agrees with qwen as much as two qwen runs agree with each other (fresh qwen
  against stored qwen: 89/100).
- The database has no manual stage 1 value (2466 rows, all `vlm`). So the table shows
  agreement, not accuracy. Two images where qwen and minicpm-v-4.6 disagree were checked by
  eye (`check_0.jpg`, `check_1.jpg`). Both show a full bottle; the first one is a back
  view. qwen was correct for both.
- vLLM refuses the strict schema of stage 1 (`Grammar error: Unimplemented keys:
  ["uniqueItems"]`). llama.cpp accepts it but does not enforce it: 12 minicpm-v-4.6 answers
  hold `["front_label", "front_label"]`.

## Stage 2: detail JSON (strict `json_schema`)

All 100 images:

| Measure | qwen | minicpm-v-4.6 | minicpm-v-4.5 |
|---|---|---|---|
| Valid answers | 99/100 | 85/100 | 85/100 |
| Failures | 1 timeout at 300 s | 15 loops to `max_tokens` 8192 (about 92 s each) | 11 timeouts at 300 s, 4 HTTP 502 |
| p50 / p90 ms | 16420 / 33261 | 4563 / 92783 | 48598 / 300226 |
| Words that mix alphabets | 0 | 64 | 1 |

Each minicpm model paired with qwen on the images valid in both:

| Model | n | Name words found (model / qwen) | Producer words found (model / qwen) | p50 ms (model / qwen) |
|---|---|---|---|---|
| minicpm-v-4.6 | 85 | 40% / 68% | 38% / 56% | 4147 / 15720 |
| minicpm-v-4.5 | 85 | 64% / 71% | 55% / 58% | 44127 / 15818 |

Examples of `texts` (selected items):

| Catalogue | qwen | minicpm-v-4.6 | minicpm-v-4.5 |
|---|---|---|---|
| Кокур, Два Сердца | ДВА СЕРДЦА, КОКУР, КРЫМ | ДВА СЕРДЦА, КOKVP, КРМ | ДВА СЕРДЦА, КОКУР, КРЫМ |
| Декантер. Каберне Фран 2019, Фанагория | ВЫДЕРЖАНО В БУТЫЛКАХ | ВИДЕРЖАНО В ВУТЯЛКАХ | ВЫДЕРЖАНО В БУТЫЛКАХ |
| Блан де Блан, Скалистый берег | СКАЛИСТЫЙ БЕРЕГ, экстра брют | СКАЛИСТЫЙ БЕРГЕТ, экстра бrious | СКАЛАИСТЫЙ БЕРЕГ, экстра брют |
| Di Caspico розовое брют, Дербент Вино | БРЮТ РОЗОВОЕ | БРИТ РОЗОВOE | БРИОТ РОЗОВОЕ |
| Rose Cuvee Prestige, ESSE | ВИНО ИГРИСТОЕ, ПИНО НУАР, ШАРДОНЕ | ВИНО НИРПИСТОЕ, РОЗОВОЕ БРИТ | ВИНО ИГРИСТОЕ, ПИНО НУАР, ПАРДОНО |
| Совиньон Блан Резерва, Uppa Winery | PAVEL SHVETS, SAUVIGNON BLANC RESERVA | PAVEL SHVETS, SAUVIGNON BLANC RESERVA | PAVEL SHVETS, SAUVIGNON BLANC RESERVA |

minicpm-v-4.5 keeps the Russian alphabet. Its errors are wrong letters inside a word
(`СКАЛАИСТЫЙ`, `БРИОТ`, `ПАРДОНО`), not mixed alphabets.

## Stage 3: label JSON (`json_object`)

| Measure | qwen | minicpm-v-4.6 | minicpm-v-4.5 |
|---|---|---|---|
| Valid answers | 99/100 | 16/100 | 88/100 |
| Failures | 1 with no key `bottle` | 47 not JSON, 27 a list for `bottle`, 10 no key `marks` | 9 timeouts at 300 s, 1 not JSON, 1 cut off, 1 no key |
| p50 / p90 ms | 21180 / 46293 | 3528 / 5545 | 54797 / 180771 |
| Loop guard (second call) | 5 | 0 | 0 |
| Name words found, paired with qwen (model / qwen) | — | 31% / 74% (n = 16) | 63% / 71% (n = 87) |

- The valid minicpm-v-4.5 answers hold 407 completion tokens at the median (maximum 1359).
  So its timeouts come from a slow call (image prefill and decode with 4 parallel
  requests), not from a loop.
- With `json_object`, the answers of minicpm-v-4.6 are not limited to valid JSON. The cause
  (gateway, llama.cpp version, or chat template) was not examined.
- The 4 HTTP 502 answers of minicpm-v-4.5 in stage 2 came one after the other. The gateway
  log did not show the cause.

## Cluster re-rank (lab runs, test set `my`)

The main table: four runs on 2026-10-01 with the same index (built 10:46:34), the same
rules (11:05:16), and the same clusters (11:40:48). The test set grew during the runs
(2484 to 2493 queries). The table holds the 2484 queries that are in all four runs
(1874 positive). The runs are matched by the photo hash, the slug, and the label.

| Measure | base (no re-rank) | qwen | minicpm-v-4.6 | minicpm-v-4.5 |
|---|---|---|---|---|
| R@1, positive | 81.00% (1518/1874) | 82.60% (1548/1874) | 81.00% (1518/1874) | 82.55% (1547/1874) |
| R@5, positive | 97.12% | 97.12% | 97.12% | 97.12% |
| Re-rank triggered | — | 631 | 631 | 631 |
| Rank 1 changed by the re-rank | — | 76 | 7 | 94 |
| Fixes / breaks against base | — | 42 / 12 | 2 / 2 | 41 / 12 |
| VLM answer refused (base order kept) | — | 18 | 550 | 47 |
| Same rank-1 answer as qwen (of 631) | — | — | 557 | 563 |
| VLM ms p50 / p90 | — | 5804 / 10620 | 2323 / 3206 | 11696 / 25370 |

- Each refused answer of the three models has the error `the option scores of q1 total N;
  expected 100`. The JSON Schema fixes the keys but not the sum.
- On 2026-10-01, 626 of the 631 qwen answers and 626 of the minicpm-v-4.6 answers came
  from `model_cache` (the same requests as on 2026-09-30). A cached answer keeps the time
  of its first call, so the VLM times stay valid. The wall times of these runs are not
  comparable and are not shown. The minicpm-v-4.5 answers were fresh, except 95.
- The runs of 2026-09-30 (other index, 2479 queries) gave the same order: base 81.26%,
  qwen 83.13% (46 fixes, 11 breaks), minicpm-v-4.6 81.10% (1 fix, 4 breaks). The tables
  are in `lab-tables-2026-09-30.md` and `lab-tables-2026-10-01.md`.

## Limits

- 100 images for the descriptions. The name and producer word recall is a proxy: a
  catalogue name in Cyrillic and a label in Latin gives a miss for each model.
- Stage 1 has no manual reference. The distributions and two checks by eye support qwen.
- The latencies come from 4 parallel requests on the shared gx10 GPU. Other sessions used
  the gateway at the same time. The minicpm-v-4.5 replay ran about 10 hours after the
  other two.
- The pipeline sends `temperature` 0. The model card of minicpm-v-4.5 recommends 0.6 with
  `top_k` 20 and `top_p` 0.95. The comparison did not test these values.
- Only one re-rank pipeline was compared.

## How to repeat

The scripts read `config.yaml` next to them (the scratch copy).

```sh
cd docs/reports/minicpm-vs-qwen35-9b-2026-10-01
python3 replay.py --vlm minicpm-v-4.5 --out new-45.jsonl --shas-from replay-qwen.jsonl \
  --n 100 --workers 4 --stages 1,2,3,4
python3 analyze_replay.py qwen=replay-qwen.jsonl minicpm-4.6=replay-minicpm.jsonl \
  minicpm-4.5=new-45.jsonl
# A lab run, from the workbench root:
python3 pipeline/run_job.py --config docs/reports/minicpm-vs-qwen35-9b-2026-10-01/config.yaml \
  --name barcode-rerank-minicpm45-siglip2-p512-rot5-seg --set my \
  --jobs-dir <scratch>/jobs --runs-dir <scratch>/runs
python3 docs/reports/minicpm-vs-qwen35-9b-2026-10-01/analyze_lab.py base=<run> qwen=<run> \
  minicpm-4.6=<run> minicpm-4.5=<run>
```

`replay.py --stages 4` sends stage 1 with the strict schema. The scratch config sets
`rebuild_embeddings_on_run: false` and `image_description.watch: false`. Compare lab runs
only when their `run.json` names the same `embeddings.built_at`, `rules_updated_at`, and
`clusters_built_at`.
