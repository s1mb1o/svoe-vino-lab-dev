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
The production chunk is 763.86 kB before compression and 113.86 kB with gzip.
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

## Implementation review

The implementation reviewer had shared code, group data, official additions, and source notes.
The packet summarized the 562 linked records. It did not replace the actual map files.
The repository contains all linked records and the independent baseline files.
The reviewer did not run the application or tests.

1. Navigation groups: generic labels now use `Группа` and `Группы`.
   The group description stays visible when the group expands.
   The details card also shows the group description and its source caveats.
   A new group-kind field is unnecessary for this neutral UI contract.
2. Provenance: tests pin the full source SHA-256, exact producer names, and independent expected counts.
   Tests require exact gray-addition coverage and check every shipped image hash.
   `PRODUCT_LINE_CATALOG_SNAPSHOT` enables a full source-byte and source-row check.
   That check passed against all 2,103 snapshot records with no producer misattribution.
3. Koktebel tiles: each added product name now includes its identity and volume.
   Both `variant` values are empty. No other new map has a non-empty `variant`.
4. Gray labels: tiles say `Нет карточки`.
   The map header and availability message identify the portal and the snapshot date.
5. Alma Valley tiers: the two rank-1 tiers are one `core` tier.
   Validation rejects duplicate non-zero ranks and empty tiers.
6. Production methods: one visibility helper hides both unknown-method phrases.
   The details label says `Производство в группе`.
   A method for a mixed group is no longer presented as a product-specific method.
   The existing string schema remains compatible with the Abrau map.
7. Empty state: the text describes groups without a price rank.
   It does not assume that every producer has drinks or package formats.
8. Unsupported producer link: the explicit Abrau example link remains.
   That preview now has a selector for all eleven maps.
   The scanner home page does not become a producer catalog.
   This optional navigation change is not needed for supported producer resolution.
9. Early image failures: the component checks failed server-rendered images on mount.
   The browser regression delays JavaScript, returns an image 404, and checks recovery after hydration.
10. Producer selector: the native label is `Производитель`.
    Selection alone does not navigate. The user submits `Открыть карту`.
11. Browser tooling: reports are written on success and failure.
    Tests cycle between new producers and poll the completed route change.
    Mobile entry checks wait for the actual dialog element.

## Optional findings

Locantita stays attributed to Alma Valley only because the source snapshot assigns that producer.
The group description now makes that limit explicit.
Vedernikov's mixed core group states that some cards have no confirmed series.
The registry sort no longer mutates its input array.
Group counts use correct Russian plural forms.
The scanner integration and full-catalog resolver checks cover the suggested identity risks.
The nine missing images remain labeled placeholders.
The original source images remain unchanged.
Per-producer lazy loading and uniform image resampling remain possible performance work.
Unknown noindex preview routes retain the existing explanation and links to available maps.
Runtime validation remains an invariant check, with the build gate described above.
These optional changes do not block the verified local preview.
