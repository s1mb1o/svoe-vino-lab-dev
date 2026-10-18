# MCP component instructions

Read the workspace instructions before work.
Read `README.md` and `../docs/plans/01_wine-catalog-mcp.md`.
Use short active sentences in technical documents.

Keep this component read-only.
Use the official pinned MCP SDK and the lockfile.
Keep catalog operations in `src/catalog.mjs` independent of the protocol adapter.
Keep stdout exclusive to the MCP protocol.
Never use a provider request for an optional-content fallback.
Keep the existing product-line mock explicitly marked as demo.
Replace the mock only after the owner accepts the merged product-line dependency.
Keep inactive IDs out of discovery and public card claims.
Do not expose raw matcher configuration or local paths.

Run `npm run check`, `npm test`, and `npm run demo` after changes.
Update ChangeLog, ResearchLog, and SMOKE_TESTS when behavior changes.
Do not commit node_modules, environment files, or generated media.
