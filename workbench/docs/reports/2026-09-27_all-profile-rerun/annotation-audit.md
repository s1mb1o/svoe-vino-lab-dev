# Frozen annotation audit

Date: 2026-09-27. Scope: metadata only.
The raw baseline contains 2228 query rows and 1851 recorded image digests.
The labels contain 1644 positive rows and 584 negative constraints.
This audit changes no label, denominator, exclusion, or score.

The audit finds 67 digest groups with incompatible exact-slug positive constraints
under the same-bytes, same-answer assumption.
These groups contain 136 positive rows. They contain 70 disjoint positive-row pairs.
No positive truth slug is forbidden by a negative row in the same digest group.
These are constraint conflicts, not established annotation mistakes.

## Semantics and counts

A positive answer must belong to the row's complete `truth` list.
A negative row forbids its `slug`. It does not identify the correct wine.
Different positive truth lists are compatible when they retain a common accepted answer.
The full group is compatible only when all positive truth lists share an answer
that no negative row forbids.

All 1644 positive truth lists have one slug in this baseline.
All 584 negative truth lists are empty. The audit still uses set operations.

| Check | Count |
|---|---:|
| Digest groups with repeated rows | 266 |
| Rows in repeated-digest groups | 643 |
| Extra rows beyond one per digest | 377 |
| Groups with more than one positive row | 93 |
| Groups with empty total positive intersection | 67 |
| Groups with at least one disjoint positive pair | 67 |
| Groups where every positive-row pair is disjoint | 66 |
| Disjoint positive-row pairs | 70 |
| Empty total intersection but no disjoint pair | 0 |
| Different truth sets with a nonempty common intersection | 0 |
| Groups with positive and negative rows | 150 |
| Mixed groups whose constraints are jointly compatible | 135 |
| Direct positive/negative conflicting pairs | 0 |
| Positive rows excluded by combined negative constraints | 0 |
| Common positive answer removed by negative constraints | 0 |

An empty total intersection does not require a disjoint pair in general.
For example, `{A,B}`, `{B,C}`, and `{A,C}` overlap in every pair but share no common answer.
No such case occurs in this baseline.
Likewise, `{A,B}` and `{B,C}` differ but are compatible through `B`.
The audit does not classify that case as a conflict.

The group containing `q-000051`, `q-000052`, and `q-000057` has two equal positive truths
and one different truth. It contains disjoint pairs, but not every pair is disjoint.
This explains the difference between 67 conflicting groups and 66 groups where every pair is disjoint.

The conflicting groups also contain 19 negative rows across 15 mixed-label groups.
Those negative constraints do not exclude a positive truth in the same group.

| Conflicting group shape | Groups | Positive rows per group | Distinct accepted slugs | Maximum correct positive rows per group | Minimum misses per group |
|---|---:|---:|---:|---:|---:|
| Two different singleton truths | 65 | 2 | 2 | 1 | 1 |
| Two equal truths and one different truth | 1 | 3 | 2 | 2 | 1 |
| Three different singleton truths | 1 | 3 | 3 | 1 | 2 |

## Exact conflict groups

Every row below has an empty total positive-truth intersection.
The JSON stores full digests, paths, truth lists, negative constraints, and every conflicting pair.
The shortened digest in this table is an identifier only.

| Group | Digest prefix | Positive query IDs | Negative query IDs in the same group | Minimum positive misses under the stated assumptions |
|---|---|---|---|---:|
| C01 | `e682f356b9e59e1a` | `q-000012`, `q-000125`, `q-000133` | — | 2 |
| C02 | `eae9f5cef7e45b7c` | `q-000051`, `q-000052`, `q-000057` | `q-000066`, `q-000073` | 1 |
| C03 | `caba220e03d01cd9` | `q-000053`, `q-000058` | — | 1 |
| C04 | `5c5aa740e2be0ee5` | `q-000054`, `q-000059` | `q-000067` | 1 |
| C05 | `fce0a8590039635f` | `q-000065`, `q-000072` | — | 1 |
| C06 | `b36d05015ee10f28` | `q-000092`, `q-000197` | — | 1 |
| C07 | `ca5f33db7651ec29` | `q-000094`, `q-000196` | — | 1 |
| C08 | `d66258b61c9563e8` | `q-000107`, `q-000120` | — | 1 |
| C09 | `4ad7c1e449e17303` | `q-000109`, `q-000118` | — | 1 |
| C10 | `5e112980ebf22b51` | `q-000137`, `q-000141` | — | 1 |
| C11 | `ce40b292ad8b47cb` | `q-000183`, `q-000187` | — | 1 |
| C12 | `d345db79165a44ff` | `q-000184`, `q-000189` | — | 1 |
| C13 | `1402b200de200b00` | `q-000185`, `q-000190` | — | 1 |
| C14 | `4e2f06a7a8b54c7a` | `q-000195`, `q-000198` | — | 1 |
| C15 | `f47a2cdd591c982b` | `q-000323`, `q-000325` | — | 1 |
| C16 | `3b19b68c1bd764fd` | `q-000393`, `q-000398` | — | 1 |
| C17 | `079b561012212215` | `q-000394`, `q-000399` | — | 1 |
| C18 | `64c09146bcb360cd` | `q-000483`, `q-000484` | — | 1 |
| C19 | `6cd3823cec1bc77b` | `q-000556`, `q-000563` | — | 1 |
| C20 | `97f23e3c07874450` | `q-000557`, `q-000565` | — | 1 |
| C21 | `8d654091273f07ef` | `q-000558`, `q-000564` | — | 1 |
| C22 | `c8dd6840449fddea` | `q-000560`, `q-000567` | — | 1 |
| C23 | `bd02d6d4cd9994f2` | `q-000561`, `q-000568` | — | 1 |
| C24 | `c1f9510bf2786067` | `q-000562`, `q-000569` | — | 1 |
| C25 | `790c3ee32b811bd0` | `q-000571`, `q-000578` | — | 1 |
| C26 | `892caed1dea782b9` | `q-000600`, `q-001591` | — | 1 |
| C27 | `53d7d605647bceba` | `q-000646`, `q-000682` | — | 1 |
| C28 | `7fb7b9208c07a361` | `q-000772`, `q-000776` | `q-001861` | 1 |
| C29 | `6454f4c246db03ec` | `q-000773`, `q-000777` | — | 1 |
| C30 | `d3b14fef58139a4c` | `q-000774`, `q-000778` | — | 1 |
| C31 | `300a1eea0b701de8` | `q-000775`, `q-000779` | `q-001862` | 1 |
| C32 | `8ee09db92c1f6b3c` | `q-000820`, `q-000823` | `q-000827` | 1 |
| C33 | `7ea1e09aab1a5086` | `q-000821`, `q-000825` | `q-000828` | 1 |
| C34 | `2565fcf5d3754eae` | `q-000844`, `q-000845` | — | 1 |
| C35 | `2724fa4582ac6633` | `q-000876`, `q-000878` | — | 1 |
| C36 | `c5b244904814bfec` | `q-000877`, `q-000879` | — | 1 |
| C37 | `b4e0396ef74be499` | `q-001106`, `q-001111` | — | 1 |
| C38 | `849ca672afe98531` | `q-001107`, `q-001114` | — | 1 |
| C39 | `20739d85addc55e6` | `q-001108`, `q-001113` | — | 1 |
| C40 | `acfe5a685885c12f` | `q-001115`, `q-001555` | — | 1 |
| C41 | `798cb100da8a4f57` | `q-001157`, `q-001158` | `q-001165`, `q-001180` | 1 |
| C42 | `08953d3d023fae30` | `q-001159`, `q-001160` | — | 1 |
| C43 | `9bb5450cbed058a7` | `q-001171`, `q-001174` | `q-001179` | 1 |
| C44 | `2aa3574aaf85078e` | `q-001200`, `q-001204` | — | 1 |
| C45 | `49408707499d659d` | `q-001212`, `q-001219` | — | 1 |
| C46 | `f7899b9801ae52aa` | `q-001213`, `q-001220` | — | 1 |
| C47 | `2da72a68a2d0dedd` | `q-001214`, `q-001221` | — | 1 |
| C48 | `12d5825c8737d27f` | `q-001238`, `q-001376` | `q-001231` | 1 |
| C49 | `c8f7dcd4be785e10` | `q-001240`, `q-001641` | — | 1 |
| C50 | `716dcf6a544b2985` | `q-001241`, `q-001642` | — | 1 |
| C51 | `96528e05c447cff5` | `q-001292`, `q-001700` | `q-001242`, `q-001303` | 1 |
| C52 | `030ce9a5e54a612c` | `q-001291`, `q-001699` | — | 1 |
| C53 | `458187832b574923` | `q-001296`, `q-001298` | — | 1 |
| C54 | `fa68fb122788bd12` | `q-001306`, `q-001307` | — | 1 |
| C55 | `6b3ee175e736e813` | `q-001325`, `q-001717` | — | 1 |
| C56 | `182738f15b0f0ece` | `q-001326`, `q-001718` | — | 1 |
| C57 | `c95ba8cad63dc3c5` | `q-001356`, `q-001359` | — | 1 |
| C58 | `9b217d513fa27f67` | `q-001357`, `q-001360` | — | 1 |
| C59 | `c1b028fe1caa3c91` | `q-001358`, `q-001361` | — | 1 |
| C60 | `d524a88456ccfd95` | `q-001390`, `q-001452` | `q-001387` | 1 |
| C61 | `64c16ab5d2923e97` | `q-002019`, `q-002024` | `q-001458`, `q-002027` | 1 |
| C62 | `ed744633483f6f75` | `q-001482`, `q-001483` | `q-001487` | 1 |
| C63 | `ae6d65d059990641` | `q-001565`, `q-001752` | — | 1 |
| C64 | `fb458a2b38ccd672` | `q-001566`, `q-001751` | — | 1 |
| C65 | `f82c3c4065276965` | `q-001931`, `q-001935` | `q-001928` | 1 |
| C66 | `b19fcec0f0c39385` | `q-002022`, `q-002025` | `q-002018` | 1 |
| C67 | `815bb1a773357c2b` | `q-002023`, `q-002026` | — | 1 |

Negative rows in these groups do not forbid any listed positive truth.
Their presence does not create the positive conflict.
`q-000483` and `q-000484` are the previously documented pilot conflict.
`q-000152` and `q-000160` have compatible positive and negative constraints.
The [JSON evidence](annotation-audit.json) retains all duplicate groups, including compatible groups.

## Conditional top-1 ceiling

Assume that identical bytes always produce the same deterministic top-1 wine slug.
Assume that the recognizer uses no query ID, path, place, annotation, or other row-specific metadata.
Assume that randomness, time, and request context do not change that answer.
Treat matching recorded digests as identical bytes. Source files were not opened or rehashed.

For each digest, count how many positive truth sets contain each possible answer.
Take the largest count for that digest. Sum those largest counts across digests.
Keep every positive row at its original weight.

`ceiling = sum_d max_a sum_(positive row i in d) 1[a in truth_i]`

The 1508 positive rows outside conflicting groups can contribute at most 1508 correct answers.
The 136 positive rows in conflicting groups can contribute at most 68 correct answers.
Thus, the conditional ceiling is **1576 / 1644 = 95.8637%**.
At least **68 positive rows** must miss top-1 under these assumptions.
One group has three different positive truths and costs two misses.
The other 66 conflicting groups cost one miss each.

This is an optimistic metadata bound. It assumes perfect recognition wherever labels permit it.
It ignores missing index coverage and operational errors. It is not an achieved result.
It does not bound top-5 recall. A ranked list can contain more than one accepted wine.
It does not apply to answers that vary by row-specific metadata or nondeterministic behavior.
No saved predictions were read or rescored.

The exact-slug conflicts do not identify the physically correct wine.
Different slugs may need a catalogue review, but this audit does not merge aliases or entities.
The same photo may intentionally represent multiple catalogue identities.
This audit does not choose a correct label or predict what recall any model can achieve.
The raw benchmark results and denominators remain unchanged.

## Sources

- [Frozen baseline queries](../../../runs/2026-09-26T213857Z-lab-barcode-rerank-siglip2-512-crop-my/queries.jsonl).
- Query-file SHA-256: `99673ed979606f881fcfa4bf26f0156f9f55d58e061dd3e624b74f2a3bae91dc`. The digest remained unchanged after the audit.
- [Query selection](../../../pipeline/benchmark.py) defines saved `truth`, `slug`, and label fields.
- [Existing classification](../../../scripts/benchmark_recognition_latency.py) uses accepted-truth membership and the negative forbidden slug.
- [Complete audit evidence](annotation-audit.json) contains exact groups and per-digest ceiling calculations.
