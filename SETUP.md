# Установка и запуск

## Требования

- Node.js 24 LTS для Web UI.
- Python 3.11 или новее для matcher.
- Python 3.12 или новее и `uv` для Telegram-бота.
- CMake и C++ compiler для полного workbench environment.

## Web UI без моделей

Этот режим показывает полный пользовательский flow с явным mock result.

```bash
cd webui
npm ci
npm run dev
```

Откройте [http://127.0.0.1:8153](http://127.0.0.1:8153).

## Mock matcher

Выполните команды из корня репозитория:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r matcher/requirements.txt

export SVOE_VINO_MATCHER_CONFIG=matcher/tests/config.yaml
export SVOE_VINO_MATCHER_OUTPUT_DIR=work/matcher-requests
python -m uvicorn matcher.app:app --host 127.0.0.1 --port 8158
```

Проверьте service:

```bash
curl http://127.0.0.1:8158/healthz
curl -F image=@matcher/tests/data/02eef911.webp \
  http://127.0.0.1:8158/v1/eval/predict
```

## Web UI с matcher

Создайте `webui/.env`:

```dotenv
NUXT_PREDICTION_MODE=upstream
NUXT_PREDICTION_ENDPOINT=http://127.0.0.1:8158/v1/eval/predict
NUXT_SHELF_MODE=disabled
```

Перезапустите Web UI. Браузер продолжит вызывать route на origin Web UI.

## Реальный SigLIP2 matcher

Реальный matcher требует:

1. Bundle `matcher/data/gx10-siglip2-so400m-patch16-naflex-p512`. Он хранится в Git.
2. OpenAI-compatible SigLIP2 endpoint.
3. Environment variable `SIGLIP2_ENDPOINT` без suffix `/v1`.

Bundle создаёт `workbench/scripts/build_matcher_bundle.py`. Model services можно
развернуть из [bootstrap/README.md](bootstrap/README.md). Затем запустите matcher без
`SVOE_VINO_MATCHER_CONFIG`:

```bash
unset SVOE_VINO_MATCHER_CONFIG
export SIGLIP2_ENDPOINT=http://127.0.0.1:18090
export SVOE_VINO_MATCHER_OUTPUT_DIR=work/matcher-requests
python -m uvicorn matcher.app:app --host 127.0.0.1 --port 8158
```

## Telegram-бот

```bash
cd telegram-bot
uv sync --extra dev
cp .env.example .env
```

Задайте `TELEGRAM_BOT_TOKEN`, `MATCHER_ENDPOINT`, `MODERATION_ENDPOINT`,
`SAM3_ENDPOINT`, catalogue paths и data paths. `MATCHER_ENDPOINT` MUST оканчиваться на
`/v1/match`. Не добавляйте `.env` в Git.

```bash
set -a
. ./.env
set +a
uv run chto-za-vino-bot
```

## Проверка

```bash
# Matcher
python -m unittest discover -s matcher/tests -v

# Web UI
cd webui
npm run typecheck
npm test
npm run build

# Telegram-бот
cd ../telegram-bot
uv run ruff check .
uv run pytest -q
```

Подробности находятся в `matcher/README.md`, `webui/README.md` и
`telegram-bot/README.md`.
