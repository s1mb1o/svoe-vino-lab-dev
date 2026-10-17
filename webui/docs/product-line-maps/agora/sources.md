# AGORA WINERY: source evidence

Date: 2026-10-16.

Include all 32 exact catalog cards for `AGORA WINERY`.
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

- `yachting`: Reserve Yachting. Rank 3. Catalog row indices: 23, 24, 25, 26, 27, 28. Sources: official-yachting, svoe-vino-2026-09-17.
- `terroir`: AGORA Терруарное. Rank 3. Catalog row indices: 17, 18. Sources: official-terroir, svoe-vino-2026-09-17.
- `core`: AGORA · классическая. Rank 2. Catalog row indices: 0, 1, 2, 3, 4, 5, 6, 14, 15, 16. Sources: official-core, svoe-vino-2026-09-17.
- `rosa-still`: ROSA VIVA · тихие. Rank 1. Catalog row indices: 9, 10, 11, 12. Sources: official-rosa-still, svoe-vino-2026-09-17.
- `rosa-sparkling`: ROSA VIVA · игристые. Rank 0. Catalog row indices: 7, 8, 13. Sources: official-rosa-sparkling, svoe-vino-2026-09-17.
- `cuvee`: AGORA CUVEE. Rank 0. Catalog row indices: 21, 22. Sources: official-cuvee, svoe-vino-2026-09-17.
- `vintage`: VINTAGE. Rank 0. Catalog row indices: 19, 20. Sources: official-vintage, svoe-vino-2026-09-17.
- `blush`: BLUSH MIRAGE. Rank 0. Catalog row indices: 29, 30, 31. Sources: official-blush, svoe-vino-2026-09-17.
- `crispy`: Crispy Wine. Rank 0. Catalog row indices: none. Sources: official-crispy, svoe-vino-2026-09-17.

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
