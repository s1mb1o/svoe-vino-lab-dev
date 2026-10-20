# Bot landing pages specification

Date: 2026-10-20
Status: Implemented

## Objective

Add public landing pages for the Telegram bot and the MAX bot.
Use the layout of `/iphone`.
List the bot features.
Add both pages to the «Приложения» group of `/sitemap`.

## Routes

- `/telegram-bot` presents `@ChtoZaVinoBot` (`https://t.me/ChtoZaVinoBot`).
- `/max-bot` presents `@se14697933_bot` (`https://max.ru/se14697933_bot`).

`/max` MUST NOT be used for a landing page.
`/max` is the MAX mini app of «Винный дневник» (`isMaxAppPath` in `shared/account.ts`).
On the main host, `/max` redirects to `/account`.
The owner selected `/telegram-bot` and `/max-bot` on 2026-10-20.

## Implementation

- `app/data/botLandings.ts` holds the content of both pages.
- `app/components/BotLanding.vue` renders one page from one content object.
- `app/pages/telegram-bot.vue` and `app/pages/max-bot.vue` pass the content to the component.
- `app/app.vue` shows «Бот в Telegram» or «Бот в MAX» in the header section and the footer.
- `AppIcon.vue` has the `message` icon for MAX. The site does not use the MAX logo.

## Product claims

The owner selected the feature set of GitHub `main` on 2026-10-20.
The production bots can run older revisions. Some claims need a bot update first.
See «Production gap».

The pages MUST describe these functions of both bots:

- A photo, an album, or an image file: JPEG, PNG, WebP, HEIC, or HEIF.
- HEIC and HEIF conversion to JPEG without EXIF data.
- One result for each photo of an album.
- The wine card: bottle image, name, producer, color, sugar, grape varieties, and «Открыть страницу вина».
- The queue receipt with the position and the approximate wait.
- «✅ Совпало» and «❌ Не совпало» for a single photo, three alternatives after «❌ Не совпало».
- The tentative answer when the confidence is low.
- The «Винный дневник» history records when the messenger is linked and recording is on.
- The automatic safety check and the 30-day deletion of photos and request data.
- The 18+ confirmation. A photo sent before the confirmation is processed after it.
- The commands `/start`, `/help`, `/stats`, and `/privacy`.
- The limit of 50 photos per hour.

The Telegram page MUST also describe the one-time diary link and `/unlink`.
The MAX page MUST describe the link in the MAX mini app. The MAX page MUST NOT list `/unlink`.

## Production gap

Production state on 2026-10-20 at 10:50 MSK, from the container labels on gx10:

- The production Telegram bot runs revision `014654bf` of GitHub `main`, with `BOT_ACCOUNT_ENDPOINT` set.
  It has all the functions that the Telegram page describes.
  The `chtozavino-deploy` record still states revision `874fbd6`. That record is out of date.
- The production MAX bot runs revision `3e7c20d2` of 2026-10-18.
  It does not send «Винный дневник» history records.

Deploy the MAX bot from GitHub `main` before the MAX page goes live, or accept the gap.

## Page structure

1. A hero with the bot value, the bot action, the facts, and an example chat.
2. A grid of 8 features.
3. Four steps from the first message to the checked result.
4. «Винный дневник»: the history, the link steps, and a link to `/account`.
5. The command list.
6. A final action with the bot link, the scanner link, and the privacy link.

## Example chat

The hero chat is HTML. It is not a platform screenshot.
The caption states «Пример переписки · не снимок экрана Telegram» or «… MAX».
The chat MUST use the real bot texts: the queue receipt, the caption labels, and the button labels.
The example wine is «Абрау-Дюрсо Пино Нуар» with the existing image
`public/line-wines/abrau-dyurso-abrau-dyurso-pino-nuar-krasnoe-suhoe-13.webp`.
The chat has `role="img"` and a text alternative. Screen readers read the alternative only.
The chat font size uses `cqw` units, so the chat scales with the phone frame.

## Appearance

Use the palette variables, the heading font, and the section styles of `/iphone`.
Support light and dark themes. Support a 320-pixel viewport.
Respect `prefers-reduced-motion`.
Secondary text uses `--bot-soft` (`--ink` 75 % on `--paper`), not `--muted`.
`--muted` has a contrast ratio of 3.93:1 on `--paper` in the light theme.
`--bot-soft` has at least 5.73:1 on `--paper` and `--cream` in both themes.

## Search discovery

Each page has a unique title and description.
The canonical URL is `https://chtozavino.ru/telegram-bot` or `https://chtozavino.ru/max-bot`.
Each page publishes `WebPage` structured data with a `SoftwareApplication` in `about`.
`public/sitemap.xml` and `app/data/sitemap.ts` list both pages.

## Verification

- `tests/bot-landing.test.ts` checks the content, the routes, the site map, and the header labels.
- `npm run typecheck`, `npm test`, and `npm run build` MUST pass.
- A browser check MUST cover 320, 390, 768, 1024, and 1440 CSS pixels in both themes.
