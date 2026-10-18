# «Что за вино?» for iPhone

This directory contains the native SwiftUI iPhone application.
The application supports iOS 17.2 and later.
The user interface is in Russian.
The bundle identifier is `chtozavino.alolalab.com`.

The application has the Android user functions:

- 18+ age confirmation.
- Camera and photo-library input.
- EAN, UPC, Code 128, Data Matrix, and QR scan.
- Manual code input in the simulator.
- DIS or YOLO26n-seg foreground segmentation.
- SigLIP2 Base NaFlex p512, SigLIP2 Base 224, or MobileCLIP2-S2 image encoding.
- Ranked local vector search.
- Mask, crop, and white-background debug images.
- Local history with 50 rows.
- Saved settings and system appearance.
- VoiceOver, Dynamic Type, Reduce Motion, Reduce Transparency, Voice Control, and Switch Control support.
- A debug HTTP API on port 18088.

Recognition and catalogue lookup stay on the device.
The application needs a network connection only when the user opens a result page.

Read `docs/specification.md` and `docs/model-pack.md` for the contracts.

## Generated files

The generated model packages, compiled models, and resource pack stay outside Git.
Create a Python environment:

```bash
cd ios
python3 -m venv .venv
.venv/bin/pip install -r requirements-tools.txt
```

Supply the official DIS source, the `isnet-general-use.pth` weights, and the official
`yolo26n-seg.pt` checkpoint.
The accepted DIS weight SHA-256 is
`ea0889743a78391b48d6b7c40b4def963ee329cb10934c75aa32481dc5af9c61`.
The accepted YOLO checkpoint SHA-256 is
`361fbfabab285c3237700b6bb91d7ecfa602cd945fffda8dbe1242829b71e73f`.

Create the production models and vectors:

```bash
.venv/bin/python tools/export_dis_coreml.py \
  --source /path/to/DIS \
  --weights /path/to/isnet-general-use.pth
.venv/bin/python tools/export_yolo26_coreml.py \
  --checkpoint /path/to/yolo26n-seg.pt
.venv/bin/python tools/export_siglip2_coreml.py
.venv/bin/python tools/export_siglip2_naflex_coreml.py
.venv/bin/python tools/export_mobileclip2_coreml.py
.venv/bin/python tools/build_siglip2_naflex_vectors.py --device mps
.venv/bin/python tools/build_mobileclip2_vectors.py --device mps
.venv/bin/python tools/build_resource_pack.py \
  --mobileclip-vectors build/mobileclip2-s2-vectors.f32 \
  --naflex-vectors build/siglip2-base-naflex-p512-vectors.f32 \
  --version 20261006-ios-naflex-production
.venv/bin/python tools/compile_models.py
xcodegen generate
```

`export_siglip2_coreml.py` uses FP32 by default.
The FP32 export preserves the Android catalogue vectors.
`compile_models.py` compiles each package on the internal temporary volume.
This step avoids the `coremlc` external-volume permission error on macOS 26.

The YOLO checkpoint uses the Ultralytics AGPL-3.0 license.
The MobileCLIP2 model weights use the Apple model research license.
Confirm both licenses before public application distribution.

## Simulator test

Run the unit tests:

```bash
xcodebuild \
  -project ChtoZaVino.xcodeproj \
  -scheme ChtoZaVino \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -derivedDataPath DerivedData \
  CODE_SIGNING_ALLOWED=NO \
  test
```

The debug build accepts `-show_settings` as a launch argument.
This argument opens Settings for an automated simulator screenshot.
The `/v1/match` response contains `timings_ms` for segmentation, embedding, and local search.

The `ChtoZaVinoUITests` target checks the age gate, recognition screen, History,
Settings, code scanner, and unavailable-camera screen.
The recognition test uses the largest accessibility text size.
