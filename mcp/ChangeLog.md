# Change log

## 2026-10-19 — Six more producer maps

- Serve Burnier, Golubitskoe Estate, Chateau de Talu, AYA, Раевское and Имение Сикоры from the shared Web registry. The registry now has 25 maps and 1,203 products.
- Update the pinned registry and Active-ID coverage checks: 1,127 exact slugs, three verified aliases and 963 unavailable Active IDs.
- Keep the MCP bundle count separate from coverage of the 2,103-card Web snapshot. Keep the existing Active-ID link checks and response-size checks.
- Pass all 49 tests, the syntax checks and the SDK client demonstration on Node.js 26.4.0.

## 2026-10-19 — «Винный дневник» account tools (#65)

- With `CHTOZAVINO_ACCOUNT_TOKEN` (and optional `CHTOZAVINO_ACCOUNT_URL`) the server adds the read-only tools `get_my_profile` and `list_my_wines`. They call `https://chtozavino.ru/api/app/v1/*` with the bearer token: HTTPS only (loopback HTTP for tests), no redirects, 5 s timeout, 256 KiB limit.
- New error code `unauthorized` for a refused token; network errors, timeouts, 5xx, and 429 give `unavailable`. Catalog tools keep working.
- A malformed token stops the start with a sanitized message. Without a token the tool list and the server instructions are unchanged.
- `src/account.mjs`; 6 new tests with a loopback fake diary and a real SDK client (48 in total).
- Review fix: the 256 KiB answer limit applies while the body streams (and to `Content-Length`), so a large answer never reaches memory in full. 1 new test (49 in total).

## 2026-10-19

- Read the producer list from `webui/shared/data/product-line-index.json`. The Web UI now loads each map on demand, and `index.ts` holds lazy loaders.
  Read `webui/docs/plans/04_lazy-product-line-maps.md`.
- Stop startup when the index does not list exactly the map files or does not match the maps.
- Check that the index resolves every Active ID like the full maps.
- Pass 42 tests, the syntax checks, and the SDK client demonstration.
- Replace the six-node Abrau demo of `get_producer_line` with the verified product-line maps of 19 producers (#25).
  Read `docs/plans/03_mcp-producer-line-maps.md`.
- Read the map list from `webui/shared/data/product-line-maps/index.ts`.
  Validate the maps with the shared module `webui/shared/product-line-core.ts`.
- Return `status: ok` with `resolution` (`placed`, `alias`, or `unplaced`), the tiers, the groups, all nodes, and the current node.
  Producers without a map return unavailable.
- Return a node slug and a link only for an Active ID of this snapshot. Report `catalog_state` for every node.
- Add `product_line_maps_sha256` to the catalog metadata. The catalog `version` now covers the map files.
- Stop startup for a damaged registry, a missing map file, a renamed producer, or an invalid map.
- Name the product-line maps in the startup error message.
- Copy the map files into the test fixture. The damaged-source tests now fail for their own defect.
- Add the shared map paths to the CI trigger paths and the sparse checkout.
- Pass 40 tests, the syntax checks, and the SDK client demonstration with Node.js 22.19.0 and Node.js 26.4.0.
- The branch history kept a copy of the demo data in `mcp/src/abrau-demo.mjs` after the removal of `webui/shared/experiences.ts`. This change deletes the copy.

## 2026-10-18

- Pull the Node.js test image in a separate CI step with three attempts. Docker Hub pulls failed twice on the self-hosted runner.
- Rename the plan to `docs/plans/02_wine-catalog-mcp.md`. The number `01` belongs to the earlier `main` plan `01_im-core-package.md`.
- Fix the protocol test for Linux CI. The test started the server in the macOS-only `/private/tmp` directory. It now uses `os.tmpdir()`.
- Implement the read-only wine catalog MCP server for issue 25.
- Add five strict tools, a stdio entry point, and an independent catalog service.
- Verify 2,094 matcher IDs and expose 2,093 Active records for discovery.
- Keep exact IDs, source hashes, evidence labels, unknown fields, and inactive states.
- Reuse the existing six-node `ABRAU_LINE` mock with an explicit demo result.
- Record the required product-line replacement checklist in issue 25.
- Add approved audio manifest reading with record binding, byte checks, and path containment.
- Return unavailable when approved recordings are absent or fail checks.
- Add a real SDK client example, 28 tests, component documentation, and a focused CI workflow.
- Pass all 28 tests on macOS with Node.js 22.19.0 and Node.js 26.4.0.
- Pass JavaScript syntax checks and the SDK client demonstration.
- Preserve existing Web, matcher, bot, and workbench source behavior.

The current source snapshot is not a verified live production pairing.
Product-line output remains a mock until the map dependency merges.
Production audio assets, an interactive external-host run, and the Qwen conversation loop remain separate acceptance work.
The CI workflow is added. A hosted CI execution is not claimed by these local results.
