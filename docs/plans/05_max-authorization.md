# MAX authorization for «Винный дневник»

Date: 2026-10-19.
Issue: https://github.com/s1mb1o/svoe-vino-lab-dev/issues/50.
Branch: `feature/account`.
Base: `0621952f` (`main`).
Depends on: plan `04_user-accounts.md` (issue #48). This plan adds MAX to that account service.
Status: The account service checks MAX launch data and links MAX (commit `64545eb5`). The
mini app `/max`, «Привязать мессенджер» → «MAX» on the site, and the Nuxt host guard exist
(2026-10-19, `webui/docs/account.md`, "MAX link"). The bot changes and the deployment do not exist
yet. Plan 04 dropped
passwords on 2026-10-19: the login methods are the email code and Yandex ID.
Sketches: boards 5 and 6, and the third screen of board 1, in
[`04_user-accounts/sketches/`](04_user-accounts/sketches/). They are sketches, not a final design.
Review: Codex (`gpt-6.1-sol`, xhigh) reviewed the combined plan twice on 2026-10-19. This plan
applies the MAX findings: no one-time login codes, no account calls in bot handlers, launch
data relay and replay checks, a route list for the public host, an advisory outbox enqueue,
no link cache in the bot, and pages under `/max/*`.

## Goal

Let a MAX user open «Винный дневник» inside MAX, and keep the wines that the MAX bot finds.

1. Open the diary inside MAX as a MAX mini app. The site shows a fixed QR code that opens it.
2. Link MAX to an account: the person logs in with the email code inside the mini app, then
   confirms the link.
3. Optional (issue #50 decides): a linked MAX user gets a session at each launch
   (`MAX_LOGIN_ENABLED`, off by default). MAX-only registration is not implemented.
4. Save the searches of the MAX bot to the diary of a linked user.

Every existing component MUST keep its current behavior when the account service is down,
not deployed, or not configured. This includes the MAX bot.

Out of scope:

- Login on a desktop browser by a QR code scanned in MAX. See "MAX platform rule" and the
  appendix.
- Unlinking MAX. An account keeps at least one login method.
- Telegram linking.
- Ratings inside the bot. The bot feedback «✅ Совпало» / «❌ Не совпало» stays a recognition
  check. It is not a taste rating.

## Facts that shape the design

- MAX puts the mini-app launch data in the URL fragment (`#WebAppData=…`). The data contains
  `auth_date`, `query_id`, `ip`, `user`, `chat`, and `hash`
  (`wiki/raw/dev.max.ru/docs/webapps/validation.md:19`, `:36-60`).
- The MAX bot handles updates one at a time (`max-bot/src/chto_za_vino_max_bot/delivery.py:67-96`).
  A slow call in a handler stops all users.
- The MAX bot supervisor stops the whole bot when any supervised task ends or raises
  (`max-bot/src/chto_za_vino_max_bot/app.py:2423-2430`).
- An exception after a successful match marks the request `internal_failed` and sends an error
  (`max-bot/src/chto_za_vino_max_bot/app.py:290-300`).
- The MAX bot deletes request data after 30 days. Production refuses another value
  (`max-bot/src/chto_za_vino_max_bot/config.py:347-349`). Retention also deletes bot `users`
  rows without requests (`max-bot/src/chto_za_vino_max_bot/storage.py:1812-1818`).
- The bot schema uses `CREATE TABLE IF NOT EXISTS` and has no column migration
  (`max-bot/src/chto_za_vino_max_bot/storage.py:207`).
- No source confirms that the mini-app `initData.user.id` equals the Bot API `user_id`.
- Since 2026-10-17 the whole site `chtozavino.ru` requires HTTP Basic (#37).

## MAX platform rule

The MAX rules define «Авторизационные сообщения» as messages that contain or start the
transfer of one-time codes, «в т.ч. QR-коды», tokens, or links for authentication or
identification on third-party resources (`wiki/raw/dev.max.ru/docs/legal/rules.md:37`).
Requirement 1.5 forbids forming or sending them through the API without a contract with MAX
(`wiki/raw/dev.max.ru/docs/legal/requirements.md:55`). The bot guide says:
«отправлять авторизационные сообщения через диплинки запрещено»
(`wiki/raw/dev.max.ru/docs/chatbots/bots-coding/prepare.md:286`).
MAX can suspend or delete an app on a violation or a suspected violation
(`wiki/raw/dev.max.ru/docs/legal/rules.md:161-163`).

A one-time code in a QR code or deep link that logs a browser in, or links an account,
matches this definition. This plan does not use one.

The plan uses the MAX mini-app identity instead. MAX signs the launch data (`initData`) of a
mini app. The data contains the MAX user. The server checks the signature. No code and no
message go through the bot. The QR code on the site is a fixed link without a code.

The mini app needs no separate agreement in the checked sources:

- Mini apps are open to legal entities, IP, and self-employed RF residents. A developer
  connects one in the bot settings (`wiki/raw/dev.max.ru/docs/webapps/introduction.md:11`,
  `wiki/raw/dev.max.ru/help/miniapps.md`). The platform rules of the bot apply.
- The rules expect accounts that an app creates from a MAX account. Such an app MUST let the
  person delete the account and the data (`wiki/raw/dev.max.ru/docs/legal/rules.md:136`).
- MAX gives the app the user ID with the consent of the person at the first launch
  (`wiki/raw/dev.max.ru/docs/legal/privacy.md:43`, `:65`). Our own 152-FZ duties still apply.
- MAX documents the `initData` check to confirm a real user
  (`wiki/raw/dev.max.ru/docs/webapps/validation.md`).

This is a reading of the published texts, not legal advice. A short written question to
`partner_support@max.ru` removes the remaining doubt.

## Mini app

Mini app: the Nuxt pages under `/max/*` on a separate host `https://max.chtozavino.ru/`
(see "Deployment"). The host root redirects to `/max`. Connect the root URL in the bot settings
(«Чат-боты → ⋮ → Настройки»). Deep link: `https://max.ru/<bot>?startapp=account`.
The payload `account` is a constant.

The URL rules list only Latin letters, digits, the dot, and the hyphen
(`wiki/raw/dev.max.ru/help/miniapps.md`). A host root without a path meets these rules.
A settings change can start a new bot moderation of up to 48 working hours. Users see the
old version during that time (`wiki/concepts/bot-registration-and-moderation.md:76-82`).

Open the diary in MAX:

1. On the site, the tab «Через MAX» shows the QR code of the deep link. A phone shows
   «Открыть в MAX» with the same link.
2. MAX opens the mini app. With `MAX_LOGIN_ENABLED`, the page sends `window.WebApp.initData`
   to `POST /v1/auth/max/session` and a linked person gets a session (1 day).
3. Otherwise, or for a person without a link, the mini app shows «Войти по коду из письма».
   The code goes by email and the person types it on our page. No code passes through MAX.
   A new address completes the sign-up of plan 04 (username and two checkboxes).

Link MAX:

- After the email-code login, the page shows the MAX name from `initData`: «Привязать
  MAX-аккаунт «Имя Фамилия» к дневнику anna_wine?». A person who sees a foreign name stops.
- «Привязать» sends `initData` to `POST /v1/me/identities/max`.
- The site shows the same fixed QR code under «Настройки» → «Привязать MAX».

Mini-app screens. The host holds the diary only. Photo recognition stays in the bot chat.

1. Start: the 18+ gate, then the `initData` check. This shows a short loading state.
2. Welcome, for a MAX user without a link: two sentences about the diary and «Войти по коду
   из письма». A new address continues to the sign-up (username, the terms checkbox, and the
   consent checkbox). Then «Привязать MAX-аккаунт «Имя Фамилия» к дневнику …?».
3. Onboarding: the four preference steps of plan 04. Each step has «Пропустить».
4. «Винный дневник»: «История» (searches from the bot and the site, with photos), «Оценки»,
   «Предпочтения».
5. «Настройки»: «Email», «Отвязать MAX»; «Сохранять историю поисков с фото»;
   «Удалить все фото»; «Удалить аккаунт».
6. Footer on every screen: links to `/privacy`, `/terms`, and `/contacts`, and the alcohol
   warning.
7. Errors: «Дневник временно недоступен» when the service is down.
8. Outside MAX (an ordinary browser, no `initData`): «Откройте дневник в MAX» with the deep
   link and its QR code. No account data and no forms.

## Launch data checks

A person can copy their own launch URL and send it to another person. Without checks, the
other person could register, log in, or link an account for the MAX identity of the sender.
Each exchange of `initData` MUST pass all these checks:

- a valid signature;
- `auth_date` at most 5 minutes old;
- a `query_id` that the service did not see before. The service keeps used IDs for 1 hour;
- the signed `ip` equals the client address that Caddy reports.

Each exchange makes at most one session. A `max` session takes `auth_at` from the signed
`auth_date`. A replayed launch cannot make a new recent session, because each `query_id`
works once.

The Phase 0 test checks that `ip` is present and matches on mobile data and on Wi-Fi. If it
does not, the owner decides between two choices: release with the residual risk (the
single-use 5-minute window and the visible MAX name on every screen), or turn off MAX
registration and linking.

Rules:

- Use a key derived from the bot token: `HMAC_SHA256(key="WebAppData", msg=bot_token)`.
  The operator computes it once. The account service gets only this key, never the bot token.
- Never trust `initDataUnsafe`. Never write `initData` to a log.
- A MAX `user_id` links to one account at most.
- Load the MAX Bridge script only on the `/max/*` pages.

## Account service changes

Implemented in `001_initial.sql` (commit `64545eb5`): `identities` with the provider `max`,
`used_launches`, and the session method `max`.

Later, in new schema files:

| Change | Columns |
| --- | --- |
| `users` | new `photos_cleared_at` |
| `searches` | new `captured_at`; `source` gets the value `max`; `source_ref` holds the bot request ID |

- The service stores no MAX names or usernames. It stores the MAX `user_id` only.
- «Удалить все фото» sets `photos_cleared_at`.
- Account deletion also deletes the identities of the user.

Credentials:

| Credential | Format | Storage | Lifetime |
| --- | --- | --- | --- |
| `max` session | 32 random bytes | SHA-256 hash | 1 day |
| Service token (max-bot) | `openssl rand -hex 32`, distinct from the web token | Server env file, mode 0600 | Until rotation |
| MAX mini-app key | Derived from the bot token | Server env file, mode 0600 | Until bot token rotation |

- `MAX_WEBAPP_KEY` holds the derived key. `chto-za-vino-account max-key` computes it from the
  bot token on stdin.

Routes:

| Route | Consumer | Purpose |
| --- | --- | --- |
| `POST /v1/auth/max/session` | web | Implemented. Check `initData`; a session or `not_linked` (only with `MAX_LOGIN_ENABLED`) |
| `POST /v1/me/identities/max` | web | Implemented. Link `initData` to the logged-in account |
| `DELETE /v1/me/identities/max` | web | Implemented. Unlink MAX |
| `POST /v1/bot/searches`, `PUT /v1/bot/searches/{id}/image` | max-bot | Later. Save a bot search (`saved` or `skipped`) and its photo |

- The service rejects a bot save with a capture time before the link time of the identity.
  It drops the photo of a save with a capture time before `photos_cleared_at`. A deleted and
  recreated account therefore never gets old searches or photos.
- The bot sends only photos that its own moderation accepted.

## Bot changes (`max-bot/`)

- The start message and a new `/diary` command get a «Винный дневник» button that opens the
  mini app. The bot makes no account call in any handler.
- After `_send_result` returns, the bot calls an advisory enqueue with its own exception
  handling. A failure is logged without user data. It does not change the request status and
  sends no message. The enqueue MUST NOT reach the general handler at `app.py:290-300`.
- The enqueue adds a row to a new table `account_outbox` (`CREATE TABLE IF NOT EXISTS`; no
  change to existing tables). The row holds the request ID, the MAX `user_id`, the capture
  time, the slug, and the wine snapshot. The request ID references `requests` with
  `ON DELETE CASCADE`, so the bot retention and the user deletion remove outbox rows too.
- A background worker sends each row once as an idempotent `POST /v1/bot/searches` without the
  photo. The service resolves the MAX identity. It answers `saved` or `skipped` (not linked,
  saving off, or captured before the link). It stores nothing for `skipped`.
- After `saved`, the worker sends the moderated photo from the bot image store with
  `PUT /v1/bot/searches/{id}/image`. The bot keeps no link state.
- The worker runs outside the update dispatcher. It uses a 5 s timeout per call. It catches
  every error and never ends while the bot runs. Retries use backoff for at most 24 hours.
  Then the row is dropped.
- An empty `ACCOUNT_ENDPOINT` turns off the button, the outbox, and the worker.
- Update the privacy text, `PRIVACY.ru.md`, `docs/specification.md`, and the README.

## Web UI changes

- `/account`: the new tab «Через MAX» with the fixed QR code and «Открыть в MAX».
- «Настройки»: «Привязать MAX» with the same QR code.
- `/max/*`: the mini-app pages (`/max`, `/max/onboarding`, `/max/settings`, and others).
  They reuse the account components of plan 04. Their navigation stays under `/max/*`.
  They use a small header of their own without the site links: the route list of the mini-app
  host does not allow `/android`, `/ideas`, and the other site pages.
- The global 18+ gate also covers `/max/*`.
- On the mini-app host, do not load Metrika and do not register the service worker.
  This keeps the cookie question of #41 off the mini app.
- Exclude `/max*` from the Workbox navigation cache.
- On the mini-app host, the Nuxt server allows only the email-code, sign-up, MAX, and
  account routes. It rejects the Yandex ID routes. Sessions from the main site do not reach
  this host: the session cookie is host-only.
- The account deletion page states that the MAX bot keeps its own operational copies of
  photos for at most 30 days.

## Failure isolation

| Component | Account service is down or not configured |
| --- | --- |
| MAX bot | Works unchanged. Handlers make no account calls. Saves wait in the outbox. |
| MAX mini app | Shows «Дневник временно недоступен». |
| Web «Через MAX» tab | Shows the fixed QR code. It needs no service call. |

## Deployment

- Public access (owner decision, 2026-10-19): only the page that MAX uses is public.
  `chtozavino.ru` keeps HTTP Basic.
- A new Caddy site block `max.chtozavino.ru` has no HTTP Basic. It proxies to the same Nuxt
  server. It allows only these paths and returns 404 for all others:
  - `/` (HTTP 302 to `/max`; browsers keep the URL fragment, so `initData` stays);
  - `/max` and `/max/*` (the mini-app pages);
  - `/_nuxt/*` (built JS and CSS; no data);
  - `/reference/*` and `/icons/*` (logo, font, background, and icons of the layout);
  - `/api/account/*` routes from an explicit list of methods and paths in the Nuxt server:
    email code, sign-up, MAX, and account routes;
  - the legal pages `/privacy`, `/terms`, and `/contacts` (#37);
  - `/robots.txt`, answered by Caddy with `Disallow: /`.
- Test in a fresh browser without Basic credentials: the mini-app host loads and works, any
  other path on it returns 404, and `chtozavino.ru` still returns 401.
- DNS: the `A` record for `max.chtozavino.ru` points to Claudette (the VDS that serves
  `chtozavino.ru`). Caddy gets the certificate.
- gx10: the MAX bot reaches the account service on a shared Docker network. The bot reads
  `BOT_ACCOUNT_ENDPOINT` and `ACCOUNT_MAX_TOKEN` (the same name and value as in the account
  service; not `MAX_BOT_TOKEN`).
- MAX: connect `https://max.chtozavino.ru/` in the bot settings (owner action).
- Put host files in the workspace `deploy/` directory, not in this repository.
- Get owner approval for every production deploy and restart.

Release order:

1. Connect the URL to a separate test bot first, if the second bot slot of the
   self-employed profile is free. Run the Phase 0 test and the acceptance checks there.
2. Enter the URL in the production bot only after these checks pass. Moderators then see a
   working page. A broken page can get «Нужны исправления».
3. The settings stay locked during the moderation (up to 48 working hours). Make the other
   bot card and text changes (#10) before, not during, this time.

Before the review, the page at `https://max.chtozavino.ru/` MUST:

- open in MAX over HTTPS with a valid certificate and without HTTP Basic;
- do what the bot button promises. Do not submit a placeholder page. The rules forbid an app
  that misleads about its functions (`wiki/raw/dev.max.ru/docs/legal/requirements.md:51`);
- show the 18+ gate;
- link the operator details (name, ИНН, contacts), the privacy policy, and the terms of use
  from every screen (requirement 2.1). The texts of #10 and #37 MUST be complete, without
  placeholders such as `{ФИО}` or `{ИНН}`;
- ask the person to accept the terms of use explicitly. The terms define and forbid illegal
  content (requirement 3.1 а). Photos and notes are user content;
- offer account deletion (rule 4.5.5);
- check `initData` on the server (requirement 4.2);
- show a clear screen for errors and for an ordinary browser (requirement 4.4).

## Legal and texts

- The account also stores the MAX `user_id`. Add it to `/privacy` (#37).
- The operator removal CLI of plan 04 serves requirement 3.1 б: removal of illegal user content
  on a complaint or an authority request.
- Add the MAX texts to the lawyer review (#45).

## Implementation steps

Phase 0 — checks and decisions:

1. Done: the owner confirmed the mini-app design. Optionally ask MAX support to confirm it
   under rule 1.5.
2. Done: only the mini-app host is public. The owner added the `A` record for
   `max.chtozavino.ru` on 2026-10-19, with the same address as `chtozavino.ru`.
   The reg.ru name servers published it on 2026-10-19 at 00:46.
3. Live test on a test bot, on mobile data and on Wi-Fi:
   - `initData.user.id` equals the Bot API `user_id` of the same person. The bot saves
     depend on it;
   - the signed `ip` is present and equals the client address of the page request;
   - the URL fragment survives the HTTP 302 from `/` to `/max`.

Phase 1 — account service (after Phase 1 of plan 04):

4. Done (commit `64545eb5`): launch data checks, used launch IDs, MAX link and unlink,
   `max` sessions behind `MAX_LOGIN_ENABLED`.
5. Not planned: passwords (plan 04 dropped them). MAX-only registration waits for #50.
6. Bot routes with the link-time and photo-cutoff rules.

Phase 2 — Web UI:

7. Done (2026-10-19): `/max`, the host route list, «Привязать мессенджер» → «MAX». The «Через MAX»
   login tab waits for `MAX_LOGIN_ENABLED` (#50).
8. Caddy block for `max.chtozavino.ru` (deploy files outside the repository).

Phase 3 — bot:

9. «Винный дневник» button, `/diary`, advisory enqueue, `account_outbox`, the worker.
10. Bot docs and privacy text.

Phase 4 — release:

11. Test bot, then the "Before the review" checklist, then the production bot settings.

## Acceptance checks

Isolation:

- Stop the account service. The MAX bot passes its existing checks.
- A 5 s hang of the service does not delay a bot reply.
- An outbox worker error does not stop the bot. Recognition continues.
- An outbox enqueue error leaves the request `recognized` and sends no error message.
- The bot starts on a copy of the current production database, with and without
  `ACCOUNT_ENDPOINT`.
- The outbox delivers saved searches after the service recovers.

Mini app and security:

- The fixed QR code on a desktop and the button on a phone both open the mini app.
- The mini-app host loads without HTTP Basic, loads no Metrika, and returns 404 for paths
  outside its list. `chtozavino.ru` still returns 401 without credentials.
- The email-code login and the MAX link work in the mini app.
- Modified `initData`, `initData` older than 5 minutes, a reused `query_id`, or a different
  client address fails. A launch URL copied to another browser gets no session.
- On the mini-app host, the Yandex ID routes fail and the email-code login works. A refresh
  on a `/max/*` page works.
- A MAX `user_id` that is already linked cannot link a second account.
- Logs and errors contain no `initData`.

Bot saves and deletion:

- A scan after a MAX registration is saved, even right after an earlier skipped scan.
- «Удалить все фото» stops a pending bot photo from before that time.
- A new account with the same MAX user does not get searches from the outbox of the old account.

## Owner decisions

Recorded on 2026-10-19:

1. MAX design: the mini app. A desktop QR login is not planned (it needs a contract with MAX).
2. Site access: only the page that MAX uses is public (`max.chtozavino.ru`). The rest of
   `chtozavino.ru` keeps HTTP Basic.

## Appendix: desktop QR login (not planned)

Use this only with a written permission or contract from MAX. The design needs:

- protection against a relayed QR code: an attacker shows their own code to a victim and gets
  the victim's session after the victim confirms;
- confirmation texts that differ for login and for linking;
- account calls in a separate per-user queue, outside the bot update dispatcher;
- analytics off on every page that shows the code;
- an acceptance test with an attacker browser and a victim phone.
