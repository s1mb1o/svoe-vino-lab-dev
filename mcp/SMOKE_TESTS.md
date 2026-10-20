# MCP smoke checks

Run commands from `mcp/`.

Use the [current completion checklist](README.md#completion-checklist--2026-10-20) to distinguish
implemented features, production rollout, pending acceptance, and future integrations.
The procedures below describe checks to run; the dated records describe checks already completed.

1. Run `npm ci --ignore-scripts` from the lockfile.
2. Run `npm run check`.
3. Run `npm test`.
4. Run `npm run demo`.
5. Confirm that the demo lists five read-only tools and two selected IDs.
6. Confirm catalog count 2,094 and Active count 2,025 for the current snapshot.
7. Confirm the producer-line result is `ok` with resolution `alias`. Confirm that audio is `unavailable` without approved assets.
8. Check one non-fixture card and a comparison in a compatible MCP host.
9. Create a token on `/account` → «Токены приложений». Set `CHTOZAVINO_ACCOUNT_TOKEN` in the host configuration. Confirm seven tools and that `get_my_profile` returns your username.
10. Keep the MCP connection open and revoke the token on the site. Confirm that the next calls to both `get_my_profile` and `list_my_wines` return `isError: true`, `status: error`, and `code: unauthorized`. Repeat both calls. Confirm `find_wines` still returns `status: ok` after revocation and in the repeat check, without restarting or reconnecting MCP.
11. Set a malformed token. Confirm exit code 1 and a stderr message without the value.
12. Check an unknown ID, an unknown region, and a limit of 11.
13. Confirm a valid call still works after a rejected call.
14. Close the client. Confirm that its server subprocess exits.

The automated suite covers damaged sources, source joins, inactive records, product-line map resolution, map registry defects, and audio integrity failures.
The automated SDK example does not replace a later interactive Qwen or external-host acceptance run.

The 2026-10-19 map expansion has 25 registered producers and 1,203 products.
The pinned Active-ID checks expect 1,074 exact map nodes, three aliases and 948 unavailable IDs.
The loader and schema checks cover every registered map, including the six new producers.

## Recorded live account check — 2026-10-20

A real SDK client connected over stdio to the local MCP server with an authorized account on
`https://chtozavino.ru`. The run used Node.js 26.4.0 and the pinned SDK at 2.3.1.

- Discover seven tools with `readOnlyHint: true`: passed.
- Read the profile with `get_my_profile`: passed; username and creation date returned, preferences null.
- Read all diary pages with `list_my_wines`: passed; 27 unique wines across two pages, newest first.
  The first request used `limit: 2`; the next used the returned cursor and `limit: 50`.
- Observe diary sources and saved status: `photo` and `shelf`; all 27 saved statuses null.
- Read the catalog with `find_wines` while account access is enabled: passed.
- Check server output: stderr empty; no token in the checked tool results or captured stderr.

The token was supplied in memory and was not saved to a file or configuration.
Production token revocation and interactive third-party assistant acceptance remain unchecked by this run.
The diary count is an observation at the check time, not a required count for future runs.
Read [ResearchLog.md](ResearchLog.md#2026-10-20--live-account-access) for the detailed record.

## Recorded production token revocation check — 2026-10-20

A later production check used a real SDK client over stdio, Node.js 26.4.0, and the pinned SDK at 2.3.1.
The client and server subprocess stayed connected throughout the check.

- Before revocation, `get_my_profile`, `list_my_wines` (`limit: 1`), and `find_wines` (`limit: 1`) returned `status: ok`.
- The signed-in account page on `https://chtozavino.ru` confirmed successful revocation of the selected application token.
- The next calls to both account tools returned `isError: true`, `status: error`, and `code: unauthorized`.
- A repeat check on the same connection returned the same errors for both account tools.
- `find_wines` returned `status: ok` after revocation and in the repeat check.
- Captured server stderr was empty. The checked tool results and stderr contained no token.

The token was supplied in memory and was not saved to a file or configuration.
No restart or reconnect was needed. Other tokens and diary entries were unchanged.
This result does not claim production deployment of schema 007 or interactive third-party assistant acceptance.
Read [ResearchLog.md](ResearchLog.md#2026-10-20--production-token-revocation) for the detailed record.

## Preferences and ratings acceptance

Local acceptance has passed as recorded below. Production acceptance remains open until the matching
account service and portal deployment is recorded and this procedure passes against production.

1. Record the target environment and deployed revision. Confirm account schema 007, the matching portal, and the MCP adapter are available there.
2. In account settings, save preferences, reload, and confirm that `get_my_profile` returns those exact choices.
3. Rate a history wine from 1 to 5 and add a tasting note. Confirm the same rating and `note` in `list_my_wines`.
4. Add a different private note to the saved wine. Confirm that this private note is absent from all MCP results.
5. Remove the wine from history. Confirm that `collection=rated` still returns the rating and tasting note.
6. Page through `rated` using its returned cursor. Confirm newest rating updates first and no duplicates.
7. Change the rating, clear the tasting note, delete the rating, and reset preferences. Confirm each change through MCP.
8. Confirm another account sees none of these values, and an application token cannot call owner write routes.

These checks use disposable accounts. Do not save a real application token or raw personal responses in the repository.

The 2026-10-20 local acceptance run passed in Chromium and WebKit through
`webui/scripts/check-account-taste.mjs`: actual account service, built portal, and real stdio MCP.
All 53 MCP tests also passed. These results do not claim a production deployment of schema 007.
