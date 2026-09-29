# Ideas landing page

The `/ideas` page describes product ideas beyond photo recognition.
The page uses Russian UI text and the shared product identity.
The page keeps the shared age gate, theme control, and health warning.
The page MUST keep this section order: implemented, demo, mock.
The sections use the stable fragments `#implemented`, `#demo`, and `#mock`.
The section links show counts derived from their content arrays.

## Status evidence

The implemented section describes three complete scenarios.
Each card identifies the application that provides the scenario.

| Scenario | Source |
| --- | --- |
| Open the exact source catalogue card | `app/components/PhotoScanner.vue`, `server/utils/wine-metadata.ts`, `shared/catalog.ts` |
| Read and clear local recognition history | `../android/app/src/main/java/com/alolalab/chtozavino/AppUi.kt`, `../android/README.md` |
| Confirm a match or show three alternatives | `../telegram-bot/README.md`, requirements 28 to 30 |

The demo section describes all four current result actions.
The source of truth is `app/components/WineExperiences.vue` and `docs/result-experiences.md`.
Dish and taste rules run on the selected wine metadata.
The label explanation uses the fixed Syrah and Viognier example.
The product-line map contains six Abrau-Durso examples.
These actions remain demos even when part of their logic is complete.

The mock section shows six static interface sketches.
The sketches cover grocery ingredients, audio stories, taste search and similar wines,
personal preferences, a blind-style quiz, and planogram comparison.
These ideas come from `../docs/feature-inventory-2026-09-28.md`.
The landing page adds the sketches. It does not claim that the services exist.
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
