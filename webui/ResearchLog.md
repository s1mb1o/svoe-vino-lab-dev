# Research log

## 2026-10-20 — Email code input alignment

The six-box grid keeps its existing 384 px maximum width and uses automatic inline margins to center within the account form. Narrow layouts retain the full available width. Vue style compilation passed; browser verification remains manual.

## 2026-10-20 — Android dual-pipeline release

Published website `40a54074` at 19:22:28 UTC.
All 622 deployed website tests, type checking, and Linux build passed.
The complete staged and public GET downloads match all 753111053 APK bytes and the release SHA-256.
Public browser checks passed at 320, 390, and 1440 pixels in both system themes.
The existing download route is GET-only. HEAD returns 404. Browser GET downloads pass.
The previous website and APK remain preserved. Caddy and matcher services did not change.

The two complete encoder/index pairs use one shared catalogue image archive.
The signed APK contains 753111053 bytes. Its display size is 718 MiB.
The public versioned filename and physical configured file MUST identify the same artifact.
A byte-count guard prevents the route from serving an older APK under the new release name.
The existing screenshots remain version 0.1.4 evidence. They do not measure version 0.3.0 quality.
The Android measurement record provides the separate Pixel retrieval results.

## 2026-10-20 — Shelf Lens source integration

The owner requested integration into the main checkout after choosing local-only delivery.
The standalone source is `drink-atlas-workspace/sites/shelf-lens-landing-ru/dist`.
The existing `/shelf` route scans a photograph. The new `/shelf-lens` route presents the Android video workflow.
The page uses the existing Nuxt shell, `Playfair Display` font, theme storage, and age gate.
All page classes and custom properties use the `sl-` prefix. Dark theme selectors follow the scoped CSS rule.
Vue refs replace the standalone DOM listeners. Route exit pauses both videos, removes listeners, and releases the body scroll lock.

The installed Nitro static handler returns HTTP 200 for a video Range request.
This prevents a direct jump to a late chapter in WebKit before the full download.
The page now uses `/shelf-lens-video/<filename>` for two allowlisted server assets.
The handler supports GET, HEAD, single ranges, open ranges, suffix ranges, and HTTP 416.
It reads one bounded compressed asset into memory per request. The largest asset is 16,880,750 bytes.
A large video catalog would need a streaming media server. This page has two fixed assets.
The remaining images stay under `public/shelf-lens/`.
The existing service worker does not precache these media paths.

The displayed 3 shelves, 95 facings, and 46 recognized bottles describe the supplied example.
These counts do not measure recognition accuracy.
The current implementation supports ratings from «Своё Вино».
Bottle search, AR navigation, and taste highlighting remain future scenarios.

Validation on 2026-10-20:

- `npm run typecheck`: passed.
- `npm test`: 31 files passed. 610 tests passed. 26 existing tests skipped.
- `npm run build`: passed.
- `npm run test:bundle`: passed. `/` uses 165.5 KB gzip. `/shelf` uses 165.7 KB gzip. All 25 producer maps remain lazy.
- HTTP checks passed for both video assets. The checks compare exact byte ranges, suffix ranges, and open ranges with the source bytes. HEAD, HTTP 416, unknown-file HTTP 404, and method HTTP 405 checks passed.
- The in-app WebKit browser passed the shared age gate, both rendered themes, chapter selection, video playback, and a direct seek to 114 seconds.
- Escape paused the full video, restored body scrolling, and returned focus to the opener.
- The phone planogram used an 880-pixel image inside a 320-pixel scroll viewport.
- Both themes fit at 320, 390, 768, and 1280 CSS pixels without horizontal page overflow.
- Nuxt navigation passed from the scanner to `/ideas`, through the Shelf Lens card, and back to the page. The three scanner modes remain available.
- The browser reported no warnings or errors during these checks.

Evidence is under `/private/tmp/shelf-lens-integration/`.
`http-results.json` records HTTP checks. `desktop-light.jpg` and `mobile-dark.jpg` record the integrated page.
Reduced-motion emulation and physical-device playback were not tested in this integration run.
The source includes reduced-motion handling. Physical-device acceptance remains separate.
No production service or hosting configuration changed.

## 2026-10-20 — Original result pin and public device copy

Main `969b58eb` supplied an offline card only to alternative and comparison pins.
The original recognition-result pin saved to the diary but did not create a device copy.
The original pin now requests one exact public card after a successful server save.
The dedicated route resolves the ID and version from the existing pinned F04 snapshot.
The route does not use alternative ranking or depend on optional result metadata.
The lookup has a four-second timeout. A lookup or storage failure preserves the diary save and exposes retry.
An account generation and owner/epoch check rejects a response after account reset.
Existing saved wines can use the explicit copy action on the original pin.
No automatic copy of the complete saved list is added.

Validation on 2026-10-20:

- `npm test`: 30 files passed. 601 tests passed. 26 existing tests skipped. Tests that start loopback servers ran with local network permission.
- `npm run typecheck` and `npm run build`: passed.
- `npm run test:f04`: passed in Chromium and WebKit. The report finished at 14:05:47 Moscow with no page errors.
- The new browser cases verify the exact public-card route, original save before alternatives, lookup failure and timeout, explicit retry, offline reload, existing saved copy, unavailable result metadata, denied storage, and an account switch during lookup.
- The existing alternative, comparison, diary status/note, logout, account deletion, login continuation, and cache-isolation checks also pass.
- `npm run test:bundle`: passed. `/`: 165.0 KB gzip. `/shelf`: 165.2 KB gzip. All 25 producer-map chunks remain lazy.
- The existing PWA browser check passed against the same build. Warmed offline reload returns HTTP 200 from the service worker. API requests remain unavailable offline. The worker update waits.
- `git diff --check` and browser-script syntax checks passed.

Evidence root: `/private/tmp/f04-result-offline-20261020`.
The accepted browser report is `browser-verified/browser-report.json` in that directory.
The browser run uses the real account service with isolated SQLite and memory mail. The test-code override is disabled.
Recognition uses a deterministic upstream fixture. No recognition-accuracy, production-deployment, or new physical-phone claim is made.

## 2026-10-20 — Saved wine as the second comparison card

Owner request: choose the second wine from saved wines.
The initial F04 entry accepted only a ranked alternative.
The new entry uses the authenticated saved-slug endpoint of the existing account service.
The Web server resolves those IDs and the first ID against the same pinned comparison snapshot.
The selector does not apply alternative ranking, producer exclusion, or style filters.
An unsupported exact ID remains visible with an explicit unavailable state.
The response contains no note, personal status, account token, or uploaded photo.
The saved list remains in component memory and is cleared when the picker closes or the account resets.
Login continuation stores only the first public slug in session storage.
The existing pair-return format and public offline-card format remain unchanged.
No account schema or service change is required.
Read `docs/f04-saved-comparison-2026-10-20.md` for the validation of this change.

## 2026-10-20 — F04 identities, persistence, and acceptance

The existing diary already stores saved statuses and private notes. F04 reuses that backend.
`SavedSource` has no `alternatives` value. This photo-result journey uses `photo`.
Saving a candidate must not record another recognized photo.
The existing MCP loader provides the checked Active IDs and comparison semantics.
A server-only generated asset removes runtime dependence on MCP, source exports, and model files.
Exact map aliases provide producer identities. A slug prefix cannot prove identity.
Missing still/sparkling data stays unknown. The filter cannot infer still wine.
The selected twenty-anchor manifest yields eighteen strict results and two explained empty results.
A same-transaction owner/epoch check prevents delayed writes from restoring a cleared device cache.
An IndexedDB quota exception can occur inside an asynchronous success callback. Catch that exception and abort the transaction before reporting a result.
The existing `__Host-` cookie contract requires a secure context in tests. Desktop checks use a disposable local TLS proxy. The physical Pixel 8 check uses Chrome's localhost secure context.
Memory-mail code verification with `ACCOUNT_TEST_CODE` disabled does not establish real SMTP delivery.
WebKit automation does not establish physical iPhone acceptance.
Read `docs/f04-acceptance-2026-10-20.md` for source identity, commands, test boundaries, and human gates.

Decision: reuse the existing catalog and diary. Add only a bounded public-card cache.
Alternative: merge the complete legacy PWA. Rejected because that would restore an independent online collection and unrelated paths.
Consequence: public cards can open offline after warm-up. Notes, status mutations, new recognition, and source links still require the network.

## 2026-10-20 — Email code boxes

- The owner supplied the current account screen and a six-box reference. The implementation
  uses six visible cells with the existing theme variables instead of the reference blue.
- One native input retains the existing label, numeric keyboard hint, six-digit validation,
  and `autocomplete="one-time-code"`. The visual cells are hidden from assistive technology.
  The field and visual digit content retain Metrika exclusion classes.
- Native selection drives the active cell and selected cells. Pointer input selects one
  existing digit. Arrow keys, Backspace, Delete, and select-all remain native operations.
- The input handler restores the caret after the parent model update. Assigning the model
  and reading it immediately can read the previous prop and move the caret to the end.
- A full pasted code replaces the value from any cell. Shorter pasted text edits the native
  selection. Non-digits are removed before truncation, and leading zeros remain strings.
- Chromium checks used intercepted account replies and `test@example.com`. No email was
  sent. The checks covered both themes at four widths. Device autofill was not tested;
  the browser check supplied a complete value through the native input event.

## 2026-10-20 — Bot landing pages

- `/max` is the MAX mini app (`definePageMeta({ alias: ['/max'] })` in `pages/account.vue`).
  On the main host, `maxHostGuard` redirects `/max` to `/account`. The earlier guide commit
  `b087d387` on `feature/im-bot` used `/max` and never reached `main` for this reason.
  The owner chose `/telegram-bot` and `/max-bot`.
- Feature sources: `telegram-bot/README.md`, `max-bot/README.md`, both `profile.py` files,
  `im-core/.../result_card.py` (caption labels), the `_queue_receipt_text` function of
  `telegram-bot/.../app.py` (receipt text), `docs/account.md` (diary links), and plan 07 (history).
- Both bots: photo, album, image file (JPEG, PNG, WebP, HEIC, HEIF), HEIC to JPEG without EXIF,
  one result for each photo, «✅ Совпало» and «❌ Не совпало» for a single photo, three
  alternatives and «Ничего из этого», tentative answers, the 18+ confirmation with the held
  photo, 50 photos per hour, deletion after 30 days, and diary history records.
- Telegram links to the diary with a one-time `t.me/ChtoZaVinoBot?start=link_<code>` link and has
  `/unlink`. MAX links only in the mini app: MAX forbids a one-time code in a bot message.
- Production on 2026-10-20 at 10:50 MSK (container labels on gx10): Telegram runs `014654bf`
  of GitHub `main` with `BOT_ACCOUNT_ENDPOINT`. MAX runs `3e7c20d2` (2026-10-18), which has no
  diary history records. The `chtozavino-deploy` record still states Telegram `874fbd6`.
- Plan 07 notes an open risk: no source confirms that the MAX mini-app user ID equals the MAX Bot
  API user ID. If they differ, MAX history records get `not_linked`.
- The catalog record of the example wine has no sugar field. The page uses «Сухое» from the
  catalog slug `…-pino-nuar-krasnoe-suhoe-13`.
- `--muted` has 3.93:1 on `--paper` and 3.59:1 on `--cream` in the light theme.
  `color-mix(in srgb, var(--ink) 75%, var(--paper))` has 6.28:1 and 5.73:1 (light) and 8.0:1 and
  6.84:1 (dark).
- Container query units (`cqw`) resolve against an ancestor container, not against the element
  itself. The chat font size is therefore on `.chat-screen` inside the `.bot-device` container.
- In a grid cell with an auto row, an image with `height: 86%` kept its natural height and spilled
  out of the chat bubble. The chat images use `em` heights.

## 2026-10-20 — Android artifact identity

- The release APK uses `com.alolalab.chtozavino`, not the old reverse-order ID.
- The signed APK has 414,941,197 bytes and SHA-256
  `6c9ba0c364f762023818cd6d6885e16359c146e23bc84d8316343a9836c34cb3`.
- Its certificate matches the published 0.1.4 test-signed APK.
- The default query path uses complete Base NaFlex p512 without segmentation.
- Existing product screenshots document version 0.1.4, not the new encoder's results.
- Keep the route filename, runtime file path, page metadata, and archive hash consistent.

## Public site map, 2026-10-19

The Web UI had `public/sitemap.xml` and a sitemap reference in `public/robots.txt`, but no HTML site map.
The `/sitemap` page comes from `feature/im-bot` commit `a82c96c8`. That version reused the application guide links of commit `b087d387`.
The guides are not on `main`. Their `/max` guide page would take the path of the MAX mini app (`isMaxAppPath` in `shared/account.ts`).
The port to `main` therefore lists the existing pages directly: 10 product and project pages and the 3 legal pages from `app/data/legal.ts`.
The `/hackaton` page stays excluded. The account pages `/account` and `/max` are `noindex` and stay excluded.
The page uses the shared age gate and theme variables.
The original page used `--muted` for the lead, the eyebrow, and the card descriptions. That color has a contrast ratio of 3.93:1 on `--paper` in the light theme. The port uses `--ink`.
The footer row links also used `--muted` and were 14 pixels high. They now use `--ink` and are at least 44 pixels high.
The review document of the original version stays on `feature/im-bot` (`a82c96c8`, `docs/reviews/2026-10-19_sitemap-claude-code.md`). It does not describe the port, so `main` does not include it.

A separate Claude agent reviewed the port on 2026-10-19. It found no runtime defect. It reported a misleading copied review document, weak test checks, low contrast and small targets in the footer and eyebrow, and documentation gaps. All of them are fixed.
It also reported an existing problem: on the MAX mini app host, the legal pages show the full site header and footer. Their links lead to pages that this host does not serve. This needs a host-based footer decision and is not part of the port.

Verification on 2026-10-19: type checks, all tests, and the production build passed. Chromium checked `/sitemap` at 320, 390, 768, and 1440 CSS pixels in both themes: 13 cards, 6 groups, all destinations HTTP 200, no overflow, the age gate, and WCAG AA text contrast.

## Legal pages: features on main, 2026-10-19

The legal pages were rebased onto `origin/main` at `7911e52f`. This entry is the evidence for the new sections.

### «Винный дневник» (`account/`, `app/pages/account.vue`)

- Login by a 6-digit e-mail code (10 minutes, 5 attempts) or by Yandex ID. Telegram and MAX can only be linked (`account/src/chto_za_vino_account/service.py`, `yandex.py`).
- The service stores the username, the creation time, the consent and terms versions with times, identities (e-mail address, Yandex user ID with the Yandex `default_email`, Telegram user ID, MAX user ID), session token hashes with the login method and times, and application token hashes with names and times (`schema/001`–`004`).
- Diary entries do not exist yet. Recognition requests are not linked to accounts.
- Yandex: the service reads and stores only `id` and `default_email`. The access token is used once.
- E-mail: SMTP from `noreply@chtozavino.ru`. The deploy records name REG.RU hosting SMTP. The production SMTP host is not recorded.
- Cookies: `__Host-cv_session` (400 days, renewed at every visit), `__Host-cv_email`, `__Host-cv_signup`, `__Host-cv_yandex`, `__Host-cv_next` (10 to 30 minutes). All are `HttpOnly`, `Secure`, `__Host-` (`webui/server/utils/account.ts`).
- Sessions have a 100-year TTL. They end at logout or account deletion.
- Self-service deletion cascades to identities, sessions, link codes, and tokens. Backups keep data for at most 8 days (`account/README.md`). Login and link codes are deleted 1 hour after expiry. Application tokens are deleted 30 days after expiry or revocation.
- The service logs no e-mail address or user IP. Rate limits keep IP addresses in memory only (`limits.py`).
- MAX mini app: the service checks the launch signature and stores only the MAX user ID. Telegram: the bot sends only the Telegram user ID.
- Metrika skips the account pages and hides the code and token fields (`shared/metrika.ts`, `account.vue`).
- The sign-up consent checkbox names only the username and the e-mail or Yandex ID. The owner decided to keep this text until the lawyer review (#45).

### Wine for a dish (`/dish`, `dinner-lens/`)

- The browser re-encodes the photo to JPEG, at most 1600 px, without EXIF, and sends it as base64 JSON (`app/composables/useDinnerLens.ts`).
- The web UI forwards only the validated body to Dinner Lens on gx10. It sends no cookie or client IP (`server/utils/dinner.ts`).
- Dinner Lens and the web UI store no photo, dish name, preference, or result. The continuation cursor is signed and expires after 1 hour.
- The primary model is the local Qwen3.5-9B on gx10.
- The production config has a cloud fallback `qwen3.8-flash` at `maas.qwencloudapi.com`. On 2026-10-19 this host resolved to `8.219.175.122`, registered to Alibaba Cloud (Singapore) Private Limited.
- The owner decided on 2026-10-19 to turn the fallback off. `/privacy` describes local processing only.

### Other changes

- MCP runs on the user's computer over stdio. Its account tools use application tokens.
- The matcher has no retention job yet (`da8c8954` changed only the configuration format).
- The web server moved from Princess to Claudette (Selectel VDS, Moscow) on 2026-10-19.
- Plan 06 (`910e11d7`) serves wine images from `chtozavino.ru/img/wines/`. The browser loads no image from `api.vino-svoe.ru`.
  The server requests wine cards from `api.vino-svoe.ru` with the slug only. `/privacy` no longer lists the portal as a recipient.

### Verification

- 484 tests passed, 20 optional catalog checks were skipped. The type check passed.

## Legal pages: data flow facts, 2026-10-19

This entry is the evidence for `/terms`, `/privacy`, and `/contacts` (`docs/legal-pages.md`, #37).
Sources: `feature/im-bot` at `a82c96c8`, `android/current` at `af19e83d` in `svoe-vino-lab-android`,
`main` at `2e1d4033` in `svoe-vino-lab-iphone`, and the `chtozavino-deploy` records.
Production runs other commits: Web UI `e678cf0c`, matcher `dce69cf4`, Telegram bot `874fbd6`, MAX bot `3e7c20d2`.
The user-facing bot texts are the same in these commits and on `feature/im-bot`.

### Website

- The single-bottle page sends `POST /api/predict`. The shelf page sends `POST /v1/group/match`. Both send one multipart `image` (`app/composables/useWineScanner.ts:76-77`, `useShelfScanner.ts:55-56`).
- The Web UI keeps the photo in memory and forwards only the image to the matcher (`server/utils/prediction.ts:60-98`, `server/utils/group.ts`). It writes no photo, mask, or response to disk or logs.
- The website photos do not pass the bot moderation service.
- `app/components/PhotoScanner.vue:81` says «Фото не сохраняется». This text is false, because the matcher archives the photo.
- First-party browser storage: `localStorage` keys `svoe-vino.age-confirmed.v1` and `svoe-vino.theme.v1`. First-party code sets no cookie.
- The service worker caches pages and static files. It does not cache photos or `/api/` and `/v1/` responses (`nuxt.config.ts:89-143`).
- Yandex.Metrika counter `113460637` loads in the server-rendered head of every page, before the age gate. No consent banner exists (#41).
  Options: `webvisor:false`, `clickmap:true`, `trackLinks:true`, `accurateTrackBounce:true`, `ecommerce:"dataLayer"` (`shared/metrika.ts:11`). The code sends no goals or parameters.
- Wine images load from `api.vino-svoe.ru` with `referrerpolicy="no-referrer"`. The server requests wine cards from `api.vino-svoe.ru` with the slug only.
- Caddy access logs on Princess keep the client IP, user agent, path, and status for 7 days (`princess/Caddyfile`, `roll_keep_for 168h`).
- The website has no account, sign-in, or contact form.

### Matcher archive

- The matcher saves every accepted image and a `request.json` file for `/v1/eval/predict`, `/v1/match`, and `/v1/group/match` (`matcher/app.py:289-378`, `matcher/audit.py:42-80`).
- `request.json` contains the time, the client IP, the request headers with credentials redacted, file metadata, and the result.
- This applies to website, bot, and API requests. The bots send the full source image.
- No retention job exists (`gx10/matcher-prod.md:313`). Snapshots go to the ds1825 NAS and the owner's T7 drive. No job removes old snapshots.
- Matcher Inspector shows the archive on the LAN without authentication (`gx10/matcher-inspector.md`).

### Telegram and MAX bots

- The bots store the user ID, the chat ID, the available first name, last name, and username, the age choice and its date, the source photo, processing artifacts, moderation and quality results, recognition candidates, feedback, filter-error reports, and step timings (`telegram-bot/src/chto_za_vino_bot/storage.py:192-311`, `max-bot/src/chto_za_vino_max_bot/storage.py:207-358`).
- The MAX bot also stores the raw update JSON in `update_inbox` for about 1 to 2 days, and the texts of its own messages with keyboards (`sent_messages`).
- The bots store an image sent as a file without change, except HEIC and HEIF. EXIF metadata can stay in such a file (`im-core/src/chto_za_vino_core/image_types.py:58-78`).
- The bots do not store a phone number, a language, or a terms-acceptance record.
- The bots delete finished requests, files, and artifacts after 30 days (`config.py` refuses another value in production). A profile without requests is deleted at the same time. Photos sent before the age confirmation are held for 24 hours.
- No self-service deletion exists. The operator deletes a user with `chto-za-vino-delete-user` or `chto-za-vino-max-delete-user`, or one request with «Удалить запрос» (not deployed yet).
- Moderation (ShieldGemma 2), SAM3, and the matcher run on gx10. They receive the image without user identifiers.
- Data leaves the operator's hosts only to Telegram, to MAX, and as catalogue image requests to `api.vino-svoe.ru`. The reply can contain the user's own photo when the catalogue image is not available.
- Bot logs contain no user ID, name, or message text. Docker keeps 5 files of 10 MB for each container.
- The bots state the purposes «для работы сервиса и улучшения качества распознавания» (`profile.py`). The specifications collect difficult images for recognition improvement.
- Copies outside the 30-day retention: the matcher archive, the old Telegram data on the NAS, and the Telegram deployment backup of 2026-09-29.

### Mobile apps

- Android (`chtozavino.alolalab.com`, 0.1.4) and iOS (0.1.0) recognize wine and look up codes on the device. Their code has no upload or HTTP client.
- The apps open `vino-svoe.ru` pages in the browser. The apps have no analytics, crash reporting, ads, or account.
- Android uses Google Code Scanner from Google Play services. Its dependencies add the `INTERNET` permission and Google log transport. The code does not show what Google collects.
- History: up to 50 rows and a bottle preview on the device. The «Очистить» action deletes them. Android keeps camera originals in the app cache.
- The website offers a debug APK. Its test HTTP server is off by default.
- No evidence shows that the iOS app is distributed.

### Hosting

- `chtozavino.ru` and `api.chtozavino.ru` run on Princess, a Selectel VDS. The region is not documented.
- The bots, the matcher, and the models run on gx10 in the owner's home LAN. The country is not documented.
- The documents do not state the location. The owner confirmed on 2026-10-19 that all these hosts are in Russia.

### Owner decisions, 2026-10-19

- Keep every photo for 30 days, including the matcher archive and its backups. A cleanup job is necessary before deployment.
- Describe Yandex.Metrika as it works now. Do not claim consent until the #41 banner exists.
- Replace «Фото не сохраняется» on `/`.
- Show e-mail, Telegram, and MAX on `/contacts`. The MAX handle is not known yet, so the page shows e-mail and Telegram.

### Verification

- Chromium (Playwright) checked `/terms`, `/privacy`, and `/contacts` at 320, 390, 768, and 1440 CSS pixels in both themes.
- No age gate, no horizontal overflow, one H1, the footer links, and `aria-current` passed on every page.
- The age gate stays on `/` and `/sitemap`, also after client navigation from a legal page.
- The fragments `/privacy#max` and `/terms#android` scroll to their sections. The skip link gets the first focus.
- The light theme `--muted` color has a contrast ratio of 3.93:1 on `--paper`. This is below WCAG AA for small text.
  The legal pages use `--ink` for the lead, the revision date, the term labels, and the footer legal links. All measured text is at least 4.5:1.
- Other site elements that use `--muted`, for example the eyebrow labels and the footer text, keep the low contrast. Accessibility issue #35 tracks the site.

## iPhone landing status note, 2026-10-19

The owner removed the TestFlight preparation note below the release facts.
The WebApp action and the GitHub issue 36 release-status action remain available.
The page does not add another replacement notice.

## iPhone landing page, 2026-10-19

The native iPhone application supports iOS 17.2 and later.
The verified simulator used an iPhone 17 Pro with iOS 26.2.
The verified application pack contains 2,093 wines and 2,093 images.
The simulator does not provide Neural Engine execution.
The landing page does not present simulator speed as physical-device speed.

The default encoder is SigLIP2 Base NaFlex p512.
The application also includes SigLIP2 Base 224 and MobileCLIP2-S2.
The application includes DIS and YOLO26n-seg segmentation.
The settings offer `Авто`, `ANE`, and `CPU` compute modes.

The optimized simulator search stage took 11 ms.
The warm DIS and NaFlex request took 3,216 ms.
The warm YOLO and NaFlex request took 1,884 ms.
The landing page shows only the 11 ms search value and gives its simulator context.

The final accessibility run passed 12 unit tests and 6 accessibility UI tests.
It covered VoiceOver, Dynamic Type, Reduce Motion, Reduce Transparency,
Voice Control, Switch Control, focus movement, status announcements, and 44-point controls.

The project has no public TestFlight link.
The page uses the WebApp as the available action.
GitHub issue 36 is the release-status action.

## Wine Crocodile highlight content, 2026-10-19

The owner removed the round-time and score highlights below the hero.
Use the existing three difficulty levels and the fact-or-legend card stories as replacement benefits.
Keep the detailed rules unchanged.

## Wine Crocodile hero wording, 2026-10-19

The owner supplied exact replacement text for the hero tagline and photo caption.
Keep the supplied wording. Use a line break before the alcohol-free participation statement.

## Live producer-map validation, 2026-10-19

The committed Linux release `772a396e` is active at 18:20:46 UTC. All 25 map routes render the expected product counts.
All 157 added bottle images match the source bytes. Chromium and WebKit each pass 15 staging and 15 live checks.
The first live WebKit harness run logged deferred Nuxt manifest errors during rapid hard navigations.
A focused check returned HTTP 200 with automatic and explicit same-origin Basic authentication.
The final harness waits for the deferred response before replacing a page and passes its strict console-error check. No application code changed for this check.
The private deployment evidence preserves the first result and the final script.
All 532 Linux tests pass with the full pinned snapshot. Browser checks still use emulated viewports; physical-phone testing remains unperformed.

## Map merge and coverage, 2026-10-19

GitHub `main` at `910e11d7` already contains the index and page layout as `6d0cae18` and `d9cdc6cd`.
The local equivalents are `96a9d190` and `c61b428e`. The merge retains the existing `main` behavior and adds six producer maps.
Log and sitemap conflicts retain the newer `main` entries. The two new producer log sections remain at the top.

The full snapshot hash remains `e915493a0a960df040b4055d33c815940e48fb1a2994a7979a819786b2c41961`.
The resolver covers 1,135 exact slugs and three verified aliases. One supported card remains intentionally unplaced, and 964 cards have no producer map.
The 25 maps cover 1,138 of 1,139 supported-producer cards. Golubitskoe includes both verified exact source names.
The MCP bundle is a different source: it has 1,127 exact mapped Active IDs and three aliases. Its remaining 963 Active IDs return unavailable.

## Five more producer maps, 2026-10-19

The requested batch covers Golubitskoe Estate, Chateau de Talu, AYA, Раевское and Имение Сикоры.
The exact producer subsets contain 31, 26, 27, 23 and 21 records. The independent attribution test found two more Golubitskoe cards under `Поместье Голубицкое`.
Official sources identify both Golubitskoe names with the same winery. The map covers all 33 cards and preserves the exact producer field for every source row.
Classic Chardonnay is one of these linked cards. The official-only Golubitskoe addition is Tête de Cheval Semi-dry.

The batch adds 130 exact snapshot identities and five selected official additions. It does not claim full current producer coverage.
The registry test now accepts an explicitly pinned set of exact producer names for a map. It checks each crosswalk producer against the independent full-catalog projection.
The absence check for Golubitskoe must cover both producer names.

Golubitskoe separates the main and reserve Tête de Cheval families. Their prices are not compared with still-wine ranks.
The current Petnat White grape list differs from the saved card. Keep the historical grapes and mark the limitation.
Southern Vertical and Miroir de Talu, and Раевское Eklego and Glow, use snapshot-only groups at rank 0.
The direct Talu HTML endpoints return HTTP 502. Source hashes for these pages identify retrieved web-extracted text, not raw HTML.

The Southern Vertical Cabernet Franc image has an opaque white background. Built-in imagegen creates one transparent display derivative.
The complete contour, capsule, glass and main label artwork pass light and dark inspection. Generated fine print is not product-identity evidence.
The original catalog image, generated image and final asset hashes and exact English prompt are in `docs/product-line-maps/chateau-de-talu/imagegen-cutouts.json`.
All other saved bottle images retain their original WebP bytes. Official PNG additions use lossless WebP encoding.

The broad WebKit producer run passed 102 cases before a network-idle timeout on the existing Zolotaya Balka mobile page. It recorded no browser errors.
The producer browser suite now fulfills external analytics requests locally. This keeps map checks independent of remote analytics availability.
The rerun passes all 105 WebKit producer cases. Chromium also passes all 105 cases. Both engines pass 145 targeted cases and the Abrau regressions.

## Burnier product-line map, 2026-10-19

The neutral band uses the UI heading «Другие коллекции». The price explanation remains in the description.

The exact producer filter finds 20 `Винодельня Бюрнье` rows in the pinned catalog snapshot.
The official catalog lists 22 wines. White and red Exponat are absent from the saved producer rows.
The new map keeps these two additions without catalog links.

The original dark labels, wax capsules and official catalog image alt text identify three Elite Series wines.
Their official cards specify 36 months in French barriques. This supports an editorial premium cue.
The sources do not establish the relative prices of Classic, Lyublyu, Vinisazh, Exponat and late harvest. These groups use rank 0.

The Pinot Blanc snapshot row points to the Viognier image. The original label confirms the mismatch.
The map uses the official Pinot Blanc image and retains both input hashes in the crosswalk.
No vintage equivalence is inferred. Names, grapes, descriptions and slugs remain exactly as saved.
The other 19 saved WebP images retain their bytes. Three official PNG images use lossless WebP encoding.
Read `docs/product-line-maps/burnier/sources.md` for the evidence and limits.

## 2026-10-19: Wine Crocodile page evidence

The owner selected a separate `/crocodile` route in the existing portal.
The existing game worktree contained unrelated edits. Use the isolated `codex/wine-crocodile-landing-20261019` worktree.
Use the approved thirty-card source for six examples. Keep the coupe story labeled as an unverified legend.
Use the owner's photos for two retouched editorial compositions. Do not use generated microtext as factual evidence.
The page exposes local card flips and filters. It does not claim online multiplayer, sales, reviews, or expert validation.
Keep the existing physical print masters byte-identical in the download directory.
Read `docs/crocodile-landing.md` for the full page contract and the browser verification command.

## Automatic Dinner Lens updates, 2026-10-19

The owner removed the explicit confirmation step for dish-to-wine recommendations.
Decision: refresh after a recognized image, explicit dish choice, and heat or sauce change.
Debounce typed names for 450 ms. Cancel previous requests and ignore their late results.
Taste changes during image recognition must preserve the recognition request and apply after it resolves.
Keep the editing focus. Announce the latest results without moving to the wine cards.
An unresolved image must retain clarification. A failed recommendation has a contextual retry action.
Seven scheduler regressions cover rapid text edits, explicit choice, stale responses, recognition settings,
empty names, cancellation, route disposal and availability. Desktop/mobile browser checks cover the same entry paths.


## Game card replacement, 2026-10-19

The owner identified the blind-style quiz mock in a screenshot and requested a link to the game landing page in that position.
Decision: replace that card with the existing Wine&Dine Merge artwork and a `/game` link.
Use a working-prototype badge and accurate merge-game copy. Do not imply that the merge game implements the former quiz.


## Game landing evidence, 2026-10-19

The game is a separate public PWA at `game.chtozavino.ru`.
Version `0.8.22` has six main route regions, eight optional regions, and a separate pouring mode.
The owner selected a main-portal landing page reached from `/ideas`.
Decision: add `/game` and a separate Game invitation on `/ideas`. Keep the existing game root and pouring URL.
This preserves campaign storage under its current origin and keeps the blind-style quiz mock distinct.
Use original game SVG artwork as local static assets. Do not import the game runtime into Nuxt.
Runtime SVG strings can contain HTML boolean attributes and CSS-controlled overflow layers.
Standalone image exports need valid XML attributes and explicit removal of inactive overflow artwork.
Check regional menu names against current `WINE_STAGES` and the Russian catalog before publishing copy.
Read [the page contract](docs/game-landing.md) for the source revision and verification procedure.
Vue scoped styles need the complete dark descendant selector inside `:global(...)`.
A trailing descendant outside that construct can be omitted by the scoped transform.
The narrow dark browser check detected an unintended root border from that pattern.
The corrected selectors preserve the root dimensions and all 16 production layout checks pass.

## Bottle result overlap, 2026-10-19 (#67)

The owner reported that a bottle covers «Лучшее совпадение» in the result for «БЮРНЬЕ.КРАСНОСТОП сухое красное».
The desktop container was 205 px high for a 250 px image. The mobile container was 215 px high for a 245 px image.
A local browser check reproduced a negative gap between the image box and the label: -13.5 px at 1440 px and -5 px at 390 px.
The container now takes its height from the image and cannot shrink. The existing bottom margins give a gap of 9 px on desktop and 10 px on mobile.
The same long title exposed clipping in the grid at narrow widths. The result panel now has `min-width: 0`, and the title can wrap inside a long word.
Browser verification uses intercepted prediction and metadata responses with local bottle assets. It does not measure recognition quality or verify production deployment.

## Dish uploads, 2026-10-19

The dish uploader previously rejected HEIC by MIME before decoding and had no drop handler. Bottle/shelf HEIF handling belongs to the matcher and cannot supply a normalized dish image without an unrelated recognition call.
The dish path now checks signatures and normalizes locally. Pinned `heic-to` 1.6.6 uses libheif 1.23.6. Its CSP build runs inside a disposable outer worker so that cancellation releases its decoder work. HEIF metadata dimensions are checked before decoding. The client deadline allows the preparation budget before the existing upstream budget.
An actual macOS-encoded synthetic HEIC with EXIF orientation 6 produces the expected 32×64 red-top/blue-bottom JPEG in Chromium and WebKit. WebKit can add technical EXIF to its canvas output; the test checks that source metadata is removed instead of rejecting all browser-generated EXIF. The decoder is loaded only for HEIC and is excluded from PWA precaching.

## Producer map index and page layout, 2026-10-19

The owner asked for the map pages to use the page space instead of a scroll box inside the page.
The canvas content already reflows: tiers hold groups in a CSS grid, and groups hold products in a grid. Only the fixed 1120 px canvas width, the scale transform, and the fixed viewport height made it a scroll box.
The page layout removes those three and uses `auto-fill` grids. At 1440 px the groups use 3 columns. At 390 px they use 1 column.
The page map then scrolls the window. Centering, «Перейти к группе», and the expand-all anchor use window coordinates.
After the change, the first-load JavaScript of `/` is 135 KB gzip. The index summary adds about 1 KB.
The index holds the first image of each map as its cover. A chunk marker in the tests must therefore use another image of the map.
`/lineup` returns no `x-robots-tag`. `/lineup/abrau-durso` returns `noindex, nofollow, noarchive` with the rule `/lineup/*`.

## «Винный дневник» web part, 2026-10-19

The account service runs on gx10 in the LAN. Nuxt runs on the public edge host and reaches it only through a reverse SSH tunnel.
So the browser talks only to same-site `/api/account/*` routes. The routes hold the service token and keep every service secret in httpOnly `__Host-` cookies.
The header link must not call the service on every page. Nuxt decides it during SSR from `NUXT_ACCOUNT_ENDPOINT` and serializes the flag with `useState`.
Decision: the session cookie is SameSite=Lax. The Yandex flow cookie must be Lax too: the Yandex callback is a top-level GET navigation from `oauth.yandex.ru`.
The Yandex callback is a server route that answers only with HTTP 302. Metrika sends `location.href`, so a page callback would leak the one-time code to analytics.
Decision: the Metrika init script skips `/account*`. A visit that starts on another page still loads Metrika; the plugin then sends no hit for `/account*`.
Caddy is the only proxy in front of Nuxt. The last `X-Forwarded-For` entry is the client address only when the socket is loopback.
Playwright route interception does not see the target of a redirect after a navigation. The end-to-end check reads the 302 of the start route with `maxRedirects: 0`.
The service allows one email code per minute for an address. The end-to-end run checks the limit message, then waits for the window.
The service deletes an account only after a login in the last 15 minutes. Without a reauth control the person met a dead end. The confirmation panel now offers a fresh login (reported by session svoe-vino-final-39).

## Dinner Lens mode, 2026-10-19

The existing mode selector uses separate `/` and `/shelf` pages. A third route preserves navigation and unmount cancellation semantics. The 320-node label export is separate from wine rules and curation.
The backend currently accepts inline JPEG/PNG. The browser therefore normalizes supported files to an oriented metadata-free JPEG before upload. Safari camera input is explicit; unrenderable HEIC needs a JPEG copy.
The recognition endpoint also returns class-level wine suggestions. The UI intentionally withholds them until the user confirms or corrects the dish. Confirmation calls the deterministic selection endpoint and does not repeat vision.
The Nuxt proxy uses a private endpoint and environment-injected token. It strips provider receipts and diagnostics, bounds JSON before parsing, rejects redirects and checks exact source links.
The existing optional producer snapshot tests remain optional. New state and proxy tests cover stale replies, cursor preservation, duplicates, explicit negative attributes and fail-closed service errors.
The actual service check returns 8 ribeye wines, 12 Olivier wines and 12 king crab wines. Each case reaches discovery choices after five curated choices and exhausts the cursor without duplicates. A real photo traverses browser normalization, the private proxy, recognition, user confirmation and deterministic selection with one vision request.
The independent Opus review caught hidden manual-input clarification and identified focus and retry improvements. A persistent live region now announces state, category fallback receives focus, and continuation focuses its first new heading. Recognition retry is tied to the failed step. Manual corrections clear the stale category. Prototype attribute keys fail validation instead of throwing; malformed JSON produces the localized incomplete-result message.
Desktop Chromium and mobile Chromium/WebKit pass the mode, state, error and layout checks. Both themes pass the upload-action contrast check. The test caught a low-contrast secondary upload action in the existing mobile dark palette; the shared upload style now keeps its accent text readable.

## Producer map loading, 2026-10-19

The scanner page chunk imported `shared/product-line-map.ts` statically. That module imported all 19 map JSON files.
The first-load JavaScript of `/` was 296 KB gzip in 12 files. The map data chunk was 181 KB gzip (1.3 MB raw), 61% of it.
One map is 4.7 to 21.6 KB gzip. An index with producer names, aliases, slug prefixes, and slugs is 13 KB gzip.

Vite makes one chunk for each explicit `import('./<id>.json')` in the registry. Nitro also accepts these dynamic imports in the shared module.
`/lineup/<producer>` keeps server rendering through `useAsyncData`.
The service worker precaches `_nuxt/**/*.js`, so the map chunks download in the background after the first visit. Product images are not precached.
TypeScript infers a literal type with all 985 slug keys for the index JSON. A direct cast to `ProductLineIndex` fails, so the module casts through `unknown`. The index test checks the content.

After the change, `/` loads 139 KB gzip by the same method (134 KB with `npm run test:bundle`). No page prefetches a map chunk.

A review claimed that Chromium caches a failed dynamic `import()`, so that a retry cannot recover.
A local check with Playwright 1.64.1 did not confirm this. In Chromium and WebKit, a second `import()` after a blocked request sent a new request and loaded the module.
Firefox was not checked. The browser suite now tests a blocked map chunk followed by a successful retry.

`npm run test:line-map` failed on `main` before this change. It clicked a «Вся полка» button. The mode pages changed the mode switch to links. The suite now clicks the link.

## Matcher answer for HEIC without HEIF support, 2026-10-18

The production matcher has no HEIF support (#24). A staging check on Princess sent a real HEIC photo.
`/v1/eval/predict` and `/v1/group/match` of the matcher answered HTTP 422 `image file is invalid or damaged`.
The portal changed 422 to 502, so the page asked the visitor to retry. A retry cannot help.
The portal now passes 422. The page shows a HEIC-specific message for a HEIC photo.

## Mode pages and HEIC uploads, 2026-10-18

The owner chose `/` for «Одна бутылка» and `/shelf` for «Вся полка».
`/` stays the default, so existing links and the evaluator flow do not change.
Other pages use English slugs (`/android`, `/ideas`, `/presentation`).
Each mode page renders `ScannerPage`. A mode switch is a navigation, so Metrika records a page view with the page title.

The owner chose to send HEIC to the matcher without conversion in the browser.
The production matcher rejects HEIC until #24 is deployed. Issue #44 has the deploy order: matcher first, then the web UI.
An iPhone file picker can convert HEIC to JPEG when the `accept` list has no HEIC type. This behavior was not verified on a device.
With HEIC in the `accept` list, iPhone Safari can send the original HEIC. That is the reason for the deploy order.
The server check reads the `ftyp` box. The major brands `heic`, `heix`, `heim`, `heis`, `hevc`, `hevx`, `hevm`, `hevs`, `mif1`, and `msf1` pass.
AVIF (`avif`) gets HTTP 415. The matcher decodes the image with `pillow-heif` and makes the final decision.
Chrome and Firefox cannot show HEIC in an `img` element. The preview then shows a text. The shelf result has a JPEG preview from the matcher.
A Chrome probe with a fake matcher confirmed the preview text, the match in both modes, and `image.heif` on both matcher endpoints.

## Cookie consent under Russian law, 2026-10-18

The owner asked whether Russian law requires cookie consent for `chtozavino.ru`. Issue #41 has the full analysis and sources.
152-FZ article 9 part 1 requires specific, informed, conscious, and unambiguous consent.
Since 01.09.2025 (156-FZ), the consent must be separate from other information and documents that the person confirms or signs.
Article 9 part 3 puts the burden of proof on the operator.
The Metrika terms of 07.08.2026 make the site owner the operator and Yandex the processor.
The owner must inform visitors and obtain consent where the law requires it.
KoAP 13.11 part 1 (edition of 04.08.2026) fines citizens 10,000–15,000 ₽ for processing without a lawful basis.
The law has no cookie-specific rule. The regulator position that identifying cookies are personal data is reported, not found in an official document.
Conclusion: load Metrika only after an explicit choice. Remove the `noscript` image.
Keep the cookie choice separate from the 18+ confirmation. A lawyer should review the consent text.

## Metrika page title on client navigation, 2026-10-18

A Codex review of the port found that a client-navigation `hit` used the title of the previous page.
The `hit` method uses `document.title` when `options.title` is absent.
Reference: https://yandex.ru/support/metrica/en/objects/hit
`router.afterEach` runs before Nuxt renders the head of the new page.
Nuxt pauses head rendering on `page:start`. Its `page:finish` hook queues the head render with `setTimeout(0)`.
`NuxtPage` calls `page:loading:end` once for each navigation.
For a new page, it calls the hook after `page:finish`. For a reused page, it calls the hook on the next tick.
A reused page has the same route key, for example after a hash change or after `/IDEAS` → `/ideas`.
The plugin queues each hit in `router.afterEach`. A `setTimeout(0)` from `page:loading:end` sends the queue.
That timer runs after the head render timer, so `document.title` is the title of the new page.
A first fix used `page:finish` and the path string. Codex found that `/IDEAS` → `/ideas` then lost the hit.
A Chrome probe blocked all `mc.yandex.ru` requests and recorded `ym` calls.
Before the fix, `/ideas` → `/android` and browser Back sent the previous title.
After the fix, four navigations each sent one hit with the title of its own page:
the link, browser Back, the in-page anchor `#implemented`, and `/IDEAS?utm_source=campaign` → `/ideas`.
Production release `10632011` still has the defect.

## Eight producer review resolution, 2026-10-17

The external review identified evidence gaps and unsafe group-level generalizations. Original-label checks corrected four ESSE placements and separated uncertain historical Chateau Pinot blends. Some AGORA concerns were disproved by exact official pages. Read docs/reviews/2026-10-17-eight-producer-maps-resolution.md for every disposition and verification limit.

## soyuz-vino review correction, 2026-10-17

The current catalog does not establish the historical wine collections or their price ranks. Current Lavetti ciders do not identify older wine records.

## valery-zakharyin review correction, 2026-10-17

The original labels confirm Reserve status in different collections. The Rubedo page alone cannot establish the autochthon reserve identities.

## chateau-pinot review correction, 2026-10-17

A current blend with the same grapes does not prove the historical collection. Two original labels explicitly identify Gravity.

## esse review correction, 2026-10-17

Original Pinot Noir, Chenin Blanc, Odessa Black, and Saperavi Heaven photos read ESSE UNPLUGGED. They do not support KACHA VALLEY membership.

## sober-bash review correction, 2026-10-17

The official Грани collection lists all six retained varietal and blend identities. Collection membership is not limited to the first three entries.

## belbek review correction, 2026-10-17

The contradictory Белое сухое card can be a Reserve counterpart. Its conflicting fields do not establish exact equivalence.

## agora review correction, 2026-10-17

The official range index supports CUVEE premium wording and the current 12–18 month Reserve Yachting range. Historical cards only establish 12 months or more.

## novy-svet review correction, 2026-10-17

The snapshot does not establish one premium rank for all special Novy Svet releases. Two short varietal identities lack a confirmed collection.

## Sober Bash amphora source, 2026-10-17

The saved official Грани page lists all four amphora products in the map. The reserve collection URL did not establish this membership. Keep the existing products, groups, and relative tiers.

## Novy Svet absence scope, 2026-10-17

The Novy Svet display name differs from the exact snapshot producer value. A literal query with the display name can select zero rows. Scope the absence check to Новый Свет. Дом шампанских вин and retain the 44-card baseline.

## Eight producer map verification, 2026-10-16

The eight producer extracts contain 370 exact snapshot identities. The full catalog coverage is now 988 of 2103 cards. An exact producer-field check found a separate Сатера card outside the ESSE scope. Source checks distinguished alcoholic and alcohol-free La Petite Perle cans. Read docs/validation/eight-producer-maps.md for evidence and source limits. Automatic approval review rejected the external Claude packet transfer; explicit owner approval is pending.

## Союз-Вино, 2026-10-16

Check Союз-Вино against the exact catalog producer field and official collection sources. Preserve separate snapshot identities. Record editorial tiers and source limitations in docs/product-line-maps/soyuz-vino/sources.md.

## AGORA WINERY, 2026-10-16

Check AGORA WINERY against the exact catalog producer field and official collection sources. Preserve separate snapshot identities. Record editorial tiers and source limitations in docs/product-line-maps/agora/sources.md.

## Собер Баш, 2026-10-16

Check Собер Баш against the exact catalog producer field and official collection sources. Preserve separate snapshot identities. Record editorial tiers and source limitations in docs/product-line-maps/sober-bash/sources.md.

## Бельбек, 2026-10-16

Check Бельбек against the exact catalog producer field and official collection sources. Preserve separate snapshot identities. Record editorial tiers and source limitations in docs/product-line-maps/belbek/sources.md.

## Новый Свет, 2026-10-16

Check Новый Свет against the exact catalog producer field and official collection sources. Preserve separate snapshot identities. Record editorial tiers and source limitations in docs/product-line-maps/novy-svet/sources.md.

## Валерий Захарьин, 2026-10-16

Check Валерий Захарьин against the exact catalog producer field and official collection sources. Preserve separate snapshot identities. Record editorial tiers and source limitations in docs/product-line-maps/valery-zakharyin/sources.md.

## Шато Пино, 2026-10-16

Check Шато Пино against the exact catalog producer field and official collection sources. Preserve separate snapshot identities. Record editorial tiers and source limitations in docs/product-line-maps/chateau-pinot/sources.md.

## ESSE, 2026-10-16

Check ESSE against the exact catalog producer field and official collection sources. Preserve separate snapshot identities. Record editorial tiers and source limitations in docs/product-line-maps/esse/sources.md.

## Abrau-Durso catalog completion, 2026-10-16

The saved producer snapshot contains 57 cards. The initial sheet map represented 35 cards through canonical slugs and aliases.
Twenty-one identified cards belong to five still-wine groups. Keep every distinct snapshot identity.
The owner excluded `rozovoe-polusladkoe-2` until exact bottle and collection identification.
The extended map represents 56 cards through 53 canonical slugs and three aliases. It retains all 20 gray products.
The map has 73 product nodes in 19 groups.
Official collection pages establish premium Abrau-Durso positioning and medium Abrau Estates positioning.
Current blends can differ from snapshot blends. Keep the saved product description and grape values.
Abrau Collection is also the current name of the retro-car still-wine range. Keep this group separate from sparkling cans with that name.
Az Abrau and Femme d’Abrau have a neutral price tier. Their sources do not establish one common price rank.
All 21 source bottles already have transparent backgrounds. No generated label or new segmentation is required.
The larger premium section exposed initial-centering drift in Chromium after web-font loading changed a group heading height.
Wait for `document.fonts.ready` before measuring a center target. Keep the delayed-font browser regression.
An existing in-app Abrau tab still displayed the old 52-product client. Full navigation loaded the new 73-product client.
The catalog still contains large producers without maps. The largest exact producer fields are Союз-Вино (69), ESSE (53), Шато Пино (50), Валерий Захарьин (46), and Новый Свет. Дом шампанских вин (44).
Read `docs/validation/catalog-lineup-coverage.json` for the complete ranking and source hash.
Counts refer to catalog cards. They do not measure production volume.


## Missing bottle-image recovery, 2026-10-16

The owner clarified that the reported card means the bottle image.
The registry contains 647 products in 11 producer maps. Eleven image values were null.
Eight unresolved Zolotaya Balka snapshot photos have exact official product photos.
The Massandra base collection supplies its missing white semi-sweet bottle photo.
The Fanagoria rose semi-sweet official card supplies a real single-bottle photo for «Она сказала Да!».
This photo replaces an unrelated generated wedding scene.
The official 5000 page assigns a Cabernet Franc label photo to a Cabernet Sauvignon caption.
Use that assigned official photo with a visible discrepancy badge. Do not change the label or infer a wine_slug.
A small 74x254 Zolotaya Balka source triggered two unwanted generated halos.
The accepted edit starts from the original small photograph and retains its modest detail.
Inspect light and dark composites. An alpha channel alone does not prove a clean outline.
Read each changed producer’s `image-recovery.json` for URLs, hashes and exact built-in imagegen prompts.
Catalog identities, descriptions, grapes, groups and links stay unchanged.

## Visible bottle size, 2026-10-16

The image element height does not establish the visible bottle height.
A square image with transparent side fields can reach max-width before the requested height.
31 reviewed images rendered at approximately 118–127 px inside a 176 px desktop image area.
Measured JSON frames remove this source-canvas dependency. The renderer preserves the original source pixels.
Cropping source assets would change their bytes. Runtime alpha scans would add work to mobile navigation.
Use measured frames for stable server-rendered layout. Read `docs/product-image-sizing.md`.
A framed source image can extend beyond its clipped wrapper. Use the wrapper bounds in visual checks.
WebKit can keep decode() pending for a hidden lazy image. Load only the images required by a screenshot check.
The gray filter can belong to the frame wrapper. Check the rendered image container when verifying the filter.

## Complete lineup image review, 2026-10-16

The manual review covers 636 image files in 22 light and dark contact sheets.
One additional mask defect occurs beside the Decanter Saperavi 2017 neck.
The replacement uses the original catalog image and built-in imagegen.
31 images have large transparent fields and an approximate desktop bottle height below 130 px.
A square source canvas can reduce a narrow bottle to 120 px under the CSS max-width limit.
Read `docs/validation/lineup-image-visual-review.md` for the full scope, correction and open framing observations.

## Fanagoria Decanter background remnants, 2026-10-16

The previous Rkatsiteli 2019 cutout contained opaque gray and white stripes outside the right contour.
The earlier alpha, border and geometry checks did not detect this defect.
A transparent border can surround an image that still contains an opaque background remnant.
Regenerate from the original source. Inspect the complete outline on contrasting flat backgrounds.
Use the original catalog image as the edit target. Do not use the defective derivative as the source.

## Product image backgrounds, 2026-10-16

An alpha channel alone does not prove that a photo has no background. Three 5000 scene images had only a few transparent corner pixels.
The full image audit found 84 backgrounds among 638 referenced files.
The user selected built-in imagegen. The accepted result contains 82 cutouts and two labeled placeholders for unverified source photos.
Imagegen can change fine print and reflections. Review must check the main bottle identity before acceptance.
A wide field of nearly transparent pixels can reduce bottle scale under CSS max-width. Frame the output from visible alpha and verify the actual desktop and mobile sizes.
Read `docs/validation/product-image-cutouts.md` for the decisions, exact prompt manifests, source conflicts, and checks.

## Producer map verification, 2026-10-16

The ten new maps contain 595 products in 132 groups.
562 nodes preserve exact snapshot cards. 33 nodes are verified official additions.
Nine snapshot products have no confirmed local image.
A missing image and a missing catalog link are independent states.
A controlled HTTP 404 image probe passed in Chromium and WebKit at mobile and desktop sizes.
The selected product and portal link remain unchanged when its image fails.
The full 2,103-record snapshot check found no false producer attribution.
Gray additions and all 586 new image checksums match their crosswalk records.
The implementation review identified hidden group caveats and ambiguous volume-only labels.
The final UI exposes group caveats and keeps group methods separate from product facts.
Read `docs/validation/producer-maps.md` for the full verification scope.
Read `docs/reviews/2026-10-16-producer-maps-resolution.md` for review decisions.

Wrong: use `import.meta.glob` in the shared map module.
Right: use explicit JSON imports in the shared map registry.
Nitro preserves the glob call in its server output and returns HTTP 500.
Unit tests alone did not detect this server integration failure.


## Мысхако, 2026-10-16

The map covers 92 exact catalog slugs from 2026-09-17.
The map adds 5 verified products without a catalog match.
0 products have no verified local image and use the explicit placeholder.
Read `docs/product-line-maps/myskhako/sources.md` for collection evidence and limits.

## Кубань-Вино, 2026-10-16

The map covers 97 exact catalog slugs from 2026-09-17.
The map adds 6 verified products without a catalog match.
0 products have no verified local image and use the explicit placeholder.
Read `docs/product-line-maps/kuban-vino/sources.md` for collection evidence and limits.

## Фанагория, 2026-10-16

The map covers 102 exact catalog slugs from 2026-09-17.
The map adds 6 verified products without a catalog match.
0 products have no verified local image and use the explicit placeholder.
Read `docs/product-line-maps/fanagoria/sources.md` for collection evidence and limits.

## ЗМВ Коктебель, 2026-10-16

The map covers 26 exact catalog slugs from 2026-09-17.
The map adds 2 verified products without a catalog match.
0 products have no verified local image and use the explicit placeholder.
Read `docs/product-line-maps/koktebel/sources.md` for collection evidence and limits.

## Ведерниковъ, 2026-10-16

The map covers 43 exact catalog slugs from 2026-09-17.
The map adds 2 verified products without a catalog match.
0 products have no verified local image and use the explicit placeholder.
Read `docs/product-line-maps/vedernikov/sources.md` for collection evidence and limits.

## Shared module loading, 2026-10-16

Nitro preserves import.meta.glob in this shared module path.
The initial production preview returned HTTP 500 even though unit tests and type checks passed.
The map registry now uses explicit JSON imports.
A registry test requires every producer JSON to be registered.
The production browser checks verify actual server rendering before selection.
Independent per-producer source extracts preserve names, descriptions, grapes, exact slugs, and the full source SHA-256.

## Массандра, 2026-10-16

The map covers 44 exact catalog slugs from 2026-09-17.
The map adds 2 verified products without a catalog match.
1 products have no verified local image and use the explicit placeholder.
Read `docs/product-line-maps/massandra/sources.md` for collection evidence and limits.

## Инкерман, 2026-10-16

The map covers 15 exact catalog slugs from 2026-09-17.
The map adds 2 verified products without a catalog match.
0 products have no verified local image and use the explicit placeholder.
Read `docs/product-line-maps/inkerman/sources.md` for collection evidence and limits.

## Alma Valley, 2026-10-16

The map covers 39 exact catalog slugs from 2026-09-17.
The map adds 2 verified products without a catalog match.
0 products have no verified local image and use the explicit placeholder.
Read `docs/product-line-maps/alma-valley/sources.md` for collection evidence and limits.

## Золотая Балка, 2026-10-16

The map covers 41 exact catalog slugs from 2026-09-17.
The map adds 2 verified products without a catalog match.
8 products have no verified local image and use the explicit placeholder.
Read `docs/product-line-maps/zolotaya-balka/sources.md` for collection evidence and limits.

## Дербент Вино, 2026-10-16

The map covers 63 exact catalog slugs from 2026-09-17.
The map adds 4 verified products without a catalog match.
0 products have no verified local image and use the explicit placeholder.
Read `docs/product-line-maps/derbent-vino/sources.md` for collection evidence and limits.

## Additional producer maps, 2026-10-16

The owner requested ten producer maps and one commit per producer.
The scope includes 562 exact catalog slugs from the 2026-09-17 snapshot.
Nine source cards have no local image path. A null image is separate from a null wine_slug.
A null image shows an explicit placeholder. It does not disable the product or its portal link.
Official product pages supply additional products and collection evidence.
The maps do not claim to cover each complete live assortment.
Read `docs/plans/02_add-producer-maps.md` for scope and verification.
Each producer has source notes and an exact catalog crosswalk under `docs/product-line-maps/`.

## Mobile wine popup, 2026-10-16

The owner replaced the mobile bottom card with a popup widget.
A native modal dialog provides focus containment and top-layer display.
A fixed-position panel would need separate focus and parent-dialog handling.
The mobile popup reuses the same product details as the desktop side card.
The popup stays closed on map entry. The recognized product stays selected and centered.
This lets the user inspect the map before opening details.
This also avoids opening a child modal before the parent map dialog becomes visible.
A product tap or «О выбранном вине» opens the popup.
Popup closure preserves the map state and restores the explicit opener.
The earlier notes about an in-flow mobile panel describe the previous design.

A reopened dialog can retain its internal reading position.
Reset only the popup scroll body before focusing the product heading.
Do not reset the canvas or outer scroll containers.
Native dialog Tab navigation can move focus to browser chrome.
In the browser checks, that transition sets `document.hasFocus()` to false.
The checks permit that transition. They reject focus on an underlying page control.
The checks also verify that Tab returns to the popup and that background focus is blocked.

WebKit exposed an additional case with three native dialogs.
With shelf, map, and wine dialogs open, Tab reached the shelf Return control.
The mobile popup now cycles plain Tab and Shift+Tab through its own visible controls.
The handler leaves browser shortcuts and desktop behavior unchanged.
The regression check rejects focus on an underlying shelf or map control.
WebKit also allowed a programmatic `focus()` call to reach the underlying map.
A temporary `focusin` listener now returns outside focus to the popup heading.
The listener preserves the saved map and page scroll positions.
The component removes the listener before closure and during cleanup.
An attachment flag keeps cleanup safe during server rendering.

Final validation passed in Chromium and WebKit on 2026-10-16.
The strict shelf case also attempts focus on the outer shelf Return control.
Both attempts remain inside the popup after the correction.
Both complete suites report no browser errors or hydration warnings.
The 320/390 px popup screenshots were inspected in light and dark themes.
These results use browser emulation. No physical phone test was performed.

## Producer product-line map, 2026-10-15

The owner selected groups on a common canvas.
The owner selected a desktop side card and a mobile bottom card.
Read `docs/plans/01_product-line-map.md` for the requirements and decision.
Read `docs/product-line-map-sources.md` for source paths and identity rules.

The six prepared sheets cover 52 unique products and packages in 14 families.
The drink-sheet manifest says 14 packages. The renderer and image show 16 packages.
Two Fizz packages occur on two sheets. The map includes each package once.
The catalog snapshot provides 32 canonical slugs and 3 equivalent aliases.
The map preserves 20 products without a verified catalog match.
The source materials contain no numeric retail prices.
The intermediate relative price tiers are editorial assignments.
A separate neutral section avoids unsupported price comparisons across package formats.

The previous map contained six fixed nodes.
Its scale transform did not resize the horizontal scroll surface.
The new map sizes the scroll surface from the rendered canvas and current scale.
The scanner and shelf result both use `WineExperiences.vue`.
The guide retains that native dialog and uses an internal details panel.
This avoids another nested dialog inside the shelf result.
The parent centers the initial product after the native dialog becomes visible.
The preview reads the same static graph. It does not fetch remote wine metadata.

Claude Code accepted `claude-opus-5-5` with effort `max`.
The probe response identified the canonical model as `claude-opus-5-5`.
The review uses a sanitized prompt, disabled tools, and safe mode.
The owner explicitly requested external plan and implementation review.
The reviews receive no credentials.
Read `docs/reviews/2026-10-15-product-line-map-resolution.md` for review decisions and validation.

WebKit does not consistently focus a pointer-clicked button.
Record `event.currentTarget` when a dialog opens. Do not rely only on `document.activeElement`.
A mobile detail panel in normal document flow does not need a viewport-height cap.
Such a cap can hide fixed-size action controls in landscape.
The standalone header must use the same mobile breakpoint as global full-width buttons.
A long gift-box title can consume the full capped side panel in a compact desktop window.
The final CSS removes that cap at widths up to 1100 px and heights up to 800 px.
The normal wide and tall desktop layout retains the bounded panel.
Both complete browser suites passed after this correction on 2026-10-16.

## Yandex.Metrika, 2026-10-06

The owner supplied counter `113460637` and requested installation on `chtozavino.ru`.
This request authorizes this counter in addition to the existing product scope.
Use the supplied script in the shared Nuxt head configuration. Keep every supplied option.
Place the supplied no-JavaScript image in a body-start noscript tag.
The script sends the initial page view. Register client navigation tracking after app mounting.
Send a `hit` only after successful navigation to a different URL.
Include the previous page URL as `referer`. Do not send a second initial page view.
Reference: https://yandex.ru/support/metrica/en/code/counter-spa-setup

The script probe confirmed every initialization option, the asynchronous loader,
the duplicate-load guard, and the fallback URL.
Published isolated release `106320119585fb741dec0fcddd5b8c7ac140aa6c` from production source revision `de1c7ae`.
The previous release is `de1c7aead4cf3f039f9f2bb3080f5615bbb02247-video-20260929`.
The presentation files and recorded video remain byte-identical to the previous release.
All 169 tests, type checks, and the Linux production build passed.
Staged and public browser checks confirmed one initializer on all five pages,
one page view per successful client navigation, no duplicate initial page view,
the no-JavaScript fallback request, and navigation with a blocked external loader.
The real Metrika loader returned HTTP 200. Yandex returned HTTP 200 for the initial
page view and the client-navigation page view. Each page view was sent once.
Public health, upstream recognition availability, and shelf availability passed.
The temporary staging service and verification tunnel were stopped after verification.

## Hackathon direct URL, 2026-09-29

The owner requested crawler exclusion and sitemap removal for `/hackaton`.
The page is intended for organizers who receive the direct URL.
Remove inbound links from the presentation page, ideas page, and shared footer.
Keep the route available without adding a login requirement.
Add `Disallow: /hackaton`, HTML robots metadata, and the `X-Robots-Tag` header.
Apply the header to both the base path and its slash form.
Crawler instructions are voluntary. They do not restrict visitors with the URL.
Google cannot read noindex when robots.txt blocks a page. A previously discovered
URL can therefore remain in results. This change prioritizes the requested crawl block.
Reference: https://developers.google.com/search/docs/crawling-indexing/block-indexing

Published release `0c2f96481ccbbce4c00c593c6d6bc83570b3fbe5` on Princess.
The previous release `600fd2a` remains available for rollback.
All 169 tests and type checks passed locally and on Linux. The Linux build passed.
Staged and public checks confirmed HTTP 200 and robots metadata for the base,
trailing-slash, and query-string URLs. The header applies to each form.
The other four pages retain their indexing behavior and contain no incoming link.
Client navigation from `/hackaton` to `/ideas` removes the noindex metadata.
Direct access, age confirmation, and platform anchors passed at 320 and 1440 pixels.
Presentation artifact hashes, public file sizes, service health, and upstream availability passed.


## Hackathon landing publication, 2026-09-29

The owner requested deployment at `https://chtozavino.ru/hackaton`.
Release `600fd2ae25a3eab4d338b2cd3dccbd21e5435b2e` starts from production revision `8d07fad`.
It publishes the landing, its linked Android and ideas pages, and the APK download route.
The current presentation page and its files remain unchanged.
The APK package metadata and signature passed verification.
The current 0.1.4 APK has 576,503,447 bytes and SHA-256 `fc4cf0f44b8fefcff5286b04746efb7fa44b9742ec6df282aa0cc959f6777ea2`.
The release metadata now matches that artifact.
All 169 tests, type checks, and the Linux build passed on Princess.
Staged and public browser checks passed at 320, 390, 768, and 1440 pixels in both themes.
The checks cover the age gate, screenshots, anchors, linked pages, metadata, and the APK GET response.
No browser errors or hydration warnings occurred.
Public APK and presentation file SHA-256 values match the verified sources.
The scanner health, upstream mode, recognition availability, and shelf availability remain active.
The previous release remains available for rollback. The staging service was stopped.
See `<workspace>/deploy/princess/webui.md` for server paths and the deployment record.

## Presentation project card, 2026-09-29

The owner requested a wide card below the resource links.
The card uses the full content width and links to `/hackaton` in the same tab.
The card reuses the presentation file card styles.
The current production release does not include `/hackaton`.
Published release `8d07fad` with the card. Publication of the target page and its related pages remains a separate scope decision.
Local type checks and the production build passed. All 165 release tests, type checks, and the Linux build passed on Princess.
Browser checks confirmed the full card width, placement, destination, and no overflow at 320, 390, 768, and 1440 pixels.
The phone and desktop captures were visually inspected. Both presentation file hashes and service health remain valid.

## Presentation resource links, 2026-09-29

The owner requested GitHub and Google Drive links below the presentation video.
The cards reuse the presentation file grid and card styles.
Both links use the exact supplied URLs and open in new tabs with `noopener noreferrer`.
The content of the linked repository and folder is not copied or embedded.
Published release `dbdd3b6` from the isolated production branch.
All 165 release tests, type checks, and the Linux build passed.
Public browser checks confirmed both URLs, new tabs, placement below the video, matching card styles, and no horizontal overflow at 320, 390, 768, and 1440 pixels.
The phone and desktop captures were visually inspected.

## Presentation video, 2026-09-29

The owner requested a video below the presentation links at `/presentation/video.mp4`.
The owner will record the video later.
The page uses a native video player with metadata preload, controls, and inline phone playback.
A media error replaces the player with `Видео появится после записи`.
The future file belongs at `public/presentation/video.mp4` and stays outside Git.
The release must be rebuilt after the file is added because Nitro indexes public assets during the build.
No placeholder recording or external video service is used.
Type checks and the production build passed.
The browser check passed at four widths in both themes with the recording absent.
A temporary local MP4 verified that metadata load replaces the placeholder and that playback works without autoplay.
The temporary test clip is not part of the application or release.
Published release `c615490` on the existing `codex/presentation-release` branch.
All 165 release tests, type checks, and the Linux build passed before activation.
The public browser check passed at four widths in both themes. Both presentation file hashes still match.

## Presentation publication, 2026-09-29

The owner requested deployment after reviewing the presentation page.
Published revision `36fb8e2d824d10bb5b8dcfed6ebcf67e5d05e837` from branch `codex/presentation-release`.
The isolated release starts from production revision `459625f` and adds the presentation page.
Other pending Web UI pages remain in this working tree.
The presentation logo now returns to the deployed scanner at `/`.
All 165 tests in that release, type checks, and the Linux production build passed on Princess.
Staged and public file checks confirmed both content types and matching SHA-256 hashes.
The public browser check passed at four widths in both themes with no browser errors.
Health, upstream recognition, and shelf availability remained active.
The previous release remains available for rollback. The temporary staging service was stopped.
The deployment record is `<workspace>/deploy/princess/webui.md`.

## Presentation files, 2026-09-29

The user requested `/presentation` with two adjacent links to the supplied PowerPoint and its PDF version.
The route already contained a browser slideshow.
Decision: replace that view with the requested file links.
A local copy of the previous page and its browser check remains in `reports/presentation-files/`.
The PowerPoint source is `../../svoe-wino-hackaton/presentation/chtozavino-presentation.pptx`.
No PDF existed in the source presentation directory.
LibreOffice exported all 49 slides from an unchanged copy of the supplied PowerPoint.
The PDF preserves the source content, including its draft and template slides.
All 49 PDF pages were rendered and inspected in contact sheets.
The public files are in `public/presentations/` and stay outside Git.
The production build includes the public files. A fresh checkout requires the documented preparation commands.
The PowerPoint link downloads the file. The PDF link opens a new tab.
The page keeps the shared age gate and the existing white presentation palette.

Type checks, all 169 existing tests, and the production build passed.
The sandbox blocked the HTTP test server. The test suite passed with loopback access.
The production browser check passed at 320, 390, 768, and 1440 pixels in both themes.
Both file responses returned HTTP 200 with their correct content types and matching SHA-256 hashes.
The source PowerPoint and public copy also passed a direct byte comparison.
The PowerPoint download, age gate, canonical URL, and landing-page navigation passed.
No browser errors or hydration warnings occurred.
The 320-pixel and 1440-pixel page captures were visually inspected.

## Ideas beyond recognition, 2026-09-29

The user requested a landing page for ideas beyond recognition.
The user specified implemented features first, demos second, and mockups last.
Decision: add `/ideas` and keep the scanner at `/`.
The feature inventory from 2026-09-28 provides the initial concept list.
The current result component and specification determine the demo status.
The four result actions remain demos even when metadata rules are implemented.
The implemented section covers source-card navigation, Android local history, and Telegram feedback.
The mock section uses static interface sketches for six future scenarios.
The page labels each status and identifies application-specific limits.
The demo area reuses `WineExperiences` with three existing local wine cards.
The page does not need recognition or an external API to open a demo.
The page reuses existing image assets and the shared light and dark palettes.

Type checks, all 169 existing tests, and the production build passed.
The first test run could not open a loopback socket in the sandbox.
The same tests passed with local socket access.
Chromium checks passed at 320, 390, 768, 1024, and 1440 pixels in both themes.
The checks covered age gating, section order and counts, metadata, anchors,
all four dialogs, example selection, focus return, backdrop close, images,
horizontal overflow, network scope, and internal navigation.
A 320-pixel overflow from the rotated hero image was fixed before the final check.
No browser errors or hydration warnings occurred.
Local review captures are in the ignored `reports/ideas/` directory.
The desktop, narrow-phone, and dark-theme captures were visually inspected.


## Browser presentation, 2026-09-29

The user requested a presentation page based on `/hackaton`.
The user then specified a white background.
Decision: create `/presentation` as a browser presentation with five slides.
Decision: use a local white palette and preserve the saved site theme.
The cover uses an existing catalogue bottle image.
The application slides reuse the landing screenshots and the labeled Telegram scenario.
No new recognition result, performance metric, or external asset was created.
The final slide reuses the shared Android release metadata and configured APK URL.

The presentation keeps the shared age gate.
Keyboard navigation must ignore the gate and editable controls.
The slide index is bounded. URL fragments allow direct links and reloads.
On small screens, the active slide scrolls while the controls remain visible.
Horizontal touch gestures change slides. Vertical gestures preserve normal scrolling.
The fullscreen control appears only when the browser supports the API.

Type checks, all 169 existing tests, and the production build passed.
The presentation browser check passed at 1920x1080, 1440x900, 1366x768, 1024x768,
768x1024, 390x844, and 320x740.
All desktop slides fit without scrolling. Phone slides scroll inside the fixed controls.
The white palette remained active with a saved dark theme. The dark theme returned on the landing page.
The production checks covered age gating, keyboard navigation, touch events, stable
fragments, reloads, fullscreen entry and exit, image decoding, metadata, and links.
No browser errors or hydration warnings occurred in the production check.
Desktop and mobile slide screenshots were inspected in `reports/presentation/`.

## Hackathon landing page, 2026-09-29

The user requested `/hackaton` with WebApp, Android App, and Telegram Bot sections.
The WebApp section MUST show desktop and mobile screenshots together.
The Android section MUST highlight recognition without internet, including parking.

The existing manifest screenshots show the previous header identity.
Decision: capture the current local WebApp in light mode for the landing page.
Decision: keep these captures separate from the manifest screenshots.
The Android result uses the verified 0.1.4 screenshot already in `public/screenshots/android/`.
The Telegram bot address and supported photo album flow come from `../telegram-bot/README.md`.
The Telegram illustration describes the interaction. It is labeled as an example scenario.
The page states that WebApp recognition, Telegram, and source portal links need internet.
The Android section tells the visitor to install the APK before going offline.

Validation passed: type checks, 169 tests in 14 files, and the production build.
Chromium checks passed at 320, 390, 768, 1024, and 1440 pixels in both themes.
The checks covered the age gate, image decoding, horizontal overflow, platform anchors,
internal navigation, Telegram link targets, release attributes, and unique page metadata.
No browser errors or hydration warnings occurred.
The production page and three screenshot URLs returned HTTP 200.
The APK GET returned HTTP 200 with the Android package content type.
The production age gate and page hydration passed.

## Android landing page, 2026-09-29

The Android 0.1.4 APK is 576,503,269 bytes.
The APK is too large to store as a generated Web UI artifact in Git.
The Android build directory already excludes APK files from Git.
Decision: stream the local APK from a configured path.
Decision: allow the public download link to use a different configured URL.
Decision: use the exact versioned file name in the default route and attachment header.

The current APK uses the Android debug signing key.
Decision: label the file as a test version on the public page.
Decision: explain that Android can request permission to install an APK from the
browser.

The verified Android screenshot set contains light and dark screens and real results.
Decision: copy six WebP derivatives into the Web UI public directory.
Decision: keep the source screenshot file names for traceability.
Decision: do not create artificial phone screens or result values.

The strongest additional benefits are on-device processing, the built-in 2,093-wine
catalogue, automatic per-model GPU or CPU selection, persistent local history, system
theme support, Android 9 compatibility, and a direct source-portal link.
Decision: state that the portal link needs an internet connection.
Decision: do not describe cosine similarity as a probability or confidence.

The local production route returned the configured Android package with HTTP 200.
The response used `application/vnd.android.package-archive`.
The response used the exact size and the versioned attachment name.
An invalid file name returned HTTP 404.
The server-rendered page contained one `/android` canonical URL and the application
structured data.
All six public screenshot files matched the verified Pixel 8 source files byte for
byte.

## Current-theme icon button, 2026-09-29

The user requested a sun or crescent moon instead of the theme select.
The icon MUST identify the current palette, not the next action.
Decision: render both decorative icons and let the early `data-theme` attribute select the visible icon.
Decision: announce the current palette and next action in the button label.
Decision: use the system palette while there is no explicit preference and write storage only after a click.
Decision: retain the existing `svoe-vino.theme.v1` key and accept old `light`, `dark`, and `system` values.

## Product header identity, 2026-09-29

The user requested the product logo and name in place of the source-portal wordmark.
The shared artwork is available in `../assets/` and already has an exact public SVG copy.
The Android app and Telegram bot use the name `Что за вино?`.
Decision: reuse the existing product artwork without color filters.
Decision: use one `ProductBrand` component in the header and age gate.
Decision: align the footer, page title, social metadata, structured data, and installed app name.
Decision: retain the source-portal name in links and source attribution.

## Header theme selection, 2026-09-29

The user requested a light-mode selector in the Web UI header.
The previous palette depended only on `prefers-color-scheme`.
Decision: provide `Авто`, `Светлая`, and `Тёмная` in one native select.
Decision: keep `Авто` as the default and store the preference under `svoe-vino.theme.v1`.
Decision: apply the stored preference in the document head before first paint.
Decision: use `data-theme` for all dark styles, including dialogs and mobile buttons.
Decision: synchronize browser theme colors and preferences across open tabs.
Decision: retain the current-page selection if local storage is unavailable.

## Shared product branding, 2026-09-29

The user designated the repository-level `assets/` directory as the source of Web UI product assets.
The shared 640 by 640 artwork is a bottle with a question mark inside scanner marks.
Decision: keep the source-portal wordmark in the page header because it labels the linked portal identity.
Decision: use the shared product artwork for the favicon, PWA install icons, Apple touch icon, and social preview.
Decision: copy the shared SVG without modification for the favicon.
Decision: derive the fixed-size PNG icons from the shared PNG.
Decision: scale the maskable artwork to 400 by 400 on its original cream background so the visible mark stays inside the safe area.

## Result-aware product-line guide, 2026-09-29

The product-line map contains six curated Abrau-Durso wines.
The source catalog snapshot contains 57 records with producer `Абрау-Дюрсо`.
The six-node map cannot assign a verified tier to every source record.
The resolved wine contains a producer, a slug, an image, and a source URL.
Decision: normalize punctuation in the producer name before the brand comparison.
Decision: accept the `abrau-dyurso-` source slug prefix as a fallback brand signal.
Decision: mark a map node only after an exact slug match.
Decision: show an unmatched Abrau-Durso result in a separate card.
Decision: do not place that separate result in a collection tier.
Decision: keep Victor Dravigny as the fixed example for another producer.
Decision: label the fixed example as a demonstration and not as the user's wine.

## Product-line image selection, 2026-09-29

The Abrau-Durso map used one generated CSS bottle shape for all six wines.
The local `Своё Вино` catalog snapshot contains a `main` image for every map wine.
The patch directory contains a replacement for `abrau-dyurso-udelnoe-vedomstvo-imperatorskoe-beloe-bryut`.
The original catalog match for this wine is shared and does not show the correct package.
The cropped derivative for this slug was regenerated from the patch.
The other five selected slugs have no patch.
Decision: prefer `patched` by exact slug.
Decision: use `main` when the exact patch does not exist.
Decision: publish local transparent WebP derivatives for the map.
Decision: do not request source catalog images from the browser.

## Taste and regional dish inference, 2026-09-29

The source catalog analysis contains 2,103 unique wine records.
All source records have a description.
The resolved source cards can also contain broad pairing categories.
Examples include `Блюда из рыбы`, `Мясо и стейки`, `Сыры`, and `Запеченные овощи`.

The inference audit found two JavaScript regex errors.
The token `\w` matches ASCII word characters by default.
It does not match Russian suffixes.
The token `\b` does not create reliable Russian word boundaries.
The old patterns could miss inflected Russian terms.
One broad reverse pattern could also treat `вино насыщенного золотистого цвета` as body evidence.
The corrected patterns use explicit Cyrillic ranges and contextual exclusions.
The tests now cover color words and `лёгкая терпкость`.

The public Wine Reviews CSV contains 129,971 rows.
The source ZIP SHA-256 is `8e6b7df797df88929c34b41b93cf60643cefa4c93b9af7396ff2196efdf47551`.
The CSV SHA-256 is `52af2643c8ac29f010f0cc629dfbdda1c74aa0f332d11762af9ef3de4e567ac9`.
The source license is `CC BY-NC-SA 4.0`.
The build selected 66,562 reviews across 18 grape varieties.
The aggregate file stores descriptor frequencies, structural levels, observation counts, and sample counts.
It does not store review text, critic scores, prices, wineries, or bottle names.
The aggregate file SHA-256 is `09a19fa5be08515fedc4d89fad3d23c6db609308494270399bbd827e103486a9`.
The raw dataset is not stored in the repository.

An external factual audit confirmed the three pilot dish forms.
The Russian расстегай has an open center and commonly uses a fish filling.
The Dagestani чуду can be a thin dry-pan flatbread with cheese and greens.
The Adyghe халыж or халюж is a fried pastry with Adyghe cheese.
The generated images show these defining features.
Sources: `https://www.gastronom.ru/text/amp/1000410`, `https://xn----8sbehgcimb3cfabqj3b.xn--p1ai/recipes/selection/chudu-lepeshki-iz-tonkogo-testa-s-syrom-i-zelenyu/`, and `https://etnografia.kunstkamera.ru/files/etnografia_journal/2026_01/05_kurinskikh_1_31_2026.pdf`.
The Kaggle dataset page confirmed the `CC BY-NC-SA 4.0` label on 2026-09-29.

Decision: use source descriptions and source pairing categories as the primary evidence.
Decision: use a matching dataset aggregate only when source evidence does not fill a value.
Decision: use deterministic grape, color, category, and production-method rules to fill gaps.
Decision: do not copy a third-party tasting review into the application.
Decision: do not transfer a foreign critic score to a Russian wine.
Decision: compare each wine with one international style, not one specific bottle.
Decision: state one shared property and one possible difference for each comparison.
Decision: select three dishes from three different cuisines.
Decision: include Russian, Tatar, Kalmyk, Tuvan, Dagestani, Ossetian, Chechen, Adyghe, Balkar, and Georgian dishes in the local dish rules.
Decision: show when a source pairing category supports a dish.
Decision: call the result a gastronomic hypothesis because a recipe can change the pairing.
Decision: show the dataset source and license even when the wine has no reliable grape mapping.
Decision: apply sweet-wine rules before dry varietal comparisons.
Decision: add images only for the three dishes in the default demonstration result.
Decision: keep all other dish cards complete without an image.

## PWA behavior review, 2026-09-29

A headless Chromium probe checked `https://chtozavino.ru/` with Playwright 1.58.2.
The live `sw.js` is 2394 bytes. The local production build has the same size.
Chrome reported no installability errors and no manifest errors.
The service worker controlled the page after the first visit because of `clientsClaim`.
The precache held 22 entries. It held no API responses and no shelf example photos.
An offline reload after one online visit failed with `net::ERR_FAILED`.
Reason: the first navigation occurs before the service worker is active, so `svoe-vino-pages` stays empty.
An offline reload after two online visits returned the page from the service worker with HTTP 200.
The offline page rendered «Найти вино по фото» and loaded the Playfair Display font.
The README and the specification say that the app shell opens offline after one successful online visit. The probe does not confirm this statement.
The cached HTML contains the `portal-config` SSR payload. The payload is a copy of the `/api/config` response, for example `apiAvailable: true` and `shelfAvailable: true`.
An offline start therefore shows the last known service state.
`registerType: 'autoUpdate'` makes `vite-plugin-pwa` 1.3.0 call `window.location.reload()` when an updated service worker activates.
The Nuxt module plugin does not pass `onNeedReload`. A reload after a deploy can discard the selected photo and the shown result.
Live `/sw.js` and `/manifest.webmanifest` use `cache-control: public, max-age=0, must-revalidate`. The manifest uses `application/manifest+json`.
The maskable icon mark reaches 205.6 px from the center. The safe radius is 204.8 px. The difference is antialiasing only.
The `theme-color` meta has one value, `#7b3528`. The manifest `background_color` is the light `#fefdfa` also in the dark system theme.
The owner selected the fixes on 2026-09-29.
Decision: correct the offline statement in the documents. Do not add page-cache warming code.
Decision: use `registerType: 'prompt'` without an update banner. Reason: a scanner session is short, and a reload can discard a photo or a result.
Consequence: an app page that stays open keeps the old version until all app pages close.
Decision: keep the SSR config payload in the cached page. The specification now states this exception.
Decision: add a dark `theme-color` with the dark page color `#211e1c`.
The manifest cannot change `background_color` for the dark theme in current browsers, as far as this review found. The launch screen stays cream.
Decision: add JPEG manifest screenshots. The Chrome richer install dialog needs screenshots.
Unhead lists `theme-color` in `MetaTagsArrayable`. Two `theme-color` tags with `media` both render.
With `prompt`, the generated `sw.js` has no `clientsClaim` and calls `skipWaiting` only for a `SKIP_WAITING` message.
`scripts/check-pwa-browser.mjs` uses a loopback proxy that appends a comment to `sw.js`. This change starts a real service-worker update without a second build.
The check passed against the local `prompt` build. It failed against the live `autoUpdate` build with a destroyed execution context, which is a page reload.

## Complete result metadata fallback, 2026-09-29

The upstream recognizer can return more wine slugs than the 12 local Web UI records contain.
The source portal provides `GET https://api.vino-svoe.ru/v1/wines/<slug>`.
The endpoint returned the complete card for `massandra-muskat-rozovyy-pozdnego-sbora-rozovoe-sladkoe-10`.
The response includes the title, producer, region, grapes, style, description, and source image path.
Decision: keep the local records as the first lookup.
Decision: request an unknown valid slug from the official source JSON API.
Decision: use a fixed source host and reject redirects, mismatched slugs, untrusted image paths, oversized responses, and invalid records.
Decision: keep the existing explicit UI fallback when source metadata is unavailable.

## Owner-supplied shelf examples, 2026-09-29

The project owner supplied four supermarket shelf photographs.
The first and fourth files had the same SHA-256 value.
Decision: store the three unique photographs.
Decision: replace the Wikimedia example and its attribution.
Decision: convert each photograph to a 2560 by 1928 WebP file.
Decision: remove embedded metadata during conversion.
Decision: let the visitor select one example before the portal sends it through the normal group-match route.

## Production resilience verification, 2026-09-29

A bounded public load test sent one, four, eight, and twelve concurrent recognition requests.
All requests passed through concurrency eight.
At concurrency twelve, eight requests passed and four requests reached the matcher capacity guard.
The matcher returned HTTP 503 with `matcher is busy`.
The Web UI changed this response to HTTP 502.
The same mapping changed the matcher HTTP 413 JPEG pixel-limit response to HTTP 502.
Decision: preserve the matcher HTTP status when the status is safe and actionable.
Decision: do not expose the matcher response body.
Decision: map an unexpected matcher status or an invalid matcher response to HTTP 502.

The live shelf example returned HTTP 502 from the Web UI.
The deployed matcher revision was `9ba496d230d23398f76275cbbd187d5a820c4bfe`.
Its OpenAPI document did not contain `/v1/group/match`.
Commit `b752591` added this endpoint after the deployed revision.
Decision: deploy a committed matcher revision that includes `b752591` before shelf mode stays enabled.

Web UI revision `11ebfbf` preserved HTTP 413 for the JPEG dimension bomb.
A second 12-request burst returned nine HTTP 200 responses and three HTTP 503 responses.
The matcher health route stayed at HTTP 200.
The first shelf request after the route deployment found 93 bottles.
It failed because the SigLIP2 service accepts at most 64 inputs in one request.
Matcher revision `013ab56` split larger logical batches into requests of at most 64 inputs.
The final public shelf request returned HTTP 200 in 2598.775 ms.
It returned 93 bottles and 93 ready matches.
The production browser opened bottle 1 as `Траминер` and closed the card without a second recognition request.

## Search discovery and age gate, 2026-09-28

The age gate previously replaced the complete server-rendered page with a loading element.
A new visitor then received only the age gate after hydration.
Decision: always render the scanner page.
Decision: render the age gate as a fixed overlay before the local storage check.
The client removes the overlay only after it finds a stored confirmation.
Decision: make the scanner controls inert while the gate is open.
This design preserves the mandatory interaction block and keeps the page content available to crawlers.
The apex and `www` hosts previously returned identical HTML without a canonical signal.
Decision: use `https://chtozavino.ru/` as the canonical URL.
Decision: redirect the complete `www` host to the apex with HTTP 308 at Caddy.
Decision: publish one sitemap URL because the portal has one indexable page.
Decision: describe the portal as `WebSite` and `WebApplication`.
The portal does not own indexable wine pages, so it does not publish wine `Product` metadata.
The reference file names are stable but are not content hashes.
Decision: cache these files for seven days and allow one day of stale revalidation.

## Matcher readiness, 2026-09-28

The matcher provides the public `GET /healthz` readiness route.
The readiness response contains `status: "ok"` and the selected pipeline.
The configured prediction URL can use a private loopback or network address.
Decision: the Nuxt server checks matcher readiness.
Decision: derive the health path from the final `/v1/eval/predict` path.
Decision: do not change the Web UI `GET /api/health` liveness contract.
Decision: report matcher readiness as `apiAvailable` in `GET /api/config`.
The prediction request remains the final availability check because readiness can change after the configuration request.

## Progressive Web App, 2026-09-28

The user requested PWA support and the Telegram bot icon.
The Web UI reuses `telegram-bot/assets/botpic.svg` as the icon source.
The user selected the PWA module implementation after reviewing the first local implementation.
Decision: use `@vite-pwa/nuxt` 1.1.1 and its generated Workbox service worker.
The installed module resolves `vite-plugin-pwa` 1.3.0.
The package audit reported no vulnerabilities after installation.
Decision: use automatic service-worker updates and generated manifest registration.
Decision: precache Nuxt client bundles, install icons, and app-shell reference assets.
The production Workbox build precaches 22 entries with a total size of 638 KiB.
Decision: use `NetworkFirst` for page navigation and exclude the `/api/` and `/v1/` route prefixes.
Workbox runtime routes use GET by default. Photo upload requests do not match a cache route.
Development mode does not enable the generated service worker.
The maskable icon uses a solid cream background and keeps the mark in the central safe area.
Recognition, metadata, and source portal navigation remain online-only operations.
The production browser loaded the manifest link and the new SVG favicon without warnings or errors.
The production contract check loaded the service worker, manifest, and all declared PNG icons.

## Local result demonstrations, 2026-09-28

The selected implementation is a fully local demonstration.
The product action must explain a future coordinate request without invoking browser geolocation.
Decision: use a fictional SuperLenta store and fictional domestic products.
Decision: mark paid food priority visibly and do not include an alcohol purchase action.
The public `vino-svoe.ru` Abrau-Durso catalog provides stable wine detail paths for the product-line demonstration.
Decision: keep map positions and descriptions local and link each node to its public source page.
Decision: use a separate normal link for keyboard and touch access in addition to node double click.
The desktop and 390 px mobile checks confirmed the age gate, result actions, dialogs, product cards, story rotation, and map controls.

## Matcher group endpoint integration, 2026-09-28

The matcher now provides `POST /v1/group/match` on the same service that provides `POST /v1/eval/predict`.
The group response includes the shelf preview, detected bottle coordinates, segmentation masks, and ready best matches.
Decision: the browser calls same-origin `/v1/group/match` through the Nuxt server.
Decision: derive the upstream group URL from the existing `NUXT_PREDICTION_ENDPOINT` origin and path prefix.
Decision: do not add `NUXT_GROUP_MATCH_ENDPOINT`.
This keeps one matcher configuration and prevents the browser from receiving a private service address.
The matcher performs all bottle matching during the group request.
Bottle selection is now local UI state and does not start another prediction request.
The matcher can archive the original group photo.
The Web UI does not claim that the photo is never stored.

## Princess deployment and shelf suspension, 2026-09-28

Princess has 1 vCPU, 1.9 GiB RAM, and a 25 GB disk.
The live check showed approximately 1.7 GiB available RAM and 23 GB available disk space.
Caddy used approximately 46 MiB RSS during the check.
The Nuxt production output used approximately 22 MB on the build host.
Decision: Princess can run Caddy and the Nuxt portal for demo and moderate traffic.
Decision: keep matcher and SAM3 computation on GX10.
The existing Princess loopback tunnel provides the compatible `/v1/eval/predict` route on port 28000.
Its current pipeline is `official-eval-mock`.
The existing public Caddy API also owns `/v1/eval/predict` and requires a bearer token.
Decision: keep that route unchanged and send browser photo requests to the equivalent portal `/api/predict` route.
The owner selected a selectable temporary-unavailable view for «Вся полка».
The Princess deployment does not set `SAM3_ENDPOINT`.
The server rejects the disabled shelf route before it reads an upload.

## Shelf mode, 2026-09-15

The user requested segmented shelf photos and a popup for each selected bottle.
The existing GX10 SAM3 gateway accepts multipart `image` and `text=wine bottle`.
Use canonical `SAM3_ENDPOINT`. Keep all service requests behind our portal API.
The first live request used the public Wikimedia shelf example documented in `docs/assets.md`.
The source JPEG hash matched the public download. No private user photo was used.
The request returned 96 masks at 1280 × 853 in 68.162 seconds after model loading.
The service returned binary full-frame masks. Eleven detector boxes extended slightly outside the photo.
Some masks had disconnected fragments outside the detector box.
Decision: clamp detector boxes and exclude mask fragments outside each box.
Return cropped overlays to avoid one full-frame browser texture per detected bottle.
Recognize only a selected crop. A dense shelf must not trigger 96 prediction requests.
The native popup reuses the existing wine result and food recommendation flow.

Independent code review identified malformed crop parsing and missing server-side prediction cancellation.
Added strict data URL validation and propagated client disconnects to the prediction provider.
The focused tests cover these corrections and retain the existing evaluator contract.
Physical camera, touch, and full visual checks remain separate device verification work.

The first production request encountered a transport reset while the gateway loaded SAM3.
The gateway recorded an empty 502 after 58.311 seconds. No SAM3 validation error was recorded.
The same normalized public photo passed after loading. It returned 94 masks through the portal.
Added one retry for known transient socket and transport timeout codes within the original time budget.
Permanent address errors, malformed output, and cancellation do not trigger this retry.
Tests cover these branches. A new cold-start failure was not forced on the shared service.
The final browser flow returned 94 selectable bottles, a source-linked demo wine, and three live foods at public test store 5020.
All new browser tools rejected invalid input. Reset cleared the shelf and popup.
The existing evaluator accepted all three requests after the shelf changes.

## Demo service boundary, 2026-09-15

The user clarified that the Web UI must query our portal and our service must provide the response.
The current code already follows this boundary.
`useFoodRecommendations` calls relative `/api/food/stores` and `/api/food/pairings` routes.
The server handlers call the Globus adapter and return normalized data.
The browser has no direct retailer data API call.
Product images and user-selected retailer links remain separate media and navigation requests.
Decision: preserve the implementation and make the boundary explicit in the specification.
No separate service endpoint was supplied or connected in this clarification.

## 2026-09-15

- Read the official evaluator script and its README.
- Confirmed `POST`, multipart field `image`, and response field `slug`.
- Confirmed the evaluator timeout and HTTP status rules.
- Inspected the supplied public catalog in the browser.
- Recorded source colors, typeface, layout, navigation, and bottle assets.
- Selected Nuxt for one local UI and API server.
- Selected a fixed mock prediction to avoid implying image recognition.
- The task document recommends Strapi for the catalog. The user permits a mock implementation.
- Eight demo slugs occur in the official CSV. Four newer slugs use public portal metadata.
- The portal reports `108%` alcohol for `muskat-ottonel-gusev`. The demo record omits this invalid value.
- Nuxt 4.5.2 requires Vue Router 5.2.0. The project uses the matching version.
- Relative shared imports failed in the Nuxt production server output. The documented `#shared` alias resolves the production imports.
- The official evaluator accepted all three production mock responses.
- WebMCP checks confirmed search state changes, invalid input rejection, and scanner dialog opening.
- Full visual regression, physical camera behavior, and a real recognition service remain untested.
- Aligned the Node engine range with the installed Nuxt 4.5.2 package metadata.
- The first GitLab CI job failed during the Docker Hub image download. One retry was started.

## Photo search scope correction, 2026-09-15

The user requires a dedicated photo search page with the source visual identity.
The user does not want a duplicate catalog UX.
Decision: replace the catalog page with one responsive scanner workspace.
A modal-first alternative adds an unnecessary opening action. A catalog-first alternative conflicts with the corrected request.
Keep the prediction API and metadata fixture. Remove the catalog UI and local detail navigation.
A valid prediction must survive metadata fetch errors. The old scanner assigned the slug too late.

The scanner state checks confirm that metadata 404, 500, invalid JSON, wrong slug, network failure, and timeout retain the valid prediction link.
The production browser example completed through the same automatic upload path as the UI.
The updated production evaluator check passed for all three official photos.

## Food source selection, 2026-09-15

The user selected a retailer with an accessible API instead of demo products.
The sibling `retail-query/docs/store-search-capabilities.md` already documents Globus, METRO, and Lenta.
Globus has a confirmed coordinate directory and guest product search.
METRO directory access remains unverified. Lenta requires a specific network access profile in that report.
Decision: use Globus directly. No proxy, login, or API key is needed for the verified guest flow.
A new live probe returned HTTP 200 for the directory, store 5020 context, three searches, and one product detail.
The directory contained 22 records at the test time.
The queries were `филе индейки`, `моцарелла`, and `хумус`.
`docs/validation/globus-access.json` records the sanitized observation.
The source fields show that `quantity` is basket state and `quantity_max` is available quantity.
Some prices require the loyalty card. The UI preserves the returned promotion conditions.
Product links come from `data.product.share_text`. Do not construct a speculative path.
No user location was obtained. Verification uses public store coordinates or an explicit public store ID.

The integration uses an application API, not a public developer contract.
The directory limits geographic coverage. Straight-line distance does not represent travel time or delivery eligibility.
The pairing rules use source labels first and editorial defaults second.
The product search samples up to eight candidates per idea. It does not prove full catalog coverage.
An independent code review found an incorrect fixed wine-color reason and overly broad preparation matching.
Removed the fixed color assertion. Excluded salted fish and pickled mushrooms from baking ideas.
Try a second candidate when the first detail record becomes unavailable or fails validation.

### Static image metadata, 2026-10-16

Nitro embeds static file size and ETag metadata in the server build.
An image copied directly into `.output/public` retained its old Content-Length.
The browser request reported a parse error because the new file body was longer.
Rebuild the application and restart the server after a public asset replacement.
The rebuilt server returned the new image hash in both browser engines.

### Crocodile visual verification findings

Set an explicit automatic height when a responsive product photo has HTML width and height attributes.
In scoped Vue CSS, keep the full theme descendant selector inside `:global(...)`.
The split form affected the HTML root in this build.
The final browser check verifies photo proportions, theme background luminance, and main text and button contrast.
See `docs/validation/crocodile-landing.md` for the final evidence.

### Original-photo upload budget, 2026-10-20

The owner requested a timeout fix without reducing recognition quality, followed by a USB retest on the realme.
The earlier reproduction sent a 9,023,122-byte JPEG and aborted after ten seconds on an explicit 4 Mbit/s upload limit.
Its 1600 px copy changed the selected wine. The fix preserves the original file and its pixels.
Interactive photo search now has a 120-second total request budget and a 30-second upstream budget after upload.
The evaluator proxy keeps its eight-second upstream budget. Both routes share validation and byte-preserving forwarding.
Metadata still has a separate four-second browser budget. Cancellation and replacement retain their existing abort behavior.
All 620 unit tests pass, with 26 existing optional catalog skips. Type check and production build pass.
A compiled HTTP check accepts a nine-second matcher reply on `/api/predict` and retains evaluator timeout behavior.
Both compiled routes forward exactly the source image SHA-256.
The local production build used the unchanged live matcher through SSH forwarding.
Physical realme Chrome, through USB reverse forwarding, uploaded two full-resolution JPEGs of 9.0 MB and 8.7 MB.
At 4 Mbit/s they completed in 20.49 and 19.57 seconds with the expected original wine identities.
At 1 Mbit/s the 9.0 MB file completed in 73.98 seconds. Every outgoing file hash matched its source.
Cancellation after twelve seconds and an immediate unthrottled retry passed.
These are diagnostic controls and transport checks, not new benchmark scores or universal accuracy claims.
The matcher, models and prompts were not changed. The checked code remains on a local fix branch until publication is authorized.
The workspace report is `reports/original-photo-timeout-fix-2026-10-20/README.md`.
