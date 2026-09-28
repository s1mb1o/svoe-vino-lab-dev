# Decision 017: Recognition through the matcher endpoint `/v1/match`

Date: 2026-09-28

## Context

The bot sent each photo to the old matcher `svoe-vino-matcher` on `127.0.0.1:8158`.
The bot selected the pipeline `rerank-siglip2-512-crop` with `MATCHER_PIPELINE`.
The bot read the wine cards from a local catalogue file and a local wine code map.
The owner wants the bot to become a thin client of `svoe-vino-lab/matcher`.
The matcher has the endpoint `POST /v1/match` since commit `9ba496d` (plan 74).
The endpoint returns ranked candidates with a wine card for each candidate.

## Options

### Keep the old matcher and the local catalogue

This option keeps the pipeline `rerank-siglip2-512-crop`.
The bot keeps two copies of the catalogue data: its own file and the matcher data.
The catalogue version of the bot and of the matcher can differ.

### Add `/v1/match` to the old matcher

This option keeps the old pipeline.
It adds a second implementation of the same contract in another project.

### Use `/v1/match` of `svoe-vino-lab/matcher`

The matcher owns the catalogue data in its bundle.
The bot and the matcher always use the same catalogue version.
The prod pipeline is `siglip2-p512-as-is`. It has a lower accuracy than
`rerank-siglip2-512-crop` (see `ResearchLog.md`, 2026-09-28).

## Decision

Use `/v1/match?k=4` of `svoe-vino-lab/matcher` on the prod port 28000.
Do not send a pipeline name. The matcher configuration selects the pipeline.
Take the wine card of each candidate from the matcher answer.
Store the cards in `request_candidates.wine_json`.
Keep the thresholds 0.70 and 0.015.
Deploy the bot in Docker in `/srv/svoe-vino-lab/prod/telegram-bot`.

## Consequences

The bot has no local catalogue file and no local wine code map.
The QR URLs come from the lab database through the bundle: 37 wines instead of 3.
A request of the old version has no stored card. Its alternatives show the slug.
At the same thresholds, the lab run predicts fewer confident answers: about 59 % of the
positive photos instead of about 72 %, with a precision of about 0.91 in both cases.
A better matcher pipeline improves the bot without a bot change.
A rollback to the old matcher needs the previous bot image or the old systemd deployment.
