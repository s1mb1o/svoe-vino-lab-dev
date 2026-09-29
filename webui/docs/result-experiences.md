# Result experience specification

Status: implemented and browser-verified on 2026-09-28.

## Scope

The portal MUST show a mandatory age confirmation before it shows the application.
The portal MUST show four follow-up actions after it resolves wine metadata.
The actions MUST use demonstration content by default.
The product-line action MAY use the resolved wine when its producer is `Абрау-Дюрсо`.
All four actions MUST run in the browser.
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

The result MUST show these actions:

1. `Подобрать блюда`.
2. `Рассказать об этикетке`.
3. `Паспорт вкуса`.
4. `Путеводитель по линейке`.

Each action MUST open one native dialog.
The dialog MUST close with its close control, Escape, and a backdrop click.
The dialog MUST return focus to the action that opened it.
Every dialog MUST identify demonstration content.
The product-line dialog MUST identify result-backed content when the resolved producer is `Абрау-Дюрсо`.

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

The dialog MUST show the grape varieties from the resolved wine metadata.
The dialog MUST use Syrah and Viognier as a fixed explanation example.
The copy MUST state that this example is not a claim about the recognized wine.
The copy MUST explain why variety information changes the expected wine style.

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

The dialog MUST show a map for `Абрау-Дюрсо`.
The map MUST place premium examples at the top and mass-market examples at the bottom.
The map MUST state that this placement is not a quality rating.
Each map node MUST show the selected `main` or `patched` catalog image for that wine.
The image selection MUST prefer `patched` when a patch exists for the wine slug.
The image selection MUST use `main` when a patch does not exist.
The map MUST use local image copies and MUST NOT request the catalog image at runtime.
The user MUST be able to zoom in and zoom out.
The application MUST detect `Абрау-Дюрсо` from the resolved producer or source slug.
When the resolved slug equals one map slug, the matching node MUST show `ВАШЕ ВИНО`.
The direction control MUST move that matching node into view.
When the producer matches but the map does not contain the resolved slug, the dialog MUST show the resolved wine separately.
The dialog MUST NOT assign an unverified collection tier to that separate wine.
When the producer does not match, the map MUST use the fixed demonstration node.
The fixed node MUST show `ПРИМЕР · ДЕМО` and MUST NOT call itself the user's wine.
A double click on a node MUST open its `vino-svoe.ru` page.
The selected node MUST also show a normal link for keyboard and touch users.

## Privacy and compliance

The result actions MUST not contain a purchase action for alcohol.
The result actions MUST not transfer a foreign critic score to a Russian wine.
The result actions MUST not copy a third-party tasting review.
The portal MUST retain the health warning in its footer.
