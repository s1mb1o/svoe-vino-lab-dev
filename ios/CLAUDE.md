# iPhone application

This directory contains the offline iPhone client for «Что за вино?».

Read `README.md`, `docs/specification.md`, and `docs/model-pack.md` before a change.

The application MUST support iOS 17.2 and later.
The application MUST use Russian text in the user interface.
The application MUST keep recognition on the device after resource installation.
The application MUST reject a resource pack when an encoder or vector dimension does
not match the application contract.

Do not add downloaded source model weights to Git.
Do not add generated Core ML models or generated resource packs to Git.
Use the tools in `tools/` to create generated resources.

Update `ChangeLog.md` and `SMOKE_TESTS.md` with each functional change.
