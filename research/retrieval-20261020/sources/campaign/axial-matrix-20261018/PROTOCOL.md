# Complete axial retrieval matrix

Use the two existing frozen testsets and catalogue.
Preserve the original photos, original vectors, and original results.
Do not use a reranker.

Use the existing -30 to +30 degree bottle-axis renders at 5-degree steps.
Retain the exact zero-angle vectors once.
Keep unsupported sources at their existing baseline vectors.
Combine axial vectors with each existing zero, cardinal, and rot5 gallery.
Use a gallery union. Do not render a Cartesian product of axial and image-plane angles.

Cross all seven bottle pooling profiles with all seven query geometries and all three reference galleries.
Use the existing query vectors for each pooling profile.
Cross all 147 axial bottle configurations with all 24 label configurations and all 42 fixed fusion policies.
Keep label vectors and label pooling unchanged.
Score 147 new bottle controls and 148176 fusion configurations per testset.
The extension has 148323 unique configurations per testset.
The 24 label-only controls already exist and MUST NOT be counted twice.
The combined benchmark has 296670 unique configurations per testset.

Reuse standard axial vectors.
Encode the six missing custom pooling profiles in one native vision pass per batch.
Use the pinned SigLIP2 SO400M NaFlex checkpoint and at most 512 patches.
Use BF16 and vision batches of 36.
Preserve the native learned attention head and its log-weight bias.
Preserve the existing fractional and whole-empty-patch definitions.
Keep padded tokens excluded.

The bottle-axis renderer preserves the bottle silhouette.
Use the exact frozen foreground mask for each source.
Project the label mask through the same remap coordinates as the rendered label texture.
Intersect each projected label mask with the bottle foreground.
Keep the zero-angle masks unchanged for the control.
Check every rendered RGB pixel hash against the existing frozen axial render.
Verify the mask projection on sampled sources before a full transfer.
Verify native zero-angle vectors against all seven existing pooling controls.
Verify standard axial vectors against the previous axial build.

Keep at least 20 GiB available on GX10.
A new model load needs at least 28 GiB available.
Cap the native worker at 8 GiB of CUDA memory.
Preserve other jobs and resident services.
Set timestamps on submitted copies and archive headers before the workspace cutoff.

Score by the maximum cosine for each wine across source images and retained views.
Use the existing accepted answers and assignment metrics.
Keep negative and no_match metrics separate.
Add image-weighted metrics and paired baseline fixes and regressions to the updated reports.
Keep the declared assignment-based leaderboard order for compatibility.
Show image-weighted rankings as a separate view.

Audit every expected variant ID, candidate list, rank, metric, and source identity.
Check all original axial singles and the reproduced standard-pooling axial fusion controls.
Update the coverage report, both matrix reports, the axial report, and top-five leaderboards.
Identify development-test selection, testset overlap, saturated Top-10 ties, and the index-builder restriction in the report.
