# MCP component instructions

Read the workspace instructions before work.
Read `README.md`, `../docs/plans/02_wine-catalog-mcp.md`, and `../docs/plans/03_mcp-producer-line-maps.md`.
Use short active sentences in technical documents.

Keep this component read-only.
Use the official pinned MCP SDK and the lockfile.
Keep catalog operations in `src/catalog.mjs` independent of the protocol adapter.
Keep stdout exclusive to the MCP protocol.
Never use a provider request for an optional-content fallback.
Serve product-line maps only from the Web index `webui/shared/data/product-line-index.json` through `webui/shared/product-line-core.ts`. Do not copy map data.
Link only Active snapshot IDs from map nodes. A null slug has no source link.
Keep inactive IDs out of discovery and public card claims.
Do not expose raw matcher configuration or local paths.

Run `npm run check`, `npm test`, and `npm run demo` after changes.
Update ChangeLog, ResearchLog, and SMOKE_TESTS when behavior changes.
Do not commit node_modules, environment files, or generated media.
