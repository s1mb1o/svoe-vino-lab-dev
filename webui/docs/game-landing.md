# Wine&Dine Merge landing page

Date: 2026-10-19.

## Entry and scope

The owner selected a landing page on the main portal.
The navigation path is `/hackaton` → `/ideas` → `/game`.
The Game invitation on `/ideas` opens `/game`.
The Play links open `https://game.chtozavino.ru/`.
The pouring link opens `https://game.chtozavino.ru/?mode=pour`.
The game origin and game entry URLs do not change.

The page uses the portal header, age gate, theme, and footer.
It has one heading, canonical metadata, and a sitemap entry.
It introduces ingredient merging, wine selection, and pouring.
It shows three selectable regional scenes and their current menu examples.
The scene selector supports click, Tab, arrow keys, Home, and End.
Native `details` elements provide the FAQ.
The page does not load the game runtime or read campaign progress.
The Play action navigates in the same tab.

The existing blind-style quiz mock remains separate on `/ideas`.
Do not identify the merge game as that quiz.
Describe the game as a working educational prototype.
State that pairing and service rules are simplified and have no completed expert review.
Do not claim educator approval or physical-device acceptance.

## Content evidence

The source game is `s1mb1o/wine-and-dine-merge` at revision `1bb250e45a801c11cec3c08e9843f695146fba9a`, version `0.8.22`.
The local source is `/Volumes/Storage/svoe-vino-final/code/wine-and-dine-merge`.
The README describes six main regions, eight optional regions, and three services per region.
`src/wine-geography.ts`, `src/content.ts`, and `src/i18n.ts` provide the regional menu examples.
The FAQ follows the README for browser play, optional installation, local progress, standalone practice, and content limits.
The game UI supports Russian and English. This portal page uses the existing Russian interface.

## Artwork

Seven standalone local SVG files are in `public/game-art/`.
They derive from original game artwork in `src/art.ts`, `src/regional-art.ts`, `src/ingredient-art.ts`, and `src/dish-art.ts`.
The hero is a new composition of that artwork.
The board in the hero is an illustration, not an interactive game board.
The food illustration uses the retained fish-and-lemon dish.
Regional captions use only the selected current regional menu.
Static glass exports omit runtime overflow layers and use XML attributes for hidden groups.
The page requires no external image host, generated bitmap, or game bundle.

## Verification

Run `npm run typecheck` and `npm run build`.
Run `npm run test:bundle` after a build.
Use the browser script against the preview or production build:

```sh
PLAYWRIGHT_MODULE=/absolute/path/to/playwright/index.mjs \
PORTAL_ORIGIN=http://127.0.0.1:PORT \
node scripts/check-game-landing-browser.mjs
```

The script tests Chromium and WebKit at 320, 390, 768, and 1440 pixels in both system themes.
It checks the age gate, exact outgoing URLs, route navigation, canonical metadata, local images, FAQ disclosure, region selection, keyboard focus, and horizontal overflow.
It saves screenshots and a JSON result in `reports/game-landing/` by default.
Use `GAME_LANDING_REPORT_DIR` for a different evidence directory.
Browser emulation is not a physical-phone test.

Production deployment follows the existing portal runbook in `<workspace>/deploy/princess/webui.md`.
Preserve the existing portal audience and game deployment.
