# Catalog lineup coverage

Date: 2026-10-19.
Snapshot: `official-2026-09-17`.
Snapshot SHA-256: `e915493a0a960df040b4055d33c815940e48fb1a2994a7979a819786b2c41961`.

The 25 maps represent 1,138 of 2,103 catalog cards (54.1132%).
The supported producers account for 1,139 cards. The maps represent 1,138 of these cards (99.9122%).
The maps have 1,203 product nodes in 272 groups and 68 null-slug products.
Gray products do not count as catalog coverage.

The count includes 1,135 exact slugs and 3 verified aliases.
Producer-name fallback does not count as coverage.
The 964 unsupported cards have no prepared producer map.
One supported card, `rozovoe-polusladkoe-2`, remains outside its map by owner decision until exact identification.
Abrau-Durso covers 56 of 57 cards (98.2456%). All 24 other supported maps cover every card of their verified snapshot producer names.

Golubitskoe Estate includes the exact source names `Golubitskoe Estate` and `Поместье Голубицкое`.
These names identify one winery and one prepared map. The source producer values remain unchanged.

## Supported maps

| Producer | Covered cards | Catalog cards | Product nodes | Gray products | Groups |
| --- | ---: | ---: | ---: | ---: | ---: |
| Абрау-Дюрсо | 56 | 57 | 73 | 20 | 19 |
| Бельбек | 39 | 39 | 40 | 1 | 8 |
| Валерий Захарьин | 46 | 46 | 47 | 1 | 14 |
| Ведерниковъ | 43 | 43 | 45 | 2 | 10 |
| Винодельня Бюрнье | 20 | 20 | 22 | 2 | 6 |
| Дербент Вино | 63 | 63 | 67 | 4 | 8 |
| ЗМВ Коктебель | 26 | 26 | 28 | 2 | 10 |
| Золотая Балка | 41 | 41 | 43 | 2 | 10 |
| Имение Сикоры | 21 | 21 | 22 | 1 | 6 |
| Инкерман | 15 | 15 | 17 | 2 | 6 |
| Кубань-Вино | 97 | 97 | 103 | 6 | 26 |
| Массандра | 44 | 44 | 46 | 2 | 9 |
| Мысхако | 92 | 92 | 97 | 5 | 20 |
| Новый Свет | 44 | 44 | 45 | 1 | 6 |
| Раевское | 23 | 23 | 24 | 1 | 6 |
| Собер Баш | 37 | 37 | 38 | 1 | 6 |
| Союз-Вино | 69 | 69 | 70 | 1 | 19 |
| Фанагория | 102 | 102 | 108 | 6 | 25 |
| Шато Пино | 50 | 50 | 51 | 1 | 13 |
| AGORA WINERY | 32 | 32 | 33 | 1 | 9 |
| Alma Valley | 39 | 39 | 41 | 2 | 8 |
| AYA Organic Wine & Vineyards | 27 | 27 | 28 | 1 | 9 |
| Chateau de Talu | 26 | 26 | 27 | 1 | 6 |
| ESSE | 53 | 53 | 54 | 1 | 6 |
| Golubitskoe Estate | 33 | 33 | 34 | 1 | 7 |

## Producers without a map

The ranking uses exact snapshot producer values. It does not measure production volume or the complete current assortment.

| Producer without a map | Catalog cards |
| --- | ---: |
| WINEMAFIA | 31 |
| АРАТТИ | 31 |
| Olymp Winery | 29 |
| Усадьба Мезыбь | 26 |
| Château Le Grand Vostock | 25 |
| Belmas Winery | 22 |
| Усадьба Перовских | 22 |
| Denisov Winery | 21 |
| Галицкий и Галицкий | 20 |
| Скалистый берег | 20 |
| Domaine Lipko | 20 |
| Золотое Поле | 19 |
| Винодельня Батрак | 19 |
| Агролайн | 18 |
| Vibes | 18 |
| Реликта | 17 |
| Усадьба Дивноморское | 17 |
| Шато АЛВИСА | 16 |
| Виноградники Гай-Кодзора | 16 |
| LETO | 16 |

Read [catalog-lineup-coverage.json](catalog-lineup-coverage.json) for all supported maps, unsupported producers, and the source hash.
The counts were recomputed from the full pinned snapshot through `resolveProductLineIndex`.
The generated index was checked against all map JSON files with `buildProductLineIndex` and `validateProductLineMaps`.
