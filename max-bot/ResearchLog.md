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

## 2026-10-17: Telegram and MAX differences that the platform does not force

The comparison covers `feature/im-bot` at `24f560c3`: both specifications, the non-shared modules
(`app.py`, `config.py`, `profile.py`, `profile_sync.py`, `storage.py`), the Russian user texts, and
the settings. The user texts are equal, except the platform name and the user ID in the privacy
answer. The settings are equal, except the MAX transport settings and the gx10 ports.

Differences without a platform reason:

1. API rate limits. The MAX client keeps 30 requests per second and 2 message operations per
   second in one chat, and it repeats a send after HTTP 429. The Telegram bot has no throttle and
   no retry after HTTP 429, although Telegram also limits bots.
2. Administration retry source. MAX reads the stored accepted copy (M17). Telegram downloads the
   image again by its `file_id`. Both bots keep the accepted copy.
3. Download retry. MAX reads the message again and retries once (M16). The reason is the
   undocumented attachment URL lifetime. Telegram does not retry a failed download.
4. Privacy answer. MAX adds the user ID of the user. Telegram does not. The MAX specification lists
   this as platform difference 7, but Telegram has no limit here.
5. The MAX specification does not list FR 54.1, 60.1, 64.1, 116.1, and 142.1. The MAX code
   implements them (album result fallback, `/users` and `/reset_limit` range checks, stale
   feedback, administration retry date directory).

Differences that the platform forces: the album model (one message in MAX), the age-gate hold
(`file_id` in Telegram, a message ID read again in MAX), the durable update inbox (MAX `GET /updates`
consumes the updates), stored bodies of messages with keyboards (a MAX keyboard edit sends the
complete body), the file type of an image file (MIME type in Telegram, file name in MAX), the
command menu scope, the bot description API, the alert dialog, the link preview option of an edit,
`bot_started`, and the Russian Trusted Root CA.

