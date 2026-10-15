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

- `npm test` with `PRODUCT_LINE_CATALOG_SNAPSHOT`: 231 tests passed in 16 files.
- Without the full snapshot, 12 source-file checks are skipped. Pinned baselines and image hashes are still checked.
- `npm run typecheck`: passed.
- `npm run build`: passed, including map validation in `prebuild`.
- Every map JSON is registered. Exact slugs and aliases have no cross-producer collisions.
- Each map matches its independent catalog extract and its crosswalk.
- The initial build verified 638 referenced image files. The later background-extraction pass references 636 files; see [product-image-cutouts.md](product-image-cutouts.md).
- `git diff --check`: passed.

## Browser checks

The existing Abrau-Durso regression suite passed in Chromium and WebKit.
The suite covers alias selection, drag and zoom, popup focus, nested shelf dialogs, short viewports, and breakpoint changes.
The new producer suite passed 45 cases in each engine.
These cases include 40 viewport/theme checks, four large-canvas expand/collapse checks, and one image-before-hydration regression.
Each producer was checked at 1440 px in both themes, 390 px in light theme, and 320 px in dark theme.
The suite checks exact selection, gray selection, missing-image placeholders, portal links, producer changes, and mobile return state.
The suite waits for visible images to load before screenshots.
No unexpected page errors, console errors, or hydration warnings were observed.
The image-failure regression intentionally returns one HTTP 404.

Eight additional scanner integration cases passed.
These cases use Derbent Vino and Fanagoria in both engines at desktop and mobile sizes.
The browser uses controlled prediction and wine metadata responses.
Each case uses one prediction request and one metadata request.
No external service request was made by these fixtures.
The recognized marker survives gray selection.
The locate action returns to the original recognized wine.
The mobile popup preserves canvas scroll, zoom, selection, parent dialogs, and opener focus.

The last linked product was centered at 320 px and 1440 px for all eleven maps in both engines.
Four controlled image-404 cases preserved selection and the exact portal link.

## Reproduction

Set `PLAYWRIGHT_MODULE` to the installed `playwright/index.mjs`.
Set `PORTAL_ORIGIN` to the running local preview.
Set `PRODUCT_LINE_CATALOG_SNAPSHOT` to the full `official-2026-09-17/catalog.jsonl` path to verify its bytes and every producer row.
Run `npm run test:line-map` and `npm run test:producer-maps`.
Set `PLAYWRIGHT_BROWSER=webkit` to repeat both scripts in WebKit.
Use the browser cache path for the installed engine.
The local WebKit cache for this run was `/private/tmp/product-line-map-browsers`.

The scripts write ignored JSON reports and PNG files under `reports/`.
The final independent scanner probe results are saved in `/private/tmp/lineup-expansion/review_setup/integration/final-build/`.
These checks use emulated mobile viewports. No physical device test was performed.

## Review and limits

Claude Opus 5.5 with effort max reviewed the plan and implementation.
The implementation findings were resolved or documented. The reviewer did not rerun the final build.
Read the review records and resolution in `docs/reviews/`.
After image review, ten catalog products and one official addition use a labeled placeholder. The two new exclusions and the image checks are recorded in [product-image-cutouts.md](product-image-cutouts.md).
The shared map chunk is 763.86 kB before compression and 113.86 kB with gzip.
Vite reports its chunk-size advisory. The build succeeds.

## Winery commits

Each winery has one separate commit on `product-line-map`.
Shared UI, registry, and validation changes have separate commits.
The branch has not been pushed as part of this work.

| Producer | Commit |
| --- | --- |
| Дербент Вино | `e9e94b0d` |
| Золотая Балка | `2dbd11bf` |
| Alma Valley | `549eb4c0` |
| Инкерман | `5d9d346f` |
| Массандра | `4d4cf292` |
| Ведерниковъ | `785a7afb` |
| Коктебель | `f0ac8155` |
| Фанагория | `59e563ab` |
| Кубань-Вино | `8fed702f` |
| Мысхако | `0556e26e` |
