# fb-mask-tap-over-label-box A real mask hit beats another label's rectangle

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-mask-tap-over-label-box.json)

**scene-v1:** Contract N/A; fallback: target differs  
**semantic-v2:** Recorded checks pass

![fb-mask-tap-over-label-box comparison](../previews/fb-mask-tap-over-label-box.jpg)

## Expected result

- Group: `review`; provenance: `geometry_fixture`.
- Expected subject: `3`; acceptable IDs: `[3]`.
- Expected status: `selected`; expected selection mode: `confident`.
- Interaction: `{"tap": [0.54, 0.6]}`.
- Annotation source: declared geometry fixture.
- Complete label GT: `False`.

Diagnostic geometry fixture, not a photograph or model output. The gold crosshair marks the photo center; no aim is supplied unless declared.

This is a diagnostic geometry fixture, not a photo. Annotated expected geometry and detector input masks are identified separately below. The new selector contract is not scored as legacy scene-v1 accuracy; target differences are shown only as observations.

## Original input and masks

![Original fb-mask-tap-over-label-box](../assets/images/fb-mask-tap-over-label-box.png)

![Masks fb-mask-tap-over-label-box](../overlays/fb-mask-tap-over-label-box.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | bottle | `None` |  | [view raw mask](../assets/masks/fb-mask-tap-over-label-box-i1.png) |
| `2` | bottle | `None` |  | [view raw mask](../assets/masks/fb-mask-tap-over-label-box-i2.png) |
| `3` | bottle | `None` | yes | [view raw mask](../assets/masks/fb-mask-tap-over-label-box-i3.png) |
| `4` | label_front | `None` |  | [view raw mask](../assets/masks/fb-mask-tap-over-label-box-i4.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine bottle | 0.9 | `[10, 20, 80, 230]` | [view input mask](../fixture-masks/fb-mask-tap-over-label-box-d0.png) |
| `d1` | wine bottle | 0.9 | `[100, 20, 124, 230]` | [view input mask](../fixture-masks/fb-mask-tap-over-label-box-d1.png) |
| `d2` | wine bottle | 0.9 | `[125, 20, 195, 230]` | [view input mask](../fixture-masks/fb-mask-tap-over-label-box-d2.png) |
| `d3` | wine label | 0.9 | `[20, 100, 135, 180]` | [view input mask](../fixture-masks/fb-mask-tap-over-label-box-d3.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET DIFFERS (new contract not scored) | `2` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `3` | `confident` | not scored | `explicit_tap` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-mask-tap-over-label-box-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-mask-tap-over-label-box-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-mask-tap-over-label-box-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-mask-tap-over-label-box-fallback-semantic-v2-keep.png)
