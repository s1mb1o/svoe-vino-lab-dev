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
# QR_SCANNER_ENDPOINT. The image sets none of them. The siglip2 pipeline reads the
# variable of its endpoint field.
#
# The image holds no embedding bundle. Mount the bundle read-only at the path of the
# bundle field; a relative path resolves against /app, for example
# /app/matcher/data/<bundle>.

FROM python:3.11-slim@sha256:e41613d42d4891e4930f79523f93f81bbc7632584ec65e36ab055f41a800b41e

ARG REVISION=unknown
LABEL org.opencontainers.image.title="svoe-vino-lab-matcher" \
      org.opencontainers.image.revision="${REVISION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SVOE_VINO_MATCHER_CONFIG=/config/config.yaml \
    SVOE_VINO_MATCHER_OUTPUT_DIR=/data/requests

WORKDIR /app

COPY requirements.txt requirements.lock matcher/
RUN pip install --no-cache-dir --require-hashes -r matcher/requirements.lock

# BuildKit does not apply .dockerignore to a tar context from stdin, so copy the
# service files by name. Add a COPY line for each new package directory or data file.
COPY *.py matcher/

# uid 1000 is the owner of /srv/svoe-vino-lab on gx10, so the bind mounts are writable.
RUN groupadd --gid 1000 matcher \
    && useradd --uid 1000 --gid 1000 --no-create-home --shell /usr/sbin/nologin matcher
USER 1000:1000

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=20s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/readyz', timeout=18)"]

CMD ["python", "-m", "uvicorn", "matcher.app:app", "--host", "0.0.0.0", "--port", "8080"]
