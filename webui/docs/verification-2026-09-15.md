# Photo search verification

Date: 2026-09-15, Europe/Moscow.
Runtime: Node.js 26.4.0 on macOS arm64.
Application: Nuxt 4.5.2, Vue 3.5.40, Vue Router 5.2.0.
Scope: the dedicated «Найти вино по фото» page, shelf mode, and live food recommendations.

## Results

| Check | Result |
|---|---|
| TypeScript | Passed |
| API, metadata, and scanner state tests | 102 passed in seven files |
| Production build | Passed |
| Official evaluator on the production mock route | 3 of 3 requests accepted |
| Home page | HTTP 200; photo upload controls; no catalog grid or filters |
| Old catalog paths | Redirect to the home page |
| Old detail path | HTTP 302 to the exact vino-svoe card |
| Local metadata records and bottle assets | 12 of 12 available |
| Missing metadata | HTTP 404 |
| Browser tool example | Automatic upload completed; one bottle, title, and external link returned |
| Browser tool invalid input | All three tools rejected extra fields |
| Browser reset | Returned to idle; photo and result cleared |

The browser example returned `priboj-marchenko-beloe-polusuhoe`.
The result title was «Прибой Марченко белое полусухое».
The result image was `/wines/priboj-marchenko-beloe-polusuhoe.webp`.
The result link was `https://vino-svoe.ru/wines/priboj-marchenko-beloe-polusuhoe`.
The invalid tool calls did not change the completed result.
The earlier food preview used manually selected store 5020.
This store was a public test selection. It was not a location inferred for the user.

The production evaluator report is `validation/photo-search-contract.json`.
The report records the unchanged evaluator script hash.
Report timestamps use UTC. The local verification date is 2026-09-15.
`validation/production-contract.json` preserves the earlier catalog baseline report.

## Food results

- Live Globus guest access passed without a login, token, cookie, or proxy.
- The directory returned 22 stores.
- A public location approximately 111 m from store 5020 selected «Глобус Медведково».
- The production request returned three products in 2563 ms.
- The foods were turkey fillet, mozzarella, and hummus.
- Source price units, loyalty conditions, and product URLs were preserved.
- Invalid coordinates returned 400. Unknown wine metadata returned 422. Unknown store returned 400.
- Responses used `Cache-Control: no-store`.
- The browser tool flow reached `ready` with three live products.
- The new browser tools rejected four invalid inputs without altering the result.
- The unchanged official evaluator still accepted three prediction requests.

Evidence: `validation/globus-access.json`, `validation/food-production.json`, and `validation/food-release-contract.json`.
No real user coordinates were obtained or stored.
Location denial, cancellation, and stale responses were verified with state fixtures.
The first sandboxed test run could not bind its local HTTP fixture. The permitted rerun passed all 75 tests.

## Shelf results

- The production route returned HTTP 200 with `Cache-Control: no-store`.
- The normalized public example measured 1280 × 853 pixels and contained no EXIF metadata.
- The response contained 94 bottles without truncation.
- All 94 transparent overlays matched their normalized detector boxes.
- All 94 JPEG crops decoded within the configured crop dimensions.
- Cropped overlays used 504,500 pixels in total. Full-frame overlays would use 102,632,960 pixels.
- Recognition did not run before a bottle selection.
- Selecting `b1` returned the fixed mock slug, title, and exact source portal link.
- The browser flow reached `ready` with 94 bottle controls.
- The popup closed and reopened for `b2` while preserving the shelf.
- Its food flow returned three live products at public test store 5020 without requesting user location.
- Reset returned to `idle` and cleared photo, segmentation, popup, and food state.
- All six new browser tools rejected invalid input. Invalid mode selection preserved the existing wine result.
- Single-bottle example search remained functional.
- The final type check, production build, and 102 tests passed.

Evidence: `validation/shelf-service.json`, `validation/shelf-production.json`, and `validation/shelf-release-contract.json`.
The direct source-image probe returned 96 detections. The normalized JPEG returned 94 detections.
These are model detections. They are not a manually verified segmentation accuracy measurement.
The first portal attempt failed during a cold-start transport reset. The warm service check passed.
Transient transport retry was verified with fixtures. A new cold-start reset was not forced on the shared service.
No private user photos or location were used.

## Limits

Mock mode returns one fixed slug. These checks do not measure recognition accuracy.
Result metadata contains 12 demo entries. Metadata misses preserve the external portal link.
A full visual regression check has not run.
Physical camera capture and a real recognition service have not been tested.
The upstream provider tests use a local HTTP fixture.
Local checks do not establish remote CI status.

Browser location permission on a physical device remains untested.
Globus endpoint stability and current stock are external dependencies.
The live check covers one selected store and does not establish universal store availability.
