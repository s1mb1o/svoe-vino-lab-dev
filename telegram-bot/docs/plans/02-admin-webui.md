# Administration web interface plan

Date: 2026-09-26

Status: Superseded for production deployment by
[plan 06](06_matcher-match-endpoint.md). The interface remains active on production port
`28003`. The obsolete systemd assets were removed.

## Goal

Add a private administration web interface for the Telegram bot.
Run the interface as a separate FastAPI service on `gx10`.
Use the existing SQLite database as the shared source of state.

## Scope

1. Show aggregate request statistics.
2. Show a paginated user list.
3. Show a paginated recent request list.
4. Show one request with step timings, recognition data, quality data, and candidates.
5. Show moderation filter error reports.
6. Reset the current rate-limit window for one user.
7. Request safe retry processing for one eligible request.
8. Do not serve accepted or quarantine image files.

## Security

1. Require HTTP Basic authentication for every administration page and action.
2. Require at least 32 characters in `BOT_ADMIN_WEB_PASSWORD`.
3. Compare credentials with constant-time comparisons.
4. Limit failed authentication attempts by socket client address.
5. Restrict client addresses to configured CIDR networks.
6. Use only `127.0.0.1` and `::1` as the default allowed networks.
7. Require a process-local CSRF token for every state-changing form.
8. Add restrictive browser security headers.
9. Do not render image bytes or storage paths.
10. Do not permit retry for an unsafe request or a request with an incomplete moderation step.
11. Require a TLS proxy assertion before a non-loopback listener can start.

## Retry flow

1. The administrator selects retry for an eligible request.
2. The web service changes the status to `retry_requested` in one transaction.
3. The web service clears the old feedback and recognition result.
4. The web service preserves the old step timing rows.
5. The bot polls for `retry_requested` rows.
6. The bot claims one row with a compare-and-set update to `queued`.
7. The bot submits the request to the existing work queue.
8. The normal processing pipeline downloads and moderates the image again.
9. A bot restart restores a claimed request from the `queued` state.

## Historical deployment

This deployment procedure is no longer valid.
Production uses Docker Compose as specified in [plan 06](06_matcher-match-endpoint.md).

## Verification

1. Add repository tests for list, detail, retry, claim, and rate-limit reset behavior.
2. Add web tests for authentication, CIDR checks, CSRF checks, redaction, reset, and retry.
3. Add bot watcher tests.
4. Run `uv run ruff check .`.
5. Run `uv run pytest -q`.
6. Check the production health endpoint on `gx10`.
7. Check authenticated pages through the configured HTTPS proxy or secure tunnel.
