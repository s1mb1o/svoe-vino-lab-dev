# Administrator commands

Date: 2026-09-26

## Context

Public statistics must not show aggregate service data.
One administrator needs aggregate statistics and user management commands.
The administrator must reset a rate limit without deleting request history.

## Options

1. Use text commands with a configured Telegram user ID.
2. Use an inline administrator menu.
3. Add a separate web administration interface.

## Decision

Use text commands.
Authorize the administrator with the Telegram user ID.
Use `207286210` as the production administrator user ID.
Use `/users [page]` for a paginated user list.
Use `/reset_limit [user_id|@username]` for a rate reset.
Use the administrator user ID when `/reset_limit` has no argument.

Add a persistent `rate_limit_exempt` marker to a request.
A reset marks current-window requests as exempt from the rate limit.
The reset does not delete a request.

## Consequences

The administrator commands work in a private Telegram chat.
The bot rejects an administrator command in a group chat.
The administrator command menu has two additional commands.
A username lookup uses the most recent stored identity snapshot.
The Telegram user ID remains the stable authorization value.
