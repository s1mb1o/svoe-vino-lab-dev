# Telegram album receipt

Date: 2026-09-26

## Context

Telegram sends each photo in an album as a separate update.
The previous implementation sent one queue receipt for each update.
This behavior produced duplicate queue messages for one user action.

## Options

### Send one receipt for each photo

This option maps each receipt to one queue job.
This option produces duplicate messages for an album.

### Send one receipt for the complete album

This option reduces message noise.
This option keeps separate processing and results for each photo.

### Send no receipt for an album

This option produces the fewest messages.
This option does not confirm that the bot accepted the album.

## Decision

Use `chat_id` and `media_group_id` to identify one Telegram album.
Send the queue receipt only for the first accepted photo in the album.
Keep one queue job and one result for each photo.
Expire a tracked identifier after five minutes.
Keep at most 1000 tracked identifiers.

## Consequences and risks

One album produces one queue receipt.
Each photo still uses one request from the rate limit.
Each photo still produces one recognition result.
A process restart during album delivery can produce a second receipt.
