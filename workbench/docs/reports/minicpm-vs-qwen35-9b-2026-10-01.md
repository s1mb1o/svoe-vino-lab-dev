# minicpm-v-4.6 compared with qwen3.5-9b-nvfp4

Date: 2026-10-01.
Source: owner message of 2026-10-01T00:11:00+0300; owner answers of 00:16:00
("Replay + lab run", baseline `qwen3.5-9b-nvfp4`).
Artifacts: `docs/reports/minicpm-vs-qwen35-9b-2026-10-01/` (not in git).

## Result

Keep `qwen3.5-9b-nvfp4` for all four VLM tasks of the workbench.
`minicpm-v-4.6` is not a drop-in replacement for any of them.

- minicpm is faster for each call: p50 1.7 times (stage 1), 2.5 times (re-rank),
  3.8 times (stage 2), and 6 times (stage 3).
- minicpm gives an invalid answer for most pipeline requests that do not send a strict
  JSON Schema. The pipeline then records a failure, or the re-rank keeps the base order.
- minicpm reads Latin label text well. It reads Cyrillic label text badly: it mixes Latin
  and Ukrainian letters into Russian words and changes words.
- With a strict JSON Schema, minicpm gives valid class answers, but the values are nearly
  constant: `front`, `["front_label", "back_label"]` for each image.
- In the cluster re-rank, minicpm lowers R@1 by 0.16 points. qwen raises it by 1.87 points.

## The compared tasks

| Task | Code | Request |
|---|---|---|
| Stage 1: class JSON | `describe_images.describe` | `PROMPT`, image 1024 px, `json_object` |
| Stage 2: detail JSON | `describe_images.describe_detail` | `PACKAGE_PROMPT` or `LABEL_PROMPT`, cut 1536 px, strict `json_schema`, `max_tokens` 8192 |
| Stage 3: label JSON | `describe_images.describe_label` | `label_rules.DESCRIBE_PROMPT`, 2048 px, `json_object`, `max_tokens` 1500 |
| Cluster re-rank | `cluster_rerank.ClusterRerank` | `SCORE_PROMPT`, label cut 1536 px, `json_schema`, `max_tokens` 256 |

All prompts are in English. So the weak Russian of minicpm in its answers does not apply to
the prompts. It applies to the label text that the model must copy.

## Method

- Gateway `http://192.168.86.14:18081/v1`. `minicpm-v-4.6`: MiniCPM-V 4.6, 1.3 B,
  llama.cpp, Q8_0. `qwen3.5-9b-nvfp4`: vLLM, pinned.
- Descriptions: `replay.py` sends the requests of the pipeline code itself for 100
  catalogue images (random, seed 20261001). Each image has a stored answer in
  `image_description`, `image_detail`, and `image_label_description`. Both models got
  fresh calls. `model_cache` was off, so no call read or wrote the shared cache.
  4 parallel requests for each model. The models ran one after the other.
- Re-rank: three lab runs of `run_job.py` on the test set `my` (2479 queries: 1873
  positive, 606 negative) from a scratch copy of `config.yaml`:
  `barcode-siglip2-p512-rot5-seg` (base, no re-rank),
  `barcode-rerank-siglip2-p512-rot5-seg` (qwen), and a twin of it with
  `rerank.vlm: minicpm-v-4.6`. `config-scratch.diff` shows the changes of the copy.
- The shared `config.yaml`, the catalogue database, and `workbench/runs/` did not change.

## Stage 1: class JSON

| Model | Valid answers | All 5 fields equal to the stored qwen answer | p50 ms | p90 ms |
|---|---|---|---|---|
| qwen, pipeline request | 100/100 | 89/100 | 3311 | 3808 |
| minicpm, pipeline request | 0/100 | — | 1930 | 2571 |
| minicpm, strict `json_schema` (not the pipeline request) | 88/100 | 5/88 | 1750 | 1892 |

- With the pipeline request, minicpm writes values that are not in the enums, for example
  `"subject_scope": "the label of a wine bottle"` or `"content_roles": ["brand", "logo"]`.
  4 answers are not JSON.
- With the strict schema, the values of minicpm are nearly constant:

| Field | qwen (fresh, 100 images) | minicpm strict (88 valid) |
|---|---|---|
| `subject_scope` | full_package 96, label_closeup 4 | label_closeup 47, full_package 41 |
| `package_view` | front 91, back 9 | front 88 |
| `content_roles` | front 83, back 9, both 8 | both 88 |

- The database has no manual stage 1 value (2466 rows, all `vlm`). So the table shows
  agreement, not accuracy. Two images where the models disagree were checked by eye
  (`check_0.jpg`, `check_1.jpg`). Both show a full bottle. The first one is a back view.
  qwen was correct for both. minicpm said `label_closeup` for both and `front` for the back view.
- vLLM refuses the strict schema of stage 1 (`Grammar error: Unimplemented keys:
  ["uniqueItems"]`). qwen does not need it: its pipeline request is valid for 100 of 100.

## Stage 2: detail JSON (strict `json_schema`)

Images with a valid answer from both models (n = 85):

| Measure | qwen | minicpm |
|---|---|---|
| p50 / p90 ms | 15720 / 28477 | 4147 / 6957 |
| Catalogue name words found in the texts | 68% | 40% |
| Catalogue producer words found in the texts | 56% | 38% |
| Slug alcohol found | 9/61 | 8/61 |
| Year of the name = `vintage` | 8/8 | 8/8 |

All 100 images:

| Measure | qwen | minicpm |
|---|---|---|
| Valid answers | 99/100 | 85/100 |
| p50 / p90 ms | 16420 / 33261 | 4563 / 92783 |
| Failure | 1 timeout at 300 s | 15 loops to `max_tokens` 8192, about 92 s each |

Examples of `texts` (the first items):

| Catalogue | qwen | minicpm |
|---|---|---|
| Кокур, Два Сердца | ДВА СЕРДЦА, КОКУР, Сладкое вино, КРЫМ | ДВА СЕРДЦА, КOKVP, Спиче Брда, КРМ |
| Декантер. Каберне Фран 2019, Фанагория | ВЫДЕРЖАНО В БУТЫЛКАХ, КАБЕРНЕ ФРАН | ВИДЕРЖАНО В ВУТЯЛКАХ, КАБЕРне ФРАН |
| Блан де Блан, Скалистый берег | СКАЛИСТЫЙ БЕРЕГ, экстра брют | СКАЛИСТЫЙ БЕРГЕТ, экстра бrious |
| Di Caspico розовое брют, Дербент Вино | БРЮТ РОЗОВОЕ, СДЕЛАНО В ДАГЕСТАНЕ | БРИТ РОЗОВOE, СДЕЛано В ДАГЕСТАНЕ |
| Совиньон Блан Резерва, Uppa Winery | PAVEL SHVETS, SAUVIGNON BLANC RESERVA | PAVEL SHVETS, SAUVIGNON BLANC RESERVA, UPPAWINERY.RU |

## Stage 3: label JSON (`json_object`)

| Measure | qwen | minicpm |
|---|---|---|
| Valid answers | 99/100 | 16/100 |
| p50 / p90 ms | 21180 / 46293 | 3528 / 5545 |
| Loop guard (second call) | 5 | 0 |
| Name words found (all valid answers) | 68% | 31% |

minicpm failures: 47 answers are not one JSON object, 27 give a list for `bottle`, and 10
have no key `marks`. The one qwen failure has no key `bottle`.
With `json_object`, the answers of minicpm are not limited to valid JSON. The cause
(gateway, llama.cpp version, or chat template) was not examined.

## Cluster re-rank (lab runs, test set `my`)

| Measure | base (no re-rank) | qwen | minicpm |
|---|---|---|---|
| R@1, positive | 81.26% (1522/1873) | 83.13% (1557/1873) | 81.10% (1519/1873) |
| R@5, positive | 97.33% | 97.33% | 97.33% |
| False match at rank 1, negative | 107 | 107 | 109 |
| Re-rank triggered | — | 707 | 707 |
| Rank 1 changed by the re-rank | — | 89 | 13 |
| Fixes / breaks against base | — | 46 / 11 | 1 / 4 |
| VLM answer refused (base order kept) | — | 23 | 619 |
| VLM ms p50 / p90 | — | 5877 / 10227 | 2363 / 3158 |
| Step ms p50 / p90 (SAM3 cut and VLM) | — | 7594 / 12216 | 2456 / 3283 |
| Wall time of the run | 753 s | 1422 s | 491 s |

- Each refused answer of both models has the error `the option scores of q1 total N;
  expected 100`. For minicpm, 203 answers total 0 and 126 total 10. The JSON Schema fixes
  the keys but not the sum. The 1.3 B model does not keep the rule "the scores total 100".
- In the 88 accepted minicpm answers, it gave 1 fix and 4 breaks.
- The base run was the first run of the new photos of `my`, so its wall time includes
  the new SAM3 cuts and embeddings. The two re-rank runs read them from the cache.
- 111 qwen answers and 130 minicpm answers came from `model_cache` (repeated photos, and
  5 queries of a smoke run). A cached answer keeps the time of its first call.

## Limits

- 100 images for the descriptions. The name and producer word recall is a proxy: a
  catalogue name in Cyrillic and a label in Latin gives a miss for both models.
- Stage 1 has no manual reference. The distributions and two checks by eye support qwen.
- The latencies come from 4 parallel requests on the shared gx10 GPU. Other sessions used
  the gateway at the same time.
- The re-rank runs used the cluster rules of 2026-10-01. Only one pipeline was compared.

## How to repeat

The scripts read `config.yaml` next to them (the scratch copy).

```sh
cd docs/reports/minicpm-vs-qwen35-9b-2026-10-01
python3 replay.py --vlm minicpm-v-4.6 --out new-minicpm.jsonl --n 100 --workers 4
python3 replay.py --vlm qwen3.5-9b-nvfp4 --out new-qwen.jsonl --n 100 --workers 4
python3 analyze_replay.py new-qwen.jsonl new-minicpm.jsonl
# The lab runs, from the workbench root:
python3 pipeline/run_job.py --config docs/reports/minicpm-vs-qwen35-9b-2026-10-01/config.yaml \
  --name barcode-rerank-minicpm-siglip2-p512-rot5-seg --set my \
  --jobs-dir <scratch>/jobs --runs-dir <scratch>/runs
```

`replay.py --stages 4` sends stage 1 with the strict schema. The scratch config sets
`rebuild_embeddings_on_run: false` and `image_description.watch: false`.
