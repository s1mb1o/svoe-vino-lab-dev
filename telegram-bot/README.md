# Что за вино?

This project runs the Telegram bot at [@ChtoZaVinoBot](https://t.me/ChtoZaVinoBot).
The bot accepts one wine photo or a Telegram photo album.
It processes each photo as a separate request.
It returns one result per photo.
Each result contains a result photo, the wine name, producer, color, sugar class,
grape varieties, and the catalogue page on `vino-svoe.ru`.

The bot runs on `gx10` in Docker with Telegram long polling.
The bot does not need a public inbound port.
The private administration interface listens behind a TLS proxy or a secure tunnel.
The authenticated internal recognition API listens on port `28002`.
The bot is a thin client of the matcher `svoe-vino-lab/matcher`.
The matcher returns the ranked candidates and the wine cards.
The bot does not read a local catalogue.

## Age confirmation

The `/start` command asks the user to confirm an age of at least 18 years.
The bot stores the selected answer in SQLite.
The bot does not accept a photo before the adult confirmation.
An unconfirmed photo does not use the rate limit.
The bot does not perform identity or document verification.
The confirmation screen and each successful result show the alcohol notice.

## Request flow

1. The bot reserves one request in the user rate window.
2. The bot records the request in SQLite.
3. The bot adds the request to the shared FIFO queue.
4. A queue worker downloads the Telegram photo into memory.
5. The worker validates and normalizes a moderation copy in memory.
6. In production, `shieldgemma-2-4b-it` classifies the moderation copy
   through a multipart request.
7. The production bot fails closed if moderation fails.
8. The bot writes a safe image under `accepted`.
9. The bot writes an unsafe image under `quarantine`.
10. The bot creates an irreversible blurred administration preview for an unsafe image.
11. The bot replies with the rejection illustration for an unsafe image.
12. Pillow measures blur and glare.
13. SAM3 checks for a wine bottle and a usable label.
14. The bot stores quality results as advisory metadata.
15. SAM3 returns full-size masks for the bottle and label prompts.
16. The bot stores safe pipeline artifacts for the administration inspector.
17. The bot continues to recognition when the quality check or artifact generation fails.
18. The bot sends an image that passed moderation to `POST /v1/match?k=4` of the matcher.
    A non-production test can use the explicit moderation bypass.
19. The matcher returns up to four ranked candidates with scores and wine cards.
20. The bot answers `Не уверен` when no candidate exists, or when the Top-1 score or the
    score margin is too low.
21. The bot takes the wine parameters and the official image URL from the wine card.
22. The bot downloads and normalizes the official result image.
23. The bot detects the bottle area from transparency or a white background.
24. The bot fits the complete bottle on a white 4:5 canvas with 5% padding.
25. The bot uses the submitted accepted photo when the official image is unavailable.
26. The bot sends the result as a Telegram photo with a caption and a URL button.
27. The bot records the request result and image hashes in SQLite.
28. A successful single-photo result shows match feedback buttons.
29. A negative feedback action shows three alternatives and `Ничего из этого`.
30. The bot stores the first feedback value from the source user.
31. The bot stores the queue wait and main step durations in `request_step_timings`.
32. The service journal records the request ID, step, duration, and outcome.

Telegram sends each photo in an album as a separate update.
The bot handles updates in order and adds each photo to the shared FIFO queue.
The bot sends one editable queue receipt for the complete album.
The receipt shows the initial queue position and approximate wait.
Each result replies to its source photo.
Album results do not show feedback buttons.

The default queue has one worker and a total capacity of 100 jobs.
The bot continues to accept commands and new updates while the worker is busy.
The bot restores requests with `received`, `queued`, or `processing` status after a restart.

## Commands

| Command | Result |
|---|---|
| `/start` | Show the invitation and the data notice. |
| `/help` | Show photo tips. |
| `/stats` | Show personal statistics. Show aggregate statistics to the administrator. |
| `/privacy` | Show the short privacy notice. |
| `/users [page]` | Show a paginated user list to the administrator. |
| `/reset_limit [user_id or @username]` | Reset the current rate use for an administrator-selected user. |

The administrator commands work only for the explicitly configured `BOT_ADMIN_USER_ID`
in its private chat. The bot refuses to start when this value is absent.
`/reset_limit` without an argument resets the administrator's own limit.
A limit reset preserves request history and statistics.

## Administration web interface

The administration interface is a separate FastAPI service.
Keep it on loopback and use an SSH tunnel, or put it behind an HTTPS reverse proxy.
Do not send the HTTP Basic password over a shared plain-HTTP network.
The browser asks for the configured HTTP Basic username and password.

The interface shows these pages:

- Aggregate statistics and recent requests.
- Users and their current rate-limit use.
- Recent requests with optional status filtering.
- One request with timings, moderation, quality, candidates, feedback, and visual artifacts.
- Moderation filter error reports.

The interface can reset one user's rate limit.
The interface can request a retry only for a previously accepted request.
The bot receives the retry through SQLite and sends it through the shared FIFO queue.
The bot runs moderation again before recognition when moderation is enabled.

The request inspector shows the exact matcher input, the moderation image, SAM3 masks,
the combined mask overlay, bottle and label crops, masked cutouts, and the Telegram result image.
The interface serves full-fidelity artifacts only for a request with a current safe
moderation result or an explicit non-production moderation bypass.
For a quarantined request, the interface shows one irreversible server-side blurred preview.
The preview is reduced to 24 pixels on its longest side before enlargement and Gaussian blur.
The interface does not serve accepted source files or quarantine images directly.
The service rejects addresses outside `BOT_ADMIN_WEB_ALLOWED_NETWORKS`.
A non-loopback listener requires `BOT_ADMIN_WEB_BEHIND_TLS_PROXY=true`.
This flag is an operator assertion. The proxy MUST terminate TLS and MUST be the only
published route to the application container.

## HTTP recognition API

The bot process provides a synchronous API for internal tests.
The API uses the same FIFO queue and the same processing pipeline as Telegram requests.
The API requires `Authorization: Bearer <BOT_HTTP_API_TOKEN>`.
The token MUST contain at least 32 characters and MUST differ from the Telegram token.
The API applies a per-client request limit and a global in-flight request limit before it reads
the upload body. These limits protect the shared Telegram queue.
The service rejects addresses outside `BOT_HTTP_API_ALLOWED_NETWORKS`.
Do not expose the recognition API port `28002` to WAN.

Send one image in the multipart `image` field:

```bash
curl -sS \
  -H "Authorization: Bearer $BOT_HTTP_API_TOKEN" \
  -F "image=@wine.jpg" \
  http://192.168.86.14:28002/api/v1/recognize
```

The request waits for queue processing to finish.
The JSON response contains the request status, moderation result, quality metadata,
wine parameters, up to four ranked candidates, matcher pipeline, and step timings.
The moderation object contains `performed`, `bypassed`, and nullable `safe` fields.
An explicit bypass gives `performed=false`, `bypassed=true`, and `safe=null`.
When the matcher wine card has QR URLs, the selected wine and its candidate
object also contain `qr_urls`.
The response omits `qr_urls` when no valid URL exists.
An unsafe response has status `quarantined` and does not expose the source image.
OpenAPI is available at `http://192.168.86.14:28002/openapi.json`.
Swagger UI is available at `http://192.168.86.14:28002/docs`.
`GET /healthz` is a process liveness check. `GET /readyz` also checks the database,
queue, and TCP reachability of the configured model services.
The API accepts JPEG, PNG, and WebP images. It preserves the source format in storage and
in the matcher multipart request.

Reconstruct artifacts for one previously safe or quarantined request without Telegram output:

```bash
uv run chto-za-vino-artifacts REQUEST_ID
```

The public privacy deep link is
`https://t.me/ChtoZaVinoBot?start=privacy`.
Use this URL in the BotFather Privacy Policy field.

## Configuration

The bot reads the service endpoints from `config.yaml` in its working directory.
Set `BOT_CONFIG` to use a different file.
Each endpoint MUST be an HTTP(S) URL or an exact `"{env:NAME}"` reference.
An environment reference reads the named variable when the bot starts.

The default [config.yaml](config.yaml) contains these entries:

```yaml
moderation:
  enabled: true

endpoints:
  moderation: "{env:MODERATION_ENDPOINT}"
  sam3: "{env:SAM3_ENDPOINT}"
  matcher: "{env:MATCHER_ENDPOINT}"
```

Production MUST keep `moderation.enabled` set to `true`.
Local development and tests MAY set it to `false` to bypass ShieldGemma. The bot then does
not resolve `endpoints.moderation` and does not send a moderation request. It accepts each
valid image for recognition. It stores `disabled` as the moderation category and stores no
safety verdict. The default is `true`.

Copy `.env.example` outside the repository or use a deployment environment file.
Set the three endpoint variables, `TELEGRAM_BOT_TOKEN`, `BOT_ADMIN_USER_ID`, and
`BOT_HTTP_API_TOKEN` in that protected file.
`MODERATION_ENDPOINT` is not required when moderation is disabled.
Do not commit the token.

The example environment uses these service endpoints for `gx10`:

| Variable | Example or default |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Required secret from BotFather. No default. |
| `BOT_CONFIG` | `config.yaml` |
| `BOT_ENVIRONMENT` | `production` |
| `MODERATION_ENDPOINT` | `http://127.0.0.1:18081/upstream/shieldgemma-2-4b-it/classify` |
| `SAM3_ENDPOINT` | `http://192.168.86.14:18081/upstream/sam3` |
| `MATCHER_ENDPOINT` | `http://192.168.86.14:28000/v1/match` |
| `BOT_DATA_ROOT` | `data` for a bare process; `/data` in the image. |
| `BOT_DATABASE` | `<BOT_DATA_ROOT>/bot.sqlite3` |
| `BOT_REJECTION_IMAGE` | `assets/content-rejected-monkey-640x640.png` |
| `BOT_ADMIN_USER_ID` | Required Telegram user ID. No default. |
| `BOT_DATA_RETENTION_DAYS` | `30`; production requires this value. |
| `BOT_RATE_LIMIT` | `50` |
| `BOT_RATE_WINDOW_SECONDS` | `3600` |
| `BOT_QUEUE_WORKERS` | `1` |
| `BOT_QUEUE_CAPACITY` | `100` |
| `BOT_QUEUE_ESTIMATE_SECONDS` | `20` |
| `BOT_MAX_IMAGE_BYTES` | `20971520` |
| `BOT_MATCH_MIN_SCORE` | `0.70` |
| `BOT_MATCH_MIN_MARGIN` | `0.015` |
| `BOT_QUALITY_BLUR_MIN_VARIANCE` | `80` |
| `BOT_QUALITY_GLARE_MAX_RATIO` | `0.20` |
| `BOT_QUALITY_BOTTLE_MIN_AREA_RATIO` | `0.10` |
| `BOT_QUALITY_LABEL_MIN_AREA_RATIO` | `0.015` |
| `BOT_SYNC_PROFILE` | `true` |
| `BOT_LOG_LEVEL` | `INFO` |
| `BOT_ADMIN_WEB_USERNAME` | `admin` |
| `BOT_ADMIN_WEB_PASSWORD` | Required strong random secret. No default. |
| `BOT_ADMIN_WEB_HOST` | `127.0.0.1` |
| `BOT_ADMIN_WEB_PORT` | `28003` |
| `BOT_ADMIN_WEB_ALLOWED_NETWORKS` | `127.0.0.1/32,::1/128` |
| `BOT_ADMIN_WEB_BEHIND_TLS_PROXY` | `false` |
| `BOT_HTTP_API_HOST` | `127.0.0.1` |
| `BOT_HTTP_API_PORT` | `28002` |
| `BOT_HTTP_API_ALLOWED_NETWORKS` | `127.0.0.1/32,::1/128,192.168.86.0/24` |
| `BOT_HTTP_API_TOKEN` | Required random secret of at least 32 characters. |
| `BOT_HTTP_API_RATE_LIMIT` | `10` |
| `BOT_HTTP_API_RATE_WINDOW_SECONDS` | `3600` |
| `BOT_HTTP_API_MAX_IN_FLIGHT` | `2` |

`endpoints.matcher` MUST name the matcher path `/v1/match`.
The bot refuses to start with another path, for example `/v1/not-match`.
The bot sends `k=4` and no pipeline name. The matcher configuration selects the pipeline.

The bare-process defaults use the production ports `28003` and `28002`.
The Docker image sets `BOT_DATA_ROOT=/data`, `BOT_REJECTION_IMAGE`, and the recognition API
to `0.0.0.0:8080`. The administration interface stays on loopback by default. A deployment can
set its listener to `0.0.0.0:8080` only behind its TLS proxy and with
`BOT_ADMIN_WEB_BEHIND_TLS_PROXY=true`. In a container, `127.0.0.1` is the container itself, so
the deployment sets each model endpoint to the LAN address of `gx10`.

Set `BOT_ADMIN_WEB_PASSWORD` to a strong random value.
The administration service refuses to start without this value.

Production refuses to start when moderation is disabled. Local development and tests must set
`BOT_ENVIRONMENT=development` or `BOT_ENVIRONMENT=test` before they use the explicit bypass.

## Data lifecycle

Production keeps request data for 30 days. The bot removes expired terminal requests, source
images, artifacts, and inactive user profiles at startup and once each day. Active requests are
not deleted.

Stop the bot before an early user-requested deletion. Then run:

```bash
uv run chto-za-vino-delete-user TELEGRAM_USER_ID --confirm
```

The command deletes the user's request rows, source images, pipeline artifacts, and profile.

## Local verification

Run the complete local verification entry point:

```bash
./scripts/verify.sh
```

The script checks the lock file, installs the development extra, runs Ruff, runs all tests,
and runs the deterministic host demo. A CI service can use the same entry point.

The equivalent individual commands start with:

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest -q
```

Run the deterministic host demo without Telegram, model services, or the private LAN:

```bash
uv run chto-za-vino-host-demo
```

The command exercises the production request builders, response parsers, confidence logic,
and catalogue-card validation with local deterministic responses. It returns one recognized
demonstration wine as JSON.

Run the same host demo in the pinned container without runtime network access:

```bash
docker compose -f compose.host-demo.yaml up --build \
  --abort-on-container-exit --exit-code-from host-demo
```

Start the bot only after you set a valid token:

```bash
set -a
. ./.env
set +a
uv run chto-za-vino-bot
```

Start the administration interface only after you set its password:

```bash
uv run chto-za-vino-admin
```

Probe the live local services without a Telegram token:

```bash
uv run chto-za-vino-probe ./safe-wine-photo.jpg
```

## Deployment

The bot runs in Docker on `gx10` since 2026-09-28.
The deployment document is `<workspace>/deploy/gx10/telegram-bot-prod.md`.
The image comes from [Dockerfile](Dockerfile). Build it from a committed revision.
One image runs two containers: the bot and the administration interface.
The data directory is `/srv/svoe-vino-lab/prod/telegram-bot/data`.
The protected environment file is
`/srv/svoe-vino-lab/prod/telegram-bot/config/telegram-bot.env`.

Production uses Docker Compose only. This project contains no systemd service units.

## License

This project does not grant reuse or distribution rights. Read [LICENSE.md](LICENSE.md).
The project owner must select another license before an event or distributor requires one.

Read [the specification](docs/specification.md), [the privacy policy](PRIVACY.ru.md),
and [the smoke tests](SMOKE_TESTS.md).
