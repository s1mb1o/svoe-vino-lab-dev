# fb-missed-tap-reticle Missed tap continues to the explicit reticle

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-missed-tap-reticle.json)

**scene-v1:** Contract N/A; fallback: target differs  
**semantic-v2:** Recorded checks pass

![fb-missed-tap-reticle comparison](../previews/fb-missed-tap-reticle.jpg)

## Expected result

- Group: `review`; provenance: `geometry_fixture`.
- Expected subject: `2`; acceptable IDs: `[2]`.
- Expected status: `selected`; expected selection mode: `confident`.
- Interaction: `{"tap": [0, 0], "aim": [0.8, 0.5]}`.
- Annotation source: declared geometry fixture.
- Complete label GT: `False`.

Diagnostic geometry fixture, not a photograph or model output. The gold crosshair marks the photo center; no aim is supplied unless declared.

This is a diagnostic geometry fixture, not a photo. Annotated expected geometry and detector input masks are identified separately below. The new selector contract is not scored as legacy scene-v1 accuracy; target differences are shown only as observations.

## Original input and masks

![Original fb-missed-tap-reticle](../assets/images/fb-missed-tap-reticle.png)

![Masks fb-missed-tap-reticle](../overlays/fb-missed-tap-reticle.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | bottle | `None` |  | [view raw mask](../assets/masks/fb-missed-tap-reticle-i1.png) |
| `2` | bottle | `None` | yes | [view raw mask](../assets/masks/fb-missed-tap-reticle-i2.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine bottle | 0.9 | `[15, 20, 85, 230]` | [view input mask](../fixture-masks/fb-missed-tap-reticle-d0.png) |
| `d1` | wine bottle | 0.9 | `[155, 20, 225, 230]` | [view input mask](../fixture-masks/fb-missed-tap-reticle-d1.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET DIFFERS (new contract not scored) | `1` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `2` | `confident` | not scored | `explicit_capture_reticle` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-missed-tap-reticle-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-missed-tap-reticle-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-missed-tap-reticle-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-missed-tap-reticle-fallback-semantic-v2-keep.png)
