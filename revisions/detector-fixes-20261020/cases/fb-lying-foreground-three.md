# fb-lying-foreground-three A lying foreground bottle survives two upright bottles near center

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-lying-foreground-three.json)

**scene-v1:** Contract N/A; fallback: target differs  
**semantic-v2:** Recorded checks pass

![fb-lying-foreground-three comparison](../previews/fb-lying-foreground-three.jpg)

## Expected result

- Group: `review`; provenance: `geometry_fixture`.
- Expected subject: `1`; acceptable IDs: `[1]`.
- Expected status: `selected`; expected selection mode: `confident`.
- Interaction: `{}`.
- Annotation source: declared geometry fixture.
- Complete label GT: `False`.

Diagnostic geometry fixture, not a photograph or model output. The gold crosshair marks the photo center; no aim is supplied unless declared.

This is a diagnostic geometry fixture, not a photo. Annotated expected geometry and detector input masks are identified separately below. The new selector contract is not scored as legacy scene-v1 accuracy; target differences are shown only as observations.

## Original input and masks

![Original fb-lying-foreground-three](../assets/images/fb-lying-foreground-three.png)

![Masks fb-lying-foreground-three](../overlays/fb-lying-foreground-three.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | bottle | `None` | yes | [view raw mask](../assets/masks/fb-lying-foreground-three-i1.png) |
| `2` | bottle | `None` |  | [view raw mask](../assets/masks/fb-lying-foreground-three-i2.png) |
| `3` | bottle | `None` |  | [view raw mask](../assets/masks/fb-lying-foreground-three-i3.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine bottle | 0.9 | `[10, 180, 230, 230]` | [view input mask](../fixture-masks/fb-lying-foreground-three-d0.png) |
| `d1` | wine bottle | 0.9 | `[95, 60, 125, 140]` | [view input mask](../fixture-masks/fb-lying-foreground-three-d1.png) |
| `d2` | wine bottle | 0.9 | `[150, 50, 180, 130]` | [view input mask](../fixture-masks/fb-lying-foreground-three-d2.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET DIFFERS (new contract not scored) | `2` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `1` | `confident` | not scored | `foreground_scale_and_lower_base` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-lying-foreground-three-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-lying-foreground-three-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-lying-foreground-three-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-lying-foreground-three-fallback-semantic-v2-keep.png)
