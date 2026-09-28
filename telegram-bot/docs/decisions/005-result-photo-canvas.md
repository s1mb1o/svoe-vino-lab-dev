# Result photo canvas

Date: 2026-09-26

## Context

The catalogue contains result images with different aspect ratios.
Some transparent WebP images are more than three times taller than their width.
Telegram crops these images in the chat preview.

## Options

### Fit the complete source image on a fixed canvas

This option is simple.
This option keeps unused margins that exist in the source image.

### Detect the foreground and fit it on a fixed canvas

This option removes unused transparent or white margins.
This option keeps the complete detected bottle visible.
This option does not need another model.

### Segment the bottle with a model

This option can support complex backgrounds.
This option adds GPU load and a new failure mode.

## Decision

Detect the foreground from alpha when the source has transparency.
Use a threshold of 16 for the alpha mask.
Detect differences from white for an opaque source.
Remove isolated noise with a median filter.
Keep a 1% source margin around the detected foreground.
Fit the result on a white 1024 by 1280 pixel canvas.
Keep 5% padding on the constrained canvas axis.

## Consequences and risks

Telegram shows the complete bottle in a 4:5 preview.
A narrow bottle has larger horizontal margins.
An opaque image with a non-white background keeps most or all of its source area.
The submitted user photo fallback keeps its original aspect ratio.
