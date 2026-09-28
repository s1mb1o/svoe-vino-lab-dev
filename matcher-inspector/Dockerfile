# Read-only web interface for the matcher request archive and embedding bundles.
# Build context: matcher-inspector/

FROM python:3.11-slim

ARG REVISION=unknown
LABEL org.opencontainers.image.title="svoe-vino-lab-matcher-inspector" \
      org.opencontainers.image.revision="${REVISION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MATCHER_INSPECTOR_REQUESTS_ROOT=/data/requests \
    MATCHER_INSPECTOR_BUNDLE_ROOT=/data \
    MATCHER_INSPECTOR_PORT=8080

WORKDIR /app
COPY app.py /app/app.py

RUN groupadd --gid 1000 inspector \
    && useradd --uid 1000 --gid 1000 --no-create-home --shell /usr/sbin/nologin inspector
USER 1000:1000

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4)"]

CMD ["python", "/app/app.py"]
