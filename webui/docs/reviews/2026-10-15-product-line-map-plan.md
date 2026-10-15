# Plan Review: Abrau-Durso Product Line Map

## Verdict: Changes required before implementation

The plan handles data honestly. It uses a dated snapshot and claims no live prices. It forbids AI-made labels. It keeps variants distinct, defines unplaced and unsupported states, and separates the selected product from the recognized one.

However, six decisions are still open. Each one changes the JSON file, the component, and the tests. Resolve the P0 items in the specification first. Two tasks can start now: asset extraction and the sheet crosswalk.

I reviewed only this text. Confirm the file paths, the scanner contract, and existing dependencies against 20a9903.

## P0: Blockers

**1. Choose the layout. I recommend B.**

| | A: 14 group nodes that expand | B: all products in group panels |
|---|---|---|
| Coverage of the six sheets | Hidden until groups open | Visible on open |
| Recognized wine in context | Only its group opens | Whole lineup visible |
| Pan and zoom stability | Expanding reflows the canvas | Layout stays static |
| Groups that span tiers | Group must sit in one band | Each product sits in its own band |
| Mobile | Cleaner overview, more taps | Denser; needs Fit and two-way pan |
| Build and test cost | Expand state and placement logic | Lower |

- B matches "as comprehensive as six sheets." It also needs no graph engine.
- At Fit zoom, B gives the same overview as A.
- Put each group's thumbnail and product count in its panel header.
- If the user picks A, add these:
  - an "Expand all" control;
  - several groups open at once;
  - scroll anchored to the tapped group;
  - the recognized group kept open;
  - tests that combine expand, collapse, and Locate.

**2. Freeze the lineup schema before data entry.**
- Define these fields:
  - `schema_version`
  - `producer {id, names, verified_aliases}`
  - `snapshot {date, sources}`
  - `tiers [{id, rank, label, meaning}]`
  - `groups [{id, name, cover_product_id}]`
  - `products [{id, wine_slug|null, tier_id, format_ml, package, kosher, image|null, info, sources[]}]`
  - `edges [{from, to, type}]`, with types limited to `contains` and `variant_of`
  - `slug_aliases {alias: canonical}`
- Store group membership once, as `contains` edges.
- Give each product exactly one parent group.
- Link cross-group variants, such as kosher bottles, with `variant_of`.
- Derive counts and the gray state. Do not store them.
- Keep one node per slug. Each magnum, kosher, or gift variant gets its own verified slug or null.

**3. Model price and positioning separately.**
- The user asked for both. The plan offers one "editorial tier."
- The two diverge for magnums, gift boxes, and kosher bottles.
- Write a tier rubric.
- If the sheets show prices, treat them as dated evidence:
  - normalize them to 0.75 L;
  - place gift packages with their base wine;
  - decide explicitly whether to show the numbers.
- Show relative price as a rank within the producer, not as a currency amount.
- Give each group a one-line rationale, and one for each exception.
- Add a legend with:
  - the direction of the axis;
  - what each band means;
  - the snapshot date;
  - the note "not live prices."
- In the details panel, compare each product with the recognized wine, for example "one band above your wine."

**4. Specify the recognition contract.**
- Name the fields the map receives: wine slug, producer ID or name, and display name.
- An exact slug or alias match wins.
- Use the producer field only to separate "unplaced Abrau" from "unsupported." Without it, the two cases look the same.
- Match producers through verified aliases: "Абрау-Дюрсо", "Abrau-Durso", "Abrau Durso".
- Add a registry that maps a producer ID to a lazy JSON import.
- Write a pure `resolveRecognition()` function that returns one of: `placed`, `alias`, `unplaced`, `unsupported`, `none`. Unit-test every branch.

**5. Pick one navigation model.**
- The plan mixes four surfaces: a side panel, a bottom sheet, a native modal, and a card that "returns to the map."
- Keep the map mounted at all times.
- Show details in a non-modal side panel on desktop and a bottom sheet on mobile.
- Escape and Back close the details first, then the map. Neither may drop the scan result.
- Decide how the portal link behaves. Choose one:
  - a new tab with `rel="noopener"`; or
  - the same tab, restoring product, zoom, and scroll from history and `sessionStorage`.
- If the scan result persists across navigation, use one route for both flows. Real browser history then handles Back and the portal return.
- Keep the "recognized" flag in memory, so a URL never claims recognition.
- If the modal stays, close its layers on `popstate`.

**6. Add the requested implementation review.**
- The plan omits it.
- After QA and before the final commit, run an Opus 5.5 max-effort review. Give it the diff, the test output, and screenshots.
- Fix or record every finding.

## P1: High

**7. Prove coverage, not just counts.**
- Commit a crosswalk that maps each sheet and label to a node ID.
- Document the deduplication rules behind the 52 nodes and the source of each group.
- Test that the crosswalk and the JSON match one to one.
- Record how each slug and alias was verified.
- Mark each null slug as either "verified absent" or "unchecked."

**8. Define the details content.**
- Fields:
  - name, group, style, sweetness, color;
  - format, package, kosher, vintage;
  - tier, relative price, portal status, source sheet.
- Take every value from the sheets.
- Hide empty fields.
- Generate no descriptions and no tasting notes.
- Keep product names as printed. Follow the app's locale.

**9. Specify mobile behavior.**
- Center the recognized product in the area above the bottom sheet.
- Open the sheet in a peek state.
- Use `100dvh`, `overscroll-behavior: contain`, and a background scroll lock. The page behind a modal dialog still scrolls.
- Never set `user-scalable=no`.
- Decide how pinch works: page zoom plus buttons, or canvas-only pinch through `touch-action`. Test the choice on iOS Safari.
- Limit minimum zoom so tap targets stay at least 24 px. 44 px is better.

**10. Harden pan and zoom.**
- Lay out the canvas at a fixed width per breakpoint, independent of zoom. Otherwise the panels re-wrap as the user zooms.
- Anchor zoom on the visible center.
- Reserve image dimensions. Center only after layout completes, using `requestAnimationFrame`.
- Set `scrollLeft` and `scrollTop` on the canvas itself. `scrollIntoView` also scrolls the parent containers.
- Subtract the side panel's width when centering.
- Add mouse drag-to-pan, with a small movement threshold so clicks still register. A standard mouse wheel cannot scroll sideways without Shift.
- Add a Fit button.
- Keep band labels sticky during horizontal pan.

**11. Make the map accessible.**
- Render each node as a button, in a logical DOM order: band, then group, then product.
- Mark the recognized, selected, and gray states with text or icons, not color alone.
- Test a node that is both selected and gray.
- Meet 4.5:1 contrast for text and 3:1 for other UI, in both themes.
- Move focus into the details panel when it opens. Return focus to the node when it closes.
- Announce the preselected wine through a polite live region.
- Respect `prefers-reduced-motion`.

**12. Split validation into build-time and runtime checks.**
- Run the full checks in tests and the build:
  - unique IDs and slugs, and slug format;
  - alias-to-canonical collisions and alias chains;
  - dangling references and cover references;
  - missing and orphan assets;
  - crosswalk parity.
- A browser cannot check whether asset files exist.
- Ship only a light runtime guard that checks version and shape. On failure, show the unavailable state.
- Add no client-side validation library unless the repo already has one.

## P2: Medium

**13. Draw fewer edges.**
- Panels already show which group a product belongs to.
- Draw variant edges only for the selected node. Alternatively, list them as "Also available as" links that select and center the related product.
- If you keep the SVG lines, recompute them on zoom and resize. Correct every measurement for the zoom factor.

**14. Tighten assets.**
- Use a neutral bottle silhouette for missing images. Never use a generated label.
- Normalize crop, height, and background. White JPEG backgrounds glare in dark mode.
- Write alt text for every image.
- Record each file's source, crop, and usage rights.
- Set a size budget, such as 30 KB or less per 2x WebP thumbnail.

**15. Avoid Nuxt pitfalls.**
- Measure the DOM only in `onMounted`.
- Switch between desktop and mobile layouts with CSS media queries, not render-time JavaScript. This prevents hydration mismatches.
- Style `<dialog>` and `::backdrop` for dark mode. Browser default colors follow `color-scheme`.
- Lazy-load the map and the JSON, so the scanner bundle stays small.
- Keep the types exported from `shared/experiences.ts` stable.
- Keep the portal base URL in config, not in each producer's JSON. Reuse any existing helper, and encode slugs.

**16. Generalize the QA route.**
- Build it as `/lineup/[producer]`, so a new JSON file needs no new page.
- An unknown producer shows the unavailable state.
- An unknown `wine` value selects nothing and shows a notice.
- Label the selection "linked," never "your wine."
- Add `noindex`, and keep the route out of every sitemap.

**17. Avoid dead ends.**
- For unsupported producers, hide or disable the lineup entry and state the reason.
- Keep the unavailable state for direct links.

**18. Close test gaps.**
- Add these tests:
  - table tests for all 32 slugs and 3 aliases;
  - failures for alias collisions and malformed slugs;
  - the portal round trip;
  - Android Back;
  - rotation keeps the same center;
  - reduced motion;
  - zero hydration and console errors;
  - zero Abrau nodes for unsupported producers;
  - no leftover demo code.
- Run a WebKit pass or test on a real iPhone. Chromium emulation does not reproduce WebKit's behavior for `dialog`, `dvh`, or nested scrolling.
- State which checks are automated and which are manual smoke cases.

## P3: Low

**19. Fix the copy.**
- Label gray nodes "No portal page." The word "Unavailable" reads as "out of stock."
- Show "Catalog of 20 Sep 2026" beside the legend.
- Drop the price field that is always null, or render nothing for it.

**20. Tighten operations.**
- Install from the lockfile. List any new dependency in the plan before adding it.
- Create the branch explicitly from 20a9903. Check how far `github/main` has moved before handoff.
- Serve the production build on `127.0.0.1:18553`.
- Check that the port is free first. Never stop a process you did not start. Record the URL and the PID.
- Keep build output out of the commit.
- Confirm that the documentation files live inside webui.

## Minimum acceptance criteria

- [ ] `abrau-durso.json` lives in its own file and loads through the registry.
- [ ] The file validates as a graph with:
  - 14 groups and 52 products;
  - 32 unique canonical slugs, 3 aliases, and 20 null slugs;
  - valid `contains` and `variant_of` edges.
- [ ] The crosswalk maps every sheet entry to exactly one node.
- [ ] Every image is a real crop or the neutral placeholder.
- [ ] Each of the 32 slugs and 3 aliases opens the map with the correct product:
  - selected and centered;
  - marked "your wine";
  - with its details shown (peek state on mobile).
- [ ] A wine not listed in the snapshot shows an unplaced card, with a portal link and no tier.
- [ ] An unsupported or missing producer shows the unavailable state and renders zero Abrau nodes.
- [ ] Null-slug nodes appear gray with a text label.
- [ ] Every node opens its details by tap, click, Enter, or Space.
- [ ] Null-slug details show no portal link and explain why.
- [ ] The legend and details explain the band, relative price, snapshot date, and "not live prices."
- [ ] Variants explain how their format or package differs.
- [ ] Close, Escape, and Back restore the same zoom, scroll position, and selection.
- [ ] Focus returns to the node, and the scan result survives.
- [ ] Following the portal link and coming back restores the same map state.
- [ ] Zoom stays anchored.
- [ ] Pan works by touch, trackpad, mouse wheel, mouse drag, and keyboard.
- [ ] Locate recenters the recognized wine, or focuses the unplaced card.
- [ ] QA passes at 360×740, 390×844, 768×1024, and 1440×900, in both system themes, on WebKit and Chromium, with:
  - no page-level horizontal scroll;
  - no hydration or console errors;
  - tap targets of at least 24 px at minimum zoom.
- [ ] The QA route is `noindex` and never labels a linked wine "recognized."
- [ ] The scanner flow and the other experiences pass regression smoke tests.
- [ ] No demo code remains.
- [ ] Typecheck, build, and tests pass.
- [ ] The Opus 5.5 implementation review is complete, and its findings are closed.
- [ ] The commit is on `product-line-map`, branched from 20a9903.
- [ ] The server answers on port 18553.
