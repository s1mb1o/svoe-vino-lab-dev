# Ideas landing page

## Implemented ideas moved, 2026-10-20

The owner requested this change. Live features MUST NOT stay in the demo or mock sections.
These items moved to the implemented section:

| Former item | Former section | Implemented card | Link |
| --- | --- | --- | --- |
| Wine&Dine Merge | mock | Wine&Dine Merge | `/game` |
| Личный паспорт предпочтений | mock | Винный дневник | `/account` |
| Этикетка понятным языком | demo | Что расскажет этикетка | `/` |
| Место в линейке | demo | Путеводитель по линейке | `/lineup` |

The mock card «Полка как система» was removed. The Shelf Lens card names comparison with a reference planogram as the next step.
The diary card describes saved wines, notes, and history. It does not promise a taste profile or personal recommendations.
The line-map card takes the producer count from `PRODUCT_LINE_INDEX`.
The mock card «Искать по вкусу» did not change. F04 alternatives do not search by a described taste.

## Wine&Dine Merge entry, 2026-10-19

The Game invitation after the interactive demos opens `/game`.
The game is a working educational prototype on a separate origin.
On 2026-10-19, the former blind-style quiz mock card showed Wine&Dine Merge and linked to `/game`.
Since 2026-10-20, the game is an implemented card. The mock section has no game card.
The Game invitation is separate from the implemented features, the result demos, and the remaining mockups.
Read [the game landing contract](game-landing.md).

The `/ideas` page describes product ideas beyond photo recognition.
The page uses Russian UI text and the shared product identity.
The page keeps the shared age gate, theme control, and health warning.
The page MUST keep this section order: implemented, demo, mock.
The sections use the stable fragments `#implemented`, `#demo`, and `#mock`.
The section links show counts derived from their content arrays.

## Status evidence

The implemented section describes nine complete scenarios.
Each card identifies the application that provides the scenario.

| Scenario | Source |
| --- | --- |
| Scan a shelf video with AR ratings and a planogram | `app/pages/shelf-lens.vue`, `../shelf-lens/README.md` |
| Find wine from a dish photo, name, or category | `app/components/DinnerScanner.vue`, `docs/dinner-lens.md` |
| Open the exact source catalogue card | `app/components/PhotoScanner.vue`, `server/utils/wine-metadata.ts`, `shared/catalog.ts` |
| Read the label guide of a recognized wine | `app/components/WineExperiences.vue`, `shared/label.ts` |
| Open the product-line map of the producer | `app/components/WineExperiences.vue`, `app/pages/lineup/`, `shared/product-line-map.ts` |
| Read and clear local recognition history | `../android/app/src/main/java/com/alolalab/chtozavino/AppUi.kt`, `../android/README.md` |
| Save wines with notes and read the history in «Винный дневник» | `app/pages/account.vue`, `app/components/PinButton.vue`, `app/components/DiarySaved.vue` |
| Confirm a match or show three alternatives | `../telegram-bot/README.md`, requirements 28 to 30 |
| Play Wine&Dine Merge in the browser | `app/pages/game.vue`, [game landing contract](game-landing.md) |

The demo section describes two result actions: dishes and taste.
The source of truth is `app/components/WineExperiences.vue` and `docs/result-experiences.md`.
Dish and taste rules run on the selected wine metadata.
These actions remain demos even when part of their logic is complete.
The example playground still opens all four result actions, including the implemented label guide and line map.

The final section shows two static interface sketches: audio stories, and taste search with similar wines.
These ideas come from `../docs/feature-inventory-2026-09-28.md`.
The sketch badges do not claim that those services exist.
The mockups MUST NOT present working purchase, playback, search, quiz, or save controls.

## Demo interaction

The page requests the existing local `/api/wines` endpoint through server rendering.
The page limits the selector to three bundled wine cards.
The page identifies the selected card as an example, not as a recognition result.
Changing the card remounts the existing `WineExperiences` component.
All four dialogs keep their existing keyboard, focus, and close behavior.
The page shows a retry action when example cards are unavailable.
The examples MUST NOT call the matcher, geolocation, or retailer endpoints.

## Discovery and assets

The shared footer and `/hackaton` link to `/ideas`.
The page has route-specific canonical and social metadata and a sitemap entry.
The hero and demo section reuse existing bottle and dish images.
The page creates mock interface visuals with HTML and CSS.
No new external image asset is required.
