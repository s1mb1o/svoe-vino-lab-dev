# Android application

This directory contains the offline Android client for «Что за вино?».

Read [README.md](README.md), [docs/specification.md](docs/specification.md), and
[docs/model-pack.md](docs/model-pack.md) before a change.

The application MUST support Android 9 and later.
The application MUST use `minSdk 28`.
The application MUST use Russian text in the user interface.
The application MUST keep recognition on the device after model-pack installation.
The application MUST reject a model pack when its SigLIP2 model or vector dimension does
not match the application contract.

Do not add model weights or generated model packs to Git.
Use `tools/build_verified_naflex_pack.py` for the default format 6 pack.
Use `tools/build_model_pack.py` only for legacy fixed Base/224 packs.
Write generated packs outside the Android source directory.
Use the pinned `app/libs/naflex-0.2.0.aar` for the complete p512 runtime.
Do not substitute a split graph or a fixed Base/224 reference index.
Keep GPU creation, execution, and cleanup on the same inference worker.

Update `ChangeLog.md` and `SMOKE_TESTS.md` with each functional change.
