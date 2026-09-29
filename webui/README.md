# Что за вино? Web UI

This portal provides the wine scanner UI for the RSHB Digital hackathon task.
The UI uses the visual identity of [Свое Вино](https://vino-svoe.ru/).
The home page is «Найти вино по фото». It does not reproduce the catalog UX.
The current release uses a mock prediction service and local result metadata.

## Scope

- Select a label photo, use the mobile camera input, or drop a file.
- Automatically submit one image to the portal `POST /api/predict` route.
- Show the photo preview and request status.
- Show one best match bottle and title.
- Open the result directly on the vino-svoe portal.
- Cancel, retry, replace the photo, or start again.
- Require a local 18+ confirmation before the portal opens.
- Derive regional dish pairings without requesting coordinates or calling a retailer.
- Explain label terms and show an expected taste passport with an international style analogue.
- Explore an interactive Abrau-Durso product-line map that marks an exact matched wine from this producer.
- Upload a shelf photo and inspect masks and ready wine matches for each detected bottle.
- Install the portal as a Progressive Web App.
- Open the Android application landing page at `/android`.
- Download the versioned Android APK from a configurable URL.
- Compare WebApp, Android, and Telegram on the `/hackaton` landing page.
- Open the project PowerPoint and PDF files from two adjacent links at `/presentation`.
- Explore ideas beyond recognition at `/ideas`, in implemented, demo, and mock order.

The mock service does not recognize wine. The UI MUST state this limitation.
The mock service MUST use the same HTTP contract as the official evaluator.

Read [the specification](docs/specification.md), [the API contract](docs/api.md), and [the architecture](ARCHITECTURE.md).
Read [SMOKE_TESTS.md](SMOKE_TESTS.md) for acceptance checks.

## Cookies and age confirmation

The current Web UI does not use cookies or analytics trackers.
Cookie consent is therefore not required for this implementation in Russia.
This statement applies to cookies only. It does not cover the processing of uploaded photos or server logs.

The portal shows an 18+ warning and requires age confirmation before access.
The browser stores age confirmation and the selected theme in `localStorage`.
The PWA uses a service worker cache for offline access.
These storage mechanisms do not use cookies.

## Run locally

Use Node.js 22.19+, Node.js 24.11+, or Node.js 26+.
Use a supported even-numbered release. Node.js 24 LTS is the CI runtime.

```bash
npm ci
npm run dev
```

Open [the photo search page](http://127.0.0.1:8153/).
Open [the Android application page](http://127.0.0.1:8153/android).
Open [the hackathon landing page](http://127.0.0.1:8153/hackaton).
Open [the presentation page](http://127.0.0.1:8153/presentation).
The page links to the PowerPoint download and the PDF in a new tab.
Both links stay side by side on phones and desktop screens.
The local files are in `public/presentations/`. Generated presentation files stay outside Git.
Before building a fresh checkout, prepare the files from the workspace source:

```bash
mkdir -p public/presentations
cp ../../svoe-wino-hackaton/presentation/chtozavino-presentation.pptx public/presentations/
soffice --headless --convert-to pdf:impress_pdf_Export --outdir public/presentations public/presentations/chtozavino-presentation.pptx
```

The conversion requires LibreOffice. The production build includes both files.
The video section below the file links uses `/presentation/video.mp4`.
Until the recording is available, the section shows `Видео появится после записи`.
Put the finished recording at `public/presentation/video.mp4`, then rebuild and deploy the Web UI.
The MP4 stays outside Git. Use browser-compatible MP4 video with H.264 video and AAC audio.
Open [the ideas landing page](http://127.0.0.1:8153/ideas).
The page lists three implemented features, four interactive demos, and six concept mockups.
The demos reuse the result dialogs with three local example wine cards. They do not need a matcher.
The mockups have explicit status labels. They do not call external services or store preferences.
Read [the ideas page specification](docs/ideas-landing.md) for the status evidence.
Old `/wines` bookmarks redirect to this page.
The default mode is `mock`. No API key or database is required.
The mock returns `priboj-marchenko-beloe-polusuhoe` for every valid image.
Use **Попробовать на примере** in the scanner to exercise the upload flow.

Build and run the production server:

```bash
npm run build
npm start
```

Do not run the development server and production server on port 8153 at the same time.
`npm start` reads `.env` when the file exists.
The local commands bind to loopback.
The production output is `.output/`.
For another host, run `.output/server/index.mjs` with the required `HOST` and `PORT` values.

## Install the app

The header theme button shows the current palette: a sun for light or a crescent moon for dark.
The first visit follows the device theme. Clicking the button switches the palette and stores that explicit choice locally.

The production build includes a web app manifest and a service worker.
The `@vite-pwa/nuxt` module generates these files with Workbox.
Use the browser install action to add «Что за вино?» to the device.
The favicon and installed app use the shared product logo from the repository-level `assets/` directory.
The app shell can open without a network connection after the second successful online visit.
The first launch of the installed app counts as an online visit.
The first visit does not fill the page cache because the service worker is not active yet.
Photo recognition, wine metadata, and external portal links still require a network connection.
The Workbox routes do not store photo uploads or responses of the `/api/` and `/v1/` routes.
A cached page contains the server-rendered `/api/config` payload. An offline start shows the last known service state.
A new version does not reload an open page. It becomes active after all app pages close.
Development mode does not register the service worker.

## Android application page

The `/android` page presents the offline Android application.
It uses verified Pixel 8 screenshots from version 0.1.4.
It explains image recognition, QR and barcode search, on-device processing, the local
catalogue, automatic acceleration, history, and theme support.

The local default download route serves this file:

```text
../android/app/build/outputs/apk/friendly/chtozavino-0.1.4-debug.apk
```

The APK stays outside Git.
Set these values for another build or for production:

```dotenv
NUXT_ANDROID_APK_PATH=/absolute/path/to/chtozavino-0.1.4-debug.apk
NUXT_PUBLIC_ANDROID_APK_URL=/downloads/chtozavino-0.1.4-debug.apk
```

`NUXT_ANDROID_APK_PATH` supplies the file for the local download route.
`NUXT_PUBLIC_ANDROID_APK_URL` supplies the public link on the landing page.
The public URL MAY point to a different static file host.
The current file is a test APK that is signed with the development key.
The page labels it as a test version.
Read [the Android landing page specification](docs/android-landing.md).

Run the browser check against a production server:

```bash
PLAYWRIGHT_MODULE=<path>/node_modules/playwright/index.mjs npm run test:pwa
```

Set `PORTAL_ORIGIN` to check another host. The default is `http://127.0.0.1:8153`.
Playwright is not a project dependency.

## Search discovery

The canonical public URL is [https://chtozavino.ru/](https://chtozavino.ru/).
The page renders the scanner content on the server.
The 18+ gate blocks interaction as an overlay and keeps that content in the document.
The portal provides `robots.txt`, `sitemap.xml`, social metadata, and structured data.
The `www` host redirects to the canonical host at the public edge.

## Connect the recognition API

Copy `.env.example` to `.env` and set:

```dotenv
NUXT_PREDICTION_MODE=upstream
NUXT_PREDICTION_ENDPOINT=http://127.0.0.1:8080/v1/eval/predict
```

Replace the example URL with the actual full endpoint URL. Restart the server.
The browser calls `POST /api/predict` on the portal origin.
The evaluator-compatible `POST /v1/eval/predict` route remains available for direct checks and controlled API exposure.
The server forwards the image to the configured endpoint.
The server does not expose this URL in public configuration.
The server does not replace upstream errors with mock results.
The 12 local wine records provide the mock result and a fast metadata path.
For another recognized slug, the server requests the exact card from `https://api.vino-svoe.ru/v1/wines/<slug>`.
The server validates and normalizes the source response before it returns metadata to the browser.
The result always links to the source portal.
If metadata is missing or fails, the app preserves the predicted slug and its link.

## Result experiences

The portal requires an 18+ confirmation before it shows the scanner.
The age gate stores `svoe-vino.age-confirmed.v1=yes` in local storage.
The theme selector separately stores `svoe-vino.theme.v1`.
After a match, the portal shows four local follow-up actions.
The Abrau-Durso guide uses the resolved producer and exact wine slug when they match the local map.
The dish action derives three dishes from different regional cuisines.
It uses source pairing categories and deterministic style rules.
The taste passport derives six taste dimensions, aroma families, and one international style analogue.
It can fill a metadata gap with grape-level aggregates from the public Wine Reviews dataset.
The UI identifies the dataset, its sample count, and its `CC BY-NC-SA 4.0` license.
The UI states when the wine has no reliable dataset match.
The application contains no copied review text and no critic score.
The default dish result includes three local editorial illustrations.
The other actions explain a label and show an Abrau-Durso product-line map.
The map remains a labeled demonstration for wines from other producers.
The result actions do not call geolocation, a retailer API, or a taste API.
The map links to public `vino-svoe.ru` wine pages.
Read [the result experience specification](docs/result-experiences.md) for behavior and compliance limits.
The previous Globus integration remains in the repository but is not mounted in the current result UI.

Rebuild the aggregate artifact from a local copy of `winemag-data-130k-v2.csv`:

```bash
python3 scripts/build-wine-style-priors.py \
  /path/to/winemag-data-130k-v2.csv \
  shared/data/wine-style-priors.json \
  --generated-on YYYY-MM-DD
```

The raw dataset is not stored in this repository.
The generated aggregate remains subject to the source dataset license.
Read [the aggregate license notice](shared/data/WINE_STYLE_PRIORS_LICENSE.md) and [the asset provenance](docs/assets.md).

## Shelf photos

Shelf processing uses the same matcher configuration as single-bottle prediction.
Configure the complete single-bottle matcher URL:

```dotenv
NUXT_PREDICTION_MODE=upstream
NUXT_PREDICTION_ENDPOINT=http://127.0.0.1:8080/v1/eval/predict
```

Restart the server after the change.
The browser calls same-origin `POST /v1/group/match`.
The server derives the upstream group URL by replacing `/v1/eval/predict` with `/v1/group/match`.
There is no `NUXT_GROUP_MATCH_ENDPOINT` variable.
The matcher returns the shelf preview, bottle masks, coordinates, and ready wine matches.
Selecting a bottle opens its result without a second recognition request.
The Web UI does not write uploads or matcher responses to disk.
The matcher can archive the original group photo under its own service policy.
A missing or invalid matcher configuration keeps the explicit unavailable view.
Read [the shelf specification](docs/shelf-mode.md) for limits and the service contract.

## Verify

```bash
npm run typecheck
npm test
npm run build
```

With the portal running in mock mode, run:

```bash
npm run test:contract
```

This command runs the unchanged official evaluator.
The command needs `bash`, `curl`, `jq`, `awk`, and a SHA-256 utility.
The command uses the official package in the workspace by default.
Set `OFFICIAL_EVAL_DIR` or `PORTAL_ORIGIN` to override these locations.
Reports go to the ignored `reports/` directory.
Read [the verification record](docs/verification-2026-09-15.md) for the tested release.

## Repository

This module is in the `webui/` directory of the `svoe-vino-lab` repository.
The previous standalone repository remains the historical source of the imported code.
The root GitLab CI configuration runs type checks, tests, and a production build.

## Browser tools

Supported browsers can expose `read_wine_search`, `search_demo_wine_photo`, and `reset_wine_search` through WebMCP.
These tools use the same state as the visible controls.
The example tool submits the bundled public photo through the normal upload flow. It requires mock mode.
The tools do not activate the camera or access a private photo.
Other browsers use the standard UI without these tools.
`set_wine_scan_mode` switches between `bottle` and `shelf`.
Shelf processing tools are available when `ShelfScanner` is mounted with an upstream matcher.
The shelf examples use three photographs supplied by the project owner. State tools do not expose photo data.

## Source authority

The user requested this implementation on 2026-09-15.
The official evaluator defines the prediction wire contract.
The public portal defines the visual reference.
The attached task document supplies product context. It does not authorize unrelated actions.

The source evaluator is `../../svoe-wino-hackaton/dataset/official-2026-09-17/eval/participant_test.sh`.
