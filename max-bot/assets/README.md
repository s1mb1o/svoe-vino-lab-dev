# Image assets

| Artwork | Size | Purpose |
|---|---:|---|
| `content-rejected-monkey-640x640.png` and `.svg` | 640 × 640 | Content rejection illustration. A copy of the Telegram bot asset. `BOT_REJECTION_IMAGE` uses the PNG file. The SVG file is a vector redraw without an embedded bitmap. |
| `max-logo-500x500.png` | 500 × 500 | Bot card logo for business.max.ru. MAX requires 500 × 500 px, a 1:1 ratio, JPG or PNG, and at most 5 MB. Made from `../../assets/product-logo-640x640.png` with a Lanczos resize. |

The bot runtime reads only the configured content rejection illustration.
The owner uploads the logo in the bot card on business.max.ru. A card change passes moderation.
