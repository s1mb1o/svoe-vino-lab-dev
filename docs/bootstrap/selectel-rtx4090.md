# Развертывание сервисов моделей на Selectel с NVIDIA GPU

Дата: 2026-09-28

## Назначение

Эта инструкция развертывает ML-инфраструктуру на хосте Selectel с NVIDIA GPU.
Она использует нативный Python, CUDA и Ollama.
Она не использует Docker.

Проверенный хост использовал Ubuntu 24.04.3 и RTX 4090 с 24 564 MiB VRAM.
Отдельные модели прошли проверку на этом хосте.
Одновременная нагрузочная проверка еще не выполнена.

Задайте в `SELECTEL_HOST` IP-адрес или DNS-имя, которое получил организатор.
Выполняйте команду `export` в каждом новом локальном терминале.

## Требования

- Ubuntu 24.04
- NVIDIA GPU с поддержкой CUDA
- NVIDIA driver 580 или новее
- Не менее 24 GiB VRAM для основной системы
- Не менее 48 GiB VRAM, если ShieldGemma и Qwen3.5-9B также работают на GPU
- Не менее 80 GiB свободного места на файловой системе `/opt`
- Не менее 32 GiB RAM для основной системы
- Не менее 64 GiB RAM для профиля с ShieldGemma и Qwen3.5-9B на CPU
- SSH-доступ с правами `root`
- Исходящий HTTPS-доступ к репозиториям пакетов Ubuntu, PyPI, `download.pytorch.org` и Ollama

Модель ShieldGemma нужна только для модерации изображений в `telegram-bot`.

## Политика безопасности

Bootstrap предназначен для доверенной частной сети.
Сервисы bootstrap не выполняют аутентификацию.
Launcher по умолчанию привязывается к `127.0.0.1`.
Сохраняйте это значение на публичном облачном хосте.
Используйте SSH-туннель для удаленного доступа.

Задайте `--host` равным адресу частного интерфейса только для доступа из доверенной частной сети.
Межсетевой экран MUST блокировать доступ из других сетей.
Для публичного или недоверенного доступа используйте внешний шлюз с TLS, аутентификацией и ограничением частоты запросов.
Такой шлюз не входит в bootstrap.

## Проверка хоста и установка системных пакетов

```sh
export SELECTEL_HOST=server.example.org
ssh root@${SELECTEL_HOST}
df -h /opt
free -h
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y curl python3.12-venv rsync
curl -fsSIL --max-time 20 https://pypi.org/simple/ >/dev/null
curl -fsSIL --max-time 20 https://download.pytorch.org/whl/cu130/ >/dev/null
nvidia-smi
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
```

Остановите установку, если на файловой системе `/opt` доступно менее 80 GiB.
Остановите установку, если доступно менее 32 GiB оперативной памяти.
Каждая команда `curl` MUST завершиться без ошибки.
Остановите установку, если `nvidia-smi` не показывает NVIDIA GPU с 24 GiB VRAM или больше.

## Копирование исходного кода

Выполните эту команду из каталога, который содержит репозиторий `svoe-vino-lab`:

```sh
rsync -avc \
  --exclude '.venv/' \
  --exclude '.cache/' \
  --exclude 'runtime/' \
  --exclude 'artifacts/model-bundles/*.tar*' \
  --exclude '__pycache__/' \
  svoe-vino-lab/bootstrap/ \
  root@${SELECTEL_HOST}:/opt/svoe-vino-model-bootstrap/
```

## Установка пакетов Python

```sh
ssh root@${SELECTEL_HOST}
cd /opt/svoe-vino-model-bootstrap
sh scripts/setup-selectel.sh
```

Скрипт устанавливает закрепленную версию PyTorch для CUDA 13.0.
Скрипт запускает модульные тесты.
Скрипт завершает работу с ошибкой, если PyTorch не может использовать CUDA.

## Установка Ollama и Qwen3.5-9B

Ollama является рекомендуемой средой выполнения Qwen3.5-9B на NVIDIA GPU.
Инструкции для Mac и NVIDIA используют одну модель `qwen3.5:9b` и один OpenAI-совместимый API.
Вы MAY пропустить этот раздел, если Qwen3.5-9B работает в другой среде инференса или на другом хосте.
Другая среда MUST предоставлять совместимый эндпоинт `POST /v1/chat/completions`.
Задайте ее адрес и имя модели через `VLM_ENDPOINT` и `VLM_MODEL`.

Установите Ollama:

```sh
curl -fsSL https://ollama.com/install.sh | sh
systemctl edit ollama.service
```

Добавьте следующие строки в редактор:

```ini
[Service]
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_CONTEXT_LENGTH=8192"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_KEEP_ALIVE=-1"
```

Сохраните файл.
Закройте редактор.
Затем выполните команды:

```sh
systemctl daemon-reload
systemctl restart ollama
systemctl status ollama --no-pager
ollama pull qwen3.5:9b
```

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
Для основной системы в столбце `PROCESSOR` должен быть указан GPU.

Если NVIDIA GPU имеет 24 GiB VRAM и нужна ShieldGemma, запускайте Qwen3.5-9B на CPU.
Добавьте в тот же override-файл строку:

```ini
Environment="CUDA_VISIBLE_DEVICES=-1"
```

Перезапустите Ollama.
`ollama ps` MUST показать `100% CPU`.
Этот профиль требует не менее 64 GiB RAM.

## Скачивание моделей

Откройте [папку с моделями на Google Drive](https://drive.google.com/drive/folders/1k_suN_6i6jaaS_ti1Lsm5xUypy5vh4HQ) на исходной машине.

Дождитесь завершения загрузки всех файлов.
Перед скачиванием убедитесь, что в папке видны следующие пять файлов:

- `manifest.json`
- `facebook--sam3.tar`
- `google--shieldgemma-2-4b-it.tar`
- `google--siglip2-so400m-patch16-naflex.tar`
- `google--siglip2-so400m-patch16-512.tar`

Скачайте каждый файл в `svoe-vino-lab/bootstrap/artifacts/model-bundles/`.
Не изменяйте имена файлов.
Передавайте архив с ограниченным доступом только получателю, который принял применимое лицензионное соглашение модели.

## Передача приватных пакетов моделей

Выполните эту команду на исходной машине:

```sh
rsync -av --partial --append-verify --info=progress2 \
  svoe-vino-lab/bootstrap/artifacts/model-bundles/ \
  root@${SELECTEL_HOST}:/opt/svoe-vino-model-bootstrap/artifacts/model-bundles/
```

Ограничьте доступ к лицензированным архивам:

```sh
ssh root@${SELECTEL_HOST} \
  'chmod 600 /opt/svoe-vino-model-bootstrap/artifacts/model-bundles/*.tar'
```

## Установка пакетов моделей

```sh
ssh root@${SELECTEL_HOST}
cd /opt/svoe-vino-model-bootstrap
.venv/bin/python scripts/install_model_bundles.py \
  --bundles artifacts/model-bundles \
  --model-root runtime/models
```

Установщик проверяет размер и SHA-256 каждого архива до извлечения.
Установщик отклоняет ссылки и небезопасные пути в архивах.

## Запуск одной модели

Пример запуска SAM3 вместе с QR-сканером:

```sh
ssh root@${SELECTEL_HOST}
cd /opt/svoe-vino-model-bootstrap
.venv/bin/python launcher.py --model sam3 --device cuda --with-qr
```

Вместо `sam3` укажите один из следующих идентификаторов моделей:

- `shieldgemma-2-4b-it`
- `siglip2-so400m-patch16-naflex`
- `siglip2-so400m-patch16-512`

Эти две модели SigLIP2 являются альтернативами.
Не запускайте обе модели SigLIP2 одновременно.

Используйте только `qr-scanner`, если модель с ускорителем не требуется.

ShieldGemma использует bfloat16 на CUDA.
Не изменяйте тип данных на float16.
Проверенный запуск с float16 вернул неконечные оценки политик.

## Одновременный запуск основной системы

Убедитесь, что Ollama уже запущен и что `qwen3.5:9b` загружена.
Запустите QR-сканер, SAM3 и одну модель SigLIP2:

```sh
ssh root@${SELECTEL_HOST}
cd /opt/svoe-vino-model-bootstrap
.venv/bin/python launcher.py \
  --model sam3 \
  --model siglip2-so400m-patch16-naflex \
  --with-qr \
  --device cuda \
  --allow-multiple-accelerators
```

Замените `siglip2-so400m-patch16-naflex` на `siglip2-so400m-patch16-512`, если нужна модель fixed-512.
Не запускайте обе модели SigLIP2 одновременно.

Модель ShieldGemma не нужна для остальной системы.
Если нужен `telegram-bot`, добавьте `--model shieldgemma-2-4b-it` в эту команду.
Профиль с ShieldGemma должен соответствовать увеличенным требованиям к памяти из раздела «Требования».

## Открытие SSH-туннеля

Выполните эту команду на клиентской машине:

```sh
ssh -N \
  -L 18090:127.0.0.1:18090 \
  -L 11434:127.0.0.1:11434 \
  root@${SELECTEL_HOST}
```

После этого клиент может использовать шлюз на `http://127.0.0.1:18090` и Ollama на `http://127.0.0.1:11434`.

## Проверка с реальным запросом

Выполните эту команду во второй SSH-сессии:

```sh
ssh root@${SELECTEL_HOST}
cd /opt/svoe-vino-model-bootstrap
.venv/bin/python scripts/smoke.py --model sam3
```

Вместо `sam3` укажите идентификатор активной модели.
Проверяйте каждую модель с ускорителем отдельно.
Остановите launcher перед запуском следующей модели с ускорителем.

## Настройка клиента

Используйте следующие значения на хосте Selectel или через SSH-туннель:

```sh
export SAM3_ENDPOINT=http://127.0.0.1:18090/upstream/sam3
export QR_SCANNER_ENDPOINT=http://127.0.0.1:18090/upstream/qr-scanner
export MODERATION_ENDPOINT=http://127.0.0.1:18090/upstream/shieldgemma-2-4b-it/classify
export SIGLIP2_ENDPOINT=http://127.0.0.1:18090
export VLM_ENDPOINT=http://127.0.0.1:11434/v1
export VLM_MODEL=qwen3.5:9b
```

`MODERATION_ENDPOINT` нужен только для `telegram-bot`.

## Остановка и проверка

Остановите launcher с помощью `Ctrl-C`.

Убедитесь, что шлюз остановлен:

```sh
ss -ltnp | grep ':18090 ' || true
nvidia-smi
```

Проверенный хост успешно обработал реальные проверочные запросы для пяти Python-эндпоинтов по отдельности.
Процедура Ollama еще не прошла проверку на этом хосте.
