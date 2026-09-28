# Развертывание сервисов моделей на Apple Silicon

Дата: 2026-09-28

## Назначение

Эта инструкция развертывает локальную ML-инфраструктуру на Mac с Apple Silicon.
Она использует нативный Python, PyTorch MPS и Ollama.
Она не использует Docker.

Отдельные модели проверены на Mac с Apple M2 Max и 32 GiB объединенной памяти.
Эта конфигурация не соответствует требованию одновременной работы.

## Требования

- Apple Silicon
- macOS 14 или новее
- Python 3.12
- Не менее 80 GiB свободного места на диске
- Не менее 48 GiB объединенной памяти без ShieldGemma
- Не менее 64 GiB объединенной памяти с ShieldGemma
- Исходящий HTTPS-доступ к GitHub, Google Drive, PyPI и Ollama
- Репозиторий `svoe-vino-lab`
- Приватные архивы моделей и файл `manifest.json`

Модель ShieldGemma нужна только для модерации изображений в `telegram-bot`.

## Сетевая модель

Bootstrap предназначен для доверенной частной сети.
Сервисы bootstrap не выполняют аутентификацию.
По умолчанию launcher привязывает шлюз к `127.0.0.1`.
Задайте `--host` равным адресу частного интерфейса только для доступа из доверенной частной сети.
Межсетевой экран MUST блокировать доступ из других сетей.
Для публичного или недоверенного доступа используйте внешний шлюз с TLS, аутентификацией и ограничением частоты запросов.
Такой шлюз не входит в bootstrap.

Некоторые репозитории моделей требуют принятия лицензионного соглашения.
Не публикуйте архив модели с ограниченным доступом.
Передавайте такой архив только получателю, который принял применимое лицензионное соглашение.

## Скачивание моделей

Откройте [папку с моделями на Google Drive](https://drive.google.com/drive/folders/1k_suN_6i6jaaS_ti1Lsm5xUypy5vh4HQ).

Дождитесь завершения загрузки всех файлов.
Перед скачиванием убедитесь, что в папке видны следующие пять файлов:

- `manifest.json`
- `facebook--sam3.tar`
- `google--shieldgemma-2-4b-it.tar`
- `google--siglip2-so400m-patch16-naflex.tar`
- `google--siglip2-so400m-patch16-512.tar`

Скачайте каждый файл в `bootstrap/artifacts/model-bundles/`.
Не изменяйте имена файлов.

## Установка пакетов Python

Выполните команды из корня репозитория `svoe-vino-lab`:

```sh
cd bootstrap
sh scripts/setup-macos.sh
```

Скрипт создает `.venv` и `.cache` внутри `bootstrap/`.

## Установка Ollama и Qwen3.5-9B

Ollama является рекомендуемой средой выполнения Qwen3.5-9B на Mac.
Вы MAY пропустить этот раздел, если Qwen3.5-9B работает в другой среде инференса.
Другая среда MUST предоставлять совместимый эндпоинт `POST /v1/chat/completions`.
Задайте ее адрес и имя модели через `VLM_ENDPOINT` и `VLM_MODEL`.
Скачайте и установите [Ollama для macOS](https://ollama.com/download/mac).
Закройте Ollama перед установкой переменных среды.

Выполните команды:

```sh
launchctl setenv OLLAMA_HOST "127.0.0.1:11434"
launchctl setenv OLLAMA_CONTEXT_LENGTH "8192"
launchctl setenv OLLAMA_NUM_PARALLEL "1"
launchctl setenv OLLAMA_KEEP_ALIVE "-1"
open -a Ollama
ollama pull qwen3.5:9b
```

Модель Ollama использует Metal.
После команды `ollama pull` модель может работать без доступа к интернету.

Проверьте OpenAI-совместимый API:

```sh
curl http://127.0.0.1:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen3.5:9b",
    "messages": [{"role": "user", "content": "Ответь одним словом: готов"}],
    "max_tokens": 16,
    "stream": false
  }'
ollama ps
```

`ollama ps` MUST показать `qwen3.5:9b`.

## Установка пакетов моделей

Убедитесь, что в `bootstrap/artifacts/model-bundles/` находятся пять файлов из раздела «Скачивание моделей».

Ограничьте доступ к лицензированным архивам:

```sh
chmod 600 artifacts/model-bundles/*.tar
```

Проверьте и установите все пакеты:

```sh
.venv/bin/python scripts/install_model_bundles.py \
  --bundles artifacts/model-bundles \
  --model-root runtime/models
```

Установщик проверяет размер и SHA-256 каждого архива до извлечения.
Установщик отклоняет ссылки и небезопасные пути в архивах.
Установщик не заменяет существующий каталог модели.

## Проверка QR-сканера

Запустите сервис в терминале 1:

```sh
.venv/bin/python launcher.py --model qr-scanner
```

Выполните проверку с реальным запросом в терминале 2:

```sh
.venv/bin/python scripts/smoke.py --model qr-scanner
```

Остановите терминал 1 с помощью `Ctrl-C`.

Переносимый QR-сканер использует `zxing-cpp`.
Он не содержит резервных механизмов BoofCV, super-resolution, SAM3 и VLM, которые доступны только на GX10.

## Проверка моделей с ускорителем

Проверяйте каждую модель отдельно.
Остановите launcher перед запуском следующей модели.

SAM3:

```sh
.venv/bin/python launcher.py --model sam3 --device mps
.venv/bin/python scripts/smoke.py --model sam3
```

ShieldGemma:

```sh
.venv/bin/python launcher.py --model shieldgemma-2-4b-it --device mps
.venv/bin/python scripts/smoke.py --model shieldgemma-2-4b-it
```

SigLIP2 NaFlex:

```sh
.venv/bin/python launcher.py --model siglip2-so400m-patch16-naflex --device mps
.venv/bin/python scripts/smoke.py --model siglip2-so400m-patch16-naflex
```

SigLIP2 fixed-512:

```sh
.venv/bin/python launcher.py --model siglip2-so400m-patch16-512 --device mps
.venv/bin/python scripts/smoke.py --model siglip2-so400m-patch16-512
```

Добавьте `--with-qr`, если QR-сканер должен работать вместе с выбранной моделью с ускорителем.

## Одновременный запуск основной системы

Убедитесь, что Ollama уже запущен и что `qwen3.5:9b` загружена.
Запустите QR-сканер, SAM3 и одну модель SigLIP2:

```sh
.venv/bin/python launcher.py \
  --model sam3 \
  --model siglip2-so400m-patch16-naflex \
  --with-qr \
  --device mps \
  --allow-multiple-accelerators
```

Замените `siglip2-so400m-patch16-naflex` на `siglip2-so400m-patch16-512`, если нужна модель fixed-512.
Не запускайте обе модели SigLIP2 одновременно.

Если нужен `telegram-bot`, запустите также ShieldGemma:

```sh
.venv/bin/python launcher.py \
  --model sam3 \
  --model siglip2-so400m-patch16-naflex \
  --model shieldgemma-2-4b-it \
  --with-qr \
  --device mps \
  --allow-multiple-accelerators
```

Для этого профиля требуется не менее 64 GiB объединенной памяти.

## Настройка клиента

URL шлюза по умолчанию: `http://127.0.0.1:18090`.

```sh
export SAM3_ENDPOINT=http://127.0.0.1:18090/upstream/sam3
export QR_SCANNER_ENDPOINT=http://127.0.0.1:18090/upstream/qr-scanner
export SHIELDGEMMA_ENDPOINT=http://127.0.0.1:18090/upstream/shieldgemma-2-4b-it
export MODERATION_ENDPOINT=${SHIELDGEMMA_ENDPOINT}/classify
export SIGLIP2_ENDPOINT=http://127.0.0.1:18090
export VLM_ENDPOINT=http://127.0.0.1:11434/v1
export VLM_MODEL=qwen3.5:9b
```

Клиент SigLIP2 отправляет запрос `POST ${SIGLIP2_ENDPOINT}/v1/embeddings`.
Поле `model` в JSON выбирает модель SigLIP2.
`MODERATION_ENDPOINT` нужен только для `telegram-bot`.

Проверьте все настроенные внешние ML endpoint одной командой:

```sh
.venv/bin/python scripts/check_compatibility.py
```

Удалите `SHIELDGEMMA_ENDPOINT` из окружения, если ShieldGemma не запущена.

## Важные сведения о запуске

ShieldGemma использует float32 на MPS.
Не изменяйте тип данных на float16.
Проверенный запуск с float16 вернул неконечные оценки политик.

Первый импорт и загрузка модели с внешнего диска могут занимать несколько минут.
Первый проверенный инференс SAM3 занял приблизительно 61 секунду.
Проверенный запрос ShieldGemma для трех политик занял приблизительно 4,1 минуты.
Процедура Ollama и совместный запуск всех моделей еще не прошли нагрузочную проверку.

Если MPS недоступен, выполните эту команду вне sandbox приложения:

```sh
.venv/bin/python -c 'import torch; print(torch.backends.mps.is_built(), torch.backends.mps.is_available())'
```

Оба значения должны быть равны `True`.
