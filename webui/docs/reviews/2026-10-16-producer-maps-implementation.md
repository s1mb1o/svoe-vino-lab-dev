# Producer expansion implementation review

Reviewer: Claude Opus 5.5, effort max.
Date: 2026-10-16.
Scope: Shared code, UI, test code, group metadata, official additions, and provenance notes.
The packet summarized linked product counts. It did not contain all linked product records.
The reviewer had no tool access.

# Producer-map expansion review (10 maps)

## Verdict

**Not done yet.** I found no crash-level defect in the supplied code. The resolver matches the stated design: exact and alias matches select a product, and name or prefix fallbacks return unplaced only. The validator also covers what the plan says it covers.

There are three Medium issues and several Low UX and tooling issues. The packet does not include the 562 linked nodes, so I cannot confirm their coverage from it.

**What checks out in the supplied data:**
- Every `source_ids` and `image.source_id` in tiers, groups and additions points to a declared source, in all 10 maps.
- Every tier has at least one group.
- Every addition image path passes the validator.
- There are no name, alias or prefix collisions between the 10 new maps.
- The plural labels are correct for the current counts.
- All prices shown are `null`.

## Confirmed defects

**1. Medium: navigation groups are shown as official "Коллекция", and their disclaimers disappear once the group is expanded.**
- **Code (`ProductLineMap.vue`):**
  - `.plm-group-description` only renders inside `<template v-if="!expandedGroups.has(group.id)">`.
  - The details panel shows `<dt>Коллекция</dt><dd>{{ selectedGroup.name }}</dd>` with no description.
  - The kicker, picker and toggles call every group a "коллекция".
- **Data:** vedernikov `pet-nat`, `sparkling`; koktebel `dessert`, `sparkling`; alma `locantita`; myskhako `mono`, `sparkling`; fanagoria `unassigned`.
- **Effect:**
  - The initial group is auto-expanded by the `watch` and by `centerInitial`.
  - A scanner user landing on Koktebel `dessert` sees "Коллекция: Десертные вина".
  - They never see "Совпадение с текущей официальной коллекцией не установлено".
  - The source notes say explicitly that these groups are not collection claims.
- **Fix:**
  - Add a validated `group.kind: 'collection' | 'navigation'` and label navigation groups "Группа на карте".
  - Render `selectedGroup.description` in the details panel, or keep it visible when a group is expanded.

**2. Medium: the snapshot provenance is never actually tested.**
- **Where:** `tests/product-line-registry.test.ts`, test "covers the saved catalog crosswalk".
- **What the test does:**
  - `source_sha256` is only checked against the pattern `/^[a-f0-9]{64}$/`.
  - `records.length === expected_count` compares two values from the same file.
  - Gray additions and the crosswalk image hashes cited in the notes are never checked.
- **Why it matters:** this contradicts "full snapshot SHA256" in the plan disposition.
- **Fix:**
  - Pin one expected snapshot SHA and assert every baseline equals it.
  - When a snapshot path is provided (for example via an environment variable), hash the file and recompute each producer's rows by the exact `producer` field.
  - Assert that every null-slug product has a crosswalk addition record.
  - Assert that the SHA-256 of each `public/` image equals its crosswalk hash.

**3. Medium: two Koktebel addition tiles show only the bottle size.**
- **Cause:** the tile renders `<strong>{{ product.variant || product.name }}</strong>`.
- **Data:** `official-geometry-pinot-gris.variant = "0,75 л"` and `official-planerskoe-traminer-magnum.variant = "1,5 л"`.
- **Effect:** the tiles read "0,75 л" and "1,5 л", with no grape or product name.
- **Fix:** either set `variant` to "" and put the volume in `name`, or render name plus variant on the tile. Also audit the linked products (not in the packet) for non-empty `variant`.

**4. Low: the gray tile text "Нет в каталоге" is misleading.**
- **Problem:**
  - Every gray node in these maps is an official producer product, so "not in catalog" reads as "not in the producer's range".
  - The visible text also differs from the accessible name, "Нет карточки на Свое Вино".
- **Fix:** use "Нет на «Свое Вино»".

**5. Low: Alma Valley has two tiers with the same rank.**
- **Problem:**
  - `varietal` and `everyday` are both `rank: 1`, so they render as two stacked bands.
  - The stable sort puts varietal above everyday.
  - Combined with "Премиальные коллекции — выше", this implies an ordering the data does not make.
- **Fix:** merge the two tiers, or give them distinct ranks with evidence. Add a validator that rejects duplicate non-zero ranks.

**6. Low: the `method` field is handled inconsistently.**
- **Canvas:** the canvas hides only the exact string `'Не указан в источнике'`. Inkerman `sparkling` and `winemaker-sparkling` use "Метод не указан в источнике", so it shows.
- **Details panel:** `v-if="selectedGroup?.method"` prints the placeholder itself ("Производство: Не указан в источнике") for dozens of groups.
- **Product accuracy:**
  - The group method is shown as a product fact even when it is wrong for that product.
  - Example: zolotaya `more-nebo` "Тихие вина и метод Шарма-Мартинотти" appears on the still red.
  - Several groups put a style label such as "Тихие вина" in the "Производство" slot.
- **Fix:**
  - Make `method` nullable.
  - Use one shared visibility check in both places.
  - Have the validator reject placeholder strings.

**7. Low: Abrau-specific copy appears in the empty state.**
- **Where:** `.plm-empty-selection` says "Форматы и напитки — отдельно."
- **When:** it appears on desktop at `/lineup/<id>` without `?wine`.
- **Why it's wrong:** for Inkerman the rank-0 tier is "Игристые коллекции"; for Massandra it is "Исторические и сладкие стили".
- **Fix:** derive the line from the rank-0 tier label, or use neutral copy.

**8. Low: the scanner fallback still links only to Abrau.**
- **Where:** `WineExperiences.vue` `.line-unavailable` links only to "Посмотреть карту Абрау-Дюрсо".
- **Fix:** list `PRODUCT_LINE_MAPS`, or link to an index page.

**9. Low: image errors before hydration show a broken image instead of the placeholder.**
- **Problem:**
  - Server-rendered `<img @error>` elements can fail before Vue attaches listeners during hydration.
  - This covers the eager detail image and the expanded and preview tiles.
  - The result is a broken image with no placeholder.
- **Fix:** in `onMounted`, mark any image with `complete && naturalWidth === 0` as failed.

**10. Low (accessibility): the producer select on `[producer].vue` navigates on `change`.**
- **Navigation:** `changeProducer` runs on `change`. On platforms where arrow keys change a closed select and fire `change` (for example Chromium on Windows), every arrow press navigates.
- **Accessible name:** `aria-label="Выбрать производителя"` overrides the visible label "Производитель", so the label is not contained in the name.
- **Fix:**
  - Add an explicit open button, or navigate on Enter.
  - Drop the `aria-label`, since the wrapping label already names the select.
  - Update the browser script's selector accordingly.

**11. Low (QA tooling): problems in `scripts/check-producer-maps-browser.mjs`.**
- **No report on failure:**
  - `results.json` is written after `assert.deepEqual(errors, [])`.
  - Any assertion inside the loop also aborts first.
  - Fix: write the report in `finally`, with a status field.
- **Always the same navigation target:**
  - `next` is always the first other file in `readdir` order (Abrau, if it lists first).
  - Navigation from one new map to another is never exercised.
- **Race after navigation:**
  - After `waitForURL`, the script reads `data-selected-product` once using `node:assert`.
  - That read can hit the outgoing page during the swap.
  - Fix: use `waitForFunction` or a polling check.
- **Weak mobile entry check:**
  - The mobile check "popup must stay closed on entry" can run before hydration swaps `aside` for `dialog`.
  - Fix: wait for `[data-product-dialog]` first.

## Optional recommendations

- **R1. Bundle size.**
  - All 11 maps are statically imported. Per the packet counts that is about 595 new nodes with full descriptions.
  - They load with `WineExperiences.vue` through `resolveProductLine`.
  - Consider an eager slim index (names, aliases, prefixes, slug→producer) plus a lazy import of the full map when the line dialog opens.
- **R2. Fallback misattribution.**
  - The notes show slugs such as `polusladkoe-krasnoe-zolotaya-balka` and `beloe-polusladkoe` that do not start with the declared `zolotaya-balka-` or `massandra-` prefixes.
  - Brand-word prefixes and aliases (`quintessence-`, `koktebel-`, `aristov-`, "Quintessence", "Высокий Берег") widen the fallback.
  - Meanwhile the unplaced panel asserts "Это вино производителя …".
  - Add a full-snapshot test: any row that resolves to a map must be `placed`, or have an allow-listed exact producer.
  - Remove prefixes that match none of the producer's own snapshot slugs.
- **R3. Image assets.**
  - Zolotaya, Alma, Inkerman and Massandra additions are converted to lossless WebP with no resizing. Zolotaya's sources are 800×800 JPEGs.
  - Fanagoria, Kuban and Myskhako resize to ≤480 px.
  - Images display at ≤120×176. Align on ≤480 px lossy WebP and check the file sizes.
- **R4. Content consistency.**
  - The badge "Подтверждено производителем" appears only on gray additions in fanagoria, kuban and myskhako. This implies the linked cards are unconfirmed.
  - Style format differs between maps: "Красное · сухое" versus "Красное сухое".
  - The ₽ price labels are used in only 4 maps.
  - Fanagoria `cru` and `surlie` say "премиальная коллекция" but sit below the tier labeled premium.
  - Fanagoria's `unassigned` group renders as "Коллекция: Коллекция не уточнена".
- **R5. Verify Locantita.** The Zolotaya notes record a "Locantita More" card from Скалистый берег in the full snapshot. The Alma notes do not reconcile this, yet the map presents `locantita` as an Alma Valley group.
- **R6. Vedernikov `core`.**
  - This group carries the official main-collection name and source.
  - The notes say it also holds "snapshot cards without a clear named series".
  - Split those cards into a neutral group, or soften the label.
- **R7. Validation hardening and small fixes.**
  - Reject empty tiers.
  - Decide a policy for `variant`.
  - Either assert `linked_count` and `largest_group` against the data or strip them.
  - Use `[...registeredProducerMaps].sort(...)` so the sort does not mutate the registry export.
  - Decline "КОЛЛЕКЦИЙ" properly; it is hardcoded and only correct for the current counts by chance.
  - Guard `normalizedProducer` against a nullish `Wine.producer`, if that can happen.
- **R8. Header wording.** "Серые позиции — без карточки на «Свое Вино»" sits next to "Материалы на 16.10.2026". Qualify it inline with "в снимке от 17.09.2026".
- **R9. Unknown producers.** `/lineup/<unknown>` returns 200, which is a soft 404. Consider returning 404.
- **R10. Browser coverage gaps.**
  - Overview mode (no `?wine`) for the new maps.
  - The scanner path, including the nested dialog on WebKit mobile.
  - The unplaced state.
  - "Открыть все" on the 25- and 26-group maps.
- **R11. Runtime throw.** One invalid JSON among 11 now breaks the scanner at import. Consider skipping invalid maps with `console.error` in production, and keep the throw in tests and dev.
- **R12. Group order.** Collapsed previews show the first 4 products. In mixed groups, list linked cards before gray additions.

## Packet limits

- **Only additions are in the packet:**
  - The map JSONs contain only the 33 null-slug additions plus `linked_count` and `largest_group`.
  - If these are the literal files, every map fails the "Empty group" check and the module throws at import.
  - I assumed they are excerpts, so the 562 linked nodes are unreviewed: their grouping, images and variants.
  - `linked_count` and `largest_group` are not in the schema. If they ship, nothing validates them.
- **Not supplied:** the registry index, the Abrau JSON, `sourceWineUrl`, the crosswalk and baseline files, the assets and the build config.
- **No results claimed:** I have not run any tests or builds and claim no results.
