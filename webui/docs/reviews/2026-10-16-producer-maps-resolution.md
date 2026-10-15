# Producer map review resolution

Date: 2026-10-16.
Reviewer: Claude Opus 5.5 with effort max.

## Plan review

The reviewer received the plan without repository files.
The review identified data identity, provenance, registry, and rendering risks.
The implementation resolves exact product slugs before producer metadata.
A producer fallback returns an unplaced wine. It never selects a similar product.
Validation rejects cross-producer slug, name, and overlapping prefix collisions.
The existing Abrau aliases remain unchanged.

Each new catalog card has one product node.
Each producer has an independent catalog extract with exact slugs, names, descriptions, and grapes.
The extracts record the source path, producer value, expected count, and full source SHA-256.
Tests compare each map with its extract and with its separate crosswalk.
Each winery commit includes its own data, assets, provenance, and expected count.

The registry uses explicit JSON imports.
A test requires every map JSON to appear in the registry.
The prebuild command validates map data before Nuxt starts the production build.
Runtime validation remains as an invariant check for the existing module contract.
The code does not accept remote or user-authored maps at runtime.

Image null and image load failure both show the labeled placeholder.
The details card states that positioning is editorial.
Each source scope states that the map covers snapshot cards and verified additions.
All numeric prices remain null.
The crosswalk records collection evidence and ambiguous source fields.
Independent reviews checked the 33 official additions for false duplicates.

## Clarifications to plan-only findings

The existing Abrau implementation already used a JSON file and supported slug aliases.
No Abrau format migration was needed.
The user requested the same map integration as Abrau.
New maps are therefore available from recognized results and from the preview route.
The producer selector exists only on the noindex preview route.
The scanner home page retains its photo search flow.
The user already authorized the local preview server.
Restarting that server after a build stays within that authorization.

The static registry remains in the shared client module.
The production chunk is 762.74 kB before compression and 113.55 kB with gzip.
The build emits the existing Vite chunk-size advisory at the 500 kB threshold.
Per-producer asynchronous loading is a possible later performance change.
It is not required for identity correctness or the verified local interaction flows.

## Source corrections

The Derbent Endemy Bianca card has conflicting catalog color metadata.
Official evidence identifies a white brut. The map records that correction.
The shared Derbent collection page does not establish the method for Monte Garu.
The map therefore leaves the method unknown.
Two Myskhako cards have conflicting style metadata.
The map labels those conflicts and does not copy a current product blend onto an older snapshot card.
Descriptions and grapes remain equal to the snapshot.
