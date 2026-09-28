# Change log

## 2026-09-28

### Initial Android application

- Added an Android 9 application project with the ID `Chtozavino.alolalab.com`.
- Added the offline DIS and SigLIP2 recognition contract.
- Added the verified external model-pack contract.
- Added the Russian user-flow specification and smoke tests.
- Added the model-pack builder with strict model, dimension, pipeline, and hash checks.
- Added local cosine-search and barcode normalization tests.
- Added a model-pack builder test that rejects the current 1,152-dimensional GX10 vectors.
- Verified lint, unit tests, and the debug APK build with JDK 17.
- Verified `minSdkVersion` 28, `targetSdkVersion` 36, and the application ID in the APK.
- Kept model files and catalogue vectors outside Git.
