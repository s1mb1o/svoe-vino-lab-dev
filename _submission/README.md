# Своё Вино Lab

**Поиск вина по фотографии для каталога «Своё Вино».**

Система принимает фотографию бутылки и возвращает наиболее вероятные карточки вина.
Она объединяет штрихкод, сегментацию упаковки, визуальные embeddings и точечный VLM
re-rank для похожих этикеток.

Этот репозиторий содержит инженерную лабораторию решения. Лаборатория хранит каталог,
готовит изображения, строит индексы, запускает распознавание и сохраняет проверяемые
результаты экспериментов.

## Результат

Опорный pipeline `barcode-rerank-siglip2-512-crop` проверен на фиксированном наборе из
2 228 фотографий.

| Метрика | Результат |
| --- | ---: |
| R@1 на 1 644 positive-фотографиях | **84,67%** (1 392 / 1 644) |
| R@5 на 1 644 positive-фотографиях | **97,02%** |
| R@10 на 1 644 positive-фотографиях | **97,81%** |
| False match at 1 на 584 negative-фотографиях | 90 / 584 |

Это инженерный reference result. Это не финальный результат подачи. Отчёт фиксирует
ограничения индекса и разметки. Финальный score нужно пересчитать на итоговом snapshot.

Полные данные: [сравнение 53 профилей](docs/reports/2026-09-27_all-profile-rerun.md) и
[анализ ошибок опорного pipeline](docs/reports/2026-09-27_after5-failure-analysis.md).

## Как работает распознавание

```text
фото
  → GTIN или QR fast path
  → SAM3 package cut
  → SigLIP2 embedding
  → поиск кандидатов по cosine similarity
  → VLM rule для сложного cluster
  → top candidates + trace + latency
```

- Штрихкод даёт детерминированный ответ, когда код однозначен.
- SAM3 отделяет бутылку, банку, пакет или коробку от фона.
- SigLIP2 сравнивает фотографию с изображениями каталога.
- Clusters группируют визуально близкие карточки.
- VLM rule различает винтаж, сорт, цвет и другие детали этикетки.
- Каждый benchmark сохраняет запросы, ответы, метрики и trace шагов.

Подробнее: [ARCHITECTURE.md](ARCHITECTURE.md).

## Интерфейс

Локальный Web UI содержит семь разделов:

- `Dataset` — каталог, изображения, коды, связи и ручная разметка.
- `Embeddings` — состояние индексов и их сборка.
- `Clusters` — группы похожих карточек и правила различения.
- `Testset` — тестовые наборы и ground truth.
- `Runs` — результаты, метрики и ошибки каждого запуска.
- `Recognize` — распознавание одной фотографии.
- `Health` — состояние базы, jobs, моделей и endpoints.

Интерфейс поддерживает светлую и тёмную системную тему.

## Быстрый запуск лаборатории

Нужны Python 3, Git, CMake и C++ compiler для `zxing-cpp`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-local.txt

# Выполните эти две команды один раз после clean clone.
python3 pipeline/db_export.py restore --from db-export --db data/lab.sqlite3
python3 pipeline/labdb.py data/lab.sqlite3

python3 pipeline/lab_server.py --config config.example.yaml --no-browser
```

Откройте [http://127.0.0.1:8168](http://127.0.0.1:8168).

Этот путь запускает локальную лабораторию и просмотр каталога. Полное распознавание
также требует model endpoints и готового embedding index. Задайте их в отдельной
локальной конфигурации. Не добавляйте ключи или private endpoints в Git.

## Проверка

```bash
python3 -m compileall -q pipeline scripts tests
python3 -m unittest discover -s tests
```

Подробные ручные проверки находятся в [SMOKE_TESTS.md](SMOKE_TESTS.md).

## Структура репозитория

| Путь | Назначение |
| --- | --- |
| `pipeline/` | Активная лаборатория, распознавание и Web UI. |
| `pipeline/schema/` | Последовательные изменения схемы SQLite. |
| `tests/` | Автоматические тесты. |
| `db-export/` | Текстовый snapshot лабораторной базы. |
| `data/images/` | Версионируемые изображения каталога и ручные дополнения. |
| `docs/reports/` | Benchmark reports и анализ ошибок. |
| `docs/plans/` | Решения и implementation plans. |
| `scripts/` | Legacy pipeline подготовки исходного test set. |

## Ограничения

- Сервер слушает `127.0.0.1` и не имеет аутентификации. Не публикуйте его напрямую.
- Полный pipeline использует внешние model services.
- `data/embeddings/`, test photos, model cache и run artifacts не входят в Git.
- `config.yaml` содержит developer-specific settings. Для проверки используйте
  `config.example.yaml` или свою локальную конфигурацию.

## Документация

- [Архитектура](ARCHITECTURE.md)
- [Команды](COMMANDS.md)
- [API guide](docs/API.md)
- [OpenAPI](docs/openapi.yaml)
- [Research log](ResearchLog.md)
- [Change log](ChangeLog.md)
