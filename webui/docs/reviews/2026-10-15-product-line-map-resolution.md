# Product-line map review resolution

Date: 2026-10-15.
Base: `20a9903eb81d08af334079fca8281da10e359da5`.
Reviewer: Claude Opus 5.5. Canonical model: `claude-opus-5-5`. Effort: `max`.
The owner explicitly requested external plan and implementation review.
The review used Claude Code safe mode with tools disabled.
The review prompt contained task source and code. The prompt contained no credentials.
The implementation review used a frozen source snapshot. Later changes require a separate delta record.

## Plan findings

Read [the original plan review](2026-10-15-product-line-map-plan.md).
The reviewer returned `Changes required before implementation`.
The final specification resolves the open design decisions as follows.

| Finding | Resolution |
| --- | --- |
| Choose grouped or flat layout. | The owner selected the grouped canvas. The map supports several expanded groups, an expand-all control, a group selector, and scroll anchoring. |
| Freeze the graph schema. | `group_id` stores the only product containment relation. The renderer derives edges. Each package has a stable product ID. The validator checks references and ambiguous slugs. |
| Separate price from premium rank. | All numeric prices are null. The source sheets contain no numeric prices. Dated editorial bands describe relative positioning. Cans and drinks use a neutral section. Package differences remain explicit. |
| Specify recognition resolution. | The pure resolver returns `none`, `unsupported`, `unplaced`, `placed`, or `alias`. Exact identity takes priority over producer metadata. Tests cover all 32 canonical slugs and 3 aliases. |
| Define navigation. | The map stays mounted while the internal details panel changes. Return preserves selection, scale, and canvas position. Native Escape closes the map dialog and restores its opener. Portal links open in a separate tab. No synthetic browser-history entries are added. |
| Define coverage evidence. | The source crosswalk maps all 54 sheet entries to 52 unique products. Local assets and source references are checked. The two repeated Fizz packages have one node each. |
| Make mobile controls accessible. | Native touch pan, viewport arrow keys, zoom controls, group navigation, and focus restoration are implemented. Mobile selection reveals its detail panel. Return reveals the canvas. |
| Provide a review route. | `/lineup/[producer]` uses the same registry and component. Unknown producers and unknown slugs have explicit states. The route has noindex metadata and headers. |

A separate `variant_of` edge is unnecessary for this scope.
The product group and distinct package label express the required relation.
The single small producer file uses a static import. Additional producers must be registered explicitly.
The current map does not claim a numerical price comparison between two products.

## Browser findings

The first browser pass found an incorrect dark-theme selector. The selector was corrected.
The first mobile pass found a detail panel that covered part of the canvas. The panel now occupies normal page flow.
The mobile native dialog retained the browser default maximum width. The map dialog now sets an explicit mobile maximum width.
The map now centers a product only after its dialog is visible.
Group expansion preserves the group header position.
The overview control no longer promises to fit all content at an unreadable scale.
Short viewports use uncapped detail panels. The enclosing page or dialog provides scrolling.
WebKit does not always focus a button after a pointer click.
The shelf dialog now records `event.currentTarget` for focus restoration.

## Validation method

Unit tests cover graph identity, aliases, membership, source references, assets, and missing links.
The browser suite uses local prediction and catalog fixtures for deterministic scanner and shelf flows.
The suite does not measure recognition accuracy or upload a photo to the GPU service.
The running review server uses the existing upstream matcher configuration.
The standalone map preview requires no matcher request.
Browser screenshots are local artifacts in the ignored `reports/product-line-map/` directory.

## Verified checks

- All 176 unit tests passed in 15 files.
- `npm run typecheck` passed.
- `npm run build` passed.
- Chromium passed at 1440, 390, and 320 px in light and dark themes.
- Chromium checked mouse pan, native touch pan, arrow keys, and zoom.
- Both browser engines passed at 844 by 390 and 667 by 375 px.
- Both browser engines passed the 700, 701, 767, and 768 px boundary checks.
- WebKit 26.5 passed at 390 px in light mode and 320 px in dark mode.
- WebKit passed nested map and shelf dialog focus restoration.
- The source crosswalk covers every sheet entry. All 52 image responses succeeded.
- Scanner fixtures passed exact selection, alias selection, reset, unknown products, and unsupported producers.
- Gray products had usable details and no portal link.
- Portal links used the canonical verified slug. Return retained canvas state.
- Browser runs reported no script errors or hydration warnings.

The 701 px WebKit check exposed a full-width scanner link inside a horizontal page heading.
The standalone page now uses the same 767 px header breakpoint as the map.
The scanner link has an explicit automatic width.
The final 701, 767, and 768 px checks passed in both browser engines.

## Implementation review findings

Read [the original implementation review](2026-10-15-product-line-map-implementation.md).
The reviewer returned `Changes required` for the frozen source snapshot.
The review confirmed graph coverage, identity resolution, nullable links, and the noindex preview.
The following changes address its findings. Final delta review is recorded separately.

| Finding | Resolution |
| --- | --- |
| Gray product text has low contrast. | Darken the light gray text token. Use the same readable token for the product style. Keep the image gray and the product selectable. |
| Preview and reopen controls lose keyboard focus when removed. | Focus the stable group toggle after a preview expands. Reopen details through a function that focuses the detail heading. |
| The group picker loses focus on change. | Keep focus in the native select. Scroll and expansion do not move keyboard focus. |
| The fit label promises an impossible mobile fit. | Rename the control to `Обзор`. Keep the readable minimum scale and two-axis canvas navigation. The control no longer promises that all content fits. |
| Mobile selection and Return can leave content outside the screen. | Reveal details after a user selection. Reveal the viewport after Return. Preserve inner canvas position and scale. Browser checks cover these actions. |
| Expand-all can anchor a group outside the current view. | Prefer the topmost group that intersects the current viewport. Use the stored navigation group only as a fallback. |
| Old smoke checks still describe six demo nodes. | Replace those checks with the current graph checklist. Preserve dated historical validation records. |

The optional unsupported-producer link now opens the separate preview in a new tab.
The original scanner result remains in its page.
The kosher identity test now checks the exact canonical kosher node and its actual badge.
The mobile position check compares the detail panel with the viewport bottom.
The browser script supports Chromium and WebKit through one optional engine setting.

`PhotoScanner.vue` obtains `mock` from `useWineScanner`.
The composable sets this flag from `X-Prediction-Mode` or the requested mock mode.
Therefore `:recognized="!mock"` does not mark a mock result as a recognized bottle.
The original review did not include this composable excerpt. The final review receives the excerpt.

The final full Chromium and WebKit runs also passed the added review regressions.
These checks cover preview focus, reopened detail focus, picker focus, visible-group anchoring, and gray-text contrast.
The light gray text contrast is 5.23:1. The dark gray text contrast is 5.66:1.
Native select arrow keys and committed change events are tested separately.
Synthetic key sequences cannot reliably commit the macOS headless native menu.
The test keeps the native arrow-key focus assertion and sends two actual selection change events.
This test still detects the removed focus transfer in `jumpToGroup`.
Only the Chromium run uses a CDP touch-swipe command. WebKit runs the remaining shared suite.

## Final external verdict, 2026-10-16

Read [the follow-up review](2026-10-16-product-line-map-follow-up.md).
Claude Opus 5.5 with effort `max` returned `Approved with non-blocking notes`.
The reviewer confirmed that all seven original findings were resolved.
The reviewer checked source only. Browser verification was performed separately.
The native-select test correction was already applied after the review snapshot.
The 767 and 768 px cases had passed a separate browser probe. They are now also part of the shared suite.
The shared suite now asserts Return visibility and retained canvas state at 667 by 375 px.

A later local probe found a compact desktop issue with a long gift-box title at 800 by 650 px.
The bounded detail body had zero height. The Return button exceeded the clipped card by 4 px.
A small CSS patch removes the detail cap at compact desktop widths and heights.
The normal wide, tall desktop layout retains its bounded side panel.
This CSS patch follows the approved review snapshot. It is verified by a new browser regression.
No fourth external review was requested for this CSS patch.

Two optional notes remain design limitations.
Expand-all uses the topmost intersecting group, which can be a small visible part of the previous row.
Automatic detail reveal uses the mobile width breakpoint. Wide landscape layouts use ordinary outer scrolling.
Neither note prevents product selection, access to details, portal navigation, or Return.

## Final production verification, 2026-10-16

Both complete browser suites passed after the compact desktop CSS patch.
The shared suite now includes 767 and 768 px boundaries.
At 667 by 375 px, Return reveals the complete viewport and retains inner scroll, zoom, and selection.
The gift-box description and actions remain reachable at 800 by 650 and 1440 by 720 px.
These compact desktop cases pass in both standalone and scanner views.
Both browser engines report no script errors or hydration warnings.
All 176 unit tests and type checks passed. The final production build passed.
The local production server remains on loopback port 18553.
The source patch is limited to `webui`.
