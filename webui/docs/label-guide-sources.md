# Label guide — issue 57

The guide replaces the fixed Syrah/Viognier example with local references selected from the resolved wine's grapes, category and region. The optional alcohol section uses an explicit source value. Empty fields and placeholder strings produce no section or missing-data message. Source metadata and identifiers remain verbatim.

## Content and sources

`shared/label-reference.ts` contains short original paraphrases and an explicit source registry. References are limited to Russian publishers and institutions: Roskachestvo, AVVR, VINO.RU, Simple Wine News, the Magarach institute and journal, and the South Russian viticulture research journal. Sources were inspected on 20 October 2026. No third-party article or tasting review is reproduced in full.

The dictionary covers every grape in the twelve saved preview cards. It also includes common catalog grapes and exact aliases, with independently editable references for distinct varieties. The dictionary is finite: a new supplied grape or region keeps its source value and gets a general explanation of that field with a Russian reference. This fallback never invents origin, flavors or production methods. `LabelNote.specific` distinguishes this fallback for coverage checks; it is not a user-facing warning.

Grape notes describe varieties generally. Multiple named varieties get separate notes and an explanation of blending, without inferred proportions or assigned blending roles. Exact aliases such as Syrah/Shiraz and Pinot Noir/Pinot Black do not imply multiple varieties. Explicit source percentages remain visible; the guide does not generate any.

Sweetness comes only from an unambiguous category, never a name, slug, grape or aroma. Semi-dry still-wine copy explains slight sweetness and its balance with acidity. Explicit sparkling categories use the sparkling scale, including dry, semi-dry, extra dry and brut styles. Region notes provide geographical and wine-growing context without assigning a protected status to the bottle.

The dictionary is deterministic; it sends no metadata to a model or reference service. These notes are editorial explanations, not a tasting of the selected bottle. The user's preview feedback informed the copy; no independent human wine-editor sign-off is claimed. Photo OCR and fields absent from the current `Wine` contract remain outside this change.

## Validation

`tests/label.test.ts` checks multi-variety notes, all twelve preview cards, missing fields, alias deduplication, distinct muscat varieties, source percentages, explicit sweetness, region suffixes, safe unknown-value fallback, alcohol ranges and the publisher allowlist.

`scripts/check-label-browser.mjs` checks the real guide dialog, source links, selection, responsive layout and focus recovery. It also injects sparse and empty metadata through the existing preview endpoint to verify hiding behavior.

A scoped Claude Opus review covered the implementation and related tests. Its findings led to separate Krasnostop and Terek references, narrower sourced claims, punctuation and blend-list handling, separate sparkling sweetness copy, and accessibility corrections. Regression cases cover those changes. Source checks confirmed the Kokur and Bastardo claims in the Roskachestvo articles; the Bianca claim was reduced to white semi-dry blends. The AVVR standards list Pinot Franc as Pinot Noir and distinguish Gewurztraminer from Traminer Pink, so those aliases retain their documented identities.
