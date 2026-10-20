# Comprehensive repository review

Date: 2026-10-20, Europe/Moscow.

## Scope

Review the README, setup instructions, architecture, assessment evidence, service configuration,
main HTTP paths, account service, MCP server, bot core, bot transports, tests, and packaging.
The initial review inspected the Android and iPhone source contracts.
The initial review changed no application source.

The checkout changed during the review through other work.
The initial revision was `d2edf952`.
The final source inspection used `1fa56ce2d0034001ea56693d36853c80ba498066`.
The test results below describe the working tree at execution time.
They do not establish a deployment state.

## Findings

### R1. [P2] Metadata lookup rejects valid catalogue identifiers

Location: [wine-metadata.ts, line 7](../../webui/server/utils/wine-metadata.ts#L7).

`SOURCE_SLUG` excludes underscores.
`fetchSourceWine` returns `null` before the HTTP request when this check fails.
The metadata route checks only 12 local records before this call.
The matcher bundle contains 37 affected identifiers outside those 12 records.
Of these identifiers, 36 also exist in the Active alternative catalogue snapshot.
Examples include `perovskih_aligote`, `denisov_barynya_kurmyshi`, and `twopeters_kokur`.

A successful prediction of one of these wines cannot load its full result card.
The scanner retains the predicted identifier and marks metadata as unavailable.

Verification: call the actual `fetchSourceWine` implementation with a stub fetch function.
`perovskih_aligote` returns `null` with zero fetch calls.
A hyphenated control identifier calls the stub and returns metadata.
Compare bundle identifiers with `webui/server/data/wines.json` and
`webui/server/data/alternative-catalog.json` to reproduce the affected counts.

Correction: accept the complete supported catalogue identifier format.
Keep path encoding and the rejection of path separators.
Add a regression with a real underscore identifier.

### R2. [P2] The real matcher setup uses removed environment variables

Location: [SETUP.md, lines 62–72](../../SETUP.md#L62).

The setup exports `SIGLIP2_ENDPOINT=http://127.0.0.1:18090`.
The current loader reads the endpoint from YAML only.
The documented command therefore keeps `http://192.168.86.14:18081/v1/embeddings`.
A user with local bootstrap services cannot reach those services through this command.
The same setup also exports `SVOE_VINO_MATCHER_OUTPUT_DIR`, which the loader ignores.
The mock setup and the evaluator instructions contain the same obsolete convention.

Verification: set the documented environment variables, then call
`load_matcher('matcher/config.yaml')` without inference.
`matcher.backend.url` remains the GX10 URL.
`matcher.resolved_output_dir()` remains the YAML value.
The component [configuration instructions](../../matcher/README.md#L284) explicitly document
the removal of these variables.

Correction: make the root setup select an explicit YAML file.
Show the local endpoint and archive directory in that file.
Update the evaluator instructions with the same configuration method.

The matcher also ignores `SAM3_ENDPOINT` by design.
This behavior conflicts with the workspace instruction that makes `SAM3_ENDPOINT` canonical.
The review does not resolve this configuration policy conflict.

### R3. [P2] The lab runtime dependencies omit jsonschema

Location: [requirements-local.txt, lines 8–18](../../workbench/requirements-local.txt#L8).

The dependency file says that the lab server needs only its first four packages.
The file does not declare `jsonschema`.
The lab server imports `describe_images` at startup.
That module imports `jsonschema` unconditionally at line 58.
A documented lightweight environment therefore cannot import the lab server.
The failure occurs before the server can listen.

Verification: the existing model environment failed to import
`tests/test_production_error_routes.py` with `ModuleNotFoundError: No module named 'jsonschema'`.
The import chain is `lab_server -> describe_images -> jsonschema`.
The focused 16-test suite passes under the system interpreter that has this dependency.

The [historical startup record](../../workbench/ChangeLog.md#L7104) already records a workaround.
That record uses another interpreter.
The workaround does not correct the declared runtime dependencies.

Correction: declare `jsonschema` in the lab server dependencies.
Correct the lightweight dependency instructions.
Verify a clean-environment import of `pipeline/lab_server.py`.

### R4. [P2] The assessment references absent Android evidence

Location: [ASSESSMENT.md, lines 370–372](../../ASSESSMENT.md#L370).

The assessment presents the Android research package as local portable evidence.
This checkout contains no `research/android-20261020/` directory.
It also lacks `ANDROID-RESEARCH-AND-RESULTS-20261020.md` and
`android/docs/releases/0.3.0.md`.
The assessment has 25 local link occurrences that point to absent Android evidence.
The documented verifier command cannot start from this checkout.
The existing Android source uses the earlier format 6 contract.

Verification: check the local paths and the final Git tree.
The paths are absent in both.
This finding does not dispute a result recorded in another source revision.
It identifies a broken evidence path in the submitted source package.

Correction: include the portable evidence package, or use links to its exact external revision.
Label the external commands with the checkout that they require.
Keep the current checkout and the later Android release distinct.

### R5. [P3] The README still says that the Web UI has no Dinner Lens integration

Location: [README.md, line 19](../../README.md#L19).

The statement groups the Web UI and both bots as unconnected clients.
The current Web UI has a `/dish` page, a Dinner Lens client, and three same-origin proxy routes.
`NUXT_DINNER_LENS_ENDPOINT` and `NUXT_DINNER_LENS_API_TOKEN` enable the integration.
The separate [Web UI integration guide](../../webui/docs/dinner-lens.md) documents these settings.
The root statement incorrectly tells a reviewer that this implemented feature is absent.

Correction: describe the Web UI integration and its required settings.
State the bot integration status separately.

## Executed checks

| Check | Result |
| --- | --- |
| Account pytest suite | 186 passed |
| MCP syntax checks, tests, and local demo | Passed; 53 tests passed |
| Web UI type check | Passed |
| Web UI Vitest suite | 619 passed; 26 skipped |
| Web UI production build | Passed |
| Built Web UI producer-map bundle check | Passed |
| Alternative catalogue consistency check | Passed; 2,025 wines; 90 comparison pairs |
| Matcher unittest suite | 281 passed; 1 optional MLflow integration test skipped |
| Shared bot core pytest suite | 191 passed |
| Telegram bot pytest suite | 271 passed |
| MAX bot pytest suite | 511 passed |
| Workbench database export tests | 8 passed |
| Workbench production-error tests | 16 passed |
| Bootstrap unit tests | 22 passed |
| Portable retrieval verifier | Passed; 58 file hashes; 5,432 recipes; 281 compact metric rows |
| Underscore identifier reproduction | Confirmed R1 with a stub fetch function |
| Matcher configuration reproduction | Confirmed R2 without model calls |
| Assessment local-link check | Confirmed R4 |

The first network-fixture runs could not bind loopback sockets under the sandbox.
The successful network-fixture runs used permission to bind temporary loopback servers.
No fixture failure from the sandbox is classified as an application defect.
Bot test environments used cached locked dependencies in temporary directories.
The bootstrap tests used the existing model environment and a temporary copy of the cached
pure-Python `qrcode` package.
The complete counted result is 2,158 passed tests and 27 skipped tests.

## Limits

The review does not repeat a recognition benchmark or a deployment check.
The review does not send a real bot message or a model-provider request.
The review does not build or install a mobile application.
The Dinner Lens embedding indexes are absent.
The complete Dinner Lens suite therefore remains unverified.
The full workbench suite and device acceptance suites were not repeated.
Initial bootstrap test attempts lacked test dependencies.
The final bootstrap unit suite passed all 22 tests.
The unit suite does not load model weights or prove hardware compatibility.

Read `workbench/FIX_LATER.md` and `matcher/docs/KNOWN_ISSUES.md` for deferred defects.
The review does not report those entries as new findings.
Passing local tests does not prove recognition accuracy or production security.

## Remediation follow-up

Date: 2026-10-20, Europe/Moscow.
The owner authorized fixes for all five findings.
The original findings and test results above describe the initial review.
The following results describe the corrected working tree.

| Finding | Resolution |
| --- | --- |
| R1 | Fixed. Source metadata accepts the 36 affected Active identifiers. A real underscore identifier has a regression. Path separators remain invalid. The inactive `__aaaaa` sentinel remains invalid. |
| R2 | Fixed. `matcher/config.local.example.yaml` supplies the loopback gateway and archive path. Setup and evaluator instructions select that file. `SAM3_ENDPOINT` now overrides the SAM3 URLs for shelf, hand-selection, and cascade clients. YAML fallback URLs remain available when the variable is absent. |
| R3 | Fixed. `workbench/requirements-server.txt` declares the five lightweight runtime dependencies, including jsonschema. `requirements-local.txt` includes that list. A fresh environment imports the server and passes the focused route tests. |
| R4 | Not applicable on `main`. Commit `906bd778` adds `research/android-20261020/`, `ANDROID-RESEARCH-AND-RESULTS-20261020.md`, and `android/docs/releases/0.3.0.md`. All local links in `ASSESSMENT.md` resolve on `main`. The finding describes only the reviewed checkout. The assessment is unchanged. |
| R5 | Fixed. The README identifies `/dish`, the Web UI proxy routes, and both required private settings. It states the bot integration status separately. |

### Remediation checks

| Check | Result |
| --- | --- |
| Web UI type check | Passed |
| Web UI unit tests | 625 passed; 26 existing skips |
| Web UI production build and producer-map bundle check | Passed |
| Isolated matcher suite | 285 passed; 1 optional MLflow integration test skipped |
| Fresh lightweight Workbench installation | Installed the five declared runtime dependencies from cached packages; server import passed |
| Workbench production-error tests in the fresh environment | 16 passed |
| Local matcher example | Loads the committed bundle; selects `http://127.0.0.1:18090/v1/embeddings` and `work/matcher-requests` without inference |
| Catalogue identifier coverage | All 36 affected Active identifiers pass the corrected validator |
| Assessment local links on `main` | No missing targets |
| README, setup, assessment, and evaluator local links | No missing targets |
| Git whitespace check | Passed |

The first matcher remediation run inherited the real `SAM3_ENDPOINT`.
Some fixture images reached the configured service instead of the local fake service.
That run failed 14 assertions.
The subprocess fixtures now remove the inherited override.
CI and the documented test command also remove the ambient override.
The final matcher run used `env -u SAM3_ENDPOINT` and passed.
Dedicated override tests use their own fixture URLs.

This follow-up does not repeat mobile inference, a recognition benchmark, or a deployment.
No model weights or APKs were imported.

### Rebase onto main

The fixes were rebased onto `main` at `82fd80fe`.
R4 was evaluated again on that base. R4 is not applicable there.
The rebased tree passed the isolated matcher suite: 292 tests ran, and 1 optional test was skipped.
The rebased tree passed the Web UI type check.
The Web UI unit tests passed 637 tests with 26 existing skips.
The Workbench tests were not repeated after the rebase.
