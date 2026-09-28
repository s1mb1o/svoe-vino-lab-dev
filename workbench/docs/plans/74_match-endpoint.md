# 74 — Extended matcher endpoint `/v1/match`

Date: 2026-09-28.
Status: stages 1 and 2 are in commit `9ba496d`. Stage 3 (bot) is in commit `c0d483e`
(plan `telegram-bot/docs/plans/06_matcher-match-endpoint.md`). The prod matcher and the
bot run on gx10 since 2026-09-28.

## Goal

Add the endpoint `POST /v1/match` to the matcher service in `svoe-vino-lab/matcher/`.
The endpoint returns ranked candidates with a wine card for each candidate.
`telegram-bot` uses this endpoint. The owner wants the bot to become a thin client.
The endpoint `POST /v1/eval/predict` keeps the hackathon contract `{"slug": "..."}`.
This plan does not change `/v1/eval/predict`.

## Base

The commits `15a10d8` and `d8955b1` on `main` added the backend `siglip2`.
The session `drink-atlas-workspace-a0` reported this change on 2026-09-28.

- `matcher/config.yaml` selects the pipeline `siglip2-p512-as-is`.
- `matcher/tests/config.yaml` selects the mock pipeline `official-eval-mock`.
- `matcher/service.py` has `MockMatcher` and `Siglip2Matcher`. Both have `predict(image)`.
- `matcher/siglip2.py` embeds the photo through `<SIGLIP2_ENDPOINT>/v1/embeddings`.
- `matcher/bundle.py` has `Bundle.top1(view, query)`. It takes the maximum cosine of
  each wine in the view `full`. Equal cosines go to the smallest slug.
- The bundle `matcher/data/gx10-siglip2-so400m-patch16-naflex-p512` is not in git.
  It has format version 1 and 2,094 wines.
- `workbench/pipeline/matcher_bundle.py` builds and validates the bundle (plan 72).

## Owner decisions

The owner gave these answers on 2026-09-28. The text is in `docs/owner-messages.md`.

1. The response contains the candidates and a wine card for each candidate.
2. The default of `k` is 20.
3. When fewer than `k` candidates exist, the response contains the available candidates.
4. The service uses only the pipeline that `config.yaml` selects.
   The request has no pipeline parameter.
5. The wine card comes from the bundle.
6. For a known mock image, rank 1 is the configured slug. Ranks 2 to `k` are random
   bundle wines.
7. For an unknown mock image, the response contains `k` random bundle wines.
8. The service skips a candidate that has no wine card.

## Request

- Method and path: `POST /v1/match`.
- Body: multipart field `image`. The rules are the same as for `/v1/eval/predict`.
- Query parameter `k`: an integer from 1 to 20. The default is 20.
- A `k` value outside the range gives HTTP 422.
- Authorization: `Authorization: Bearer <token>` when `matcher.token` is configured.
- The size limits, the pixel limit, the upload timeout, and the request queue are the
  same as for `/v1/eval/predict`.
- The request archive records each request. The record contains the candidate slugs.

## Response

HTTP 200:

```json
{
  "pipeline": "siglip2-p512-as-is",
  "latency_ms": 812.5,
  "candidates": [
    {
      "rank": 1,
      "slug": "massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16",
      "score": 0.83,
      "wine": {
        "name": "...",
        "page_url": "https://vino-svoe.ru/wines/...",
        "producer": "...",
        "category": "...",
        "region": "...",
        "color": "...",
        "grapes": "...",
        "sugar": "Сладкое",
        "image_url": "https://api.vino-svoe.ru/...",
        "qr_urls": []
      }
    }
  ]
}
```

Rules:

1. `rank` starts at 1 and increases by 1.
2. `score` is a finite number. `score` does not increase from one rank to the next.
3. Each `slug` occurs one time in the response.
4. The number of candidates is from 0 to `k`.
5. An empty `candidates` list means that no match exists.
6. `wine.name` and `wine.page_url` are always strings.
7. `producer`, `category`, `region`, `color`, `grapes`, `sugar`, and `image_url` are a
   string or `null`. The lab database fills the first four for every wine.
8. `qr_urls` is a list of normalized HTTP or HTTPS URLs. The list can be empty.
9. `pipeline` is the name of the selected pipeline.
10. `latency_ms` is the processing time of the request in milliseconds.

A pipeline without a card source gives HTTP 503 for `/v1/match`.
Examples: a bundle of format version 1, or a mock pipeline without a bundle.
`/v1/eval/predict` continues to work. The hackathon image does not need a card source.

## Card source: bundle format version 2

### Builder and validator in `workbench/pipeline/matcher_bundle.py`

1. `FORMAT_VERSION` becomes 2. The builder writes version 2 only.
2. The validator accepts version 1 and version 2.
3. A version 2 `wines.jsonl` record has these keys:
   `wine_slug`, `name`, `producer`, `category`, `region`, `color`, `grapes`,
   `page_url`, `image_url`, and `qr_urls`.
4. `color` and `grapes` come from `wine_catalog`. `grapes` can be `null`.
5. `page_url` is `https://vino-svoe.ru/wines/<slug>`.
   All 2,103 records of the hackathon `catalog.jsonl` use this form.
6. `image_url` is `https://api.vino-svoe.ru/v1/img/str-api/1920/1920/resize/uploads/`
   plus `wine_image.source_name` of the image type `main`. It is `null` when the wine
   has no `main` image.
7. `qr_urls` comes from `wine_code` with `kind = 'qr_url'`. The builder normalizes and
   sorts the values with the rules of the bot. `lab.sqlite3` has QR URLs for 37 wines.
   The bot code map has them for 3 wines.
8. The vectors, the items, and the candidates do not change.
   `/v1/eval/predict` gives the same answers with the new bundle.

The check of 2026-09-28 compared `lab.sqlite3` with the hackathon `catalog.jsonl`.
`name`, `color`, and `grapes` are equal for all common wines.
The `main` image name differs for 15 wines. All 15 lab image URLs gave HTTP 200.
Five of the 15 catalogue image URLs gave HTTP 400.

### Reader in `matcher/bundle.py`

1. `load_bundle` accepts version 1 and version 2.
2. For version 2, `load_bundle` reads `wines.jsonl` into the wine cards.
3. The matcher computes `sugar` from the slug and the name with the rules of the bot.
4. For version 1, the bundle has no cards.

### Rebuild of the real bundle

1. Rename the old directory to
   `matcher/data/gx10-siglip2-so400m-patch16-naflex-p512.v1` as a backup.
2. Build version 2 at the original path. `matcher/config.yaml` does not change.
3. Validate the new bundle.
4. Compare the payloads. `vectors.npy`, `items.jsonl`, `candidates.jsonl`, and
   `omissions.jsonl` MUST be byte-identical. Then `/v1/eval/predict` cannot change.
   The result of 2026-09-28: all four files are identical. For 300 query vectors,
   `top1` of the old and the new bundle agreed 300 times.

## Ranked interface of the backends

Each matcher class gets the method `match(image, k)`.
The method returns a list of `(slug, score)` pairs in rank order.
The service skips a slug without a card. The ranks of the remaining candidates are
consecutive. `predict(image)` stays. Its result MUST NOT change.

### Backend `siglip2`

1. Add `Bundle.ranked(view, query)`. It returns all wines in rank order.
2. `ranked` uses the same maximum per wine as `top1`.
3. `ranked` sorts by cosine in descending order. Equal cosines go to the smallest slug.
4. The first element of `ranked(view, query)` MUST equal `top1(view, query)`.
5. `match` takes the first `k` ranked wines that have a card.
6. The score is the cosine.

### Backend `mock`

1. A mock pipeline gets an optional field `bundle`. The bundle gives the cards and the
   wine list.
2. For a known image SHA-256, rank 1 is the configured slug with score `1.0`.
   Ranks 2 to `k` are random bundle wines with random scores in the range `[0, 1)`.
3. For an unknown image, the response contains `min(k, number of wines)` random bundle
   wines with random scores in the range `[0, 1)`.
4. The service sorts the random candidates by score.
5. The service skips a configured slug without a card.
   `tabia_pino_nuar` and `donum_xxiv` are not in the lab catalogue.
6. The mock scores have no meaning.

## Stages

1. **Bundle.** Version 2 in the builder and in the validator. Rebuild the real bundle.
2. **Matcher.** Add `/v1/match`, the ranked interface, the card reader, and the mock
   behavior. Update `matcher/openapi.yaml`, `matcher/README.md`, `matcher/TESTING.md`,
   `ChangeLog.md`, and `SMOKE_TESTS.md`.
3. **Bot.** A separate plan. The bot calls `/v1/match?k=4` and does not send a pipeline.
   The bot stores the card of each candidate in its SQLite database.
   The negative feedback action reads the stored cards.
   The bot removes `CATALOG_FILE` and `WINE_CODE_MAP_FILE`.
   The bot uses `rerank-siglip2-512-crop` on port 8158 today.
   The new matcher pipeline is `siglip2-p512-as-is`: no rerank and no crop.
   The two pipelines have different scores and possibly a different accuracy.
   Stage 3 MUST calibrate `BOT_MATCH_MIN_SCORE` and `BOT_MATCH_MIN_MARGIN` again.

## Tests

1. The existing bundle tests, matcher tests, and official harness test pass.
2. The `/v1/eval/predict` schema in `openapi.yaml` does not change.
3. A version 2 fixture bundle passes validation. A version 1 fixture bundle still passes.
4. The validator rejects a version 2 wine record with a missing or extra key.
5. The builder writes `page_url`, `image_url`, and normalized `qr_urls`.
6. The first element of `Bundle.ranked` equals `Bundle.top1` on the test bundles.
7. `Bundle.ranked` gives unique slugs in cosine order. Equal cosines go to the smallest
   slug.
8. A known mock image gives the configured slug at rank 1 with score `1.0` and `k - 1`
   other wines.
9. An unknown mock image gives `min(k, number of wines)` unique wines in score order.
10. A configured slug without a card is skipped.
11. Without `k`, the response has up to 20 candidates. `k=1` works.
    `k=0` and a value above the maximum give HTTP 422.
12. A pipeline without a card source gives HTTP 503 for `/v1/match`.
13. `/v1/match` needs the bearer token when `matcher.token` is configured.
14. The image limits apply to `/v1/match`.
15. The `sugar` rules match the bot rules.
16. The request archive record contains the candidate slugs.

## Resolved questions

The owner answered on 2026-09-28T15:24:13+0300.

1. The maximum of `k` is 20.
2. This plan may change the bundle builder files of the section
   `codex-side-matcher-bundle`.
3. The lab wine `__aaaaa` is a test wine. The owner removes it. This plan does not
   change it.

## Implementation notes

1. `matcher/protection.py` protects `/v1/eval/predict` and `/v1/match`.
2. `matcher/app.py` uses one helper for the validation, the archive, and the audit record
   of both endpoints. The audit record of `/v1/eval/predict` did not change.
3. The regenerated `matcher/openapi.yaml` keeps the `/v1/eval/predict` operation and the
   old schemas. The file lists the responses of that operation in a new order.
4. `matcher/tests/test_siglip2.py` now uses format version 3 as the unsupported version.
