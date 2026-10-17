# Союз-Вино: source evidence

Date: 2026-10-16.

Include all 69 exact catalog cards for `Союз-Вино`.
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

- `terra-pia`: Terra Pia. Rank 2. Catalog row indices: 57, 58. Sources: official-terra-pia, svoe-vino-2026-09-17.
- `green-valley`: Зелёная Долина · бутылки. Rank 1. Catalog row indices: 59, 61, 63, 65, 67, 68. Sources: official-green-valley, svoe-vino-2026-09-17.
- `green-cans`: Зелёная Долина · банки. Rank 0. Catalog row indices: 60, 62, 64, 66. Sources: official-green-cans, svoe-vino-2026-09-17.
- `isola-cans`: Isola del Sole · банки. Rank 0. Catalog row indices: 6, 7. Sources: official-isola-cans, svoe-vino-2026-09-17.
- `el-crucero`: Эль Крусеро. Rank 0. Catalog row indices: 0, 1. Sources: svoe-vino-2026-09-17.
- `gloria`: Gloria de Luna. Rank 0. Catalog row indices: 2, 3, 4, 5. Sources: svoe-vino-2026-09-17.
- `canon`: Канонические Традиции. Rank 0. Catalog row indices: 8, 9. Sources: official-canon, svoe-vino-2026-09-17.
- `kartuli`: Картули Суприс. Rank 0. Catalog row indices: 10, 11, 12. Sources: svoe-vino-2026-09-17.
- `confessa`: Confessa. Rank 0. Catalog row indices: 13, 14, 15. Sources: svoe-vino-2026-09-17.
- `kubanskoe`: Кубанское Традиционное. Rank 0. Catalog row indices: 16, 17, 18, 19, 20, 21, 22, 23. Sources: svoe-vino-2026-09-17.
- `lac`: Lac d’Azur. Rank 0. Catalog row indices: 24, 25, 26, 27. Sources: svoe-vino-2026-09-17.
- `lavetti-wine`: Lavetti · тихое вино. Rank 0. Catalog row indices: 28, 29, 30, 31, 32. Sources: svoe-vino-2026-09-17.
- `lenty`: Ленты. Rank 0. Catalog row indices: 33, 34, 35. Sources: svoe-vino-2026-09-17.
- `mosavali`: Мосавали. Rank 0. Catalog row indices: 36, 37, 38. Sources: svoe-vino-2026-09-17.
- `montgolfier`: Шато де Монгольфьер. Rank 0. Catalog row indices: 39, 40, 41. Sources: svoe-vino-2026-09-17.
- `sheremetev`: Шереметьевские Погреба. Rank 0. Catalog row indices: 42, 43, 44, 45. Sources: svoe-vino-2026-09-17.
- `soyuz-bottles`: Союз-Вино · бутылки. Rank 0. Catalog row indices: 48, 50, 53, 56. Sources: svoe-vino-2026-09-17.
- `soyuz-box`: Союз-Вино · пакеты и Bag-in-Box. Rank 0. Catalog row indices: 46, 47, 49, 51, 52, 54, 55. Sources: svoe-vino-2026-09-17.
- `perle`: La Petite Perle · банки. Rank 0. Catalog row indices: none. Sources: official-perle, svoe-vino-2026-09-17.

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
Historical brands without an exact official collection source cite only the saved snapshot and use rank 0.
The current Lavetti cider catalog does not establish the identity of historical wine cards.
The saved alcoholic La Petite Perle page is distinct from the alcohol-free homepage promotion.
