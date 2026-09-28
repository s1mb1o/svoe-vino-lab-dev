# Decision 002: Shared photo processing queue

Date: 2026-09-26

## Context

Aiogram can run message handlers concurrently.
Concurrent handlers can send several requests to the moderation model and matcher.
These services share GPU resources on `gx10`.
The bot must continue to accept Telegram updates while a photo is processed.

## Options

### Semaphore in each message handler

This option limits concurrent upstream calls.
Each Telegram handler stays active until the request completes.
This option has no explicit queue state or recovery flow.

### In-memory FIFO queue with database recovery

This option gives the bot one explicit work queue.
The queue stores only request identifiers and Telegram file identifiers.
SQLite keeps the request state.
The bot can restore queued and interrupted requests after a restart.

### External queue service

This option can provide durable distributed processing.
This option adds a new service and new operational work.
The current bot runs as one process on one host.

## Decision

Use one in-memory FIFO queue.
Use SQLite as the recovery source.
Use one worker by default.
Make the worker count configurable.
Make the total queue capacity configurable.
Reject new jobs when the configured capacity is full.
Do not count a capacity rejection against the user rate limit.

## Consequences

The bot accepts new Telegram updates while a worker processes a photo.
The default configuration protects the shared GPU services from concurrent bot calls.
An operator can increase the worker count after a load test.
The queue exists in one bot process.
The bot restores accepted jobs after a process restart.
The queue does not provide distributed coordination between multiple bot processes.
