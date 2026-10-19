# fb-held-unlabelled-carton Wine label presence cannot override stronger contact with an unlabelled held carton

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-held-unlabelled-carton.json)

**scene-v1:** Contract N/A; fallback: target match  
**semantic-v2:** Recorded checks pass

![fb-held-unlabelled-carton comparison](../previews/fb-held-unlabelled-carton.jpg)

## Expected result

- Group: `review`; provenance: `geometry_fixture`.
- Expected subject: `3`; acceptable IDs: `[3]`.
- Expected status: `selected`; expected selection mode: `confident`.
- Interaction: `{}`.
- Annotation source: declared geometry fixture.
- Complete label GT: `False`.

Diagnostic geometry fixture, not a photograph or model output. The gold crosshair marks the photo center; no aim is supplied unless declared.

This is a diagnostic geometry fixture, not a photo. Annotated expected geometry and detector input masks are identified separately below. The new selector contract is not scored as legacy scene-v1 accuracy; target differences are shown only as observations.

## Original input and masks

![Original fb-held-unlabelled-carton](../assets/images/fb-held-unlabelled-carton.png)

![Masks fb-held-unlabelled-carton](../overlays/fb-held-unlabelled-carton.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | bottle | `None` |  | [view raw mask](../assets/masks/fb-held-unlabelled-carton-i1.png) |
| `2` | label_front | `None` |  | [view raw mask](../assets/masks/fb-held-unlabelled-carton-i2.png) |
| `3` | box | `None` | yes | [view raw mask](../assets/masks/fb-held-unlabelled-carton-i3.png) |
| `4` | hand | `None` |  | [view raw mask](../assets/masks/fb-held-unlabelled-carton-i4.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine bottle | 0.9 | `[15, 20, 85, 230]` | [view input mask](../fixture-masks/fb-held-unlabelled-carton-d0.png) |
| `d1` | wine label | 0.9 | `[20, 100, 80, 180]` | [view input mask](../fixture-masks/fb-held-unlabelled-carton-d1.png) |
| `d2` | box | 0.9 | `[80, 65, 155, 170]` | [view input mask](../fixture-masks/fb-held-unlabelled-carton-d2.png) |
| `d3` | hand | 0.9 | `[85, 80, 115, 190]` | [view input mask](../fixture-masks/fb-held-unlabelled-carton-d3.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET MATCH (new contract not scored) | `3` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `3` | `confident` | not scored | `unique_visible_hand_contact` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-held-unlabelled-carton-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-held-unlabelled-carton-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-held-unlabelled-carton-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-held-unlabelled-carton-fallback-semantic-v2-keep.png)
