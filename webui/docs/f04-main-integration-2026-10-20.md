# F04 integration with main

Date: 2026-10-20, Europe/Moscow.
Authority: the owner's explicit request to merge to `origin/main`.
Main base: `5cd2cecf` (six separate email-code boxes).
F04 base: `e6e1f26f1e42420fa6af418ca00af3988cc4c5a9`.
Saved-picker extension: `f04e06d`.

## Integration

The combined source preserves the current label guide, bot landing pages, and email-code input.
The three content conflicts were in `ChangeLog.md`, `ResearchLog.md`, and `SMOKE_TESTS.md`.
Both sets of entries remain in the resolved documents.
The workbench and account backend match the main base without changes.
Only `origin/main` is the authorized push target. The feature branch stays local.
The original F04 and saved-picker acceptance reports remain unchanged.
This integration does not establish a production deployment or complete the remaining physical-device release checks.

## Validation of the combined source

| Check | Result |
| --- | --- |
| `npm test` | Passed. 30 files. 601 tests passed. 26 existing tests skipped. |
| `npm run typecheck` | Passed. |
| `npm run build` | Passed. |
| `npm run test:f04` | Passed in Chromium and WebKit at 13:43:49 Moscow. No page errors. The normal email-code login returns to both the saved picker and the existing comparison. |
| `npm run test:bundle` | Passed. `/`: 164.8 KB gzip. `/shelf`: 165.0 KB gzip. Producer-map chunks remain lazy. |
| Existing PWA browser check | Passed on the combined build. Warmed offline launch returns HTTP 200 from the service worker. Account APIs remain unavailable offline. Worker update waits. |
| `git diff --check` | Passed. |

New evidence uses `/private/tmp/f04-main-integration-20261020`.
Browser validation uses the actual account service with an isolated database and memory mail.
Recognition uses a deterministic upstream fixture. No recognition-accuracy claim is made.
The final browser report is `browser/browser-report.json` in that evidence directory.
It confirms exact saved selection, replacement, search, cancellation, both themes, retry, empty states, unchanged saved rows and history, and login continuation.
