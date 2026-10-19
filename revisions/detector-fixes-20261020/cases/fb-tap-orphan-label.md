# fb-tap-orphan-label An explicit tap can select an off-center unowned label

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-tap-orphan-label.json)

**scene-v1:** Contract N/A; fallback: target differs  
**semantic-v2:** Recorded checks pass

![fb-tap-orphan-label comparison](../previews/fb-tap-orphan-label.jpg)

## Expected result

- Group: `review`; provenance: `geometry_fixture`.
- Expected subject: `2`; acceptable IDs: `[2]`.
- Expected status: `selected`; expected selection mode: `confident`.
- Interaction: `{"tap": [0.2, 0.5]}`.
- Annotation source: declared geometry fixture.
- Complete label GT: `False`.

Diagnostic geometry fixture, not a photograph or model output. The gold crosshair marks the photo center; no aim is supplied unless declared.

This is a diagnostic geometry fixture, not a photo. Annotated expected geometry and detector input masks are identified separately below. The new selector contract is not scored as legacy scene-v1 accuracy; target differences are shown only as observations.

## Original input and masks

![Original fb-tap-orphan-label](../assets/images/fb-tap-orphan-label.png)

![Masks fb-tap-orphan-label](../overlays/fb-tap-orphan-label.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | bottle | `None` |  | [view raw mask](../assets/masks/fb-tap-orphan-label-i1.png) |
| `2` | label_front | `None` | yes | [view raw mask](../assets/masks/fb-tap-orphan-label-i2.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine bottle | 0.9 | `[150, 30, 190, 230]` | [view input mask](../fixture-masks/fb-tap-orphan-label-d0.png) |
| `d1` | wine label | 0.9 | `[0, 50, 110, 190]` | [view input mask](../fixture-masks/fb-tap-orphan-label-d1.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET DIFFERS (new contract not scored) | `1` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `2` | `confident` | not scored | `explicit_tap` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-tap-orphan-label-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-tap-orphan-label-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-tap-orphan-label-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-tap-orphan-label-fallback-semantic-v2-keep.png)

Label crop views: [view 1](../assets/crops/fb-tap-orphan-label-fallback-semantic-v2-label-0.png).
