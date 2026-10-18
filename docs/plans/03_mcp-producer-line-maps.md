# MCP producer-line maps

Date: 2026-10-19.
Issue: https://github.com/s1mb1o/svoe-vino-lab-dev/issues/25.
Branch: `product-line-map`.
Base: `github/main` `316d8da9`.
Status: Implemented on 2026-10-19. The owner approved option A for D1 to D6. Read `../../mcp/ChangeLog.md` for the checks.

## Problem

The branch `product-line-map` adds verified product-line maps for 19 producers to `webui/`.
Its first commit deletes `webui/shared/experiences.ts`.
On `main`, `mcp/src/catalog.mjs` imports `ABRAU_LINE` and `isAbrauWine` from that file.
After the rebase, the MCP server cannot start.
`npm test` in `mcp/` fails with `ERR_MODULE_NOT_FOUND`.
A push to `main` starts `mcp-tests.yml`, because the workflow watches the deleted file.

Plan `02_wine-catalog-mcp.md` requires this replacement after the map merges.
The replacement MUST keep exact membership, nullable slugs, source conflicts, and unsupported-producer states.
The owner chose the replacement on 2026-10-19.
This plan replaces the six-node demo with the real maps.
Plan 02 stays unchanged. It is a record.

## Measured facts

Measured on 2026-10-19 on the rebased branch.

- The registry has 19 maps with 1,046 products. 61 products have no catalog slug.
- The MCP catalog has 2,094 IDs. 980 IDs are map nodes: 977 exact slugs and 3 aliases. All 3 aliases are Abrau-Durso IDs.
- 1,114 IDs belong to producers without a map. No ID has a producer with a map and no node.
- 8 map slugs are not in the MCP catalog: Abrau-Durso 2, ESSE 1, Fanagoria 1, Zolotaya Balka 4.
- A compact map projection without product descriptions is at most about 46 KB (Fanagoria, 108 products). The largest map file is 183 KB. The server rejects results larger than 128 KiB.
- Tier price labels are relative, for example «Базовый ориентир · ₽». No product has a price.
- Source conflicts are product badges, for example «Противоречие в данных каталога».
- Node.js cannot import `webui/shared/product-line-map.ts`. Its JSON imports have no import attribute (`ERR_IMPORT_ATTRIBUTE_MISSING`). It also has a directory import and an extensionless runtime import.
- Node.js imports `webui/shared/catalog.ts`. The MCP server uses this module now.
- The MCP catalog allows a null producer. The website resolver expects a string.

## Decisions

The owner decides D1 to D6. The recommended option is first.

### D1. Shared resolution code

- **A (recommended).** Move the pure types and functions of `product-line-map.ts` to a new module `webui/shared/product-line-core.ts`. The new module has only type imports. `product-line-map.ts` keeps its public exports and binds the registered maps. The MCP imports the core module. The website and the MCP then use one resolver and one validator.
- **B.** Implement a separate resolver in `mcp/src/`. Do not change `webui/`. The two resolvers can drift.

### D2. Registry source

- **A (recommended).** Read the list of map files from the explicit imports in `webui/shared/data/product-line-maps/index.ts`. Stop startup when the list is empty or a file is missing. The MCP then serves exactly the maps that the website registers.
- **B.** Read every JSON file in the directory. A test compares the set with `index.ts`.

### D3. Exact ID against producer text

- **A (recommended).** Use the website rule: an exact slug or alias on a map has priority over the producer text of the catalog record. The current MCP test expects `unavailable` for this conflict. This test changes.
- **B.** Return `unavailable` when the producer text of the record conflicts with the map producer.

### D4. Map nodes outside the MCP catalog

- **A (recommended).** Return `slug: null` and no source link. Add `catalog_state` with the value `linked`, `outside_snapshot`, or `no_catalog_card`. Do not expose an ID that `get_wine` cannot read.
- **B.** Return the map slug and `in_snapshot: false`.

### D5. History of the branch

- **A (recommended).** Fold a shim into the first branch commit. The shim copies `ABRAU_LINE` and `isAbrauWine` without changes into `mcp/src/abrau-demo.mjs`. The MCP behavior stays identical. Every commit then keeps a working MCP server. Add one sentence to the commit message. The port commit at the tip deletes the shim.
- **B.** Add only the port at the tip. The 64 earlier commits keep the broken import.

### D6. Acceptance record in issue 25

- **A (recommended).** After the push, post the acceptance results as a comment on issue 25. Plan 02 requires a separate acceptance record for this integration.
- **B.** Record the results only in `mcp/ChangeLog.md`.

## Tool contract

The input stays `{ "slug": "<exact ID>" }`.
An unknown ID stays an `unknown_wine` error.
A producer without a map keeps the current `unavailable` result.
Other results have `status: ok` and these fields:

| Field | Content |
| --- | --- |
| `wine_slug` | The requested ID |
| `resolution` | `placed` (exact slug), `alias` (verified alias), or `unplaced` (the producer has a map, and the ID is not a node) |
| `producer` | `id`, `name` |
| `scope` | `label`, `as_of`, `catalog_snapshot` |
| `price_positioning` | `kind`, `currency`, `disclaimer` |
| `tiers` | `id`, `label`, `rank`, `price_label` |
| `groups` | `id`, `name`, `tier_id`, `method` |
| `products` | `id`, `group_id`, `name`, `variant`, `slug` (nullable), `catalog_state`, `release_status`, `badges`, `current`, `source_url` (nullable) |
| `current_product` | Null for `unplaced`. Otherwise the full node: the product fields, `category`, `style`, `grapes`, `description`, and its sources (`id`, `label`, `url`) |
| `note` | Fixed text: membership comes from the producer map, and tiers are relative positions, not prices |

Rules:

- For `placed` and `alias`, exactly one product has `current: true`. For `unplaced`, no product has it.
- `slug` is the product slug only when the MCP catalog has this exact ID. A null slug has no `source_url`.
- Keep all badges. Source conflicts stay visible.
- Do not return image paths, image frames, or product descriptions outside `current_product`.
- Do not return prices. The data policy stays unchanged.
- Remove `status: demo`, `mock`, `mock_slug`, `items`, `source`, and `replacement_issue`.
- Schema bounds MUST cover the current maxima with a margin. A test checks every map against the schema and the 128 KiB limit.
- Update the tool description and the server instructions. Remove the demo text.

## Implementation steps

1. Rebase the branch onto `github/main`. The new commit `316d8da9` changes only root documents.
2. D5: fold the shim into the first branch commit. Replay the other commits. Run the MCP tests on the amended first commit.
3. D1: add `product-line-core.ts`. Keep the public API of `product-line-map.ts`. Accept a null producer in the core. Use only erasable TypeScript syntax.
4. MCP: load and validate the registered maps in `CatalogService.load`. Use the existing bounded file reader. Implement the new `getProducerLine`. Replace the output schema. Delete the shim.
5. Tests: replace the two demo tests in `catalog.test.mjs`. Cover `placed`, `alias`, `unplaced` (synthetic record), `unavailable`, `outside_snapshot`, conflict badges, D3, the registry list, the coverage counts, and the size limit for every map. Update the protocol test and the client example.
6. Documents: update `mcp/README.md`, `mcp/CLAUDE.md`, `mcp/ChangeLog.md`, `mcp/ResearchLog.md`, `mcp/SMOKE_TESTS.md`, `webui/ChangeLog.md` (core module), and the push paths in `mcp-tests.yml`.
7. `ASSESSMENT.md`: write F-24 and F-48 again from the current code and tests. Keep the header. The root `ChangeLog.md` entry states that only F-24 and F-48 were checked again.
8. Checks: in `webui/`, run `npm test`, `npm run typecheck`, and `npm run build`. In `mcp/`, run `npm ci --ignore-scripts`, `npm run check`, `npm test`, and `npm run demo`.
9. Codex review with `gpt-6.1-sol` and `xhigh` reasoning: the port commits and the `ShelfScanner.vue` merge. Fix the findings and run the checks again. Stop and ask the owner when a finding needs a decision.
10. Fetch `github`. Confirm a fast-forward. Push `product-line-map` to `main`. Do not force-push.

## Acceptance checks

- The MCP server starts on every commit of the branch (D5 A).
- `get_producer_line` answers for all 980 map nodes. It returns `unavailable` for the other 1,114 IDs.
- The 3 alias IDs return `alias` and the product of the canonical slug.
- A synthetic Abrau-Durso record outside the map returns `unplaced` without a current product.
- The 8 outside-snapshot nodes have `slug: null`, no link, and `catalog_state: outside_snapshot`.
- The largest result is smaller than 128 KiB.
- The website tests, type check, and build pass. The public map API does not change.
- The pinned SDK client calls the tool over stdio and gets `status: ok`.

## Implementation notes

These details were found during the implementation.

- The README states that every result contains snapshot versions and source hashes. The catalog metadata therefore has `product_line_maps_sha256`, and the catalog `version` covers the registry and the map files.
- `linked` requires an Active record. An inactive ID has `catalog_state: outside_snapshot`. The component rules keep inactive IDs out of public card claims.
- One Abrau-Durso source (prepared sheets) has no URL. The result returns `url: null` for it.
- One product has an empty `variant`. The schema allows an empty variant.
- The CI job uses a sparse checkout. It now includes `webui/shared/product-line-core.ts` and `webui/shared/data/product-line-maps/`.
- The test fixture copies the map folder. Without it, the damaged-source tests would reject for the missing registry instead of their own defect.
- The former demo ID `abrau-dyurso-victor-dravigny-bryut` is a verified alias. The protocol test expects `resolution: alias`.

## Risks

- The core module changes a shared webui file. The webui tests and the production build guard the public API. The browser suites need a portal environment. They are not part of this plan.
- A larger future map can exceed the size limit. The size test fails first.
- The `index.ts` parser depends on the explicit import format. `webui/CLAUDE.md` requires this format. A test guards the parser.
- `main` can move before the push. Fetch again, rebase, and run the checks again.
