# Container image of the «Винный дневник» account service.
#
# Build from a committed revision, in the root of the repository:
#   REV=$(git rev-parse HEAD)
#   git archive "$REV" account | docker build -f account/Dockerfile \
#     --build-arg REVISION="$REV" -t "svoe-vino-lab-account:$REV" -
#
# Mount at run time:
#   /data  account.sqlite3
#
# The environment file holds the consumer tokens, ACCOUNT_CODE_KEY, the SMTP and Yandex ID
# credentials, and MAX_WEBAPP_KEY. The image holds no secret.

FROM ghcr.io/astral-sh/uv:0.8.14@sha256:f3660c56d5b08d6c516360981bedc439f499b9bf37f46a216018da3777a74011 AS uv

FROM python:3.12.14-slim-trixie@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f

ARG REVISION=unknown
LABEL org.opencontainers.image.title="svoe-vino-lab-account" \
      org.opencontainers.image.revision="${REVISION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    PATH=/opt/venv/bin:$PATH \
    ACCOUNT_ENVIRONMENT=production \
    ACCOUNT_DATABASE=/data/account.sqlite3 \
    ACCOUNT_HOST=0.0.0.0 \
    ACCOUNT_PORT=8080

WORKDIR /app

COPY --from=uv /uv /uvx /bin/

# uv.lock pins every package. --frozen fails the build when the lock is out of date.
COPY account/pyproject.toml account/uv.lock account/README.md ./
COPY account/src ./src
RUN uv sync --frozen --no-editable

# The container runs as uid 1000. The bind-mounted data directory must be writable for uid 1000.
RUN groupadd --gid 1000 account \
    && useradd --uid 1000 --gid 1000 --no-create-home --shell /usr/sbin/nologin account
USER 1000:1000

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/readyz', timeout=4)"]

CMD ["chto-za-vino-account"]
