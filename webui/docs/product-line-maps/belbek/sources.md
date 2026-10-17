# Бельбек: source evidence

Date: 2026-10-16.

Include all 39 exact catalog cards for `Бельбек`.
Use the independent catalog baseline and crosswalk in this directory.
Preserve catalog names, descriptions, grapes, and separate identities.
Do not infer vintage, alcohol, or price from slug suffixes.
Do not treat this map as the complete live assortment.

## Collections and positioning

Ranks compare groups within this producer. Numeric prices remain null.
Rank 0 means that no relative price rank is confirmed.
Read `source-evidence.json` for exact URLs, document sections, retrieval dates, source hashes, and snapshot-only groups.
Read `group_basis` in the crosswalk for each product membership decision.
Read collection labels from original input photographs. Do not use generated text.

- `reserve`: Резерв и Баррик. Rank 3. Catalog row indices: 9, 10, 13, 25, 29, 34, 35, 36. Sources: official-reserve, svoe-vino-2026-09-17.
- `red`: Красные сортовые и купажи. Rank 2. Catalog row indices: 2, 3, 4, 6, 7, 12, 14, 16, 17, 19, 20, 23, 24, 32, 33. Sources: official-red, svoe-vino-2026-09-17.
- `white`: Белые сортовые. Rank 2. Catalog row indices: 0, 5, 8, 18, 21, 28, 30, 37. Sources: official-white, svoe-vino-2026-09-17.
- `rose`: Розовые вина. Rank 0. Catalog row indices: 11, 26, 31. Sources: official-rose, svoe-vino-2026-09-17.
- `orange`: Мускат Оранж. Rank 0. Catalog row indices: 22. Sources: official-orange, svoe-vino-2026-09-17.
- `sweet`: Фиолент и Поздний сбор. Rank 0. Catalog row indices: 1, 27. Sources: official-sweet, svoe-vino-2026-09-17.
- `zakat`: Закат. Rank 0. Catalog row indices: 38. Sources: svoe-vino-2026-09-17.
- `unresolved`: Карточка с противоречием. Rank 0. Catalog row indices: 15. Sources: svoe-vino-2026-09-17.

## Images

The crosswalk records input and output SHA-256 values.
Use `imagegen-cutouts.json` where present for exact prompts and generated hashes.
Use `scripts/measure-product-image-frames.mjs` for actual image dimensions, alpha outlines, and frame containment.
Inspect cutouts on light and dark surfaces. Generated fine print is not product evidence.

## Review correction, 2026-10-17

The owner authorized the exact review packet. Claude Opus 5.5 Max reviewed that packet.
Source records now distinguish official collection evidence from snapshot-only navigation.
Separate catalog records retain separate nodes. Neutral card numbers do not assert a vintage or package difference.
Official additions remain unlinked when a possible historical catalog counterpart cannot be verified.
Белое сухое has conflicting red Cabernet metadata. It remains unresolved.
The possible Reserve counterpart is recorded. No verified equivalence is claimed.
