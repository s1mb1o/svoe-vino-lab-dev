# Container image of the "Что за вино" Telegram bot and its administration interface.
#
# The build context is the repository root with im-core/ (the shared core) and telegram-bot/.
# Build from a committed revision, in the root of the repository:
#   REV=$(git rev-parse HEAD)
#   git archive "$REV" im-core telegram-bot | docker build -f telegram-bot/Dockerfile \
#     --build-arg REVISION="$REV" -t "svoe-vino-lab-telegram-bot:$REV" -
#
# One image runs two containers. Each container listens on its own port 8080:
#   chto-za-vino-bot    Telegram long polling and the recognition HTTP API (the default)
#   chto-za-vino-admin  the administration web interface
#
# Mount at run time:
#   /data  the bot data: bot.sqlite3, the accepted and quarantine images, the artifacts
#
# The environment file holds TELEGRAM_BOT_TOKEN, BOT_ADMIN_USER_ID, BOT_HTTP_API_TOKEN,
# BOT_ADMIN_WEB_PASSWORD, and the service endpoints. The image holds no secret.
# In the container, 127.0.0.1 is the container itself. Use the LAN address of gx10 in
# each model endpoint URL.

FROM ghcr.io/astral-sh/uv:0.8.14@sha256:f3660c56d5b08d6c516360981bedc439f499b9bf37f46a216018da3777a74011 AS uv

FROM python:3.12.14-slim-trixie@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f

ARG REVISION=unknown
LABEL org.opencontainers.image.title="svoe-vino-lab-telegram-bot" \
      org.opencontainers.image.revision="${REVISION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    PATH=/opt/venv/bin:$PATH \
    BOT_ENVIRONMENT=production \
    BOT_CONFIG=/app/config.yaml \
    BOT_DATA_ROOT=/data \
    BOT_REJECTION_IMAGE=/app/assets/content-rejected-monkey-640x640.png \
    BOT_HTTP_API_HOST=0.0.0.0 \
    BOT_HTTP_API_PORT=8080 \
    BOT_ADMIN_WEB_HOST=127.0.0.1 \
    BOT_ADMIN_WEB_PORT=8080

WORKDIR /app

COPY --from=uv /uv /uvx /bin/

# uv.lock pins every package. --frozen fails the build when the lock is out of date.
# The bot depends on ../im-core. --no-editable installs the core into /opt/venv, so the image
# needs /im-core only during the build.
COPY im-core /im-core
COPY telegram-bot/pyproject.toml telegram-bot/uv.lock telegram-bot/README.md telegram-bot/config.yaml ./
COPY telegram-bot/src ./src
RUN uv sync --frozen --no-editable

COPY telegram-bot/assets/content-rejected-monkey-640x640.png ./assets/

# uid 1000 is the owner of /srv/svoe-vino-lab on gx10, so the bind mount is writable.
RUN groupadd --gid 1000 bot \
    && useradd --uid 1000 --gid 1000 --no-create-home --shell /usr/sbin/nologin bot
USER 1000:1000

EXPOSE 8080

# The bot and the administration interface both answer GET /readyz on port 8080.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/readyz', timeout=4)"]

CMD ["chto-za-vino-bot"]
