# Eight additional producer maps

Date: 2026-10-16.
Status: Implemented. Read ../validation/eight-producer-maps.md for verification.

## Scope

Add Soyuz-Vino, ESSE, Chateau Pinot, Valery Zakharyin, Novy Svet, Belbek, Sober Bash, and AGORA WINERY.
Include the 370 exact catalog identities from the 2026-09-17 snapshot.
Keep each producer in one JSON file.
Keep each producer in one separate commit.
Reuse the existing grouped canvas, desktop details, and mobile popup.

## Evidence

Pin each exact producer extract and the full snapshot checksum.
Preserve each catalog name, description, grapes, and wine_slug.
Keep separate cards separate. Do not infer product equivalence.
Use official collection pages for group descriptions and production methods.
Use relative editorial tiers. Keep numeric prices null.
Use a neutral tier when premium positioning is not supported.
Record additional official products with a null wine_slug and an absence check.
Keep archive products explicitly marked as archive products.
Do not claim complete coverage of the live assortment.

## Images

Ship a verified product image for every node.
Preserve existing transparent image content.
Use the built-in imagegen tool for opaque backgrounds.
Record input hashes, exact prompts, generated hashes, and output hashes.
Measure the final alpha outline and store image.frame.
Inspect all assets on light and dark surfaces.

## Acceptance

Verify exact snapshot coverage and absence of cross-producer collisions.
Verify image bytes, dimensions, alpha, frames, and provenance hashes.
Run unit tests, type checks, and a production build.
Run producer browser checks and the Abrau regression suite in Chromium and WebKit.
Check desktop and mobile views in both themes.
Keep the local server at port 18553 for owner review.
Update GitHub issue 2 with the completion evidence.

## External review

The owner approved the exact prepared packet on 2026-10-17.
Claude Opus 5.5 with effort max completed the review.
Confirmed findings were corrected and verified locally.
Read [the review resolution](../reviews/2026-10-17-eight-producer-maps-resolution.md).
The revised eight maps have 81 groups. Product and catalog coverage counts remain unchanged.
