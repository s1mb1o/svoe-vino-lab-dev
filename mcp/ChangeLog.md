# Change log

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
