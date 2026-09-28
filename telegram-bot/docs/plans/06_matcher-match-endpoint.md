# 06 — Recognition through the matcher endpoint `/v1/match`

Date: 2026-09-28.
Status: implemented in commit `c0d483e` and deployed on gx10 on 2026-09-28.

Source: stage 3 of `svoe-vino-lab/workbench/docs/plans/74_match-endpoint.md`.
The owner messages are in `svoe-vino-lab/workbench/docs/owner-messages.md`,
from 2026-09-28T15:49:02+0300 to 2026-09-28T16:04:59+0300.

## Goal

The bot becomes a thin client of `svoe-vino-lab/matcher`.
The production bot sends each safely moderated photo to `POST /v1/match?k=4`.
Decision 018 permits an explicit bypass only for local development and tests.
The matcher returns the ranked candidates and a wine card for each candidate.
The bot does not read a local catalogue or a local wine code map.

## Owner decisions

1. The bot requests `k=4`.
2. The prod matcher on gx10 port 28000 runs its configured temporary pipeline.
3. The bot gets a new Docker deployment in `/srv/svoe-vino-lab/prod/telegram-bot`.
   The old systemd user services stop.
4. The owner allowed restarts. Nobody uses the services at the time of the change.

## Matcher contract

Request: `POST <MATCHER_ENDPOINT>?k=4`, multipart field `image`.
The request has no pipeline parameter. The matcher configuration selects the pipeline.

The bot reads these fields of the answer:

- `pipeline`: a non-empty string;
- `candidates`: a list of 0 to 4 objects;
- `candidates[].rank`: 1, 2, 3, 4 in order;
- `candidates[].slug`: a non-empty string, unique in the answer;
- `candidates[].score`: a finite number that does not increase from one rank to the next;
- `candidates[].wine`: the card with `name`, `page_url`, `producer`, `category`, `color`,
  `grapes`, `sugar`, `image_url`, and `qr_urls`.

The bot ignores other fields, for example `latency_ms` and `wine.region`.
An answer that breaks a rule fails closed: the request status is `recognition_failed`.

## Behavior

1. An empty `candidates` list gives the answer `Не уверен`. The status is `abstained`.
2. The confidence rule does not change: Top-1 score at least `BOT_MATCH_MIN_SCORE` and
   margin at least `BOT_MATCH_MIN_MARGIN`. One candidate has the margin 0.
3. The bot stores the card of each candidate in `request_candidates.wine_json`.
4. The negative feedback action reads the stored cards of ranks 2 to 4.
   It shows the available alternatives. It shows an alert only when no alternative exists.
5. A stored candidate without a card, from a request of the old version, gets a minimal
   card: `name` = slug and `page_url` = `https://vino-svoe.ru/wines/<slug>`.
6. The bot stores the pipeline name of the answer in `requests.matcher_pipeline`.
   The HTTP API returns this value in `matcher_pipeline`.
7. The thresholds stay 0.70 and 0.015. The calibration is in `ResearchLog.md`.

## Code changes

- `matcher.py`: the new request and the new answer parser.
- The local catalogue module becomes `wine.py`: the `Wine` card, its parser, and the minimal card.
  The catalogue loader, the QR URL normalization, and the sugar rules move to the matcher.
- `storage.py`: the columns `request_candidates.wine_json` and `requests.matcher_pipeline`,
  and an empty candidate list.
- `app.py`: no catalogue; the result card and the alternatives come from the candidates.
- `config.py`: no bot-owned pipeline, catalogue, or code-map settings.
  `MATCHER_ENDPOINT` MUST name the path `/v1/match`.
- `probe.py`: the new matcher client.
- `Dockerfile`: a new image for the bot and the administration interface.

## Deployment

The deployment document is `<workspace>/deploy/gx10/telegram-bot-prod.md`.

1. Deploy matcher commit `9ba496d` to prod 28000 with its configured pipeline.
2. Commit the bot. Build the image on gx10 from `git archive` of that commit.
3. Stop the old user services `chto-za-vino-bot` and `chto-za-vino-admin`.
4. Copy the data directory to `/srv/svoe-vino-lab/prod/telegram-bot/data`.
5. Start the Compose project. The bot HTTP API uses port 28002. The administration
   interface uses port 28003.
6. Check the HTTP API with a test photo, the administration interface, and the log of
   the Telegram polling.

## Tests

1. The parser accepts 0 to 4 valid candidates and rejects each broken rule.
2. The client sends `k=4` and no pipeline.
3. The processor stores the cards and the pipeline. An empty answer gives `abstained`.
4. The feedback action shows the stored cards.
5. The HTTP API returns the stored cards and the stored pipeline.
6. An old database gets the new columns.
7. `MATCHER_ENDPOINT` without `/v1/match` is rejected.
