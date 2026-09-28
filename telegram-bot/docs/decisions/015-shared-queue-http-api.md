# Decision 015: Shared-queue HTTP recognition API

Date: 2026-09-27

Status: Accepted. The production port and deployment procedure were superseded by
[Decision 017](017-matcher-match-endpoint.md) and
[plan 06](../plans/06_matcher-match-endpoint.md). The API now uses production port `28002`.
The obsolete systemd assets were removed.
Decision 018 permits an explicit moderation bypass only for local development and tests.

## Context

Internal LLM tests need wine recognition without Telegram.
The HTTP path must have the same behavior as the Telegram path.
The service has one queue worker because the upstream models share GPU memory.
Production must not write an unmoderated image to disk.

## Options

### Process the image in the administration service

This option reuses the administration port.
This option creates a second processing worker in another process.
It does not share the Telegram FIFO queue.
It can send concurrent requests to the GPU services.

### Add an HTTP listener to the bot process

This option uses the existing `WorkQueue` instance.
It keeps Telegram and HTTP requests in one FIFO sequence.
It keeps the HTTP image in memory until moderation.
It needs a separate TCP port.

### Store the unmoderated upload for later bot pickup

This option lets the administration process submit work through SQLite.
It writes an unmoderated image to persistent storage.
It violates the image safety rule.

## Decision

Add an HTTP listener to the bot process.
Use a dedicated TCP port for the API.
Submit each HTTP image to the existing `WorkQueue` instance.
Wait for a completion future and return a synchronous JSON response.

Keep the unmoderated multipart body in bounded memory.
Do not use `UploadFile` because it can use a temporary file.
Parse the bounded multipart body in memory.

Require a bearer token for each recognition request.
Restrict clients by configured CIDR networks.
Apply client rate and global in-flight limits before reading the upload body.

## Consequences

Telegram and HTTP recognition cannot run concurrently with one queue worker.
The API request can keep at most one configured image body in queue memory.
An interrupted API request cannot resume after a restart.
The startup recovery marks that request as failed.
The API must not be exposed to WAN.
