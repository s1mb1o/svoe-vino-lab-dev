# Собер Баш: source evidence

Date: 2026-10-16.

Include all 37 exact catalog cards for `Собер Баш`.
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

- `reserve`: Резервные вина. Rank 3. Catalog row indices: 0, 15, 19, 24, 26, 29. Sources: official-reserve, svoe-vino-2026-09-17.
- `amphora`: Грани · Амфора. Rank 2. Catalog row indices: 12, 18, 25, 28. Sources: official-amphora, svoe-vino-2026-09-17.
- `grani`: Грани. Rank 2. Catalog row indices: 2, 9, 10, 11, 13, 27. Sources: official-grani, svoe-vino-2026-09-17.
- `classic`: Классика. Rank 1. Catalog row indices: 1, 14, 16, 17, 20, 21, 22, 23. Sources: official-classic, svoe-vino-2026-09-17.
- `two-valleys`: Две долины. Rank 1. Catalog row indices: 3, 4, 5, 6, 7, 8. Sources: official-two-valleys, svoe-vino-2026-09-17.
- `sober-head`: Трезвая голова. Rank 0. Catalog row indices: 30, 31, 32, 33, 34, 35, 36. Sources: official-sober-head, svoe-vino-2026-09-17.

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
