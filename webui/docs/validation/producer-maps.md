# Producer map validation

Date: 2026-10-16.
Branch: `product-line-map`.
Local origin: `http://127.0.0.1:18553`.

## Coverage

The ten new maps contain 595 products in 132 groups.
562 products match exact cards from the `official-2026-09-17` catalog snapshot.
33 products have official evidence but no verified snapshot match.
These products have `wine_slug: null` and no portal link.
The maps do not claim complete coverage of the current official assortment.
All numeric prices remain null. Premium tiers are editorial guidance.

| Producer | Route ID | Groups | Catalog cards | Gray additions |
| --- | --- | ---: | ---: | ---: |
| Alma Valley | `alma-valley` | 8 | 39 | 2 |
| Дербент Вино | `derbent-vino` | 8 | 63 | 4 |
| Фанагория | `fanagoria` | 25 | 102 | 6 |
| Инкерман | `inkerman` | 6 | 15 | 2 |
| ЗМВ Коктебель | `koktebel` | 10 | 26 | 2 |
| Кубань-Вино | `kuban-vino` | 26 | 97 | 6 |
| Массандра | `massandra` | 9 | 44 | 2 |
| Мысхако | `myskhako` | 20 | 92 | 5 |
| Ведерниковъ | `vedernikov` | 10 | 43 | 2 |
| Золотая Балка | `zolotaya-balka` | 10 | 41 | 2 |

Each route has the form `/lineup/<route-id>`.
Add `?wine=<exact-catalog-slug>` to select a wine on entry.
The preview labels this as a link selection.
The scanner labels the actual recognized product separately from the current map selection.

## Automated checks

- `npm test`: 198 tests passed in 16 files.
- `npm run typecheck`: passed.
- `npm run build`: passed, including map validation in `prebuild`.
- Every map JSON is registered. Exact slugs and aliases have no cross-producer collisions.
- Each map matches its independent catalog extract and its crosswalk.
- All 638 referenced image files match the production output bytes.
- `git diff --check`: passed.

## Browser checks

The existing Abrau-Durso regression suite passed in Chromium and WebKit.
The suite covers alias selection, drag and zoom, popup focus, nested shelf dialogs, short viewports, and breakpoint changes.
The new producer suite passed 40 cases in each engine.
Each producer was checked at 1440 px in both themes, 390 px in light theme, and 320 px in dark theme.
The suite checks exact selection, gray selection, missing-image placeholders, portal links, producer changes, and mobile return state.
The suite waits for visible images to load before screenshots.
No page errors, console errors, or hydration warnings were observed.

Eight additional scanner integration cases passed.
These cases use Derbent Vino and Fanagoria in both engines at desktop and mobile sizes.
The browser uses controlled prediction and wine metadata responses.
Each case uses one prediction request and one metadata request.
No external service request was made by these fixtures.
The recognized marker survives gray selection.
The locate action returns to the original recognized wine.
The mobile popup preserves canvas scroll, zoom, selection, parent dialogs, and opener focus.

## Reproduction

Set `PLAYWRIGHT_MODULE` to the installed `playwright/index.mjs`.
Set `PORTAL_ORIGIN` to the running local preview.
Run `npm run test:line-map` and `npm run test:producer-maps`.
Set `PLAYWRIGHT_BROWSER=webkit` to repeat both scripts in WebKit.
Use the browser cache path for the installed engine.
The local WebKit cache for this run was `/private/tmp/product-line-map-browsers`.

The scripts write ignored JSON reports and PNG files under `reports/`.
The independent scanner probe is saved in `/private/tmp/lineup-expansion/review_setup/integration/`.
These checks use emulated mobile viewports. No physical device test was performed.

## Review and limits

The plan and implementation were submitted to Claude Opus 5.5 with effort max.
Read the review records and resolution in `docs/reviews/`.
Nine catalog products lack a confirmed local image. The UI uses a labeled placeholder.
The shared map chunk is 762.74 kB before compression and 113.55 kB with gzip.
Vite reports its chunk-size advisory. The build succeeds.
