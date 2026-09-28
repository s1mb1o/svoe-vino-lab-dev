# Decision 012: separate administration web service

Date: 2026-09-26

Status: Accepted. The production port and deployment procedure were superseded by
[Decision 017](017-matcher-match-endpoint.md) and
[plan 06](../plans/06_matcher-match-endpoint.md). The interface now uses production port
`28003`. The obsolete systemd assets were removed.

## Context

The Telegram administrator commands show only compact statistics and user data.
Operational review needs request details, timing data, moderation reports, and safe actions.
The bot process already owns Telegram polling and the processing queue.

## Options

### Add pages to the Telegram bot process

This option reduces the number of services.
An HTTP failure can affect Telegram polling.
Deployment and shutdown behavior become more complex.

### Run a separate FastAPI service

This option isolates HTTP traffic from Telegram polling.
Both processes can use SQLite WAL mode.
A persistent database status can transfer retry work to the bot process.

### Build a read-only dashboard

This option has the smallest mutation surface.
It cannot reset limits or request a retry.

## Decision

Run a separate FastAPI service.
Use the existing SQLite database.
Use persistent status changes for bot actions.
Do not serve stored images.
Require password authentication and a LAN CIDR allowlist.

## Consequences

The original deployment had one additional systemd user service.
SQLite remains the coordination point.
The bot needs a small retry watcher.
The web service can restart without losing a requested retry.
The first version uses HTTP Basic authentication on the trusted home LAN.
Public exposure is forbidden.
