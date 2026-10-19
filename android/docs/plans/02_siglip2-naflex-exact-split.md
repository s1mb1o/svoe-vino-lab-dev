# SigLIP2 NaFlex exact split

Date: 2026-10-19

## Objective

Add a SigLIP2 NaFlex runtime to the Android application.
The runtime MUST produce 1,152-dimensional vectors in the desktop model space.
The default patch limit MUST be 512.
The model pack MAY select 256, 512, or 1,024 patches.

## Model split

The first LiteRT model is the backbone.
It accepts normalized image patches, resized positional embeddings, and an attention mask.
It applies the original patch projection and vision transformer.
It returns patch tokens before the final vision LayerNorm.

The second LiteRT model is the pooling head.
It accepts the backbone patch tokens and the attention mask.
It applies the original vision `post_layernorm`.
It applies the original multi-head attention pooling operation.
It applies the original pooling LayerNorm and MLP residual.
It returns one 1,152-dimensional vector.

The application MUST L2-normalize the returned vector.

## Preprocessing

The application MUST preserve the segmented crop aspect ratio for NaFlex.
The application MUST use RGB normalization from `[0, 255]` to `[-1, 1]`.
The application MUST use 16 by 16 patches.
The application MUST use the SigLIP2 maximum-patch resize algorithm.
The application MUST pad patch values and the attention mask to the pack patch limit.

The backbone receives resized positional embeddings as an input.
The model pack includes the original 16 by 16 positional embedding table.
The application resizes this table for the selected patch grid.
This design avoids a dynamic output-size operation that `litert-torch` cannot lower.

## Model pack

Model pack format version 4 adds these files:

- `siglip2_naflex_backbone.tflite`
- `siglip2_naflex_pooling.tflite`
- `siglip2_naflex_position_embeddings.f32`

The manifest adds these fields:

- `siglip2_runtime`: `naflex-exact-split`
- `patch_size`: `16`
- `max_num_patches`: `256`, `512`, or `1024`
- `position_embedding_grid`: `16`
- `vector_dim`: `1152`

The application MUST continue to accept format versions 1 through 3.
The application MUST validate the payload list, dimensions, and hashes before installation.

## Acceleration

The current backbone uses LiteRT CPU/XNNPACK.
The pooling head uses LiteRT CPU/XNNPACK.
This rule prevents two SigLIP2 GPU `CompiledModel` instances from staying active together.
The rule also reduces the risk of the known native LiteRT GPU abort.

The Pixel 8 GPU delegate compiles all backbone operations.
The Pixel 8 GPU delegate returns a finite but incompatible vector.
`Auto` MUST select CPU for this runtime.
Explicit GPU selection MUST report a compatibility error.
The application MAY enable GPU after a device parity test passes.

## Export

`tools/export_siglip2_naflex_split.py` MUST load
`google/siglip2-so400m-patch16-naflex` from the Hugging Face cache.
It MUST export the backbone and pooling head with static tensor shapes.
It MUST export the original positional embedding table.
It MUST compare the split PyTorch output with the original model output.
It MUST compare each LiteRT output with its PyTorch output.
It MUST write a metadata file with tensor shapes, source revision, and file hashes.

Generated model files MUST stay outside Git.

## Tests

Unit tests MUST cover the maximum-patch resize algorithm.
Unit tests MUST cover patch order, padding, and the attention mask.
Unit tests MUST cover positional embedding interpolation.
Unit tests MUST cover legacy and split model-pack validation.
Python tests MUST cover the split wrappers with a small deterministic model.

The final device test MUST run one known catalogue image on the Pixel 8.
The test MUST record the selected accelerator, vector size, score, and timing.

## Readiness

The requirements are complete.
The model split is complete.
The model-pack contract is complete.
The implementation is complete.
The exporter parity checks pass.
The Android automated checks pass.
The Pixel 8 CPU result matches the expected catalogue wine.
The p512 runtime is an accuracy baseline because one query takes approximately 256
seconds on the Pixel 8.
