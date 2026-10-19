# MCP smoke checks

Run commands from `mcp/`.

1. Run `npm ci --ignore-scripts` from the lockfile.
2. Run `npm run check`.
3. Run `npm test`.
4. Run `npm run demo`.
5. Confirm that the demo lists five read-only tools and two selected IDs.
6. Confirm catalog count 2,094 and Active count 2,093 for the current snapshot.
7. Confirm the producer-line result is `ok` with resolution `alias`. Confirm that audio is `unavailable` without approved assets.
8. Check one non-fixture card and a comparison in a compatible MCP host.
9. Create a token on `/account` → «Токены приложений». Set `CHTOZAVINO_ACCOUNT_TOKEN` in the host configuration. Confirm seven tools and that `get_my_profile` returns your username.
10. Revoke the token on the site. Confirm that the next `get_my_profile` call returns `unauthorized` and that the catalog tools still work.
11. Set a malformed token. Confirm exit code 1 and a stderr message without the value.
9. Check an unknown ID, an unknown region, and a limit of 11.
10. Confirm a valid call still works after a rejected call.
11. Close the client. Confirm that its server subprocess exits.

The automated suite covers damaged sources, source joins, inactive records, product-line map resolution, map registry defects, and audio integrity failures.
The automated SDK example does not replace a later interactive Qwen or external-host acceptance run.
