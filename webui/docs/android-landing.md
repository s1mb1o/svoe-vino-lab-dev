# Android landing page specification

Date: 2026-09-29
Status: Implemented and verified

## Objective

Add a public Android application landing page to the existing Web UI.
Use the route `/android`.
Keep the existing `/` wine scanner unchanged.

## Audience

The page is for an adult user who wants to identify Russian wine on an Android phone.
The page MUST explain the main value before it shows technical details.
The page MUST identify the current APK as a test version.

## Primary message

The application recognizes wine without an internet connection after installation.
It supports a camera photo, a gallery image, QR codes, and barcodes.
It keeps the recognition models and the wine catalogue on the phone.

## Benefits

The page MUST show these benefits:

- Offline image recognition after installation.
- Camera and gallery input.
- QR and barcode search.
- On-device photo processing.
- A built-in catalogue of 2,093 wines.
- Automatic GPU or CPU selection.
- Local recognition history.
- Light and dark themes.
- Android 9 and later.
- A direct link to the matching page on `vino-svoe.ru`.

The page MUST state that a portal link needs an internet connection.
The page MUST NOT describe cosine similarity as a probability or calibrated confidence.

## Download contract

The page MUST show the application version and the APK size.
The download button MUST use the public runtime value `androidApkUrl`.
The environment variable is `NUXT_PUBLIC_ANDROID_APK_URL`.
The default URL MUST be `/downloads/chtozavino-0.1.4-debug.apk`.

The Web UI MUST NOT store the generated APK in Git.
The local server route MUST stream the APK from `androidApkPath`.
The environment variable is `NUXT_ANDROID_APK_PATH`.
The local default path MUST point to the versioned Android build output.
The route MUST return HTTP 404 when the configured file is not available.
The route MUST set the Android package content type.
The route MUST set the versioned attachment file name.

## Page structure

The page MUST contain these sections:

1. A hero with the primary message, download action, and two application screenshots.
2. A benefit grid.
3. A three-step image-recognition explanation.
4. A QR and barcode section.
5. A technical summary and a repeated download action.

The page MUST link to the existing web scanner.
The global header MUST link between the web scanner and the Android page.

## Assets

Use only verified Pixel 8 screenshots from
`../android/docs/screenshots/android-0.1.4/web/`.
Copy the selected derivatives into `public/screenshots/android/`.
Record their provenance in `docs/assets.md`.

## Appearance

Use the existing Web UI visual identity.
Use the existing product logo, Playfair Display heading font, and color variables.
Support light and dark themes.
Follow the current system preference until the user makes an explicit theme selection.
Support a 320 pixel viewport.
Respect `prefers-reduced-motion`.

## Search discovery

The page MUST have a unique title and description.
The canonical URL MUST be `https://chtozavino.ru/android`.
The page MUST publish `SoftwareApplication` structured data.
The sitemap MUST include the Android page.

## Verification

The implementation MUST pass `npm run typecheck`.
The implementation MUST pass `npm test`.
The implementation MUST pass `npm run build`.
An automated test MUST check the page content, release metadata, asset signatures,
download route, sitemap entry, and header navigation.
A browser check MUST cover desktop and mobile layouts in light and dark themes.
The local download URL MUST return the versioned APK headers.

## Open questions

There are no open questions for implementation.
Production deployment MUST configure `NUXT_ANDROID_APK_PATH` or
`NUXT_PUBLIC_ANDROID_APK_URL` before the public download is enabled.

## Verification result

Type checks passed.
All 169 tests passed in 14 files.
The production build passed.
The local APK route returned the expected HTTP 200 headers.
An invalid APK file name returned HTTP 404.
The desktop light layout and the mobile light and dark layouts passed a visual check.
