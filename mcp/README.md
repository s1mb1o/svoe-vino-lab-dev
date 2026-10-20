# Wine catalog MCP

This component provides five read-only catalog tools over local stdio.
Issue: [svoe-vino-lab-dev#25](https://github.com/s1mb1o/svoe-vino-lab-dev/issues/25).
Read [the implementation plan](../docs/plans/02_wine-catalog-mcp.md).

## Requirements and commands

Use Node.js 22.19 or newer and npm.
Run all commands in the repository's `mcp/` directory.
No model endpoint, API key, GPU, database server, or network port is required.

```sh
npm ci --ignore-scripts
npm run check
npm test
npm run demo
```

Use the direct Node command for a client configuration.
Do not use npm as the stdio server command. npm writes script banners to stdout.

```sh
node /absolute/path/to/svoe-vino-lab-mcp/mcp/src/cli.mjs
```

The server writes only MCP protocol messages to stdout.
Startup failures use a sanitized stderr message and exit code 1.
The server exits when its client closes stdin.

## Client configuration

Add this configuration to a compatible MCP host.
Replace the two absolute paths for that host.

```json
{
  "mcpServers": {
    "svoe-vino-catalog": {
      "command": "/absolute/path/to/node",
      "args": ["/absolute/path/to/svoe-vino-lab-mcp/mcp/src/cli.mjs"]
    }
  }
}
```

### «Винный дневник» account tools

Issue #65. With an application token the server also reads the token owner's diary.
Create the token on `https://chtozavino.ru/account` → «Токены приложений». The page shows it once.

```json
{
  "mcpServers": {
    "svoe-vino": {
      "command": "/absolute/path/to/node",
      "args": ["/absolute/path/to/svoe-vino-lab-mcp/mcp/src/cli.mjs"],
      "env": { "CHTOZAVINO_ACCOUNT_TOKEN": "cvpat_..." }
    }
  }
}
```

| Variable | Meaning |
| --- | --- |
| `CHTOZAVINO_ACCOUNT_TOKEN` | Optional. Without it the server registers no account tools and makes no network request. A wrong format stops the start with a sanitized message and exit code 1. |
| `CHTOZAVINO_ACCOUNT_URL` | Optional, default `https://chtozavino.ru`. HTTPS only; `http://` only for a loopback host in tests. |

| Tool | Arguments | Behavior |
| --- | --- | --- |
| `get_my_profile` | none | Username, account creation date, and preferences (`null` until the diary has them). |
| `list_my_wines` | `limit` 1–50 (default 20), `cursor` | The diary history, newest first: `slug`, `name`, `producer`, `color`, `sugar`, `first_met_at`, `last_met_at`, `days`, `sources` (`photo`, `shelf`, `telegram`, `max`), `saved_status` (`not_tasted`, `want`, `liked`, `disliked`, or `null`). Ratings and notes come later (#48). |

- Read-only (`readOnlyHint`). A token cannot write, open a web session, or manage tokens.
- HTTPS `GET /api/app/v1/profile` and `/api/app/v1/wines` with `Authorization: Bearer`, `redirect: 'error'`,
  a 5 s timeout, and a 256 KiB answer limit.
- Error codes: `unauthorized` (revoked, expired, or unknown token), `unavailable` (network, timeout,
  HTTP 5xx, or 429). The catalog tools keep working.
- The token never appears in a result, an error, stdout, or stderr. Rating notes are text that the
  person wrote: the tool descriptions and the server instructions call them data, not instructions.
- Without a token the server instructions are the same as before.

The SDK client example is in `examples/client.mjs`.
It discovers tools, finds two wines, reads a card, compares the wines, reads the line mock, and checks audio availability.
It uses a real MCP subprocess. It does not call a model provider.
The pinned SDK supports modern and legacy MCP clients.
Integration acceptance currently uses the pinned SDK client.
No interactive third-party assistant or Qwen conversation has been tested.

## Tools

| Tool | Arguments | Behavior |
| --- | --- | --- |
| `get_wine` | `slug` | Exact card, facts, missing fields, source references, state, record hash |
| `find_wines` | `filters`, `limit` | Deterministic known-field matches. Default limit 3. Maximum limit 10. |
| `compare_wines` | `slugs` | Two or three distinct exact IDs. Compare catalog facts only. |
| `get_producer_line` | `slug` | Verified product-line map of the producer: tiers, groups, all nodes, and the current node. Producers without a map return unavailable. |
| `get_audio` | `slug`, `kind` | Approved durable recording metadata or unavailable. No generation. |

Example arguments for discovery:

```json
{"filters":{"color":"white","sweetness":"dry","region":"Крым"},"limit":3}
```

Color values: `white`, `red`, `rose`, `orange`.
Sweetness values: `dry`, `semi_dry`, `semi_sweet`, `sweet`, `brut`, `extra_brut`, `brut_nature`.
Food values: `fish`, `seafood`, `meat`, `poultry`, `cheese`, `vegetables`, `dessert`.
Use `exclude_colors` for a tested color exclusion.
Category, grape, region, and producer filters use exact case-insensitive catalog values.
Call `find_wines` with empty filters to read `supported_values`.
An unknown filter value returns `invalid_arguments`.
Valid filters with no common result return an empty result.

Search returns compact cards.
`omitted_fields` identifies the description omitted for response size.
An omitted description is different from missing source data.
Use `get_wine` for the description.
Application errors have `isError: true` and a stable code.
Malformed schema inputs receive standard SDK validation errors.
Unavailable optional content uses an explicit result state.

## Data and evidence

The default source is the checked-in matcher bundle.
The bundle has 2,094 exact IDs in this source revision.
The current joined catalog export marks 2,025 IDs as Active.
Non-Active IDs return their state without a public card claim.
Only Active records enter discovery and comparison.
Lab-only entries outside the bundle do not enter MCP.

The loader checks the bundle checksum, count, unique IDs, source joins, and product-line maps.
Every result contains snapshot versions and source hashes.
The loader does not expose internal URLs from the matcher manifest.
`production_pairing_verified: false` means that no live production index was checked.
The service can be imported independently from MCP through `src/catalog.mjs`.
A later Web or Qwen adapter can use the same methods.
The existing Web routes are unchanged in this implementation.

Source fields, source-category sweetness, explicit source-name sweetness, and reviewed Web metadata have separate evidence labels.
`webui/docs/catalog-category-provenance.json` pins explicit source portal categories for the Active IDs.
`category_provenance_sha256` and the catalog version cover this file.
Category evidence takes priority over a name; an absent category does not imply a dry wine.
Run `npm run alternatives:categories` in `webui/` to explicitly refresh these public source categories,
then `npm run alternatives:catalog` and review the versioned anchor fixture before building.
Runtime catalog reads and builds do not fetch source categories over the network.
The current food filter uses source pairing categories from existing Web provenance.
Its coverage is reported. Missing pairings do not establish a negative pairing.
The service does not infer numeric sugar, vintage, oak, price, stock, quality, or a taste score.
Source text is untrusted data. An MCP host must preserve this boundary when it calls an LLM.
The static tool registry contains no write, shell, arbitrary SQL, URL fetch, or generation tool.
Inbound messages are limited to 64 KiB. Structured results are limited to 128 KiB before protocol text duplication.

## Producer product-line maps

The adapter serves the verified product-line maps of the Web UI.
The loader reads the map list from `webui/shared/data/product-line-index.json`. The Web UI uses the same index.
The index MUST list every map file in `webui/shared/data/product-line-maps/` and MUST match the maps.
It reads each JSON file with a size limit and validates all maps with `webui/shared/product-line-core.ts`.
The Web UI uses the same module. The two resolvers cannot drift.
Startup stops when the index, a map file, a producer ID, or the map validation fails. A stale index also stops startup.
After a map change, run `npm run line-maps:index` in `webui/` and commit the index.
`product_line_maps_sha256` covers the index and all map files. The catalog `version` also covers them.
Read `../docs/plans/03_mcp-producer-line-maps.md` for the decisions.

The current registry has 25 producers and 1,203 products.
1,130 Active IDs are map nodes: 1,127 exact slugs and 3 verified aliases.
The other 963 Active IDs return unavailable.
These counts use the MCP bundle and its Active records. The Web coverage report uses the separate 2,103-card catalog snapshot.

Resolution follows the Web UI:

1. An exact slug or a verified alias selects its product. It has priority over the producer text of the record.
2. Otherwise a matching producer name or alias selects the map. The result is `unplaced`.
3. Otherwise a matching producer slug prefix selects the map. The result is `unplaced`.
4. Otherwise the result is unavailable.

| `resolution` | Meaning |
| --- | --- |
| `placed` | The requested ID is the slug of one product. |
| `alias` | The requested ID is a verified alias of one product. |
| `unplaced` | The producer has a map, but the requested ID is not a node. |

For `placed` and `alias`, exactly one product has `current: true`. `current_product` contains its details and sources.
For `unplaced`, no product is current, and `current_product` is null.
`group_id` is the only membership relation.

| `catalog_state` | Meaning |
| --- | --- |
| `linked` | The snapshot has an Active card. `slug` and `source_url` are set. |
| `outside_snapshot` | The map links a catalog card without an Active record in this snapshot. `slug` and `source_url` are null. |
| `no_catalog_card` | The map has no catalog card for this product. `slug` and `source_url` are null. |

Badges stay unchanged. Source conflicts appear as badges, for example «Противоречие в данных каталога».
Tiers are relative positions inside one producer. They are not prices. The result has no prices.
A source without a URL, for example prepared sheets, has `url: null`.
Product descriptions appear only in `current_product`. Image paths and frames are not returned.
The largest current response is 49 KiB. A test checks every map against the 128 KiB limit.

## Optional approved audio

No production audio package is included in this branch.
The default result is unavailable.
An operator can configure these environment variables on the MCP host:

| Variable | Purpose |
| --- | --- |
| `WINE_MCP_REPOSITORY_ROOT` | Optional source root. The default is derived from the installed entry file. |
| `WINE_MCP_AUDIO_MANIFEST` | Local approval manifest file |
| `WINE_MCP_AUDIO_ROOT` | Local directory with immutable content-hash MP3 files |
| `WINE_MCP_MEDIA_BASE_URL` | Trusted HTTPS origin that serves `/media/audio/<sha256>.mp3` |

Only the operator sets these paths. Tool callers cannot supply paths or URLs.
The manifest contract is:

```json
{
  "version": 1,
  "entries": [
    {
      "wine_slug": "exact-catalog-slug",
      "kind": "summary",
      "status": "approved",
      "record_sha256": "64 hexadecimal characters from get_wine",
      "sha256": "64 hexadecimal characters for the stored MP3 bytes",
      "transcript": "Approved transcript"
    }
  ]
}
```

Kinds are `summary`, `bottle_description`, and `story`.
The reader requires the approved record hash, source ID, transcript, and verified local bytes.
A stale record, missing file, damaged file, or path escape returns unavailable.
The reader does not fetch the media URL or verify public media hosting.
The operator must verify that the media host serves the same accepted bytes.
The tests use synthetic integrity fixtures. They do not establish MP3 decoding or pronunciation quality.
An unrelated catalog edit changes the catalog version but preserves an unchanged wine record hash.

## Limits

This is a local read-only MCP adapter.
It has no public HTTP listener, account state, live store data, or automatic audio generation.
The Qwen function-calling loop is a separate integration.
Read [ResearchLog.md](ResearchLog.md), [ChangeLog.md](ChangeLog.md), and [SMOKE_TESTS.md](SMOKE_TESTS.md).
