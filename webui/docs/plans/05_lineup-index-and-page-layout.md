# Producer map index and page layout

Date: 2026-10-19.
Base: GitHub `main` `4530a21b`.
Status: Implemented on 2026-10-19. The owner approved the decisions below.

## Goals

1. Add `https://chtozavino.ru/lineup`: an index of the available producer maps.
2. On `/lineup/<producer>`, show the map in the page space. Do not use a scroll box inside the page.

## Owner decisions

| Topic | Decision |
|---|---|
| Index cards | Producer name, one bottle image, the product count, the group count, and the materials date. The card links to `/lineup/<producer>`. |
| Index data | Add a summary to the generated index. The index page loads no map data. |
| Index search policy | Public. `/lineup` is in `sitemap.xml`. `/lineup/<producer>` stays `noindex`. |
| Links to the index | The guide fallback for a producer without a map. A back link on each map page. |
| Map page layout | A reflowing page section: full page width, groups in 3, 2, or 1 columns, and page scrolling. No inner scroll box, no drag pan, no zoom buttons. |
| Map page details | The details popup at every width. |
| Scope | Only the `/lineup/<producer>` pages. The guide dialog keeps the pan and zoom canvas. |
| Sticky controls | Only the first toolbar row (group picker and locate) sticks to the window top inside the map. The other rows stay in place. |

## Design

- `ProductLineMap.vue` gets a `layout` prop: `canvas` (default, the guide dialog) or `page`.
- In `page` layout, the details always use the popup dialog. The map column uses the full width.
- In `page` layout, the canvas is a normal block. It has no fixed height, no transform, and no own scrolling.
- «Перейти к группе», «Показать ваше вино», and the initial selection scroll the window.
- Expanding or collapsing groups keeps the anchor group at the same window position.
- The index summary has `products`, `groups`, `as_of`, and `cover` (the first product image of the map, with its frame).
- The route rule `noindex` changes from `/lineup/**` to `/lineup/*`, so that it does not match `/lineup`.

## Tests

- Unit: the index summary matches the maps. The cover is an image of the map.
- `test:producer-maps`: page layout at all widths: popup details, window scroll preserved on return, no inner scroll box.
- `test:line-map`: the canvas scenarios (zoom, keyboard pan, drag suppression, 700 to 768 px boundaries, side card) move to the guide dialog of the scan flow. The page scenarios check the page layout.
- A new index check: 19 cards, links, images, no horizontal overflow at 320, 390, and 1440 px, both themes, and the `x-robots-tag` of `/lineup`.

## Risks

- The canvas scenarios of `test:line-map` change their entry point. The change can hide a regression in the page. The page layout gets its own checks.
- A long map page needs a way back to the groups. The group picker stays at the top of the map.
