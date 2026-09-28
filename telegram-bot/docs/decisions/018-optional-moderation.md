# Optional moderation

Date: 2026-09-28

Status: Accepted for local development and tests. Production MUST NOT use this bypass.

This decision updates the moderation conditions in Decisions 013 and 015 and in plans 01,
03, 05, and 06. Their unconditional moderation requirements remain mandatory in production.

## Context

ShieldGemma can add latency and GPU use. Local development and tests can need to run
recognition without the moderation service.

## Decision

Add `moderation.enabled` to `config.yaml`. The default value is `true`.

The bot MUST refuse to start in the production environment when the value is `false`.

When the value is `false`, the bot MUST NOT resolve `endpoints.moderation`. The bot MUST
NOT call ShieldGemma. The bot MUST accept each valid image for the remaining pipeline.
The bot MUST store `disabled` as the moderation category. It MUST store no safety verdict.
The HTTP API MUST return `performed=false`, `bypassed=true`, and `safe=null`. The bot MUST
write a warning at startup.

When the value is `true`, the existing fail-closed ShieldGemma behavior stays unchanged.

## Consequences

A local development or test deployment can run without `MODERATION_ENDPOINT` when
moderation is disabled.
An unmoderated image can enter recognition and accepted storage in this mode.
The configuration, nullable safety value, and stored category make this mode explicit.
