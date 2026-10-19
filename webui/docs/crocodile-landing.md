# Wine Crocodile landing

Date: 2026-10-19.

## Scope

The owner selected a separate `/crocodile` page in the existing portal.
Use the portal header, age gate, theme, typography, and footer.
Keep the existing scanner, Wine&Dine Merge page, and other projects unchanged.
The page introduces the physical card game. It does not sell the game or claim online multiplayer.
Add an invitation on `/ideas`, canonical metadata, social metadata, and a sitemap entry.

## Content

The approved source is `<drink-atlas-workspace>/ideas/wine-crocodile/cards-01.md`.
Use the three existing explanation modes and the one-to-three-point difficulty scale.
The base round lasts sixty seconds. The teams alternate turns and change the explaining player.
The rule text specifies zero points for a skipped or expired card.
The teams can play the complete deck or agree on an equal number of turns.
Keep the coupe story labeled as an unverified legend.
Keep six exact sample texts: R05, W08, P01, R09, W01, and P03.
The sample illustrations are the existing approved RGB artwork.
The sample cards use native HTML text, local images, and CSS mesh backs.
Use a native button for each flip. Support Enter and Space.
Use native filter buttons with `aria-pressed`.
Use native `details` elements for the FAQ.
Do not invent reviews, sales, prices, expert approval, or playtest results.

## Images and files

The owner supplied three photographs on 2026-10-19.
Built-in image_gen produced two retouched photo compositions.
The edits remove room clutter, replace the background, improve lighting, and tidy the box lid.
The images preserve the game identity and the real paper prototype appearance.
The main image also retains the owner's wine bottle.
The close-up has the box and cards only.
Do not use generated small print as factual product evidence.
Keep the exact UI text independent from the photo text.

The generated PNG masters are `docs/crocodile-media/hero-retouched.png` and `detail-retouched.png`.
The complete prompts are in `docs/crocodile-media/image-prompts.json`.
The source and output hashes are in `docs/crocodile-media/asset-manifest.json`.
The public WebP files are delivery encodings of the generated masters.
The six illustration WebP files are delivery encodings of the existing illustration assets.
The public print PDFs are exact copies of the approved home card file and manual box file.
The card PDF contains eight pages. The box PDF contains one portrait A4 page.
The box targets the owner's 12 mm deck with a 14 mm fold distance.

## Development and verification

The isolated checkout is `/Volumes/Storage/svoe-vino-final/code/svoe-vino-crocodile-landing`.
Its branch is `codex/wine-crocodile-landing-20261019`.
The preview uses loopback port 18557. The port is recorded in the owner's port registry.
Run `npm run dev -- --port 18557` from `webui/`.
Run `npm run typecheck`, `npm run build`, and `npm run test:bundle`.

```sh
PLAYWRIGHT_MODULE=/absolute/path/to/playwright/index.mjs \
PORTAL_ORIGIN=http://127.0.0.1:18557 \
node scripts/check-crocodile-browser.mjs
```

The browser check uses Chromium and WebKit at 320, 390, 768, and 1440 pixels in both system themes.
The check covers navigation, the existing age gate, metadata, filters, card flips, keyboard input, FAQ, image loading, overflow, and PDF download hashes.
The check saves screenshots and a JSON result under `reports/crocodile/`.
Browser emulation does not establish physical-device acceptance.
This task prepares local source and a production build. It does not deploy the portal.

## Accepted verification

The type check, production build, bundle check, and all sixteen browser layouts pass.
The final check includes photo proportions and real text contrast.
Read `validation/crocodile-landing.md` for the results and resolved visual failures.
