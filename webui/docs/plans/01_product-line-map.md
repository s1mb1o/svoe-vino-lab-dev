# Producer product-line map

Date: 2026-10-15
Base: `github/main` at `20a9903eb81d08af334079fca8281da10e359da5`.
Branch: `product-line-map`.
Status: Implemented and verified on 2026-10-16. The owner selected the grouped canvas design.
Read `../reviews/2026-10-15-product-line-map-resolution.md` for review decisions and validation.

## Requirements

The guide MUST use one JSON file for each producer.
The first file MUST cover the six Abrau-Durso sheets dated 2026-09-20.
The initial sheet subset MUST retain 14 groups and 52 unique products or package variants.
The catalog extension adds 21 products in five still-wine groups. The complete graph has 73 products in 19 groups.
The graph MUST retain products that have no `wine_slug`.
The map MUST show these products in gray. These products MUST remain selectable.
The map MUST show relative price positioning and premium tiers.
The map MUST label relative positioning as editorial guidance. It MUST NOT imply a quality score.
The map MUST NOT invent numeric prices. The source sheets contain no numeric prices.
The map MUST identify the source date. Missing catalog links refer to the saved source snapshot.

## Data model

The JSON MUST contain `schema_version`, `producer`, `scope`, `sources`, `price_positioning`, `tiers`, `groups`, and `products`.
The producer MUST have a stable ID, name, aliases, and slug prefixes.
Each group MUST reference one tier.
Each product MUST reference one group through `group_id`.
The renderer MUST derive containment edges from these references.
Each product MUST have a stable ID, name, variant, local image, style, description, source IDs, and nullable `wine_slug`.
Each product MAY have explicit `wine_slug_aliases`.
An alias MUST refer to the same product. An alias MUST NOT merge kosher variants or distinct packages.
Catalog availability MUST derive from `wine_slug`. Release status MUST remain separate.
The validator MUST reject duplicate IDs, ambiguous slugs, broken references, and unsafe source or asset URLs.

## Interaction

The canvas MUST show groups in premium bands.
A group control MUST expand the products in that group.
On opening, an exact recognized slug or verified alias MUST select its product.
The map MUST expand the selected group and center the selected product.
The recognized marker MUST remain distinct from the current selection.
A locate control MUST return to the recognized product.
An unmatched product of a known producer MUST use a separate selected card. It MUST NOT receive an invented tier.
An unsupported producer MUST show an explicit unavailable state.
Desktop MUST show the selected product card beside the canvas.
At widths up to 767 px, mobile MUST show product details in a centered modal popup.
The initial product MUST remain selected and centered. The popup MUST stay closed on map entry.
A product tap or the «О выбранном вине» control MUST open the popup.
The popup MUST show the complete description without a separate expansion step.
The popup MUST support its close control, Escape, backdrop, and «Вернуться к карте».
Closing the popup MUST preserve the selected product, scale, and canvas position.
Closing the popup MUST restore focus to the opener. It MUST NOT close the parent map or shelf dialog.
The popup MUST retain keyboard focus and fit the available viewport height.
At widths of 768 px or more, the details MUST use the desktop side card.
A card MUST provide a return control that preserves the canvas position and scale.
A portal link MUST exist only when the product has a verified `wine_slug`.
The link MUST use `https://vino-svoe.ru/wines/` and the encoded slug.
The canvas MUST support native touch scrolling, mouse dragging, zoom controls, and keyboard access.
Zoom MUST resize the scroll surface. The viewport MUST retain its size.
The native dialog MUST retain focus, Escape, close, and backdrop behavior.
The guide MUST support the existing light and dark themes.

## Integration

The implementation MUST remain in `webui`.
The scanner prediction contract MUST remain unchanged.
The component MUST accept the actual result from single-bottle and shelf recognition.
A noindex `/lineup/abrau-durso` route MAY expose the same map for manual review.
The route MAY select a product through a `wine` query parameter.
The preview MUST NOT describe this query selection as recognition.
Other result experiences MUST retain their behavior.

## Validation

Check all graph references, aliases, counts, local images, and link rules.
Test exact recognition, alias recognition, unknown products, and unsupported producers.
Test gray product selection, portal links, return behavior, and repeated opening.
Test mouse pan, touch pan, zoom, focus, Escape, and narrow screens.
Run unit tests, type checks, and a production build.
Check the browser in light and dark themes at desktop and mobile widths.
Use Claude Opus 5.5 with effort `max` to review the plan and final implementation.
Record the review findings and their resolution.
Leave the local review server running on a registered free port.

## Design decision

The options were grouped nodes and a flat canvas with every product.
The owner selected grouped nodes with a desktop side card.
On 2026-10-16, the owner replaced the mobile bottom card with a popup widget.
Grouping reduces the initial number of visible products.
A neutral formats section avoids unsupported price comparisons between bottles, cans, and alcohol-free drinks.
The implementation uses native scroll surfaces and Vue components. It does not need a new graph dependency.

## Image framing extension, 2026-10-16

Each image MAY contain a measured `frame` rectangle and source dimensions.
The renderer MUST size the visible frame consistently across products.
The renderer MUST retain source aspect ratio and keep the complete visible outline.
Read `../product-image-sizing.md` for the contract and measurement method.

## Catalog completion, 2026-10-16

Include every identified Abrau-Durso card from `official-2026-09-17`.
Retain the original sheet products, aliases, gray packages and image bytes.
Add Abrau-Durso still wines, Abrau Estates, Abrau blends, Az Abrau and Femme d’Abrau.
Use the exact source descriptions, names and grape values. Keep separate catalog identities separate.
Use official collection evidence for premium and medium positioning. Keep unsupported common price ranks neutral.
Do not change numeric prices or infer alcohol and vintage from slug suffixes.
The owner explicitly excluded `rozovoe-polusladkoe-2` until exact bottle and collection identification.
The resulting map covers 56 of 57 snapshot cards. The excluded card keeps the unmatched recognition fallback.
Validate exact initial selection and centering for every new slug on desktop and mobile.
Validate the mobile popup, portal link, return state, all source images and the original Abrau regression suite.
Read `../product-line-maps/abrau-durso/sources.md` for evidence and image preparation.
