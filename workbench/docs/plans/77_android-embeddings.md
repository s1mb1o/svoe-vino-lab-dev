# Plan 77: Android embeddings

Date: 2026-09-28

## Goal

Add two catalogue embeddings for the Android application.

- `android-siglip2-base-224-dis-white` MUST use the Android DIS image pipeline.
- `android-siglip2-base-224-sam3-white` MUST use the present SAM3 package derivative.
- Both entries MUST use `timm/vit_base_patch16_siglip_224.v2_webli`.
- Both entries MUST return normalized vectors with 768 values.

## Model contract

The embedding service MUST use revision
`4c3661e5ac879a276ddc5ddc6d3f0ecc78fd5d82` of
`timm/vit_base_patch16_siglip_224.v2_webli`.

The DIS step MUST use revision
`1b966dbe2f33bd5ca1299cf94fbab59265210b6b` of
`litert-community/DIS-ISNet-LiteRT`.

The DIS input is RGB float32 NCHW with size 1 by 3 by 1024 by 1024.
The normalization is `x / 255 - 0.5`.

## Image pipelines

The DIS entry MUST do these steps:

1. Limit the long source side to 2,048 pixels.
2. Resize the source to 1,024 by 1,024 for DIS.
3. Apply min-max normalization to the raw DIS output.
4. Find the mask box at threshold 0.5.
5. Reject a foreground fraction below 0.005 or above 0.995.
6. Add a margin of 4 percent on each box axis.
7. Composite the soft mask on white.
8. Put the crop at the center of a white square.
9. Resize the square to 224 by 224.

The SAM3 entry MUST do these steps:

1. Use the present package derivative.
2. Remove the background.
3. Composite the result on white.
4. Put the result at the center of a white square.
5. Resize the square to 224 by 224.

Each entry uses the `full` view. This avoids duplicate vectors from a second view.

## Build sequence

1. Add the fixed SigLIP2 model to the GX10 image-embedding registry.
2. Verify one request and the vector dimension.
3. Build the SAM3 entry.
4. Build the DIS entry.
5. Validate the indexes, vector dimensions, norms, and item counts.

The two builds MUST run sequentially.

## Failure behavior

The build MUST keep successful checkpoints.
The build MUST record a failed DIS item with a clear error.
A second build MUST continue the incomplete work.

## Verification

- Unit tests MUST cover the DIS box, white composite, square output, and invalid mask.
- Unit tests MUST cover the new step validation.
- A one-image live probe MUST return 768 values.
- Each completed index MUST contain only finite normalized vectors.
