# Separate RTX 4090 retrieval campaign

The owner selects a separate hardware campaign on 2026-10-19.
The existing GX10 campaign continues.
This campaign includes no re-ranking.

## Fixed scope

- Use the fixed my-failed-2 cohort with 668 positive assignments and 627 images.
- Use the fixed my cohort with 2970 positive assignments.
- Rebuild all bottle vectors on RTX 4090.
- Recalculate all bottle baselines on RTX 4090.
- Evaluate 5432 bottle recipes and 59752 comparisons per cohort.
- Build all 18 native stages.
- Use the same two frozen label-space score arrays for fusion.
- Keep accepted answers on the Mac.
- Complete my-failed-2 before my.
- Order my by complete my-failed-2 Top-1, Top-5, Top-10, and MRR results.

The baseline is siglip2-p512-rot5-seg.
It uses uniform bottle pooling and the original segmented query.
Its reference gallery has 5 degree in-plane rotations.
Its reference gallery has no synthetic bottle-axis rotations.

## Hardware controls

The runtime uses torch 2.11.0+cu130 and torchvision 0.26.0+cu130.
It uses transformers 5.3.0, Pillow 12.1.1, and NumPy 2.4.3.
The model is google/siglip2-so400m-patch16-naflex.
The fixed model revision is cc24074f717b612951c2dead130904ab9b65a81e.

The mixed-host pilot does not pass the declared numerical policy.
A Torchvision compatibility module uses the ARM float32 resize path.
Seven of eight sampled RGB tensors then match exactly.
One sampled tensor differs by one RGB level in one value.
The remaining GPU differences change 12 to 23 first candidates in 913 inputs.
The strict GX10 admission remains false.
No rented vector is imported into the original GX10 campaign.
GX10 stores the separate campaign vectors in a separate directory.
RTX 4090 performs ranking with the same fixed label-space score arrays.

A separate concurrency control uses 72 varied reference views.
One Torch CPU thread and eight preparation workers preserve all tensors.
The measured preprocessing times are 11.53 seconds and 6.88 seconds.
A complete 913-query control covers all 39 pooling profiles.
The maximum vector difference is zero.
The cloud reference checkpoint resumes with these settings.

## Collection controls

The recipe check covers all 5432 bottle recipes in 1001 shared computations.
The cache layout check preserves all 220896 reference owner rows.
It preserves all 27252 axial owner rows.
The local collector replays 22 saved metric rows from both cohorts.
All replayed metrics match the saved controls.
The own-baseline paired changes are zero.
The test fixtures stay separate from real RTX 4090 results.

The collector MUST verify every returned ranking archive.
The collector MUST use the rebuilt hardware baseline.
The collector MUST preserve the my-failed-2 query prefix during my encoding.
The collector MUST verify all 18 completed vector stages before each final audit.
The collector MUST keep each hardware campaign in its own metrics database.

## Approval state

The owner approves images, masks, the public model, scripts, and GPU execution.
All 80574 uploaded files pass destination SHA-256 and timestamp checks.
The transferred input payload has 13598130904 bytes.

The first arrangement keeps label scores and recipe order on GX10.
It uses the existing label-space arrays through local read-only links.

The RTX 4090 builds all bottle vectors.
The first private bridge returns completed stages to GX10.
GX10 verifies every destination SHA-256 and timestamp before publishing a stage.
The first private ranker calculates all candidates without accepted answers.
The Mac evaluates returned candidate orders against accepted answers.
The owner later approves the two label-space score arrays and the derived recipe order.
The public host receives the two fixed label-space score arrays and ranking scripts.
The payload has 21 files and 62192483 bytes.
Every destination file passes the SHA-256 and timestamp checks.
The two arrays have opaque wine columns.
The accepted answers remain on the Mac.

The prepared collector supports ranking on the public host.
The collector requires both payload approvals and the workflow approval before it selects that host.
The destination control checks public uploads and the private fallback.
The public recipe order MUST use the complete separate RTX 4090 failure-cohort results.
The public recipe order MUST contain 5432 opaque bottle recipe IDs.

Automatic approval review first rejects the runtime switch.
The owner then explicitly approves the runtime switch.
The rented server now runs codex-retrieval-score.service.
The local collector reads ranking archives from the rented server.
The waiting private duplicate ranker has stopped.
The private bridge has stopped.
The active RTX 4090 embedding worker keeps PID 8192 during the switch.
The original GX10 embedding worker keeps PID 3034448 during the switch.
The original GX10 campaign and its results remain separate.
The future my recipe order goes to the rented server after the complete failure-cohort audit.
The Mac retains all accepted answers.

## Evidence

- private-dataflow-check.json
- cloud-dataflow-check.json
- approved-cloud-ranking-payload.json
- cloud-ranking-transfer-verification.json
- cloud-ranking-activation.json
- private-ranking-stop-proof.json
- hardware-benchmark/cloud-ranking-enabled.json
- hardware-benchmark/imports/
- hardware-plan.json
- hardware-coverage-check.json
- hardware-cache-layout-check.json
- hardware-collector-control.json
- fast-runtime-control.json
- preprocess-concurrency.json
- parity-compatible-admission.json
- hardware-benchmark/report.html

## Numerical mask recovery on 2026-10-20

The p256 query pilot stopped the embedding runner. The batch-equivalence delta was 0.005837425589561462. The unchanged tolerance is 0.00002.

The versioned worker uses an explicit encoder mask when the library omits the mask for a fully occupied input. The change applies only to the six previously unbuilt p256 and p1024 stages. The original worker remains unchanged for p512, margin, and Cartesian stages. The p256 and p1024 query controls now have zero batch-equivalence delta and zero uniform-pooling delta. All 21 sampled frozen p512 reference vectors have zero delta.

The recovery receipt is `attention-mask-recovery.json`. The new worker is `hardware_worker_explicit_mask.py`. Its SHA-256 is `0fbb1467fbe55f579ab63e8ca659aa1ef23331dd7848178f4f8fba07381c9b21`. The original worker SHA-256 remains `57c786222baa658ab554d4c6a5a9bda06fef2a88d3c097e67af124c1782328f6`. The runner selects the worker by stage. The local collector audit checks the same stage allowlist and both worker hashes.

The 11 completed stage markers were preserved. The unbuilt stage metadata has a separate archive. The embedding service resumed. The ranking service stayed active. The p256 query priority vectors are complete. The p256 reference pilot passed.
