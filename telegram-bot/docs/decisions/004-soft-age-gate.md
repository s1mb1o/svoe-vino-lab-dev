# Soft age gate

Date: 2026-09-26

## Context

The bot provides information about wine.
The user requested a soft confirmation for users who are at least 18 years old.

## Options

### Confirm on `/start`

This option shows the notice before the first photo.
This option lets the bot reject a photo before download.

### Confirm on the first photo

This option reduces the initial `/start` content.
This option requires the user to send the photo again.

### Show the notice without confirmation

This option has the lowest interaction cost.
This option does not record an explicit user choice.

## Decision

The bot asks for confirmation on `/start`.
The bot stores `adult` or `minor` and the decision time in SQLite.
The bot accepts a photo only after the `adult` confirmation.
The bot does not verify an identity document.

## Consequences and risks

The flow adds one action before the first photo.
The confirmation is self-declared and does not prove the user's age.
Existing users must confirm their age after deployment.
The bot can reject a photo before it uses storage or recognition resources.
