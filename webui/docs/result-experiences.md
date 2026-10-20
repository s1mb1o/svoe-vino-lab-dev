# Result experience specification

Status: Product-line guide updated on 2026-10-16. See `plans/01_product-line-map.md`.

## Scope

The portal MUST show a mandatory age confirmation before it shows the application.
The portal MUST show up to four follow-up actions after it resolves wine metadata. The label action is conditional on supplied metadata.
The food and taste actions retain their documented demonstration limits.
The label action uses the resolved wine metadata and the local reference dictionary.
The product-line action MUST use the verified local producer graph when a graph exists.
All available actions MUST run in the browser.
The actions MUST NOT call a retailer, geolocation, taste, recommendation, or product-line API.
The actions MAY use the resolved wine metadata in the browser.

## Age confirmation

The gate MUST ask whether the visitor is at least 18 years old.
The gate MUST block the application until the visitor confirms.
The application MUST remain in the server-rendered document while the gate is open.
The gate MUST use an overlay and MUST make the application controls inert.
The gate MUST NOT replace the primary page heading.
The confirmation MUST use the local storage key `svoe-vino.age-confirmed.v1`.
The value MUST be `yes`.
The portal MUST NOT store a birth date.
The negative action MUST show a blocked state.

## Result actions

The result MUST show these actions, with the label action hidden when all supported fields are empty:

1. `Подобрать блюда`.
2. `Рассказать об этикетке`.
3. `Паспорт вкуса`.
4. `Путеводитель по линейке`.

Each action MUST open one native dialog.
The dialog MUST close with its close control, Escape, and a backdrop click.
The dialog MUST return focus to the action that opened it.
Each demonstration dialog MUST identify demonstration content. The label guide identifies its term references instead.
The product-line dialog MUST identify its source snapshot.
The product-line dialog MUST distinguish recognized wines from preview selections.

## Dish demonstration

The dialog MUST show three named dishes.
The three dishes MUST belong to three different regional cuisines.
The dish set MUST cover Russian cuisine, cuisines of the peoples of Russia, and nearby Caucasus cuisines.
The inference MUST use the source pairing categories when the resolved wine contains them.
The inference MUST use the wine description, grape varieties, color, and category to fill gaps.
The inference MUST use sweet-wine rules before dry varietal analogues.
Each dish MUST explain the structural reason for the pairing.
Each dish MUST identify whether the source card or a style rule supports the result.
An illustrated dish MAY show a local editorial image.
The image MUST depict the named dish.
The image MUST have alternative text.
The UI MUST remain complete when a dish has no image.
The dialog MUST state that a recipe, sauce, and spice level can change the result.
The dialog MUST NOT request location or show a store.

## Label explanation

The dialog MUST show each grape variety from the resolved wine metadata with a linked reference note.
Multiple distinct varieties MUST receive separate notes and a short explanation of blending.
Aliases for one variety MUST NOT turn a single-variety wine into a blend.
The guide MUST explain sweetness from the explicit category, and region from the explicit region field.
It MAY explain a supplied alcohol value. Missing and placeholder fields MUST be hidden without a missing-data message.
If all supported fields are empty, the label action MUST be hidden.
The guide MUST preserve source values. It MUST NOT infer vintage, proportions, production method, geographical status or a variety's role from the wine name or slug.
Grape-style notes MUST describe a variety generally, separately from the supplied wine values.
An unrecognized supplied name MUST retain its value and a general term reference without invented variety-specific claims.
Every reference link MUST use an explicitly listed Russian publisher or scientific institution.
The guide MUST run locally without an LLM or a reference lookup request. Photograph OCR is outside this implementation.
Dictionary scope and source review are recorded in `label-guide-sources.md`.

## Taste passport

The dialog MUST show body, acidity, tannin, sweetness, fruit intensity, and oak influence.
Each dimension MUST use a five-level scale.
The sweetness dimension MUST use the source wine category.
The other dimensions MUST use deterministic rules over the resolved metadata and local dataset aggregates.
The resolved source description MUST take priority over a dataset aggregate.
The dataset aggregate MUST take priority over a generic style fallback.
The application MUST NOT contain a copied review or a critic score from the dataset.
The application MUST identify the dataset and its license in the taste passport.
The application MUST state when no reliable grape mapping is available.
The dialog MUST show aroma families from the source description.
The dialog MUST label each aroma family as source, dataset, or style evidence.
The dialog MUST show one international style analogue.
The analogue MUST use the grape variety, wine category, production method, or structural profile.
The analogue MUST compare style only.
The analogue MUST NOT compare quality, price, or critic rating.
The dialog MUST state that the result is an expected profile and not a tasting evaluation.

## Product-line guide

Read [the product-line map specification](plans/01_product-line-map.md).
Read [the product-line source record](product-line-map-sources.md).
The graph MUST use one JSON file per producer in `shared/data/product-line-maps/`.
The Abrau-Durso graph contains 14 groups and 52 products or package variants.
The graph uses the six sheets dated 2026-09-20.
Each product MUST have a stable ID. A product MAY have a null `wine_slug`.
Null-slug products MUST remain selectable. These products MUST appear gray.
Only a product with a `wine_slug` MUST show a portal link.
The guide MUST use local images. It MUST NOT fetch catalog images at runtime.
The guide MUST show relative premium and price positioning. It MUST NOT invent numeric prices.
The guide MUST state that positioning is not a quality rating.
Products without a comparable price basis MUST use a neutral formats section.
The guide MUST select and locate the recognized product when its exact slug or explicit alias is present.
The guide MUST retain separate recognized and selected states.
An unmatched product of a known producer MUST remain in a separate selected card.
The guide MUST NOT assign an unverified group to that product.
An unsupported producer MUST receive an explicit unavailable state.
The unavailable state MAY link to the separate Abrau-Durso preview.
The guide MUST support zoom, touch scrolling, mouse dragging, group navigation, and keyboard controls.
The guide MUST preserve canvas position when the user returns from a product card.
The guide MUST use a desktop side card and a centered mobile modal popup.
At widths up to 767 px, a product tap or «О выбранном вине» MUST open the popup.
The initial selection MUST remain visible on the map without an automatic popup.
Popup closure MUST preserve canvas state and restore focus. Parent dialogs MUST remain open.
The preview route MUST use noindex metadata and headers.
The preview route MUST NOT describe query selection as recognition.

## Privacy and compliance

The result actions MUST not contain a purchase action for alcohol.
The result actions MUST not transfer a foreign critic score to a Russian wine.
The result actions MUST not copy a third-party tasting review.
The portal MUST retain the health warning in its footer.
