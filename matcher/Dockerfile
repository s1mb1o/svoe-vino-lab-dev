# Container image of the svoe-vino-lab matcher service.
#
# The build context is the matcher/ directory. Build from a committed revision,
# in the root of svoe-vino-lab:
#   REV=$(git rev-parse HEAD)
#   git archive "$REV:matcher" | docker build --build-arg REVISION="$REV" \
#     -t "svoe-vino-lab-matcher:$REV" -
#
# Mounts at run time:
#   /config/config.yaml  the matcher configuration, read-only
#   /data                the data directory; the request archive is /data/requests
#
# The endpoints of the gx10 model services are optional environment variables:
# SIGLIP2_ENDPOINT, GROUNDING_DINO_ENDPOINT, SAM3_ENDPOINT, VLM_ENDPOINT, VLM_MODEL,
# QR_SCANNER_ENDPOINT. The image sets none of them.

FROM python:3.11-slim

ARG REVISION=unknown
LABEL org.opencontainers.image.title="svoe-vino-lab-matcher" \
      org.opencontainers.image.revision="${REVISION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SVOE_VINO_MATCHER_CONFIG=/config/config.yaml \
    SVOE_VINO_MATCHER_OUTPUT_DIR=/data/requests

WORKDIR /app

COPY requirements.txt matcher/requirements.txt
RUN pip install --no-cache-dir -r matcher/requirements.txt

# BuildKit does not apply .dockerignore to a tar context from stdin, so copy the
# service files by name. Add a COPY line for each new package directory or data file.
COPY *.py matcher/

# uid 1000 is the owner of /srv/svoe-vino-lab on gx10, so the bind mounts are writable.
RUN groupadd --gid 1000 matcher \
    && useradd --uid 1000 --gid 1000 --no-create-home --shell /usr/sbin/nologin matcher
USER 1000:1000

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4)"]

CMD ["python", "-m", "uvicorn", "matcher.app:app", "--host", "0.0.0.0", "--port", "8080"]
