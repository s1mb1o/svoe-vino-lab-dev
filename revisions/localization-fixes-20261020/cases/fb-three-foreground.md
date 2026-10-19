# fb-three-foreground Three bottles: off-center foreground beats two near-center backgrounds

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-three-foreground.json)

**scene-v1:** Contract N/A; fallback: target differs  
**semantic-v2:** Recorded checks pass

![fb-three-foreground comparison](../previews/fb-three-foreground.jpg)

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

![Original fb-three-foreground](../assets/images/fb-three-foreground.png)

![Masks fb-three-foreground](../overlays/fb-three-foreground.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | bottle | `None` | yes | [view raw mask](../assets/masks/fb-three-foreground-i1.png) |
| `2` | bottle | `None` |  | [view raw mask](../assets/masks/fb-three-foreground-i2.png) |
| `3` | bottle | `None` |  | [view raw mask](../assets/masks/fb-three-foreground-i3.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine bottle | 0.9 | `[0, 0, 70, 240]` | [view input mask](../fixture-masks/fb-three-foreground-d0.png) |
| `d1` | wine bottle | 0.9 | `[100, 65, 155, 215]` | [view input mask](../fixture-masks/fb-three-foreground-d1.png) |
| `d2` | wine bottle | 0.9 | `[165, 65, 220, 215]` | [view input mask](../fixture-masks/fb-three-foreground-d2.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET DIFFERS (new contract not scored) | `2` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `1` | `confident` | not scored | `foreground_scale_and_lower_base` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-three-foreground-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-three-foreground-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-three-foreground-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-three-foreground-fallback-semantic-v2-keep.png)
