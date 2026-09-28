# Decision 01: Offline recognition

Date: 2026-09-28

## Options

### Bundle all files in the APK

This option gives one installation file.
The two models add approximately 361 MB before application resources.
Large assets also make application updates expensive.

### Download or import a model pack

This option keeps the APK small.
The application can verify and replace all related model files as one unit.
The first recognition requires model-pack installation.

### Use the matcher service

This option gives the smallest application.
It does not meet the offline requirement.

## Decision

The application imports a verified model pack.
Recognition runs locally after model-pack installation.

## Consequences

The project needs a separate model-pack release process.
The desktop export MUST use the same preprocessing and SigLIP2 model.
The application cannot use the current 1,152-dimensional GX10 vectors.
