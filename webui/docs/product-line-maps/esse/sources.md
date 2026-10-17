# ESSE: source evidence

Date: 2026-10-16.

Include all 53 exact catalog cards for `ESSE`.
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

- `kacha-valley`: KACHA VALLEY. Rank 3. Catalog row indices: 4, 6, 7, 27, 42, 45. Sources: official-kacha-valley, svoe-vino-2026-09-17.
- `classic`: ESSE classic. Rank 2. Catalog row indices: 11, 12, 13, 14, 16, 19, 36, 39, 43, 44, 47, 51, 52. Sources: official-classic, svoe-vino-2026-09-17.
- `stones`: ESSE stones / Отборное. Rank 1. Catalog row indices: 15, 20, 21, 23, 37, 48, 50. Sources: official-stones, svoe-vino-2026-09-17.
- `unplugged`: Unplugged · авторские стили. Rank 0. Catalog row indices: 17, 18, 24, 26, 28, 29, 30, 31, 32, 35, 38, 46, 49. Sources: official-unplugged, svoe-vino-2026-09-17.
- `natural-sweet`: Природно полусладкие. Rank 0. Catalog row indices: 33, 34. Sources: official-natural-sweet, svoe-vino-2026-09-17.
- `sparkling`: ESSE sparkling. Rank 0. Catalog row indices: 0, 1, 2, 3, 5, 8, 9, 10, 22, 25, 40, 41. Sources: official-sparkling, svoe-vino-2026-09-17.

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
The separate Сатера producer card remains outside the 53-card baseline.
Four original labels identify Unplugged instead of KACHA VALLEY. Membership now follows those labels.
