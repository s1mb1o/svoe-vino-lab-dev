# Wine catalog MCP implementation

Date: 2026-10-18.
Issue: https://github.com/s1mb1o/svoe-vino-lab-dev/issues/25.
Branch: `feature/mcp`.
Base: `950348759e9ce731a6acab4eb2d7b188fc874624`.
Status: Implemented. Read `../../mcp/ChangeLog.md` for actual checks and remaining dependencies.

## Scope and decisions

Implement a read-only local MCP server with five tools.
Use the official TypeScript SDK through its JavaScript exports.
Use Node.js 22.19 or newer for native TypeScript imports.
Pin server and client packages at 2.3.1. Pin Zod at 4.6.7.
Use `stdio`. Do not allocate a port or start a network service.
Keep the Web scanner and its evaluator contract unchanged.
Keep the catalog service independent of MCP so a later Web or Qwen adapter can reuse it.
Do not add a second taste calculator.
Do not implement the Qwen conversation loop in this issue.

The owner explicitly requests the current product-line mock.
Import `ABRAU_LINE` from `webui/shared/experiences.ts`.
Do not copy the data or merge the product-line branch.
Return `status: demo` and a replacement notice for this mock.
Return `unavailable` for another producer. Do not assign Abrau to that producer.
Record the replacement task in issue 25.

## Catalog domain

Read the checked-in matcher bundle and its `wines.jsonl` checksum from `manifest.json`.
Read descriptions and current states from `workbench/db-export/rows/wine_catalog.jsonl`.
Join only exact IDs. Fail startup for a missing bundle row, duplicate ID, or invalid checksum.
The current bundle contains 2,094 IDs. The joined export marks one ID as Removed.
Keep this ID resolvable with its state. Exclude non-Active IDs from discovery.
Do not add lab-only IDs or make up aliases.
Expose catalog and matcher versions and hashes without internal configuration or local paths.
Do not expose the full matcher manifest. It contains internal service settings.

Use the bundle fields as the identity source.
Read optional metadata from the existing Web fixture and its provenance only for the same exact ID.
Do not claim that the 12 Web fixture records form the whole catalog.
Distinguish structured source fields, explicit name text, and missing fields.
Sweetness MAY use an explicit sweetness term in the source name with `source_name` evidence.
Do not estimate sweetness from grape, region, color, or a missing term.
Do not extract vintage, price, oak, or quality from a name or map tier.
Food filters require source pairing categories. Do not infer a recipe from a category.
Describe the default source as the checked-in snapshot. Do not claim that a live production index was checked.

## Tool contract

All tools use strict input schemas and bounded output schemas.
All results include the catalog version and the data policy.
Application errors use `isError` and a stable code: `invalid_arguments`, `unknown_wine`, or `unavailable`.
The SDK returns standard tool validation errors for malformed input schemas.
Insufficient comparison evidence and unavailable optional content use explicit result states.

| Tool | Input | Result |
| --- | --- | --- |
| `get_wine` | One bounded exact `slug` | Known facts, unknown fields, sources, record hash, state |
| `find_wines` | Typed filters and `limit` from 1 to 10 | Deterministic matching cards, source-based reasons, supported filter values, coverage |
| `compare_wines` | Two or three distinct exact IDs | Known shared fields, differences, unknown fields, and source cards |
| `get_producer_line` | One exact ID | Six existing Abrau mock items with a demo label, or unavailable |
| `get_audio` | Exact ID and `summary`, `bottle_description`, or `story` | Approved durable recording metadata and transcript, or unavailable |

Use explicit color and sweetness enums.
Validate category, grape, region, and producer filters against the active catalog vocabulary.
Do not silently ignore an unsupported filter or an unknown key.
Comparison describes catalog facts. It does not claim a measured taste match.
Keep unknown values out of shared-fact statements.
Return a normal empty discovery result when valid filters have no intersection.

## Audio dependency

No production audio manifest exists on this base.
The default response is unavailable.
Support an optional operator-configured local approval manifest and audio directory.
Require an approved entry, matching wine record hash, transcript, content hash, and local MP3 bytes.
Verify the bytes and keep all paths inside the configured directory.
Construct media URLs from a trusted HTTPS base and the content hash.
Do not fetch URLs, invoke TTS, or generate a recording.
Do not disclose local paths in public results or errors.

## Implementation steps

1. Save this specification and record the mock replacement in issue 25.
2. Add a separate `mcp/` Node package and lock its dependencies.
3. Implement catalog loading, provenance, filtering, and fact comparison.
4. Add adapters for the shared product-line mock and optional approved audio.
5. Register five strict tools through the official SDK.
6. Add a Node CLI, graceful close behavior, and sanitized stderr errors.
7. Add a real SDK client demonstration and subprocess integration tests.
8. Add contract, data-boundary, and malformed-input tests.
9. Add component documentation, logs, smoke checks, and a focused CI workflow.
10. Run the checks. Record actual results and remaining dependencies in issue 25.

## Acceptance and regression checks

- Discover exactly five read-only tools through an SDK client over stdio.
- Read a wine outside the 12 fixtures.
- Confirm the complete bundle ID count and the Active discovery count.
- Reject an invalid checksum, a duplicate ID, and an incomplete source join.
- Exclude Removed wines from discovery and preserve their state in exact lookup.
- Check intersecting filters, unknown values, unknown keys, and limit bounds.
- Compare two or three exact IDs without inventing missing facts.
- Keep the Abrau mock labeled as demo, including an Abrau wine without a matching mock node.
- Return unavailable for another producer without returning an unrelated map.
- Read a synthetic approved audio fixture. Detect stale identity, missing bytes, bad hash, and path escape.
- Verify repeated calls through one real stdio connection.
- Verify that malformed calls do not prevent a later valid call.
- Verify that prompt-like catalog text cannot add tools or trigger a write or network request.
- Verify zero successful-server stderr errors and a valid protocol-only stdout stream.
- Verify the documented client example and clean startup from the lockfile.
- Keep all application source outside `mcp/` unchanged except a root documentation link and the new CI workflow.

## Remaining work

Replace the six-node product-line mock after the verified product-line implementation merges.
Retain exact membership, nullable slugs, source conflicts, and unsupported-producer states during that replacement.
Record a separate acceptance run for that integration.
Production audio requires reviewed assets and a trusted media host.
An end-to-end Qwen assistant needs its own validated function-calling loop.
These dependencies do not block the read-only MCP catalog core.
