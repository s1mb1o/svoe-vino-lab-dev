# Decision 001: Thin bot over existing services

Date: 2026-09-26

Status: Superseded for moderation by Decision 009.

## Context

The bot must be available on the same day.
`gx10` already runs `llama-swap` on port `18081`.
`gx10` already runs `svoe-vino-matcher` on port `8158`.

## Options

### Thin bot

The bot calls the existing moderation model and matcher.
This option has the smallest new runtime surface.

### Full recognition pipeline

The bot calls `drink-atlas-recognize`.
This option adds more service dependencies and more latency.

### Bot-owned candidate re-rank

The bot requests several candidates and applies a new VLM re-rank.
This option adds unmeasured recognition logic.

## Decision

Use the thin bot.
Use `qwen3.5-9b` for the safety classification.
Use the matcher default pipeline for recognition.
Load the catalogue metadata from the existing local JSONL file.

## Consequences

The bot does not duplicate recognition code.
The bot depends on two local services.
The moderation model is a general VLM and not a certified safety classifier.
The service fails closed when moderation is unavailable.
