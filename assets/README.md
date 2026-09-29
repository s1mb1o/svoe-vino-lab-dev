# Project image assets

This directory contains shared visual assets for the `svoe-vino-lab` project.
Each subproject MAY use these assets.
Keep a subproject-specific asset in the directory of that subproject.

## Asset catalog

| Artwork | Size | Purpose |
|---|---:|---|
| `product-logo-640x640.png` and `product-logo-640x640.svg` | 640 × 640 | Product logo. Use this artwork as the common product identifier. The Telegram bot can use it as its profile image. The image shows a wine bottle inside scanner marks. |

## File maintenance

Treat the PNG file as the visual source for its SVG counterpart.
The SVG file embeds the PNG file without a visual change.
The SVG file is not an editable path-based illustration.
Regenerate the SVG file after the PNG file changes.
Preserve the 640 × 640 canvas size during regeneration.
