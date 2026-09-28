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
Use `tools/build_model_pack.py` to create a model pack outside the repository.

Update `ChangeLog.md` and `SMOKE_TESTS.md` with each functional change.
