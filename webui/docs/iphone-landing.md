# iPhone landing page specification

Date: 2026-10-19
Status: Implemented locally

## Objective

Add a public landing page for the native iPhone application.
Use the route `/iphone`.
Keep the existing scanner and Android page unchanged.

## Audience

The page is for an adult user who wants to identify Russian wine on an iPhone.
The page MUST explain the user value before it explains the model pipeline.
The page MUST state the current TestFlight status.

## Product claims

The page MUST describe these verified functions:

- Camera and photo-library input.
- QR-code and barcode input.
- Local recognition after installation.
- A local catalogue of 2,093 wines.
- DIS and YOLO26n-seg segmentation.
- SigLIP2 Base NaFlex p512 as the default image encoder.
- SigLIP2 Base 224 and MobileCLIP2-S2 as optional image encoders.
- Core ML modes `Авто`, `ANE`, and `CPU`.
- Local recognition history.
- VoiceOver and Dynamic Type support.
- Reduce Motion and Reduce Transparency support.
- Voice Control and Switch Control support.

The page MUST state that the portal link needs an internet connection.
The page MUST NOT claim that a physical iPhone performance test passed.
The page MUST identify simulator performance measurements as simulator results.

## Distribution status

The current build has no public TestFlight link.
The page MUST NOT show a direct install action.
The page MUST link release updates to GitHub issue 36.
The WebApp MUST remain the primary available action.

## Page structure

The page contains these sections:

1. A hero with the application value, release status, and main screenshot.
2. A benefit grid.
3. A four-stage local recognition pipeline.
4. A Core ML section with the settings screenshot.
5. An accessibility section.
6. A final release-status action.

## Assets

Use only the verified iPhone 17 Pro simulator screenshots from
`ios/docs/screenshots/` in the dedicated iPhone application branch.
Store WebP derivatives in `public/screenshots/iphone/`.
Record the source and derivative hashes in `docs/assets.md`.

## Appearance

Use the existing portal visual identity.
Use the existing product logo, heading font, and palette variables.
Support light and dark themes.
Support a 320-pixel viewport.
Respect `prefers-reduced-motion`.

## Search discovery

The page MUST have a unique title and description.
The canonical URL MUST be `https://chtozavino.ru/iphone`.
The page MUST publish `SoftwareApplication` structured data.
The sitemap MUST include the iPhone page.

## Verification

The implementation MUST pass `npm run typecheck`.
The implementation MUST pass `npm test`.
The implementation MUST pass `npm run build`.
The browser check MUST cover desktop and phone layouts in light and dark themes.
The browser check MUST confirm the 18+ gate, metadata, screenshots, links, and page width.

## Verification result

Type checks passed.
All 509 active tests passed.
The suite kept 26 documented tests skipped because their optional snapshot was not configured.
The production build passed.
The desktop dark layout and the 390-pixel light layout passed visual inspection.
The 320-pixel dark layout kept all page content inside the supported 320-pixel width.
The age gate, screenshots, one H1, metadata, structured data, and public cache headers passed.
The browser reported no errors or warnings.
