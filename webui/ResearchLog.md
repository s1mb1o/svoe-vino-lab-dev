# Research log

## Complete result metadata fallback, 2026-09-29

The upstream recognizer can return more wine slugs than the 12 local Web UI records contain.
The source portal provides `GET https://api.vino-svoe.ru/v1/wines/<slug>`.
The endpoint returned the complete card for `massandra-muskat-rozovyy-pozdnego-sbora-rozovoe-sladkoe-10`.
The response includes the title, producer, region, grapes, style, description, and source image path.
Decision: keep the local records as the first lookup.
Decision: request an unknown valid slug from the official source JSON API.
Decision: use a fixed source host and reject redirects, mismatched slugs, untrusted image paths, oversized responses, and invalid records.
Decision: keep the existing explicit UI fallback when source metadata is unavailable.

## Owner-supplied shelf examples, 2026-09-29

The project owner supplied four supermarket shelf photographs.
The first and fourth files had the same SHA-256 value.
Decision: store the three unique photographs.
Decision: replace the Wikimedia example and its attribution.
Decision: convert each photograph to a 2560 by 1928 WebP file.
Decision: remove embedded metadata during conversion.
Decision: let the visitor select one example before the portal sends it through the normal group-match route.

## Production resilience verification, 2026-09-29

A bounded public load test sent one, four, eight, and twelve concurrent recognition requests.
All requests passed through concurrency eight.
At concurrency twelve, eight requests passed and four requests reached the matcher capacity guard.
The matcher returned HTTP 503 with `matcher is busy`.
The Web UI changed this response to HTTP 502.
The same mapping changed the matcher HTTP 413 JPEG pixel-limit response to HTTP 502.
Decision: preserve the matcher HTTP status when the status is safe and actionable.
Decision: do not expose the matcher response body.
Decision: map an unexpected matcher status or an invalid matcher response to HTTP 502.

The live shelf example returned HTTP 502 from the Web UI.
The deployed matcher revision was `9ba496d230d23398f76275cbbd187d5a820c4bfe`.
Its OpenAPI document did not contain `/v1/group/match`.
Commit `b752591` added this endpoint after the deployed revision.
Decision: deploy a committed matcher revision that includes `b752591` before shelf mode stays enabled.

Web UI revision `11ebfbf` preserved HTTP 413 for the JPEG dimension bomb.
A second 12-request burst returned nine HTTP 200 responses and three HTTP 503 responses.
The matcher health route stayed at HTTP 200.
The first shelf request after the route deployment found 93 bottles.
It failed because the SigLIP2 service accepts at most 64 inputs in one request.
Matcher revision `013ab56` split larger logical batches into requests of at most 64 inputs.
The final public shelf request returned HTTP 200 in 2598.775 ms.
It returned 93 bottles and 93 ready matches.
The production browser opened bottle 1 as `Траминер` and closed the card without a second recognition request.

## Search discovery and age gate, 2026-09-28

The age gate previously replaced the complete server-rendered page with a loading element.
A new visitor then received only the age gate after hydration.
Decision: always render the scanner page.
Decision: render the age gate as a fixed overlay before the local storage check.
The client removes the overlay only after it finds a stored confirmation.
Decision: make the scanner controls inert while the gate is open.
This design preserves the mandatory interaction block and keeps the page content available to crawlers.
The apex and `www` hosts previously returned identical HTML without a canonical signal.
Decision: use `https://chtozavino.ru/` as the canonical URL.
Decision: redirect the complete `www` host to the apex with HTTP 308 at Caddy.
Decision: publish one sitemap URL because the portal has one indexable page.
Decision: describe the portal as `WebSite` and `WebApplication`.
The portal does not own indexable wine pages, so it does not publish wine `Product` metadata.
The reference file names are stable but are not content hashes.
Decision: cache these files for seven days and allow one day of stale revalidation.

## Matcher readiness, 2026-09-28

The matcher provides the public `GET /healthz` readiness route.
The readiness response contains `status: "ok"` and the selected pipeline.
The configured prediction URL can use a private loopback or network address.
Decision: the Nuxt server checks matcher readiness.
Decision: derive the health path from the final `/v1/eval/predict` path.
Decision: do not change the Web UI `GET /api/health` liveness contract.
Decision: report matcher readiness as `apiAvailable` in `GET /api/config`.
The prediction request remains the final availability check because readiness can change after the configuration request.

## Progressive Web App, 2026-09-28

The user requested PWA support and the Telegram bot icon.
The Web UI reuses `telegram-bot/assets/botpic.svg` as the icon source.
The user selected the PWA module implementation after reviewing the first local implementation.
Decision: use `@vite-pwa/nuxt` 1.1.1 and its generated Workbox service worker.
The installed module resolves `vite-plugin-pwa` 1.3.0.
The package audit reported no vulnerabilities after installation.
Decision: use automatic service-worker updates and generated manifest registration.
Decision: precache Nuxt client bundles, install icons, and app-shell reference assets.
The production Workbox build precaches 22 entries with a total size of 638 KiB.
Decision: use `NetworkFirst` for page navigation and exclude the `/api/` and `/v1/` route prefixes.
Workbox runtime routes use GET by default. Photo upload requests do not match a cache route.
Development mode does not enable the generated service worker.
The maskable icon uses a solid cream background and keeps the mark in the central safe area.
Recognition, metadata, and source portal navigation remain online-only operations.
The production browser loaded the manifest link and the new SVG favicon without warnings or errors.
The production contract check loaded the service worker, manifest, and all declared PNG icons.

## Local result demonstrations, 2026-09-28

The selected implementation is a fully local demonstration.
The product action must explain a future coordinate request without invoking browser geolocation.
Decision: use a fictional SuperLenta store and fictional domestic products.
Decision: mark paid food priority visibly and do not include an alcohol purchase action.
The public `vino-svoe.ru` Abrau-Durso catalog provides stable wine detail paths for the product-line demonstration.
Decision: keep map positions and descriptions local and link each node to its public source page.
Decision: use a separate normal link for keyboard and touch access in addition to node double click.
The desktop and 390 px mobile checks confirmed the age gate, result actions, dialogs, product cards, story rotation, and map controls.

## Matcher group endpoint integration, 2026-09-28

The matcher now provides `POST /v1/group/match` on the same service that provides `POST /v1/eval/predict`.
The group response includes the shelf preview, detected bottle coordinates, segmentation masks, and ready best matches.
Decision: the browser calls same-origin `/v1/group/match` through the Nuxt server.
Decision: derive the upstream group URL from the existing `NUXT_PREDICTION_ENDPOINT` origin and path prefix.
Decision: do not add `NUXT_GROUP_MATCH_ENDPOINT`.
This keeps one matcher configuration and prevents the browser from receiving a private service address.
The matcher performs all bottle matching during the group request.
Bottle selection is now local UI state and does not start another prediction request.
The matcher can archive the original group photo.
The Web UI does not claim that the photo is never stored.

## Princess deployment and shelf suspension, 2026-09-28

Princess has 1 vCPU, 1.9 GiB RAM, and a 25 GB disk.
The live check showed approximately 1.7 GiB available RAM and 23 GB available disk space.
Caddy used approximately 46 MiB RSS during the check.
The Nuxt production output used approximately 22 MB on the build host.
Decision: Princess can run Caddy and the Nuxt portal for demo and moderate traffic.
Decision: keep matcher and SAM3 computation on GX10.
The existing Princess loopback tunnel provides the compatible `/v1/eval/predict` route on port 28000.
Its current pipeline is `official-eval-mock`.
The existing public Caddy API also owns `/v1/eval/predict` and requires a bearer token.
Decision: keep that route unchanged and send browser photo requests to the equivalent portal `/api/predict` route.
The owner selected a selectable temporary-unavailable view for «Вся полка».
The Princess deployment does not set `SAM3_ENDPOINT`.
The server rejects the disabled shelf route before it reads an upload.

## Shelf mode, 2026-09-15

The user requested segmented shelf photos and a popup for each selected bottle.
The existing GX10 SAM3 gateway accepts multipart `image` and `text=wine bottle`.
Use canonical `SAM3_ENDPOINT`. Keep all service requests behind our portal API.
The first live request used the public Wikimedia shelf example documented in `docs/assets.md`.
The source JPEG hash matched the public download. No private user photo was used.
The request returned 96 masks at 1280 × 853 in 68.162 seconds after model loading.
The service returned binary full-frame masks. Eleven detector boxes extended slightly outside the photo.
Some masks had disconnected fragments outside the detector box.
Decision: clamp detector boxes and exclude mask fragments outside each box.
Return cropped overlays to avoid one full-frame browser texture per detected bottle.
Recognize only a selected crop. A dense shelf must not trigger 96 prediction requests.
The native popup reuses the existing wine result and food recommendation flow.

Independent code review identified malformed crop parsing and missing server-side prediction cancellation.
Added strict data URL validation and propagated client disconnects to the prediction provider.
The focused tests cover these corrections and retain the existing evaluator contract.
Physical camera, touch, and full visual checks remain separate device verification work.

The first production request encountered a transport reset while the gateway loaded SAM3.
The gateway recorded an empty 502 after 58.311 seconds. No SAM3 validation error was recorded.
The same normalized public photo passed after loading. It returned 94 masks through the portal.
Added one retry for known transient socket and transport timeout codes within the original time budget.
Permanent address errors, malformed output, and cancellation do not trigger this retry.
Tests cover these branches. A new cold-start failure was not forced on the shared service.
The final browser flow returned 94 selectable bottles, a source-linked demo wine, and three live foods at public test store 5020.
All new browser tools rejected invalid input. Reset cleared the shelf and popup.
The existing evaluator accepted all three requests after the shelf changes.

## Demo service boundary, 2026-09-15

The user clarified that the Web UI must query our portal and our service must provide the response.
The current code already follows this boundary.
`useFoodRecommendations` calls relative `/api/food/stores` and `/api/food/pairings` routes.
The server handlers call the Globus adapter and return normalized data.
The browser has no direct retailer data API call.
Product images and user-selected retailer links remain separate media and navigation requests.
Decision: preserve the implementation and make the boundary explicit in the specification.
No separate service endpoint was supplied or connected in this clarification.

## 2026-09-15

- Read the official evaluator script and its README.
- Confirmed `POST`, multipart field `image`, and response field `slug`.
- Confirmed the evaluator timeout and HTTP status rules.
- Inspected the supplied public catalog in the browser.
- Recorded source colors, typeface, layout, navigation, and bottle assets.
- Selected Nuxt for one local UI and API server.
- Selected a fixed mock prediction to avoid implying image recognition.
- The task document recommends Strapi for the catalog. The user permits a mock implementation.
- Eight demo slugs occur in the official CSV. Four newer slugs use public portal metadata.
- The portal reports `108%` alcohol for `muskat-ottonel-gusev`. The demo record omits this invalid value.
- Nuxt 4.5.2 requires Vue Router 5.2.0. The project uses the matching version.
- Relative shared imports failed in the Nuxt production server output. The documented `#shared` alias resolves the production imports.
- The official evaluator accepted all three production mock responses.
- WebMCP checks confirmed search state changes, invalid input rejection, and scanner dialog opening.
- Full visual regression, physical camera behavior, and a real recognition service remain untested.
- Aligned the Node engine range with the installed Nuxt 4.5.2 package metadata.
- The first GitLab CI job failed during the Docker Hub image download. One retry was started.

## Photo search scope correction, 2026-09-15

The user requires a dedicated photo search page with the source visual identity.
The user does not want a duplicate catalog UX.
Decision: replace the catalog page with one responsive scanner workspace.
A modal-first alternative adds an unnecessary opening action. A catalog-first alternative conflicts with the corrected request.
Keep the prediction API and metadata fixture. Remove the catalog UI and local detail navigation.
A valid prediction must survive metadata fetch errors. The old scanner assigned the slug too late.

The scanner state checks confirm that metadata 404, 500, invalid JSON, wrong slug, network failure, and timeout retain the valid prediction link.
The production browser example completed through the same automatic upload path as the UI.
The updated production evaluator check passed for all three official photos.

## Food source selection, 2026-09-15

The user selected a retailer with an accessible API instead of demo products.
The sibling `retail-query/docs/store-search-capabilities.md` already documents Globus, METRO, and Lenta.
Globus has a confirmed coordinate directory and guest product search.
METRO directory access remains unverified. Lenta requires a specific network access profile in that report.
Decision: use Globus directly. No proxy, login, or API key is needed for the verified guest flow.
A new live probe returned HTTP 200 for the directory, store 5020 context, three searches, and one product detail.
The directory contained 22 records at the test time.
The queries were `филе индейки`, `моцарелла`, and `хумус`.
`docs/validation/globus-access.json` records the sanitized observation.
The source fields show that `quantity` is basket state and `quantity_max` is available quantity.
Some prices require the loyalty card. The UI preserves the returned promotion conditions.
Product links come from `data.product.share_text`. Do not construct a speculative path.
No user location was obtained. Verification uses public store coordinates or an explicit public store ID.

The integration uses an application API, not a public developer contract.
The directory limits geographic coverage. Straight-line distance does not represent travel time or delivery eligibility.
The pairing rules use source labels first and editorial defaults second.
The product search samples up to eight candidates per idea. It does not prove full catalog coverage.
An independent code review found an incorrect fixed wine-color reason and overly broad preparation matching.
Removed the fixed color assertion. Excluded salted fish and pickled mushrooms from baking ideas.
Try a second candidate when the first detail record becomes unavailable or fails validation.
