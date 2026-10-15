# Что за вино? — MAX bot

This project runs the MAX messenger bot «Что за вино?» with the nickname `@se14697933_bot`
(<https://max.ru/se14697933_bot>). It has the same functionality as the Telegram bot in
[`../telegram-bot`](../telegram-bot/README.md).

The bot accepts one wine photo or a MAX album.
It processes each photo as a separate request.
It returns one result per photo.
Each result contains a result photo, the wine name, producer, color, sugar class,
grape varieties, and the catalogue page on `vino-svoe.ru`.

The bot is a thin client of the matcher `svoe-vino-lab/matcher`.
The matcher returns the ranked candidates and the wine cards.
The bot does not read a local catalogue.

Read [the plan](docs/plans/01_max-port.md), [the decision record](docs/decisions/001-max-port.md),
and [the specification](docs/specification.md) before a change.

## What is the same as the Telegram bot

The processing core is a checked copy of the Telegram bot core: the work queue, moderation,
quality inspection, matcher client, wine cards, result photo, pipeline artifacts, HTTP API,
administration web interface, data lifecycle, artifact backfill, probe, and host demo.
`scripts/sync_shared.py` copies these modules from `../telegram-bot` and changes only the
names `chto_za_vino_bot`, `Telegram`, and `telegram`. `tests/test_shared_modules.py` fails
when a copy differs. Change the Telegram bot first, then run:

```bash
python scripts/sync_shared.py
```

The MAX-specific modules are:

| Module | Purpose |
|---|---|
| `max_api.py` | Thin async client of the MAX Bot API: auth, TLS trust, rate limits, retries, upload, download. |
| `updates.py` | Normalized `message_created`, `message_callback`, and `bot_started` updates. |
| `delivery.py` | Durable SQLite inbox, long polling, and the webhook receiver. |
| `app.py` | Handlers and the photo processor (the port of the Telegram `app.py`). |
| `storage.py` | The Telegram storage with MAX message IDs, photo locators, sent messages, and the inbox. |
| `config.py`, `profile.py`, `profile_sync.py` | MAX settings, texts, and the command menu. |

## User flow

The flow is the same as in the Telegram bot:

1. «Начать», `/start`, or a deep link shows the invitation, the data notice, the alcohol notice,
   and the buttons `Мне есть 18 лет` and `Мне нет 18 лет`.
2. An adult user sends a photo. The bot reserves one request in the rate window, records it,
   and adds it to the shared FIFO queue. The receipt shows the queue position and the wait.
3. A queue worker downloads the photo, moderates it with ShieldGemma 2, stores it, checks its
   quality with SAM3, and asks the matcher for four candidates.
4. The bot sends the result photo with the caption and the `Открыть страницу вина` button.
   A single photo also gets `✅ Совпало` and `❌ Не совпало`.
5. `❌ Не совпало` shows candidates 2 to 4 and `Ничего из этого`.
6. An unsafe photo gets the rejection illustration and `Сообщить об ошибке фильтра`.

## Platform differences

MAX is not Telegram. The bot keeps the behavior where the platform permits it.

| Topic | Telegram bot | MAX bot |
|---|---|---|
| Album | One message per photo with `media_group_id` | One message with two or more images or videos |
| Age-gate, rate-limit, or queue-capacity rejection of an album | One reply per photo | One reply per message. A moderation rejection still gives one illustration per photo |
| Private chat | Chat ID equals user ID | `chat_type == "dialog"`; the chat ID differs |
| Start | `/start` | `bot_started` («Начать», deep link) and the text `/start` |
| Privacy deep link | `t.me/ChtoZaVinoBot?start=privacy` | `max.ru/se14697933_bot?start=privacy` |
| Privacy answer | Constant text | The same text plus the user's own MAX user ID |
| Callback alert | `show_alert=True` dialog | A notification; MAX has no alert dialog |
| Keyboard edit | `edit_reply_markup` | `PUT /messages` with the stored text, the image token, and the new keyboard |
| Admin command menu | Scoped to the administrator's chat | Not shown; MAX has no command scope. The commands work |
| Bot description | `set_my_description` API | Bot card on business.max.ru, with moderation |
| Updates | Long polling | Webhook in production, long polling in development |
| API host trust | Public CA | Russian Trusted Root CA (Минцифры) for `platform-api2.max.ru` |

## MAX API notes

- Base URL: `https://platform-api2.max.ru`. The old host `platform-api.max.ru` is deprecated
  since 2026-07-19.
- The token goes in the header `Authorization: <token>`, without `Bearer`.
- `platform-api2.max.ru` presents a certificate of the Russian Trusted Sub CA. The package
  contains the public root certificate (`src/chto_za_vino_max_bot/certs/`). A test checks its
  SHA-256 fingerprint `D2:6D:2D:02:…:8E:CF:31`. The client adds this root to the public trust
  store. Do not disable TLS verification.
- Limits: 30 requests per second in total; 2 message operations per second in one chat;
  4000 characters of text; 12 images in one message.
- `PUT /messages`, `DELETE /messages`, and `POST /answers` can answer HTTP 200 with
  `success: false`. The client treats it as an error.
- A send is repeated only after HTTP 429, because the API has no idempotency key.

## Update delivery

MAX requires a webhook for production (<https://dev.max.ru/docs-api/methods/GET/updates>).

- `MAX_UPDATE_MODE=webhook` (the production default): the bot listens on
  `MAX_WEBHOOK_HOST:MAX_WEBHOOK_PORT`. A TLS proxy MUST publish it as `MAX_WEBHOOK_URL` on HTTPS
  port 443 with a certificate of a trusted CA or a Минцифры certificate. Self-signed
  certificates and plain HTTP are rejected by MAX. The receiver checks
  `X-Max-Bot-Api-Secret` and answers in milliseconds. At startup the bot subscribes the URL.
- `MAX_UPDATE_MODE=polling` (the development default): `GET /updates` with a persistent marker.
  The bot refuses to start when a webhook subscription is active. Production polling requires
  `MAX_ALLOW_PRODUCTION_POLLING=true`.

Both modes write each update to the SQLite table `update_inbox` before the bot handles it.
After a crash, the bot handles the stored updates again. Photo reservations are idempotent.

## Commands

| Command | Result |
|---|---|
| `/start` | Show the invitation and the data notice. |
| `/help` | Show photo tips. |
| `/stats` | Show personal statistics. Show aggregate statistics to the administrator. |
| `/privacy` | Show the short privacy notice and the user's MAX user ID. |
| `/users [page]` | Show a paginated user list to the administrator. |
| `/reset_limit [user_id or @username]` | Reset the current rate use for an administrator-selected user. |

The administrator commands work only for `BOT_ADMIN_USER_ID` in the administrator's dialog.
To find the MAX user ID, send `/privacy` to the bot.

## Configuration

The bot reads the service endpoints from `config.yaml`, the same as the Telegram bot.
Copy `.env.example` outside the repository and set the secrets there.

| Variable | Default |
|---|---|
| `MAX_BOT_TOKEN` | Required. business.max.ru → Чат-боты → ⋮ → Настройки. |
| `BOT_ADMIN_USER_ID` | Required MAX user ID. No default. |
| `BOT_ENVIRONMENT` | `production` |
| `MAX_API_BASE_URL` | `https://platform-api2.max.ru` |
| `MAX_API_CA_FILE` | Empty: the bundled Минцифры root. `none`: the public store only. |
| `MAX_MEDIA_ALLOWED_HOSTS` | Empty: any HTTPS host. Example: `oneme.ru,okcdn.ru`. |
| `MAX_UPDATE_MODE` | `webhook` in production, `polling` otherwise |
| `MAX_ALLOW_PRODUCTION_POLLING` | `false` |
| `MAX_POLL_TIMEOUT_SECONDS` | `30` (0 to 90) |
| `MAX_WEBHOOK_URL` | Required in webhook mode. HTTPS, no port. |
| `MAX_WEBHOOK_SECRET` | Required in webhook mode. 32 to 256 characters of `A-Za-z0-9_-`. |
| `MAX_WEBHOOK_HOST` / `MAX_WEBHOOK_PORT` | `127.0.0.1` / `28006` |
| `MAX_WEBHOOK_PATH` | The path of `MAX_WEBHOOK_URL` |
| `MAX_WEBHOOK_SUBSCRIBE` | `true` |
| `BOT_HTTP_API_PORT` | `28004` (the Telegram bot uses `28002`) |
| `BOT_ADMIN_WEB_PORT` | `28005` (the Telegram bot uses `28003`) |

All other `BOT_*` variables have the same meaning and defaults as in the Telegram bot.
`MAX_BOT_TOKEN`, `BOT_HTTP_API_TOKEN`, and `MAX_WEBHOOK_SECRET` MUST differ.

## Local run

```bash
uv sync --extra dev
cp .env.example ../../max-bot.env   # keep secrets outside the repository
set -a; . ../../max-bot.env; set +a
uv run chto-za-vino-max-bot
```

Other entry points: `chto-za-vino-max-admin`, `chto-za-vino-max-profile`,
`chto-za-vino-max-probe`, `chto-za-vino-max-artifacts`, `chto-za-vino-max-delete-user`,
`chto-za-vino-max-host-demo`.

## Verification

```bash
./scripts/verify.sh
```

The script checks the lock file, runs Ruff, checks the shared modules against `../telegram-bot`,
runs all tests, and runs the deterministic host demo.

## Deployment

Build the image from a committed revision (see [Dockerfile](Dockerfile)). One image runs two
containers: the bot and the administration interface. Use a separate data directory, for
example `/srv/svoe-vino-lab/prod/max-bot/data`, and a separate protected environment file.
In webhook mode, publish the container port `8081` only through the TLS proxy on port 443.

## Open items for the owner

1. A public HTTPS name on port 443 for the webhook, or an explicit decision to use long polling.
2. Platform requirements 2.1 and 3.1 (<https://dev.max.ru/docs/legal/requirements>): operator
   details and an explicit acceptance of the content rules by the user.
3. The contact `@s1mb1o` in the start and privacy texts is a Telegram username.
4. The bot card description on business.max.ru: at most 200 characters, no 18+ content.

## License

This project does not grant reuse or distribution rights. Read [LICENSE.md](LICENSE.md).
