# Multi-shot recognition

Date: 2026-10-18

## Objective

Allow the user to recognize one wine from one, two, or three photographs.
Keep the existing single-photo flow.
Improve recognition when one photograph has a weak bottle or label view.

## Input

- The user MAY add photographs from the camera and the gallery.
- The application MUST keep at most three selected photographs.
- The user MUST be able to remove one selected photograph.
- The user MUST be able to remove all selected photographs.
- A new selection MUST clear the previous recognition result.
- The Android debug HTTP API MUST keep its single-image contract.

## Recognition

- The application MUST process the selected photographs sequentially.
- All photographs MUST use the same segmentation and accelerator settings.
- Each photograph MUST produce up to five ranked matches.
- For each `wine.slug`, the application MUST keep the highest score from all successful photographs.
- The application MUST sort the merged matches by score in descending order.
- A score tie MUST sort by `wine.slug` in ascending order.
- The application MUST show at most five merged matches.
- The application MUST keep processing when one photograph fails.
- The application MUST report an error when all photographs fail.

Sequential processing keeps one recognition pipeline active.
This rule reduces LiteRT GPU memory pressure.

## Result evidence

- The application MUST show the debug images from the photograph that produced the final Top-1 score.
- The application MUST save that photograph result in history.
- The technical text MUST show the number of successful photographs.
- The technical text MUST show the number of selected photographs.
- The technical text MUST identify the photograph that produced the Top-1 score.
- The technical text MUST report a skipped photograph count when a photograph fails.

## Verification

- Add unit tests for maximum-score fusion.
- Add unit tests for deterministic score ties.
- Add unit tests for the five-result limit.
- Run the Android unit tests.
- Run Android lint.
- Build the debug APK.
- Perform a device smoke test with two different views of one bottle.
