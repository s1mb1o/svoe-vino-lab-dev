# Decision 016: Keep the bot on gx10

Date: 2026-09-28

## Context

The owner asked whether the bot can run on the Selectel VDS `avalon`.
`avalon` has 2 vCPU, 1.9 GiB RAM, no swap, and a 40 GB disk.
`avalon` already has a restricted SOCKS5-over-SSH tunnel to `cloudzy-ams` for `api.telegram.org:443`.
`avalon` already has a reverse tunnel from gx10 to `127.0.0.1:28000`.

The bot sends each photo to three services on gx10:

- ShieldGemma moderation through `llama-swap` on `127.0.0.1:18081`;
- SAM3 through `llama-swap` on `192.168.86.14:18081`;
- the matcher on `127.0.0.1:8158` with pipeline `rerank-siglip2-512-crop`.

## Options

### Run the bot on avalon and keep the models on gx10

The host resources are sufficient.
The bot needs a Telegram proxy option in `app.py` and the `aiohttp-socks` dependency.
The proxy port `1080` exists only on the Docker network `monitoring`.
The bot needs a container on that network or a published `127.0.0.1:1080` port.
The gx10 reverse tunnel needs new forwards for `18081` and `8158`.
The allowed listen ports of the `matcher-gx10` account were not checked.
The catalogue, the code map, and the rejection image need a copy on `avalon`.
The administration interface and the HTTP API become unavailable from the home LAN.

### Move the prod matcher to the real pipeline first

The reverse tunnel for `28000` exists.
The prod matcher on `28000` uses the mock pipeline `official-eval-mock` on 2026-09-28.
This option still needs a forward for `18081` and the Telegram proxy changes.

### Keep the bot on gx10

The bot works on gx10 now.
The home network reaches Telegram directly.
No code or network change is necessary.

## Decision

Keep the bot on gx10.

## Consequences

The bot stops when gx10 or the home network is unavailable.
A bot on `avalon` gives little more availability.
It cannot recognize a photo without gx10.
It can only report that the service is unavailable.
Examine the `avalon` options again if the bot must answer during a gx10 or home network failure.
