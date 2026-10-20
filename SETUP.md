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
python -m uvicorn matcher.app:app --host 127.0.0.1 --port 8158
```

The mock configuration stores requests in `work/matcher-test-requests`.
Change `matcher.output_dir` in a private YAML copy to use another directory.

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
```

Перезапустите Web UI. Браузер продолжит вызывать route на origin Web UI.

## Local SigLIP2 matcher

The real matcher requires the committed bundle
`matcher/data/gx10-siglip2-so400m-patch16-naflex-p512` and an OpenAI-compatible SigLIP2 endpoint.
Read [bootstrap/README.md](bootstrap/README.md) to install the model services.

Run the commands from the repository root.
The [local example configuration](matcher/config.local.example.yaml) selects the gateway
`http://127.0.0.1:18090` and the archive directory `work/matcher-requests`.
For another gateway or archive directory, make a private YAML copy.
Change `pipeline[].endpoint` and `matcher.output_dir` in that copy.
The endpoint MUST be the gateway root without `/v1`.
Set `SVOE_VINO_MATCHER_CONFIG` to the selected YAML file.
`SIGLIP2_ENDPOINT` and `SVOE_VINO_MATCHER_OUTPUT_DIR` do not override YAML.

`SAM3_ENDPOINT` is the shared SAM3 override.
Shelf segmentation and optional hand selection require SAM3.
The local bootstrap gateway provides the following SAM3 route:

```bash
export SVOE_VINO_MATCHER_CONFIG=matcher/config.local.example.yaml
export SAM3_ENDPOINT=http://127.0.0.1:18090/upstream/sam3
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

## MAX-бот

```bash
cd max-bot
uv sync --extra dev
cp .env.example ../../max-bot.env
```

Задайте `MAX_BOT_TOKEN`, `BOT_ADMIN_USER_ID`, `BOT_HTTP_API_TOKEN`, endpoints и data paths.
Для production задайте webhook: `MAX_WEBHOOK_URL` (HTTPS, порт 443 через TLS proxy) и
`MAX_WEBHOOK_SECRET`. Не добавляйте файл окружения в Git.

```bash
set -a
. ../../max-bot.env
set +a
uv run chto-za-vino-max-bot
```

## Проверка

```bash
# Matcher
env -u SAM3_ENDPOINT python -m unittest discover -s matcher/tests -v

# Web UI
cd webui
npm run typecheck
npm test
npm run build

# Telegram-бот
cd ../telegram-bot
uv run ruff check .
uv run pytest -q

# MAX-бот
cd ../max-bot
./scripts/verify.sh
```

Подробности находятся в `matcher/README.md`, `webui/README.md` и
`telegram-bot/README.md`.
