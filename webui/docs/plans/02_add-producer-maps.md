# Additional producer maps

Date: 2026-10-16.
Status: Implemented. Read `../validation/producer-maps.md` for verification.

## Scope

Add Derbent Vino, Fanagoria, Kuban-Vino, Myskhako, Zolotaya Balka, Alma Valley, Inkerman, Massandra, Vedernikov, and Koktebel.
Use one JSON file per producer.
Reuse the existing grouped canvas, desktop details, and mobile popup.
The owner requested one separate commit per producer.
Put shared infrastructure in a separate commit.

## Data

Use all 562 catalog cards from the 2026-09-17 snapshot for the ten producers.
Use exact producer values and exact catalog slugs.
Keep different cards separate unless product equivalence is documented.
Do not infer alcohol, vintage, volume, or price from slug suffixes.
Group products by documented collection.
Use an explicit neutral group when collection evidence is incomplete.
Use official producer sources for collection descriptions and additional products.
Add verified products without a snapshot match with wine_slug null.
Record the evidence and matching limitation for each additional product.
Do not claim that the maps exhaust the live assortment.
Keep numeric prices null unless a dated source supports them.
Mark relative premium tiers as editorial guidance.
Retain catalog descriptions and grapes.
Ship existing local WebP assets when available.
Allow image null when no verified image is available.
Show a labeled placeholder for a null image. Do not use another product image.
Record per-producer provenance and a catalog crosswalk.

## Integration

Register JSON maps through explicit imports in `shared/data/product-line-maps/index.ts`.
Tests MUST require every producer JSON to appear in the registry.
Validate every graph and cross-producer slug identity.
Resolve exact slugs before producer aliases or prefixes.
Keep the recognition API unchanged.
Keep gray products selectable without a portal link.
Reset component state when the preview producer changes.
Add a producer selector to the preview route for direct review.
Keep noindex on preview routes.
Do not add a catalog to the scanner home page.

## Verification

Check every catalog slug, group relation, source reference, and shipped image.
Test collision rejection and exact lookup across producers.
Check routes, linked selection, gray selection, and portal links for every producer.
Check desktop and mobile in both themes.
Check mobile popup return, focus, map state, and preview producer navigation.
Retain the complete Abrau-Durso interaction regressions.
Run unit tests, type checks, and the production build.
Review the plan and implementation with the previously requested Claude Opus 5.5 Max.
Leave the existing local server on port 18553 running for review.
