# Research log

## 2026-10-18

### Accessibility audit

- The original source-action row used one fixed horizontal layout.
- The original result cards and history rows also used fixed horizontal layouts.
- These layouts did not preserve enough width at accessibility Dynamic Type sizes.
- Several images did not identify whether they were informative or decorative.
- Recognition progress did not send a VoiceOver announcement.
- Recognition completion did not move VoiceOver focus to the new content.
- The live scanner required a visual tap on a highlighted code.
- The model status used red as one state indicator.
- The application did not have an automated accessibility audit.

### Accessibility decisions

- Standard SwiftUI controls remain the primary controls for VoiceOver, Voice Control, and Switch Control.
- Source actions, result cards, and history rows use vertical layouts at accessibility Dynamic Type sizes.
- Recognition focus moves to the main action after image selection and to the result heading after completion.
- The live scanner copies a detected code to the manual input field when VoiceOver runs.
- Model status rows use text, a symbol, and color.
- Card backgrounds use an opaque system color when Reduce Transparency is enabled.
- The root view removes custom transaction animation when Reduce Motion is enabled.
- XCTest audits the age gate, recognition screen, History, Settings, code scanner, and unavailable-camera screen.
- The recognition test starts at the largest accessibility text size.
- The recognition test checks every main control against the 44-point minimum.
- The recognition test runs every audit except the XCTest Dynamic Type audit.
- XCTest reports false Dynamic Type failures for text inside custom SwiftUI button labels.
- The recognition test uses semantic fonts and verifies the largest accessibility layout directly.
- The final simulator run passed 12 unit tests and 6 accessibility UI tests.

## 2026-10-06

### SigLIP2 Base NaFlex p512

- The model is `google/siglip2-base-patch16-naflex`.
- The output has 768 values.
- A square p512 input uses a 22 by 22 patch grid.
- The grid has 484 valid tokens and 28 padding tokens in the Transformers processor.
- Removing the masked padding tokens did not change the PyTorch output. The cosine was 1.0.
- The Core ML graph uses one fixed `[1, 484, 768]` input.
- The mixed-precision Core ML output had cosine 0.99970 against PyTorch on a random stress input.
- Layer normalization and softmax stay in FP32.
- The production catalogue contains 2,093 Base NaFlex p512 vectors.
- The iPhone 17 Pro simulator returned the exact catalogue wine at rank 1 with cosine 0.9083.

### Recognition bottleneck check

- The device was the iPhone 17 Pro simulator with iOS 26.2.
- Core ML used CPU because the simulator does not provide ANE execution.
- The baseline warm median was 6,728 ms for DIS with Base NaFlex p512.
- The baseline stage medians were 5,077 ms for segmentation, 1,311 ms for embedding, and 360 ms for search.
- Direct `Float` access removed one `NSNumber` operation for each tensor value.
- Accelerate `vDSP_mmul` replaced the scalar catalogue dot-product loops.
- The optimized warm median was 3,216 ms.
- The optimized stage medians were 2,133 ms for segmentation, 1,073 ms for embedding, and 11 ms for search.
- The complete warm request became 52.2% faster.
- The same wine stayed at rank 1. Its cosine changed by less than 0.000001.
- A full resource-pack check now writes a receipt with the pack version and manifest SHA-256.
- A later launch verifies the receipt and manifest before it reuses the completed check.
- Debug-server readiness improved from 49.1 seconds to 5.6 seconds on the simulator.
- YOLO with the same Base NaFlex p512 encoder had a warm median of 1,884 ms.
- YOLO returned the same wine at rank 1 with cosine 0.9423 on the test image.

## 2026-10-03

### SigLIP2

- The model is `vit_base_patch16_siglip_224.v2_webli`.
- The input is a 224-pixel center crop after a 248-pixel bicubic resize.
- The input range is `[-1, 1]`.
- The FP16 and mixed Core ML exports changed catalogue vectors by about 0.014 cosine distance.
- The FP32 Core ML export had a minimum cosine of approximately 1.000000 against the Android index.
- The production export uses FP32.

### MobileCLIP2-S2

- The model is the official `MobileCLIP2-S2` `dfndr2b` checkpoint.
- The input size is 256 by 256 pixels.
- The FP16 Core ML export had a minimum cosine of 0.99965113 against PyTorch.
- The mean cosine was 0.99975437.

### DIS

- The model is the official IS-Net general-use checkpoint from `xuebinqin/DIS`.
- The FP16 Core ML output had a mean absolute difference of 0.00011158 against PyTorch.
- The maximum absolute difference was 0.05597132.

### YOLO26n-seg

- The model is the official `yolo26n-seg.pt` checkpoint.
- The Core ML export has a raw 116 by 8,400 detection output.
- The Core ML export has a 32 by 160 by 160 prototype output.
- The FP16 detection output cosine was 0.99998230 against PyTorch.
- The FP16 prototype output cosine was 0.99952078 against PyTorch.
- The Swift mask parser uses the same constants and ranking formula as Android.

### Simulator

- The simulator device was iPhone 17 Pro with iOS 26.2.
- Core ML used CPU in the simulator.
- DIS with SigLIP2 returned the expected catalogue result in approximately 6,052 ms.
- DIS with MobileCLIP2-S2 returned the same result in approximately 4,469 ms.
- YOLO with SigLIP2 returned a ranked result in 3,375.97 ms.
- YOLO with MobileCLIP2-S2 returned the same Top-1 result in 1,887.67 ms.
- The final YOLO with MobileCLIP2-S2 request took 2,118.52 ms after a clean launch.
- A repeated request took 1,281.16 ms with the model cache.
- The final DIS with SigLIP2 request took 4,530.35 ms.
- The production resource pack contained 2,093 wines and 2,093 images.

### macOS build behavior

- `coremlc` failed when it compiled a model package directly on the external T7 volume.
- The compilation succeeded after the script copied each package to the internal temporary volume.
- The script copies each compiled `.mlmodelc` directory back to the workspace.
