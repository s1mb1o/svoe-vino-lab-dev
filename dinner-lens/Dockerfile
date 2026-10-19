# Build context: the committed dinner-lens/ directory. Data vectors are mounted at runtime.
FROM python:3.11-slim@sha256:e41613d42d4891e4930f79523f93f81bbc7632584ec65e36ab055f41a800b41e
ARG REVISION=unknown
LABEL org.opencontainers.image.title="svoe-vino-lab-dinner-lens" \
      org.opencontainers.image.revision="${REVISION}"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DINNER_LENS_CONFIG=/config/config.yaml
WORKDIR /app
COPY requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY pyproject.toml config.yaml /app/
COPY src/ /app/src/
COPY prompts/ /app/prompts/
COPY data/*.json /app/data/
# Dependency versions and build dependencies are already installed from the hash lock.
RUN pip install --no-deps --no-build-isolation . \
    && groupadd --gid 1000 dinner-lens \
    && useradd --uid 1000 --gid 1000 --no-create-home --shell /usr/sbin/nologin dinner-lens
USER 1000:1000
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/readyz', timeout=4)"]
CMD ["dinner-lens", "serve"]
