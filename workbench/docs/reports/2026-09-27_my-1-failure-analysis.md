# Failure analysis of `barcode-rerank-siglip2-512-crop-my-1`

Date: 2026-09-27

Run: `2026-09-27T070800Z-lab-barcode-rerank-siglip2-512-crop-my-1`

## Conclusion

The run did not have an HTTP, index, or latency failure. All 250 queries returned HTTP
200. The run completed in 20.6 seconds. The final R@1 is 30 of 250, or 12.00%.
The final R@5 is 92.00%. The final R@10 is 98.00%.

The 12.00% R@1 value is not a product-wide accuracy result. The `my-1` test set was
created from the R@1 misses of the earlier full `my` run. It is a hard-error test set.
The result means that the current pipeline recovered 30 of the previous misses. A new
full `my` run is necessary before a new product-wide R@1 value can be reported.

The reported 220 misses contain two different classes:

- 67 rows return another slug that is also a positive label for the exact same image
  bytes in the source test set. These rows are evaluation conflicts.
- 153 rows remain genuine matching misses after that alias credit.

An exact-byte alias-aware score is 97 of 250, or 38.80%. This value includes the 30
ordinary R@1 hits and the 67 alternate-valid hits. It is a measurement correction. It
is not a model improvement.

The genuine misses are mainly fine-grained sibling errors. Of the 153 genuine misses,
139 return a wine from the same producer. The expected wine is already in the top five
for 135 rows. It is in the top ten for 148 rows. Only five rows need a new retrieval or
data path.

## Scope and run health

The run has 250 positive queries and no negative queries. The source `my-1` set had 252
positive photos. The run omitted two photos of
`abrau-dyurso-victor-dravigny-brut-shardone-beloe-bryut-12` because that wine was no
longer Active when the run loaded its catalogue.

The complete result distribution is:

| Final state | Queries | Share |
| --- | ---: | ---: |
| Expected wine at rank 1 | 30 | 12.0% |
| Expected wine at rank 2 | 149 | 59.6% |
| Expected wine at rank 3 | 37 | 14.8% |
| Expected wine at rank 4 to 5 | 14 | 5.6% |
| Expected wine at rank 6 to 10 | 15 | 6.0% |
| Expected wine absent from top 10 | 5 | 2.0% |

All requests succeeded. The latency median is 248 ms. The p95 latency is 741 ms. The
maximum latency is 1,877 ms. All queries completed within three seconds. These values
come from four concurrent workers and warm caches. They do not represent a cold,
sequential user request.

The query package step used a SAM3 segment for 245 of the 250 rows. It used the crop
fallback for five rows. None of the five top-ten retrieval failures used the crop
fallback. The crop fallback is not the dominant cause.

## Exact failure accounting

The 220 reported R@1 misses have this final expected-rank distribution:

| Expected rank | Misses |
| ---: | ---: |
| 2 | 149 |
| 3 | 37 |
| 4 | 11 |
| 5 | 3 |
| 6 | 4 |
| 7 | 3 |
| 8 | 2 |
| 9 | 4 |
| 10 | 2 |
| Absent from top 10 | 5 |

This table shows that the embedding usually retrieves the correct family. It often
does not select the exact SKU. Two hundred of the 220 reported misses already contain
the expected wine in the top five. Two hundred and fifteen contain it in the top ten.

The score margins are also small. For the 215 misses with the expected wine in the
top ten, the median difference between the first score and the expected-wine score is
0.0143. The difference is at most 0.005 for 46 rows. It is at most 0.010 for 87 rows.
It is at most 0.020 for 132 rows. For rank-two misses, the median difference is 0.0106.

These values support a fine-grained discriminator for close candidates. They do not
support replacement of the base embedding model as the first action.

## Evaluation conflicts

The run has 84 queries whose exact image bytes have more than one positive slug in the
source `my` data. Seventy-eight of the 220 reported misses have this multi-truth
condition. In 67 rows, rank one is another positive slug for the same bytes.

The current benchmark accepts one slug as the expected answer. It loads variant groups
only to count `near_duplicate_confusion`. It does not use a variant group as a set of
valid positive answers. The run reports 31 near-duplicate confusions, but that metric
does not repair the primary R@1 score.

The current `my-1` data has 63 slugs in 28 variant groups. Some same-byte pairs are
duplicate catalogue cards. Other pairs can be valid product variants. These two cases
need different data actions:

- Merge duplicate catalogue cards into one canonical wine or one alias group.
- Keep real product variants as separate wines, but evaluate the specified group when
  the photo cannot identify one variant.
- Keep canonical-slug R@1 and group-aware R@1 as separate metrics.
- Do not train or tune a reranker against two contradictory single-positive labels.

One separate ground-truth defect is confirmed. Query `q-000222` expects
`usadba-mezyb-usadba-mezyb-kaberne-fran-krasnoe-suhoe-145`. The foreground bottle
visibly states `ВИОНЬЕ`. The returned
`usadba-mezyb-vione-beloe-suhoe-118` is consistent with the photo. The photo must be
reassigned after the normal manual check.

## Reranker behavior

The cluster reranker ran for 95 queries. It changed the first candidate for 23 queries.
It produced no new R@1 win on this hard set. It demoted ten raw-search R@1 answers.

This zero-win result has strong selection bias. The test set was created from the
misses of a previous run that already used this reranker. The complete earlier `my`
run gives 51 reranker wins and 10 losses. The net result is 41 additional R@1 hits.
The reranker must not be removed based on `my-1` alone.

Five of the ten apparent reranker losses return another exact-byte positive slug. The
benchmark therefore overstates the reranker damage. The ten affected queries are:

| Query | Failure mechanism | Required action |
| --- | --- | --- |
| `q-000001` | The rule asks about vintage. The VLM reads 2024 and demotes the raw correct answer. | Audit the rule, card version, and vintage mapping. |
| `q-000062`, `q-000063` | The VLM selects `aligote-avtorskoe-vino` instead of `aligote-avtorskoe`. The bytes are positive for both slugs. | Canonicalize the duplicate labels. |
| `q-000097`, `q-000098` | The VLM selects the `chteau` spelling instead of the `chateau` spelling. These cards are probable duplicate records. | Audit and merge the duplicate catalogue cards. |
| `q-000143` | The VLM reads rosé and semi-sweet evidence and moves the expected red semi-dry wine from rank 1 to rank 4. | Correct the rule or require stronger evidence. |
| `q-000157` | A volume rule selects an Inkerman Rkatsiteli slug instead of a Chardonnay slug. The bytes are positive for both slugs. | Repair the alias labels before rule tuning. |
| `q-000190` | The rule states that the labels are indistinguishable, but `verdict` mode forces the VLM to select one. The bytes are also positive for both slugs. | Keep the base order for an indistinguishable pair. |
| `q-000213` | A 2021 answer selects another Shato Taman Krasnostop slug. The bytes are positive for both slugs. | Repair the alias labels and audit the vintage rule. |
| `q-000219` | The rule states that the labels are indistinguishable, but `verdict` mode forces a choice. | Keep the base order or let the VLM abstain. |

There is a specific safety defect in the reranker. `pipeline/label_rules.py` selects
`mode="verdict"` when a rule has text but has no valid question. This can occur when
the rule also declares the pair indistinguishable. `pipeline/cluster_rerank.py` then
forces the VLM to select one candidate and moves it to the front.

The safe fix is explicit:

1. If all triggered candidates belong to one `indistinguishable` group, keep the base
   order.
2. Add an `abstain` or `keep_order` result to the verdict schema.
3. Require observable evidence before a candidate can move ahead of rank one.
4. Record the base order and final order in the result trace.

The current cluster rules were created in the NaFlex-p256 space. Retrieval uses the
fixed SigLIP2-512 space. Rebuild candidate groups in the same fixed-512 space, or use
stable producer and product-series metadata. Do not add a blanket similarity-gap
guard. A prior replay of a `0.015` guard reduced full-set R@1 from 84.67% to 84.31%.

## Barcode path

Ten queries decoded a code. Two queries found an exact `wine_code` entry and both
returned the correct wine. Eight decoded values had no matching row:

| Query | Decoded value |
| --- | --- |
| `q-000014` | EAN-13 `4607026344796` |
| `q-000028` | EAN-13 `4607026345076` |
| `q-000034`, `q-000038` | EAN-13 `5601016344987` |
| `q-000060` | EAN-13 `4640005350869` |
| `q-000125` | EAN-13 `4603040020586` |
| `q-000214` | QR URL `https://chateautamagne.ru/ru/catalog/wine/72` and EAN-13 `4607062863695` |
| `q-000224` | EAN-13 `4623721665622` |

Each code must be verified against the physical product before insertion. Queries
`q-000034` and `q-000038` use the same bytes and code under two expected slugs. This
code must map to an alias or variant group unless a manual check identifies one
canonical card. It must not map arbitrarily to one conflicting slug.

Verified mappings can make these queries deterministic. This is the simplest
high-confidence product improvement in this error set.

## Five expected wines absent from the top ten

Only five rows need retrieval beyond the present top ten:

| Query | Expected wine | Returned wine | Cause | Required action |
| --- | --- | --- | --- | --- |
| `q-000205` | `shato-pino-exclusive-pino-nuar-merlo-krasnoe-suhoe-135` | `agrolayn-mountain-eagle-semillon-semilon-beloe-suhoe-11` | The photo is a close rear-label view. The expected front design is absent. | Add rear-label vectors and OCR. Ask for a front photo if evidence stays weak. |
| `q-000206` | `shato-pino-kaberne-sovinon-krasnoe-suhoe-14` | `aratti-kaberne-sovinon-krasnoe-suhoe` | The photo is a rear-label view. Retrieval follows generic visible varietal text. | Add producer-aware rear-label OCR and rear references. |
| `q-000210` | `shato-pino-shiraz-krasnoe-suhoe-14` | `agrolayn-mountain-eagle-semillon-semilon-beloe-suhoe-11` | The photo is a rear-label view. The expected front design is absent. | Add the rear-view path and the front-photo fallback. |
| `q-000222` | `usadba-mezyb-usadba-mezyb-kaberne-fran-krasnoe-suhoe-145` | `usadba-mezyb-vione-beloe-suhoe-118` | The foreground bottle says `ВИОНЬЕ`. The expected label is wrong. | Reassign the test photo after a manual check. |
| `q-000225` | `vaynkraft-kaberne-sovinon-krasnoe-suhoe-14` | `mons-albus-kaberne-sovinon-krasnoe-suhoe-14` | The expected reference is a weak crop. A same-varietal competitor ranks first. | Add a better active reference. Use producer and label OCR. |

SAM3 produced a package segment for all five rows. Segmentation failure did not cause
these cases.

## Index condition

The fixed-512 index was rebuilt immediately before this run. It has 4,201 current
items, no stale item, and no missing indexed item in its recorded build state. It
reports 16 failed label-view items. Each failure means that the source has no label cut.
This profile searches the `full` view only. These 16 label failures do not cause the
current 220 R@1 misses.

The current database has 2,099 Active wines. The index has a current `full` row for
2,094 wines. Five Active wines have no full row:

- `polusladkoe-krasnoe-zb-vajn-frizzante`
- `polusladkoe-krasnoe-zolotaya-balka`
- `polusuhoe-rozovoe-zb-vajn-frizzante`
- `suhoe-beloe-zb-vajn-frizzante`
- `vibes-silvaner-barrel-fermented-2022`

None of these five wines is an expected answer in this run. Index incompleteness is
still a release risk, but it is not the cause of these 250 results.

## Label-space evidence

The existing `barcode-rerank-siglip2-512-crop-label` profile uses an uncalibrated mean
of the best full-view cosine and the best label-view cosine. On the complete `my` set,
it reduced R@1 from 1,392 of 1,644, or 84.67%, to 1,363 of 1,644, or 82.91%. It gained
51 rows and lost 80 rows. It also increased known-negative false matches by four.

The label query path is much slower in the saved runs. Its median was 1,800 ms and its
p95 was 3,030 ms. The reference full-view run had a median of 186 ms and a p95 of 552
ms. Cache states are not equal, so these latency values are not a controlled paired
comparison. They still show that label segmentation has a material cost.

Do not deploy the raw mean as a replacement for full-view retrieval. Use this design:

1. Keep the full-bottle tower as the first retrieval stage.
2. Trigger the label tower only for small margins and same-producer or same-series
   ambiguity.
3. Build the candidate union from both towers.
4. Calibrate the tower scores. Do not average raw cosine values.
5. Use label quality and OCR confidence as gates.
6. Keep the base order when the label evidence is missing or contradictory.

## Prioritized fix plan

The counts below overlap. Do not add them as independent gains.

| Order | Change | Evidence | Acceptance condition |
| ---: | --- | --- | --- |
| 0 | Repair aliases and wrong labels. | Sixty-seven reported misses return another exact-byte positive slug. `q-000222` has a confirmed wrong expected wine. | Report canonical R@1 and group-aware R@1. No exact image digest has contradictory single-positive labels. The hard-set group-aware R@1 starts from the verified 38.80% value. |
| 1 | Add verified GTIN and QR mappings. | Eight query rows decode a code but find no mapping. | A unique verified code returns one wine. A shared code restricts an alias or variant group. Every mapping records its evidence. |
| 2 | Make the reranker safe. | It demotes ten raw rank-one answers. Two rules explicitly say `indistinguishable` but still force a choice. | Indistinguishable groups keep the base order. The verdict can abstain. A no-evidence answer cannot move a candidate. Full-set paired results retain the current net reranker benefit. |
| 3 | Rebuild groups and rules in the fixed-512 space. | Current rules use another embedding space. Most genuine misses are same-producer fine-grained errors. | Group construction uses fixed-512 or stable catalogue metadata. Rules are checked on a wine-disjoint validation set. |
| 4 | Add a gated label and OCR discriminator. | The expected wine is in the top five for 135 of 153 genuine misses. The first-score margins are small. Naive mean fusion loses 29 full-set hits net. | The gate operates on low-margin same-producer candidates. It can keep the base order. A paired full `my` run improves R@1 without a material negative-set regression. |
| 5 | Inspect the same-producer top ten only when required. | Thirteen genuine misses have the expected wine at ranks 6 to 10. | The expanded window uses producer or series constraints. It does not pass an unrestricted top ten to the VLM. |
| 6 | Add a rear-view and weak-reference path. | Three top-ten absences are rear views. `q-000225` has a weak expected reference. | Store rear references. Use rear-label OCR. Return `need front photo` when evidence is insufficient. Replace weak catalogue references after review. |
| 7 | Complete full and label index coverage. | Five Active wines have no current full row. Sixteen label cuts are unavailable. These gaps did not cause this run, but they can invalidate other runs. | Every matchable Active wine has the required current view, or the build records an approved not-applicable reason. Benchmark preflight reports coverage. |

## Validation sequence

1. Freeze the current run artifacts and the source test set.
2. Resolve duplicate-digest labels and `q-000222`.
3. Verify the eight unresolved decoded-code rows.
4. Implement the reranker abstention and indistinguishable-group rule.
5. Rebuild the fixed-512 candidate groups and rules.
6. Run the complete `my` set and its negatives with the unchanged base profile.
7. Run the gated label and OCR discriminator on the same frozen inputs.
8. Report paired wins, paired losses, canonical R@1, group-aware R@1, R@5, R@10,
   negative false matches, and cold sequential latency.
9. Use `my-1` only as a diagnostic regression set. Do not use it as the only acceptance
   set because it was selected from prior errors.

## Evidence locations

- Run artifacts: `runs/2026-09-27T070800Z-lab-barcode-rerank-siglip2-512-crop-my-1/`
- Full reference run: `runs/2026-09-27T011711Z-lab-barcode-rerank-siglip2-512-crop-my/`
- Earlier full annotation source: `runs/2026-09-26T213857Z-lab-barcode-rerank-siglip2-512-crop-my/`
- Prior full-run failure analysis: `docs/reports/2026-09-27_after5-failure-analysis.md`
- Label-fusion analysis: `docs/reports/2026-09-27_label-fusion.md`
- Benchmark scoring: `pipeline/benchmark.py`
- Reranker gate: `pipeline/label_rules.py`
- Reranker reorder: `pipeline/cluster_rerank.py`
- Barcode path: `pipeline/barcode.py`
