# Result feedback

Date: 2026-09-26

## Context

The service needs a binary quality signal for a successful recognition result.
The feedback prompt must not add a separate Telegram message.
An album must not create many feedback prompts.

## Options

1. Add inline buttons to the result message.
2. Send a separate feedback message.
3. Keep the buttons active and permit feedback changes.

## Decision

Add `✅ Совпало` and `❌ Не совпало` inline buttons to a successful single-photo result.
Do not add feedback buttons to an album result.
Accept feedback only from the user who sent the source photo.
Accept only the first feedback value for a request.
Remove the buttons after a successful submission.

Store feedback in the request row.
Store the binary value and the submission time.
Store whether the request is eligible for feedback.

## Consequences

The feedback remains linked to the stored image and recognition result.
The database migration adds three request columns.
An old request is not eligible for feedback because its album state is unknown.
