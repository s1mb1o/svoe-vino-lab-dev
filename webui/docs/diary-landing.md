# Wine diary landing page

Date: 2026-10-20
Route: `/diary`
Source: `app/pages/diary.vue`

## Purpose

Introduce the existing account features before sign-in: shared recognition history from the
website and linked Telegram and MAX chats, saved wines, four saved statuses, and private notes.
The public landing page is distinct from the private `/account` page and the `/max` settings mini app.

## Product contract

- One website account owns the history and the saved list. Each messenger must be linked to
  that same account. New recognitions enter history only when recording is enabled.
- The history shows wine data, dates, and sources, with text, color, sugar, and source filters.
  One date per wine per day is kept. The first source of that day wins.
- Saved wines are independent of history. Removing history does not remove saved wines.
- Saved status labels come directly from `shared/diary.ts`: «Не пробовано», «Отведать желаю»,
  «Понравилось», «Не понравилось». Do not maintain a separate translated status list.
- The existing pin action saves a wine from recognition, history, a producer map, or Dinner Lens.
- Private saved-wine notes autosave and participate in saved-list text search.
- Messenger linking uses the current settings UI. Telegram uses a single-use link confirmed
  in its bot. MAX uses the signed mini-app launch and email sign-in to the existing website
  account. The MAX mini app offers settings; history remains on the website.
- The page makes no authenticated account requests and contains no real account data.

## Preview and navigation

The hero has two keyboard-accessible tabs, saved-status filters, and four catalogue wines.
Its dates, statuses, sources, and personal notes are explicitly marked as illustrative.
The preview does not persist or submit anything. Bottle images are existing local assets.

Actions lead to `/account`, `/account?tab=history`, `/account?tab=settings`, the website scanner,
and both bot landing pages. Both bot pages link back to `/diary`.
The shared footer, HTML site map, and XML sitemap expose the public route.
The page has Russian metadata, a canonical URL, and WebPage/WebApplication structured data.

## Verification

Run the existing site map and bot landing tests, full web tests, type checking, and the production
build. Check preview tabs and keyboard controls, each status filter, account destinations, and
site map/bot navigation in Chromium and WebKit. Inspect 320, 390, 768, 1024, and 1440 CSS-pixel
layouts in light and dark themes, and confirm that the public preview makes no account calls.
