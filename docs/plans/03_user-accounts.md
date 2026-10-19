# User accounts: «Винный дневник»

Date: 2026-10-19.
Issue: https://github.com/s1mb1o/svoe-vino-lab-dev/issues/48.
Branch: `feature/account`.
Base: `0621952f` (`main`).
Status: Owner decisions recorded on 2026-10-19 (see "Owner decisions"). No code exists.
Related plan: MAX authorization is in `04_max-authorization.md` (issue #50). It depends on this plan.
Sketches: boards 1–4 in [`03_user-accounts/sketches/`](03_user-accounts/sketches/). The third
screen of board 1 («Через MAX») belongs to plan 04. Rebuild the boards with
`python3 docs/plans/03_user-accounts/sketches/build.py`. They are sketches, not a final design.
Review: Codex (`gpt-6.1-sol`, xhigh) reviewed the combined plan twice on 2026-10-19. This plan
and plan 04 apply the findings. The owner split the plan into these two parts on 2026-10-19.

## Goal

Let a person keep their wine searches, rate wines, and state taste preferences.
The `/ideas` page shows this feature as a mockup (`webui/app/pages/ideas.vue:26`):
«Собирать впечатления о винах, замечать любимые стили и получать персональные рекомендации.»

The user-facing name is «Винный дневник» (owner decision, 2026-10-19). Do not use the word
«паспорт» for this feature. MAX «Цифровой ID» is «цифровой аналог паспорта» with a QR code
(`wiki/raw/dev.max.ru/docs/digital-id.md:21-26`). «Паспорт вкуса» already names the taste
profile of one wine (F-21, `webui/app/components/WineExperiences.vue`).

Keep the feature small. Every existing component MUST keep its current behavior when the
account service is down, not deployed, or not configured.

## Scope

In scope:

1. Registration and login with a username and a password.
2. Change the password.
3. A new LAN-only service `account/` on gx10. The Nuxt server calls it.
4. Saved searches from the Web UI: the photo, the found wine, and the time.
5. Explicit taste preferences. A short onboarding asks for them after registration.
6. Personal ratings of wines, with an optional note.
7. Self-service deletion: one search, all photos, or the whole account.
8. Application tokens. An MCP client uses a token to read the account data of its owner
   (Phase 2, after open decision 4).

Out of scope for this plan:

- Everything about MAX: the mini app, MAX registration and login, linking MAX, password reset
  through MAX, and saving bot searches. See plan 04.
- Catalog-wide personal recommendations. The Web UI on `main` has no full catalog. Use the
  MCP `find_wines` tool or a later issue (#31, #25).
- Email, password reset by email, OAuth, data export, shelf-mode saves.
- A learned taste model. Preferences are what the person states (#31).

## Facts that shape the design

- The Web UI runs on the VDS Princess behind Caddy (`webui/ResearchLog.md:587-600`). It reaches
  gx10 only through restricted reverse SSH tunnels (`workbench/ChangeLog.md:676-681`).
  The VDS MUST NOT keep application data
  (`workbench/docs/deployment/01_gx10-public-failover-options.md:125-128`).
- The Web UI has no auth, session, cookie, or history code on `main`. The IndexedDB collection
  that #20 describes is not on GitHub `main`.
- The Web UI MUST keep photos out of its own disk and logs (`webui/CLAUDE.md:47`).
- Since 2026-10-17 the whole site requires HTTP Basic, except `GET /api/health` (#37).
- Metrika runs on every page with `trackLinks:true` and `webvisor:false`
  (`webui/shared/metrika.ts:11`).
- Chrome and Firefox cannot decode HEIC in the page (`webui/app/components/PhotoScanner.vue:13`).
- `webui/shared/taste.ts` derives six 1–5 meters: `body`, `acidity`, `tannin`, `sweetness`,
  `fruit`, `oak`. `TasteMetric` has no basis field. `body` and `acidity` get a default value
  when the card and the dataset have no evidence (`webui/shared/taste.ts:257-266`).
- The im-core moderation client waits up to 120 s (`im-core/src/chto_za_vino_core/moderation.py:118-124`).
- #45 records an owner decision: the account keeps the version of the accepted consent text.
- Production state uses SQLite with WAL. #33 allows PostgreSQL only when many writers or hosts
  need it.

## Architecture

```mermaid
flowchart LR
    B[Browser] -->|cookie session| N[Nuxt server on Princess]
    C[MCP client] -->|app token, Phase 2| N
    N -->|reverse SSH tunnel, service token| A[account service on gx10]
    A --> D[(SQLite + photo files on gx10)]
    A -->|photo moderation| S[ShieldGemma 2]
```

- The account service is LAN-only. It has no public route.
- All public traffic goes through the Nuxt server. The browser never sees the service URL.
- The MCP client calls a public Nuxt route with an application token. Nuxt forwards the token.
- The service does not call the matcher. The matcher and the bots do not need it.
- Plan 04 adds the MAX bot as a second consumer.

## Failure isolation

| Component | Account service is down or not configured |
| --- | --- |
| Web scanner | Works unchanged. The predict route does not call the account service. |
| Web account UI | Shows «Дневник временно недоступен». No retry loop. |
| Web save after a match | The result stays on screen. A small note says the save failed. |
| SSR | Never waits for the account service. Account state loads on the client. |
| MAX and Telegram bots | No change in this plan. |
| MCP catalog tools | Work unchanged. Account tools return `unavailable`. |
| Matcher | No dependency. |

Rules:

- Nuxt: 2 s timeout for account calls; 10 s for a photo upload. No retries on writes.
- An empty `NUXT_ACCOUNT_ENDPOINT` hides all account UI. No mock account mode exists.

## Component: `account/`

Use the `max-bot` conventions: Python 3.12, uv with `uv.lock`, FastAPI, uvicorn, `src/` layout
(`chto_za_vino_account`), pytest, ruff, a digest-pinned Dockerfile, uid 1000, and
`scripts/verify.sh`. Reuse from `im-core`: image type detection, HEIC conversion, the
ShieldGemma request format, and the auth middleware pattern of `http_api.py` (CIDR allow-list,
bearer check, rate limit before the body is read).

Additional dependency: `argon2-cffi` for password hashes. Pillow is already in the stack.

### Data model

All IDs are random UUIDs. Times are UTC ISO 8601. Each schema change is a new numbered
SQL file in `account/src/chto_za_vino_account/schema/`. Plan 04 adds its tables and columns
in its own files.

| Table | Columns |
| --- | --- |
| `users` | `id`, `username` (unique, normalized), `password_hash`, `created_at`, `consent_version`, `consent_at`, `terms_version`, `terms_at`, `save_history` (default on), `onboarding_done_at` |
| `sessions` | `token_hash`, `user_id`, `auth_method` (`password`), `created_at`, `auth_at`, `expires_at` |
| `searches` | `id`, `user_id`, `created_at`, `source` (`web`), `source_ref`, `wine_slug`, `wine_snapshot` (JSON, at most 2 KiB), `image_path` (nullable), `image_sha256` |
| `ratings` | `user_id`, `wine_slug`, `stars` (1–5), `note` (at most 500 characters), `wine_snapshot`, `updated_at` |
| `preferences` | `user_id`, `schema_version`, `payload` (JSON), `updated_at` |
| `app_tokens` | `id`, `user_id`, `name`, `token_hash`, `created_at`, `expires_at`, `last_used_at`, `revoked_at` (Phase 2) |

- `source_ref` is unique per user and source. For a web save it is a browser-made UUID.
  A repeated save is idempotent.
- `wine_snapshot` keeps the name, producer, color, category, and grapes. History renders when
  the vino-svoe.ru API is down. The Nuxt server builds the snapshot, not the browser.
- Photos: `data/images/<user_id>/<search_id>.jpg`. The service re-encodes each photo to JPEG,
  at most 1280 px on the long side, without EXIF (EXIF can hold GPS data).

### Credentials

| Credential | Format | Storage | Lifetime |
| --- | --- | --- | --- |
| Password | 8–256 characters | Argon2id hash | Until change |
| Session | 32 random bytes | SHA-256 hash | 30 days, sliding |
| Application token (Phase 2) | `cvpat_` + 32 random bytes, base64url | SHA-256 hash | 30, 90 (default), or 365 days |
| Service token (web) | `openssl rand -hex 32` | Server env file, mode 0600 | Until rotation |

- Compare all secrets in constant time. Never write a credential to a log, URL, page title,
  link target, or error.
- A "recent login" is a session whose `auth_at` is less than 15 minutes old.
- Password change, token creation, and account deletion require the current password.
- A password change ends all other sessions of the user.
- Login limits: 5 failures per username per 15 minutes, 30 failures per client address per
  15 minutes. Then HTTP 429 with `Retry-After`. Nuxt sends the client address that Caddy set.
- This plan has no password recovery. A person who forgets the password cannot recover the
  account. The registration form states this. Plan 04 adds a reset through MAX.

### Internal API

Consumer: `web` (Nuxt). It has its own service token and a fixed set of routes. Nuxt adds the
session token in `X-Session-Token` or the app token in `X-App-Token`.

| Route | Purpose |
| --- | --- |
| `GET /healthz`, `GET /readyz` | Liveness; database and disk check |
| `POST /v1/users` | Register with a password; returns a session |
| `POST /v1/sessions`, `DELETE /v1/sessions/current` | Log in, log out |
| `GET /v1/me`, `PATCH /v1/me` | Account summary; `save_history` |
| `PUT /v1/me/password` | Change the password |
| `GET/PUT /v1/me/preferences` | Read or replace preferences |
| `GET/POST /v1/me/searches`, `DELETE /v1/me/searches/{id}` | History |
| `GET /v1/me/searches/{id}/image` | One photo of the owner |
| `DELETE /v1/me/images` | Delete all photos, keep the rest |
| `GET /v1/me/ratings`, `PUT/DELETE /v1/me/ratings/{slug}` | Ratings |
| `DELETE /v1/me` | Delete the account |
| `GET/POST /v1/me/app-tokens`, `DELETE /v1/me/app-tokens/{id}` | Application tokens (Phase 2) |
| `GET /v1/app/profile`, `GET /v1/app/wines` | Read-only data for MCP, app token (Phase 2) |

### Photos and moderation

- Web photos pass ShieldGemma 2 before the first disk write. This repeats the bot rule.
- The account moderation call has a 6 s deadline, inside the 10 s upload budget of Nuxt.
- A photo that fails moderation is not stored. The search row is kept without the photo.
- If moderation times out or is unavailable, the service stores the search without the photo.
- If Nuxt stops waiting, the service can still finish the save. A retry with the same
  `source_ref` does not make a second row. The history shows the saved search.
- Limits: 10 MiB upload, 40 MP decoded, 1,000 searches per user. The service refuses photo
  writes when free disk space is below 2 GiB. The search row is still saved.

### Deletion

- Delete one search: the row and its photo.
- Delete all photos: all photo files and `image_path` values. History and ratings stay.
- Delete the account: all rows of the user, all photos, sessions, and tokens.
  Use `PRAGMA secure_delete=ON`. The response comes after the files are deleted.
- Operator removal: a CLI command deletes one search, one photo, or all content of a user by
  ID. It serves complaints and authority requests about illegal user content. It logs the
  action without the content.
- Backups: a daily SQLite `.backup`, kept for 7 days. Photos are not backed up. The privacy
  page states that deleted data leaves the backups within 7 days.

## Web UI changes

Pages:

- `/account`: tabs «Вход» and «Регистрация». Plan 04 adds «Через MAX».
- `/account/onboarding`: preference steps.
- `/account` after login: «История», «Оценки», «Предпочтения», «Настройки».
- «Настройки»: change the password, «Сохранять историю поисков с фото», «Удалить все фото»,
  «Удалить аккаунт», and application tokens (Phase 2). Plan 04 adds «Привязать MAX».
- The header gets «Войти» or «Дневник» in `.header-actions` (`webui/app/app.vue:25-29`).

Server routes under `/api/account/*` forward to the service. The Nuxt server:

- sets the session cookie `__Host-cv_session` (httpOnly, Secure, SameSite=Lax, Path=/);
- checks `Origin` on every state-changing route;
- sends `Cache-Control: no-store` on all account responses, and `private, no-store` on photos;
- resolves the wine snapshot from the slug with the existing metadata code;
- refuses a save when the prediction mode is `mock`.

Registration:

1. Username, password, and two separate checkboxes that are not preset:
   «Принимаю условия использования» (links to `/terms`) and the consent to personal data
   processing (links to `/privacy`). The service records the version and time of each.
2. A note: a forgotten password cannot be recovered.
3. After registration the onboarding opens. Each step has «Пропустить».

Saving a search:

- After a match, a logged-in browser with `save_history` on sends the photo again to
  `POST /api/account/searches` with a new `source_ref` UUID.
- The browser tries to scale the photo to 1280 px JPEG on a canvas. If the browser cannot
  decode the photo (HEIC in Chrome or Firefox), it sends the original file. The service
  converts it.
- The predict route stays unchanged. This protects the evaluator contract.
- The result shows «Сохранено в дневнике» with «Удалить», or «Не удалось сохранить».
- The note «Фото не сохраняется» (`webui/app/components/PhotoScanner.vue:81`) changes to
  «Фото сохранится в вашем дневнике» only for a logged-in person with `save_history` on.

Other rules:

- The global 18+ gate also covers the account pages.
- Exclude `/account*` from the Workbox navigation cache (`webui/nuxt.config.ts:129-140`).
- Account URLs carry no secrets. Metrika `webvisor` stays off. Mark password fields with
  `ym-disable-keys`.
- Do not add account data to the WebMCP browser tools in this plan.
- Move the «Личный паспорт предпочтений» card from «Макеты» to «Реализовано» and rename it
  «Винный дневник» only after the production check.

## Taste preferences

Onboarding uses large tiles, like the Netflix and Spotify onboarding. Four steps:

1. «Какие вина вы выбираете?» — Белое, Красное, Розовое, Игристое, Оранжевое. Many choices.
2. «Насколько сладкое?» — Сухое, Полусухое, Полусладкое, Сладкое. Many choices.
3. «Какой характер?» — two controls: «Лёгкое / Среднее / Насыщенное / Не важно» and
   «Свежее / Мягкое / Не важно».
4. «Отметьте сорта, которые вам нравятся» — a grid of the 16 grapes with the most Active
   catalog wines. Many choices.

Stored payload, schema version 1:

```json
{"colors":["white"],"sparkling":true,"sweetness":["dry"],"body":"light",
 "freshness":"fresh","grapes":["Рислинг"]}
```

Use of preferences:

- The result card shows «Подходит ли вам». Each stated preference shows one of three states:
  match, no match, or «нет данных». An unknown field is never a match.
- Color, sparkling, sweetness, and grapes use the wine card fields.
- Body and freshness need evidence. Add a `basis` field to `TasteMetric`: `source`,
  `dataset`, or `default`. A `default` value shows «нет данных». `body` maps to the `body`
  meter. `freshness` maps to `acidity`: «Свежее» is 4–5, «Мягкое» is 1–2.
- Each state shows its basis: the wine card or the dataset estimate.
- The account page shows «Любимые стили» from ratings of 4 and 5 stars, grouped by color and
  category. Saves and scan counts are not taste evidence (#31).
- The UI does not claim that the service learned or measured a person's taste.

## Ratings

- 1–5 stars and an optional note of at most 500 characters, per wine slug.
- Rate from the result card and from «История». One rating per wine; a new rating replaces it.
- Ratings stay when photos or searches are deleted.

## Application tokens and MCP (Phase 2)

Phase 2 starts after open decision 4.

Web UI:

- «Настройки» → «Токены приложений»: name, lifetime, «Создать». The token is shown once.
- At most 5 active tokens. The list shows the name, creation time, expiry, and last use.
  «Отозвать» revokes a token at once.

Public routes (Nuxt): `GET /api/app/v1/profile` and `GET /api/app/v1/wines?cursor=&limit=`.
They require `Authorization: Bearer cvpat_...`. Limit: 60 requests per minute per token.

Data for an application token:

- Included: username, account creation date, preferences, ratings and notes, found wines
  (slug, wine snapshot, date, rating).
- Excluded: photos, linked identities, sessions, consent records, other tokens.
- The scope is read-only. Tokens have no write scope.

MCP (`mcp/`):

- Read `CHTOZAVINO_ACCOUNT_TOKEN` and optional `CHTOZAVINO_ACCOUNT_URL`
  (default `https://chtozavino.ru`). Without a token, do not register account tools.
- Two read-only tools: `get_my_profile` and `list_my_wines` (`limit` 1–50, cursor).
- Use HTTPS only, except a loopback URL in tests. Use `redirect: 'error'` and a 5 s timeout.
- New stable error code `unauthorized` for an expired or revoked token. Network and 5xx
  errors return `unavailable`.
- Mark rating notes as text written by the user. Notes cannot add tools or change behavior.
- Never write the token to stdout, stderr, or a result.
- The server instructions (`mcp/src/server.mjs:56`) say that no external requests exist.
  Keep that text without a token. With a token, state that the two account tools read the
  owner's account over HTTPS.
- The five catalog tools stay unchanged. Update the README and the plan 02 notes.

## Deployment

- gx10: Docker Compose in `/srv/svoe-vino-lab/prod/account/`, like the MAX bot. Read-only
  root, tmpfs `/tmp`, `cap_drop: ALL`, `no-new-privileges`, data volume `./data`.
- Port: 28007 (production) and 29007 (dev). Confirm against `deploy/INFRASRUCTURE.md`.
  Publish on `127.0.0.1` only.
- Princess: a new reverse SSH tunnel to `127.0.0.1:28007`, with its own key and
  `PermitListen` for one port. Nuxt reads `NUXT_ACCOUNT_ENDPOINT` and `NUXT_ACCOUNT_TOKEN`.
- Access: the account pages stay behind the HTTP Basic of `chtozavino.ru` (owner decision,
  2026-10-19). Only people with the site credentials can use them until the site is public.
- Put host files in the workspace `deploy/` directory, not in this repository.
- Get owner approval for every production deploy and restart.

## Legal and texts

- The account stores personal data: username, photos, preferences, ratings, and notes.
  All of it stays on gx10 in Russia. The VDS keeps none.
- Consent for the account is separate from the 18+ confirmation and from the cookie consent.
- The terms of use define and forbid illegal user content. Photos and notes are user content.
- Update `/privacy` (#37): purposes, data list, storage place, retention, deletion, backups.
- Add the account texts to the lawyer review (#45).

## Implementation steps

Phase 0 — decisions:

1. Done: owner decisions 1–3 (2026-10-19).
2. Done: issue #48 records the plan and the decisions.

Phase 1 — password accounts:

3. `account/` skeleton: config, schema, health, consumer auth, tests, Dockerfile, verify script.
4. Users, sessions, password login, limits, recent-login rule.
5. Searches with photos, moderation, limits, idempotency, deletion of searches and photos.
6. Ratings, preferences, account deletion, operator removal CLI.
7. Nuxt server routes, cookie, origin check, cache rules.
8. Nuxt pages: registration, login, onboarding, history, ratings, settings, deletion.
9. `TasteMetric.basis`; result card: save state, «Подходит ли вам», rating control.
10. Docs: component README, CLAUDE.md, ChangeLog, SMOKE_TESTS; webui docs and privacy text.
11. Deploy to dev on gx10. Run the acceptance checks. Then production after owner approval.

Phase 2 — application tokens and MCP (after open decision 4):

12. Application tokens and the `/v1/app/*` routes; the token page in «Настройки».
13. MCP account tools, conditional server instructions, and their tests.

## Acceptance checks

Isolation:

- Stop the account service. The web scanner, the shelf mode, the bots, and the MCP catalog
  tools pass their existing checks. The account UI shows the unavailable message.
- With an empty `NUXT_ACCOUNT_ENDPOINT`, the site renders no account UI and makes no account calls.
- A 5 s hang of the service does not delay SSR or a prediction.

Accounts and security:

- Register, log out, log in, change the password. The other sessions end.
- Limits return HTTP 429 after 5 failures for one username.
- A request without the service token, from a wrong address, or with a foreign session fails.
- One user cannot read, rate, or delete data of another user, including photos by ID.
- A cross-origin POST to an account route fails.
- Logs, errors, URLs, and Metrika requests contain no password, session, or token.
- Account pages are not in the Workbox cache after a visit.

Data:

- A saved web photo has no EXIF, at most 1280 px, and passed moderation.
- A HEIC photo from Chrome is saved through the original-file fallback.
- A photo that fails moderation, a moderation timeout, or moderation down stores no photo.
- A save that Nuxt abandoned and then retried makes one row.
- «Удалить все фото» removes all files of the user and keeps ratings.
- Account deletion removes all rows and files of the user. A new account with the same
  username starts empty.

Preferences:

- Each onboarding step can be skipped. The profile can be edited and reset.
- «Подходит ли вам» shows «нет данных» for an unknown field and for a `default` meter, and
  labels dataset estimates.

Tokens and MCP (Phase 2):

- A token is shown once. The service keeps only its hash.
- A revoked or expired token gets `unauthorized` at the next call.
- The token reads only its owner's data and cannot write.
- The MCP account tools return `unavailable` when the service is down. The catalog tools work.
- A note with prompt-like text comes back as data and adds no tools.

## Owner decisions

Recorded on 2026-10-19:

1. Photo retention in the account: until the person deletes them.
2. Ports: 28007 (production) and 29007 (dev).
3. Name: «Винный дневник». Do not use «паспорт» for the account.

The decisions about MAX (the mini app and the public host `max.chtozavino.ru`) are in plan 04.

Open:

4. MCP access. `/api/app/*` stays on `chtozavino.ru` behind HTTP Basic. HTTP Basic uses the
   `Authorization` header, so a `Bearer` application token cannot pass it. Until the site is
   public, MCP account tools work only if `/api/app/*` is also public, or after HTTP Basic ends.
   Phase 2 waits for this decision.
