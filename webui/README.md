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
- Find the nearest Globus store after explicit location permission, or select a store manually.
- Recommend three food products with live store prices, availability, and pairing explanations.
- Open «Вся полка» and see an explicit temporary-unavailable state without photo upload.

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
Result metadata remains a 12-wine demo fixture in upstream mode.
The result always links to the source portal.
If metadata is missing or fails, the app preserves the predicted slug and its link.
Replace `server/data/wines.json` or the metadata routes when complete catalog access becomes available.

## Food recommendations

After a match, press «Подобрать 3 продукта к вину».
The browser requests location permission. The server selects the nearest Globus store by straight-line distance.
Use «Выбрать магазин вручную» without location permission.
The food feature uses the live Globus guest API. It requires network access, but no API key or account.
Recognition stays in mock mode until configured. Food recommendations then refer to the demo wine.
Product prices and availability come from the selected store. Loyalty price conditions remain visible.
The app shows fewer products when suitable stock is insufficient. It does not substitute mock products.
The Globus integration uses application endpoints. Their contract can change.
The current network directory has limited geographic coverage. A distant store is explicitly marked.
Geolocation requires HTTPS or a secure localhost origin. Coordinates stay in request memory.
The server sends only the store ID to Globus. It does not send user coordinates.
Food selection uses source pairing labels and editorial rules. It does not call an LLM.
Read [the retailer contract](docs/food-api.md) for routes, evidence, and limits.

## Shelf photos

Shelf processing is disabled by default.
Select «Вся полка» to see the temporary-unavailable state.
The disabled interface has no file or camera control.
The server rejects `POST /api/shelf/segment` before it reads the upload or calls SAM3.

Set both variables only when shelf processing is approved:

```dotenv
NUXT_SHELF_MODE=enabled
SAM3_ENDPOINT=http://192.168.86.14:18081/upstream/sam3
```

Restart the server after the change.
When enabled, the browser calls our `/api/shelf/segment` route. Only our server calls SAM3.
The gateway can load the model on demand. The first request can take over one minute.
The service budget is 300 seconds. A missing endpoint produces an explicit error.
The server normalizes orientation and removes metadata before segmentation.
Photos, masks, and crops remain in memory. The server does not write uploads to disk.
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
After a match, `read_wine_food_pairings`, `list_wine_food_stores`, and `recommend_wine_food_at_store` are available.
The store tool uses an explicit store ID. It does not request geolocation or create an order.
Other browsers use the standard UI without these tools.
`set_wine_scan_mode` switches between `bottle` and the temporary-unavailable `shelf` view.
Shelf processing tools are available only when `ShelfScanner` is mounted in an enabled deployment.
The shelf example uses the bundled public Wikimedia photo. State tools do not expose photo data.

## Source authority

The user requested this implementation on 2026-09-15.
The official evaluator defines the prediction wire contract.
The public portal defines the visual reference.
The attached task document supplies product context. It does not authorize unrelated actions.

The source evaluator is `../../svoe-wino-hackaton/dataset/official-2026-09-17/eval/participant_test.sh`.
