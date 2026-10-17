# Product image sizing

Date: 2026-10-16.

## Contract

A product image MAY contain an optional `frame` object.
The frame describes a visible source-image rectangle in pixels.
The frame contains `x`, `y`, `width`, `height`, `source_width`, and `source_height`.
All values MUST be safe integers.
The width and height values MUST be positive.
The origin MUST be non-negative. The rectangle MUST fit inside the source image.
The existing image source ID and asset URL remain authoritative.
The schema version remains 1. The frame is an optional compatible extension.

## Measurement

Read the original WebP alpha channel without changing image bytes.
Find the bounding rectangle of alpha values greater than or equal to 128.
Add a margin of 0.5% of the visible height. Round the margin to at least one source pixel.
Clamp the rectangle to the source image.
Store the rectangle and original image dimensions in the producer JSON.
Recompute the frame when the source image changes.
Set `SHARP_MODULE` to the installed Sharp module entry.
Run `node scripts/measure-product-image-frames.mjs` from `webui`.
The script MUST reject a missing alpha channel, fully opaque images, wrong source dimensions, or a frame that clips the measured alpha outline.
The read-only script writes measured frames and source hashes to `reports/product-image-frames/frames.json`.
Copy the measured frame into the corresponding producer JSON after review.
The producer crosswalk retains the source-image SHA-256.

## Rendering

`ProductLineImage.vue` renders the source inside the measured frame.
The wrapper uses the frame aspect ratio and the available image width and height.
The source image uses proportional dimensions and an offset inside the wrapper.
The wrapper clips only pixels outside the measured frame.
The browser does not scan alpha pixels at runtime.
The frame is available during server rendering. The image size does not depend on a load event.

Group previews use a height of 106 px and a maximum width of 52 px.
Product nodes use a height of 112 px and a maximum width of 70 px.
Desktop details use a height of 176 px and a maximum width of 120 px.
Mobile details use a height of 108 px and a maximum width of 68 px.
The map zoom scales the complete canvas after image sizing.
A wide package can reach the width limit before the height limit. Keep the package proportions.
An image without a frame uses the existing image sizing behavior.
Missing images continue to use the labeled placeholder.

## Decision

Cropping source files would require new image bytes and provenance hashes.
Browser alpha scans would add image decoding and pixel analysis to mobile navigation.
Measured JSON frames retain source pixels and provide stable layout before image loading.
Use measured JSON frames for producer-map images.

## Checks

Validate all frame bounds before the production build.
Check the rendered visible height, source aspect ratio and complete outline in Chromium and WebKit.
Check previews, nodes, desktop details and mobile popups.
Keep gray rendering and image-error placeholders available.
Read `docs/validation/product-image-sizing.md` for the current results.

## Display derivatives

Imagegen cutouts are display derivatives. They do not guarantee unchanged fine print.
Use original photos and source records for product identity.
Accept a display derivative only when the complete package shape, capsule color, main label layout, and main artwork match the input.
Reject visible brand, package, color, or artwork substitutions.
Inspect the contour on light and dark surfaces.
Keep input, generated, and output hashes and the exact prompt in provenance.
Do not describe a generated label as pixel-identical to its input.

Apply consumer class and style to the frame once.
Keep native image attributes on the inner image.
Use 112 px by 70 px sizing limits when custom properties are absent.
