# Hand-aware package selection

## Scope

The SigLIP2 pipeline MAY select the main package before it computes an embedding.
The option is `pipeline[].hand_selection`. The value MUST be a YAML boolean.
The default is `false`. The mock backend MUST reject `true`.

```yaml
pipeline:
  - name: siglip2-hand
    backend: siglip2
    bundle: matcher/data/gx10-siglip2-so400m-patch16-naflex-p512
    endpoint: "{env:SIGLIP2_ENDPOINT}"
    hand_selection: true
```

The matcher MUST use the selected pipeline entry. Restart the matcher after a
configuration change. Set `SAM3_ENDPOINT` to the SAM3 base URL when the option is
enabled. The default configuration MUST keep the option disabled.

## Single-image behavior

- `POST /v1/match` and `POST /v1/eval/predict` MUST use the same selection step.
- The selector MUST request `wine bottle, can, packet, box, hand` from SAM3.
- The selector MUST apply EXIF orientation before segmentation. It MUST limit the
  long side of the segmentation image to 1600 pixels.
- Detections below confidence 0.4 MUST NOT affect selection.
- The score follows version 1 of `workbench/pipeline/main_scene.py`. It combines
  package size, position, sharpness, detector confidence, mask fill, shelf isolation,
  and edge visibility. When a hand is present, box overlap with the hand adds a
  selection signal. A size gate reduces this signal for small shelf packages.
- This signal is a geometric heuristic. It does not prove that a hand holds a package.
  Hands MUST NOT become match candidates.
- Without a hand, the selector MUST use the scene weights from the same algorithm.
- The selector MUST crop the selected package. It MUST replace pixels outside its
  binary SAM3 mask with white. It MUST NOT reconstruct an occluded label.
- With no usable package mask, the matcher MUST use the original image and its
  existing preprocessing. An invalid SAM3 response MUST be an error, not a fallback.
- A missing or invalid `SAM3_ENDPOINT` MUST return HTTP 503. Invalid service data
  MUST return HTTP 502. A SAM3 timeout MUST return HTTP 504.
- With the option disabled, single-image requests MUST NOT call SAM3.

## Group isolation

`POST /v1/group/match` MUST ignore `hand_selection`, including when its value is
`true`. The group path MUST request only `wine bottle`. It MUST retain the existing
deduplication and response limits. It MUST send every retained bottle crop to
`match_many`. That method MUST NOT select a main package or call SAM3 again.

## Verification

Tests MUST cover strict configuration validation, hand and no-hand ranking, the
small-package size gate, low-confidence hands, empty detections, invalid masks,
EXIF orientation, white mask background, and default behavior. API tests MUST cover
both single-image routes, dependency errors, and request audit status codes.
A group API test with `hand_selection: true` MUST verify the exact SAM3 prompt,
one segmentation request, and one embedding input per retained bottle.
Tests use local fake services. They do not measure recognition quality or GPU latency.
