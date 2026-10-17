# Шато Пино: source evidence

Date: 2026-10-16.

Include all 50 exact catalog cards for `Шато Пино`.
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

- `poezdnik`: A. G. Поездник. Rank 4. Catalog row indices: 2, 3. Sources: official-poezdnik, svoe-vino-2026-09-17.
- `grand-reserve`: Grand Reserve. Rank 3. Catalog row indices: 12, 13, 14, 15. Sources: official-grand-reserve, svoe-vino-2026-09-17.
- `exclusive`: Exclusive. Rank 2. Catalog row indices: 8, 9, 10, 11. Sources: official-exclusive, svoe-vino-2026-09-17.
- `gravity`: Гравитация. Rank 2. Catalog row indices: 16, 20, 36. Sources: official-gravity, svoe-vino-2026-09-17.
- `koldun`: Колдун. Rank 2. Catalog row indices: 1, 22, 23, 24, 46. Sources: official-koldun, svoe-vino-2026-09-17.
- `shantazh`: Шантаж. Rank 2. Catalog row indices: 37. Sources: official-shantazh, svoe-vino-2026-09-17.
- `classic`: Классика и сортовые вина. Rank 1. Catalog row indices: 0, 19, 21, 32, 33, 38, 47, 48. Sources: official-classic, svoe-vino-2026-09-17.
- `wild`: Дикари / Дичь. Rank 0. Catalog row indices: 7. Sources: official-wild, svoe-vino-2026-09-17.
- `sorcerer-balls`: Шары Колдуна. Rank 0. Catalog row indices: 40, 41, 42, 43, 44, 45. Sources: official-sorcerer-balls, svoe-vino-2026-09-17.
- `ice-wine`: ICE Wine. Rank 0. Catalog row indices: 17. Sources: official-ice-wine, svoe-vino-2026-09-17.
- `petnat`: Петнат. Rank 0. Catalog row indices: 26, 27, 28, 29, 30. Sources: official-petnat, svoe-vino-2026-09-17.
- `sparkling`: Классическое игристое. Rank 0. Catalog row indices: 6, 31, 35. Sources: official-sparkling, svoe-vino-2026-09-17.
- `unassigned`: Без подтверждённой коллекции. Rank 0. Catalog row indices: 4, 5, 18, 25, 34, 39, 49. Sources: svoe-vino-2026-09-17.

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
