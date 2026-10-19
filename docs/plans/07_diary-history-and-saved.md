# «Винный дневник»: history and saved wines

Date: 2026-10-20.
Branch: `feature/diary-history-saved`.
Base: `b7b2c5e8` (`main`).
Issues: #71 (light history), #64 (wish list). This plan replaces the wish list of #64 with the
«Сохранённые» list and widens #71 to the Telegram and MAX chats.
Status: implemented on the branch on 2026-10-20. Deploy: see "Deploy".

## Owner request (2026-10-20)

> please, implement history in account. It contains all wine_slugs that were matched by user in
> all connected devices / chats / webui. user can clean list completely, remove specific item,
> see data, see bottle, title, manufacturer color, sugarness. There should be filter while
> looking at history.
>
> also add another list - "Saved". Item from history can be added to saved. If then wine_slug
> from history removed, but exists in "Saved", then it kept there.
>
> "Saved" list has "Not tasted", "Not tasted, but want to taste", "Tasted and Liked",
> "Tasted and disliked"
>
> Website has a few places where user can add wine_slug to "saved": user account while watching
> "history" list, matched wines, dinner lens, product line map, ... This is possible only if user
> authorised.
>
> There should be icon in top right corner "Pin" - adds to "Saved". Using "floppy drive" icon is
> outdated. "Favorites" star also not goog, because we put to saved list.
>
> Review specification, close gaps if I miss something, implement and deploy.

## Decisions

Decisions that the owner request gives:

- R1. The history holds every wine that a logged-in person matched: the photo search of the site,
  and the Telegram and MAX chats when the messenger is linked to the diary.
- R2. A person can clear the history, remove one wine, and see the dates, the bottle image, the
  name, the producer, the color, and the sugar of each wine. The history has filters.
- R3. A second list, «Сохранённые», is independent of the history. Removal from the history does
  not remove a saved wine.
- R4. A saved wine has one of four statuses.
- R5. A pin icon in the top right corner of a wine card saves the wine. No floppy disk, no star.
- R6. Only a logged-in person can save.

Decisions of this plan (the owner can change them):

- D1. Russian names. List: «Сохранённые». Statuses: «Не пробовано» (`not_tasted`),
  «Отведать желаю» (`want`, the owner name of the #64 wish list), «Понравилось» (`liked`),
  «Не понравилось» (`disliked`). The text of the statuses has no grammatical gender.
- D2. A new saved wine gets the status «Не пробовано». The pin then opens a small panel where the
  person selects another status or removes the wine. A click on the pin of a saved wine opens the
  same panel. It does not remove the wine, so a slip of the finger loses nothing.
- D3. A logged-out person sees the pin. A click opens the panel with «Сохранять вина можно в
  «Винном дневнике»» and «Войти». Nothing is saved before login. The site does not keep a
  pending save. If the account service is off or unavailable, the pin is not shown.
- D4. History sources: `photo` (single-bottle search on the site), `shelf` (a bottle that the
  person opens in a shelf result), `telegram`, `max`. A shelf photo can hold 20 bottles, so only
  the bottles that the person opens go to the history. The product line map, Dinner Lens, and
  the wine of a demo result do not go to the history: to see a wine in a list is not to find it.
- D5. A mock prediction (`X-Prediction-Mode: mock`) is never recorded and has no pin.
- D6. One date per wine per calendar day, Europe/Moscow (#71 open decision 3, as proposed). A
  repeated match on the same day changes nothing. The first source of the day is kept.
- D7. The switch «Записывать найденные вина» is on by default (#71 open decision 1). It applies
  to the site and to the chats.
- D8. A wrong match is easy to undo where it happens. The site result card shows «Записано в
  историю дневника» with «Убрать». In Telegram and MAX, «❌ Не совпало» removes the date of
  that day, and a selected alternative wine is recorded.
- D9. Limits: 2,000 wines in the history and 366 dates for each wine; at the limit the oldest
  record goes (the history must not block a search). 500 saved wines; then HTTP 409.
- D10. The service keeps a wine snapshot (name, producer, color, sugar, region, grapes) with
  each wine, so the lists render when vino-svoe.ru is down. The Nuxt server builds it from the
  slug for the site. A bot sends the card data that it has. A newer snapshot replaces an older one.
- D11. No manual «Я пробовал это вино» history entry (#71 open decision 2). The saved statuses
  «Понравилось» and «Не понравилось» record tasting.
- D12. Line map products without a vino-svoe.ru card (`wine_slug: null`) have no pin (#64 open
  decision 2). No personal notes in v1 (#64 open decision 3).
- D13. The bots record in the background with one attempt and a 2-second timeout, as the site.
  The outbox of plan 05 stays for photo searches (#48), which carry images.
- D14. Ratings of #48 come later. A saved status is not a rating.

## Data model

Schema file `account/src/chto_za_vino_account/schema/005_diary_lists.sql`:

```sql
ALTER TABLE users ADD COLUMN save_history INTEGER NOT NULL DEFAULT 1;

CREATE TABLE history_wines (
    user_id TEXT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    wine_slug TEXT NOT NULL,
    wine_snapshot TEXT,
    first_met_at INTEGER NOT NULL,
    last_met_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, wine_slug)
);
CREATE INDEX history_wines_recent ON history_wines (user_id, last_met_at);

CREATE TABLE history_days (
    user_id TEXT NOT NULL,
    wine_slug TEXT NOT NULL,
    met_on TEXT NOT NULL,        -- YYYY-MM-DD, Europe/Moscow
    source TEXT NOT NULL,        -- photo, shelf, telegram, max
    first_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, wine_slug, met_on),
    FOREIGN KEY (user_id, wine_slug) REFERENCES history_wines (user_id, wine_slug) ON DELETE CASCADE
);

CREATE TABLE saved_wines (
    user_id TEXT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    wine_slug TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('not_tasted', 'want', 'liked', 'disliked')),
    source TEXT NOT NULL,        -- photo, shelf, lineup, dinner_lens, history
    wine_snapshot TEXT,
    added_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, wine_slug)
);
CREATE INDEX saved_wines_recent ON saved_wines (user_id, updated_at);
```

The service checks the source values. The schema does not, so a new source needs no migration.

Wine slug: `^[a-z0-9](?:[a-z0-9_-]{0,198}[a-z0-9])?$`.

Wine snapshot: a JSON object, at most 2,048 bytes in UTF-8. All fields are optional:
`name`, `producer`, `color`, `sugar`, `region` (strings of 1–200 characters) and `grapes` (at
most 12 strings of 1–80 characters). Other keys are refused with HTTP 422.

## Account service API

The Nuxt server adds `X-Session-Token` (consumer `web`). Times are ISO 8601 UTC.

| Route | Body or answer |
|---|---|
| `GET /v1/me` | `user` gains `save_history` (boolean) |
| `PATCH /v1/me` | `{ "save_history": bool }` → the `GET /v1/me` answer |
| `GET /v1/me/history` | `{ "items": [HistoryItem], "save_history": bool }`, all wines, newest `last_met_at` first |
| `GET /v1/me/history/{slug}` | `HistoryItem` with `days: [{ "met_on", "source", "first_at" }]`, newest first; 404 `not_found` |
| `POST /v1/me/history` | `{ "slug", "source": "photo" \| "shelf", "wine_snapshot"? }` → `{ "status": "recorded" \| "already" \| "off", "met_on"? }` |
| `DELETE /v1/me/history/{slug}/days/{met_on}` | 204; the last date removes the wine; 404 `not_found` |
| `DELETE /v1/me/history/{slug}` | 204; 404 `not_found` |
| `DELETE /v1/me/history` | 204 |
| `GET /v1/me/saved` | `{ "items": [SavedItem] }`, newest `updated_at` first |
| `GET /v1/me/saved/slugs` | `{ "items": [{ "slug", "status" }] }` |
| `PUT /v1/me/saved/{slug}` | `{ "status", "source", "wine_snapshot"? }` → `SavedItem`; 201 for a new wine, 200 for a change; 409 `saved_full` |
| `DELETE /v1/me/saved/{slug}` | 204; 404 `not_found` |

`HistoryItem`: `slug`, `wine` (the snapshot or `null`), `first_met_at`, `last_met_at`,
`days_count`, `sources` (the distinct day sources), `saved_status` (`null` when not saved).

`SavedItem`: `slug`, `wine`, `status`, `source`, `added_at`, `updated_at`, `in_history` (bool).

A `PUT` of a saved wine keeps `source` and `added_at`, and changes `status`, `updated_at`, and the
snapshot when the body has one.

Bots (consumers `telegram-bot` and `max-bot`; the consumer gives the provider):

| Route | Body | Answer |
|---|---|---|
| `POST /v1/bot/history` | `{ "user_id": int, "slug", "wine_snapshot"?, "replaces"? }` | `{ "status": "recorded" \| "already" \| "off" \| "not_linked", "met_on"? }` |
| `POST /v1/bot/history/undo` | `{ "user_id": int, "slug" }` | `{ "status": "removed" \| "absent" \| "not_linked" }` |

- `user_id` is the Telegram user ID or the MAX user ID (`identities.subject`).
- `undo` removes the date of today (Europe/Moscow). The last date removes the wine.
- `replaces` is the slug that the person rejected before they selected this alternative. The
  service removes today's date of `replaces` in the same transaction.
- A user without a linked identity gets `not_linked` with HTTP 200, so the bot needs no second
  request to know the link state.

Application tokens (#65): `GET /v1/app/wines` returns the history. Each item: `slug`, `name`,
`producer`, `color`, `sugar`, `first_met_at`, `last_met_at`, `days`, `sources`, `saved_status`.
The cursor is opaque. It holds `last_met_at` and `slug` of the last item.

Account deletion removes both lists (`ON DELETE CASCADE`). The operator command `merge` moves
both lists: the union of the history dates, the earliest `first_met_at`, the latest
`last_met_at`; for a saved wine in both accounts, the row with the later `updated_at`.

## Nuxt server

Routes (the rules of `webui/docs/account.md`: `Origin` on writes, `no-store`, 2 s timeout, no
retry, errors through `accountErrorMessage`):

| Route | Service route |
|---|---|
| `GET /api/account/history` | `GET /v1/me/history` |
| `GET /api/account/history/[slug]` | `GET /v1/me/history/{slug}` |
| `POST /api/account/history` | `POST /v1/me/history`; the server adds the snapshot; 409 `mock_mode` in mock mode |
| `DELETE /api/account/history` | `DELETE /v1/me/history` |
| `DELETE /api/account/history/[slug]` | `DELETE /v1/me/history/{slug}` |
| `DELETE /api/account/history/[slug]/days/[day]` | `DELETE /v1/me/history/{slug}/days/{met_on}` |
| `PATCH /api/account/me` | `PATCH /v1/me` |
| `GET /api/account/saved` | `GET /v1/me/saved` |
| `GET /api/account/saved/slugs` | `GET /v1/me/saved/slugs` |
| `PUT /api/account/saved/[slug]` | `PUT /v1/me/saved/{slug}`; the server adds the snapshot |
| `DELETE /api/account/saved/[slug]` | `DELETE /v1/me/saved/{slug}` |

- The server builds the snapshot from the slug: `server/data/wines.json`, then the vino-svoe.ru
  API (`fetchSourceWine`). A 404 refuses the write with 404 `unknown_wine`. A timeout or a 5xx
  stores the wine without a snapshot.
- The list routes accept answers of up to 2 MiB from the service.
- Without a session cookie the server answers 401 `session_required` and calls nothing.
- The MAX mini-app host does not get the new routes in v1. Its Caddy block on Claudette and
  `MAX_HOST_ROUTES` list the allowed routes, and both lists must stay equal. The mini app keeps
  the settings view. The lists are on the site. A later change can add them to both lists.

## Web UI

### Pin

`PinButton.vue`: an icon button in the top right corner of a wine card, with a pushpin icon.
Outline: not saved. Filled: saved. `aria-label` «Сохранить вино» or «Сохранено: <status>».

- The first pin on a page loads `GET /api/account/saved/slugs` once. The state is shared by all
  pins of the page. The header still makes no account call.
- 401: the logged-out panel (D3). 404 `account_disabled` or 503: no pin.
- The panel is a non-modal dialog under the pin: the four statuses as radio buttons, «Убрать из
  сохранённых», and «Все сохранённые» (link to `/account?tab=saved`). Escape and a click outside
  close it. Focus goes back to the pin.
- A failed write shows «Не удалось сохранить» in the panel. The page stays as it is.

Places:

| Place | Component | Source |
|---|---|---|
| Photo match result | `PhotoScanner.vue`, panel heading | `photo` |
| Shelf bottle dialog | `ShelfScanner.vue`, dialog top, before the close button | `shelf` |
| Product line map details | `ProductLineMap.vue`, details heading; `wine_slug` or the recognized wine | `lineup` |
| Dinner Lens wine card | `DinnerScanner.vue`, card top | `dinner_lens` |
| History row | `/account`, «История» | `history` |
| Saved row | `/account`, «Сохранённые» | (status change only) |

### History records

- `useWineScanner`: after `phase = 'matched'` and `mock === false`, the browser sends
  `POST /api/account/history` `{ slug, source: "photo" }` once, in the background. 401 and every
  error are silent.
- On `recorded` or `already`, the result card shows «Записано в историю дневника» and «Убрать».
  «Убрать» deletes that date (`met_on` from the answer).
- `useShelfScanner.selectBottle`: the same record with `source: "shelf"`, once per bottle and
  result. No result-card line.

### `/account`

Tabs «История», «Сохранённые», «Настройки» (`role="tablist"`). The tab is in the query
(`?tab=history|saved|settings`). No slug goes into a page URL.

«История»:

- Filters: text (name or producer), color, sugar, source («Сайт», «Полка», «Telegram», «MAX»).
  The page loads the whole list once and filters in the browser.
- Row: bottle image (`/img/wines/400/<slug>.webp`, silhouette on error), name, producer,
  «Красное · Сухое», «Нашли 3 раза», «Впервые 3 июня 2026», «Последний раз 19 октября», the
  sources, the pin, «Даты» (the dates with sources), «На «Свое Вино»» (vino-svoe.ru card),
  «Удалить из истории».
- «Очистить историю» with a confirmation.
- Empty state: one line and a link to the scanner.

«Сохранённые»:

- Status filter with counts («Все», four statuses), and the same text, color, and sugar filters.
- Row: bottle, name, producer, color and sugar, the status selector, «Добавлено 19 октября», the
  source («Из истории», «Из поиска по фото», «С полки», «С карты линейки», «Из «Вино к блюду»»),
  «На «Свое Вино»», «Убрать».
- Empty state: one line about the pin.

«Настройки»: today's content, the switch «Записывать найденные вина», and «Очистить историю».

Privacy: vino-svoe.ru links of the lists have the class `ym-disable-tracklink`. List content
never goes to Metrika.

## Bots

Telegram (`telegram-bot`) and MAX (`max-bot`), when `BOT_ACCOUNT_ENDPOINT` and the consumer token
are set:

- After a result card is sent to a person, the bot sends `POST /v1/bot/history` with the shown
  wine. Telegram jobs carry the sender `user_id` (today `PhotoJob` has only `chat_id`). API jobs
  (`user_id 0`) record nothing.
- «❌ Не совпало» sends `POST /v1/bot/history/undo` for the shown wine.
- A selected alternative sends `POST /v1/bot/history` with that wine and `replaces` = the
  rejected wine. «Ничего из этого» sends nothing.
- The calls run in the background (`BackgroundTasks`), with one attempt. A failure is logged
  without the user ID and changes nothing in the chat.
- MAX: new settings `BOT_ACCOUNT_ENDPOINT` and `ACCOUNT_MAX_TOKEN`; the same client code.
  Plan 05 notes that no source confirms that the MAX mini-app user ID equals the Bot API user
  ID. If they differ, a MAX record answers `not_linked`. The deploy check confirms it.

## Privacy

`/privacy` names both lists: what is stored (wine, date, source, status; no photo), the chats
(only after a link), the switch, the deletion of one wine and of the whole list, and account
deletion.

## Tests

- Account service: record, same day, new day, the switch, per-user isolation, limits, the three
  deletions, saved add/change/remove, the 500 limit, saved stays after history removal, bot
  routes (linked, not linked, undo, replaces), consumer refusals, merge, account deletion,
  `GET /v1/app/wines`.
- Nuxt server: routes, Origin, mock refusal, snapshot builder, MAX host routes.
- Bots: record after a result, undo, alternative, no record without a link or for API jobs.
- Browser: logged-in match → history row; «Убрать»; pin from the result, the line map, Dinner
  Lens, and the history; status change; logged-out panel; filters; clear; account service down.

## Deploy

1. Account service on gx10 prod: back up the database, migrate to schema 5.
2. Telegram bot on gx10 prod.
3. Portal on Claudette.
4. MAX bot: needs `ACCOUNT_MAX_TOKEN` in the account service and the bot environment (owner),
   and the move of `max-bot` prod from the GitLab revision `3e7c20d2` to GitHub `main`.

## Implementation notes (2026-10-20)

- Account service: `account/src/chto_za_vino_account/diary.py`, schema `005_diary_lists.sql`.
  `first_met_at` and `last_met_at` follow the remaining dates when a date is removed. The
  application cursor packs the slug, so it fits the 200-character limit of Nuxt and MCP. If the
  container has no time zone data, the Moscow day uses a fixed UTC+3 (no DST since 2014).
- Bots: one client for both bots in `im-core/src/chto_za_vino_core/diary.py` (`DiaryHistory`).
  The snapshot color is the matcher `category` («Красное», «Белое»): the matcher `color` is the
  tint («Рубиновый»). Telegram jobs carry the sender `user_id`.
- Web UI: «Очистить историю» is on the «История» tab, next to the list, not in «Настройки». The
  account page loads each list when its tab opens.
- The account page uses the console mail backend and a stub matcher for the local browser check.
