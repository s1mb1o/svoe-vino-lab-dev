# Matcher Inspector

Matcher Inspector is a separate read-only web service for `svoe-vino-lab/matcher`.
It has no authentication.
Expose it only on the trusted LAN.

The service shows:

- the latest matcher request journals;
- each archived input image;
- the complete `request.json` content;
- each installed embedding bundle below the data directory;
- the model, views, vector shape, wine count, installed size, and complete manifest of each bundle;
- missing bundle payload files and payload size mismatches.

The service does not use the Docker socket.
It does not show the matcher process stdout or stderr.
It reads the structured request journals that the matcher saves beside each image.

## Data layout

Mount the matcher data directory at `/data` in read-only mode.
The default request archive is `/data/requests`.
The service scans `/data` for a `manifest.json` with format
`svoe-vino-matcher-bundle`.
It skips the request archive during this scan.

The scanner does not follow symbolic links.
The viewer does not create or modify a file in `/data`.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `MATCHER_INSPECTOR_REQUESTS_ROOT` | `/data/requests` | Matcher request archive. |
| `MATCHER_INSPECTOR_BUNDLE_ROOT` | `/data` | Root for embedding bundle discovery. |
| `MATCHER_INSPECTOR_PORT` | `8080` | Container HTTP port. |

## Run without Docker

Run this command from `matcher-inspector/`:

```bash
MATCHER_INSPECTOR_REQUESTS_ROOT=../work/matcher-requests \
MATCHER_INSPECTOR_BUNDLE_ROOT=../matcher/data \
MATCHER_INSPECTOR_PORT=8080 \
python app.py
```

Open `http://127.0.0.1:8080`.
The health endpoint is `GET /healthz`.

## Build the image

Run these commands from the root of `svoe-vino-lab`:

```bash
REV=$(git rev-parse HEAD)
git archive "$REV:matcher-inspector" | docker build \
  --build-arg REVISION="$REV" \
  -t "svoe-vino-lab-matcher-inspector:$REV" -
```

The GX10 Compose files publish prod on port `28001` and dev on port `29001`.

## Test

Run this command from `matcher-inspector/`:

```bash
python -m unittest discover -s tests -v
```
