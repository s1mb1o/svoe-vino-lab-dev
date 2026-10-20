# Image assets

This directory contains images that belong only to `@ChtoZaVinoBot`.
Each current artwork has a PNG file and an SVG file.
The PNG file is the source artwork. Telegram and the bot runtime use the PNG files.
The SVG file is a vector redraw of the PNG file with paths and no embedded bitmap.
The redraw uses flat colours. It omits the paper grain and replaces soft gradients with flat shades.
`botpic-v3-scanner.svg` is the same file as `../../assets/product-logo-640x640.svg`.

## Project-wide logo

The canonical product logo is in the project-level `../../assets` directory.
The files are `../../assets/product-logo-640x640.png` and
`../../assets/product-logo-640x640.svg`.
The Telegram bot can use the PNG file as its profile image.

## Asset catalog

| Artwork | Size | Purpose |
|---|---:|---|
| `content-rejected-monkey-640x640.png` and `content-rejected-monkey-640x640.svg` | 640 × 640 | Content rejection illustration. The bot sends this illustration when moderation classifies a submitted image as unsafe. The production configuration uses the PNG file through `BOT_REJECTION_IMAGE`. |
| `description-picture-selected-640x360.png` and `description-picture-selected-640x360.svg` | 640 × 360 | Selected Telegram description picture. Use this artwork for the bot profile description. The image tells the user to send a bottle or label photo. |
| `description-picture-v2-scanner.png` and `description-picture-v2-scanner.svg` | 640 × 360 | Alternative Telegram description picture. This version uses a clean panel, a scanner illustration, explanatory text, and a call-to-action button. Keep it as a design alternative. |
| `description-variants/description-light-640x360.png` and `description-variants/description-light-640x360.svg` | 640 × 360 | Light description picture variant. Keep it in `description-variants` for design comparison. Its current PNG content is identical to `description-picture-selected-640x360.png`. |

## Runtime use

The bot runtime reads only the configured content rejection illustration from this directory.
The default file is `content-rejected-monkey-640x640.png`.
The description pictures are profile assets.
An administrator uploads the logo and the description picture through the Telegram bot management interface.

## File maintenance

Treat each PNG file as the visual source for its SVG counterpart.
Regenerate the SVG file after a PNG file changes.
Preserve the original canvas size during regeneration.
Preserve transparency when the PNG file contains an alpha channel.
