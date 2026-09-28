# Failure analysis of `barcode-rerank-siglip2-512-crop-my`

Date: 2026-09-27

Run: `2026-09-26T213857Z-lab-barcode-rerank-siglip2-512-crop-my`

## Scope

The URL opened the `after_5` filter. This filter contains 49 positive query photos.
It does not contain all run errors.

The complete run contains 2,228 query photos. It has 1,644 positive photos and 584
negative photos. The final positive R@1 is 1,392 of 1,644, or 84.67%. The positive
R@5 is 97.02%. The positive R@10 is 97.81%. There are 252 positive R@1 misses and
90 known negative false matches.

All 49 visible failures returned HTTP 200 and ten candidates. No server error caused
these failures. No barcode lookup returned a wine for these 49 photos.

The 49 visible failures have this exact structural split:

| Structural cause | Photos | Share | Meaning |
| --- | ---: | ---: | --- |
| Expected wine has no usable `full` vector | 29 | 59.2% | Retrieval cannot return the expected wine. |
| Expected wine is at rank 6 to 9 | 13 | 26.5% | Retrieval found the wine, but the top-five reranker cannot inspect it. |
| Expected wine has a vector but is absent from top 10 | 7 | 14.3% | The photo or the visual ranking does not supply enough identity evidence. |

This split is exhaustive. The first group is the dominant cause.

## Validation method

The analysis used the saved `run.json`, `metrics.json`, `queries.jsonl`, and
`results.jsonl` files. It reconstructed the order before the VLM reranker. It joined
the active catalogue images to the fixed SigLIP2-512 index. It checked image SHA-256
values for duplicate labels. It inspected the query crop, expected reference, returned
reference, candidate scores, barcode trace, and VLM answers for each visible failure.

The following read-only counterfactual checks were also made:

- The expected wine is already in the top five for 203 of all 252 positive misses.
  This is 80.6% of the positive misses.
- The returned wine has the same producer as the expected wine for 236 of all 252
  positive misses. This is 93.7% of the positive misses.
- The returned wine has the same producer as the expected wine for 39 of the 49
  visible failures. This is 79.6% of the visible failures.
- The current cluster reranker gives 51 non-barcode wins and 10 losses. Its net effect
  is 41 additional positive R@1 hits. The 24 correct unique-barcode exits give the other
  deterministic wins. The reranker must not be removed.
- A blanket similarity-gap guard was replayed against this run. A `0.015` guard gave
  40 reranker wins and 5 losses. It reduced final R@1 from 84.67% to 84.31%. A blanket
  guard is not a valid fix.
- A prior guarded same-producer OCR reranker in `svoe-vino-matcher` gained 2.25
  percentage points with 46 wins and 10 losses. It is the strongest validated method
  for the dominant same-producer error family. It still needs a paired run here.

No new model inference was started. A concurrent benchmark owns the shared inference
services and forbids competing model calls. The new `full` plus `label` profile exists
in the current working tree, but no complete run result exists yet. This report does
not claim an accuracy gain for that profile.

## Why 29 items were impossible

The run catalogue reports 127 missing current items. The 29 query photos below expect
one of 13 wines that has no usable `full` row or `label` row in the run catalogue. This
was checked with both the current database and the database backup from before the run.
A reranker cannot recover a wine that does not enter retrieval.

The catalogue loader reported 2,051 wines with a full vector, but the database had
2,101 Active wines. The loader drops stale items and continues unless the complete
index has no current vectors. It reports the missing count, but it does not require a
full vector for every Active matchable wine. This behavior allowed the invalid run.

The fixed-512 index was built at 2026-09-26T11:55:57+0300. The active package-selection
rule and catalogue state changed after that build. The run used the new query package
rule, but it used old catalogue derivatives and vectors. This version skew made the
experiment invalid for these wines.

The query and catalogue also used different image operations. A query `segment` step
keeps the scene background because the query profile has no `remove_background` step.
The catalogue profile removes the background before it adds white. The benchmark
therefore compares background-inclusive query crops with isolated catalogue packages.
The next baseline must use one tested preprocessing contract on both sides.

| Query | Expected wine -> returned wine | Exact reason and item-specific evidence | Required action |
| --- | --- | --- | --- |
| `q-000270` | `agora-muskat` -> `agora-muskat-chernyj` | The expected wine has no `full` vector. The query has the expected light Muscat design, but only the dark sibling can compete. | Re-cut the active reference and rebuild the index. Then use label text for the sibling choice. |
| `q-000271` | `agora-muskat` -> `agora-muskat-chernyj` | Same missing-vector condition as `q-000270`. | Same action as `q-000270`. |
| `q-000272` | `agora-muskat` -> `agora-muskat-chernyj` | Same missing-vector condition as `q-000270`. | Same action as `q-000270`. |
| `q-000273` | `agora-muskat` -> `agora-muskat-chernyj` | Same missing-vector condition as `q-000270`. | Same action as `q-000270`. |
| `q-000485` | `aratti-shardone-beloe-suhoe` -> `aratti-sovinon-blan-beloe-polusuhoe` | The expected Chardonnay has no `full` vector. The returned Sauvignon uses the same package design. | Rebuild the vector. Use the label tower or OCR for the varietal text. |
| `q-000488` | `arie-vyderzhka-bochka-francziya-2020` -> `arie` | The expected 2020 card has no `full` vector. The query appearance also matches the generic `arie` card more closely than its current expected reference. | Rebuild the vector. Audit whether the photo is an alias of `arie` before scoring it as a separate SKU. |
| `q-000489` | `arie-vyderzhka-bochka-francziya-2020` -> `arie` | Same missing-vector and probable card-version ambiguity as `q-000488`. | Same action as `q-000488`. |
| `q-000542` | `b-yu-rne-krasnostop-suhoe-krasnoe-classic` -> `b-yu-rne-sira-krasnoe-suhoe-classic` | The expected Krasnostop has no `full` vector. The Syrah sibling has the same bottle and label design. | Rebuild the vector. Read the varietal text from the label. |
| `q-000543` | `b-yu-rne-krasnostop-suhoe-krasnoe-classic` -> `b-yu-rne-sira-krasnoe-suhoe-classic` | Same missing-vector condition as `q-000542`. | Same action as `q-000542`. |
| `q-000544` | `b-yu-rne-krasnostop-suhoe-krasnoe-classic` -> `b-yu-rne-sira-krasnoe-suhoe-classic` | Same missing-vector condition as `q-000542`. | Same action as `q-000542`. |
| `q-000563` | `balaklava-muskat` -> `balaklava-muskat-beloe-polusladkoe` | `balaklava-muskat` has no `full` vector. The same photo bytes are also a positive example of the returned slug. The current score is therefore a ground-truth conflict. | Create one alias group or remove the duplicate label. Rebuild the missing vector. |
| `q-000564` | `balaklava-muskat` -> `balaklava-bryut-rezerv` | `balaklava-muskat` has no `full` vector. The photo also has the same bytes as a positive example of `balaklava-muskat-beloe-polusladkoe`. The returned Brut is still wrong for both labels. | Fix the duplicate label, rebuild the vector, and use label text for the Balaklava siblings. |
| `q-000565` | `balaklava-muskat` -> `balaklava-bryut-rezerv` | Same missing-vector and duplicate-label condition as `q-000564`. | Same action as `q-000564`. |
| `q-000567` | `balaklava-muskat` -> `balaklava-muskat-beloe-polusladkoe` | The expected wine has no `full` vector. The returned slug is a byte-identical positive twin. | Create one alias group or remove the duplicate label. Rebuild the vector. |
| `q-000568` | `balaklava-muskat` -> `balaklava-muskat-beloe-polusladkoe` | Same missing-vector and positive-twin condition as `q-000567`. | Same action as `q-000567`. |
| `q-000569` | `balaklava-muskat` -> `balaklava-muskat-beloe-polusladkoe` | Same missing-vector and positive-twin condition as `q-000567`. | Same action as `q-000567`. |
| `q-000570` | `balaklava-pino-nuar` -> `balaklava-bryut-rezerv` | The expected Pinot Noir has no `full` vector. The returned wine uses the same black-and-gold Balaklava design. | Rebuild the vector. Read the product line and varietal from the label. |
| `q-000600` | `bryut-rozovoe-zolotaya-balka` -> `rozovoe-bryut-1` | The expected wine has no `full` vector. The same photo bytes are positive for the returned slug. | Merge the labels into an alias group or keep one canonical slug. Rebuild only after the label decision. |
| `q-001135` | `grand-jete-blanc-de-blancs` -> `grand-jete-rose` | The expected Blanc de Blancs has no `full` vector. The query label states Blanc de Blancs, but only its Rosé sibling can compete. | Rebuild the vector. Use the label crop and OCR text. |
| `q-001563` | `pozdnij-sbor-beloe` -> `vintazh-premium` | The expected late-harvest wine has no `full` vector. The current cards also need a product-version audit. | Rebuild the vector. Verify the card mapping. Then use label text. |
| `q-001564` | `pozdnij-sbor-beloe` -> `vintazh-premium` | Same missing-vector and card-mapping condition as `q-001563`. | Same action as `q-001563`. |
| `q-001581` | `risling` -> `vinodelnya-pokrovskaya-risling-pokrovskoe-risling-reynskiy-beloe-suhoe-13` | The expected generic Riesling has no `full` vector. Retrieval therefore selects another producer with the visible Riesling concept. | Rebuild the vector. Audit the generic card and use producer plus label text. |
| `q-001582` | `risling` -> `valeriy-zaharin-risling-valeriy-zaharin-risling-reynskiy-beloe-polusladkoe-125` | Same missing-vector condition as `q-001581`. | Same action as `q-001581`. |
| `q-001607` | `shardone-balaklava` -> `balaklava-bryut-rezerv` | The expected Chardonnay has no `full` vector. The returned sibling has the same Balaklava package design. | Rebuild the vector. Read the product text from the label. |
| `q-001609` | `shardone-balaklava` -> `balaklava-bryut-rezerv` | Same missing-vector condition as `q-001607`. | Same action as `q-001607`. |
| `q-001613` | `shato-pino-aligote-rkatsiteli-beloe-suhoe-12` -> `shato-pino-sovinon-blan-semilon-beloe-suhoe-115` | The expected blend has no `full` vector. The returned Shato Pino sibling has the same illustration style. | Rebuild the vector. Read the varietal blend from the label. |
| `q-002142` | `vysokij-bereg-risling-zelenaya-seriya-1` -> `vysokij-bereg-risling-zelenaya-seriya-2` | Series 1 has no `full` vector. The query visibly matches the current Series 1 reference, but only Series 2 can compete. | Rebuild the active Series 1 vector. Add an index-completeness gate before a run starts. |
| `q-002143` | `vysokij-bereg-risling-zelenaya-seriya-1` -> `vysokij-bereg-risling-zelenaya-seriya-2` | Same missing-vector condition as `q-002142`. | Same action as `q-002142`. |
| `q-002144` | `vysokij-bereg-risling-zelenaya-seriya-1` -> `vinodelnya-78-muskat-polusladkoe-muskat-ottonel-beloe-115` | Series 1 has no `full` vector. The photo shows the rear and side, so it also lacks the front-series design. Barcode did not return a wine. | Rebuild the vector. Add rear-label and barcode recovery. Ask for a front photo when both fail. |

## Why 13 items were outside the reranker window

These expected wines are in the candidate list at ranks 6 to 9. The current reranker
has `window: 5`. It can never promote these wines. Increasing the integer alone is not
enough. The rules also cover only 382 of 2,051 wines, and the rules come from the
NaFlex-p256 space while retrieval uses the fixed-512 space.

Across all 49 visible rows, 33 top candidates have no p256 rule. One top candidate has
a rule but no second rule member in the top five. Twelve rows trigger a rule for other
siblings while the expected wine stays outside that rule and the top five. Only three
rows put the expected wine in the triggered rule cluster, and all three expected wines
are outside the top-five window. The current reranker therefore cannot recover any of
the 49 visible rows.

| Query | Expected wine -> returned wine | Expected rank | Exact reason and item-specific evidence | Required action |
| --- | --- | ---: | --- | --- |
| `q-000209` | `abrau-dyurso-victor-dravigny-brut-shardone-beloe-bryut-12` -> `abrau-dyurso-victor-dravigny-bryut` | 9 | The full-package embedding prefers a near-identical Victor Dravigny sibling. Rank 9 is outside the VLM window. | Use the label tower and guarded same-producer OCR. Supply the top-ten producer group to the discriminator. |
| `q-000227` | `abrau-dyurso-victor-dravigny-bryut` -> `abrau-dyurso-victor-dravigny-brut-shardone-beloe-bryut-12` | 6 | The two cards differ mainly in small product text. Rank 6 is outside the VLM window. | Same action as `q-000209`. |
| `q-000229` | `abrau-dyurso-victor-dravigny-bryut` -> `abrau-dyurso-imperatorskoe-bryut-shardone-beloe-12` | 7 | Bottle geometry and Abrau design dominate the full vector. Rank 7 is outside the VLM window. | Use label retrieval, producer grouping, and OCR. |
| `q-000233` | `abrau-dyurso-victor-dravigny-bryut` -> `abrau-dyurso-victor-dravigny-brut-rose-pino-nuar-rozovoe-bryut-12` | 7 | Raw rank 1 was Victor Dravigny semi-sweet Sauvignon Blanc. The VLM saw `brut`, could not see colour, and scored both Rosé and Chardonnay at 2. Stable tie order promoted Rosé. The expected generic Brut at rank 7 was not inspected. | Include the top-ten same-producer group. Require colour or another discriminating field. Keep the order when the evidence is incomplete. |
| `q-000745` | `derbent-vino-di-kaspiko-shardone-beloe-suhoe-125` -> `derbent-vino-di-kaspiko-sovinon-sovinon-blan-beloe-suhoe-12` | 9 | The same Di Caspico design hides the small varietal difference from the full vector. Rank 9 is outside the VLM window. | Use label retrieval and varietal OCR within the producer group. |
| `q-000817` | `esse-brut-cuvee-prestige-shardone-beloe-ekstra-bryut-115` -> `esse-muskat-muskat-belyy-beloe-ekstra-bryut-115` | 7 | Raw rank 1 was Demi-sec Muscat Nectar. The VLM asked only for sugar level, read `brut`, and promoted Muscat at raw rank 2. The expected Cuvée Prestige at rank 7 was not inspected. | Add product-line and varietal evidence. Pass the top-ten Esse group. Do not let one sugar-level answer select the SKU. |
| `q-000818` | `esse-brut-cuvee-prestige-shardone-beloe-ekstra-bryut-115` -> `esse-muskat-muskat-belyy-beloe-ekstra-bryut-115` | 6 | Same rule and same wrong promotion as `q-000817`. The expected wine was at rank 6. | Same action as `q-000817`. |
| `q-001045` | `fanagoriya-primum-alveus-brut-2014-shardone-igristoe-bryut-beloe-12` -> `fanagoriya-primum-alveus-brut-2017-shardone-igristoe-bryut-beloe-12` | 8 | The query visibly shows the 2017 or Roman-VII design. The returned 2017 card matches that evidence. The expected 2014 label is probably wrong. | Verify the original photo. Reassign it to 2017 if confirmed. Do not tune the matcher against this label. |
| `q-001046` | `fanagoriya-primum-alveus-brut-2014-shardone-igristoe-bryut-beloe-12` -> `fanagoriya-primum-alveus-brut-2017-shardone-igristoe-bryut-beloe-12` | 7 | Same probable 2014-versus-2017 label defect as `q-001045`. | Same action as `q-001045`. |
| `q-001048` | `fanagoriya-primum-alveus-brut-2014-shardone-igristoe-bryut-beloe-12` -> `fanagoriya-primum-alveus-brut-2017-shardone-igristoe-bryut-beloe-12` | 6 | Same probable 2014-versus-2017 label defect as `q-001045`. | Same action as `q-001045`. |
| `q-001452` | `muskat-pozdnego-sbora-rozovyj` -> `massandra-muskat-rozovyy-pozdnego-sbora-rozovoe-sladkoe-10` | 9 | The same photo bytes are positive for both slugs. The returned slug is a valid positive twin. | Merge the labels into one alias group or keep one canonical slug. |
| `q-001627` | `shato-pino-exclusive-pino-nuar-merlo-krasnoe-suhoe-135` -> `vinodelnya-pokrovskaya-pokrovskoe-sladkoe-krasnoe-kaberne-sovinon-13` | 9 | The photo is a close rear-label view. The expected front appearance is absent. Rank 9 is outside the VLM window, and barcode returned no wine. | Add rear-label OCR and back-reference vectors. Ask for a front photo when identity remains ambiguous. |
| `q-002151` | `vysokij-bereg-risling-zelenaya-seriya-2` -> `vinodelnya-vedernikov-sibirkovyy-ekstra-bryut-beloe-117` | 7 | The photo shows the rear label. The full front design is absent. Rank 7 is outside the VLM window, and barcode returned no wine. | Same action as `q-001627`. |

## Why seven indexed items were absent from the top ten

These expected wines have a usable vector. Six rows are genuine photo-to-reference
retrieval failures. `q-001811` is a test-photo or ground-truth defect.

| Query | Expected wine -> returned wine | Exact reason and item-specific evidence | Required action |
| --- | --- | --- | --- |
| `q-000041` | `abrau-dyurso-abrau-kupazh-tyomnyy-suhoe-kaberne-sovinon-krasnoe-13` -> `vinodelnya-pokrovskaya-pokrovskoe-krasnoe-kaberne-sovinon-suhoe-14` | The photo shows the rear and side with an excise mark and barcode. It does not show the front identity. Barcode returned no code. | Add perspective-tolerant barcode and rear-label OCR. Return `need front photo` if both fail. |
| `q-000375` | `agrolayn-mountain-eagle-semillon-semilon-beloe-suhoe-11` -> `vinodelnya-78-muskat-polusladkoe-muskat-ottonel-beloe-115` | The photo is a rear-label view. The front reference has different visible evidence. Barcode returned no wine. | Add back-reference vectors and rear-label OCR. Add the same front-photo fallback. |
| `q-001638` | `shato-pino-kaberne-sovinon-krasnoe-suhoe-14` -> `vinodelnya-begildeeva-kaberne-sovinon-krasnoe-suhoe-14` | The photo shows the rear label. The model follows the visible Cabernet text and returns another producer. | Use producer and rear-label OCR. Do not use the package vector alone for rear views. |
| `q-001676` | `shato-pino-shiraz-krasnoe-suhoe-14` -> `abrau-dyurso-pino-nuar-krasnoe-suhoe-12` | The photo shows the rear label. The expected front design is absent. | Use rear-label OCR and back references. Ask for a front photo when confidence is low. |
| `q-001811` | `usadba-mezyb-usadba-mezyb-kaberne-fran-krasnoe-suhoe-145` -> `usadba-mezyb-vione-beloe-suhoe-118` | The foreground query bottle visibly states `ВИОНЬЕ`. The returned Viognier is correct. The expected Cabernet Franc is a test-photo or ground-truth defect. | Reassign the photo to the Viognier card after a manual check. Do not tune retrieval against the current expected label. |
| `q-001853` | `vaynkraft-kaberne-sovinon-krasnoe-suhoe-14` -> `mons-albus-kaberne-sovinon-krasnoe-suhoe-14` | The query and expected card share artwork, but the current expected reference is a weak crop. The full vector follows the same-varietal competitor. | Add a better active reference. Use label retrieval and producer OCR. |
| `q-002136` | `vinodelnya-zhakov-neoranzh-vostorg-beloe-suhoe-123` -> `vinodelnya-zhakov-fresherst-saperavi-krasnoe-suhoe-118` | Both wines use the same Zhakov illustration style. The package vector does not read the product text. | Use the label tower and guarded same-producer OCR. |

## Confirmed benchmark defects

Eight of the 49 rows have a byte-identical positive photo under more than one slug.
The affected rows are `q-000563`, `q-000564`, `q-000565`, `q-000567`, `q-000568`,
`q-000569`, `q-000600`, and `q-001452`. Six of these rows return the other valid
positive slug. Two return an unrelated sibling.

Across all 252 positive misses, 71 rows have a byte-identical positive photo under
more than one slug. Sixty-five rows return the other valid positive slug. An alias-aware
evaluation would change positive R@1 from 84.67% to 88.63% without a pipeline change.
This metric correction is necessary, but it is not a matcher improvement.

The three Primum Alveus rows are a separate probable label defect. The photos show
the 2017 design, but the test set expects 2014. The owner must verify the original
photos before these labels change.

`q-001811` is another product-label defect. Its visible bottle says Viognier, and the
pipeline returns the Viognier card, but the test set expects Cabernet Franc.

## Pareto order

The order below uses expected impact, confidence, implementation effort, and risk.
Counts overlap after the first item, so they must not be added.

| Order | Change | Evidence and expected reach | Acceptance condition |
| ---: | --- | --- | --- |
| 0 | Repair evaluation aliases and wrong product labels. | Eight of the 49 visible rows are confirmed duplicate-label conflicts. Across the complete run, 65 reported misses are another valid positive twin. `q-001811` visibly shows the returned Viognier, not the expected Cabernet Franc. Three visible 2014 rows probably show 2017. This work changes measurement, not product quality. | No identical photo is a conflicting single-positive example. Alias-aware metrics and canonical metrics are both reported. The product and year labels are manually verified. |
| 1 | Re-cut the active catalogue, rebuild the fixed-512 index, and block incomplete runs. | This makes 29 of 49 visible rows eligible for retrieval. The saved run reports 127 missing current items. Query preprocessing and catalogue preprocessing also use different revisions. | Every active wine that requires recognition has a current `full` vector. The run must fail its preflight if coverage is incomplete. The run manifest must record the config hash, preprocessing revision, index hash, dirty state, and source commit. |
| 2 | Port the guarded same-producer OCR difference reranker. | The returned wine has the correct producer for 236 of 252 positive misses. The expected wine is already in the top five for 203. A prior wine-disjoint implementation gained 2.25 percentage points with 46 wins and 10 losses. | Candidate grouping uses producer metadata and the full-plus-label top-ten union. A missing or contradictory OCR answer keeps the base order. Tune the score-gap guard on a development split. Report a wine-disjoint holdout. |
| 3 | Run and calibrate the new `full` plus `label` retrieval profile. | The failed run used only the `full` query view even though 2,047 catalogue label vectors existed. Most residual errors differ by small varietal, vintage, colour, or sugar text. Label-only retrieval previously reduced accuracy, so fusion is required. | Compare mean, weighted-score, and rank fusion on the same frozen index and test set. Keep the full tower. Define the missing-label policy. Accept only a paired R@1 gain with no material negative-set regression. |
| 4 | Replace cross-space cluster gating with same-space or metadata groups. Inspect the top-ten union. | Current rules cover only 382 of 2,051 wines. They were built in NaFlex-p256 space, while retrieval uses fixed-512. Thirteen visible expected wines are at ranks 6 to 9. Among all misses, 145 have no rule, 3 have no second rule member in top five, and 50 trigger a different pair while the truth stays outside it. | Build groups from the fixed-512 index or stable producer/card metadata. Validate each rule on held-out wines. Weak evidence keeps the base order. Do not only change `window: 5` to `window: 10`. |
| 5 | Complete deterministic code coverage and add a rear-view path. | Ten complete-run misses decoded a valid but unmapped code. Eight can become unique hits after verification. Two share one code and must constrain candidates. Seven visible rows are rear or side views. Exact decoder options and extra native, crop, upscale, grayscale, and contrast probes still found no valid code in four representative rear-view photos. | Verify every new code. A unique GTIN exits deterministically. A shared GTIN restricts candidates. Back-reference vectors and rear-label OCR handle rear views. Ambiguous photos return `need another photo`. |
| 6 | Calibrate an abstention result for unknown wines. | The run always returns a wine. It produces 90 known false matches on 584 negative photos. | Tune score, margin, producer, and OCR-consistency thresholds on a separate development set. Report positive recall and negative false-match rate together. |
| 7 | Repair diagnostics. | The step popup omits the recorded `cluster_rules` step. Final displayed scores also follow the moved positions, so they can hide the original cosine evidence. | Show base order, final order, original cosine, VLM questions, VLM answers, rule scores, index coverage, and alias conflicts for each query. |

## Recommended execution sequence

1. Freeze the active catalogue and test-set labels.
2. Resolve the eight confirmed alias conflicts and the three probable year errors.
3. Re-cut the active catalogue with one preprocessing revision.
4. Rebuild the fixed-512 full and label vectors.
5. Require complete index coverage before a benchmark starts.
6. Run the existing profile again. This run becomes the new valid baseline.
7. Run the current full-plus-label profile against the same baseline inputs.
8. Port and run the guarded same-producer OCR reranker.
9. Add same-space top-ten grouping and compare it with producer grouping.
10. Add code mappings, the rear-view path, and abstention.

The first valid comparison must occur after the index rebuild. A model comparison on
the current stale catalogue would measure index coverage and preprocessing skew instead
of matching quality.

## Evidence locations

- Run files: `runs/2026-09-26T213857Z-lab-barcode-rerank-siglip2-512-crop-my/`
- Retrieval and fusion: `pipeline/embedding_run.py`
- Cluster reranker: `pipeline/cluster_rerank.py`
- Barcode path: `pipeline/barcode.py`
- Current profiles: `config.yaml`
- Prior sibling OCR reranker: `../../svoe-vino-matcher/svm/pipelines/difference.py`
- Prior validation plan: `../../svoe-vino-matcher/docs/plans/02_sibling-difference-rerank.md`
