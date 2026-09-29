# Photo search specification

Date: 2026-09-15.
Status: ready for implementation.
Authority: the user corrected the portal scope on 2026-09-15.
This specification replaces the previous catalog UX specification.

## Goal

The home page MUST be «Найти вино по фото».
The page MUST use the visual identity of `https://vino-svoe.ru/`.
The page MUST NOT reproduce the source portal catalog experience.
The page MUST provide «Одна бутылка» and «Вся полка» modes.
Read [the shelf mode specification](shelf-mode.md) for segmented shelf photos and wine popups.
Read [the result experience specification](result-experiences.md) for the mandatory age gate
and the local demonstration actions after recognition.
The deployment MUST enable «Вся полка» when the configured upstream matcher provides `/v1/group/match`.
The browser MUST send a shelf photo only to the same-origin portal route.
The matcher MUST return bottle coordinates, masks, matches, and wine descriptions in one response.

## Visual design

Use the shared product logo from `../assets/` and the product name `Что за вино?`.
Use Playfair Display headings, burgundy controls, cream surfaces, and the grapevine background.
Use one photo search workspace. Do not show a catalog grid, filters, sorting, or local wine detail navigation.
On desktop, place the upload area beside the result area.
On phones, place the result below the upload area. Keep the upload action prominent.
Show large touch targets. Prevent horizontal overflow.
Provide one theme button in the page header. Show a sun for the current light palette and a crescent moon for the current dark palette.
Follow the system theme when there is no explicit saved light or dark preference.
Do not write a preference on page load or on system theme changes.
On click, switch to the opposite palette and store the explicit choice in local storage.
Apply a saved preference before first paint. Keep the visible icon aligned with the palette before hydration.
Apply the selected palette to the full page and dialogs.
Follow the reduced motion preference.

## Progressive Web App

The production portal MUST provide an installable web app manifest.
The portal MUST provide 192 by 192 and 512 by 512 PNG icons.
The portal MUST provide a maskable 512 by 512 PNG icon.
The favicon and install icons MUST use the shared product logo from `../assets/`.
The manifest SHOULD provide one narrow and one wide JPEG screenshot of the home page.
The page MUST provide a `theme-color` for the active light or dark theme.
The service worker MUST store only the app shell and same-origin static assets.
The service worker MUST NOT store photo uploads or responses of the `/api/` and `/v1/` routes.
A cached page MAY contain the server-rendered `/api/config` payload.
This payload holds only the prediction mode, availability flags, and limits. It holds no photo and no recognition result.
An offline start can therefore show the last known service state.
A photo submit without a network connection MUST show a network error.
The app shell MAY open without a network connection after the second successful online visit.
The first launch of the installed app counts as an online visit.
The first visit does not fill the page cache because the service worker is not active during the first navigation.
An updated service worker MUST NOT reload an open page.
The updated service worker MUST wait until all app pages close. The next start uses the new version.
Recognition, metadata, and external links require a network connection.
Development mode MUST NOT register the service worker.

## Search discovery

The canonical public URL MUST be `https://chtozavino.ru/`.
The `www` host MUST redirect to the canonical host with HTTP 308.
The server-rendered page MUST contain the scanner heading and explanatory content.
The age gate MUST block interaction without removing the scanner from the document.
The page MUST keep `Найти вино по фото` as its primary heading.
The page MUST provide a canonical link, Open Graph metadata, Twitter card metadata,
and JSON-LD for `WebSite` and `WebApplication`.
The page MUST NOT provide wine `Product` metadata.
The portal MUST provide `robots.txt` and a one-URL `sitemap.xml`.
Compatibility redirects from `/wines` and `/wines/<slug>` MUST be permanent.
Static reference assets SHOULD use a bounded public cache policy.

## Flow

1. The user selects one photo, takes a photo, drops one file, or selects the demo example.
2. The app validates the file and shows a preview.
3. The app MUST automatically submit one request. Do not require a second submit action.
4. The app MUST show progress and offer cancellation.
5. The app MUST show one best match with the bottle image and title when metadata is available.
6. The result MUST link directly to `https://vino-svoe.ru/wines/<slug>`.
7. The user MAY replace the photo, reset the page, or retry a failed request.

## State and errors

Accept JPEG, PNG, and WebP files up to 10 MiB.
Reject empty files and multiple files before prediction.
A new selection MUST cancel and invalidate the previous request.
A stale response MUST NOT change the current result.
Release the preview URL on replacement, reset, and unmount.
A valid prediction slug MUST survive metadata failure or timeout.
If metadata is unavailable, show the slug and its source portal link. Do not invent a bottle or title.
Show a readable message when configuration or prediction is unavailable.
In upstream mode, the server MUST check matcher readiness when the browser requests `/api/config`.
The browser MUST disable photo selection when matcher readiness fails.
The retry action MUST request `/api/config` again.
Mock mode MUST be visible before upload and on the result.
The mock result MUST NOT claim to identify the uploaded image.
Do not display a confidence score. The evaluator response does not provide one.

## Routes and API

`/` is the primary page.
`/wines` and `/wines/` MUST redirect to `/` for existing bookmarks.
Previous local wine detail routes MUST redirect to the corresponding source portal page.
Preserve `POST /v1/eval/predict`: one multipart file named `image`, response `{"slug":"..."}`.
Preserve the existing mock and upstream provider configuration.
Use the local metadata fixture to resolve the demo result.
Resolve other valid slugs through the official source JSON API.
Validate and normalize source metadata on the portal server.
Do not display either metadata source as a catalog.
Photos MUST remain in request memory. Do not write photos to disk.

## Acceptance

- The home page presents photo search without a catalog interface.
- Valid selection sends exactly one automatic prediction request.
- A known result contains one bottle, title, and exact external portal link.
- Metadata errors preserve a successful prediction and external link.
- Cancellation and replacement prevent stale results.
- Mock disclosure remains visible.
- Type checks, relevant state tests, and production build pass.
- The unchanged official evaluator accepts the production mock endpoint.
- The production page exposes the manifest and registers the service worker.
- The manifest exposes regular and maskable icons with the declared sizes.
- The manifest screenshots have the declared sizes.
- `npm run test:pwa` passes: no installability errors, offline start after two visits, no cached API route, and no reload after a service-worker update.

## Limits

Real prediction requires a configured upstream matcher.
The metadata fixture contains 12 wines for the mock and fast local lookup.
An unknown slug uses the official source API and then the explicit metadata fallback if no valid card is available.
Physical camera capture needs a supported phone and browser.

## Legacy retailer integration

Date: 2026-09-15. Status: retained but not rendered.

The repository retains the previous Globus integration for reference.
The current result UI MUST NOT mount `FoodRecommendations`.
The current `Подобрать блюда` action MUST follow `docs/result-experiences.md`.
It MUST use resolved wine metadata and local deterministic rules.
It MUST NOT request coordinates or call retailer routes.
The legacy `GET /api/food/stores` and `POST /api/food/pairings` routes MAY remain in the codebase.
They are outside the active portal flow.
