# Abrau-Durso catalog completion validation

Date: 2026-10-16.
Status: passed.

The map contains 73 products in 19 groups.
It covers 56 of the 57 producer snapshot cards through 53 canonical slugs and three aliases.
The owner excluded `rozovoe-polusladkoe-2` until exact bottle and collection identification.
The 20 original gray products remain unchanged.
The saved snapshot is `official-2026-09-17`. This is not a claim of complete current manufacturer assortment coverage.

## Data and image checks

- Pass 235 unit tests in 16 files with the full catalog snapshot enabled.
- Match the independent 57-card producer baseline to the original snapshot and its SHA-256.
- Match each of the 21 additions to the exact source name, description, grapes and slug.
- Retain all original 52 product records and their image bytes.
- Decode all 73 source images. Match dimensions and alpha outlines to their measured frames.
- Verify input and output hashes for all 21 new images.
- Confirm that new visible bottles occupy at least 170 px of the 176 px desktop image area.
- Inspect all new images on flat light and dark backgrounds.
- Pass type checks and the production build.

## Browser checks

Chromium and WebKit each pass 63 checks for the new exact slugs.
Each of the 21 new wines is checked at 1440 px in light mode, 390 px in dark mode and 320 px in light mode.
The check verifies initial selection, expanded group, exact centering, image dimensions, visible bottle height, exact portal link and preserved return position.
Mobile checks verify that the popup stays closed on entry and opens on a product tap.
All checks use the production server on port 18553.

Both engines also pass the existing Abrau browser regression suite.
The regression covers recognition aliases, gray products, keyboard and mouse navigation, native touch pan in Chromium, all 73 asset responses, scanner results and nested shelf dialogs.
The regression also covers mobile focus, popup close actions, reading-position reset, landscape views and desktop/mobile breakpoint changes.
One new regression holds the Playfair font response until the map mounts. It verifies exact centering after the font loads.
The larger premium section exposed a 27 px centering drift in Chromium before the fix.
Wait for `document.fonts.ready` before measuring a center target. Do not weaken the center assertion.

The existing in-app Abrau tab is also checked after full navigation and after the final reload.
It displays 19 groups, 73 products and the selected Abrau Estates Oranzh card with its bottle photo.
Mobile checks use browser emulation. No physical-device check is claimed.

Read [abrau-catalog-completion.json](abrau-catalog-completion.json) for structured results.
Read [the source manifest](../product-line-maps/abrau-durso/catalog-extension.json) for every source and image hash.
Read [catalog-lineup-coverage.md](catalog-lineup-coverage.md) for remaining producers without maps.
Ignored visual evidence is in `reports/abrau-catalog-completion/`.

## Repeat

Set `PRODUCT_LINE_CATALOG_SNAPSHOT` to the full recorded snapshot. Run `npm test`, `npm run typecheck` and `npm run build`.
Run `npm run test:line-map` with `PORTAL_ORIGIN=http://127.0.0.1:18553`, the installed `PLAYWRIGHT_MODULE`, and the selected `PLAYWRIGHT_BROWSER`.
Repeat for Chromium and WebKit. Open every new slug from the source manifest on desktop and mobile.
