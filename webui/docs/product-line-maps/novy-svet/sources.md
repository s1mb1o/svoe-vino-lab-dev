# Новый Свет: source evidence

Date: 2026-10-16.

Include all 44 exact catalog cards for `Новый Свет. Дом шампанских вин`.
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

- `prestige`: Кюве Де Престиж. Rank 3. Catalog row indices: 7, 10, 12, 13, 26, 32, 34. Sources: official-prestige, svoe-vino-2026-09-17.
- `limited`: Особые кюве из снимка. Rank 0. Catalog row indices: 1, 6, 15, 22, 27, 28, 29, 31, 33. Sources: svoe-vino-2026-09-17.
- `collection`: Коллекционное. Rank 2. Catalog row indices: 5, 9, 11, 30, 35, 36, 37, 38. Sources: official-collection, svoe-vino-2026-09-17.
- `aged`: Выдержанное. Rank 1. Catalog row indices: 2, 3, 4, 8, 14, 16, 17, 18, 19, 20, 23, 24, 25, 39, 40, 41, 42, 43. Sources: official-aged, svoe-vino-2026-09-17.
- `crown`: Коронационное. Rank 4. Catalog row indices: none. Sources: official-crown, svoe-vino-2026-09-17.
- `varietal-unconfirmed`: Алиготе и Кокур · серия не уточнена. Rank 0. Catalog row indices: 0, 21. Sources: svoe-vino-2026-09-17.

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
The exact snapshot producer is Новый Свет. Дом шампанских вин. The baseline contains 44 records.
Two explicit aged cards move to aged. Two shorter varietal cards have no confirmed collection and use rank 0.
Special historical cuvees use rank 0. Do not claim a common limited status or premium rank.
