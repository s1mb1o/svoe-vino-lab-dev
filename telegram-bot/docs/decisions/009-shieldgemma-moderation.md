# ShieldGemma moderation

Date: 2026-09-26

## Context

The existing moderation uses a general vision language model and a custom prompt.
A dedicated `shieldgemma-2-4b-it` classification endpoint is available on `gx10`.
The endpoint returns policy violation probabilities and a thresholded `flagged` list.

## Options

1. Replace the existing moderation with the ShieldGemma endpoint.
2. Apply a client-owned threshold to the returned scores.
3. Run the old and new moderation checks together.

## Decision

Replace the existing moderation check.
Send a multipart `image` field to `/upstream/shieldgemma-2-4b-it/classify`.
Use the `dangerous`, `sexual`, and `violence` policies.
Use the service `flagged` list at threshold `0.5`.
Reject an image when the `flagged` list is not empty.
Fail closed for a transport error or an invalid response.

Validate the model name, threshold, policy names, score ranges, and `flagged` consistency.
Do not keep the old moderation model as a fallback.

## Consequences

The bot no longer sends a base64 image in a chat completion request.
The bot no longer needs `MODERATION_MODEL`.
The moderation category stores the flagged policy names.
The moderation confidence stores the maximum violation probability.
The moderation reason stores all three policy scores.
