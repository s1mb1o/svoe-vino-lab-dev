# «Своё Вино»: поиск вина по фотографии

Проект распознаёт вино по фотографии бутылки или этикетки. Пользователь получает
карточку вина и ссылку на каталог [vino-svoe.ru](https://vino-svoe.ru/).

Решение создано для задачи #10 от РСХБ.Цифра "Сканер российских вин с описанием на платформе Свое Вино". Репозиторий содержит:
- Web UI, 
- Telegram-бота, 
- MAX-бота, 
- HTTP matcher, 
- локальные model service, 
- сервис для обработки датасетов и проведения экспериментов.

Для организаторов и жюри хакатона (людей и LLM): [ASSESSMENT.md](ASSESSMENT.md) — карта возможностей проекта.
Для каждой возможности файл указывает код, тесты и другие доказательства.

Food-to-wine recommendations for #28 run as a separate backend: [Dinner Lens](dinner-lens/README.md)
documents code-enforced filters, curated choices, embedding discovery and the authenticated API.
The Web UI connects to Dinner Lens through `/dish` and the same-origin `/api/dinner/*` routes.
Set `NUXT_DINNER_LENS_ENDPOINT` and `NUXT_DINNER_LENS_API_TOKEN` on the Web UI server.
Read [the integration guide](webui/docs/dinner-lens.md) for configuration and limits.
The Telegram bot and the MAX bot are not connected to Dinner Lens yet.
The current Dinner Lens JSON covers 200 dishes and 120 fallback/intermediate classes;
the original 75-dish dataset and photographic benchmark remain available separately.

## Что умеет система

- Принимает JPEG, PNG, WebP и HEIF (HEIC) через Web UI и HTTP API матчера (HEIC в production
  с 2026-10-18). MAX-бот и Telegram-бот этого репозитория переводят HEIC-файл в JPEG.
  Telegram-бот в production принимает фото и альбомы, но не HEIC-файлы.
- Android-приложение принимает JPEG, PNG, WebP и HEIF (HEIC) из галереи.
- The Web UI shows an 18+ warning and requires age confirmation before access.
- Возвращает один slug через `POST /v1/eval/predict`.
- Возвращает до 20 кандидатов через `POST /v1/match`.
- Использует SigLIP2 и embedding index из 2 094 вин.
- Проверяет фотографии Telegram через ShieldGemma 2 до записи на диск.
- Использует SAM3 для поиска бутылки и этикетки.
- Показывает варианты, если уверенность результата недостаточна.
- Предлагает продукты к вину по данным выбранного магазина «Глобус».
- Сохраняет воспроизводимые benchmark runs и технический trace.

## Результаты

Для контрольной проверки организаторы предоставили тестовый датасет из 100 фотографий. Контрольная сумма датасета: d9da3ea97ebd2f348efbe56efaed637416cc86934e711b29535e747184fe57dc.

Эталонные ответы организаторы не предоставили. Команда самостоятельно составила expected.jsonl путём кросс-сопоставления базы ФРАП, каталога vino-svoe.ru, сайтов и Telegram-каналов производителей.

Решение получило 95/100 совпадений с нашим эталоном, включая допустимые альтернативные wine_slug. Это результат внутренней проверки команды, а не официальная оценка жюри.

Файл: predictions.jsonl

В отдельном диагностическом эксперименте ручная корректировка данных через UI повысила результат до 97/100. Однако изменения были сделаны после выяснения правильных ответов. Такой результат отражает подстройку под известный тест и требует проверки на независимых данных. Поэтому эти изменения не включены в финальный результат: он остаётся 95/100.


## Latest engineering measurements

The 2026-10-20 retrieval campaign reports **90.77% R@1** (2,696/2,970),
**99.83% R@5**, and **100% R@10** on the frozen `my` positive assignments.
These are the metrics of recipe R011 with SigLIP2 SO400M, custom pooling, axial reference
views, and bottle–label fusion. The campaign uses no re-ranking.
Read [the exact recipes and results](RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md).

On the selected hard cohort `my-failed-2`, the best all-budget R@1 is
**67.37%** (450/668). The best p512 R@1 is **66.17%** (442/668).
The cohorts were used for development selection. These are research results.
They do not describe the default matcher or the official hackathon score.

The later [Android 0.3.0 release record](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/6bd4abed8009296dec8cdde4e418103f610a74ba/android/docs/releases/0.3.0.md) reports
**46.56% Top-1**, **84.58% Top-5**, and **89.67% Top-10** on the same named hard cohort.
Its complete 668-request Pixel 8 replay has zero errors and a 1,372 ms median.
That release uses Base NaFlex p512 with DIS-768 and custom pooling.
It has no full-`my` quality result in that record.
The earlier separate dual-GPU experiment reached **72.29% Top-1** on full `my`,
against **69.09%** for its matched full-image control, with greater latency and memory use.
The Android 0.3.0 source and its release record are on `origin/main` at the linked commit.
This documentation update does not import that runtime into this checkout.

Read [BENCHMARKS.md](BENCHMARKS.md) for the dataset sizes, complete metric rows,
timing scopes, negative cases, and source links.

## Предыдущие инженерные бенчмарки

The 2026-09-27 snapshot has 2,228 query rows: 1,644 positive rows and 584 negative constraints.
It contains 1,851 distinct image digests.
The committed default `siglip2-p512-as-is` recorded **74.15% R@1** and **92.94% R@5**
on that snapshot. This default remains separate from the newer research recipes.

The recorded `cascade-p512-rot5` ranked API run has **90.48% R@1** and **100% R@5**
on 63 positive and 21 negative organizers' photos, with team labels and no request time budget.
The later RTX 4090 FP8 VLM run recorded **93.65% R@1** (59/63 positives) with the evaluator
time budget. Its 84 requests had zero errors and a 1,353 ms median.
Read [the recorded measurement](workbench/ResearchLog.md).
These runs use different hardware and request settings.

The 2026-09-27 workbench leader `barcode-rerank-siglip2-512-crop` recorded
**84.67% R@1** and **97.02% R@5** on the earlier 1,644-positive snapshot.
The newer research cohort has 2,970 positive assignments.
The difference from 84.67% to 90.77% is not a controlled improvement on one fixed testset.
The `cascade` backend implements code scanning, segmentation, and re-ranking.
The default `siglip2-p512-as-is` configuration does not enable those stages.

## Retrieval research without re-ranking

[Retrieval algorithms and benchmark results, 20 October 2026](RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md)
records a separate SigLIP2 SO400M NaFlex research campaign. It compares **353,188 unique
retrieval configurations per frozen testset** on `my` and `my-failed-2`.
The reference defines 39 pooling profiles, 42 fusion policies, query alignment,
label retrieval, synthetic bottle-axis views, crop margins, patch budgets, and
reference-score aggregation. It includes formulas, exact parameters, baseline
comparisons, top-five leaderboards, the best p512 variants, and 53 exact result recipes.

On the selected hard set `my-failed-2`, the best R@1 rises from **44.01% to 67.37%**;
the best p512 R@1 is **66.17%**. These are development-set research results, not
production matcher scores or official hackathon scores. The reference preserves
separate GX10 and incomplete RTX4090 results. The [portable research package](research/retrieval-20261020/README.md)
includes source snapshots, frozen specifications, compact benchmark summaries,
and an offline checker. Run `python3 research/retrieval-20261020/verify.py` to check
the package without model weights or network access. Full benchmark images, masks,
accepted answers, and complete result databases are not bundled. See F-112 in
[ASSESSMENT.md](ASSESSMENT.md).

## Быстрый запуск интерфейса

```bash
cd webui
npm ci
npm run dev
```

Откройте [http://127.0.0.1:8153](http://127.0.0.1:8153).
По умолчанию Web UI явно работает в mock mode. Для реального распознавания нужен
matcher и model endpoint. Полная инструкция находится в [SETUP.md](SETUP.md).

## Компоненты

| Каталог | Назначение |
| --- | --- |
| `webui/` | Nuxt Web UI, evaluator route и рекомендации еды. |
| `mcp/` | Read-only MCP tools for catalog cards, discovery, comparison, the product-line demo, and approved audio metadata. |
| `account/` | Сервис аккаунтов «Винный дневник»: вход по коду из письма и Яндекс ID, привязка MAX и Telegram (без входа через Telegram). |
| `telegram-bot/` | Бот [@ChtoZaVinoBot](https://t.me/ChtoZaVinoBot), moderation и очередь. |
| `max-bot/` | Бот MAX «Что за вино?» [@se14697933_bot](https://max.ru/se14697933_bot) с той же функциональностью. |
| `im-core/` | Общее ядро обработки обоих ботов (пакет `chto_za_vino_core`). |
| `shelf-lens/` | Android-приложение «Полка вина»: видео полки, поиск бутылок на телефоне, распознавание через matcher, рамки и рейтинг поверх камеры, планограмма. |
| `matcher/` | FastAPI matcher с Top-1 и ranked API. |
| `bootstrap/` | Локальные endpoints SigLIP2, SAM3, ShieldGemma 2 и QR scanner. |
| `matcher-inspector/` | Read-only просмотр запросов и embedding bundles. |
| `workbench/` | Данные, индексы, эксперименты, benchmarks и сборка bundles. |
| `eval/` | Скрипт проверки организаторов и три контрольных фотографии. |

## Документация

- [Архитектура](ARCHITECTURE.md)
- [Benchmarks](BENCHMARKS.md)
- [Retrieval research: algorithms, exact parameters, and p512 results](RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md)
- [Установка и запуск](SETUP.md)
- [Matcher API](matcher/README.md)
- [Проверка организаторов: запуск matcher и `participant_test.sh`](eval/README.md)
- [Telegram-бот](telegram-bot/README.md)
- [MAX-бот](max-bot/README.md)
- [Общее ядро ботов](im-core/README.md)
- [Web UI](webui/README.md)
- [Wine catalog MCP](mcp/README.md)
- [MCP implementation plan](docs/plans/02_wine-catalog-mcp.md)
- [Развертывание локальных моделей](docs/bootstrap/README.md)
- [Эндпоинты моделей на Apple Silicon](docs/bootstrap/apple-silicon.md)
- [Эндпоинты моделей на Selectel RTX 4090](docs/bootstrap/selectel-rtx4090.md)

## Ограничения

- Model weights не хранятся в Git. Bundle standalone matcher хранится в Git:
  `matcher/data/gx10-siglip2-so400m-patch16-naflex-p512/`.
- Реальный запуск требует SigLIP2 endpoint и bundle.
- Shelf mode в Web UI выключен по умолчанию.
- Лаборатория и inspector не имеют публичной аутентификации. Их нельзя публиковать в WAN.
- Benchmark является внутренней инженерной оценкой. Это не официальный score хакатона.
