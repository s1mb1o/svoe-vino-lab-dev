# Ideas landing page

## Wine&Dine Merge entry, 2026-10-19

The Game invitation after the interactive demos opens `/game`.
The game is a working educational prototype on a separate origin.
The former blind-style quiz mock card now shows Wine&Dine Merge and links to `/game`.
Its image and badge identify a working browser game. The card does not promise a blind-style quiz.
The Game invitation is separate from the implemented features, four result demos, and remaining mockups.
Read [the game landing contract](game-landing.md).

The `/ideas` page describes product ideas beyond photo recognition.
The page uses Russian UI text and the shared product identity.
The page keeps the shared age gate, theme control, and health warning.
The page MUST keep this section order: implemented, demo, mock.
The sections use the stable fragments `#implemented`, `#demo`, and `#mock`.
The section links show counts derived from their content arrays.

## Status evidence

The implemented section describes four complete scenarios.
Each card identifies the application that provides the scenario.

| Scenario | Source |
| --- | --- |
| Find wine from a dish photo, name, or category | `app/components/DinnerScanner.vue`, `docs/dinner-lens.md` |
| Open the exact source catalogue card | `app/components/PhotoScanner.vue`, `server/utils/wine-metadata.ts`, `shared/catalog.ts` |
| Read and clear local recognition history | `../android/app/src/main/java/com/alolalab/chtozavino/AppUi.kt`, `../android/README.md` |
| Confirm a match or show three alternatives | `../telegram-bot/README.md`, requirements 28 to 30 |

The demo section describes all four current result actions.
The source of truth is `app/components/WineExperiences.vue` and `docs/result-experiences.md`.
Dish and taste rules run on the selected wine metadata.
The label explanation uses the fixed Syrah and Viognier example.
The product-line map contains six Abrau-Durso examples.
These actions remain demos even when part of their logic is complete.

The final section shows four static interface sketches and one working game link.
The sketches cover audio stories, taste search and similar wines,
personal preferences, and planogram comparison.
The game card links to the landing page at `/game`.
These ideas come from `../docs/feature-inventory-2026-09-28.md`.
The sketch badges do not claim that those services exist. The game has its own working-prototype badge.
The planogram card distinguishes existing shelf recognition from missing planogram features.
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
