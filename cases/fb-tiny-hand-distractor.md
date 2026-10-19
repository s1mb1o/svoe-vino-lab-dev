# fb-tiny-hand-distractor A small contacted can cannot cancel a larger grip (contact alone is unconfirmed; use geometric fallback)

[All cases](../README.md) · [Group](../groups/review.md) · [Exact case metadata](../evidence/fb-tiny-hand-distractor.json)

**scene-v1:** Contract N/A; fallback: target differs  
**semantic-v2:** Recorded checks pass

![fb-tiny-hand-distractor comparison](../previews/fb-tiny-hand-distractor.jpg)

## Expected result

- Group: `review`; provenance: `geometry_fixture`.
- Expected subject: `4`; acceptable IDs: `[4]`.
- Expected status: `selected`; expected selection mode: `fallback`.
- Interaction: `{}`.
- Annotation source: declared geometry fixture.
- Complete label GT: `False`.

Diagnostic geometry fixture, not a photograph or model output. The gold crosshair marks the photo center; no aim is supplied unless declared.

This is a diagnostic geometry fixture, not a photo. Annotated expected geometry and detector input masks are identified separately below. The new selector contract is not scored as legacy scene-v1 accuracy; target differences are shown only as observations.

## Original input and masks

![Original fb-tiny-hand-distractor](../assets/images/fb-tiny-hand-distractor.png)

![Masks fb-tiny-hand-distractor](../overlays/fb-tiny-hand-distractor.png)

| Mask ID | Category | Parent | Expected subject or label | Original binary PNG |
|---|---|---|---|---|
| `1` | bottle | `None` |  | [view raw mask](../assets/masks/fb-tiny-hand-distractor-i1.png) |
| `2` | bottle | `None` |  | [view raw mask](../assets/masks/fb-tiny-hand-distractor-i2.png) |
| `3` | hand | `None` |  | [view raw mask](../assets/masks/fb-tiny-hand-distractor-i3.png) |
| `4` | can | `None` | yes | [view raw mask](../assets/masks/fb-tiny-hand-distractor-i4.png) |

## Declared detector input masks

These masks are the exact PNG bytes supplied as fixture detections. They may differ from the annotated expected geometry above. Source detector indices are not ground-truth instance IDs.

| Detector index | Class | Score | Input box | Original mask PNG |
|---|---|---:|---|---|
| `d0` | wine bottle | 0.9 | `[20, 20, 90, 230]` | [view input mask](../fixture-masks/fb-tiny-hand-distractor-d0.png) |
| `d1` | wine bottle | 0.9 | `[140, 20, 210, 230]` | [view input mask](../fixture-masks/fb-tiny-hand-distractor-d1.png) |
| `d2` | hand | 0.9 | `[90, 80, 110, 190]` | [view input mask](../fixture-masks/fb-tiny-hand-distractor-d2.png) |
| `d3` | can | 0.9 | `[110, 100, 120, 120]` | [view input mask](../fixture-masks/fb-tiny-hand-distractor-d3.png) |

## Saved selector outputs

`live` replays saved detector responses; `controlled` uses declared GT-derived detections and faults. No new inference was run for this gallery. Expected-label retention below 98% is flagged separately from target matching. A full-frame crop can retain distractors.

### fallback

| Selector | Result | Assigned subject | Mode | Expected-label retention | Reason |
|---|---|---|---|---|---|
| `scene-v1` | LEGACY: TARGET DIFFERS (new contract not scored) | `2` | `legacy` | not scored | `existing_scene_v1_rank` |
| `semantic-v2` | Recorded checks pass | `4` | `fallback` | not scored | `fallback_nearest_center` |

#### scene-v1 fallback crop

![scene-v1 fallback crop](../assets/crops/fb-tiny-hand-distractor-fallback-scene-v1.png)

[View original selector keep mask](../assets/crops/fb-tiny-hand-distractor-fallback-scene-v1-keep.png)

#### semantic-v2 fallback crop

![semantic-v2 fallback crop](../assets/crops/fb-tiny-hand-distractor-fallback-semantic-v2.png)

[View original selector keep mask](../assets/crops/fb-tiny-hand-distractor-fallback-semantic-v2-keep.png)
