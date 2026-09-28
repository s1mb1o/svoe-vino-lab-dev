# Rejection illustration

Date: 2026-09-26

## Context

An unsafe-image rejection currently edits the temporary processing status.
The rejection must show a supplied illustration and a clear message.
The response must remain linked to the source photo.

## Options

1. Replace the temporary status with one photo response.
2. Keep the temporary status and send an additional photo response.
3. Send a photo response without a reply link.

## Decision

Send the supplied 640 by 640 PNG as a Telegram photo.
Reply to the source photo.
Add the rejection message as the photo caption.
Delete the temporary processing status after the photo response succeeds.
Use the text rejection status when the photo response fails.

## Consequences

An unsafe request normally produces one final rejection response.
The supplied image becomes a required deployment asset.
The service reads the asset once during startup.
