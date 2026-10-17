# Research log

## 2026-10-17: MAX platform findings

### Command menu scope

`PATCH /me/commands` sets one list of up to 32 commands for all users.
The method has no scope for a chat or a user. The bot cannot show the administrator commands
only to the administrator. Owner decision: keep the administrator commands out of the menu.
They work when typed in the administrator dialog.

### Image sent as a file

A live update of 2026-10-17 shows the `file` attachment shape:
`filename` and `size` next to `payload` {`fileId`, `token`, `url`}.
An `image` attachment has `payload` {`photo_id`, `token`, `url`} and no file name.
The file name is the only type information of a `file` attachment.

### HEIC

Public sources do not describe how the MAX iOS app sends a HEIC photo as a file.
The bot accepts `.heic` and `.heif` file names and converts the image to JPEG.
See `../telegram-bot/ResearchLog.md` (2026-10-17) for the conversion details.

### Update delivery

MAX recommends a webhook for production. gx10 has no public HTTPS name on port 443.
Owner decision: long polling in production during the hackathon (issue #10).
The webhook switch is issue #23.
