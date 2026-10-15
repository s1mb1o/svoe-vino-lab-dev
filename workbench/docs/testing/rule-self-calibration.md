# Rule self-calibration prototype

Date: 2026-10-11.
Status: Complete isolated prototype. No production integration.

## Scope

The owner approved an isolated prototype for two wine families.
The prototype covers three Фантом wines and four Виктор Дравиньи wines.
The current combined Виктор Дравиньи cluster has six wines.
This prototype covers the four-wine label-view subset.

Artifacts are in `internal/rule-self-calibration-20261011/` from the repository root.
The prototype does not modify the production generator or recognizer.
The prototype preserves catalogue rules, catalogue images, annotations, and vectors.
The prototype uses existing services without a model load or service restart.

## Inputs

Use seven catalogue label references for calibration.
Start with the colour-enabled rules from `internal/colour-prompts-20261011/`.
Use each original reference and seven deterministic variants.
The variants use dim light, warm light, cool light, blur, low resolution, perspective, and partial occlusion.
The variants preserve printed characters and printed colours before the image transform.
Add one blank-image control per wine.
There are 56 identification cases and seven blank controls.

Reserve five additional `full_front` photographs for final evaluation.
Check `image_type`, `package_view`, and the visible front label.
Reject back views, unknown views, and conflicting metadata.
Separate source photographs before augmentation.
Reject a source photograph that occurs in both partitions.

The final photographs cover Фантом 50/50 and all four Виктор Дравиньи wines.
The final photographs do not cover Фантом 30/70 or Фантом 70/30.
Each final photograph has its original runtime crop and an unseen moderate lighting variant.
There are ten final cases.
These cases come from five source photographs.

`ClusterRerank.picture` prepares the final photographs through the shared SAM3 service.
The client reads `SAM3_ENDPOINT`.
SAM3 detected a label in all five final photographs.
All query images use the runtime white composite and a 1536-pixel long side.
The synthetic white background is not an illumination reference.

`manifest.json` records source hashes and source modification times.
The manifest also records case hashes, implementation hashes, configuration hash, and prototype hash.
Each phase verifies the frozen inputs.
Only staged copies and derivatives get a submission timestamp before the required cutoff.
Original files keep their bytes and modification times.

## Recognition

The recognizer is the configured `qwen3.5-9b-nvfp4` service.
The prototype calls the current `ClusterRerank.rerank` method.
The recognizer receives a prepared image and ordinary option-score questions.
The recognizer receives no expected wine, source filename, case identifier, or augmentation identifier.
Thinking is disabled.
The output limit is 256 tokens.
The timeout is 180 seconds.
Requests run sequentially.
The runtime checks the response scores and permits one correction request.

All candidates have equal base scores of 0.75.
This setup measures rule evidence without embedding retrieval.
A correct result requires one positive maximum evidence score for the expected wine.
A tie is not a correct result.
No positive evidence is an abstention.
Any positive evidence on a blank control is unsafe.
Option scores are model outputs, not calibrated probabilities.
The runtime gives scoreable questions equal weight.
Plain rule text does not enter the recognition request.

## Revision

The generator is configured QwenCloud `qwen3.8-max` with thinking enabled.
A revision receives the catalogue label references, metadata, and saved descriptions.
A revision also receives the current rule, calibration failures, and earlier candidate outcomes.
A revision can receive at most two failed calibration images.
The request reserves context and image capacity for this feedback.
The feedback is not a trusted reviewer note.
The generator must verify printed features against the references.
The final photographs and final recognition results do not enter a revision.

The generator retains a distinctive colour question.
The generator can improve colour-region wording and expected colour categories.
The generator can improve text questions that support the same identities.
The prototype validates each candidate with the existing rule validator.
The prototype rejects a candidate without a scoreable colour question.

## Selection

Evaluate at most three candidates per cluster, including the initial rule.
Reject a candidate that loses a previously correct calibration case.
Reject a candidate that introduces a new unique wrong choice or unsafe blank control.
Prefer fewer unsafe controls, fewer wrong choices, fewer errors, and more correct results.
Retain the earlier rule when a candidate does not improve this objective.
Use the retained rule for the next revision request.

Stop when all identification cases are correct and all blank controls are safe.
Otherwise stop at the three-candidate limit.
Report unresolved cases.
Do not force recognition when the identifying feature is absent.
Freeze the selected rules before final recognition.
Compare initial and selected rules on identical final images.
Do not revise a rule after final recognition.

## Calibration results

| Family | Candidate | Correct | Wrong | Tie | Abstain | Safe blank controls | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| Фантом | Initial | 13/24 | 0 | 0 | 11 | 3/3 | Retain |
| Фантом | Revision 1 | 19/24 | 5 | 0 | 0 | 3/3 | Reject |
| Фантом | Revision 2 | 18/24 | 6 | 0 | 0 | 3/3 | Reject |
| Виктор Дравиньи | Initial | 28/32 | 1 | 3 | 0 | 4/4 | Replace |
| Виктор Дравиньи | Revision 1 | 32/32 | 0 | 0 | 0 | 4/4 | Select |

The selected rules have 45/56 correct identification cases.
The initial rules have 41/56 correct identification cases.
All seven blank controls are safe for both initial and selected rules.
The selected rules have no unique wrong choice in calibration.

Фантом reaches the candidate limit with 11 abstentions.
The first revision improves recognition by naming the small rectangle precisely.
The first revision also introduces five wrong choices.
The second revision introduces six wrong choices.
The second revision proposes an alcohol question.
The validator excludes the alcohol question because another valid feature differs.
Both revisions fail the selection guard.
The prototype therefore preserves the initial Фантом rule.

The initial Виктор Дравиньи rule fails four calibration cases.
The warm blue-label case has conflicting sugar and background-colour evidence.
The warm green-label case assigns the background to yellow and cannot read the sugar text.
The cool and low-resolution green-label cases have ties.

The selected revision keeps the sugar question.
The selected revision explicitly mentions warm and cool colour casts in the main-label question.
The selected revision adds the background colour of the printed neck-label seal.
The expected seal colour is unknown for the blue-label reference crop.
The recognizer ignores that unknown answer for the blue-label wine.
The selected revision preserves every previously correct calibration case.
All 32 identification cases and four controls pass.
The loop therefore stops without a second Виктор Дравиньи revision.

## Preparation correction

Visual inspection found a final-image preparation error before final recognition.
The initial lighting transform changed the synthetic white background.
The corrected transform preserves the SAM3 alpha mask until the runtime white composite.
The correction uses cached SAM3 results for the same five source photographs.
The correction changes only the five unused final lighting variants.
All 63 calibration cases and five original final crops remain equal.
The selected rules remain equal.
AST comparison confirms that all recognition, revision, and selection functions remain equal.
`before-final-correction/` preserves the original code, metadata, and unused variants.
`preparation-correction.json` records the changed hashes and correction time.

## Validation and final results

Unit tests check deterministic augmentation, runtime compositing, source preservation, and front filtering.
Unit tests check source overlap, ground-truth exclusion, response correction, and unsafe controls.
Unit tests check monotonic selection, the revision limit, and exclusion of final records from feedback.
All 15 offline tests pass.
Ruff checks pass for the prototype, tests, correction script, and result audit.

| Final source cohort | Initial | Selected |
|---|---:|---:|
| Фантом 50/50, original and unseen lighting | 2/2 | 2/2 |
| Four Виктор Дравиньи wines, original and unseen lighting | 8/8 | 8/8 |
| All final cases | 10/10 | 10/10 |

Both rule sets recognize all five original photographs and all five unseen lighting variants.
The final comparison shows no regression on this cohort.
The final comparison does not show an accuracy gain because the initial rules already pass every case.
Ten cases do not mean ten independent photographs.
The cohort has five source photographs and partial per-wine coverage.
The result measures rule evidence with equal base scores.
The result does not measure retrieval or general production accuracy.
The unresolved Фантом calibration cases remain unresolved.

The run records 173 recognition results across initial, rejected, selected, and final cases.
The recognizer makes 169 live requests and uses five cached attempts.
One invalid first response receives the runtime correction request.
All final responses pass validation.
There are no unresolved service or validation errors.
The aggregate live recognition time is 19.3 minutes.
Three live revision calls take 8.4 minutes and use 46,716 total tokens.
The two initial rules are reused from the earlier prompt test.
These timings exclude the earlier initial-rule generation.

`audit.json` verifies complete case coverage and candidate selection.
The audit recomputes evidence and classifications from the saved raw responses.
The audit verifies source bytes, source modification times, and frozen metadata.
The audit verifies the final preparation correction and selected-rule freeze.
The audit confirms that final case identifiers do not enter revision feedback.
The correction proof confirms that final recognition had not started.

## Saved artifacts and decision

Read the prototype specification in `internal/rule-self-calibration-20261011/SPEC.md`.
Read `selection.json` for accepted and rejected candidates.
Read `summary.json` for cluster metrics.
Read `audit.json` for the independent result audit and per-condition metrics.
Read the JSONL result files for raw responses, validation attempts, and evidence scores.
Read `feedback-*.json` for the revision feedback.

The selected Фантом rule is `rule-a29e59138ed4-0.json`.
The selected Виктор Дравиньи rule is `rule-3346ef764c41-1.json`.
These rules remain isolated artifacts.
The prototype does not replace production rules.

Keep the candidate limit and the regression guard in any later integration.
Do not require a successful identity when the source cannot support that identity.
The prototype supports bounded rule refinement as an experiment.
The prototype does not establish that every cluster can pass every augmentation.
