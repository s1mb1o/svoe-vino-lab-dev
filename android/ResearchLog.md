# Research log

## 2026-09-28

- Google Code Scanner 16.1.0 supports Android API 23 and later.
- Google Code Scanner performs processing on the device through Google Play services.
- LiteRT 2.2.0 provides `CompiledModel` with GPU and CPU accelerators.
- `litert-community/DIS-ISNet-LiteRT` uses a 1 by 3 by 1,024 by 1,024 float input.
- DIS normalization is `x / 255 - 0.5`.
- DIS returns a 1 by 1 by 1,024 by 1,024 soft alpha mask.
- `litert-community/SigLIP2-base-patch16-224` uses a 1 by 3 by 224 by 224 float input.
- SigLIP2 normalization maps RGB values to `[-1, 1]`.
- SigLIP2 returns one L2-normalized 768-dimensional vector.
- The current workspace catalogue has 4,642 vectors of dimension 1,152.
- The current vectors use a different SigLIP2 model and cannot be used by the Android
  image encoder.
