# Decision 001: MAX port as a separate project with a checked copy of the core

Date: 2026-10-15

Status: Accepted. Reviewed with Codex (gpt-6.1-sol) on 2026-10-15; see
[plan 01](../plans/01_max-port.md), section "Review changes".

## Context

The owner needs the Telegram bot «Что за вино?» in the MAX messenger with the same functionality.
The MAX bot is registered as `@se14697933_bot`.
The Telegram bot runs in production on `gx10`. Its Docker image builds from one directory.
The MAX Bot API differs from the Telegram Bot API: string message IDs, albums as one message,
callback answers, keyboards as attachments, a required webhook in production, and a host
certificate of the Russian Trusted Root CA.

## Options

### Import the Telegram package as a library

This option avoids copies. The MAX image would need the `telegram-bot` directory and `aiogram`.
Several core modules contain Telegram names in user-visible and administration text.
A refactor of the Telegram package could break the MAX bot without a visible signal.

### Extract a shared core package from both bots

This option is the cleanest long-term structure. It changes the production Telegram bot,
its Docker build, and its tests. The owner did not ask for a Telegram change.

### Separate project with a checked copy of the core

`max-bot/` is a separate project. A script copies the processing core from `telegram-bot/` and
changes only names. A test fails when a copy differs from the Telegram source.
The transport, the storage schema, and the configuration are MAX-specific modules.

## Decision

Use a separate project with a checked copy of the core.
Write a thin MAX API client instead of a third-party SDK: MAX publishes official clients only for
Go and TypeScript, and the bot needs few methods.
Use a durable SQLite inbox for both update delivery modes.
Use a webhook in production. Keep long polling for development and tests.

## Consequences

- A core change starts in `telegram-bot/`, then `scripts/sync_shared.py` copies it.
- The MAX bot has its own database, data root, ports (28004, 28005, 28006), and image.
- The MAX bot needs a public HTTPS name on port 443 for production updates.
- The platform differences are listed in `docs/specification.md`.
