# Synthetic rule benchmark

The isolated pilot tests Фантом and Виктор Дравиньи.
The pilot uses three Фантом wines and four Виктор Дравиньи wines.
The pilot does not update production rules.

The real suite contains 301 source-identity cases and seven blank controls.
Each wine has 43 observation-condition variants.
The variants include ten transformation families at three severities.
The variants also include twelve fixed combinations.
The cases remain derivatives of seven catalogue label crops.

The controlled suite contains 127 unique query images in eight fictional clusters.
The fictional clusters test colour-only, text-only, redundant, and identical labels.
Each layout uses three or four candidates.
Feature masks define the observable candidate set.
Unknown and conflicting labels are separate controls.

Use `qwen3.8-max` for the two real-family rules.
This Cloud payload contains only the seven previously approved label references, metadata, and label descriptions.
Use resident `qwen3.5-9b-nvfp4` for fictional descriptions, fictional rules, and recognition.
Use one LAN request at a time.
The two suites use different rule-generator models.
Do not compare their scores as a model comparison.

Freeze the generated rules before recognition.
Keep the matching prompt, scoring algorithm, and configured matching limits.
Use equal initial scores to measure rule-supported identity evidence.
Do not count the initial candidate order as successful rule recognition.
Do not revise rules from these query failures.

The current runtime does not support native abstention.
The benchmark inspects evidence scores separately from the final ranking.
An ambiguous case is safe when it has zero evidence or equal evidence for all compatible candidates.
A blank or unknown case requires zero positive evidence.
A conflict-unresolved case is not an explicit runtime abstention.

Run the local safeguards before inference.
Read `SPEC.md` and the frozen manifest before a fresh run.
Read the shared GPU tracker before LAN requests.
Preserve the 20 GiB reserve.
Do not load a model or restart a service.
Derivative images use pre-cutoff modification times.
The benchmark checks original source hashes and modification times after execution.

Use the commands in [COMMANDS.md](../../COMMANDS.md).
The evidence directory is [synthetic-rule-benchmark-20261011](../../../internal/synthetic-rule-benchmark-20261011/).
The result report is `REPORT.md` in that directory.
The numbered failure mapping is `failed-cases.json`.
The local `report.html` shows original and tested label images.
The audit checks every exact transmitted query hash, frozen rule, model, response, and score.

Synthetic accuracy does not establish accuracy on independent real photographs.
Review severe-corruption failures for actual feature visibility.

## Completed pilot results

All 435 cases finished on 2026-10-11.
All frozen source, reference, query, rule, request, and score checks pass.

| Family | Correct | Wrong | Tie | Zero evidence | Error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Фантом | 23/129 (17.83%) | 2 | 5 | 99 | 0 |
| Виктор Дравиньи | 161/172 (93.60%) | 8 | 2 | 0 | 1 |

All seven real blank controls are safe.
The original queries score 1/3 for Фантом and 4/4 for Виктор Дравиньи.
The Фантом ratio question returns zero candidate-answer evidence in 117/129 cases.
The Фантом colour question returns zero candidate-answer evidence in 99/129 cases.

The controlled suite passes 111/127 checks.
All 36 text-only checks pass.
Fourteen identical-label checks require no recognition request.
The remaining controlled failures include incorrect colours, ties, zero evidence, and unsupported unique evidence after feature removal.

The pilot saves 133 stable failure numbers.
Фантом uses numbers 1–106.
Виктор Дравиньи uses numbers 107–117.
Controlled labels use numbers 118–133.
Each number has an expected candidate set, image, answers, scores, and raw response trace.

Cases 111 and 114 show correct sugar text with two incorrect colour answers.
The two colour questions outweigh the correct text question.
Case 118 returns `other: 90` and `maroon: 10` for an unknown colour.
The remaining candidate evidence creates an unsupported unique winner.
These observations identify separate perception and score-policy concerns.

The audit records 467 fresh requests.
The requests include two Cloud rule requests and 429 LAN recognition requests.
Eight recognition requests are validation retries.
No transport request fails.
One recognition case fails score validation after its retry.
All 13 local safeguards and Ruff checks pass.
The viewer loads all 133 failures without a runtime error.
The viewer passes widths 1050, 736, 360, and 320 in light and dark themes.

Read the [full report](../../../internal/synthetic-rule-benchmark-20261011/REPORT.md).
Open the [numbered failure viewer](../../../internal/synthetic-rule-benchmark-20261011/report.html).
Read the [failure records](../../../internal/synthetic-rule-benchmark-20261011/failed-cases.json) for exact machine-readable evidence.
This pilot has no old-rule comparison arm.
The pilot does not establish accuracy on independent real photographs.
