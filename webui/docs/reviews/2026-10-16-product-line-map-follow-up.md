**Verdict: Approved with non-blocking notes.**

This is a static review of the supplied deltas only. I ran no tests and inspected no screenshots. I computed the contrast ratios from the hex values.

### Original findings

1. **Contrast: resolved.**
   - `#615e5a` on `#eae7e2` is about 5.2:1 (previously about 4.05:1).
   - The style line now uses the same token (`ProductLineMap.vue` 405).
   - The dark pair is about 5.7:1.
   - The local `--muted` override (336) only darkens text. The dark override still wins on specificity.
2. **Unmounted focus: resolved.**
   - The preview path focuses the persistent `[data-group-id]` toggle after `restoreAnchor` (116, 298).
   - `reopenDetails` focuses the heading after `nextTick` (160–165, 328).
   - New browser assertions cover both paths.
3. **Picker focus: resolved.** The post-centering `focus()` call is removed. Nothing else visible in that path moves focus, and the new assertions check retention.
4. **"Обзор": resolved per the accepted scope (286).** The accessible name "Обзор карты" contains the visible label. The title states the readable scale.
5. **Mobile reveal: resolved in code (145–149, 158, 164, 201).**
   - `scrollIntoView` targets either the aside, which is a sibling of the viewport, or the viewport element itself. Only ancestors scroll, so canvas offsets and zoom are untouched.
   - Return focus keeps `preventScroll`.
   - Only the selection half has a browser assertion (note 2).
6. **Expand-all anchor: resolved for the reported stale case (118–127).** An edge case remains (note 1).
7. **Smoke instructions: resolved.** The six-node and demo steps are replaced (`SMOKE_TESTS.md` 36, 259, 263).

### Other deltas: no regressions found

- **Short screens:** The mobile and `max-height: 600px` overrides remove internal clipping. At 768 px and wider, the checks correctly require only non-clipping, which matches whole-dialog scrolling.
- **Header:** The page breakpoint now matches the map at 767 px. `width: auto` keeps the action at its intrinsic width.
- **ShelfScanner:** The default pre-flush watcher runs after `openBottle` sets `pendingOpener`. `isConnected` guards the fallback. Keyboard activation still yields the button as `currentTarget`. If selection is refused, behavior falls back to the previous logic.
- **Unsupported producer:** The preview link uses `_blank` with `rel`, so the scanner tab keeps its state.
- **Kosher test:** It now matches the real badge casing, so the negative assertion is no longer vacuous.
- **Mock provenance:** The claim matches the composable excerpt (header or requested mode).

### Non-blocking findings

1. **Expand-all can anchor to a sliver (`ProductLineMap.vue` 118–124, used at 127).**
   - `visibleGroupId()` takes the topmost group that intersects the frame by any amount.
   - If the frame's top edge cuts through a group in the row above, that group wins even though its header is off-screen.
   - Expanding that row then pushes the group the user was viewing down by the row's growth. This is the original symptom at a smaller scale.
   - **Fix:** prefer the group with the largest visible intersection, or the group containing the frame center. Keep the current fallbacks.
   - **Test gap:** the browser script (279–288) recomputes the same rule, so it cannot catch this. Scroll so that only 20–40 px of a previous-tier group shows above `fizz`. Then assert that `fizz`'s header stays fixed after "Открыть все".

2. **The Return half of finding 5 has no assertion.**
   - Lines 119–123 check detail visibility after selection.
   - Nothing checks that Return (201) brings the viewport on-screen without changing `scrollLeft`, `scrollTop`, or zoom. The disposition says browser checks cover this.
   - **Fix:** at 667×375, where the map and card together exceed the screen, record those three values and activate Return. Assert that the viewport is on-screen and the values are unchanged.

3. **Boundary coverage is narrower than claimed.**
   - The boundary loop (script 455) uses only 700 and 701. Both page and map now break at 767 px, so that pair no longer straddles the changed breakpoint.
   - `SMOKE_TESTS.md` 309 and the disposition both cite 767 and 768.
   - Line 315 also records WebKit landscape and breakpoint passes that the reported WebKit evidence doesn't include. That evidence lists 390 px light, 320 px dark, and nested dialogs.
   - **Fix:** add `[767, 740]` and `[768, 740]` to the loop. Write the dated record from the final rerun output.

4. **The picker keystroke step is platform-dependent (script 225–232).**
   - On macOS builds of Blink and WebKit, ArrowDown on a closed `<select>` opens the popup instead of changing the value.
   - Line 230 may therefore fail on a macOS host, or skip the per-change focus path it is meant to exercise.
   - **Fix:** assert focus after repeated `selectOption` calls, which is portable. Alternatively, gate the keystroke step by platform.

5. **Optional: short landscape at 768 px and wider.**
   - The new `max-height: 600px` mode also relies on outer scrolling, but `revealOnMobile` (146) matches width only.
   - At 844×390, selection focuses the heading with `preventScroll` and never reveals it. If the panel isn't sticky at that size, the focused heading can sit off-screen.
   - **Fix, if you want parity:** reveal the heading itself when `(max-height: 600px)` matches. Revealing the taller panel with `nearest` would align its bottom edge instead, leaving the heading out of view.
