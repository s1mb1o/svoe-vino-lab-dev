# Producer expansion plan review

Reviewer: Claude Opus 5.5, effort max.
Date: 2026-10-16.
Scope: Sanitized plan only. No tool access.

## Verdict: Changes required before implementation

The scope and data rules match the owner's request. However, the plan leaves five things undefined: fallback resolution, how the 562 cards are reproduced, equivalence handling, registry and commit order, and when maps go live. Each gap can cause silent wrong mappings or provenance that cannot be checked. Approve once the seven blocking items below are written into the plan. All fixes stay within the stated scope.

## Blocking

1. **Fallback resolution can bring back suffix inference (correctness).** "Exact first" still lets an alias or prefix fallback map an unseen slug, such as a different vintage or volume suffix, onto a near-match card. The Data rules forbid that inference. Producer prefixes are also likely ambiguous: a `derbent` prefix would also catch cards from Derbent brandy factories.
   - For the new producers, fallback may resolve only to the producer map, never to a preselected product. It may do so only when exactly one producer matches.
   - Validation must reject alias and prefix overlaps across all producers, including Abrau-Durso, not just identical slugs.
   - "Exact" means equal after the API's existing canonicalization. Add no new normalization.
   - Image lookup must use the exact slug only, never the fallback path.
   - Add a golden test that resolves every existing Abrau-Durso slug and alias input before and after the change. It must show identical results and an unchanged response shape.

2. **"All 562" cannot be reproduced (provenance and tests).**
   - Record the snapshot identity: file path and SHA-256 hash.
   - Record the exact producer-value strings assigned to each map, including spelling variants, legal-entity forms, and brand names used as producer values.
   - Record per-producer counts that sum to 562.
   - For each producer, test that the snapshot slugs and the map's linked slugs are the same set: none missing, extra, or duplicated.
   - Test that the retained name, producer value, description, and grapes exactly match the snapshot.
   - Tests must read the snapshot or a committed, hash-checked extract. They must not read the crosswalk they are meant to verify.
   - Cards that look misattributed in the catalog stay with their catalog producer. Record them; do not reassign them.

3. **Equivalence has no data representation (correctness).** Each node appears to hold a single `wine_slug`. Merging two equivalent cards would drop one slug from lookup and from the crosswalk.
   - The simplest option that follows the owner's rules is one node per card, with equivalence stored as metadata plus its source.
   - If merging is required, the infrastructure commit must define nodes with several slugs, which slug the portal link uses, and how each slug resolves.

4. **Registry and commit order (scope and tests).**
   - Automatic registration needs a strict filename pattern or schema check, so provenance and crosswalk files are never registered as maps.
   - Producer IDs must be unique, URL-safe, and stable.
   - The collision check must include Abrau-Durso, without migrating it to JSON.
   - Validation failures must fail tests and the build. They must not throw when the scanner loads the module.
   - The infrastructure commit lands first and passes with zero new producers.
   - Tests should be generated from the registry, and each producer commit should carry its own expected counts. Then every commit independently passes unit tests, type checks, the build, and the Abrau-Durso suite. Do not add a global 562 assertion that fails until the last commit.
   - Schema changes found later go into the infrastructure commit, not into producer commits.

5. **Release exposure is not stated (scope).** Automatic registration plus an unchanged recognition API likely makes each map reachable from scanner results as soon as its commit lands. State whether that is intended, or whether maps stay preview-only until review. Then test the chosen behavior. Also confirm:
   - No page built from the registry exposes preview routes. This includes the sitemap, navigation, and producer lists.
   - Every preview URL the producer selector generates is noindex.
   - The scanner home page's production bundle does not load full map JSON up front.

6. **Reused components were built for Abrau-Durso data (UX).** Add explicit checks for each case:
   - A null price never shows as 0, NaN, or a bare currency sign, and never breaks sorting or layout.
   - The existing image fallback shows the labeled placeholder for both null and missing (404) images. It never shows a default image or another product's image.
   - No reused text or count suggests the assortment is complete.
   - The "editorial" label on premium tiers appears on the canvas, in desktop details, and in the mobile popup.
   - Decide whether snapshot prices count as a dated source. Record the date with every price that is not null.

7. **Collection evidence is undefined (provenance).**
   - Define what counts as evidence. Options are an official listing of the product in the collection, a catalog field, and possibly a collection name that appears in the card title.
   - Record the evidence type for each product, not only for each producer.
   - The neutral group's label must read as "collection not confirmed", not as a real collection.
   - State the rule for products that appear in several collections.

## Should fix

- **Node identity:** Confirm that selection, list keys, relations, and URL state use a stable node ID that is unique within the producer, never `wine_slug`. Test selecting two different gray products one after the other.
- **Switching producers and focus:**
  - Reset component state on every producer route, not only the preview route.
  - Clear selection URL parameters and close any open popup.
  - Test switching producers with a gray product selected and the popup open. Then test back and forward navigation and an unknown producer ID.
  - The gray-product popup must not rely on the portal link for initial or return focus, and must not show an empty or disabled link.
- **Cards that look identical:** Cards that differ only by slug suffix will get identical labels. List them. Tell them apart only with structured catalog fields or a neutral card identifier.
- **Gray duplicates:** Flag any additional product whose normalized name matches a linked card from the same producer. Require a recorded note explaining why they are not the same product.
- **Images:** Assert that no image file is used by two products. Record how each shipped image was verified. Check that each image is present in the production build output.
- **Portal links:** Verify link construction offline against the snapshot. Treat live checks as spot checks only. Record dead links; do not point them somewhere else.
- **Scale:** Test the largest producer and the largest group, probably the neutral one, at mobile width in both themes. Include contrast for gray products and placeholders in dark mode. If the existing canvas cannot cope, raise it with the owner rather than redesigning it.
- **Port 18553:** The production build can overwrite the running server's output directory (for example a shared `.next` or `dist`) or leave it serving stale code. New JSON files may also need a restart.
  - Build to a separate output directory, or re-check the server afterwards.
  - If a restart cannot be avoided, get the owner's approval first.
