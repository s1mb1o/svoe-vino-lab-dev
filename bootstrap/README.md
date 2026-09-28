# Развертывание сервисов моделей

Этот каталог нужен для развертывания ML-инфраструктуры, необходимой для работы сервиса.
Комплект развертывания предоставляет все библиотеки и модели, необходимые для работы сервиса.
Модели PyTorch доступны отдельными архивами на Google Drive.

Этот каталог содержит исходный код пяти локальных эндпоинтов инференса.
Каталог также содержит инструкции для запуска Qwen3.5-9B через Ollama.

## Роль bootstrap

Основные ML-сервисы проекта работают на GX10 (NVIDIA DGX Spark).
Организатор хакатона MAY использовать эти HTTP-эндпоинты, если частная сеть доступна.
Организатор MAY использовать bootstrap для запуска тех же API на своем хосте.
Такой запуск не является обязательным для всей системы.

Клиентские компоненты системы не загружают ML-модели в свои процессы.
Они отправляют запросы в HTTP-эндпоинты.
Исключением является Android-приложение.
Адреса эндпоинтов задают переменные среды.
Поэтому ML-сервисы MAY работать на одном или на нескольких отдельных хостах.

## Сетевая модель и аутентификация

Bootstrap предназначен для доверенной частной сети.
Сервисы bootstrap не выполняют аутентификацию.
Прямой доступ к этим сервисам MUST быть разрешен только из доверенной частной сети или через SSH-туннель.
Не публикуйте порты bootstrap в Интернете или в недоверенной сети.
Для такой публикации используйте внешний шлюз с TLS, аутентификацией и ограничением частоты запросов.
Такой шлюз не входит в bootstrap.

Система развертывания обслуживает следующие идентификаторы моделей:

- `qr-scanner`
- `shieldgemma-2-4b-it` — необязательная модель для `telegram-bot`
- `siglip2-so400m-patch16-naflex`
- `siglip2-so400m-patch16-512`
- `sam3`
- `qwen3.5:9b`

`siglip2-so400m-patch16-naflex` и `siglip2-so400m-patch16-512` являются альтернативами.
Основная система MUST использовать только одну из этих моделей.
Не запускайте обе модели одновременно.

URL шлюза по умолчанию: `http://127.0.0.1:18090`.

Используйте инструкцию для требуемой платформы:

- Apple Silicon: [`../docs/bootstrap/apple-silicon.md`](../docs/bootstrap/apple-silicon.md)
- Selectel с NVIDIA GPU: [`../docs/bootstrap/selectel-rtx4090.md`](../docs/bootstrap/selectel-rtx4090.md)

Инструкции в репозитории содержат всю необходимую информацию для организаторов хакатона.

## Скачивание моделей

Архивы моделей и `manifest.json` находятся в [папке Google Drive](https://drive.google.com/drive/folders/1k_suN_6i6jaaS_ti1Lsm5xUypy5vh4HQ).

Дождитесь завершения загрузки всех файлов.
Скачайте файлы в `artifacts/model-bundles/`.
Не изменяйте имена файлов.

Qwen3.5-9B не входит в пакет Google Drive.
Ollama скачивает модель `qwen3.5:9b` отдельно.
После скачивания Ollama запускает модель без доступа к интернету.
Архив ShieldGemma можно не устанавливать, если `telegram-bot` не используется.
В этом случае установите только SAM3 и выбранную модель SigLIP2:

```sh
.venv/bin/python scripts/install_model_bundles.py \
  --bundles artifacts/model-bundles \
  --model-root runtime/models \
  --model facebook/sam3 \
  --model google/siglip2-so400m-patch16-naflex
```

Замените `google/siglip2-so400m-patch16-naflex` на `google/siglip2-so400m-patch16-512`, если нужна модель fixed-512.

## Требования для одновременной работы

Для работы основной системы следующие сервисы MUST быть запущены и готовы к запросам одновременно:

- `qr-scanner`
- `sam3`
- `qwen3.5:9b`
- одна модель SigLIP2: `siglip2-so400m-patch16-naflex` или `siglip2-so400m-patch16-512`

Модель `shieldgemma-2-4b-it` нужна только для `telegram-bot`.
`telegram-bot` использует ShieldGemma для модерации изображений на предмет эротики и насилия.
Остальная система не требует ShieldGemma.

Расчетные минимальные требования для основной системы:

| Платформа | Память | GPU | Свободный диск | Размещение Qwen3.5-9B |
|---|---:|---:|---:|---|
| Apple Silicon | 48 GiB объединенной памяти | Apple GPU | 80 GiB | Metal через Ollama |
| NVIDIA GPU | 32 GiB RAM | 24 GiB VRAM | 80 GiB | NVIDIA GPU через Ollama |

Для основной системы рекомендуется 64 GiB объединенной памяти на Apple Silicon.
Для основной системы рекомендуется 64 GiB RAM и 32 GiB VRAM на NVIDIA.

Если `telegram-bot` использует ShieldGemma, минимум для Apple Silicon составляет 64 GiB объединенной памяти.
Если `telegram-bot` использует ShieldGemma, минимум для NVIDIA составляет 64 GiB RAM и 48 GiB VRAM.
На NVIDIA GPU с 24 GiB VRAM можно оставить ShieldGemma на GPU, а Qwen3.5-9B перенести на CPU.
Для этого профиля требуется не менее 64 GiB RAM.

Эти требования предполагают контекст Qwen3.5-9B размером 8192 токена и один запрос к Qwen за один момент.
Увеличение контекста или числа параллельных запросов увеличивает расход памяти.
Совместный запуск всех моделей еще не прошел нагрузочную проверку.

## Правила запуска

QR-сканер использует CPU для библиотеки `zxing-cpp`.
SAM3 и выбранная модель SigLIP2 используют PyTorch.
Ollama является одним из поддерживаемых способов запуска Qwen3.5-9B.
Qwen3.5-9B MAY работать в другой среде инференса или на другом хосте.
Эта среда MUST предоставлять совместимый эндпоинт `POST /v1/chat/completions`.
Задайте ее адрес и имя модели через `VLM_ENDPOINT` и `VLM_MODEL`.
ShieldGemma запускайте только вместе с `telegram-bot`.

ShieldGemma использует float32 на MPS и bfloat16 на CUDA.
Не используйте float16 для ShieldGemma в этой среде выполнения.
Проверенный запуск с float16 вернул неконечные оценки политик на обоих устройствах.

## Qwen3.5-9B через Ollama

Ollama рекомендуется как опорная среда для Mac и для хостов с NVIDIA GPU, включая RTX 4090.
В опорной конфигурации установите Ollama и выполните `ollama pull qwen3.5:9b`.
Опорная конфигурация использует идентификатор модели `qwen3.5:9b` и OpenAI-совместимый API.
Другая среда инференса MAY использовать другое имя модели.

Используйте следующие значения:

```sh
export VLM_ENDPOINT=http://127.0.0.1:11434/v1
export VLM_MODEL=qwen3.5:9b
```

Ollama MUST быть привязан к `127.0.0.1`.
Не публикуйте порт `11434` без входного шлюза с аутентификацией.

Инструкция для Apple Silicon: [`../docs/bootstrap/apple-silicon.md`](../docs/bootstrap/apple-silicon.md).
Инструкция для NVIDIA GPU: [`../docs/bootstrap/selectel-rtx4090.md`](../docs/bootstrap/selectel-rtx4090.md).

## Пути API

| Модель | Метод и путь |
|---|---|
| QR-сканер | `POST /upstream/qr-scanner/scan` |
| ShieldGemma | `POST /upstream/shieldgemma-2-4b-it/classify` |
| SAM3 | `POST /upstream/sam3/segment` |
| SAM3 | `POST /upstream/sam3/segment_multi` |
| SigLIP2 | `POST /v1/embeddings` |
| Qwen3.5-9B | `POST http://127.0.0.1:11434/v1/chat/completions` |

Каждый Python-сервис имеет эндпоинт проверки состояния по пути `/upstream/<model>/health`.
Для проверки Ollama используйте `GET http://127.0.0.1:11434/api/version`.

## Быстрые проверки

Запустите статические тесты:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Запустите одну модель, затем выполните проверку работоспособности с реальным запросом:

```sh
.venv/bin/python launcher.py --model qr-scanner
.venv/bin/python scripts/smoke.py --model qr-scanner
```

## Бенчмарки

Используйте `scripts/benchmark.py` для измерения одной запущенной модели.
Используйте `scripts/run_benchmarks.py` для последовательного тестирования CUDA-моделей в изолированных процессах, привязанных к интерфейсу обратной петли (`loopback`).

Ознакомьтесь с результатами сравнения GX10 и RTX 4090:

- [`docs/benchmarks/2026-09-28-gx10-vs-rtx4090.md`](docs/benchmarks/2026-09-28-gx10-vs-rtx4090.md)
