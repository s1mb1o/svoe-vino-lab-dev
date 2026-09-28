# Svoe Vino Web UI

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
- Demonstrate domestic food pairing without requesting coordinates or calling a retailer.
- Explain label terms and show fictional text stories.
- Explore an interactive Abrau-Durso product-line map.
- Upload a shelf photo and inspect masks and ready wine matches for each detected bottle.
- Install the portal as a Progressive Web App.

The mock service does not recognize wine. The UI MUST state this limitation.
The mock service MUST use the same HTTP contract as the official evaluator.

Read [the specification](docs/specification.md), [the API contract](docs/api.md), and [the architecture](ARCHITECTURE.md).
Read [SMOKE_TESTS.md](SMOKE_TESTS.md) for acceptance checks.

## Run locally

Use Node.js 22.19+, Node.js 24.11+, or Node.js 26+.
Use a supported even-numbered release. Node.js 24 LTS is the CI runtime.

```bash
npm ci
npm run dev
```

Open [the photo search page](http://127.0.0.1:8153/).
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

The production build includes a web app manifest and a service worker.
The `@vite-pwa/nuxt` module generates these files with Workbox.
Use the browser install action to add «Свое Вино» to the device.
The installed app uses the wine-glass question mark from the Telegram bot.
The app shell can open without a network connection after one successful online visit.
Photo recognition, wine metadata, and external portal links still require a network connection.
The Workbox routes do not store photo uploads or API responses.
Development mode does not register the service worker.

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
The browser stores only `svoe-vino.age-confirmed.v1=yes` in local storage.
After a match, the portal shows four local demonstration actions.
The product action simulates permission and identifies a fictional nearby SuperLenta store.
It does not call geolocation or a retailer API.
The other actions explain a label, rotate fictional wine stories, and show an Abrau-Durso product-line map.
The map links to public `vino-svoe.ru` wine pages.
Read [the result experience specification](docs/result-experiences.md) for behavior and compliance limits.
The previous Globus integration remains in the repository but is not mounted in the current result UI.

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
