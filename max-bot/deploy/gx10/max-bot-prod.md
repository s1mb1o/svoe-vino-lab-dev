# MAX bot production deployment on gx10

This document describes the production deployment of the «Что за вино?» MAX bot
(`@se14697933_bot`). The approach is the same as for the Telegram bot
(`<workspace>/deploy/gx10/telegram-bot-prod.md`):

- One Docker image, built from a committed revision with `git archive`.
- Two containers from that image under Docker Compose: the bot and the administration interface.
- A protected environment file with the secrets. The image and git hold no secret.
- A bind-mounted data directory owned by uid 1000.

The MAX bot runs next to the Telegram bot and does not share data, ports, or secrets with it.

| Item | Telegram bot | MAX bot |
|---|---|---|
| Install directory | `/srv/svoe-vino-lab/prod/telegram-bot` | `/srv/svoe-vino-lab/prod/max-bot` |
| Environment file | `config/telegram-bot.env` | `config/max-bot.env` |
| Image | `svoe-vino-lab-telegram-bot:<revision>` | `svoe-vino-lab-max-bot:<revision>` |
| Recognition HTTP API | `28002` | `28004` |
| Administration interface | `28003` | `127.0.0.1:28005` (SSH tunnel) |
| Updates | Telegram long polling | MAX long polling (webhook later, port `28006`) |

The files of this directory:

- [`max-bot-prod.compose.yaml`](max-bot-prod.compose.yaml) — the Compose file.
- [`max-bot.env.example`](max-bot.env.example) — the template of the environment file.

## Requirements on gx10

- Docker Engine with the Compose plugin (`docker compose version`).
- Outbound HTTPS to `platform-api2.max.ru` and to the MAX media hosts. The image contains the
  Russian Trusted Root CA that `platform-api2.max.ru` needs. Do not add it to the host.
- The model services: ShieldGemma and SAM3 on `192.168.86.14:18081`, the matcher on
  `192.168.86.14:28000`.
- A deploy user with uid 1000 that can run Docker. uid 1000 owns `/srv/svoe-vino-lab`, and the
  containers run as uid 1000. Run the `docker compose` commands as this user.

## First installation

1. Make the directories. Give each one to uid 1000 explicitly: a directory that root owns
   stops the containers from writing the database.

   ```bash
   sudo install -d -o 1000 -g 1000 -m 0750 /srv/svoe-vino-lab/prod/max-bot
   sudo install -d -o 1000 -g 1000 -m 0750 /srv/svoe-vino-lab/prod/max-bot/data
   sudo install -d -o 1000 -g 1000 -m 0700 /srv/svoe-vino-lab/prod/max-bot/config
   ```

2. Copy the Compose file and the environment template from a checkout of the revision:

   ```bash
   cd /path/to/svoe-vino-lab
   sudo install -o 1000 -g 1000 -m 0640 max-bot/deploy/gx10/max-bot-prod.compose.yaml \
       /srv/svoe-vino-lab/prod/max-bot/compose.yaml
   sudo install -o 1000 -g 1000 -m 0600 max-bot/deploy/gx10/max-bot.env.example \
       /srv/svoe-vino-lab/prod/max-bot/config/max-bot.env
   ```

3. Edit `/srv/svoe-vino-lab/prod/max-bot/config/max-bot.env` with an editor. Set
   `MAX_BOT_TOKEN`, `BOT_ADMIN_USER_ID`, `BOT_HTTP_API_TOKEN`, and `BOT_ADMIN_WEB_PASSWORD`.
   Generate each random value separately, for example with `openssl rand -hex 32`.
   Write each secret between single quotes (`MAX_BOT_TOKEN='...'`): Compose expands `$NAME` in
   an unquoted value. Do not put a secret on a command line, because the shell history keeps it.

4. Check the permissions:

   ```bash
   stat -c '%a %u' /srv/svoe-vino-lab/prod/max-bot/config/max-bot.env   # 600 1000
   stat -c '%a %u' /srv/svoe-vino-lab/prod/max-bot/data                 # 750 1000
   ```

## Build and start a revision

Build the image from a committed revision, in the root of the repository:

```bash
cd /path/to/svoe-vino-lab
git fetch origin
REV=$(git rev-parse origin/feature/max-bot)
git archive "$REV:max-bot" | docker build --build-arg REVISION="$REV" \
    -t "svoe-vino-lab-max-bot:$REV" -
```

Select the image and start both containers:

```bash
cd /srv/svoe-vino-lab/prod/max-bot
echo "MAX_BOT_IMAGE=svoe-vino-lab-max-bot:$REV" > .env
docker compose up -d
docker compose ps
```

At the first start the bot creates `data/bot.sqlite3`, sets the command menu
(`BOT_SYNC_PROFILE=true`), checks that no webhook subscription is active, and starts long
polling.

## Verify

1. Both containers are `healthy`:

   ```bash
   docker compose ps
   ```

2. The bot reached MAX. The log contains `MAX bot connected bot_user_id=...` and
   `MAX bot and HTTP API started`. It contains no token:

   ```bash
   docker compose logs --tail 50 max-bot
   ```

3. Liveness and readiness of the recognition API:

   ```bash
   curl -fsS http://192.168.86.14:28004/healthz
   curl -fsS http://192.168.86.14:28004/readyz
   ```

4. In MAX, open `https://max.ru/se14697933_bot`, press «Начать», confirm the age, and send a
   wine photo. Follow `SMOKE_TESTS.md` for the complete check.

5. Open the administration interface through an SSH tunnel:

   ```bash
   ssh -N -L 28005:127.0.0.1:28005 gx10
   # then open http://127.0.0.1:28005/ on the operator computer
   ```

## Update and rollback

- Update: build the new revision, write its image name to `.env`, and run
  `docker compose up -d`. Compose recreates both containers. The bot finishes or restores the
  queued requests and continues long polling from the stored marker.
- Rollback: write the previous image name to `.env` and run `docker compose up -d`.
  Keep the image of the last good revision until the new one passes the smoke tests.
- A change of `config/max-bot.env` takes effect after `docker compose up -d`, which recreates
  the containers. `docker compose restart` does not read the file again.

## Operations

- Logs: `docker compose logs -f max-bot`. Docker keeps 5 files of 10 MB for each container.
- Stop: `docker compose stop`. The bot stops on SIGTERM and finishes cleanly.
- Token rotation: refresh the token on business.max.ru («Чат-боты → ⋮ → Настройки», the refresh
  icon), write it to `config/max-bot.env`, and run `docker compose up -d`.
- Backup: stop the bot or use `sqlite3 data/bot.sqlite3 ".backup ..."`, then copy `data/`.
  The data directory holds user photos. Keep its backup with the same protection.
- Retention: the bot deletes terminal request data after 30 days, at startup and once each day.

### Early deletion of the data of one user

The deletion command refuses a user with an active request (`received`, `queued`,
`processing`, or `retry_requested`). A stop during a photo job keeps the status of the job.

1. Count the active requests of the user. Continue only when the count is `0`:

```bash
docker compose run --rm --no-deps -T max-bot python - USER_ID <<'PY'
import sqlite3, sys
active = ("received", "queued", "processing", "retry_requested")
print(sqlite3.connect("/data/bot.sqlite3").execute(
    "SELECT COUNT(*) FROM requests WHERE user_id = ? AND status IN (?, ?, ?, ?)",
    (int(sys.argv[1]), *active),
).fetchone()[0])
PY
```

2. Stop the bot, delete the data, and start the bot:

```bash
docker compose stop max-bot
docker compose run --rm --no-deps max-bot chto-za-vino-max-delete-user USER_ID --confirm
docker compose start max-bot
```

If the deletion command reports active requests, start the bot, wait until the requests finish
(the administration interface shows their status), and repeat from step 1.

## Switch to a webhook later

MAX recommends a webhook for production. The switch needs a public HTTPS name on port 443 with a
certificate of a trusted CA or a Минцифры certificate, and a TLS proxy that forwards the webhook
path to gx10.

1. Uncomment `127.0.0.1:28006:8081` in `compose.yaml`, and point the TLS proxy at that port.
2. Set `updates.mode: webhook` in `config.yaml`. The image has `/app/config.yaml`: rebuild the
   image, or mount another file and name it with `BOT_CONFIG`. In `config/max-bot.env`, set
   `MAX_WEBHOOK_URL` and a separate random `MAX_WEBHOOK_SECRET` (32 to 256 characters of
   `A-Za-z0-9_-`). The switch is issue #23.
3. Run `docker compose up -d`. The bot subscribes the URL at startup.
4. To go back to long polling, delete the subscription first (`DELETE /subscriptions?url=...`).
   The bot refuses to start long polling while a subscription is active.

## Security notes

- The environment file has mode `0600`. The image, git, and the logs hold no secret.
- The administration interface listens on the host loopback interface only.
- The recognition API accepts only `BOT_HTTP_API_ALLOWED_NETWORKS` and a bearer token.
  Requests from gx10 itself can arrive from the Docker bridge address; use the LAN address
  `192.168.86.14` or add the bridge network to the list.
- Both containers run as uid 1000 with a read-only root file system, no capabilities, and
  `no-new-privileges`. Only `/data` and a `/tmp` tmpfs are writable.
