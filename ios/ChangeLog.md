# Change log

## 2026-10-18

### Accessibility

- Added VoiceOver labels, hints, headings, status announcements, and focus transitions.
- Added vertical layouts for accessibility Dynamic Type sizes.
- Added 44-point minimum hit regions for custom controls and links.
- Added text and symbols for states that previously used color.
- Added Reduce Motion and Reduce Transparency behavior.
- Added an accessible scanner path that copies a detected code to the manual input field.
- Added Dynamic Type support to the unavailable-camera screen.
- Added XCTest accessibility audits for the age gate, recognition screen, History, Settings, code scanner, and unavailable-camera screen.
- Added accessibility identifiers for automated UI tests.
- Passed 12 unit tests and 6 accessibility UI tests on the iPhone 17 Pro simulator with iOS 26.2.

## 2026-10-06

- Added `SigLIP2 Base NaFlex p512` with a 22 by 22 patch grid and 768-value vectors.
- Added the Core ML export and catalogue-vector tools for `google/siglip2-base-patch16-naflex`.
- Added a separate p512 vector index to the built-in resource pack.
- Made Base NaFlex p512 the default encoder for a new installation.
- Kept SigLIP2 Base 224 and MobileCLIP2-S2 as selectable encoders.
- Removed per-value `NSNumber` conversion from Core ML tensor input and output paths.
- Added Accelerate matrix-vector search for all local encoder indexes.
- Added a validation receipt after a complete resource-pack integrity check.
- Added recognition-stage timings to the debug match response.

## 2026-10-03

### Native iPhone application

- Added the SwiftUI application for iOS 17.2 and later.
- Added the Android age gate, image input, code scan, result, history, and settings flows.
- Added the local debug HTTP API on port 18088.
- Added current segmenter and encoder fields to the health response.
- Added model reuse for repeated recognition requests.
- Added the built-in catalogue with 2,093 wines and 2,093 images.

### Segmentation and encoding

- Added the DIS Core ML segmentation path.
- Added the YOLO26n-seg Core ML segmentation path.
- Added the `DIS / YOLO` saved setting.
- Added the COCO `bottle` selection and mask construction from the Android application.
- Added SigLIP2 Base 224 with the Android 768-value index.
- Added MobileCLIP2-S2 with a new 512-value index.
- Added `Авто`, `ANE`, and `CPU` compute settings.
- Added the first-start accelerator compatibility test and its repeat action.

### Verification

- Passed 9 unit tests on the iPhone 17 Pro simulator with iOS 26.2.
- Verified DIS with SigLIP2 and MobileCLIP2-S2 through the debug API.
- Verified YOLO with SigLIP2 and MobileCLIP2-S2 through the debug API.
- Verified the main screen and Settings with simulator screenshots.
