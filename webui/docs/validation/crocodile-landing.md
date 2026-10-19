# Wine Crocodile verification

Date: 2026-10-19.

The final source passes `npm run typecheck` and `npm run build`.
The build hook passes 94 existing map tests and skips 20 existing tests.
`npm run test:bundle` passes. The scanner and shelf first-load bundles remain about 139 KB gzip.
The browser script passes sixteen layouts in Chromium and WebKit.
The layouts use 320, 390, 768, and 1440 pixel widths in both system themes.
The script verifies the portal age gate, metadata, navigation, all color filters, keyboard and mouse flips, legend status, FAQ, and image loading.
Both downloadable PDFs match the recorded owner-master hashes.
The final script also verifies the two photo aspect ratios and actual text and primary-button contrast.
The rendered light and dark desktop pages and mobile pages were inspected.
The screenshots and machine-readable result are in `reports/crocodile/`.
No physical phone test or production deployment was performed.

## Resolved visual failures

The initial detail photo retained a fixed HTML height after its width changed.
Set `height: auto` and check the rendered 4:3 ratio at each viewport.

The initial scoped theme selectors put the root theme selector inside `:global(...)` and the page selector outside it.
The current Vue transform reduced that selector to the root theme selector.
This changed the root background and text color.
Put the complete theme and page selector inside `:global(...)`.
Check rendered contrast and background luminance. A theme-attribute check alone does not verify the appearance.
