# Two complete production pipelines

Date: 2026-10-20.
Source: the owner selected both pipelines and authorized a main push and website publication.

## Contract

The application MUST default to DIS-768 cropped custom.
The settings page MUST also select the previous full-image standard pipeline.
Each pipeline MUST use its measured complete Base NaFlex p512 graph and matching reference index.
The custom pipeline MUST use the measured DIS-768 graph and four-percent crop margin.
It MUST preserve the 1024-pixel render limit and fractional mask projection.
Its attention weights MUST use foreground 1.0 and background 0.1.
The standard pipeline MUST preserve its original complete graph and original index bytes.
The pack MUST contain both model/index pairs. It MUST share catalogue metadata and images.
The pack loader MUST reject a missing or incompatible model, profile, index, or segmentation model.
The application MUST keep model creation, inference, switching, and cleanup on one worker.
The custom DIS GPU path MUST use FP32 arithmetic and automatic storage.
The encoder GPU path MUST use FP32 arithmetic and BUFFER storage.
The application MUST preserve explicit CPU selection and safe automatic CPU fallback.
Each selected pipeline MUST have a distinct accelerator-check identity.
Changing the selected pipeline MUST close previous recognition resources.
The debug HTTP API MUST use the selected pipeline and report its identity.
The release MUST NOT contain the debug HTTP server.
An upgrade MUST preserve history, consent, and explicit accelerator preferences.
An upgrade MUST select the new default once. Later starts MUST preserve the selected pipeline.
Barcode and QR recognition MUST remain available.
The public format 7 pack MUST omit optional YOLO weights, as the owner selected.
Legacy pack readers MAY retain YOLO support. The new settings MUST expose only the two requested pipelines.

## Verification and release

Preserve all benchmark evidence and frozen sources.
Verify DIS-512 completion and cleanup before any Pixel change.
Test pack validation, migration, selector persistence, model/index isolation, and patch weights.
Build debug and release variants. Run Android tests and release lint.
On Pixel, compare both pipelines with saved benchmark vectors/rankings on representative inputs.
Test switching in both directions, history, diagnostics, and default-off HTTP.
Archive versioned release files outside Git. Preserve the previous signing certificate.
Integrate the feature on current origin/main. Push only origin/main.
Verify distribution licenses before public APK publication.
Read the existing deployment instructions. Update the Android landing page and download.
Verify the public page and APK hash after publication.

## State

Ready for implementation. Pixel DIS-512 reports complete with successful cleanup.
Public publication remains subject to existing model-distribution requirements.
