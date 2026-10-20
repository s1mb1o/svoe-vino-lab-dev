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
The SVG file is a vector redraw of the PNG file. It has no embedded bitmap and is 2,810 bytes.
Use the SVG file for web pages and favicons. Use the PNG file when a tool or store needs a raster image.
Redraw the SVG file after the PNG file changes. `webui/docs/assets.md` records the method.
Preserve the 640 × 640 canvas size.
`webui/public/icons/product-logo.svg` MUST stay an exact copy of the SVG file. A Web UI test checks this.
