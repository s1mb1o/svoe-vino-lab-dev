# Visible bottle sizing validation

Date: 2026-10-16.
Source image revision: `39e93b32`.
Branch: `product-line-map`.
Local origin: `http://127.0.0.1:18553`.

## Result

All 636 producer images have a measured visible frame in their producer JSON.
The renderer uses the same frame for group previews, product nodes and product details.
The 31 small-image observations from the previous review are resolved.
Their desktop visible height is now 170 px or more, inside the 176 px image area.
All 636 source-image SHA-256 values are unchanged. The source pixels were not re-encoded.
The frame preserves the complete visible outline and source aspect ratio.
A wide package can reach the width limit before the height limit. The package is not stretched.
Read [the frame contract](../product-image-sizing.md) for the measurement and rendering method.

| Producer | Framed images | Resolved small images | Commit |
| --- | ---: | ---: | --- |
| abrau-durso | 52 | 0 | `60682360` |
| alma-valley | 41 | 3 | `dd3bf5fd` |
| derbent-vino | 66 | 5 | `eed880e9` |
| fanagoria | 107 | 6 | `82c059ca` |
| inkerman | 17 | 5 | `f21dfe02` |
| koktebel | 28 | 1 | `70e79363` |
| kuban-vino | 103 | 3 | `af83439d` |
| massandra | 45 | 4 | `577d183d` |
| myskhako | 97 | 0 | `34d2cfa1` |
| vedernikov | 45 | 1 | `ad7b56d9` |
| zolotaya-balka | 35 | 3 | `f1be6df6` |

The shared renderer commit is `1d4b3b4a`.
Each producer has a separate data commit.

## Verification

All 232 tests passed with the full catalog snapshot.
Type checks and the production build passed.
Chromium and WebKit each passed 22 sizing cases across eleven producers.
Desktop used 1440 × 1000 in light theme. Mobile used 390 × 844 in dark theme.
The cases include 2544 product-node geometry checks across both engines and viewports.
Every case checks source aspect ratio, visible frame height and clipping.
The cases also check group previews, product details, gray styling, portal links and mobile popup return.
The existing producer-map suites passed 45 checks per engine.
The existing Abrau browser suite passed in both engines.
The Abrau suite includes short landscape viewports, gift-box details, viewport transitions, nested dialogs and scanner fixtures.
Image-error placeholders and existing link rules passed in both engines.
These checks use emulated viewports. No physical device test was performed.

Read [the saved sizing results](product-image-sizing.json) for browser cases and all resolved image identities.
The ignored directory `reports/product-image-sizing/` contains measurements, screenshots and the verification script.

## Reproduction

Open `/lineup/fanagoria?wine=fanagoriya-100-ottenkov-krasnogo-pino-nuar-krasnoe-suhoe-135`.
Compare Pinot Noir with the other 100 Shades products in previews and expanded nodes.
Check the same selection in desktop details and the mobile popup.
Run the read-only frame measurement script described in the frame contract when an asset changes.
Set `PORTAL_ORIGIN=http://127.0.0.1:18553` for both existing browser suites.
Set `PLAYWRIGHT_MODULE` to the installed Playwright module.
Use `PLAYWRIGHT_BROWSER=webkit` and the installed WebKit cache path for WebKit.
Run `npm run test:line-map` and `npm run test:producer-maps`.
