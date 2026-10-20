# Saved wine comparison

Date: 2026-10-20, Europe/Moscow.
Base: F04 `e6e1f26f1e42420fa6af418ca00af3988cc4c5a9`.
Scope: the owner's request to choose the second wine from saved wines.
This document records the extension. It does not replace the original F04 acceptance report.

## Behavior

The scan result exposes «Сравнить с сохранённым».
The second comparison card exposes «Выбрать из сохранённых».
The picker searches names, producers, regions, and exact IDs.
The first exact ID cannot be the second wine.
The picker permits any supported saved ID, including the same producer and a different style.
The existing eight-field comparison uses two cards from one pinned snapshot.
Unsupported saved IDs have an explicit unavailable state.
The user can cancel a replacement and retain the existing pair.
Back, Escape, close, and focus return use the existing comparison dialog.

## Data boundary

`GET /api/account/saved/comparison?base=<exact-id>` uses the current session and returns `Cache-Control: no-store`.
It reads `/v1/me/saved/slugs` from the existing account service.
It returns only public catalog cards for the saved IDs and the catalog version.
The list has a maximum of 500 IDs.
Private notes and saved statuses do not enter this response.
The private list remains in the mounted picker and is discarded on close or account reset.
Only the first public slug enters session storage for login continuation.
Selection does not change saved wines or history and does not call recognition.
The account schema, account service, and catalog snapshot remain unchanged.

## Validation

The following checks passed on the local working tree after the extension:

| Check | Result |
| --- | --- |
| `npm test` | 28 files passed. 575 tests passed. 26 existing tests skipped. |
| `npm run typecheck` | Passed. |
| `npm run build` | Passed. |
| `npm run test:bundle` | Passed. `/`: 156.2 KB gzip. `/shelf`: 156.4 KB gzip. 25 producer-map chunks remain lazy. |
| Existing PWA browser check on the completed build | Passed. Warmed offline launch returns HTTP 200 from the service worker. Account APIs stay unavailable offline. |
| `npm run test:f04` | Passed in Chromium and WebKit. Completed at 13:27:08 Moscow. No page errors. |
| `git diff --check` and browser-script syntax check | Passed. |

The new browser checks use the actual account service with isolated SQLite and a memory mail sink.
Recognition uses a deterministic upstream fixture. This run does not measure recognition accuracy.
The account test-code override stays disabled. The login check respects the normal email cooldown.
The browser check verifies exact saved selection, replacement, cancellation, search, the empty state, an unsupported ID, failure with retry, Back, Escape, and focus return.
Chromium verifies 320, 390, and 1280 CSS pixels in both themes. The WebKit saved-wine journey runs at 390 CSS pixels.
The check compares saved rows and history before and after selection. Both remain equal, including statuses and notes.
The login check returns to the saved picker without a new scan or automatic save.
The existing alternative-selection, offline-card, account-isolation, and login-pair checks also pass.

Final extension evidence: `/private/tmp/f04-saved-comparison-20261020/accepted/browser-report.json`.
The directory contains the saved-picker and comparison screenshots.
Public screenshot copies are in `/Volumes/Storage/svoe-vino-final/reports/two-wine-saved-comparison-2026-10-20`.
The original evidence at `/private/tmp/f04-implementation-20261020` remains unchanged.
No production deployment or new physical-phone acceptance was performed.
Physical phone screen readers remain a separate human check.
