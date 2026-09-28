# Research log

## Princess deployment and shelf suspension, 2026-09-28

Princess has 1 vCPU, 1.9 GiB RAM, and a 25 GB disk.
The live check showed approximately 1.7 GiB available RAM and 23 GB available disk space.
Caddy used approximately 46 MiB RSS during the check.
The Nuxt production output used approximately 22 MB on the build host.
Decision: Princess can run Caddy and the Nuxt portal for demo and moderate traffic.
Decision: keep matcher and SAM3 computation on GX10.
The existing Princess loopback tunnel provides the compatible `/v1/eval/predict` route on port 28000.
Its current pipeline is `official-eval-mock`.
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
