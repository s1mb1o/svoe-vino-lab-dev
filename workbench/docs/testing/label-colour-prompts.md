# Distinctive label colour prompts

Date: 2026-10-11.

## Requirement and change

Use a distinctive printed label colour in a cluster rule.
The colour can cover the main label or a small label region.
Name the region by its position and its shape or printed contents.
Do not use glass, liquid, or capsule colour for a label question.

`DESCRIBE_PROMPT` records the main label colour and separate colour regions.
The description includes region position, shape, contents, and observed colour.
The `colours` field includes small label regions.

`RULES_PROMPT` permits distinctive label colour without a reviewer note.
The generator uses the cluster images to check the description.
The generator retains a colour question when a text question also separates the cards.
The generator gives null when an expected region colour cannot be established.

The query prompts compare the specified region with the candidate colours.
The query prompts allow plausible illumination changes.
A blue appearance can support the only blue candidate when the image supports that explanation.
A yellow region can appear brown in dim or warm light.
The absence of a brown candidate does not establish yellow.
The query prompts preserve uncertainty when the candidate colours overlap.
The query prompts ignore synthetic white crop backgrounds as illumination references.
The query prompts permit `not visible` or `unsure`.
The score prompt permits support across several plausible options.

The current Workbench and native matcher use equal question weights.
The prompt change does not change that score rule.
The integer option scores are not calibrated probabilities.

## Models and image inputs

Stage 1 uses configured `qwen3.5-9b-nvfp4` with thinking disabled.
Stage 1 describes one bottle independently.
Stage 1 uses the package crop when a package crop exists.
Stage 1 otherwise uses the catalogue image.
Stage 1 receives no catalogue metadata.
Stage 1 uses a 2048-pixel long side.

Stage 2 uses configured `qwencloud-qwen3.8-max` with thinking enabled.
Stage 2 receives cluster label images together.
Stage 2 also receives catalogue metadata, saved descriptions, and reviewer notes.
Stage 2 uses the package crop when a label crop does not exist.
Stage 2 can include additional label photographs within its image budget.
Stage 2 uses a 768-pixel long side and a 16000-token output limit.
The live rule test has an empty reviewer note for each cluster.
The owner explicitly approved the seven-image QwenCloud payload.

Query inference uses the existing GX10 Qwen3.5-9B service.
Query inference has thinking disabled and a 1536-pixel long side.
The test uses sequential requests.
The test starts no service and loads no model.

## Test protocol

Artifacts are in `internal/colour-prompts-20261011/`.
`baseline/` contains source files before this task's changes.
`baseline-prompts.json` contains the original prompt constants.
`probe.py` contains the reproducible test driver.
The driver uses a read-only catalogue database and an isolated model cache.

The rule test compares the original and new rule prompts with identical inputs.
The test covers three Фантом wines and four Виктор Дравиньи wines.
The Фантом cluster key is `a29e59138ed4`.
The Виктор Дравиньи label-view subset key is `3346ef764c41`.
The current combined Виктор Дравиньи cluster has six wines.
This test does not cover the two additional wines.

The description test compares one package image per family.
The first new description omitted the small region from `colours`.
The revised schema wording includes small regions in `colours`.
The test retains both attempts.

The fixed-rule query test uses human-checked colour and text questions.
Both query prompts receive the same questions and candidate options.
This test isolates query interpretation from rule generation.
There are 21 catalogue queries and six existing positive real-photo queries.
Each catalogue reference has an original, dim, and warm-dim variant.
The dim variant multiplies RGB by `(0.4, 0.4, 0.4)`.
The warm-dim variant multiplies RGB by `(0.65, 0.5, 0.3)`.
These variants test sensitivity to a defined transform.
These variants do not reproduce all camera or lighting effects.
The fixed-rule test permits 1600 output tokens.

The generated-rule query test first uses the six real photographs.
None of these photographs has a stored label crop.
The first test therefore uses the whole photograph.
A separate test applies `ClusterRerank.picture` to each photograph.
This method creates a SAM3 label crop when SAM3 detects the label.
The separate test records the input kind and exact image hash.
The SAM3 client reads the canonical `SAM3_ENDPOINT` variable.
Each version receives its generated rule and corresponding query prompt.
This test uses the configured 256-token query limit.
Invalid score responses receive the existing runtime validation correction once.
All first result records and retry responses remain in the test artifacts.
The first fixed-rule runner did not retain raw replies for validation failures.
The retry runner retains the full retry reply.

A correct result requires one positive maximum evidence score for the annotated wine.
A tie is not a correct result.
No positive evidence is an abstention.
This metric measures rule evidence.
This metric does not include embedding retrieval or the final ranking adjustment.

## Unit validation and integration

The focused Workbench suites pass 92 tests.
The native option-score suite passes 32 tests.
The native suite includes 256 frozen decision-parity cases.
The parity test compares all three query prompts with `matcher/rerank.py`.
The label-rule tests check colour-question evidence and alcohol suppression.
The label-rule tests check prompt-dependent stage hash invalidation.

`workbench/scripts/cluster_rules.py` uses the same generation prompts.
`matcher/rerank.py` uses the same query prompts.
All non-prompt implementation code remains equal to the captured baseline.
Existing catalogue rules require regeneration to use the new generation prompt.
This test writes no catalogue rule, vector, annotation, or historical run.
This test performs no runtime restart or deployment.

## Generated rule results

Both new rules include one valid colour question and one text question.
Both new colour questions retain image evidence for each expected answer.
Both new rules have an empty reviewer note.

| Family | Original prompt | New prompt |
| --- | --- | --- |
| Фантом | Alcohol percentage only | Blend ratio and bottom-left square colour |
| Виктор Дравиньи, four-card subset | Sugar level only | Sugar level and main label background |

| Family | Card | Expected region colour |
| --- | --- | --- |
| Фантом | 30/70 | pink/magenta |
| Фантом | 50/50 | dark red/maroon |
| Фантом | 70/30 | purple/violet |
| Виктор Дравиньи | brut | light blue |
| Виктор Дравиньи | extra brut | black/dark grey |
| Виктор Дравиньи | semi-sweet | light green |
| Виктор Дравиньи | semi-dry | yellow/gold |

The description prompt now records the small Фантом colour region.
Qwen9B still describes the pink region as red.
QwenCloud checks the label image and correctly records pink/magenta.
This result supports retaining image input for rule generation.

## Fixed-rule query results

All results below include the one permitted validation correction.
The first responses have two validation failures with the original prompt.
The first responses have six validation failures with the new prompt.
All eight corrections return valid score objects.

| Input | Cases | Original: correct | New: correct |
| --- | ---: | ---: | ---: |
| Catalogue, original | 7 | 6 | 5 |
| Catalogue, dim | 7 | 5 | 5 |
| Catalogue, warm-dim | 7 | 3 | 3 |
| Real photograph, whole image | 6 | 3 | 3 |
| Total | 27 | 17 | 16 |

The original prompt has two unique wrong evidence winners.
The new prompt has one unique wrong evidence winner.
The new prompt increases ties from four to seven.
Both prompts have four abstentions.
This result does not establish an accuracy improvement.
This result shows that ambiguity can replace a unique choice.

The generated-rule test on whole real photographs has two correct results out of six for each version.
The new rule resolves the yellow semi-dry Виктор Дравиньи photograph.
The new rule makes the 30/70 Фантом result ambiguous.
Qwen9B reads the ratio correctly but assigns the red-looking square to dark red/maroon.
The neutral label area does not show a strong warm cast in this photograph.
A rule cannot assume that every reference-to-photo colour difference is caused by lighting.
Actual bottle colours and catalogue rendering can also differ.

## Runtime image preparation results

The runtime method detects a label for 5 photographs.
The runtime method uses the whole photograph for 1 photograph.
Both versions receive the same prepared image for each case.
The test uses the configured 256-token limit and one validation correction at most.
No response in this test needs a correction.

| Evidence result | Original | New |
| --- | ---: | ---: |
| Unique correct result | 2/6 | 3/6 |
| Unique wrong result | 0/6 | 0/6 |
| Tie | 0/6 | 2/6 |
| Abstention | 4/6 | 1/6 |
| Validation failure | 0/6 | 0/6 |

The new rule resolves the 70/30 Фантом photograph and the yellow semi-dry Виктор Дравиньи photograph.
The 30/70 Фантом photograph becomes a tie because text and colour conflict.
The warm-lit semi-sweet Виктор Дравиньи photograph becomes a tie between light green and yellow.
The six photographs are a focused test, not a representative accuracy estimate.
The test does not include retrieval or final embedding-score adjustments.

## Outcome and limits

The generator now uses the required colour regions.
The query instructions permit candidate-dependent illumination uncertainty.
The runtime-image test gains one unique correct result in six cases.
The fixed-question stress test loses one unique correct result in 27 cases.
The prompt changes do not solve colour recognition under all lighting conditions.
Do not use these results to claim a general accuracy increase.

All 13 tracked source images retain their bytes and modification times.
All non-prompt implementation code remains equal to the baseline.
Ruff passes for the changed implementations and the test driver.
The label-rule test file retains one existing E731 finding and has no new finding.
The repository diff check passes.

Read `rule-checks.json`, `summary.json`, `verification.json`, and the raw result files in the artifact directory.
Existing catalogue rules remain unchanged.
A targeted rule rebuild is required to activate the new generation prompt for an existing cluster.
