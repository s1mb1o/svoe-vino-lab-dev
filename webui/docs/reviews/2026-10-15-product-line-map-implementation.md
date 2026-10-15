# Final Review: Producer Product-Line Map

## Verdict: Changes required

The settled design is implemented faithfully in these areas:
- The data model and `group_id`-derived edges match the settled design.
- Exact identity correctly takes priority over producer metadata, and aliases resolve.
- The counts are correct: 14 groups, 52 products, 32 canonical slugs, 3 aliases, 20 null slugs. The crosswalk maps 54 sheet entries to 52 products across 6 sheets.
- Portal links appear only for products with a slug, and they use `noopener noreferrer`.
- The unplaced card shows no tier, and unsupported producers get a clear unavailable state.
- The preview route is noindex and never claims recognition.
- Return preserves canvas state, and Escape restores the opener.

Three concrete accessibility defects and two mobile defects still need focused fixes. None of the fixes reopens a settled decision.

Final verification is also still pending: the 176-test run, the final build, and the production-build browser rerun. That is a verification gap, not a code defect.

## Findings

**1. Medium: gray tiles fail WCAG AA text contrast in the light theme**
- **Where:** `ProductLineMap.vue:314`, `:382`, `:384`
- **Problem:** `--plm-muted-ink` (#726f6b) on `--plm-muted-bg` (#eae7e2) computes to about 4.05:1.
  - The product name (12px/600) and "Нет в каталоге" (8px) need 4.5:1.
  - These are active, selectable buttons, so the inactive-component exemption does not apply.
  - All 20 null-slug tiles are affected. The dark values at `:418` compute to about 5.7:1 and pass.
- **Repro:** Use the light theme. Open `/lineup/abrau-durso`, expand Victor Dravigny, and measure the text on the Zero Dosage tile.
- **Fix:** Set `--plm-muted-ink: #615e5a`, which gives about 5.2:1. Also check `.plm-product-style` (`var(--muted)`) against #eae7e2. That token is not in the snapshot.

**2. Medium: keyboard focus is lost when the activated control unmounts**
- **Where:** `ProductLineMap.vue:276` (preview "Открыть коллекцию …", rendered only while collapsed) and `:306` ("Показать карточку", inside the `v-else-if` branch)
- **Problem:** `toggleGroup` (`:107–115`) and `showDetails = true` each remove the button that has focus.
- **Repro:** Tab to "Открыть коллекцию Империал" and press Enter. `document.activeElement` becomes `body`.
  - The same happens after Return when you press Enter on "Показать карточку".
- **Fix:**
  - After a toggle started from the preview, call `mapElement(group.id,'group')?.focus({ preventScroll: true })`.
  - Add a `reopenDetails()` that sets `showDetails`, awaits `nextTick`, and focuses `detailHeading`, mirroring `selectProduct`.
  - Optionally give the preview `tabindex="-1"` to remove the duplicate tab stop.
  - Add `activeElement` assertions to the browser suite.

**3. Medium: the group picker moves focus on every `change`**
- **Where:** `ProductLineMap.vue:256` (`@change="jumpToGroup"`) and `:134`
- **Problem:** On Windows and Linux Chrome and Edge (and typically Firefox), ArrowDown on a focused, closed `<select>` commits the next option and fires `change` immediately.
  - `jumpToGroup` then moves focus to the group toggle, so users cannot arrow through the options.
  - Each attempt also expands another group. This fails WCAG 3.2.2 (On Input).
  - Playwright's `selectOption` does not exercise this path.
- **Repro:** In Windows Chrome, Tab to "Перейти к коллекции" and press ArrowDown. Focus leaves the select after one key press.
- **Fix:** Keep the expand and scroll on `change`, but remove the `.focus()` at `:134`. Move focus only on an explicit confirmation, such as `@keydown.enter` on the select or a "Перейти" button.

**4. Medium: "Уместить по ширине" cannot fit the canvas on phones or narrow tablets**
- **Where:** `ProductLineMap.vue:14`, `:122–127`, `:169`. The button stays visible on mobile (`:437`).
- **Problem:** The fit value is `clientWidth/1120`, but `changeZoom` clamps it to `MIN_ZOOM = 0.6`, so fitting needs a viewport of at least 672px.
  - At 390px the viewport is about 364px, so the fit of 0.32 is clamped to 60% and the canvas stays 672px wide.
  - Widths of 768–1000px with the side card (about 430–560px of map) behave the same way.
- **Repro:** At 390×844 on `/lineup/abrau-durso`, tap the button. Zoom reads 60% and `viewport.scrollWidth > clientWidth`.
- **Fix:**
  - Use `minZoom = Math.min(0.6, Math.max(0.25, fit))` for both the clamp and the "−" disabled state.
  - Alternatively, reflow to fewer group columns below 768px.
  - Assert `scrollWidth <= clientWidth + 1` after Fit at 390px.

**5. Medium (probable, layout-dependent): on mobile, selection and Return do not reveal the relevant region**
- **Where:** `ProductLineMap.vue:143` and `:181` (`preventScroll: true`), `:439–441`, `:340` (`overscroll-behavior: contain`)
- **Problem:** With the dialog scrolled to the top, the header, intro, toolbar, help row, 43dvh viewport, and multi-line disclaimer push the in-flow card to the fold at 390×844.
  - By my estimate from the component CSS, the card is fully below the fold at 320×740.
  - The suite itself scrolls the dialog to the bottom before capturing the gray card (script `:273`).
  - Tapping a product updates an off-screen card and focuses an off-screen heading without scrolling.
  - Return can leave the map off-screen.
  - Swipes on the canvas never chain to the dialog because of `contain`.
- **Repro:** In the 320×740 scanner dialog, tap another product. Compare the `[data-product-detail]` rectangle with the dialog's `clientHeight`.
- **Fix (keeps the in-flow card and canvas state):** Under `(max-width: 767px)`:
  - After selection, call `detailEl.scrollIntoView({ block: 'nearest' })`.
  - After Return, call `viewport.scrollIntoView({ block: 'nearest' })`.
  - `scrollIntoView` scrolls ancestors only, so the viewport's own offsets and zoom stay unchanged. The existing `canvasState` assertion still holds.

**6. Low: "Открыть все / Свернуть все" anchors on a stale group**
- **Where:** `ProductLineMap.vue:116–121`
- **Problem:** The anchor is `navigationGroup`, falling back to the first group. That value changes only on picker, toggle, or selection (`:113`, `:131`, `:141`, `:150`, `:226`), never on panning.
- **Repro:** In the overview, pan to the formats tier and press "Открыть все".
  - The anchor is Cuvée Alexander II. Everything above the formats tier grows, so Fizz and Light leave the view.
  - Selecting a Victor Dravigny product and then panning produces the same jump.
- **Fix:** Anchor on the topmost `[data-group-container]` that intersects the viewport rectangle. Fall back to `navigationGroup`.

**7. Low: `SMOKE_TESTS.md` still prescribes the removed six-node demo**
- **Where:** `SMOKE_TESTS.md`
  - "Result experience checks" still lists the six nodes, the patched Удельное Ведомство image, `ЛИНЕЙКА ВАШЕГО ПРОИЗВОДИТЕЛЯ`, `ПРИМЕР · ДЕМО` for other producers, and the "one current map item" test.
  - "Ideas beyond recognition" still describes an Abrau demonstration for other producers.
- **Problem:** These contradict `WineExperiences.vue:26` and `:91–96`, and the new "Producer product-line map" section. Manual reviewers following them will log false failures.
- **Fix:** Delete these bullets or point them to the new section.

## Non-blocking notes (optional)

- **Unsupported-state link (uncertain):** `WineExperiences.vue:95` navigates in the same tab. If scanner state is component-local, the scan result is lost. A new tab would match the portal-link rationale.
- **Copy:**
  - The component uses «Свое Вино» (`:247`, `:250`, `:278`, `:300`, `:304`); the rest of the app uses «Своё Вино».
  - "ВЫБРАНО НА КАРТЕ" (`:293`) appears for an unplaced wine in non-recognized contexts, although that wine is not on the map.
  - The badges duplicate "Архивный выпуск"/"Архив" and the limited-release labels (`:297`).
- **Readability:** Labels of 7–9px (`:316`, `:350`, `:380–381`) render at about 4–5px at 60% zoom.
- **Dead code:** `.plm-keyboard-help` (`:420`), `.plm-details-collapsed` (`:253`, no rule), and the legacy `.line-viewport` and `.line-paths` rules in `main.css`.
- **Disabled zoom buttons (browser-dependent):** The zoom buttons become `disabled` while focused at the limits, which may drop focus. Using `aria-disabled` with a guard avoids this.
- **Tests:**
  - Script `:118` asserts `detail.y > frame.y`, which does not prove the card is below the map. Use `>= frame.bottom`.
  - Unit test `:37` checks for uppercase 'КОШЕРНОЕ' on a product with no badges, while the data uses 'Кошерное', so the check is vacuous.
  - Add cases for preview and reopen focus, picker arrow keys, and Fit at 390px.

## Response to the earlier review

- **Implemented:** Zoom anchors to the viewport center, and single-group toggles keep their toggle fixed. The alias tests, the crosswalk test, and the CSS body scroll lock are present.
- **Weak:** Open-all anchoring is weak (#6), and Fit does not work on mobile (#4).
- **Pending:** Mobile verification depends on the production-build browser rerun.

## Verification limits

- I did not run tests, the typecheck, builds, or browsers, and I did not review screenshot pixels.
- The `PhotoScanner.vue` script was not supplied, so I cannot confirm that `mock` is the mock-mode boolean behind `:recognized="!mock"`. The browser suite covers upstream mode only.
- Product descriptions and the global CSS tokens were not supplied. The contrast check covers only the hard-coded colors, and the data checks rely on the structural summary.
- The layout estimates in #5 come from the component CSS only.
