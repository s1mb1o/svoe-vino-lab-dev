# MCP research log

## 2026-10-20 — Production token revocation

A real SDK client connected to the local MCP server over stdio with an authorized production
application token. The run used Node.js 26.4.0, the pinned SDK packages at 2.3.1, and the production
account origin `https://chtozavino.ru`. The same client, server subprocess, and connection stayed open
through the checks before and after revocation.

The account owner authorized revocation. The signed-in production account page revoked the selected
application token and displayed a success confirmation. Other tokens and diary entries were unchanged.

| Tool | Before revocation | Next call after revocation | Repeat check |
| --- | --- | --- | --- |
| `get_my_profile` | `status: ok`; no tool error. | `isError: true`, `status: error`, `code: unauthorized`. | Same error. |
| `list_my_wines` (`limit: 1`) | `status: ok`; no tool error. | `isError: true`, `status: error`, `code: unauthorized`. | Same error. |
| `find_wines` (`limit: 1`) | `status: ok`; no tool error. | `status: ok`; no tool error. | Same successful result state. |

Both account reads lost access on their next call without restarting or reconnecting MCP.
The repeat check confirmed continued denial, while catalog access remained available.
These are observed MCP results; the probe did not capture the underlying HTTP response status.
Captured server stderr was empty. The checked tool results and stderr did not contain the token.
The token entered through stdin with terminal echo disabled and was passed to the subprocess in memory.
It was not saved to a file or configuration. This record omits token values, token names, account
identifiers, and raw personal responses.

This check establishes production token revocation. It does not establish production deployment of
schema 007 or acceptance through an interactive third-party assistant.

## 2026-10-20 — Preferences and rating contract

The account service stores stated preferences instead of returning a fixed null value.
Ratings and tasting notes have separate storage from history and saved wines, so deletion of either list
cannot erase a rating. The existing saved-wine notes remain private to the site.
The new tasting notes are explicitly shared with owner application tokens.
`list_my_wines` keeps its default history behavior and accepts `collection=rated` for all ratings.
That collection sorts by rating update and uses the existing bounded cursor; missing history dates are null.
The account API shortens long pages below 100 KiB; MCP validates a 128 KiB structured-output bound.
Local validation passes all 53 MCP tests. The built-portal check also passes in Chromium and WebKit:
actual account service, disposable SQLite, browser writes, and a real stdio MCP subprocess.
It verifies stored preferences, rating and note reads, private-note exclusion, rating survival after
history removal, account isolation, update, clearing, deletion, and preference reset.
Local validation uses disposable accounts and synthetic tokens. It does not establish deployment or a new
production-account check of the richer fields. The earlier live acceptance record below remains unchanged.


## 2026-10-20 — Live account access

At 22:11 MSK (19:11 UTC), a real SDK client connected to the local MCP server over stdio.
The run used Node.js 26.4.0 and the pinned MCP client and server packages at 2.3.1.
The account client used the default production origin, `https://chtozavino.ru`.
The account owner supplied the token. It entered through stdin with terminal echo disabled and
was passed to the MCP subprocess in memory through `CHTOZAVINO_ACCOUNT_TOKEN`.
No token was saved to a file or configuration. The record omits the username, account creation
timestamp, wine names, and raw account responses.

| Check | Observed result |
| --- | --- |
| Tool discovery | Seven tools; all advertised `readOnlyHint: true`. |
| `get_my_profile` | `status: ok`; username and creation timestamp returned; `preferences: null`. |
| `list_my_wines` | `status: ok`; 27 records with 27 unique slugs. |
| Pagination | First request used `limit: 2`; the next used the returned cursor and `limit: 50`. Two pages exhausted the history without duplicates or a repeated cursor. |
| Ordering | All records were ordered by `last_met_at`, newest first. |
| Diary fields | `slug`, `name`, `producer`, `color`, `sugar`, `first_met_at`, `last_met_at`, `days`, `sources`, and `saved_status` were present in the first item. Some descriptive values were null. |
| Sources and saved status | Observed sources were `photo` and `shelf`; all 27 records had `saved_status: null`. |
| Catalog access | `find_wines` with `limit: 1` still returned `status: ok`. |
| Output checks | Captured server stderr was empty. The checked tool results and captured stderr did not contain the token. |

Both production account endpoints worked with bearer authentication. The HTTP Basic blocker
described in the 2026-10-19 entry did not reproduce for these requests; the run did not inspect Caddy configuration.
The check read the profile and diary. It did not revoke the token or modify diary entries.
Production revocation, failure modes, and an interactive third-party assistant were not checked in this run.
The automated loopback tests cover refused tokens, service outages, and oversized responses separately.
The 27-record count describes this account at the check time; it is not a fixed acceptance expectation.

## 2026-10-19 — Six more producer maps

The expanded Web registry has 25 producers and 1,203 products.
The existing MCP loader reads all six new maps without a runtime change.
Of 2,093 Active bundle IDs, 1,127 resolve by exact slug and three resolve by verified alias. The other 963 IDs have no map.
The largest measured producer-line response is 50,126 bytes, below the 128 KiB limit.
These bundle counts differ from the Web report because the two sources have different exact IDs.

## 2026-10-19 — Account tools

- Transport: stdio only (issue #65, open decision 2, option A). The token stays in the client
  configuration. Hosted assistants need a remote MCP endpoint and usually the MCP OAuth flow; that
  is a separate issue.
- `chtozavino.ru` needs HTTP Basic for every path (#37). A `Bearer` token cannot pass HTTP Basic, so
  the tools work in production only after Caddy exempts `/api/app/*` (open decision 1, option A)
  and keeps the `Authorization` header for it. Until then use a loopback or LAN `CHTOZAVINO_ACCOUNT_URL`.
- End-to-end check on a local stack (account service, Nuxt, this server): a token from the page
  read the profile; after «Отозвать» the next call returned `unauthorized`; no log had the token.

## 2026-10-19

### Product-line map integration

Node.js cannot import `webui/shared/product-line-map.ts`.
Its JSON imports have no import attribute. Node.js stops with `ERR_IMPORT_ATTRIBUTE_MISSING`.
The module also has a directory import and an extensionless runtime import.
The Nuxt build needs these imports. Do not change them for the MCP server.
The pure functions now live in `webui/shared/product-line-core.ts` without runtime imports.
Node.js loads this module through native type stripping, like `webui/shared/catalog.ts`.

The 19 maps have 1,046 products. 61 products have no catalog slug.
980 of 2,094 bundle IDs are map nodes: 977 exact slugs and 3 aliases. All aliases are Abrau-Durso IDs.
No bundle ID has a mapped producer without a node.
8 map slugs are absent from the bundle: Abrau-Durso 2, ESSE 1, Fanagoria 1, Zolotaya Balka 4.
The former demo ID `abrau-dyurso-victor-dravigny-bryut` is a verified alias.
The former "other producer" test ID `avtohtonnoe-vino-kryma-beloe-suhoe` is now a node of the Valery Zakharyin map.

Full map files are up to 183 KB. A projection without product descriptions and images is at most about 46 KB.
With the current node and the envelope, the largest response is 49 KiB. The server limit is 128 KiB.
Tier price labels are relative, for example «Базовый ориентир · ₽». No product has a price.
Source conflicts are product badges. One Abrau-Durso source has no URL.

## 2026-10-18

### SDK decision

The official TypeScript SDK publishes the v2 server and client separately.
Use `@modelcontextprotocol/server` 2.3.1 and `@modelcontextprotocol/client` 2.3.1.
The npm metadata was checked before installation.
Zod 4.6.7 provides strict input and structured output schemas.
Use native Node TypeScript imports for the existing shared Web constants.
No TypeScript build pipeline is required for this small JavaScript package.

Primary source: https://github.com/modelcontextprotocol/typescript-sdk.
Inspector source: https://modelcontextprotocol.io/docs/tools/inspector.
Read the installed SDK types for actual transport and result behavior.
Do not implement the wire protocol manually.

### Data decision

The checked-in matcher bundle contains 2,094 exact IDs.
The source export contains additional lab entries.
Join by the matcher IDs. Do not publish every lab row.
One bundle ID is Removed in the export.
Return this state without asserting a public source card.
Use 2,093 Active IDs for discovery.
The default is a reproducible source snapshot. A live production index was not checked.

The bundle checksum is `cdd53eb8be5dbb8ffbeafda7513398551359c4bb9eedcffe82f249bf455abc70`.
The initial combined catalog version is `f9e85e3a0f8b9619d375be482bf6613bd9b729680a88ff11b6e21e0b504ba388`.
Existing Web provenance supplies optional pairings and serving fields for supported records.
Do not extend that limited coverage by generating facts.

### Mock decision

The owner requested the current product-line mock on 18 October.
Import the same `ABRAU_LINE` that the Web demo imports.
Mark its six nodes as demo.
Do not return it as the map of another producer.
Issue 25 contains the replacement checklist.
The verified product-line branch was not merged or copied by this task.

### Test interpretation

The integration test uses a real SDK client and a server subprocess over stdio.
The tests do not call Qwen or another model.
The prompt-like text test checks server data handling and the fixed tool boundary.
It does not prove that every external LLM host resists prompt injection.
Audio tests check approval, identity binding, byte integrity, and path containment.
They do not verify production hosting, decoding, voice quality, or accessibility playback.
These limits remain explicit in the component README.
